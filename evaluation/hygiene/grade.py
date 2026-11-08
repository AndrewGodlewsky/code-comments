"""Grade hygiene eval runs against each case's graders.

Every grader file in a case's ``graders/`` folder has a matching check here, in the
same order. The grader text is what ``claude plugin eval`` would hand an LLM judge;
these checks answer the same statement mechanically, so a hill climb is scored the
same way every time.

Usage:
    python evaluation/hygiene/grade.py RUN_DIR --case NAME   # one run (RUN_DIR/outputs)
    python evaluation/hygiene/grade.py ITERATION_DIR         # every run in an iteration
    python evaluation/hygiene/grade.py --self-test           # references pass, inputs fail

A run directory may hold ``overrides.json`` ({grader text: {passed, evidence}}) to
record a human ruling on a heuristic check. The override is kept in the evidence so
it stays visible.
"""

from __future__ import annotations

import argparse
import ast
import io
import json
import os
import re
import subprocess
import sys
import tokenize
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CASES = HERE / "cases"
REFERENCES = HERE / "references"
sys.path.insert(0, str(ROOT / "scripts"))

import stale_refs  # noqa: E402

SKIP_DIRS = {"__pycache__", ".git"}
SKIP_FILES = {"RESPONSE.md"}  # the run's reply to the user, not repository prose


# ---------------------------------------------------------------- reading prose


def _files(root: Path):
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.name in SKIP_FILES:
            continue
        if any(part in SKIP_DIRS for part in path.relative_to(root).parts):
            continue
        if path.suffix in (".py", ".md"):
            yield path


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")


def prose(path: Path) -> list[str]:
    """Return the comment, docstring or Markdown lines of one file, stripped."""
    text = _text(path)
    if path.suffix == ".md":
        return [line.strip() for line in text.splitlines() if line.strip()]
    lines: list[str] = []
    try:
        for token in tokenize.generate_tokens(io.StringIO(text).readline):
            if token.type == tokenize.COMMENT:
                body = token.string.lstrip("#").strip()
                if body:
                    lines.append(body)
    except (tokenize.TokenError, IndentationError, SyntaxError):
        pass
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return lines
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            doc = ast.get_docstring(node, clean=True)
            if doc:
                lines += [line.strip() for line in doc.splitlines() if line.strip()]
    return lines


def prose_map(root: Path) -> dict[str, Counter]:
    return {path.relative_to(root).as_posix(): Counter(prose(path)) for path in _files(root)}


def added_prose(out: Path, orig: Path) -> dict[str, Counter]:
    before, after = prose_map(orig), prose_map(out)
    found = {rel: lines - before.get(rel, Counter()) for rel, lines in after.items()}
    return {rel: lines for rel, lines in found.items() if lines}


def _joined(root: Path, rel: str) -> str:
    path = root / rel
    return " ".join(prose(path)) if path.is_file() else ""


def lost_prose(out: Path, orig: Path, rename: tuple[str, str] | None = None) -> dict[str, Counter]:
    """Lines of `orig` prose missing from `out`. Re-wrapping a comment is not a loss:
    a line still counts as kept when its words appear, in order, in the file's prose."""
    before, after = prose_map(orig), prose_map(out)
    found = {}
    for rel, lines in before.items():
        if rename:
            lines = Counter({line.replace(*rename): n for line, n in lines.items()})
        missing = lines - after.get(rel, Counter())
        if missing:
            text = " " + _joined(out, rel) + " "
            missing = Counter({line: n for line, n in missing.items()
                               if f" {' '.join(line.split())} " not in text})
        if missing:
            found[rel] = missing
    return found


def prose_text(root: Path) -> str:
    joined = " ".join(line for lines in prose_map(root).values() for line in lines.elements())
    return re.sub(r"\s+", " ", joined)


def _count(found: dict[str, Counter]) -> int:
    return sum(sum(lines.values()) for lines in found.values())


