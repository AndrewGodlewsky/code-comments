"""CLI for the `comment-edit` eval: list cases, self-test the grader, init a flow, run a variant.

python -m evaluation.skill_eval.run cases
python -m evaluation.skill_eval.run selftest
python -m evaluation.skill_eval.run init --flow-dir .claude/hillclimb/comment-edit --seed 7
python -m evaluation.skill_eval.run run --flow-dir .claude/hillclimb/comment-edit --adapter oracle --variant baseline
"""

import argparse
import concurrent.futures
import difflib
import hashlib
import json
from pathlib import Path
import random
import re
import shutil
import sys
import tempfile
import threading
import time

from .adapters import ADAPTERS
from .grade import CASES, FAMILIES, Case, GraderError, grade, load_cases


ROOT = Path(__file__).resolve().parents[2]
HARNESS_PATHS = [
    "evaluation/skill_eval/adapters.py",
    "evaluation/skill_eval/check_runner.py",
    "evaluation/skill_eval/comments.py",
    "evaluation/skill_eval/grade.py",
    "evaluation/skill_eval/live.py",
    "evaluation/skill_eval/run.py",
]
METRIC_DECLARATIONS = [
    {"id": "pass", "kind": "binary", "label": "Pass"},
    {"id": "behavior", "kind": "binary", "label": "Behavior"},
    {"id": "recall", "kind": "float", "label": "Fact recall"},
    {"id": "misplaced", "kind": "float", "better": "lower", "label": "Misplaced"},
    {"id": "bad_claims", "kind": "float", "better": "lower", "label": "Bad claims"},
    {"id": "preserved", "kind": "float", "label": "Preserved"},
    {"id": "noise_lines", "kind": "float", "better": "lower", "label": "Noise lines"},
]


def case_set_version(root: Path = CASES) -> str:
    digest = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if p.is_file() and "__pycache__" not in p.parts):
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(path.read_bytes().replace(b"\r\n", b"\n"))
    return digest.hexdigest()[:12]


def harness_sha(paths: list[str]) -> str:
    digest = hashlib.sha256()
    for relative in sorted(paths):
        digest.update(relative.encode())
        digest.update((ROOT / relative).read_bytes().replace(b"\r\n", b"\n"))
    return digest.hexdigest()


def prepare(case: Case, destination: Path) -> Path:
    workspace = destination / case.id
    shutil.copytree(case.visible, workspace)
    return workspace


def diff(case: Case, workspace: Path) -> str:
    chunks = []
    for name in case.spec["files"]:
        before = (case.visible / name).read_text(encoding="utf-8").splitlines(keepends=True) if (case.visible / name).is_file() else []
        after = (workspace / name).read_text(encoding="utf-8").splitlines(keepends=True) if (workspace / name).is_file() else []
        chunks.extend(difflib.unified_diff(before, after, f"a/{name}", f"b/{name}"))
    return "".join(chunks) or "(no changes)"


def attempt(case: Case, adapter: str, scratch: Path, live_options: dict | None = None) -> dict:
    """Run one adapter on a fresh workspace and grade the end state."""
    workspace = prepare(case, scratch)
    started = time.perf_counter()
    if adapter == "live":
        from . import live  # spends money; imported only when asked for
        result = live.run(case, workspace, **(live_options or {}))
    else:
        result = {"note": ADAPTERS[adapter](case, workspace), "model": f"offline:{adapter}",
                  "usage": {"input_tokens": 0, "output_tokens": 0}}
        result["trace"] = [{"role": "system", "content": f"Offline adapter `{adapter}`; no model was called."},
                           {"role": "user", "content": case.task}]
    result.setdefault("latency_s", round(time.perf_counter() - started, 4))
    result["scores"], result["explanation"] = grade(case, workspace)
    result["diff"] = diff(case, workspace)
    return result


# --- commands -----------------------------------------------------------------


