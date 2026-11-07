"""Downstream sequence eval (#19, stage 1): does maintained context help a fresh reader?

python -m evaluation.skill_eval.sequence list
python -m evaluation.skill_eval.sequence selftest
python -m evaluation.skill_eval.sequence init --flow-dir <dir> --reps 3
python -m evaluation.skill_eval.sequence run --flow-dir <dir> --variant baseline --arm code-only \\
    --writer-model claude-sonnet-5-5 --reader-model claude-haiku-5-5 --jobs 3

Each sequence has two steps:
  1. WRITER: an existing comment-edit case, run under one context-maintenance arm
     (`code-only`, `docs-folder`, or `inline:<variant>`), with the case's evidence
     available under `evidence/`.
  2. HAND-OFF: `evidence/` and the step-1 TASK.md are deleted. Code, comments and any
     docs the arm maintained stay. The reader's TASK.md is written.
  3. READER: a fresh session with no skill and no evidence makes the follow-up change.
     The sequence's hidden checks score it. That is the PRIMARY score (`pass`).

Design and rationale: issue #19, `intent.md` ("The user's fuller theory"), ADR 0001.
Live runs spend money and need the user's approval (`intent.md`).
"""

import argparse
import concurrent.futures
from dataclasses import dataclass
import difflib
import json
from pathlib import Path
import re
import shutil
import sys
import tempfile
import threading

from .adapters import ADAPTERS
from .comments import blocks, normalize
from .grade import Case, GraderError, grade, load_cases, matches, run_check_file, run_checks


ROOT = Path(__file__).resolve().parents[2]
SEQUENCES = Path(__file__).resolve().parent / "sequences"
ARMS = Path(__file__).resolve().parent / "arms"
EVIDENCE = "evidence"
READER_PROMPT = ("Complete the request in TASK.md in the current directory. Do not modify TASK.md. "
                 "If comments or documentation disagree with the code, the code is authoritative.")
HARNESS_PATHS = [
    "evaluation/skill_eval/sequence.py", "evaluation/skill_eval/live.py", "evaluation/skill_eval/grade.py",
    "evaluation/skill_eval/check_runner.py", "evaluation/skill_eval/comments.py",
    "evaluation/skill_eval/arms/docs-folder/project-docs/SKILL.md",
]


@dataclass(frozen=True)
class Sequence:
    root: Path
    spec: dict
    case: Case

    @property
    def id(self) -> str:
        return self.spec["id"]

    @property
    def reader_task(self) -> str:
        return (self.root / "reader" / "TASK.md").read_text(encoding="utf-8")


def load_sequences(root: Path = SEQUENCES) -> list[Sequence]:
    cases = {case.id: case for case in load_cases()}
    found = []
    for spec_path in sorted(root.glob("*/sequence.json")):
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
        if spec["id"] != spec_path.parent.name:
            raise ValueError(f"{spec_path}: id must match directory name")
        if spec["writer_case"] not in cases:
            raise ValueError(f"{spec['id']}: unknown writer_case {spec['writer_case']!r}")
        if spec.get("fact_type") not in ("non-derivable", "local-visible"):
            raise ValueError(f"{spec['id']}: fact_type must be non-derivable or local-visible")
        found.append(Sequence(spec_path.parent, spec, cases[spec["writer_case"]]))
    return found


def arm_skill_dir(arm: str) -> Path | None:
    """`code-only` has no skill; `docs-folder` is the docs practice; `inline:<variant>` a Code Comments variant."""
    if arm == "code-only":
        return None
    if arm == "docs-folder":
        return ARMS / "docs-folder" / "project-docs"
    if arm.startswith("inline:"):
        path = ROOT / "skill-variants" / arm.split(":", 1)[1] / "code-comments"
        if not (path / "SKILL.md").is_file():
            raise ValueError(f"unknown inline variant in arm {arm!r}")
        return path
    raise ValueError(f"unknown arm {arm!r}: use code-only, docs-folder or inline:<variant>")