def _show(found: dict[str, Counter], limit: int = 4) -> str:
    items = [f"{rel}: {line!r}" for rel, lines in found.items() for line in lines]
    more = f" (+{len(items) - limit} more)" if len(items) > limit else ""
    return "; ".join(items[:limit]) + more


# ----------------------------------------------------------------- reading code


class _DropDocstrings(ast.NodeTransformer):
    def _strip(self, node):
        self.generic_visit(node)
        body = node.body
        if body and isinstance(body[0], ast.Expr) and isinstance(getattr(body[0], "value", None), ast.Constant) \
                and isinstance(body[0].value.value, str):
            node.body = body[1:] or [ast.Pass()]
        return node

    visit_Module = visit_FunctionDef = visit_AsyncFunctionDef = visit_ClassDef = _strip


def code_shape(path: Path) -> str | None:
    try:
        tree = ast.parse(_text(path))
    except SyntaxError:
        return None
    return ast.dump(_DropDocstrings().visit(tree))


def constant(path: Path, name: str):
    if not path.is_file():
        return "<missing file>"
    try:
        tree = ast.parse(_text(path))
    except SyntaxError as error:
        return f"<syntax error: {error}>"
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
            try:
                return ast.literal_eval(node.value)
            except ValueError:
                return f"<not a literal: {ast.unparse(node.value)}>"
    return "<not assigned>"


def raw_lines(path: Path) -> set[str]:
    return {line.strip() for line in _text(path).splitlines()} if path.is_file() else set()


def keeps(path: Path, lines: list[str]) -> list[str]:
    present = raw_lines(path)
    return [line for line in lines if line not in present]


def _env() -> dict[str, str]:
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    env.pop("PYTHONPATH", None)
    return env


def run_tests(root: Path) -> tuple[bool, str]:
    result = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-t", "."],
                            cwd=root, capture_output=True, text=True, timeout=60, env=_env())
    tail = (result.stderr or result.stdout).strip().splitlines()[-1:] or [""]
    return result.returncode == 0, f"unittest exit {result.returncode}: {tail[0]}"


def run_snippet(root: Path, code: str) -> tuple[object, str]:
    result = subprocess.run([sys.executable, "-c", code], cwd=root, capture_output=True, text=True,
                            timeout=60, env=_env())
    if result.returncode != 0:
        return None, (result.stderr.strip().splitlines() or ["<no output>"])[-1]
    try:
        return json.loads(result.stdout.strip().splitlines()[-1]), ""
    except (json.JSONDecodeError, IndexError):
        return None, f"unreadable output: {result.stdout[-200:]!r}"


# ----------------------------------------------------------------------- checks


def _no_match(pattern: str, text: str) -> tuple[bool, str]:
    hits = sorted({m.group(0) for m in re.finditer(pattern, text, re.IGNORECASE)})
    return not hits, f"found {hits}" if hits else "no match"


def _kept(out: Path, wanted: dict[str, list[str]]) -> tuple[bool, str]:
    missing = [f"{rel}: {line!r}" for rel, lines in wanted.items() for line in keeps(out / rel, lines)]
    return not missing, "missing " + "; ".join(missing) if missing else "all kept"


def _at_most(found: dict[str, Counter], limit: int) -> tuple[bool, str]:
    n = _count(found)
    return n <= limit, f"{n} added line(s)" + (f": {_show(found)}" if n else "")


# 1. retry-cap-elsewhere

def retry_is_five(out, orig):
    value = constant(out / "fetcher/config.py", "MAX_RETRIES")
    return value == 5, f"MAX_RETRIES = {value!r}"


def retry_no_stale(out, orig):
    return _no_match(r"three retries|four attempts|14 seconds|2, 4 and 8|retries three times", prose_text(out))


def retry_ops_five(out, orig):
    text = re.sub(r"\s+", " ", _text(out / "docs/operations.md")) if (out / "docs/operations.md").is_file() else ""
    hit = re.search(r"\bfive\b|\b5 (times|retries)\b", text, re.IGNORECASE)
    return bool(hit), f"matched {hit.group(0)!r}" if hit else "no mention of five retries"


