import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from evaluation.runner import context_files, read_record, run_diagnostic


class RunnerRecordTests(unittest.TestCase):
    def test_temporal_facts_are_equal_and_retired_before_new_step(self):
        for step in (1, 2, 3):
            inline = context_files({'policy.py': 'def sample(): pass\n'}, 'inline', step)
            external = context_files({'policy.py': 'def sample(): pass\n'}, 'external', step)
            self.assertNotIn('context.md', inline)
            self.assertNotIn('five retries', inline['policy.py'] if step > 1 else '')
            self.assertEqual(inline['TASK.md'], external['TASK.md'])
            self.assertEqual(inline['README.md'], external['README.md'])
            inline_facts = [line[2:] for line in inline['policy.py'].splitlines()
                            if line.startswith('# ') and 'reference context' not in line]
            external_facts = [line[2:] for line in external['context.md'].splitlines() if line.startswith('- ')]
            self.assertEqual(inline_facts, external_facts)
        first = context_files({'policy.py': 'pass\n'}, 'inline', 1)
        second = context_files(first, 'inline', 2)
        self.assertNotIn('five retries', second['policy.py'])
        self.assertEqual(second['policy.py'].count('upgraded backend'), 1)
        self.assertNotIn('Retry delays', second['policy.py'])

    def test_manifest_is_reused_but_drift_and_overwrite_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'run'
            run_diagnostic(path, seed=17, stop_after=0)
            before = (path / 'manifest.json').read_bytes()
            report = run_diagnostic(path, seed=17, resume=True, stop_after=0)
            self.assertFalse(report['complete'])
            self.assertEqual(before, (path / 'manifest.json').read_bytes())
            with self.assertRaises(ValueError):
                run_diagnostic(path, seed=18, resume=True, stop_after=0)
            with self.assertRaises(FileExistsError):
                run_diagnostic(path, seed=17, stop_after=0)

    def test_locked_interrupted_and_corrupted_runs_are_not_replayed(self):
        for filename in ('run.lock', 'inflight.json', 'manifest.json'):
            with self.subTest(filename=filename), tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / 'run'
                run_diagnostic(path, stop_after=0)
                (path / filename).write_text('{}', encoding='utf-8')
                with self.assertRaises((ValueError, FileExistsError)):
                    run_diagnostic(path, resume=True, stop_after=0)

    def test_configuration_validation_precedes_directory_creation(self):
        for options in ({'adapter': 'paid'}, {'mode': 'anything'}, {'seed': True}, {'stop_after': -1}):
            with self.subTest(options=options), tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / 'run'
                with self.assertRaises(ValueError):
                    run_diagnostic(path, **options)
                self.assertFalse(path.exists())

    def test_interruption_leaves_ambiguous_attempt_guard_and_no_replay(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'run'
            with patch('evaluation.runner._attempt', side_effect=KeyboardInterrupt) as adapter:
                with self.assertRaises(KeyboardInterrupt):
                    run_diagnostic(path)
                adapter.assert_called_once()
            self.assertTrue((path / 'inflight.json').exists())
            self.assertFalse((path / 'run.lock').exists())
            with patch('evaluation.runner._attempt') as adapter:
                with self.assertRaises(ValueError):
                    run_diagnostic(path, resume=True)
                adapter.assert_not_called()

    def test_orphan_record_is_rejected_before_any_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'run'
            run_diagnostic(path, stop_after=0)
            payload = {'status': 'passed'}
            import hashlib
            checksum = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
            (path / 'step-inline-3.json').write_text(json.dumps({'sha256': checksum, 'payload': payload}), encoding='utf-8')
            with patch('evaluation.runner._attempt') as adapter:
                with self.assertRaises(ValueError):
                    run_diagnostic(path, resume=True)
                adapter.assert_not_called()


@unittest.skipUnless(os.environ.get('CODE_COMMENTS_DOCKER') == '1', 'opt-in Docker integration')
class DockerTrajectoryTests(unittest.TestCase):
    def test_oracle_replay_and_resume_preserve_records_and_cumulative_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'run'
            partial = run_diagnostic(path, seed=4, stop_after=1)
            self.assertFalse(partial['complete'])
            first = next(path.glob('step-*.json'))
            before = first.read_bytes()
            report = run_diagnostic(path, seed=4, resume=True)
            self.assertTrue(report['complete'])
            self.assertEqual(report['successful_trajectories'], 3)
            self.assertEqual(report['model_calls'], 0)
            self.assertEqual(before, first.read_bytes())
            self.assertEqual(len(list(path.glob('step-*.json'))), 9)
            replay = run_diagnostic(path, seed=4, resume=True)
            self.assertEqual(report, replay)
            for filename in path.glob('step-*.json'):
                record = read_record(filename)
                self.assertTrue(record['grading']['passed'])
                self.assertTrue(record['observations'])
                self.assertIsNone(record['usage']['input_tokens'])
                if record['step'] == 3:
                    self.assertIn('override=None', record['before']['policy.py'])
                    self.assertNotIn('five retries', record['before']['policy.py'])
            envelope = json.loads(first.read_text(encoding='utf-8'))
            envelope['payload']['status'] = 'failed'
            first.write_text(json.dumps(envelope), encoding='utf-8')
            with self.assertRaises(ValueError):
                run_diagnostic(path, seed=4, resume=True)

    def test_noop_failure_stops_each_trajectory_without_inventing_later_attempts(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'run'
            report = run_diagnostic(path, adapter='noop', mode='controlled')
            self.assertTrue(report['complete'])
            self.assertEqual(report['successful_trajectories'], 0)
            self.assertEqual(report['attempted_steps'], 3)
            self.assertEqual(report['unattempted_steps'], 6)
            for filename in path.glob('step-*.json'):
                record = read_record(filename)
                self.assertIn('Matched reference facts', record['prompt'])
                self.assertEqual(record['step'], 1)
                self.assertEqual(record['status'], 'failed')


if __name__ == '__main__':
    unittest.main()