# --- workspace transforms -------------------------------------------------------


def prepare_writer(sequence: Sequence, destination: Path) -> Path:
    """Copy the case; move its evidence from docs/ to evidence/ so a docs-folder arm can own docs/."""
    workspace = destination / sequence.id
    shutil.copytree(sequence.case.visible, workspace)
    if (workspace / "docs").is_dir():
        (workspace / "docs").rename(workspace / EVIDENCE)
        task = workspace / "TASK.md"
        task.write_text(task.read_text(encoding="utf-8").replace("docs/", f"{EVIDENCE}/"), encoding="utf-8")
    return workspace


def hand_off(sequence: Sequence, workspace: Path) -> None:
    """Remove the step-1 evidence and request; keep code, comments and maintained docs."""
    shutil.rmtree(workspace / EVIDENCE, ignore_errors=True)
    (workspace / "TASK.md").unlink(missing_ok=True)
    (workspace / "TASK.md").write_text(sequence.reader_task, encoding="utf-8")


def apply_tree(source: Path, workspace: Path) -> None:
    for path in source.rglob("*"):
        if path.is_file():
            target = workspace / path.relative_to(source)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)


# --- measurements ---------------------------------------------------------------


def context_texts(workspace: Path) -> list[str]:
    """Explanation anywhere the next reader could find it: code comments and docstrings, and markdown docs."""
    texts = []
    for path in workspace.rglob("*"):
        if not path.is_file() or EVIDENCE in path.relative_to(workspace).parts or path.name == "TASK.md":
            continue
        if path.suffix == ".py":
            try:
                texts += [block.text for block in blocks(path.read_text(encoding="utf-8"))]
            except (SyntaxError, ValueError, UnicodeDecodeError):
                continue
        elif path.suffix == ".md":
            texts += [normalize(part) for part in re.split(r"\n\s*\n", path.read_text(encoding="utf-8", errors="replace")) if part.strip()]
    return texts


def writer_measures(sequence: Sequence, workspace: Path) -> dict:
    spec = sequence.case.spec
    texts = context_texts(workspace)
    facts = spec.get("required_facts", [])
    claims = spec.get("forbidden_claims", [])
    return {
        "writer_behavior": int(not run_checks(sequence.case, workspace)),
        "context_recall": round(sum(any(matches(f["anchors"], t) for t in texts) for f in facts) / len(facts), 4) if facts else 1.0,
        "context_bad_claims": sum(any(matches(c["anchors"], t) for t in texts) for c in claims),
        "inline_recall": grade(sequence.case, workspace)[0]["recall"],
        "docs_files": sum(1 for p in workspace.rglob("*.md") if EVIDENCE not in p.relative_to(workspace).parts and p.name != "TASK.md"),
    }


def reader_measures(trace: list[dict]) -> dict:
    reads = [t["content"] for t in trace if t.get("role") == "tool_call" and t.get("name") == "Read"]
    return {
        "reader_opened_docs": int(any(re.search(r"(docs[/\\\\]|AGENTS\.md)", r) for r in reads)),
        "reader_searches": sum(1 for t in trace if t.get("role") == "tool_call" and t.get("name") in ("Grep", "Glob")),
    }


def workspace_diff(sequence: Sequence, workspace: Path) -> str:
    chunks = []
    names = sorted({p.relative_to(workspace).as_posix() for p in workspace.rglob("*") if p.is_file() and p.suffix in (".py", ".md")} - {"TASK.md"})
    for name in names:
        before_path = sequence.case.visible / name
        before = before_path.read_text(encoding="utf-8").splitlines(keepends=True) if before_path.is_file() else []
        after = (workspace / name).read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
        chunks.extend(difflib.unified_diff(before, after, f"a/{name}", f"b/{name}"))
    return "".join(chunks) or "(no changes)"


# --- one attempt ------------------------------------------------------------------