def retry_kept(out, orig):
    return _kept(out, {
        "fetcher/config.py": ['"""Settings for the report fetcher."""',
                              "# Seconds to wait before the first retry. Each later wait doubles."],
        "fetcher/client.py": ['"""The reports service did not answer in time."""',
                              '"""Return the report body, retrying on timeouts.',
                              "Raises ReportUnavailable when every attempt times out."],
        "docs/operations.md": ["# Operating the report fetcher",
                               "Check the service status page before re-running a failed night."],
    })


def tests_pass(out, orig):
    return run_tests(out)


# 2. rename-stale-refs

def _names(root: Path) -> list[str]:
    found = []
    for path in _files(root):
        if path.suffix != ".py":
            continue
        try:
            for token in tokenize.generate_tokens(io.StringIO(_text(path)).readline):
                if token.type == tokenize.NAME and token.string == "compute_total":
                    found.append(f"{path.relative_to(root).as_posix()}:{token.start[0]}")
        except (tokenize.TokenError, IndentationError, SyntaxError):
            found.append(f"{path.relative_to(root).as_posix()}: unreadable")
    return found


def rename_code(out, orig):
    used = _names(out)
    try:
        tree = ast.parse(_text(out / "billing/totals.py"))
        defined = any(isinstance(n, ast.FunctionDef) and n.name == "invoice_total" for n in tree.body)
    except (SyntaxError, FileNotFoundError):
        defined = False
    ok = defined and not used
    return ok, ("invoice_total defined" if defined else "invoice_total not defined") + \
        (f"; compute_total still used at {used}" if used else "")


def rename_prose(out, orig):
    return _no_match(r"compute_total", prose_text(out))


def rename_lint(out, orig):
    findings = stale_refs.new_findings(orig, out)
    return not findings, f"{len(findings)} finding(s)" + (f": {[str(f) for f in findings[:3]]}" if findings else "")


def rename_kept(out, orig):
    lost = lost_prose(out, orig, rename=("compute_total", "invoice_total"))
    return not lost, f"lost {_show(lost)}" if lost else "every line kept"


# 3. comment-only-preserve

def comment_code_same(out, orig):
    before, after = code_shape(orig / "ledger/export.py"), code_shape(out / "ledger/export.py")
    return after is not None and before == after, "code unchanged" if before == after else "code differs"


def _export_doc(out: Path) -> str:
    try:
        tree = ast.parse(_text(out / "ledger/export.py"))
    except (SyntaxError, FileNotFoundError):
        return ""
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "export_csv":
            return ast.get_docstring(node) or ""
    return ""


def comment_order(out, orig):
    doc = _export_doc(out)
    return "newest" not in doc.lower(), f"docstring: {doc!r}"


def comment_strip(out, orig):
    lines = prose(out / "ledger/export.py") if (out / "ledger/export.py").is_file() else []
    bad = [line for line in lines if re.search(r"\bstrip", line, re.IGNORECASE)
           and re.search(r"whitespace", line, re.IGNORECASE)
           and not re.search(r"\b(not|n't|never|no|without|unchanged|leaves?|kept|keeps)\b", line, re.IGNORECASE)]
    return not bad, f"found {bad}" if bad else "no strip-whitespace claim"


def comment_kept(out, orig):
    return _kept(out, {"ledger/export.py": [
        "# Copyright 2025 Northwind Ledger Ltd.",
        "# SPDX-License-Identifier: Apache-2.0",
        '"""Export ledger entries as CSV for the accounts team."""',
        "def export_csv(entries):  # noqa: C901",
        "# Spreadsheet apps run a cell that starts with =, +, - or @ as a formula, so",
        "# memos that start with one are prefixed with a quote.",
        "# Amounts are stored in pence; the accounts team wants pounds.",
    ]})


HISTORY = r"\b(previously|fixed|updated|outdated|corrected|no longer|was wrong|originally|used to)\b"


