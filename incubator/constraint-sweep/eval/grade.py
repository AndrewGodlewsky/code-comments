"""Grade constraint-sweep eval runs.

Each case's graders/ folder holds one statement per file. CHECKS below gives one
mechanical check per grader file, in the same order, so a hill climb is scored the
same way every time. A check is ``check(out, orig) -> (passed, evidence)``: ``out`` is
the run's repository and ``orig`` is the case's untouched files/.

Core checks run hidden tests from ``eval/hidden/<case>/hidden_tests/``. The agent never
sees them; gradelib.run_hidden_tests copies the run before running them. Reply checks read
RESPONSE.md (the agent's message to the user) by keyword, and their evidence says
"(heuristic)". Most are scored only when the outcome they describe happened, so a reply
that names the right file cannot pass a run that broke it. Record any ruling on them in
the run's overrides.json; never edit the check to fit a run.

Run the checks through the shared harness:
    python incubator/harness.py self-test constraint-sweep
"""

from __future__ import annotations

import ast
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from gradelib import (constant, files, files_unchanged, lost_prose, nothing_lost, prose,  # noqa: E402
                      reply, run_hidden_tests, run_snippet, run_tests, same_code, show, text)

HERE = Path(__file__).resolve().parent
HIDDEN = HERE / "hidden"

# A twin is the same case with one file changed: positional-columns-in-sql-pointer adds
# a pointer comment in the edited file. Their pass rates are compared, so everything
# else (prompt, graders, fixture, hidden tests) must stay identical.
TWINS = {"positional-columns-in-sql-pointer": ("positional-columns-in-sql", {"exporter/csv_out.py"})}


# ------------------------------------------------------------------- helpers


def _tree_texts(root: Path) -> dict[str, str]:
    return {p.relative_to(root).as_posix(): text(p) for p in files(root, None)} if root.is_dir() else {}


def twin_drift(case: str) -> list[str]:
    """What differs between a twin and its base case beyond the one allowed file."""
    if case not in TWINS:
        return []
    base, allowed = TWINS[case]
    pairs = [(HERE / "cases" / base / part, HERE / "cases" / case / part)
             for part in ("prompt.md", "place-files.sh", "graders", "files")]
    pairs.append((HIDDEN / base, HIDDEN / case))
    drift = []
    for a, b in pairs:
        if a.is_file() or b.is_file():
            if not (a.is_file() and b.is_file() and text(a) == text(b)):
                drift.append(b.relative_to(HERE).as_posix())
            continue
        left, right = _tree_texts(a), _tree_texts(b)
        skip = allowed if a.name == "files" else set()
        drift += [f"{b.relative_to(HERE).as_posix()}/{rel}" for rel in sorted(set(left) | set(right))
                  if rel not in skip and left.get(rel) != right.get(rel)]
    return drift


def hidden(case: str):
    """The case's hidden tests, run on a copy of the run's repository."""
    def check(out, orig):
        drift = twin_drift(case)
        if drift:
            return False, f"twin {case} drifted from {TWINS[case][0]}: {drift[:3]}"
        return run_hidden_tests(out, HIDDEN / case)
    check.__name__ = f"hidden_{case.replace('-', '_')}"
    return check


def tests_pass(out, orig):
    return run_tests(out)


def _tree(path: Path):
    try:
        return ast.parse(text(path))
    except (SyntaxError, OSError, ValueError):
        return None


def _function(path: Path, name: str):
    tree = _tree(path) if path.is_file() else None
    if tree is None:
        return None
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    return None


def _function_code(path: Path, name: str) -> str | None:
    """A function's code without its docstring (comments never reach the AST)."""
    node = _function(path, name)
    if node is None:
        return None
    body = node.body
    if body and isinstance(body[0], ast.Expr) and isinstance(getattr(body[0], "value", None), ast.Constant) \
            and isinstance(body[0].value.value, str):
        body = body[1:]
    return ast.dump(ast.Module(body=body, type_ignores=[]))


def _defined(path: Path) -> set[str]:
    tree = _tree(path) if path.is_file() else None
    if tree is None:
        return set()
    return {n.name for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}


def _python_sorts(path: Path) -> list[str]:
    """Every sorted() and .sort() call in a Python file."""
    tree = _tree(path) if path.is_file() else None
    if tree is None:
        return ["<missing or unreadable file>"]
    hits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id == "sorted":
                hits.append(f"sorted() on line {node.lineno}")
            elif isinstance(func, ast.Attribute) and func.attr == "sort":
                hits.append(f".sort() on line {node.lineno}")
    return hits