def attempt(sequence: Sequence, scratch: Path, *, writer: str, reader: str, arm: str = "code-only",
            writer_model: str = "", reader_model: str = "", timeout_s: float = 900, max_budget_usd: float = 1.0) -> dict:
    """writer/reader are `live`, `oracle` or `null`; offline modes exist to validate the plumbing."""
    workspace = prepare_writer(sequence, scratch)
    trace, cost, usage = [], 0.0, {"writer": {}, "reader": {}}
    if writer == "live":
        from . import live
        result = live.run_session(workspace, live.TASK_PROMPT, skill_dir=arm_skill_dir(arm), label=f"writer:{arm}",
                                  model=writer_model, timeout_s=timeout_s, max_budget_usd=max_budget_usd)
        trace += result["trace"]
        cost += result.get("cost_usd") or 0
        usage["writer"] = result["usage"]
    elif writer == "oracle":
        ADAPTERS["oracle"](sequence.case, workspace)
        trace.append({"role": "system", "content": "Offline writer: applied the case reference."})
    elif writer != "null":
        raise ValueError(f"writer mode {writer!r}")
    measures = writer_measures(sequence, workspace)
    hand_off(sequence, workspace)
    trace.append({"role": "system", "content": "--- hand-off: evidence/ and the step-1 TASK.md removed; fresh reader session starts ---"})
    trace.append({"role": "user", "content": sequence.reader_task})
    if reader == "live":
        from . import live
        result = live.run_session(workspace, READER_PROMPT, skill_dir=None, label="reader",
                                  model=reader_model, timeout_s=timeout_s, max_budget_usd=max_budget_usd)
        trace += result["trace"]
        cost += result.get("cost_usd") or 0
        usage["reader"] = result["usage"]
    elif reader == "oracle":
        apply_tree(sequence.root / "private" / "reference", workspace)
    elif reader != "null":
        raise ValueError(f"reader mode {reader!r}")
    failures = run_check_file(sequence.root / "private" / "checks.py", workspace, sequence.id)
    measures.update(reader_measures(trace))
    scores = {"pass": int(not failures), **measures}
    explanation = {"pass": "; ".join(failures[:8]) or "ok"}
    trace.append({"role": "assistant", "content": f"Final workspace diff against the case's original files:\n\n```diff\n{workspace_diff(sequence, workspace)}```"})
    return {"scores": scores, "explanation": explanation, "trace": trace, "cost_usd": round(cost, 6), "usage": usage}


# --- commands -----------------------------------------------------------------------


def cmd_list(_: argparse.Namespace) -> int:
    for sequence in load_sequences():
        print(f"{sequence.id}: {sequence.spec['fact_type']}, writer case {sequence.case.id}; {sequence.spec['summary']}")
    return 0


def validity_problems(sequence: Sequence) -> list[str]:
    problems = []
    task = normalize(sequence.reader_task)
    facts = {f["id"]: f for f in sequence.case.spec.get("required_facts", [])}
    for fact_id in sequence.spec.get("depends_on", []):
        if fact_id not in facts:
            problems.append(f"depends_on names unknown fact {fact_id!r}")
        elif matches(facts[fact_id]["anchors"], task):
            problems.append(f"reader TASK.md leaks fact {fact_id!r} (the reader must not be told it)")
    for required in ("reader/TASK.md", "private/checks.py", "private/reference"):
        if not (sequence.root / required).exists():
            problems.append(f"missing {required}")
    return problems