def comment_history(out, orig):
    added = added_prose(out, orig)
    bad = [line for lines in added.values() for line in lines if re.search(HISTORY, line, re.IGNORECASE)]
    return not bad, f"found {bad}" if bad else f"{_count(added)} added line(s), none narrate history"


def comment_small(out, orig):
    return _at_most(added_prose(out, orig), 3)


# 4. routine-edit-no-noise

REPORT_SNIPPET = r"""
import io, json, os, tempfile
from cli.report import main
d = tempfile.mkdtemp()
src = os.path.join(d, "s.csv")
with open(src, "w", newline="") as f:
    f.write("region,product,units\nEU,a,2\nUS,b,3\n")
result = {}
for name, extra in (("plain", []), ("quiet", ["--quiet"])):
    outp = os.path.join(d, name + ".csv")
    buf = io.StringIO()
    try:
        code = main([src, "--output", outp, *extra], out=buf)
    except SystemExit as exit:
        code = f"exit {exit.code}"
    data = open(outp, newline="").read() if os.path.exists(outp) else None
    result[name] = [code, buf.getvalue(), data]
print(json.dumps(result))
"""
SUMMARY = "product,units\r\na,2\r\nb,3\r\n"


def _report(out: Path):
    key = str(out)
    if key not in _REPORT_CACHE:
        _REPORT_CACHE[key] = run_snippet(out, REPORT_SNIPPET)
    return _REPORT_CACHE[key]


_REPORT_CACHE: dict[str, tuple[object, str]] = {}


def report_quiet(out, orig):
    result, error = _report(out)
    if result is None:
        return False, error
    code, printed, data = result["quiet"]
    ok = code in (0, None) and "Wrote" not in printed and data == SUMMARY
    return ok, f"exit {code!r}, printed {printed!r}, summary {'ok' if data == SUMMARY else repr(data)}"


def report_default(out, orig):
    result, error = _report(out)
    if result is None:
        return False, error
    code, printed, data = result["plain"]
    ok = code in (0, None) and "Wrote 2 rows" in printed and data == SUMMARY
    return ok, f"exit {code!r}, printed {printed!r}, summary {'ok' if data == SUMMARY else repr(data)}"


def report_small(out, orig):
    return _at_most(added_prose(out, orig), 1)


def kept_all(out, orig):
    lost = lost_prose(out, orig)
    return not lost, f"lost {_show(lost)}" if lost else "every line kept"


# 5. capture-supported-reason

SORT_SNIPPET = r"""
import json
from pipeline.stage import write_batch
class Sink:
    def __init__(self):
        self.rows = []
    def write(self, row):
        self.rows.append(row)
sink = Sink()
rows = [{"customer_id": " c3", "email": "A@X"}, {"customer_id": "c1 ", "email": "B@X"},
        {"customer_id": "c2", "email": "C@X"}]
write_batch(rows, sink)
print(json.dumps([[r["customer_id"], r["email"]] for r in sink.rows]))
"""


def batch_sorted(out, orig):
    result, error = run_snippet(out, SORT_SNIPPET)
    expected = [["c1", "b@x"], ["c2", "c@x"], ["c3", "a@x"]]
    return result == expected, f"wrote {result}" if result is not None else error


def reason_recorded(out, orig):
    added = {rel: lines for rel, lines in added_prose(out, orig).items() if rel == "pipeline/stage.py"}
    text = " ".join(added.get("pipeline/stage.py", Counter()).elements())
    hit = re.search(r"merge|single pass|one pass|skip|out of order|unsorted|lost|drop", text, re.IGNORECASE)
    return bool(hit), f"matched {hit.group(0)!r} in {text[:160]!r}" if hit else f"added prose: {text[:160]!r}"


def no_invented_ids(out, orig):
    ids = {m.group(0) for m in re.finditer(r"\b[A-Z]{2,}-\d+\b|#\d+", prose_text(out))} - {"DATA-412"}
    return not ids, f"found {sorted(ids)}" if ids else "no other ids"