def _fenced(text: str, info: str = "") -> str:
    fence = "`" * max(4, max((len(run) for run in re.findall(r"`+", text)), default=0) + 1)
    return f"{fence}{info}\n{text.rstrip()}\n{fence}\n"


def cmd_cases(args: argparse.Namespace) -> int:
    cases = load_cases()
    print(f"# comment-edit seed cases (version {case_set_version()}, {len(cases)} cases)\n")
    print("| id | family | tags | summary |\n| --- | --- | --- | --- |")
    for case in cases:
        print(f"| {case.id} | {case.family} | {', '.join(case.spec['tags'][1:])} | {case.spec['summary']} |")
    for case in cases:
        print(f"\n## {case.id}\n\n{case.spec['summary']}\n")
        for path in sorted(p for p in case.visible.rglob("*") if p.is_file()):
            print(f"### visible/{path.relative_to(case.visible).as_posix()}\n\n{_fenced(path.read_text(encoding='utf-8'))}")
        if args.with_ledger:
            # Grader-only material: for the user's grading sign-off, never for an agent under test.
            print(f"### private/case.json (grader only)\n\n{_fenced((case.private / 'case.json').read_text(encoding='utf-8'), 'json')}")
            for path in sorted((case.private / "reference").rglob("*")):
                if path.is_file():
                    print(f"### private/reference/{path.relative_to(case.private / 'reference').as_posix()}\n\n{_fenced(path.read_text(encoding='utf-8'), 'python')}")
    return 0


# Expected bands per adapter. A case that violates its band is broken, not hard.
def _band_failures(adapter: str, case: Case, scores: dict) -> list[str]:
    spec = case.spec
    problems = []
    if adapter == "oracle" and scores["pass"] != 1:
        problems.append("oracle must pass")
    if adapter == "null" and scores["pass"] != 0:
        problems.append("null must fail")
    if adapter == "strip" and (spec.get("required_facts") or spec.get("protected_comments")):
        if scores["recall"] == 1.0 and scores["preserved"] == 1.0:
            problems.append("strip must lose a required fact or protected comment")
    if adapter == "spam" and scores["noise_lines"] <= spec["noise_budget"]:
        problems.append("spam must exceed the noise budget")
    if adapter == "stale" and spec.get("forbidden_claims") and scores["bad_claims"] == 0:
        problems.append("stale must register bad claims")
    return problems


def _case_validity(case: Case) -> list[str]:
    """Each ledger entry must match its own text, and the reference must touch graded files."""
    from .comments import normalize
    from .grade import matches
    problems = []
    for item in case.spec.get("required_facts", []) + case.spec.get("forbidden_claims", []):
        if not matches(item["anchors"], normalize(item["text"])):
            problems.append(f"{item['id']}: anchors do not match its own text")
    # Probe sentences pin down anchor behaviour: paraphrases a fact must accept, and
    # correct remarks (often negations of the refuted idea) a claim must not flag.
    for fact in case.spec.get("required_facts", []):
        for sentence in fact.get("also_matching", []):
            if not matches(fact["anchors"], normalize(sentence)):
                problems.append(f"{fact['id']}: rejects accepted paraphrase {sentence!r}")
    for claim in case.spec.get("forbidden_claims", []):
        for sentence in claim.get("not_matching", []):
            if matches(claim["anchors"], normalize(sentence)):
                problems.append(f"{claim['id']}: flags correct remark {sentence!r}")
    if not (case.private / "reference").is_dir():
        problems.append("missing private/reference")
    if case.spec["behavior"] == "checks" and not (case.private / "checks.py").is_file():
        problems.append("missing private/checks.py")
    leaks = [p.name for p in case.visible.rglob("*") if p.name in {"case.json", "checks.py"} or "reference" in p.parts]
    if leaks:
        problems.append(f"grader material in visible/: {leaks}")
    return problems


