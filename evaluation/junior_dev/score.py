"""Score a Junior-dev iteration and apply the user's decision rule (#52).

    python -m evaluation.junior_dev.score <iteration-dir>   # writes summary.json and summary.md

Comprehension of a run is the share of quiz items the readers answered correctly from the
final artifact alone, averaged over readers. Items the author marked as never decided are
left out of that run (their share is reported separately). Arms are compared within each
case, and the 95% interval is bootstrapped over cases (seed 52, 2000 resamples), because
cases, not runs, are the independent units.

The decision rule is the user's, revised on 2026-11-13 (docs/junior-dev/design.md, "Decided by
the user"). Comprehension sits near its ceiling for first drafts and cannot see layout, so the
blind pairwise clarity judge decides, and comprehension and length are guardrails. See decide().
"""

from __future__ import annotations

from collections import defaultdict
import json
from pathlib import Path
import random
import re
import statistics
import sys

PRICES = {"haiku": (0.10, 0.50), "sonnet": (2.0, 10.0), "opus": (4.0, 20.0)}  # $ per million tokens (in, out)
PRODUCT_ROLES = {"draft", "junior", "author", "teachback", "verdict", "self", "critic", "critic-revise", "simplify"}
JUDGE_WIN, COMP_TOLERANCE, OPUS_WIN, WORTH_IT_GAP, EPS = 0.65, 0.03, 0.45, 0.05, 1e-9
PRIMARY_JUDGE = "opus"  # chosen on 2026-11-13: decisive across orders where the Sonnet judge followed position


def comprehension(grades: dict, excluded: set) -> float | None:
    per_reader = []
    for items in grades.values():
        scored = [g for g in items if g["id"] not in excluded]
        if scored:
            per_reader.append(sum(g["correct"] for g in scored) / len(scored))
    return sum(per_reader) / len(per_reader) if per_reader else None


def run_cost(usage: dict) -> float:
    """API-equivalent dollars for the product roles only, at 4 characters per token."""
    total = 0.0
    for role, u in usage.get("roles", {}).items():
        if role in PRODUCT_ROLES and u.get("model") in PRICES:
            p_in, p_out = PRICES[u["model"]]
            total += u["in"] / 4 * p_in / 1e6 + u["out"] / 4 * p_out / 1e6
    return total


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def load_runs(iteration_dir: Path) -> list[dict]:
    rows = []
    for run_json in sorted(Path(iteration_dir).rglob("run.json")):
        d = run_json.parent
        run, grades, checks = _load(run_json), _load(d / "grades.json"), _load(d / "checks.json")
        transcript, usage = _load(d / "transcript.json"), _load(d / "usage.json")
        final = (d / "artifact-final.md").read_text(encoding="utf-8")
        reqs = checks.get("requirements", [])
        honesty = checks.get("honesty", [])
        rows.append({
            "case": run["case"], "arm": run["arm"], "author": run["author"], "mode": run["mode"], "rep": run["rep"],
            "comprehension": comprehension(grades.get("grades", {}), set(grades.get("excluded", []))),
            "per_reader": {r: comprehension({r: g}, set(grades.get("excluded", []))) for r, g in grades.get("grades", {}).items()},
            "excluded": len(grades.get("excluded", [])),
            "requirements_rate": (sum(r["present"] for r in reqs) / len(reqs)) if reqs else None,
            "holes_reported": sum(h["reported_as_hole"] for h in honesty), "invented": sum(h["invented"] for h in honesty),
            "mermaid_ok": not checks.get("mermaid_errors"), "rounds": transcript.get("rounds", 0),
            "end_reason": transcript.get("end_reason"), "words": len(re.findall(r"\w+", final)),
            "cost_usd": run_cost(usage), "errors": run.get("errors", []), "skill_rev": run.get("skill_rev"),
        })
    return rows


def _case_means(summary: dict, arm: str, author: str, mode: str, field: str = "comprehension") -> dict:
    by_case = defaultdict(list)
    for r in summary["runs"]:
        if r["arm"] == arm and r["author"] == author and r["mode"] == mode and r.get(field) is not None:
            by_case[r["case"]].append(r[field])
    return {c: statistics.fmean(v) for c, v in by_case.items()}


