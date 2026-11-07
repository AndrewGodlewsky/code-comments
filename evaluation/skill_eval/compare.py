"""Compare tournament arms against the control with paired, case-clustered intervals.

python -m evaluation.skill_eval.compare <flow-dir> [--split train|test|all] [--markdown]

Implements the winner rule in docs/skill/design.md. For each arm and each case,
average the reps; subtract the control's average on the same case; report the mean
difference over cases with a 95% interval (1.96 x sd / sqrt(n_cases)). Pairing
removes case difficulty, and using cases as the unit respects correlated reps.
Guardrails (behavior, bad_claims, noise_lines) get the same paired treatment.
"""

import argparse
import json
from pathlib import Path
import re
import statistics
import sys


METRICS = ("pass", "behavior", "recall", "bad_claims", "noise_lines")


def load(flow: Path) -> dict[str, dict]:
    arms = {}
    for directory in sorted(flow.iterdir()):
        if not (directory.is_dir() and re.fullmatch(r"baseline|v\d+", directory.name)):
            continue
        if not (directory / "results.jsonl").is_file():
            continue  # an arm that has not produced rows yet
        rows = [json.loads(line) for line in (directory / "results.jsonl").read_text(encoding="utf-8").splitlines()]
        errors = (directory / "errors.jsonl").read_text(encoding="utf-8").splitlines() if (directory / "errors.jsonl").is_file() else []
        summary = json.loads((directory / "summary.json").read_text(encoding="utf-8"))
        arms[directory.name] = {"label": summary.get("label", directory.name), "rows": rows, "errors": len(errors)}
    return arms


def per_case(rows: list[dict], metric: str) -> dict[str, float]:
    grouped: dict[str, list[float]] = {}
    for row in rows:
        if row.get("status", "ok") == "ok":
            grouped.setdefault(row["prompt_id"], []).append(float(row["grade"][metric]))
    return {case: sum(values) / len(values) for case, values in grouped.items()}


def paired(arm: dict[str, float], control: dict[str, float]) -> tuple[float, float, int]:
    diffs = [arm[case] - control[case] for case in arm if case in control]
    if not diffs:
        return float("nan"), float("nan"), 0
    half = 1.96 * statistics.stdev(diffs) / len(diffs) ** 0.5 if len(diffs) > 1 else float("nan")
    return statistics.mean(diffs), half, len(diffs)


def table(flow: Path, split: str) -> str:
    arms = load(flow)
    if "baseline" not in arms:
        raise SystemExit("no baseline (control) arm")

    def pick(rows):
        return [r for r in rows if split == "all" or r.get("split") == split]

    control = {m: per_case(pick(arms["baseline"]["rows"]), m) for m in METRICS}
    lines = [f"### {flow.name} — split: {split}", "",
             "| arm | pass | Δpass vs control (95% CI) | Δbehavior | Δbad_claims | Δnoise_lines | cost/attempt | errors |",
             "| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: |"]
    for name, arm in arms.items():
        rows = pick(arm["rows"])
        scores = {m: per_case(rows, m) for m in METRICS}
        mean_pass = statistics.mean(scores["pass"].values()) if scores["pass"] else float("nan")
        costs = [r["cost_usd"] for r in rows if r.get("cost_usd") is not None]
        cost = f"${statistics.mean(costs):.4f}" if costs else "—"
        if name == "baseline":
            label = arm["label"] if arm["label"] == "control" else f"{arm['label']} (control)"
            lines.append(f"| {label} | {mean_pass:.3f} | — | — | — | — | {cost} | {arm['errors']} |")
            continue
        cells = []
        for metric in ("pass", "behavior", "bad_claims", "noise_lines"):
            diff, half, n = paired(scores[metric], control[metric])
            cells.append(f"{diff:+.3f} ± {half:.3f} (n={n})" if metric == "pass" else f"{diff:+.2f}")
        lines.append(f"| {arm['label']} | {mean_pass:.3f} | " + " | ".join(cells) + f" | {cost} | {arm['errors']} |")

    families = sorted({r["tags"][0] for arm in arms.values() for r in arm["rows"]})
    lines += ["", "Pass rate by family (mean over cases of the per-case rep average):", "",
              "| arm | " + " | ".join(families) + " |", "| --- |" + " ---: |" * len(families)]
    for name, arm in arms.items():
        cells = []
        for family in families:
            values = list(per_case([r for r in pick(arm["rows"]) if r["tags"][0] == family], "pass").values())
            cells.append(f"{statistics.mean(values):.2f}" if values else "—")
        lines.append(f"| {arm['label']} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("flow_dir")
    parser.add_argument("--split", choices=("train", "test", "all"), default="all")
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print(table(Path(args.flow_dir), args.split))
    return 0


if __name__ == "__main__":
    sys.exit(main())