def cmd_selftest(_: argparse.Namespace) -> int:
    problems: list[str] = []
    sequences = load_sequences()
    with tempfile.TemporaryDirectory() as temporary:
        for sequence in sequences:
            problems += [f"{sequence.id}: {p}" for p in validity_problems(sequence)]
            for writer, reader, expected in (("oracle", "oracle", 1), ("oracle", "null", 0), ("null", "null", 0)):
                try:
                    result = attempt(sequence, Path(temporary) / f"{writer}-{reader}", writer=writer, reader=reader)
                except GraderError as error:
                    problems.append(f"{sequence.id} [{writer}/{reader}]: grader error {error}")
                    continue
                if result["scores"]["pass"] != expected:
                    problems.append(f"{sequence.id} [{writer}/{reader}]: expected pass={expected}, got {result['scores']} ({result['explanation']})")
            # The reader's reference must keep the step-1 behaviour (no regressions allowed).
            workspace = prepare_writer(sequence, Path(temporary) / "regression")
            ADAPTERS["oracle"](sequence.case, workspace)
            apply_tree(sequence.root / "private" / "reference", workspace)
            if run_checks(sequence.case, workspace):
                problems.append(f"{sequence.id}: reader reference breaks the step-1 checks")
    print(json.dumps({"kind": "sequence_selftest", "model_calls": 0, "sequences": len(sequences),
                      "fact_types": {t: sum(s.spec["fact_type"] == t for s in sequences) for t in ("non-derivable", "local-visible")},
                      "passed": not problems, "problems": problems}, indent=2))
    return 0 if not problems else 1