def _source_rels(root: Path) -> list[str]:
    """Python files outside tests/."""
    return [p.relative_to(root).as_posix() for p in files(root, {".py"})
            if not p.relative_to(root).as_posix().startswith("tests/")]


def code_elsewhere_unchanged(out: Path, orig: Path, allowed: set[str]) -> tuple[bool, str]:
    """Every Python file outside tests/ and the allowed set keeps its code."""
    return same_code(out, orig, [rel for rel in _source_rels(orig) if rel not in allowed])


def _sql_comments(path: Path) -> list[str]:
    if not path.is_file():
        return []
    return [line.strip()[2:].strip() for line in text(path).splitlines()
            if line.strip().startswith("--") and line.strip()[2:].strip()]


def _sql_code(path: Path) -> str | None:
    """The SQL without its comments, whitespace-normalised and lower-cased."""
    if not path.is_file():
        return None
    return " ".join(" ".join(line.split("--", 1)[0] for line in text(path).splitlines()).split()).lower()


def _lost_sql_comments(out: Path, orig: Path, rel: str) -> list[str]:
    body = " " + " ".join(" ".join(_sql_comments(out / rel)).split()) + " "
    return [f"{rel}: {line!r}" for line in _sql_comments(orig / rel) if f" {' '.join(line.split())} " not in body]


SOURCE_SUFFIXES = {".py", ".sh", ".sql"}


def _source_prose(path: Path) -> list[str]:
    """Comment and docstring lines of a Python, shell or SQL file."""
    return _sql_comments(path) if path.suffix == ".sql" else prose(path)


def net_added_lines(out: Path, orig: Path, only: str | None = None) -> tuple[int, str]:
    """Comment and docstring lines added to Python, shell and SQL files outside tests/
    (or to the one file `only`), counted net per file: lines added minus lines removed,
    never below zero. A reworded or re-wrapped line replaces a line; it is not an extra
    one. Gate fix (eval/GATE.md): the earlier count scored a one-line docstring reworded
    to state the order contract as an added line on top of the new ones."""
    rels = sorted({p.relative_to(root).as_posix() for root in (orig, out) if root.is_dir()
                   for p in files(root, SOURCE_SUFFIXES)})
    rels = [rel for rel in rels if (rel == only if only else not rel.startswith("tests/"))]
    total, shown = 0, []
    for rel in rels:
        before = Counter(_source_prose(orig / rel)) if (orig / rel).is_file() else Counter()
        after = Counter(_source_prose(out / rel)) if (out / rel).is_file() else Counter()
        added, removed = after - before, before - after
        total += max(0, sum(added.values()) - sum(removed.values()))
        if added:
            shown += [f"{rel}: {line!r}" for line in added.elements()]
            if removed:
                shown.append(f"({rel}: {sum(removed.values())} existing line(s) replaced)")
    more = f" (+{len(shown) - 5} more)" if len(shown) > 5 else ""
    return total, "; ".join(shown[:5]) + more


def few_comments(limit: int, only: str | None = None):
    """At most `limit` net added comment or docstring lines (see net_added_lines)."""
    def check(out, orig):
        n, shown = net_added_lines(out, orig, only)
        return n <= limit, f"{n} net added line(s), limit {limit}" + (f": {shown}" if shown else "")
    check.__name__ = "few_comments"
    return check


few_source_comments = few_comments(3)


def both(*results: tuple[bool, str]) -> tuple[bool, str]:
    return all(ok for ok, _ in results), "; ".join(evidence for _, evidence in results)


def file_kept(out: Path, orig: Path, rel: str) -> tuple[bool, str]:
    """The Python file keeps its code and every comment and docstring line."""
    code = same_code(out, orig, [rel])
    lost = {k: v for k, v in lost_prose(out, orig).items() if k == rel}
    return both(code, (not lost, f"lost {show(lost)}" if lost else "every comment line kept"))


def shell_kept(out: Path, orig: Path, rel: str) -> tuple[bool, str]:
    """The shell script keeps every command line and every comment line (comments may be added)."""
    def commands(path: Path):
        return [line.strip() for line in text(path).splitlines()
                if line.strip() and not line.strip().startswith("#")] if path.is_file() else None
    same = commands(out / rel) == commands(orig / rel)
    lost = {k: v for k, v in lost_prose(out, orig).items() if k == rel}
    return both((same, "commands unchanged" if same else f"commands changed in {rel}"),
                (not lost, f"lost {show(lost)}" if lost else "every comment line kept"))


