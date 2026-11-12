"""Score code-comments-v5 iterations by case group, for the hill-climb's selection rule
and gates (see ../README.md).

    python incubator/code-comments-v5/eval/score.py ITERATION [ITERATION ...] [--arm ARM ...]

Reads ``iterations/ITERATION/<case>/<arm>/run-*/grading.json``, as ``harness.py grade``
writes it, and skips ``excluded-runs/`` and ``skill-snapshot/``. ITERATION is a folder
name under ``iterations/`` or a path to one. Several iterations are pooled, as gate G2
pools Haiku and Sonnet. ``--arm`` keeps only the arms named.

Prints one JSON object per arm, one per line:
- ``groups``: for train, screen, hygiene and heldout, two sets of figures, ``all`` (every
  check) and ``core`` (checks whose focus is core). Each gives the checks passed and
  their total, pooled over runs, the number of runs, and the mean of each run's pass
  rate. A run with no core check is left out of the core figures.
- ``per_case``: for each case the arm ran, the checks passed and their total over its
  runs, the core checks passed and their total (``core_passed``, ``core_total``), the
  number of runs, and ``full_mark_runs``, the runs that passed every check.
- ``ungraded_runs``: run folders with no grading.json.

The train, screen and hygiene groups are the fixed lists below. Screen cases are also
hygiene cases. The heldout group is every case whose case.yaml says ``held_out: true``.
Standard library only.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ITERATIONS = HERE / "iterations"
CASES = HERE / "cases"

TRAIN = ("request-quotes-stale-docstring", "request-quotes-true-docstring", "stale-cents-comment",
         "true-cents-comment", "docs-sync-keeps-requirements", "positional-columns-in-sql",
         "positional-columns-in-sql-pointer", "sort-relied-on-elsewhere", "stale-constraint-elsewhere",
         "dispatched-by-name")
SCREEN = ("no-invented-reason", "issue-pointer-beside-reason", "change-contradicts-comment",
          "reason-only-in-test", "capture-supported-reason")
HYGIENE = ("capture-supported-reason", "change-contradicts-comment", "clause-goes-stale", "comment-only-preserve",
           "issue-pointer-beside-reason", "no-invented-reason", "no-issue-tag-routine", "reason-only-in-test",
           "rename-stale-refs", "retry-cap-elsewhere", "routine-edit-no-noise")
GROUPS = ("train", "screen", "hygiene", "heldout")
ARMS = ("with_skill", "shipped_skill", "reminder", "without_skill")
SKIP = {"excluded-runs", "skill-snapshot"}
RUN = re.compile(r"run-(\d+)")


def held_out(cases: Path, case: str) -> bool:
    """``held_out: true`` (or yes) in the case's case.yaml, read as harness.py reads it."""
    path = cases / case / "case.yaml"
    if not path.is_file():
        return False
    match = re.search(r"^held_out:\s*([^\s#]+)", path.read_text(encoding="utf-8"), re.M)
    if match is None:
        return False
    value = match.group(1).lower()
    if value not in ("true", "yes", "false", "no"):
        raise SystemExit(f"{path}: held_out must be true or false, got {match.group(1)!r}")
    return value in ("true", "yes")


def resolve(name: str) -> Path:
    for path in (ITERATIONS / name, Path(name)):
        if path.is_dir():
            return path
    raise SystemExit(f"no iteration {name!r} under {ITERATIONS} and no such folder")


def label(iteration: Path) -> str:
    """The iteration's name under iterations/, or the path as given for one elsewhere."""
    try:
        return iteration.resolve().relative_to(ITERATIONS.resolve()).as_posix()
    except ValueError:
        return iteration.as_posix()


def read_runs(iteration: Path):
    """Yield (case, arm, run folder, grading or None) for every run-K folder."""
    for case_dir in sorted(p for p in iteration.iterdir() if p.is_dir() and p.name not in SKIP):
        for arm_dir in sorted(p for p in case_dir.iterdir() if p.is_dir()):
            runs = [p for p in arm_dir.iterdir() if p.is_dir() and RUN.fullmatch(p.name)]
            for run in sorted(runs, key=lambda p: int(RUN.fullmatch(p.name).group(1))):
                path = run / "grading.json"
                grading = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None
                yield case_dir.name, arm_dir.name, run, grading


def _counts(grading: dict, where: Path) -> dict:
    items = grading.get("expectations")
    if not isinstance(items, list):
        raise SystemExit(f"{where}: grading.json has no expectations list")
    core = [e for e in items if e.get("focus", "core") == "core"]
    return {"passed": sum(bool(e["passed"]) for e in items), "total": len(items),
            "core_passed": sum(bool(e["passed"]) for e in core), "core_total": len(core)}


def _figures(pairs: list[tuple[int, int]]) -> dict:
    rated = [(p, t) for p, t in pairs if t]
    rates = [p / t for p, t in rated]
    return {"passed": sum(p for p, _ in rated), "total": sum(t for _, t in rated), "runs": len(rated),
            "mean_pass_rate": round(sum(rates) / len(rates), 4) if rates else None}


def score(iterations: list[Path], cases: Path = CASES, arms: list[str] | None = None) -> list[dict]:
    rows, ungraded = [], {}
    for iteration in iterations:
        for case, arm, run, grading in read_runs(iteration):
            if arms and arm not in arms:
                continue
            if grading is None:
                ungraded[arm] = ungraded.get(arm, 0) + 1
                continue
            rows.append({"case": case, "arm": arm, **_counts(grading, run)})
    held = {case for case in {r["case"] for r in rows} if held_out(cases, case)}
    members = {"train": set(TRAIN), "screen": set(SCREEN), "hygiene": set(HYGIENE), "heldout": held}
    found = {r["arm"] for r in rows} | set(ungraded)
    order = [a for a in ARMS if a in found] + sorted(found - set(ARMS))
    if arms:
        order = list(dict.fromkeys(arms))
    results = []
    for arm in order:
        mine = [r for r in rows if r["arm"] == arm]
        groups = {}
        for group in GROUPS:
            inside = [r for r in mine if r["case"] in members[group]]
            groups[group] = {"all": _figures([(r["passed"], r["total"]) for r in inside]),
                             "core": _figures([(r["core_passed"], r["core_total"]) for r in inside])}
        per_case = {}
        for case in sorted({r["case"] for r in mine}):
            runs = [r for r in mine if r["case"] == case]
            per_case[case] = {"passed": sum(r["passed"] for r in runs), "total": sum(r["total"] for r in runs),
                              "core_passed": sum(r["core_passed"] for r in runs),
                              "core_total": sum(r["core_total"] for r in runs),
                              "runs": len(runs),
                              "full_mark_runs": sum(r["passed"] == r["total"] for r in runs)}
        results.append({"arm": arm, "iterations": [label(p) for p in iterations], "groups": groups,
                        "per_case": per_case, "ungraded_runs": ungraded.get(arm, 0)})
    return results


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("iterations", nargs="+", help="iteration names under iterations/, or paths")
    parser.add_argument("--arm", action="extend", nargs="+", default=None, help="arms to report")
    parser.add_argument("--cases", type=Path, default=CASES, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    for result in score([resolve(name) for name in args.iterations], args.cases, args.arm):
        print(json.dumps(result, sort_keys=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
