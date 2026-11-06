"""Offline diagnostic trajectories; oracle/no-op adapters make no model calls."""

import argparse
import difflib
import hashlib
import json
import os
from pathlib import Path
import random
import time
import uuid

from evaluation.grading import grade
from evaluation.offline import CONDITIONS, FIXTURE, GUIDE, _facts_at_step
from evaluation.sandbox import DockerSandbox, IMAGE


BEGIN = '# BEGIN reference context (diagnostic oracle)\n'
END = '# END reference context\n'


def _json(value) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=True, allow_nan=False)


def _hash(value) -> str:
    return hashlib.sha256(_json(value).encode()).hexdigest()


def _write_record(path: Path, payload: dict) -> None:
    # Exclusive creation and fsync preserve completed attempts across safe resumes.
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(_json({'sha256': _hash(payload), 'payload': payload}) + '\n')
        stream.flush()
        os.fsync(stream.fileno())


def read_record(path: Path) -> dict:
    envelope = json.loads(path.read_text(encoding='utf-8'))
    if (not isinstance(envelope, dict) or set(envelope) != {'sha256', 'payload'}
            or not isinstance(envelope['payload'], dict)
            or _hash(envelope['payload']) != envelope['sha256']):
        raise ValueError(f'corrupt record: {path.name}')
    return envelope['payload']


def _facts(step: int) -> list[dict]:
    manifest = json.loads((FIXTURE / 'manifest.json').read_text(encoding='utf-8'))
    return _facts_at_step(manifest, step)


def context_files(previous: dict[str, str], condition: str, step: int) -> dict[str, str]:
    if condition not in CONDITIONS or type(step) is not int or step not in (1, 2, 3):
        raise ValueError('invalid condition or step')
    files = dict(previous)
    source = files['policy.py']
    if source.startswith(BEGIN):
        if END not in source:
            raise ValueError('reference context boundary was damaged')
        source = source.split(END, 1)[1]
    files['policy.py'] = source
    files.pop('context.md', None)
    files['TASK.md'] = (FIXTURE / 'private' / f'step-{step}.md').read_text(encoding='utf-8')
    files['README.md'] = GUIDE
    facts = _facts(step)
    if condition == 'inline':
        files['policy.py'] = BEGIN + ''.join(f"# {f['text']}\n" for f in facts) + END + source
    elif condition == 'external':
        files['context.md'] = '# policy.py reference context\n\n' + ''.join(f"- {f['text']}\n" for f in facts)
    return files


def _config(seed, mode, adapter, image, timeout) -> dict:
    if type(seed) is not int or mode not in ('discovery', 'controlled') or adapter not in ('oracle', 'noop'):
        raise ValueError('invalid seed, exposure mode or diagnostic adapter')
    DockerSandbox({}, image=image, timeout=timeout)  # Validate limits without executing.
    root = Path(__file__).resolve().parent
    paths = sorted(FIXTURE.rglob('*')) + [root / name for name in ('runner.py', 'sandbox.py', 'grading.py', 'offline.py')]
    hashes = {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in paths if p.is_file() and '__pycache__' not in p.parts}
    order = list(CONDITIONS)
    random.Random(seed).shuffle(order)
    return {'schema_version': 1, 'seed': seed, 'mode': mode, 'adapter': adapter,
            'condition_order': order, 'image': image, 'command_timeout_seconds': timeout,
            'artifact_hashes': hashes, 'model_spend_limit_usd': 0,
            'kind': 'public_development_diagnostic', 'efficacy_evidence': False}