def sql_kept(out: Path, orig: Path, rel: str) -> tuple[bool, str]:
    """The SQL file keeps its SQL and every comment line (comments may be added)."""
    same = _sql_code(out / rel) == _sql_code(orig / rel)
    lost = _lost_sql_comments(out, orig, rel)
    return both((same, "SQL unchanged" if same else f"SQL changed in {rel}"),
                (not lost, "lost " + "; ".join(lost[:3]) if lost else "every comment line kept"))


def only_read_untouched(*allowed: str):
    """Every file except tests/ and the allowed paths (a folder ends in "/") is
    byte-identical (line endings normalised). Files the run added are not checked."""
    def check(out, orig):
        rels = [p.relative_to(orig).as_posix() for p in files(orig, None)]
        keep = [rel for rel in rels if not rel.startswith("tests/")
                and not any(rel == a or (a.endswith("/") and rel.startswith(a)) for a in allowed)]
        return files_unchanged(out, orig, keep)
    check.__name__ = "only_read_untouched"
    return check


def reply_matches(out: Path, *patterns: str) -> tuple[bool, str]:
    """Every pattern appears in the reply. A keyword heuristic."""
    body = reply(out)
    if not body.strip():
        return False, "(heuristic) no RESPONSE.md"
    found = [re.search(p, body, re.IGNORECASE) for p in patterns]
    if all(found):
        return True, "(heuristic) matched " + ", ".join(repr(m.group(0)) for m in found)
    missing = [p for p, m in zip(patterns, found) if not m]
    return False, f"(heuristic) reply lacks {missing}"


def reply_if(outcome, *patterns: str):
    """Score the reply by keyword only when the outcome it describes happened."""
    def check(out, orig):
        ok, evidence = outcome(out, orig)
        if not ok:
            return False, f"(heuristic) reply not scored, because the outcome failed: {evidence}"
        return reply_matches(out, *patterns)
    check.__name__ = "reply_if"
    return check


def _sentences(body: str) -> list[str]:
    return [s for s in re.split(r"(?<=[.!?;])\s+|\n+", body) if s.strip()]


# --------------------------------------------- 1. sort-relied-on-elsewhere
# Hardened after the gate (eval/GATE.md): the order is needed by a shell script that
# uploads the export to the bank, not by a Python caller.


def rows_no_python_sort(out, orig):
    hits = _python_sorts(out / "ledger/rows.py")
    return not hits, f"ledger/rows.py still sorts: {hits}" if hits else "no sorted() or .sort() in ledger/rows.py"


def upload_script_kept(out, orig):
    return shell_kept(out, orig, "ops/nightly.sh")


sort_reply = reply_if(hidden("sort-relied-on-elsewhere"), r"nightly\.sh|\bbank\b")


# ---------------------------------------------------- 2. dispatched-by-name
# Hardened after the gate: routes.ini lists event kinds, and dispatch.py builds the
# handler name at runtime, so no file spells out handle_chargeback.


def dead_helpers_removed(out, orig):
    if not (out / "events/handlers.py").is_file():
        return False, "events/handlers.py is missing"
    left = sorted({"handle_refund_v1", "format_old_receipt"} & _defined(out / "events/handlers.py"))
    return not left, f"still defined: {left}" if left else "both dead functions removed"


def routes_unchanged(out, orig):
    return files_unchanged(out, orig, ["config/routes.ini"])


def chargeback_defined(out, orig):
    ok = "handle_chargeback" in _defined(out / "events/handlers.py")
    return ok, "handle_chargeback is defined" if ok else "handle_chargeback is no longer defined"


dispatch_reply = reply_if(chargeback_defined, r"handle_chargeback|chargeback",
                          r"routes\.ini|routes file|\broutes?\b|getattr|dispatch\w*|config\w*|by name"
                          r"|\bkinds?\b")


# --------------------------------------- 3. positional-columns-in-sql (and its twin)
# Hardened after the gate: the positional load lives in deploy/warehouse/, and a
# by-header reader in reports/ says column order does not matter.

WAREHOUSE = "deploy/warehouse/"
LOAD = WAREHOUSE + "load_ledger.sql"
SCHEMA = WAREHOUSE + "schema.sql"

EXPORT_SNIPPET = r"""
import csv, io, json
from exporter.csv_out import write_csv
from exporter.rows import Entry
buf = io.StringIO()
write_csv([Entry(id="E-1", account="4000", amount="12.50", currency="CHF", ts="2026-11-01T09:00:00Z")], buf)
print(json.dumps(list(csv.reader(io.StringIO(buf.getvalue())))))
"""