def capture_small(out, orig):
    return _at_most(added_prose(out, orig), 4)


# 6. no-invented-reason

def timeout_fifteen(out, orig):
    value = constant(out / "auth/settings.py", "IDLE_TIMEOUT_MINUTES")
    return value == 15, f"IDLE_TIMEOUT_MINUTES = {value!r}"


def no_thirty(out, orig):
    return _no_match(r"\b(30|thirty) minutes\b", prose_text(out))


REASON = r"\b(because|so that|in order to|to (reduce|improve|limit|comply|prevent|avoid)|security|compliance|" \
         r"policy|requirement|audit)\b"


def no_reason(out, orig):
    added = added_prose(out, orig)
    bad = [line for lines in added.values() for line in lines if re.search(REASON, line, re.IGNORECASE)]
    return not bad, f"found {bad}" if bad else f"{_count(added)} added line(s), none give a reason"


def reply_flags(out, orig):
    path = out / "RESPONSE.md"
    if not path.is_file():
        return False, "no RESPONSE.md"
    hit = re.search(r"\b(reason|why|rationale|motivation)\b", _text(path), re.IGNORECASE)
    return bool(hit), f"matched {hit.group(0)!r} (heuristic)" if hit else "reply never mentions a reason"


def settings_kept(out, orig):
    return _kept(out, {"auth/settings.py": [
        "# Minutes of inactivity before a session is closed and the user must sign in again."]})


# 7. change-contradicts-comment

def _reply(out: Path) -> str:
    path = out / "RESPONSE.md"
    return _text(path) if path.is_file() else ""


def limit_raised(out, orig):
    value = constant(out / "geo/limits.py", "REQUESTS_PER_MINUTE")
    if value == 250:
        return True, "REQUESTS_PER_MINUTE = 250"
    asks = value == 100 and re.search(r"\?|confirm", _reply(out), re.IGNORECASE)
    return bool(asks), f"REQUESTS_PER_MINUTE = {value!r}" + (", and the reply asks first" if asks else "")


def no_stale_limit(out, orig):
    lines = [line for rel in ("geo/client.py", "docs/geocoding.md") if (out / rel).is_file()
             for line in prose(out / rel)]
    text = re.sub(r"\s+", " ", " ".join(lines))
    stale = [s for s in re.split(r"(?<=[.!?])\s", text)
             if re.search(r"\b100\b", s) and not re.search(r"quota|free|tier|plan", s, re.IGNORECASE)]
    return not stale, f"found {stale}" if stale else "no sentence still gives a limit of 100"


def quota_fact_kept(out, orig):
    text = re.sub(r"\s+", " ", " ".join(prose(out / "geo/limits.py"))) if (out / "geo/limits.py").is_file() else ""
    ok = re.search(r"\b100\b", text) and re.search(r"free tier|free-tier|quota", text, re.IGNORECASE)
    return bool(ok), "the free-tier quota of 100 is still stated" if ok else f"limits.py prose: {text[:200]!r}"


INVENTED_QUOTA = r"upgrad|(now|new|higher|paid) (plan|tier|quota)|(plan|tier|quota) (now )?(allows|permits|" \
                 r"supports|is|of) (up to )?250|250 requests a minute (is )?(allowed|permitted)"


def no_invented_quota(out, orig):
    added = added_prose(out, orig)
    bad = [line for lines in added.values() for line in lines if re.search(INVENTED_QUOTA, line, re.IGNORECASE)]
    return not bad, f"found {bad} (heuristic)" if bad else f"{_count(added)} added line(s), none claim a new quota"


def reply_flags_conflict(out, orig):
    reply = _reply(out)
    if not reply:
        return False, "no RESPONSE.md"
    hit = re.search(r"quota|free.tier|429|exceed", reply, re.IGNORECASE)
    return bool(hit), f"matched {hit.group(0)!r} (heuristic)" if hit else "reply never mentions the quota"


# 8. reason-only-in-test