def cmd_selftest(_: argparse.Namespace) -> int:
    broken: list[str] = []
    cases = load_cases(problems=broken)
    if not cases:
        print("no cases found", file=sys.stderr)
        return 1
    totals: dict[str, list[int]] = {name: [] for name in ADAPTERS}
    with tempfile.TemporaryDirectory() as temporary:
        for case in cases:
            broken += [f"{case.id}: {p}" for p in _case_validity(case)]
            for adapter in ADAPTERS:
                try:
                    result = attempt(case, adapter, Path(temporary) / adapter)
                except GraderError as error:
                    broken.append(f"{case.id} [{adapter}]: grader error: {error}")
                    continue
                totals[adapter].append(result["scores"]["pass"])
                broken += [f"{case.id} [{adapter}]: {p} (scores {result['scores']}; {result['explanation']})" for p in _band_failures(adapter, case, result["scores"])]
    counts = {family: sum(case.family == family for case in cases) for family in FAMILIES}
    print(json.dumps({
        "kind": "skill_eval_selftest", "model_calls": 0, "case_set_version": case_set_version(),
        "cases": len(cases), "families": counts,
        "pass_rate": {name: round(sum(v) / len(v), 3) if v else None for name, v in totals.items()},
        "passed": not broken, "problems": broken,
    }, indent=2))
    return 0 if not broken else 1


