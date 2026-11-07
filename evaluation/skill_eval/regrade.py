"""Regrade a finished flow offline after a grader or case fix, with no model calls.

python -m evaluation.skill_eval.regrade <flow-dir> --reason "<why>" [--out <dir>]

Workspaces are deleted after grading, but each trace's final turn holds the unified
diff of the graded files. This rebuilds every end state as `visible/` plus that diff,
grades it with the current grader and cases, and writes a separate flow
(`<flow>-regraded` by default). The raw flow is never modified. Each row keeps its
original grade in `meta.original_grade`, so a report can show both numbers. A grader
change made after seeing results must be reported as such; see docs/skill/design.md.

Limitation: files outside the case's graded `files` are not in the diff. If an agent
created a helper module that a graded file imports, behaviour can differ after the
rebuild. Changed `behavior` values are listed in the output for that reason.
"""

import argparse
import json
from pathlib import Path
import re
import shutil
import sys
import tempfile

from .grade import grade, load_cases
from .run import case_set_version


HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


def split_diff(text: str) -> dict[str, list[str]]:
    files: dict[str, list[str]] = {}
    current = None
    for line in text.splitlines(keepends=True):
        if line.startswith("--- a/"):
            current = None  # header of the next file; its "+++ b/" line follows
        elif line.startswith("+++ b/"):
            current = line[6:].strip()
            files[current] = []
        elif current is not None:
            files[current].append(line)
    return files


def apply(original: str, hunk_lines: list[str]) -> str:
    old = original.splitlines(keepends=True)
    out: list[str] = []
    position = 0
    index = 0
    while index < len(hunk_lines):
        match = HUNK.match(hunk_lines[index])
        if not match:
            index += 1
            continue
        start = int(match[1]) - (0 if match[2] == "0" else 1)
        out.extend(old[position:start])
        position = start
        index += 1
        while index < len(hunk_lines) and not hunk_lines[index].startswith("@@"):
            line = hunk_lines[index]
            tag, body = line[:1], line[1:]
            if tag in (" ", "-"):
                if position >= len(old) or old[position].rstrip("\r\n") != body.rstrip("\r\n"):
                    raise ValueError(f"hunk does not apply at line {position + 1}: {body!r}")
                if tag == " ":
                    out.append(old[position])
                position += 1
            elif tag == "+":
                out.append(body if body.endswith("\n") else body + "\n")
            index += 1
    out.extend(old[position:])
    return "".join(out)


def rebuild(case, trace: list[dict], destination: Path) -> Path:
    workspace = destination / case.id
    shutil.copytree(case.visible, workspace)
    final = trace[-1]["content"]
    fenced = final[final.find("```diff\n") + len("```diff\n"): final.rfind("```")]
    if fenced.strip() == "(no changes)":
        return workspace
    for name, hunks in split_diff(fenced).items():
        path = workspace / name
        before = path.read_text(encoding="utf-8") if path.is_file() else ""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(apply(before, hunks), encoding="utf-8", newline="\n")
    return workspace


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("flow_dir")
    parser.add_argument("--reason", required=True, help="why the flow is being regraded (recorded in _state.json)")
    parser.add_argument("--out")
    args = parser.parse_args(argv)
    source = Path(args.flow_dir)
    target = Path(args.out) if args.out else source.with_name(source.name + "-regraded")
    if target.exists():
        print(f"{target} exists; remove it deliberately first", file=sys.stderr)
        return 1
    cases = {case.id: case for case in load_cases()}
    state = json.loads((source / "_state.json").read_text(encoding="utf-8"))
    target.mkdir(parents=True)
    state.update(regraded_from=source.name, regrade_reason=args.reason,
                 original_case_set_version=state.get("case_set_version"), case_set_version=case_set_version())
    state.pop("harness_sha", None)
    (target / "_state.json").write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    changed: dict[str, int] = {}
    failures = 0
    with tempfile.TemporaryDirectory() as temporary:
        for variant in sorted(p for p in source.iterdir() if p.is_dir() and re.fullmatch(r"baseline|v\d+", p.name)):
            out = target / variant.name
            shutil.copytree(variant, out, ignore=shutil.ignore_patterns("results.jsonl"))
            rows = []
            for line in (variant / "results.jsonl").read_text(encoding="utf-8").splitlines():
                row = json.loads(line)
                trace = json.loads((variant / "traces" / f"{row['prompt_id']}_rep{row['rep']}.json").read_text(encoding="utf-8"))
                try:
                    workspace = rebuild(cases[row["prompt_id"]], trace, Path(temporary) / variant.name / f"rep{row['rep']}")
                    scores, explanation = grade(cases[row["prompt_id"]], workspace)
                except Exception as error:
                    failures += 1
                    print(f"cannot regrade {variant.name}/{row['prompt_id']} rep{row['rep']}: {error}", file=sys.stderr)
                    continue
                for metric, value in scores.items():
                    if row["grade"].get(metric) != value:
                        changed[metric] = changed.get(metric, 0) + 1
                        if metric == "behavior":
                            print(f"behavior changed: {variant.name}/{row['prompt_id']} rep{row['rep']}", file=sys.stderr)
                row["meta"] = {**row.get("meta", {}), "original_grade": row["grade"], "regraded": True}
                row["grade"], row["explanation"] = scores, explanation
                rows.append(json.dumps(row))
            (out / "results.jsonl").write_text("".join(f"{r}\n" for r in rows), encoding="utf-8")
    print(json.dumps({"regraded_flow": str(target), "changed_metric_counts": changed, "unregradable_rows": failures}))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