def paired(summary: dict, arm_a: str, arm_b: str, author: str, mode: str = "natural", seed: int = 52,
           n: int = 2000, author_b: str | None = None) -> dict:
    a = _case_means(summary, arm_a, author, mode)
    b = _case_means(summary, arm_b, author_b or author, mode)
    common = sorted(set(a) & set(b))
    diffs = [a[c] - b[c] for c in common]
    if not diffs:
        return {"mean_diff": None, "ci95": (None, None), "n_cases": 0, "per_case": {}}
    rng = random.Random(seed)
    boots = sorted(statistics.fmean(rng.choices(diffs, k=len(diffs))) for _ in range(n))
    return {"mean_diff": statistics.fmean(diffs), "ci95": (boots[int(0.025 * n)], boots[int(0.975 * n) - 1]),
            "n_cases": len(diffs), "per_case": dict(zip(common, diffs))}


def _mean_over_common(a: dict, b: dict) -> tuple[float | None, float | None]:
    common = sorted(set(a) & set(b))
    if not common:
        return None, None
    return statistics.fmean(a[c] for c in common), statistics.fmean(b[c] for c in common)


def decide(summary: dict, judges: dict | None = None, junior_arm: str = "junior", self_arm: str = "self-review",
           mode: str = "natural", reference: tuple = ("opus", "no-review")) -> dict:
    """The user's revised rule (2026-11-13; docs/junior-dev/design.md, "Decided by the user").

    useful:   >= 65% blind clarity wins against the same author's SelfReview (both orders), comprehension
              within 3 points of SelfReview, and length within 1.5x SelfReview's.
    worth_it: >= 45% blind wins against Opus alone, comprehension within 5 points of it, at a lower cost.
    `judges` is judge_summary() output; the Opus pair is keyed (junior_arm, "no-review@opus", author, mode)."""
    judges = judges or {}
    ref_author, ref_arm = reference
    out = {}
    authors = sorted({r["author"] for r in summary["runs"] if r["arm"] == junior_arm and r["mode"] == mode})
    for author in authors:
        vs_self = paired(summary, junior_arm, self_arm, author, mode)
        vs_opus = paired(summary, junior_arm, ref_arm, author, mode, author_b=ref_author)
        words_j, words_s = _mean_over_common(_case_means(summary, junior_arm, author, mode, "words"),
                                             _case_means(summary, self_arm, author, mode, "words"))
        cost_j, cost_o = _mean_over_common(_case_means(summary, junior_arm, author, mode, "cost_usd"),
                                           _case_means(summary, ref_arm, ref_author, mode, "cost_usd"))
        win_self = (judges.get((junior_arm, self_arm, author, mode)) or {}).get("win_rate")
        win_opus = (judges.get((junior_arm, f"{ref_arm}@{ref_author}", author, mode)) or {}).get("win_rate")
        length_ok = words_j is not None and words_s and words_j <= 1.5 * words_s + EPS
        useful = (win_self is not None and win_self >= JUDGE_WIN - EPS and vs_self["mean_diff"] is not None
                  and vs_self["mean_diff"] >= -COMP_TOLERANCE - EPS and bool(length_ok))
        cheaper = cost_j is not None and cost_j < cost_o
        worth_it = (win_opus is not None and win_opus >= OPUS_WIN - EPS and vs_opus["mean_diff"] is not None
                    and vs_opus["mean_diff"] >= -WORTH_IT_GAP - EPS and cheaper)
        out[author] = {"useful": bool(useful), "worth_it": bool(worth_it), "win_vs_self": win_self,
                       "win_vs_opus": win_opus, "vs_self": vs_self, "vs_opus": vs_opus,
                       "length_ratio": (words_j / words_s) if words_j is not None and words_s else None,
                       "cheaper_than_opus": bool(cheaper)}
    return out


def grader_agreement(by_models: list[dict], a: str = "sonnet", b: str = "opus") -> tuple[int, int]:
    """(items where graders a and b agree, items both graded), over runs graded by both."""
    agree = total = 0
    for by_model in by_models:
        if a not in by_model or b not in by_model:
            continue
        for reader, items in by_model[a].items():
            other = {g["id"]: g["correct"] for g in by_model[b].get(reader, [])}
            for g in items:
                if g["id"] in other:
                    total += 1
                    agree += g["correct"] == other[g["id"]]
    return agree, total