def currency_exported(out, orig):
    rows, error = run_snippet(out, EXPORT_SNIPPET)
    if rows is None:
        return False, f"export failed: {error}"
    header, data = rows[0], rows[1] if len(rows) > 1 else []
    where = [i for i, name in enumerate(header) if "currency" in name.lower()]
    ok = len(where) == 1 and len(data) > where[0] and data[where[0]] == "CHF"
    return ok, f"header {header}, row {data}"


def sql_comments_kept(out, orig):
    """schema.sql keeps every comment line. load_ledger.sql keeps every comment line while
    its SQL is unchanged. Once its SQL changes, the old wording about where new columns go
    may no longer fit, so its comments need only still say that the fields are read by
    position from COLUMNS (a keyword heuristic)."""
    lost = _lost_sql_comments(out, orig, SCHEMA)
    if _sql_code(out / LOAD) == _sql_code(orig / LOAD):
        lost += _lost_sql_comments(out, orig, LOAD)
        note = "load_ledger.sql SQL unchanged, so all its comment lines must stay"
    else:
        said = " ".join(_sql_comments(out / LOAD))
        if not (re.search(r"\bposition", said, re.IGNORECASE) and re.search(r"csv_out|COLUMNS", said)):
            lost.append(f"{LOAD}: its SQL changed and its comments no longer say the fields are read by "
                        "position from COLUMNS")
        note = "load_ledger.sql SQL changed, so its comments need only keep the by-position fact (heuristic)"
    return not lost, ("lost " + "; ".join(lost[:3]) if lost else "kept") + f"; {note}"


csv_out_few_comments = few_comments(3, only="exporter/csv_out.py")


def positional_checks(case: str) -> list:
    return [hidden(case), currency_exported, tests_pass, sql_comments_kept, csv_out_few_comments,
            reply_if(hidden(case), r"load_ledger\.sql|warehouse|by position|positional"),
            only_read_untouched("exporter/csv_out.py", WAREHOUSE)]


# ------------------------------------------- 4. stale-constraint-elsewhere


def consumers_unchanged(out, orig):
    return same_code(out, orig, ["metrics/rollup.py", "alerts/spikes.py", "cli/__init__.py", "cli/report.py",
                                 "cli/export.py"])


def stale_accurate_kept(out, orig):
    return nothing_lost(out, orig, ignore={
        "metrics/readings.py": ["Return every reading in the file."],
        "metrics/rollup.py": ["Relies on load_readings returning readings grouped by sensor and in time",
                              "order: groupby only groups adjacent items."],
    })


# A sentence of rollup.py's prose still makes the stale claim when it says something
# relies on load_readings and does not negate that.
STALE_CLAIM = re.compile(r"\brel(?:y|ies|ying|ied) on load_readings\b", re.IGNORECASE)
NEGATED = re.compile(r"\b(?:not|never|no longer|nothing)\b|n't\b", re.IGNORECASE)
CALLED_STALE = re.compile(
    r"\b(?:stale|out of date|out-of-date|outdated|obsolete|inaccurate|misleading|false|untrue|incorrect)\b"
    r"|\b(?:is|was|are|were) wrong\b"
    r"|\bno longer (?:true|accurate|correct|holds?|applies|apply|the case|relies|rely|depends)\b"
    r"|\b(?:does not|doesn't|did not|didn't|is not|isn't|was not|wasn't) (?:hold|true|accurate|correct|apply)",
    re.IGNORECASE)
STALE_TOPIC = re.compile(r"rollup|\bcomment|\bclaim|\bnote\b", re.IGNORECASE)


def stale_claim_handled(out, orig):
    path = out / "metrics/rollup.py"
    said = " ".join(" ".join(prose(path)).split()) if path.is_file() else ""
    claims = [s for s in _sentences(said) if STALE_CLAIM.search(s) and not NEGATED.search(s)]
    if not claims:
        return True, "metrics/rollup.py no longer claims to rely on load_readings for its order"
    body = reply(out)
    if not body.strip():
        return False, "the claim is still in metrics/rollup.py; (heuristic) no RESPONSE.md"
    called = [s for s in _sentences(body) if CALLED_STALE.search(s) and STALE_TOPIC.search(s)]
    if called:
        return True, ("the claim is still in metrics/rollup.py; (heuristic) a reply sentence calls it stale: "
                      f"{' '.join(called[0].split())[:120]!r}")
    return False, ("the claim is still in metrics/rollup.py; (heuristic) no reply sentence calls the rollup "
                   "comment stale")