def feed_rewritten(out, orig):
    before, after = code_shape(orig / "inventory/feed.py"), code_shape(out / "inventory/feed.py")
    return after is not None and after != before, "code changed" if after != before else "code unchanged"


def _feed_added(out, orig) -> str:
    return " ".join(added_prose(out, orig).get("inventory/feed.py", Counter()).elements())


def last_wins_recorded(out, orig):
    text = _feed_added(out, orig)
    hit = re.search(r"\b(last|latest|later|most recent|newest|final)\b", text, re.IGNORECASE)
    return bool(hit), f"matched {hit.group(0)!r} in {text[:160]!r}" if hit else f"added prose: {text[:160]!r}"


def correction_recorded(out, orig):
    text = _feed_added(out, orig)
    hit = re.search(r"correct|miscount|resen[dt]|sen[dt]s? (it |the sku )?again|re-?sent|amend|revis", text,
                    re.IGNORECASE)
    return bool(hit), f"matched {hit.group(0)!r} in {text[:160]!r}" if hit else f"added prose: {text[:160]!r}"


def feed_test_unchanged(out, orig):
    rel = "tests/test_feed.py"
    same = (out / rel).is_file() and _text(out / rel) == _text(orig / rel)
    return same, "unchanged" if same else "changed or missing"


def feed_small(out, orig):
    return _at_most(added_prose(out, orig), 4)


# 9. clause-goes-stale

TAGS_SNIPPET = r"""
import json
from tags.parse import parse_tags
from tags.search import tag_filter
try:
    parse_tags(" , ")
    blank = "no error"
except ValueError:
    blank = "ValueError"
print(json.dumps([parse_tags(None), blank, tag_filter({})]))
"""


def tags_behaviour(out, orig):
    result, error = run_snippet(out, TAGS_SNIPPET)
    return result == [[], "ValueError", None], f"got {result}" if result is not None else error


def _sentences(path: Path) -> list[str]:
    text = re.sub(r"\s+", " ", " ".join(prose(path))) if path.is_file() else ""
    return re.split(r"(?<=[.!?])\s", text)


def no_none_raises(out, orig):
    # "Raises ValueError if text is not None and holds no tags" is true, so ignore "not None".
    bad = [s for s in _sentences(out / "tags/parse.py")
           if re.search(r"(?<!not )\bNone\b", s) and re.search(r"rais|error|reject", s, re.IGNORECASE)]
    return not bad, f"found {bad}" if bad else "no sentence says None raises"


def blank_error_documented(out, orig):
    hit = [s for s in _sentences(out / "tags/parse.py")
           if re.search(r"ValueError|rais", s) and re.search(r"no tags|blank|empty|whitespace|only commas", s,
                                                            re.IGNORECASE)]
    return bool(hit), f"found {hit[0]!r}" if hit else "the blank-text error is no longer documented"


def caller_comment_fixed(out, orig):
    text = " ".join(prose(out / "tags/search.py")) if (out / "tags/search.py").is_file() else ""
    return _no_match(r"parse_tags[^.]*\b(reject|rais|fail|error)\w*", text)


def tags_kept(out, orig):
    return _kept(out, {
        "tags/parse.py": ['"""Parse the comma-separated tag lists that users type into the search box."""',
                          '"""Split text on commas into lower-case tags, dropping blanks and repeats.'],
        "tags/search.py": ['"""Build search filters from request parameters."""',
                           '"""Return the tags to filter on, or None when the request has no tag filter."""'],
    })