def iteration_agreement(iteration_dir: Path) -> tuple[int, int]:
    return grader_agreement([_load(p).get("by_model", {}) for p in Path(iteration_dir).rglob("grades.json")])


def validation_gates(summary: dict, agreement: float) -> dict:
    """The grader checks of plan Task 7, on NoReview runs over the reference and its variants."""
    def by_case(mode, reader=None):
        vals = defaultdict(list)
        for r in summary["runs"]:
            if r["mode"] == mode:
                v = r["per_reader"].get(reader) if reader else r["comprehension"]
                if v is not None:
                    vals[r["case"]].append(v)
        return {c: statistics.fmean(v) for c, v in vals.items()}

    ref, implicit, padded = by_case("null"), by_case("seeded-implicit"), by_case("padded")
    low_ref, low_pres = by_case("null", "haiku-low"), by_case("seeded-presentation", "haiku-low")
    mean = lambda d: statistics.fmean(d.values()) if d else float("nan")
    lower = [c for c in implicit if c in ref and implicit[c] <= ref[c] - 0.15 + EPS]
    share_lower = len(lower) / len(implicit) if implicit else 0.0
    common = sorted(set(low_ref) & set(low_pres))
    separation = statistics.fmean(low_ref[c] - low_pres[c] for c in common) if common else float("nan")
    gates = {
        "reference_high": {"value": mean(ref), "threshold": ">= 0.85", "passed": mean(ref) >= 0.85 - EPS},
        "implicit_lower": {"value": share_lower, "threshold": ">= 0.70 of cases at least 0.15 below the reference",
                           "passed": share_lower >= 0.70 - EPS},
        "padding_neutral": {"value": mean(padded) - mean(ref), "threshold": "padding earns at most +0.05",
                            "passed": mean(padded) - mean(ref) <= 0.05 + EPS},
        "grader_agreement": {"value": agreement, "threshold": ">= 0.90", "passed": agreement >= 0.90 - EPS},
        "hurried_reader_separates": {"value": separation, "threshold": ">= 0.10 (reported, not blocking)",
                                     "passed": separation >= 0.10 - EPS},
    }
    return gates


def judge_summary(iteration_dir: Path, judge_model: str | None = None, judge_prompt: str = "judge") -> dict:
    """Per (arm_a, arm_b, author, mode): arm_a's preference over arm_b (+1 win, -1 loss, 0 tie, mean over both
    orders), how often both orders agree, and whether the judge simply preferred the longer document.
    `judge_model` keeps one judge's verdicts when an iteration was judged by more than one; `judge_prompt`
    keeps one prompt's ("judge", the clarity rubric, for rows written before prompts were tagged)."""
    rows = []
    for path in sorted(Path(iteration_dir, "judgments").glob("*.json")):
        rows += json.loads(path.read_text(encoding="utf-8"))
    rows = [j for j in rows if j.get("judge_prompt", "judge") == judge_prompt]
    if judge_model:
        rows = [j for j in rows if j.get("judge_model") == judge_model]
    groups = defaultdict(lambda: defaultdict(list))
    for j in rows:
        if j.get("winner_arm") is None:
            continue
        groups[(j["arm_a"], j["arm_b"], j["author"], j["mode"])][(j["case"], j["rep"])].append(j)
    out = {}
    for key, pairs in groups.items():
        arm_a = key[0]
        scores, consistent, longer = [], 0, []
        for js in pairs.values():
            vals = [1 if j["winner_arm"] == arm_a else 0 if j["winner_arm"] == "tie" else -1 for j in js]
            scores += vals
            consistent += len(js) == 2 and vals[0] == vals[1]
            for j in js:
                if j["winner"] in ("A", "B") and j["words_a"] != j["words_b"]:
                    longer.append((j["winner"] == "A") == (j["words_a"] > j["words_b"]))
        out[key] = {"pairs": len(pairs), "judgments": len(scores), "preference": statistics.fmean(scores) if scores else None,
                    "win_rate": sum(v == 1 for v in scores) / len(scores) if scores else None,
                    "position_consistency": consistent / len(pairs) if pairs else None,
                    "longer_wins": sum(longer) / len(longer) if longer else None}
    return out