def cmd_init(args: argparse.Namespace) -> int:
    from .run import harness_sha
    flow = Path(args.flow_dir)
    if (flow / "_state.json").exists():
        print(f"{flow / '_state.json'} exists; delete it deliberately to restart", file=sys.stderr)
        return 1
    flow.mkdir(parents=True, exist_ok=True)
    ids = [s.id for s in load_sequences()]
    state = {"flow": "sequence", "reps": args.reps, "train_ids": ids, "test_ids": [],
             "note": "Stage-1 pilot: descriptive, no train/test split (#19).",
             "harness_paths": HARNESS_PATHS,
             "metrics": [{"id": "pass", "kind": "binary", "label": "Reader pass"},
                         {"id": "writer_behavior", "kind": "binary", "label": "Writer ok"},
                         {"id": "context_recall", "kind": "float", "label": "Facts kept"},
                         {"id": "context_bad_claims", "kind": "float", "better": "lower", "label": "Stale claims"},
                         {"id": "reader_opened_docs", "kind": "binary", "label": "Read docs"}],
             "perf_fields": [{"id": "cost_usd", "label": "Cost", "unit": "$"}]}
    (flow / "_state.json").write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {flow / '_state.json'} with {len(ids)} sequences")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    from .run import harness_sha
    flow = Path(args.flow_dir)
    state = json.loads((flow / "_state.json").read_text(encoding="utf-8"))
    if not re.fullmatch(r"baseline|v[1-9][0-9]*", args.variant):
        print("variant must be `baseline` or v<N>", file=sys.stderr)
        return 1
    live_mode = args.writer == "live" or args.reader == "live"
    current = harness_sha(state["harness_paths"])
    if args.approve_harness:
        state["harness_sha"] = current
        (flow / "_state.json").write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    elif live_mode and state.get("harness_sha") != current:
        print("harness changed or never approved; re-run with --approve-harness (the user's decision)", file=sys.stderr)
        return 2
    arm_skill_dir(args.arm)  # validate early
    label = f"{args.arm}|w:{args.writer}:{args.writer_model}|r:{args.reader}:{args.reader_model}"
    variant = flow / args.variant
    (variant / "traces").mkdir(parents=True, exist_ok=True)
    results_path, errors_path = variant / "results.jsonl", variant / "errors.jsonl"
    done = set()
    if results_path.is_file():
        for line in results_path.read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            if row["meta"]["adapter"] != label:
                print(f"{variant} holds rows for {row['meta']['adapter']!r}; use a new variant", file=sys.stderr)
                return 1
            done.add((row["prompt_id"], row["rep"]))
    (variant / "summary.json").write_text(json.dumps({"description": f"arm {args.arm}; writer {args.writer_model or args.writer}; reader {args.reader_model or args.reader}",
                                                      "label": args.arm, "target": "skill"}, indent=2) + "\n", encoding="utf-8")
    if args.variant != "baseline":
        (variant / "change.md").write_text(f"Context arm `{args.arm}` (writer {args.writer_model or args.writer}, reader {args.reader_model or args.reader}).\n", encoding="utf-8")
    wanted = set(args.sequences.split(",")) if args.sequences else None
    sequences = [s for s in load_sequences() if s.id in state["train_ids"] + state["test_ids"] and (not wanted or s.id in wanted)]
    lock, counts = threading.Lock(), {"written": 0, "failed": 0}

    def one(sequence: Sequence, rep: int, temporary: str) -> None:
        try:
            result = attempt(sequence, Path(temporary) / f"rep{rep}", writer=args.writer, reader=args.reader, arm=args.arm,
                             writer_model=args.writer_model, reader_model=args.reader_model,
                             timeout_s=args.timeout_s, max_budget_usd=args.max_budget_usd)
        except Exception as error:  # never abort the run; never score plumbing as a model failure
            entry = {"prompt_id": sequence.id, "rep": rep, "failure_class": getattr(error, "failure_class", "harness_exception"),
                     "error": f"{type(error).__name__}: {error}", "retries": 0}
            with lock:
                counts["failed"] += 1
                with errors_path.open("a", encoding="utf-8") as errors:
                    errors.write(json.dumps(entry) + "\n")
            return
        row = {"prompt_id": sequence.id, "rep": rep, "prompt": sequence.reader_task,
               "tags": [sequence.spec["fact_type"], sequence.case.family, sequence.case.id],
               "split": "train", "status": "ok", "grade": result["scores"], "explanation": result["explanation"],
               "model": args.reader_model or f"offline:{args.reader}", "cost_usd": result["cost_usd"],
               "usage": {k: result["usage"]["writer"].get(k, 0) + result["usage"]["reader"].get(k, 0)
                         for k in ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")},
               "meta": {"adapter": label, "arm": args.arm, "writer_model": args.writer_model, "reader_model": args.reader_model,
                        "writer_usage": result["usage"]["writer"], "reader_usage": result["usage"]["reader"]}}
        with lock:
            (variant / "traces" / f"{sequence.id}_rep{rep}.json").write_text(json.dumps(result["trace"], indent=2) + "\n", encoding="utf-8")
            with results_path.open("a", encoding="utf-8") as results:
                results.write(json.dumps(row) + "\n")
            counts["written"] += 1
            print(f"  {sequence.id} rep{rep}: reader pass={row['grade']['pass']} cost={row['cost_usd']}", flush=True)

    with tempfile.TemporaryDirectory() as temporary:
        jobs = [(s, rep) for rep in range(args.reps or state["reps"]) for s in sequences if (s.id, rep) not in done]
        with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
            list(pool.map(lambda job: one(job[0], job[1], temporary), jobs))
    print(f"wrote {counts['written']} rows, {counts['failed']} errors -> {variant}")
    return 0 if not counts["failed"] else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list")
    commands.add_parser("selftest")
    init = commands.add_parser("init")
    init.add_argument("--flow-dir", required=True)
    init.add_argument("--reps", type=int, default=3)
    run = commands.add_parser("run")
    run.add_argument("--flow-dir", required=True)
    run.add_argument("--variant", required=True)
    run.add_argument("--arm", default="code-only", help="code-only | docs-folder | inline:<variant>")
    run.add_argument("--writer", choices=("live", "oracle", "null"), default="live")
    run.add_argument("--reader", choices=("live", "oracle", "null"), default="live")
    run.add_argument("--writer-model", default="")
    run.add_argument("--reader-model", default="")
    run.add_argument("--reps", type=int)
    run.add_argument("--jobs", type=int, default=1)
    run.add_argument("--sequences", help="comma-separated sequence ids")
    run.add_argument("--timeout-s", type=float, default=900)
    run.add_argument("--max-budget-usd", type=float, default=1.0)
    run.add_argument("--approve-harness", action="store_true")
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    return {"list": cmd_list, "selftest": cmd_selftest, "init": cmd_init, "run": cmd_run}[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