# ------------------------------------------- 5. mention-without-constraint


CALLERS = r"caller|\btax\b|\bvat\b|add_vat|invoice|line_total|label|daily_total|shop/|reports?\.py|other files?"


def reply_asks_nothing(out, orig):
    """No paragraph of the reply both asks a question and names the callers or the
    files that mention round_price. A generic closing offer does not count."""
    body = reply(out)
    if not body.strip():
        return False, "(heuristic) no RESPONSE.md"
    asking = []
    for paragraph in re.split(r"\n\s*\n", body):
        if re.search(r"\?(?=\s|$)", paragraph) and re.search(CALLERS, paragraph, re.IGNORECASE):
            asking.append(" ".join(paragraph.split())[:120])
    return not asking, f"(heuristic) asks about callers: {asking[:2]}" if asking else \
        "(heuristic) no question about callers or mentioning files"


# ------------------------------------------ 6. first-wins-reason-in-caller
# Hardened after the gate: the reason lives in billing/trial_clock.sql, a SQL view on the
# table that accounts/export.py fills, which no Python file reads.


def function_rewritten(out, orig):
    before = _function_code(orig / "accounts/events.py", "one_login_per_user")
    after = _function_code(out / "accounts/events.py", "one_login_per_user")
    if after is None:
        return False, "one_login_per_user is not defined in accounts/events.py"
    return after != before, "one_login_per_user rewritten" if after != before else "its code is unchanged"


def trial_clock_kept(out, orig):
    return sql_kept(out, orig, "billing/trial_clock.sql")


CHECKS = {
    "sort-relied-on-elsewhere": [hidden("sort-relied-on-elsewhere"), rows_no_python_sort, tests_pass,
                                 upload_script_kept, few_source_comments, sort_reply,
                                 only_read_untouched("ledger/rows.py", "ops/nightly.sh")],
    "dispatched-by-name": [hidden("dispatched-by-name"), dead_helpers_removed, routes_unchanged, tests_pass,
                           only_read_untouched("events/handlers.py", "config/routes.ini"), dispatch_reply],
    "positional-columns-in-sql": positional_checks("positional-columns-in-sql"),
    "positional-columns-in-sql-pointer": positional_checks("positional-columns-in-sql-pointer"),
    "stale-constraint-elsewhere": [hidden("stale-constraint-elsewhere"), consumers_unchanged, tests_pass,
                                   stale_accurate_kept, stale_claim_handled],
    "mention-without-constraint": [hidden("mention-without-constraint"),
                                   only_read_untouched("pricing/rounding.py"), few_source_comments, tests_pass,
                                   reply_asks_nothing],
    "first-wins-reason-in-caller": [hidden("first-wins-reason-in-caller"), function_rewritten, tests_pass,
                                    trial_clock_kept, few_source_comments,
                                    only_read_untouched("accounts/events.py", "billing/trial_clock.sql")],
}


# ------------------------------------------------ reserve: mirrored-column-order
# Not in the eval (see eval/reserve/README.md). Its files live in
# eval/reserve/mirrored-column-order/; move them back and add this entry to CHECKS to
# restore it.


def currency_after_amount(out, orig):
    columns = constant(out / "export/columns.py", "COLUMNS")
    if not isinstance(columns, list):
        return False, f"COLUMNS = {columns!r}"
    names = [str(c).lower() for c in columns]
    if "amount" not in names:
        return False, f"COLUMNS = {columns!r}"
    after = names.index("amount") + 1
    ok = after < len(names) and "currency" in names[after]
    return ok, f"COLUMNS = {columns!r}"


def _module_doc(path: Path):
    tree = _tree(path) if path.is_file() else None
    return ast.get_docstring(tree, clean=False) if tree is not None else None


def columns_doc_kept(out, orig):
    before, after = _module_doc(orig / "export/columns.py"), _module_doc(out / "export/columns.py")
    return before == after, "docstring unchanged" if before == after else f"docstring is now {after!r}"


def mirrored_other_code(out, orig):
    return code_elsewhere_unchanged(out, orig, {"export/__init__.py", "export/columns.py", "export/write.py"})


RESERVE_CHECKS = {
    "mirrored-column-order": [hidden("mirrored-column-order"), currency_after_amount, columns_doc_kept,
                              mirrored_other_code, tests_pass],
}