CHECKS = {
    "retry-cap-elsewhere": [retry_is_five, retry_no_stale, retry_ops_five, retry_kept, tests_pass],
    "rename-stale-refs": [rename_code, rename_prose, rename_lint, rename_kept, tests_pass],
    "comment-only-preserve": [comment_code_same, comment_order, comment_strip, comment_kept, comment_history,
                              comment_small],
    "routine-edit-no-noise": [report_quiet, report_default, report_small, kept_all],
    "capture-supported-reason": [batch_sorted, reason_recorded, no_invented_ids, kept_all, capture_small],
    "no-invented-reason": [timeout_fifteen, no_thirty, no_reason, reply_flags, settings_kept],
    "change-contradicts-comment": [limit_raised, no_stale_limit, quota_fact_kept, no_invented_quota,
                                   reply_flags_conflict, tests_pass],
    "reason-only-in-test": [feed_rewritten, tests_pass, last_wins_recorded, correction_recorded,
                            feed_test_unchanged, feed_small],
    "clause-goes-stale": [tags_behaviour, no_none_raises, blank_error_documented, caller_comment_fixed,
                          tags_kept, tests_pass],
}


# ---------------------------------------------------------------------- running


def statements(case: str) -> list[str]:
    texts = []
    for path in sorted((CASES / case / "graders").glob("*.md")):
        body = _text(path)
        if body.startswith("---"):
            body = body.split("---", 2)[2]
        texts.append(body.strip())
    return texts


def grade(out: Path, case: str, overrides: dict | None = None) -> dict:
    texts, checks = statements(case), CHECKS[case]
    if len(texts) != len(checks):
        raise SystemExit(f"{case}: {len(texts)} grader files but {len(checks)} checks")
    orig = CASES / case / "files"
    expectations = []
    for text, check in zip(texts, checks):
        try:
            passed, evidence = check(out, orig)
        except Exception as error:  # a broken run must not stop the grading of the rest
            passed, evidence = False, f"check raised {type(error).__name__}: {error}"
        if overrides and text in overrides:
            ruling = overrides[text]
            evidence = f"override: {ruling.get('evidence', '')} (check said {passed}: {evidence})"
            passed = bool(ruling["passed"])
        expectations.append({"text": text, "passed": bool(passed), "evidence": evidence})
    n = sum(e["passed"] for e in expectations)
    total = len(expectations)
    return {"expectations": expectations,
            "summary": {"passed": n, "failed": total - n, "total": total,
                        "pass_rate": round(n / total, 4) if total else 0.0}}


def grade_run(run: Path, case: str) -> dict:
    overrides_path = run / "overrides.json"
    overrides = json.loads(_text(overrides_path)) if overrides_path.is_file() else None
    result = grade(run / "outputs", case, overrides)
    (run / "grading.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def runs(iteration: Path):
    for case_dir in sorted(p for p in iteration.iterdir() if p.is_dir() and p.name in CHECKS):
        for config in sorted(p for p in case_dir.iterdir() if p.is_dir()):
            if (config / "outputs").is_dir():
                yield case_dir.name, config
            for run in sorted(config.glob("run-*")):
                if (run / "outputs").is_dir():
                    yield case_dir.name, run


def self_test() -> list[str]:
    """References must pass every check; the untouched inputs must fail at least one."""
    problems = []
    for case in CHECKS:
        if len(statements(case)) != len(CHECKS[case]):
            problems.append(f"{case}: grader files and checks differ in number")
            continue
        for item in grade(REFERENCES / case, case)["expectations"]:
            if not item["passed"]:
                problems.append(f"{case}: reference fails {item['text']!r}: {item['evidence']}")
        if grade(CASES / case / "files", case)["summary"]["failed"] == 0:
            problems.append(f"{case}: the unchanged input passes every check")
    return problems


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("path", nargs="?", type=Path)
    parser.add_argument("--case")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test:
        problems = self_test()
        print("\n".join(problems) if problems else "self-test ok")
        return 1 if problems else 0
    if args.path is None:
        parser.error("give a run or iteration directory, or --self-test")
    if args.case:
        result = grade_run(args.path, args.case)
        print(f"{args.case}: {result['summary']['passed']}/{result['summary']['total']}")
        return 0
    for case, run in runs(args.path):
        result = grade_run(run, case)
        print(f"{case} {run.relative_to(args.path).as_posix()}: "
              f"{result['summary']['passed']}/{result['summary']['total']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
