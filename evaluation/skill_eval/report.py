"""Generate a complete, reproducible markdown report for one or more finished eval flows.

python -m evaluation.skill_eval.report <flow-dir> [<flow-dir> ...] --out docs/evaluation/runs/<name>.md

Run it after every eval run (see docs/evaluation/skill-evals.md). It reports
numbers only, with no interpretation: run metadata, paired comparisons against the
control (overall, train, test), per-family and per-case results, every metric,
failure reasons, cost and tokens, and, for regraded flows, what changed from the
original grades. Write interpretation in a separate narrative report.
"""

import argparse
from collections import Counter
import json
from pathlib import Path
import statistics
import sys

from .compare import load, paired, per_case


METRICS = ("pass", "behavior", "recall", "misplaced", "bad_claims", "preserved", "noise_lines")
FAIL_TESTS = {
    "behavior": lambda g: g["behavior"] == 0,
    "recall": lambda g: g["recall"] < 1,
    "bad_claims": lambda g: g["bad_claims"] > 0,
    "preserved": lambda g: g["preserved"] < 1,
    "noise_lines": None,  # depends on the case budget; resolved from the explanation text
}


def mean(values):
    values = list(values)
    return statistics.mean(values) if values else float("nan")


def fmt(value, digits=3):
    return "—" if value != value else f"{value:.{digits}f}"