def cmd_init(args: argparse.Namespace) -> int:
    flow = Path(args.flow_dir)
    state_path = flow / "_state.json"
    if state_path.exists():
        print(f"{state_path} exists; the split is fixed once. Delete it deliberately to re-draw.", file=sys.stderr)
        return 1
    cases = load_cases()
    rng = random.Random(args.seed)
    train, test = [], []
    for family in FAMILIES:
        ids = sorted(case.id for case in cases if case.family == family)
        rng.shuffle(ids)
        cut = round(len(ids) * args.test_fraction)
        test += ids[:cut]
        train += ids[cut:]
    flow.mkdir(parents=True, exist_ok=True)
    state = {
        "flow": "comment-edit", "current_round": 0, "reps": args.reps,
        "goal": {"target": "pass", "direction": "higher", "hold": ["behavior", "bad_claims", "noise_lines"]},
        "approve_each_round": False, "best": None,
        "case_set_version": case_set_version(), "split_seed": args.seed,
        "train_ids": sorted(train), "test_ids": sorted(test),
        "harness_paths": HARNESS_PATHS,
        "metrics": METRIC_DECLARATIONS,
        "perf_fields": [{"id": "cost_usd", "label": "Cost", "unit": "$"}, {"id": "latency_s", "label": "Latency", "unit": "s"},
                        {"id": "tool_calls", "label": "Tool calls"}],
    }
    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    (flow / "metrics.md").write_text(
        "# comment-edit metrics\n\nSee docs/evaluation/skill-evals.md for definitions. "
        "`pass` is the headline; `bad_claims`, `noise_lines` and `behavior` are guardrails.\n",
        encoding="utf-8",
    )
    print(f"wrote {state_path}: {len(train)} train / {len(test)} test, case set {state['case_set_version']}")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    flow = Path(args.flow_dir)
    state_path = flow / "_state.json"
    if not state_path.is_file():
        print(f"run `init --flow-dir {flow}` first", file=sys.stderr)
        return 1
    if not re.fullmatch(r"baseline|v[1-9][0-9]*", args.variant):
        print("variant must be `baseline` or v<N> (the report builder ignores other names)", file=sys.stderr)
        return 1
    state = json.loads(state_path.read_text(encoding="utf-8"))
    if state.get("case_set_version") != case_set_version():
        print("case set changed since init; scores are not comparable. Re-init deliberately.", file=sys.stderr)
        return 2
    # A change detector, not enforcement: anyone can pass the flag or edit _state.json.
    current = harness_sha(state["harness_paths"])
    if args.approve_harness:
        state["harness_sha"] = current
        state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    elif state.get("harness_sha") != current:
        print("harness files changed or were never approved; the user must re-run with --approve-harness", file=sys.stderr)
        return 2
    reps = args.reps if args.reps is not None else state.get("reps", 1)

    adapter_label = f"live:{args.skill}:{args.model}" if args.adapter == "live" else args.adapter
    variant = flow / args.variant
    (variant / "traces").mkdir(parents=True, exist_ok=True)
    results_path, errors_path = variant / "results.jsonl", variant / "errors.jsonl"
    done = set()
    if results_path.is_file():
        kept = []
        for line in results_path.read_text(encoding="utf-8").splitlines():
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                print(f"dropping a truncated row from {results_path}; that (case, rep) will re-run", file=sys.stderr)
                continue
            if row.get("meta", {}).get("adapter") != adapter_label:
                print(f"{variant} holds rows from adapter {row.get('meta', {}).get('adapter')!r}; "
                      f"refusing to mix in {adapter_label!r}. Use a new variant.", file=sys.stderr)
                return 1
            kept.append(line)
            done.add((row["prompt_id"], row["rep"]))
        results_path.write_text("".join(f"{line}\n" for line in kept), encoding="utf-8")
    split = {case_id: "train" for case_id in state["train_ids"]} | {case_id: "test" for case_id in state["test_ids"]}
    wanted = set(args.cases.split(",")) if args.cases else None
    cases = [case for case in load_cases() if case.id in split and (wanted is None or case.id in wanted)]
    if wanted and len(cases) != len(wanted):
        print(f"unknown case ids: {sorted(wanted - {c.id for c in cases})}", file=sys.stderr)
        return 1
    live_options = None
    if args.adapter == "live":
        if not args.skill:
            print("--adapter live needs --skill <variant id from skill-variants/variants.json>", file=sys.stderr)
            return 1
        live_options = {"skill": args.skill, "model": args.model, "timeout_s": args.timeout_s, "max_budget_usd": args.max_budget_usd}
        registry = json.loads((ROOT / "skill-variants/variants.json").read_text(encoding="utf-8"))["variants"]
        hypothesis = next(v["hypothesis"] for v in registry if v["id"] == args.skill)
        if args.variant != "baseline":
            # The report builder takes a variant's one-line description from change.md.
            (variant / "change.md").write_text(f"Skill variant `{args.skill}`: {hypothesis}\n", encoding="utf-8")
        description = args.description or f"skill variant {args.skill} on {args.model}"
    else:
        description = args.description or f"offline adapter: {args.adapter}"
    summary = {"description": description, "label": args.skill or args.adapter, "target": "skill"}
    (variant / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    counts = {"written": 0, "failed": 0}
    lock = threading.Lock()

    def one(case: Case, rep: int, temporary: str) -> None:
        try:
            result = attempt(case, args.adapter, Path(temporary) / f"rep{rep}", live_options)
        except Exception as error:  # never abort the run; never score plumbing as a model failure
            failure_class = getattr(error, "failure_class", None) or (
                "grader_error" if isinstance(error, GraderError) else "harness_exception")
            entry = {"prompt_id": case.id, "rep": rep, "failure_class": failure_class,
                     "error": f"{type(error).__name__}: {error}", "retries": 0}
            if getattr(error, "usage", None):
                entry.update(model=error.model, usage=error.usage)  # billed-but-failed spend is still spend
            with lock:
                counts["failed"] += 1
                with errors_path.open("a", encoding="utf-8") as errors:
                    errors.write(json.dumps(entry) + "\n")
            return
        trace = result["trace"] + [{"role": "assistant", "content": f"{result['note']}\n\n```diff\n{result['diff']}```"}]
        row = {
            "prompt_id": case.id, "rep": rep, "prompt": case.task, "tags": case.spec["tags"],
            "split": split[case.id], "status": "ok", "stop_reason": result.get("stop_reason"),
            "grade": result["scores"], "explanation": result["explanation"],
            "model": result["model"], "latency_s": result["latency_s"], "usage": result["usage"],
            "meta": {"offline": args.adapter != "live", "adapter": adapter_label, "case_set_version": state["case_set_version"]},
        }
        for field in ("cost_usd", "tool_calls", "num_turns", "wall_s"):
            if result.get(field) is not None:
                row[field] = result[field]
        with lock:
            (variant / "traces" / f"{case.id}_rep{rep}.json").write_text(json.dumps(trace, indent=2) + "\n", encoding="utf-8")
            with results_path.open("a", encoding="utf-8") as results:
                results.write(json.dumps(row) + "\n")
            counts["written"] += 1
            print(f"  {case.id} rep{rep}: pass={row['grade']['pass']} cost={row.get('cost_usd')}", flush=True)

    with tempfile.TemporaryDirectory() as temporary:
        jobs = [(case, rep) for rep in range(reps) for case in cases if (case.id, rep) not in done]
        with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
            list(pool.map(lambda job: one(job[0], job[1], temporary), jobs))
    written, failed = counts["written"], counts["failed"]
    rows = [json.loads(line) for line in results_path.read_text(encoding="utf-8").splitlines()] if results_path.is_file() else []
    for part in ("train", "test"):
        # Reps of one case are correlated, so the interval is over per-case means (n = cases).
        per_case: dict[str, list[int]] = {}
        for row in rows:
            if row["split"] == part:
                per_case.setdefault(row["prompt_id"], []).append(row["grade"]["pass"])
        means = [sum(v) / len(v) for v in per_case.values()]
        if means:
            mean = sum(means) / len(means)
            spread = (sum((m - mean) ** 2 for m in means) / (len(means) - 1)) ** 0.5 if len(means) > 1 else 0.0
            half = 1.96 * spread / len(means) ** 0.5
            print(f"{args.variant} {part}: pass {mean:.3f} +/- {half:.3f} (n={len(means)} cases, {sum(map(len, per_case.values()))} rows)")
    print(f"wrote {written} rows, {failed} errors -> {variant}")
    return 0 if not failed else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    cases = commands.add_parser("cases", help="print every case's visible inputs as markdown for review")
    cases.add_argument("--with-ledger", action="store_true", help="also print grader-only facts, claims and references")
    commands.add_parser("selftest", help="validate the grader with offline adapters")
    init = commands.add_parser("init", help="write _state.json with a fixed, stratified split")
    init.add_argument("--flow-dir", required=True)
    init.add_argument("--seed", type=int, required=True)
    init.add_argument("--test-fraction", type=float, default=0.5)
    init.add_argument("--reps", type=int, default=3)
    run = commands.add_parser("run", help="run one variant and append results")
    run.add_argument("--flow-dir", required=True)
    run.add_argument("--adapter", choices=sorted(ADAPTERS) + ["live"], required=True)
    run.add_argument("--skill", help="live only: variant id from skill-variants/variants.json (`control` = no skill)")
    run.add_argument("--model", default="claude-sonnet-5-5", help="live only: model under test")
    run.add_argument("--timeout-s", type=float, default=900, help="live only: hard wall-clock ceiling per attempt")
    run.add_argument("--max-budget-usd", type=float, default=1.0, help="live only: spend cap per attempt")
    run.add_argument("--cases", help="comma-separated case ids (default: every case in the split)")
    run.add_argument("--jobs", type=int, default=1, help="attempts to run concurrently")
    run.add_argument("--variant", required=True)
    run.add_argument("--reps", type=int, default=None, help="defaults to `reps` in _state.json")
    run.add_argument("--description")
    run.add_argument("--approve-harness", action="store_true", help="record the current harness hash (the user's decision)")
    args = parser.parse_args(argv)
    # Case text is UTF-8; a Windows console or pipe defaults to cp1252 and would crash.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    return {"cases": cmd_cases, "selftest": cmd_selftest, "init": cmd_init, "run": cmd_run}[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