def win_rate_ci(iteration_dir: Path, arm_a: str, arm_b: str, author: str, mode: str = "natural",
                judge_prompt: str = "judge", judge_model: str = PRIMARY_JUDGE, seed: int = 52, n: int = 2000) -> dict:
    """arm_a's share of judgments won against arm_b, with a 95% interval from a bootstrap over cases
    (each case keeps both of its orders together)."""
    rows = []
    for path in sorted(Path(iteration_dir, "judgments").glob("*.json")):
        rows += json.loads(path.read_text(encoding="utf-8"))
    by_case = defaultdict(list)
    for j in rows:
        if (j.get("judge_prompt", "judge") == judge_prompt and j.get("judge_model") == judge_model and j["arm_a"] == arm_a
                and j["arm_b"] == arm_b and j["author"] == author and j["mode"] == mode and j.get("winner_arm")):
            by_case[j["case"]].append(1 if j["winner_arm"] == arm_a else 0)
    cases = sorted(by_case)
    if not cases:
        return {"win_rate": None, "ci95": (None, None), "judgments": 0, "cases": 0}
    flat = [v for c in cases for v in by_case[c]]
    rng = random.Random(seed)
    stats = []
    for _ in range(n):
        sample = [v for _ in cases for v in by_case[rng.choice(cases)]]
        stats.append(sum(sample) / len(sample))
    stats.sort()
    return {"win_rate": sum(flat) / len(flat), "ci95": (stats[int(0.025 * n)], stats[int(0.975 * n) - 1]),
            "judgments": len(flat), "cases": len(cases)}


def _logistic(rows: list[tuple], ridge: float) -> list[float]:
    """Penalised logistic regression by Newton's method; rows are (y, features...) with an intercept added."""
    import math
    k = len(rows[0])          # intercept + (len - 1) features
    beta = [0.0] * k
    for _ in range(50):
        grad = [-ridge * b for b in beta]
        hess = [[(ridge if i == j else 0.0) for j in range(k)] for i in range(k)]
        for y, *x in rows:
            f = [1.0, *x]
            z = sum(b * v for b, v in zip(beta, f))
            p = 1.0 / (1.0 + math.exp(-max(min(z, 35.0), -35.0)))
            for i in range(k):
                grad[i] += (y - p) * f[i]
                for j in range(k):
                    hess[i][j] += p * (1 - p) * f[i] * f[j]
        # Solve hess * step = grad (Gaussian elimination; k is 3).
        m = [row[:] + [g] for row, g in zip(hess, grad)]
        for c in range(k):
            piv = max(range(c, k), key=lambda r: abs(m[r][c]))
            m[c], m[piv] = m[piv], m[c]
            for r in range(k):
                if r != c and m[c][c]:
                    fac = m[r][c] / m[c][c]
                    m[r] = [a - fac * b for a, b in zip(m[r], m[c])]
        step = [m[i][k] / m[i][i] if m[i][i] else 0.0 for i in range(k)]
        beta = [b + s for b, s in zip(beta, step)]
        if max(abs(s) for s in step) < 1e-8:
            break
    return beta