def section(flow: Path) -> list[str]:
    arms = load(flow)
    state = json.loads((flow / "_state.json").read_text(encoding="utf-8"))
    rows_all = [row for arm in arms.values() for row in arm["rows"]]
    models = sorted({row["model"] for row in rows_all})
    spend = sum(row.get("cost_usd") or 0 for row in rows_all)
    out = [f"## Flow `{flow.name}`", ""]
    if state.get("regraded_from"):
        out += [f"> **Regraded** from `{state['regraded_from']}` (case set `{state.get('original_case_set_version')}` → `{state['case_set_version']}`).",
                f"> Reason: {state.get('regrade_reason')}", ""]
    out += [
        "| Field | Value |", "| --- | --- |",
        f"| Model(s) | {', '.join(models)} |",
        f"| Arms | {', '.join(f'{a} = `{v['label']}`' for a, v in arms.items())} |",
        f"| Case set | `{state.get('case_set_version')}`, split seed {state.get('split_seed')}: {len(state.get('train_ids', []))} train / {len(state.get('test_ids', []))} test |",
        f"| Attempts scored | {len(rows_all)} |",
        f"| Harness errors | {sum(a['errors'] for a in arms.values())} |",
        f"| Spend (API-equivalent, reported by the CLI) | ${spend:.2f} |",
        f"| Model-reported run time, summed | {sum(row.get('latency_s') or 0 for row in rows_all) / 60:.1f} min |",
        "",
    ]
    control_rows = arms.get("baseline", {}).get("rows", [])
    # Metrics come from the rows: comment-edit and sequence flows record different sets.
    metrics = list(dict.fromkeys(key for row in rows_all for key in row["grade"]))
    secondary = [m for m in metrics if m != "pass"]
    for split in ("all", "train", "test"):
        pick = (lambda rows: rows) if split == "all" else (lambda rows, s=split: [r for r in rows if r.get("split") == s])
        out += [f"### Arms vs control — {split} cases", "",
                "| Arm | Pass | Δpass (95% CI, n cases) | " + " | ".join(secondary) + " |",
                "| --- | ---: | --- |" + " ---: |" * len(secondary)]
        control = {m: per_case(pick(control_rows), m) for m in metrics}
        for name, arm in arms.items():
            scores = {m: per_case(pick(arm["rows"]), m) for m in metrics}
            if name == "baseline" or not control["pass"]:
                delta = "— (control)"
            else:
                d, half, n = paired(scores["pass"], control["pass"])
                delta = f"{d:+.3f} ± {fmt(half)} (n={n})"
            out.append(f"| `{arm['label']}` | {fmt(mean(scores['pass'].values()))} | {delta} | "
                       + " | ".join(fmt(mean(scores[m].values()), 2) for m in secondary) + " |")
        out.append("")

    families = sorted({r["tags"][0] for r in rows_all})
    out += ["### Pass rate by family (all cases)", "", "| Arm | " + " | ".join(families) + " |", "| --- |" + " ---: |" * len(families)]
    for arm in arms.values():
        out.append(f"| `{arm['label']}` | " + " | ".join(
            fmt(mean(per_case([r for r in arm["rows"] if r["tags"][0] == f], "pass").values()), 2) for f in families) + " |")
    out.append("")

    cases = sorted({r["prompt_id"] for r in rows_all})
    labels = [arm["label"] for arm in arms.values()]
    out += ["### Per-case results (passes / attempts)", "",
            "| Case | Split | " + " | ".join(f"`{l}`" for l in labels) + " |", "| --- | --- |" + " ---: |" * len(labels)]
    split_of = {r["prompt_id"]: r.get("split", "") for r in rows_all}
    for case in cases:
        cells = []
        for arm in arms.values():
            rows = [r for r in arm["rows"] if r["prompt_id"] == case]
            cells.append(f"{sum(r['grade']['pass'] for r in rows)}/{len(rows)}" if rows else "—")
        out.append(f"| {case} | {split_of[case]} | " + " | ".join(cells) + " |")
    out.append("")

    if not {"behavior", "recall", "bad_claims", "preserved", "noise_lines"} <= set(metrics):
        out += ["### Cost and effort per attempt (means)", "", "| Arm | Cost | Input tokens (incl. cache) | Output tokens |", "| --- | ---: | ---: | ---: |"]
        for arm in arms.values():
            rows = arm["rows"]
            tokens_in = mean(sum(r["usage"].get(k, 0) for k in ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")) for r in rows)
            out.append(f"| `{arm['label']}` | ${mean(r.get('cost_usd') or 0 for r in rows):.4f} | {tokens_in:,.0f} | {mean(r['usage'].get('output_tokens', 0) for r in rows):,.0f} |")
        out.append("")
        return out
    out += ["### Why attempts failed (counts of failing attempts by failed metric; one attempt can fail several)", "",
            "| Arm | Failing attempts | behavior | recall | bad_claims | preserved | noise over budget |", "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for arm in arms.values():
        reasons, failing = Counter(), 0
        for row in arm["rows"]:
            g = row["grade"]
            if g["pass"]:
                continue
            failing += 1
            for metric, test in FAIL_TESTS.items():
                if test is not None and test(g):
                    reasons[metric] += 1
            if g["behavior"] and g["recall"] == 1 and not g["bad_claims"] and g["preserved"] == 1:
                reasons["noise_lines"] += 1  # the only remaining condition is the noise budget
            elif "budget" in row["explanation"].get("noise_lines", "") and _over_budget(row):
                reasons["noise_lines"] += 1
        out.append(f"| `{arm['label']}` | {failing} | " + " | ".join(str(reasons[m]) for m in ("behavior", "recall", "bad_claims", "preserved", "noise_lines")) + " |")
    out.append("")

    out += ["### Cost and effort per attempt (means)", "",
            "| Arm | Cost | Input tokens (incl. cache) | Output tokens | Tool calls | Turns | Model time (s) |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for arm in arms.values():
        rows = arm["rows"]
        tokens_in = mean(sum(r["usage"].get(k, 0) for k in ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")) for r in rows)
        out.append(f"| `{arm['label']}` | ${mean(r.get('cost_usd') or 0 for r in rows):.4f} | {tokens_in:,.0f} | "
                   f"{mean(r['usage'].get('output_tokens', 0) for r in rows):,.0f} | {fmt(mean(r.get('tool_calls') or 0 for r in rows), 1)} | "
                   f"{fmt(mean(r.get('num_turns') or 0 for r in rows), 1)} | {fmt(mean(r.get('latency_s') or 0 for r in rows), 1)} |")
    out.append("")

    if any(r.get("meta", {}).get("original_grade") for r in rows_all):
        out += ["### Regrade: original vs regraded pass rate (all cases)", "", "| Arm | Original | Regraded | Attempts whose pass changed |", "| --- | ---: | ---: | ---: |"]
        for arm in arms.values():
            rows = arm["rows"]
            original = mean(r["meta"]["original_grade"]["pass"] for r in rows)
            changed = sum(r["meta"]["original_grade"]["pass"] != r["grade"]["pass"] for r in rows)
            out.append(f"| `{arm['label']}` | {fmt(original)} | {fmt(mean(r['grade']['pass'] for r in rows))} | {changed} |")
        out.append("")
    return out


def _over_budget(row) -> bool:
    text = row["explanation"]["noise_lines"]
    try:
        count = int(text.split()[0])
        budget = int(text.split("budget")[1].strip(" )"))
        return count > budget
    except (ValueError, IndexError):
        return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("flows", nargs="+")
    parser.add_argument("--out", required=True)
    parser.add_argument("--title", default="Eval run report")
    args = parser.parse_args(argv)
    lines = [f"# {args.title}", "",
             "Generated by `python -m evaluation.skill_eval.report`. Numbers only; interpretation lives in the narrative reports linked from `docs/evaluation/README.md`.",
             "Δpass is paired against the control on the same cases; the interval is 1.96 × sd / √n over cases.", ""]
    for flow in args.flows:
        lines += section(Path(flow))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines).rstrip("\n") + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {out} ({len(lines)} lines)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
