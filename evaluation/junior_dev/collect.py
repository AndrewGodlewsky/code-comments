"""Write a finished tournament batch's runs into an iteration directory (#52).

    python -m evaluation.junior_dev.collect <workflow-output.json> <iteration-dir>

Each run lands in <iteration>/<case>/<arm>/<author>/<mode>/run-<rep>/. A run directory that
already exists is never overwritten: results are evidence.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

from . import mermaid


def _dump(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def _report(run: dict) -> str:
    lines = [f"## Review of {run['case']} ({run['arm']}, author {run['author']}, {run['mode']})", "",
             f"Rounds: {run.get('rounds', 0)}. Ended: {run.get('end_reason')}.", "", "### What changed"]
    lines += [f"- {c}" for c in run.get("changes", [])] or ["- Nothing was changed."]
    lines += ["", "### Holes"] + ([f"- {h}" for h in run.get("holes", [])] or ["- None."])
    return "\n".join(lines) + "\n"


def collect(output_file: Path, iteration_dir: Path) -> list[Path]:
    data = json.loads(Path(output_file).read_text(encoding="utf-8"))
    result = data.get("result", data)
    runs = result.get("runs", [])
    iteration_dir = Path(iteration_dir)
    targets = []
    for run in runs:
        if not run:
            continue
        target = iteration_dir / run["case"] / run["arm"] / run["author"] / run["mode"] / f"run-{run['rep']}"
        if target.exists():
            raise FileExistsError(f"refusing to overwrite {target}")
        targets.append((run, target))
    finals = [run.get("artifact_final") or "" for run, _ in targets]
    diagram_errors = mermaid.check_many(finals)
    written = []
    for (run, target), errors in zip(targets, diagram_errors):
        target.mkdir(parents=True)
        (target / "artifact-initial.md").write_text(run.get("artifact_initial") or "", encoding="utf-8", newline="\n")
        (target / "artifact-final.md").write_text(run.get("artifact_final") or "", encoding="utf-8", newline="\n")
        _dump(target / "transcript.json", {"transcript": run.get("transcript", []), "teachbacks": run.get("teachbacks", []),
                                           "rounds": run.get("rounds", 0), "end_reason": run.get("end_reason")})
        (target / "report.md").write_text(_report(run), encoding="utf-8", newline="\n")
        _dump(target / "author-key.json", run.get("author_key", {}))
        _dump(target / "readers.json", run.get("reader_answers", {}))
        _dump(target / "grades.json", {"grades": run.get("grades", {}), "by_model": run.get("grades_by_model", {}),
                                       "excluded": run.get("excluded", [])})
        _dump(target / "checks.json", {"requirements": run.get("requirements", []), "honesty": run.get("honesty", []),
                                       "mermaid_errors": errors})
        _dump(target / "usage.json", run.get("usage", {}))
        _dump(target / "run.json", {k: run.get(k) for k in ("run_id", "case", "arm", "author", "rep", "mode", "label",
                                                              "skill_rev", "errors", "changes", "holes")})
        written.append(target)
    missing = sum(1 for r in runs if not r)
    if missing:
        iteration_dir.mkdir(parents=True, exist_ok=True)
        with (iteration_dir / "missing-runs.log").open("a", encoding="utf-8") as f:
            f.write(f"{result.get('label')}: {missing} runs returned nothing\n")
    return written


def collect_judge_runner(output_file: Path, iteration_dir: Path) -> list[Path]:
    """Store every batch of a judge-runner workflow (children run under one shared concurrency cap).

    Refuses the whole output, writing nothing, if any judgment has no winner: a failed call (a usage cap,
    say) is re-run by resuming the runner, never collected as missing."""
    data = json.loads(Path(output_file).read_text(encoding="utf-8"))
    batches = data.get("result", data)["batches"]
    failed = [(b or {}).get("label") for b in batches if not b or any(not j or not j.get("winner") for j in b["judgments"])]
    if failed:
        raise ValueError(f"batches with failed calls, resume the runner first: {failed}")
    return [collect_judgments(output_file, iteration_dir, result=b) for b in batches]


def collect_judgments(output_file: Path, iteration_dir: Path, result: dict | None = None) -> Path:
    """Store a judge batch's judgments under <iteration>/judgments/<label>.json (never overwritten)."""
    if result is None:
        data = json.loads(Path(output_file).read_text(encoding="utf-8"))
        result = data.get("result", data)
    target = Path(iteration_dir) / "judgments" / f"{result['label']}.json"
    if target.exists():
        raise FileExistsError(f"refusing to overwrite {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    _dump(target, [j for j in result["judgments"] if j])
    return target


if __name__ == "__main__":
    paths = collect(Path(sys.argv[1]), Path(sys.argv[2]))
    print(f"wrote {len(paths)} runs")