def _attempt(before: dict, condition: str, step: int, config: dict, run_id: str) -> dict:
    started = time.monotonic()
    prompt = 'Read README.md and TASK.md; inspect policy.py and context.md if present. Complete only the current task.'
    if config['mode'] == 'controlled':
        prompt += '\nMatched reference facts:\n' + ('\n'.join(f['text'] for f in _facts(step))
                                                    if condition != 'baseline' else '(baseline: no added facts)')
    record = {'run_id': run_id, 'condition': condition, 'step': step,
              'before': before, 'before_sha256': _hash(before), 'prompt': prompt,
              'observations': [], 'after': None, 'patch': None, 'grading': None,
              'status': 'infrastructure_error', 'error': None,
              'usage': {'model_calls': 0, 'input_tokens': None, 'output_tokens': None,
                        'model_cost_usd': 0, 'infrastructure_cost_usd': None}}
    try:
        with DockerSandbox(before, image=config['image'], timeout=config['command_timeout_seconds']) as sandbox:
            # Scripted discovery tests the trace path, not a model's retrieval choices.
            command = ['python', '-I', '-B', '-c',
                       "import json,pathlib; print(json.dumps({p:pathlib.Path(p).read_text() for p in ('README.md','TASK.md','policy.py','context.md') if pathlib.Path(p).is_file()}))"]
            observed = sandbox.run(command)
            record['observations'].append({'command': command, 'output': observed.output,
                                           'returncode': observed.returncode,
                                           'timed_out': observed.timed_out, 'output_limited': observed.output_limited,
                                           'wall_seconds': observed.elapsed_seconds})
            if observed.returncode or observed.timed_out or observed.output_limited:
                raise RuntimeError('diagnostic read failed')
            if config['adapter'] == 'oracle':
                # This adapter deliberately knows the current reference answer. It is
                # a plumbing oracle and must never be reported as an agent outcome.
                source = (FIXTURE / 'private' / 'reference' / f'step-{step}.py').read_text(encoding='utf-8')
                source = context_files({'policy.py': source}, condition, step)['policy.py']
                command = ['python', '-I', '-B', '-c', "import pathlib,sys; pathlib.Path('policy.py').write_text(sys.stdin.read(),encoding='utf-8')"]
                edited = sandbox.run(command, source)
                record['observations'].append({'command': command, 'stdin': source, 'output': edited.output,
                                               'returncode': edited.returncode, 'timed_out': edited.timed_out,
                                               'output_limited': edited.output_limited, 'wall_seconds': edited.elapsed_seconds})
                if edited.returncode or edited.timed_out or edited.output_limited:
                    raise RuntimeError('oracle edit failed')
            after = sandbox.snapshot()
        if set(after) != set(before) or any(after[name] != before[name] for name in before if name != 'policy.py'):
            raise ValueError('diagnostic adapter changed protected inputs or workspace shape')
        record['after'] = after
        record['patch'] = ''.join(difflib.unified_diff(before['policy.py'].splitlines(keepends=True),
                                                    after['policy.py'].splitlines(keepends=True),
                                                    fromfile='before/policy.py', tofile='after/policy.py'))
        record['grading'] = grade({'policy.py': after['policy.py']}, step,
                                  image=config['image'], timeout=config['command_timeout_seconds'])
        record['status'] = 'passed' if record['grading']['passed'] else 'failed'
    except (OSError, RuntimeError, ValueError) as error:
        record['error'] = f'{type(error).__name__}: {error}'
    record['wall_seconds'] = time.monotonic() - started
    return record


