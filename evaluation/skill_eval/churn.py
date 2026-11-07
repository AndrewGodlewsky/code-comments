"""Measure unnecessary code churn: real code changes beyond the minimal reference change.

python -m evaluation.skill_eval.churn <flow-dir> [<flow-dir> ...] [--threshold 3]

For every graded attempt, the end state is rebuilt from its trace diff. Comments,
docstrings and formatting are removed (AST round-trip), and the changed lines are
counted against the case's visible files. The case reference gets the same count.
"Excess" is attempt minus reference. A large excess means the agent rewrote more
code than the task needed, which is a per-edit proxy for the "tangled codebase over
time" concern. Read it as a proxy: some excess is legitimate refactoring.
"""

import argparse
import ast
import difflib
import json
from pathlib import Path
import re
import statistics
import sys
import tempfile

from .grade import load_cases
from .regrade import rebuild


def normalized_lines(source: str) -> list[str] | None:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and node.body:
            first = node.body[0]
            if isinstance(first, ast.Expr) and isinstance(getattr(first, "value", None), ast.Constant) and isinstance(first.value.value, str):
                node.body = node.body[1:] or [ast.Pass()]
    return ast.unparse(tree).splitlines()


def code_churn(before: Path, after: Path, files: list[str]) -> int | None:
    total = 0
    for name in files:
        old = (before / name).read_text(encoding="utf-8") if (before / name).is_file() else ""
        new = (after / name).read_text(encoding="utf-8") if (after / name).is_file() else ""
        old_lines, new_lines = normalized_lines(old) or [], normalized_lines(new)
        if new_lines is None:
            return None  # the attempt left a file that does not parse
        total += sum(1 for line in difflib.unified_diff(old_lines, new_lines, lineterm="")
                     if line[:1] in "+-" and not line.startswith(("+++", "---")))
    return total


def measure(flow: Path, threshold: int) -> list[dict]:
    cases = {case.id: case for case in load_cases()}
    reference = {cid: code_churn(c.visible, c.private / "reference", c.spec["files"]) for cid, c in cases.items()}
    rows_out = []
    with tempfile.TemporaryDirectory() as temporary:
        for variant in sorted(p for p in flow.iterdir() if p.is_dir() and re.fullmatch(r"baseline|v\d+", p.name)):
            label = json.loads((variant / "summary.json").read_text(encoding="utf-8")).get("label", variant.name)
            excess, big, passes = [], 0, []
            for index, line in enumerate((variant / "results.jsonl").read_text(encoding="utf-8").splitlines()):
                row = json.loads(line)
                case = cases.get(row["prompt_id"])
                if case is None:
                    continue
                trace = json.loads((variant / "traces" / f"{row['prompt_id']}_rep{row['rep']}.json").read_text(encoding="utf-8"))
                workspace = rebuild(case, trace, Path(temporary) / variant.name / str(index))
                churn = code_churn(case.visible, workspace, case.spec["files"])
                if churn is None:
                    continue
                excess.append(churn - reference[case.id])
                big += (churn - reference[case.id]) >= threshold
                passes.append(row["grade"]["pass"])
            rows_out.append({"flow": flow.name, "arm": label, "attempts": len(excess),
                             "pass": statistics.mean(passes) if passes else float("nan"),
                             "mean_excess": statistics.mean(excess) if excess else float("nan"), "big_excess": big})
    return rows_out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("flows", nargs="+")
    parser.add_argument("--threshold", type=int, default=3)
    args = parser.parse_args(argv)
    print(f"| Flow | Arm | Pass | Mean excess code lines | Attempts with >= {args.threshold} excess |")
    print("| --- | --- | ---: | ---: | ---: |")
    for flow in args.flows:
        for row in measure(Path(flow), args.threshold):
            print(f"| {row['flow']} | `{row['arm']}` | {row['pass']:.2f} | {row['mean_excess']:+.2f} | {row['big_excess']}/{row['attempts']} |")
    return 0


if __name__ == "__main__":
    sys.exit(main())