def length_adjusted(iteration_dirs, arm_a: str, arm_b: str, authors: list[str], mode: str = "natural",
                    judge_prompt: str = "judge", judge_model: str = PRIMARY_JUDGE, ridge: float = 0.5,
                    n_boot: int = 500, seed: int = 52) -> dict:
    """arm_a's chance of winning a judgment against arm_b when both documents have the same length.

    Fits P(arm_a wins) = logistic(b0 + b1 * log2(words_a / words_b) + b2 * position), position +0.5 when
    arm_a is shown first and -0.5 otherwise, over both orders and the given authors; ties are left out.
    `equal_length_win` is logistic(b0); `length_slope` is b1 (how strongly the judge prefers the longer
    document). The interval is a bootstrap over cases. A light ridge keeps the fit finite when one arm
    wins everything."""
    import math
    dirs = iteration_dirs if isinstance(iteration_dirs, (list, tuple)) else [iteration_dirs]
    by_case = defaultdict(list)
    for d in dirs:
        for path in sorted(Path(d, "judgments").glob("*.json")):
            for j in json.loads(path.read_text(encoding="utf-8")):
                if (j.get("judge_prompt", "judge") != judge_prompt or j.get("judge_model") != judge_model
                        or j["arm_a"] != arm_a or j["arm_b"] != arm_b or j["author"] not in authors
                        or j["mode"] != mode or j.get("winner_arm") not in (arm_a, arm_b)):
                    continue
                first = j["order"] == "ab"
                wa, wb = (j["words_a"], j["words_b"]) if first else (j["words_b"], j["words_a"])
                by_case[(j["author"], j["case"])].append(
                    (1 if j["winner_arm"] == arm_a else 0, math.log2(max(wa, 1) / max(wb, 1)), 0.5 if first else -0.5))
    cases = sorted(by_case)
    if not cases:
        return {"equal_length_win": None, "ci95": (None, None), "length_slope": None, "judgments": 0}
    sig = lambda z: 1.0 / (1.0 + math.exp(-z))
    beta = _logistic([r for c in cases for r in by_case[c]], ridge)
    rng = random.Random(seed)
    boots = sorted(sig(_logistic([r for _ in cases for r in by_case[rng.choice(cases)]], ridge)[0]) for _ in range(n_boot))
    return {"equal_length_win": sig(beta[0]), "ci95": (boots[int(0.025 * n_boot)], boots[int(0.975 * n_boot) - 1]),
            "length_slope": beta[1], "position": beta[2], "judgments": sum(len(by_case[c]) for c in cases)}


def score(iteration_dir: Path) -> dict:
    rows = load_runs(iteration_dir)
    groups = defaultdict(list)
    for r in rows:
        groups[(r["arm"], r["author"], r["mode"])].append(r)
    table = []
    for (arm, author, mode), rs in sorted(groups.items()):
        comp = [r["comprehension"] for r in rs if r["comprehension"] is not None]
        table.append({"arm": arm, "author": author, "mode": mode, "runs": len(rs),
                      "comprehension": statistics.fmean(comp) if comp else None,
                      "requirements_rate": statistics.fmean([r["requirements_rate"] for r in rs if r["requirements_rate"] is not None] or [0]),
                      "invented": sum(r["invented"] for r in rs), "mermaid_broken": sum(not r["mermaid_ok"] for r in rs),
                      "rounds": statistics.fmean(r["rounds"] for r in rs), "words": statistics.fmean(r["words"] for r in rs),
                      "cost_usd": statistics.fmean(r["cost_usd"] for r in rs), "errors": sum(bool(r["errors"]) for r in rs)})
    summary = {"runs": rows, "table": table}
    judges = judge_summary(iteration_dir, judge_model=PRIMARY_JUDGE)
    summary["judges"] = {" | ".join(k): v for k, v in judges.items()}
    summary["decision"] = decide(summary, judges) if any(r["arm"] == "junior" for r in rows) else {}
    Path(iteration_dir, "summary.json").write_text(json.dumps(summary, indent=1, default=list) + "\n", encoding="utf-8",
                                                   newline="\n")
    lines = ["| arm | author | mode | runs | comprehension | requirements | invented | rounds | words | cost $ | errors |",
             "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for t in table:
        comp = "n/a" if t["comprehension"] is None else f"{t['comprehension']:.3f}"
        lines.append(f"| {t['arm']} | {t['author']} | {t['mode']} | {t['runs']} | {comp} | {t['requirements_rate']:.2f} | "
                     f"{t['invented']} | {t['rounds']:.1f} | {t['words']:.0f} | {t['cost_usd']:.4f} | {t['errors']} |")
    Path(iteration_dir, "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return summary


if __name__ == "__main__":
    s = score(Path(sys.argv[1]))
    print(Path(sys.argv[1], "summary.md").read_text(encoding="utf-8"))
    print(json.dumps(s["decision"], indent=1, default=list))