def run_diagnostic(destination: Path, *, seed: int = 0, mode: str = 'discovery', adapter: str = 'oracle',
                   image: str = IMAGE, timeout: float = 10, resume: bool = False, stop_after: int | None = None) -> dict:
    config = _config(seed, mode, adapter, image, timeout)
    if stop_after is not None and (type(stop_after) is not int or stop_after < 0):
        raise ValueError('stop_after must be a nonnegative integer')
    destination = Path(destination)
    if not resume:
        destination.mkdir(parents=True, exist_ok=False)
    lock = destination / 'run.lock'
    with lock.open('x', encoding='utf-8') as stream:
        stream.write(str(os.getpid()))
    try:
        inflight = destination / 'inflight.json'
        if inflight.exists():
            raise ValueError('ambiguous interrupted attempt; inspect records and containers; automatic replay is refused')
        if resume:
            manifest = read_record(destination / 'manifest.json')
            if manifest.get('config') != config:
                raise ValueError('run configuration or source hashes changed; create a new run')
        else:
            manifest = {'run_id': uuid.uuid4().hex, 'config': config}
            _write_record(destination / 'manifest.json', manifest)
        # Validate the entire existing prefix before any new work, including records
        # after a gap or terminal failure. Checksums detect damage, not malicious hosts.
        existing = {path.name: read_record(path) for path in destination.glob('step-*.json')}
        states, records, expected_names = {}, [], set()
        for condition in config['condition_order']:
            previous = {'policy.py': (FIXTURE / 'initial' / 'policy.py').read_text(encoding='utf-8')}
            next_step = 1
            for step in (1, 2, 3):
                name = f'step-{condition}-{step}.json'
                if name not in existing:
                    break
                before = context_files(previous, condition, step)
                record = existing[name]
                if (record.get('run_id') != manifest['run_id'] or record.get('condition') != condition
                        or record.get('step') != step or record.get('before') != before
                        or record.get('before_sha256') != _hash(before)
                        or record.get('status') not in ('passed', 'failed', 'infrastructure_error')):
                    raise ValueError(f'inconsistent trajectory record: {name}')
                expected_names.add(name)
                records.append(record)
                next_step = step + 1
                if record['status'] != 'passed':
                    next_step = 4
                    break
                previous = record['after']
            states[condition] = (previous, next_step)
        if set(existing) != expected_names:
            raise ValueError('records exist after a gap or terminal failure')
        attempts = 0
        for condition in config['condition_order']:
            previous, next_step = states[condition]
            for step in range(next_step, 4):
                if stop_after is not None and attempts >= stop_after:
                    break
                before = context_files(previous, condition, step)
                _write_record(inflight, {'run_id': manifest['run_id'], 'condition': condition, 'step': step})
                record = _attempt(before, condition, step, config, manifest['run_id'])
                _write_record(destination / f'step-{condition}-{step}.json', record)
                inflight.unlink()
                records.append(record)
                attempts += 1
                if record['status'] != 'passed':
                    break
                previous = record['after']
        trajectories = []
        for condition in config['condition_order']:
            rows = sorted((r for r in records if r['condition'] == condition), key=lambda r: r['step'])
            complete = bool(rows) and (len(rows) == 3 or rows[-1]['status'] != 'passed')
            trajectories.append({'condition': condition, 'complete': complete, 'attempted_steps': len(rows),
                                 'passed': len(rows) == 3 and all(r['status'] == 'passed' for r in rows)})
        return {'run_id': manifest['run_id'], 'kind': config['kind'], 'efficacy_evidence': False,
                'complete': all(t['complete'] for t in trajectories), 'trajectories': trajectories,
                'successful_trajectories': sum(t['passed'] for t in trajectories),
                'attempted_steps': len(records), 'unattempted_steps': 9 - len(records),
                'infrastructure_errors': sum(r['status'] == 'infrastructure_error' for r in records),
                'model_calls': 0, 'model_cost_usd': 0, 'infrastructure_cost_usd': None,
                'wall_seconds': sum(r['wall_seconds'] for r in records)}
    finally:
        lock.unlink()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination', type=Path, required=True)
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--mode', choices=('discovery', 'controlled'), default='discovery')
    parser.add_argument('--adapter', choices=('oracle', 'noop'), default='oracle')
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--stop-after', type=int)
    args = parser.parse_args()
    try:
        report = run_diagnostic(**vars(args))
        print(json.dumps(report, indent=2))
        return 1 if report['infrastructure_errors'] or (report['complete'] and report['successful_trajectories'] < 3) else 0
    except (OSError, ValueError) as error:
        parser.exit(2, f'error: {error}\n')


if __name__ == '__main__':
    raise SystemExit(main())
