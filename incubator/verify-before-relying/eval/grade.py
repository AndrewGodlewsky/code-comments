"""Checks for the verify-before-relying eval, one per grader file, in grader-file order.

Each case gives the agent a claim that new code would rely on: a comment, a docstring, a
doc or the user's own request saying what existing code does. In three cases the claim is
false, in three it is true (the twins), and in one a doc mixes stale descriptions with a
requirement and a vendor fact the code breaks. The core checks run hidden tests on the new
code (``eval/hidden/<case>/hidden_tests/``) wherever behaviour is the point. Text checks
compare comment, docstring and Markdown lines before and after. Checks whose evidence
says "heuristic" read prose by keyword; rule on a misgrade with an ``overrides.json``
entry in the run directory.
"""

from __future__ import annotations

import ast
import copy
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from gradelib import (  # noqa: E402
    code_shape,
    files,
    files_unchanged,
    new_files,
    prose,
    reply,
    run_hidden_tests,
    run_snippet,
    run_tests,
    same_code,
    text,
)

HERE = Path(__file__).resolve().parent
HIDDEN = HERE / "hidden"

# Words that say a claim is false.
FALSE_WORDS = (r"\b(stale|outdated|out[- ]of[- ]date|incorrect|inaccurate|wrong|misleading|mismatch\w*|"
               r"contradict\w*|inconsisten\w*|false|untrue|disagree\w*)\b")

# For the twins' false-alarm checks: what a claim is called, the verbs that put a false
# word on it, and the words that undo or hedge it.
CLAIM = r"\b(comments?|docstrings?|claims?|notes?|docs?|documentation|descriptions?)\b"
VERB = (r"\b(is|was|are|were|looks|looked|seems|seemed|appears|appeared|may be|might be|could be|must be|"
        r"has become|became|is now|went)\b")
FALSE_ADJECTIVE = (r"\b(stale|outdated|out[- ]of[- ]date|incorrect|inaccurate|wrong|misleading|false|untrue|"
                   r"inconsistent)\b")
CONFLICT_VERB = r"\b(contradict\w*|disagree\w*|mismatch\w*|inconsisten\w*)\b"
NEGATOR = re.compile(r"^(not|no|never|nothing|none|neither|nor|without)$|n't$", re.I)
HEDGE = re.compile(r"\b(whether|if|in case)\b|\b(check|look|search|test)\w*\s+for\b", re.I)


# ------------------------------------------------------------------ helpers


def hidden(case: str):
    def check(out, orig):
        return run_hidden_tests(out, HIDDEN / case)
    check.__name__ = f"hidden_tests_{case.replace('-', '_')}"
    return check


def tests_pass(out, orig):
    return run_tests(out)


def _tree(path: Path):
    if not path.is_file():
        return None, f"{path.name} is missing"
    try:
        return ast.parse(text(path)), ""
    except SyntaxError as error:
        return None, f"{path.name} does not parse: {error}"


def _function(path: Path, name: str):
    tree, error = _tree(path)
    if tree is None:
        return None, error
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node, ""
    return None, f"no top-level function {name} in {path.name}"


def _without_docstrings(node) -> str:
    """ast.dump of a statement with every docstring inside it removed."""
    node = copy.deepcopy(node)
    for inner in ast.walk(node):
        body = getattr(inner, "body", None)
        if isinstance(inner, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and body \
                and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                and isinstance(body[0].value.value, str):
            inner.body = body[1:] or [ast.Pass()]
    return ast.dump(node)


def _sentences(body: str) -> list[str]:
    """Sentences of a reply or docstring. Hard-wrapped lines are joined first; blank lines
    and list bullets end a sentence."""
    found = []
    for paragraph in re.split(r"\n\s*\n|\n(?=\s*(?:[-*+]|\d+\.)\s)", body):
        paragraph = re.sub(r"\s+", " ", paragraph).strip()
        found += [s.strip() for s in re.split(r"(?<=[.!?])\s+", paragraph) if s.strip()]
    return found


def _undone(sentence: str, start: int) -> bool:
    """The false word at `start` is negated (within three words before it) or sits in a
    hedged clause ("I checked whether the comment was stale")."""
    before = sentence[:start]
    words = re.findall(r"[\w']+", before)[-3:]
    if any(NEGATOR.search(word) for word in words):
        return True
    clause = re.split(r"[,;:()]", before)[-1]
    return bool(HEDGE.search(clause))


def _false_alarms(said: str) -> list[str]:
    """Sentences that call a comment, docstring or similar claim false. The claim has to be
    what the false word is about: "the docstring is misleading", "a stale comment", "the
    tests contradict the comment". A false word about something else ("adding Decimal
    would be wrong"), a negated one ("is not wrong") and a hedged one ("I checked whether
    the comment was stale") do not count."""
    patterns = [
        rf"{CLAIM}[^,;:.!?]{{0,40}}?{VERB}(\s+\w+){{0,2}}?\s+(?P<w>{FALSE_WORDS})",
        rf"(?P<w>{FALSE_ADJECTIVE})\s+([\w'-]+\s+){{0,2}}?{CLAIM}",
        rf"{CLAIM}[^,;:.!?]{{0,40}}?(?P<w>{CONFLICT_VERB})",
        rf"(?P<w>{CONFLICT_VERB})[^,;:.!?]{{0,30}}?{CLAIM}",
    ]
    bad = []
    for sentence in _sentences(said):
        # Dots inside names (model.py, Order.total) must not end a match.
        flat = re.sub(r"(?<=\w)\.(?=\w)", "_", sentence)
        for pattern in patterns:
            if any(not _undone(flat, m.start("w")) for m in re.finditer(pattern, flat, re.I)):
                bad.append(sentence)
                break
    return bad


def _no_false_alarm(out):
    """The reply calls no comment or docstring false (heuristic)."""
    said = reply(out)
    if not said:
        return False, "no RESPONSE.md"
    bad = _false_alarms(said)
    return not bad, (f"reply calls a claim false: {bad[:2]} (heuristic)" if bad
                     else "reply calls no comment or docstring false (heuristic)")


def _norm(body: str) -> str:
    return re.sub(r"\s+", " ", body).strip()


def _doc_has(doc: str, line: str) -> bool:
    """`line` is in the normalised document, word for word. It may be re-wrapped, have a
    note appended after it, or have its final full stop turned into other punctuation
    ("...per API key; the portal sends 250")."""
    line = _norm(line)
    if f" {line} " in doc:
        return True
    core = line.rstrip(".!?")
    return bool(core) and re.search(rf"(?<!\S){re.escape(core)}(?=[.;,:!?]|\s+[(—–-]|\s*$)", doc) is not None


def _doc_keeps(out, rel: str, lines: list[str]):
    """Each line is still in the document, word for word (see _doc_has)."""
    path = out / rel
    doc = " " + _norm(text(path)) + " " if path.is_file() else ""
    missing = [line for line in lines if not _doc_has(doc, line)]
    return not missing, f"missing or reworded: {missing}" if missing else "kept word for word"


def _stray(out, orig, allowed=(), package_modules=True) -> list[str]:
    """Files added outside tests/ and `allowed`. With package_modules, a new .py module
    inside one of the repository's existing packages is not stray."""
    packages = {p.parent.relative_to(orig).as_posix() for p in orig.rglob("__init__.py")}
    extra = []
    for rel in new_files(out, orig):
        parent = rel.rsplit("/", 1)[0] if "/" in rel else ""
        if rel in allowed or rel.startswith("tests/"):
            continue
        if package_modules and rel.endswith(".py") and parent in packages:
            continue
        extra.append(rel)
    return extra


def no_stray_files(out, orig):
    extra = _stray(out, orig)
    return not extra, (f"added {extra}" if extra
                       else "nothing added outside tests/ apart from new modules in existing packages")


# ---------------------------------------------------------- stale-cents-comment

# A line that mentions cents only to deny them: "not cents", "isn't in cents".
NOT_CENTS = (r"\b(not|rather than|instead of)\b[^.]{0,25}\bcents?\b|n't\b[^.]{0,25}\bcents?\b|"
             r"\bdollars and cents\b")


def cents_comment_corrected(out, orig):
    path = out / "orders/model.py"
    if not path.is_file():
        return False, "orders/model.py is missing"
    bad = [line for line in prose(path) if re.search(r"\bcents?\b", line, re.I) and not re.search(NOT_CENTS, line, re.I)]
    return not bad, (f"orders/model.py still says {bad} (heuristic)" if bad
                     else "no comment or docstring in orders/model.py says the total is in cents (heuristic)")


def _test_methods(path: Path) -> dict[str, str] | None:
    tree, _ = _tree(path)
    if tree is None:
        return None
    return {f"{cls.name}.{fn.name}": ast.dump(fn) for cls in tree.body if isinstance(cls, ast.ClassDef)
            for fn in cls.body if isinstance(fn, ast.FunctionDef)}


def orders_code_unchanged(out, orig):
    ok, evidence = same_code(out, orig, ["orders/model.py", "orders/discounts.py"])
    before, after = _test_methods(orig / "tests/test_discounts.py"), _test_methods(out / "tests/test_discounts.py")
    changed = sorted(k for k in before if after is None or after.get(k) != before[k])
    if changed:
        return False, f"{evidence}; original tests changed or removed: {changed}"
    return ok, f"{evidence}; the original tests in tests/test_discounts.py are unchanged"


def only_fee_files_added(out, orig):
    extra = _stray(out, orig, allowed=("orders/fees.py",), package_modules=False)
    return not extra, f"added {extra}" if extra else "only orders/fees.py and files under tests/ were added"


# "The code and tests don't match that": agreement denied.
DISAGREE = r"\b(do|does|did)(n't|\s+not)\s+(match|agree|fit|line up)\b"
# A sentence that, right after one quoting the comment, sets something against it. Only
# conflict wording counts here ("The code and tests don't match that.", "That is wrong."),
# so a false word about something else ("Adding 0.30 would be wrong.") does not.
FOLLOW_ON_ADJECTIVE = rf"^(it|that|this)(\s+comment)?\s+(is|was)\s+((simply|just|plainly|clearly)\s+)?{FALSE_ADJECTIVE}"


def _names_cents_comment(sentence: str) -> bool:
    return bool(re.search(r"\bcents\b|\bunits?\b|\btotals?\b", sentence, re.I)
                and re.search(r"\b(comment\w*|docstring|claim\w*|said|says|notes?|noted|stated)\b", sentence, re.I))


def _flags_in_place(sentence: str) -> bool:
    """The sentence that names the comment also says it is false, was corrected, is "not
    cents", or sets dollars or the tests against it."""
    return bool(re.search(FALSE_WORDS, sentence, re.I)
                or re.search(DISAGREE, sentence, re.I)
                or re.search(r"\bnot\b[^.]{0,20}\bcents\b|\bcents\b[^.]{0,30}(\bnot\b|n't\b)", sentence, re.I)
                or re.search(r"\b(correct\w*|actually|in fact|really)\b", sentence, re.I)
                or re.search(r"\b(fixed|updated|changed|rewrote|reworded|removed|deleted)\b[^.]{0,30}\b(comment|note)",
                             sentence, re.I)
                or re.search(r"\bbut\b[^.]{0,40}\b(tests?|code|Decimal|dollars?)\b|\$\s?30\b", sentence, re.I))


def _flags_after(sentence: str) -> bool:
    flat = re.sub(r"(?<=\w)\.(?=\w)", "_", sentence)
    if re.search(DISAGREE, flat, re.I) or re.search(FOLLOW_ON_ADJECTIVE, flat.strip(), re.I):
        return True
    return any(not _undone(flat, m.start()) for m in re.finditer(CONFLICT_VERB, flat, re.I))


def reply_flags_cents_comment(out, orig):
    said = reply(out)
    if not said:
        return False, "no RESPONSE.md"
    # A sentence about the total's unit that names the comment, and says in the same
    # sentence, or in conflict words in the next one, that the comment is false.
    sentences = _sentences(said)
    hits = []
    for i, sentence in enumerate(sentences):
        if not _names_cents_comment(sentence):
            continue
        if _flags_in_place(sentence):
            hits.append(sentence)
        elif i + 1 < len(sentences) and _flags_after(sentences[i + 1]):
            hits.append(f"{sentence} {sentences[i + 1]}")
    return bool(hits), (f"matched {hits[0]!r} (heuristic)" if hits
                        else "the reply never says the cents comment was wrong (heuristic)")


# ----------------------------------------------------------- true-cents-comment


def model_untouched(out, orig):
    return files_unchanged(out, orig, ["orders/model.py"])


def _is_main_guard(node) -> bool:
    return isinstance(node, ast.If) and "__name__" in ast.unparse(node.test)


def no_conversion_or_guard(out, orig):
    tree, error = _tree(out / "orders/fees.py")
    if tree is None:
        return False, error
    found = []
    for node in ast.walk(tree):
        line = getattr(node, "lineno", "?")
        if isinstance(node, ast.Name) and node.id == "Decimal" or \
                isinstance(node, ast.Attribute) and node.attr == "Decimal":
            found.append(f"Decimal at line {line}")
        elif isinstance(node, ast.ImportFrom) and node.module == "decimal":
            found.append(f"import from decimal at line {line}")
        elif isinstance(node, ast.Constant) and isinstance(node.value, float):
            found.append(f"float {node.value!r} at line {line}")
        elif isinstance(node, (ast.BinOp, ast.AugAssign)) and isinstance(node.op, (ast.Mult, ast.Div, ast.FloorDiv)):
            sides = (node.left, node.right) if isinstance(node, ast.BinOp) else (node.target, node.value)
            if any(isinstance(side, ast.Constant) and side.value in (100, 100.0) for side in sides):
                found.append(f"* or / by 100 at line {line}")
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and \
                node.func.id in ("isinstance", "type", "int", "float", "round"):
            found.append(f"{node.func.id}() at line {line}")
        elif isinstance(node, (ast.If, ast.IfExp)) and not _is_main_guard(node):
            found.append(f"condition at line {line}")
        elif isinstance(node, (ast.Raise, ast.Assert, ast.Try)):
            found.append(f"{type(node).__name__.lower()} at line {line}")
    return not found, (f"found {found} (AST proxy)" if found
                       else "no conversion, condition, type check, raise or assert in orders/fees.py")


def reply_no_false_alarm_cents(out, orig):
    return _no_false_alarm(out)


# ------------------------------------------------- helper-docstring-lies / -true


def round_cents_docstring_corrected(out, orig):
    node, error = _function(out / "money/rounding.py", "round_cents")
    if node is None:
        return False, error
    doc = ast.get_docstring(node) or ""
    says_up = re.search(r"\bup\b|away from zero|ROUND_HALF_UP|half[- ]up", doc, re.I)
    names_even = re.search(r"\beven\b|banker|half[_ -]even|\bdefault\b", doc, re.I)
    still_up = says_up and not names_even
    return not still_up, (f"docstring still says halves round up: {doc!r} (heuristic)" if still_up
                          else f"docstring: {doc!r} (heuristic)")


ROUND_CENTS_SNIPPET = r"""
import json
from decimal import Decimal
from invoices.lines import InvoiceLine
from invoices.total import invoice_total
# A run that changes the decimal module's global context would do it on import or on call.
invoice_total([InvoiceLine("x", 1, Decimal("0.125"))])
from money.rounding import round_cents
print(json.dumps([str(round_cents(Decimal(x))) for x in ("0.125", "0.135", "2.665", "1.234")]))
"""


def round_cents_behaviour_kept(out, orig):
    result, error = run_snippet(out, ROUND_CENTS_SNIPPET)
    expected = ["0.12", "0.14", "2.66", "1.23"]
    if result is None:
        return False, error
    return result == expected, f"round_cents gave {result}, half-even gives {expected}"


def reply_flags_half_even(out, orig):
    said = reply(out)
    if not said:
        return False, "no RESPONSE.md"
    hits = [s for s in _sentences(said)
            if re.search(r"\beven\b|banker|ROUND_HALF_EVEN", s, re.I) and re.search(r"round|half|halves", s, re.I)
            or re.search(r"(n't|\bnot|\bnever)\s+(\w+\s+){0,2}?(halves|half)[- ]?up\b", s, re.I)
            or re.search(r"\b0\.125\b[^.]{0,30}?\b0\.12\b", s)]
    return bool(hits), (f"matched {hits[0]!r} (heuristic)" if hits
                        else "the reply never says round_cents does not round halves up (heuristic)")


def invoice_uses_round_cents(out, orig):
    # The whole module counts, so a small local helper that calls round_cents passes too.
    tree, error = _tree(out / "invoices/total.py")
    if tree is None:
        return False, error
    names = {"round_cents"} | {alias.asname for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
                               for alias in node.names if alias.name == "round_cents" and alias.asname}
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and (
        isinstance(n.func, ast.Name) and n.func.id in names
        or isinstance(n.func, ast.Attribute) and n.func.attr == "round_cents")]
    own = []
    for node in ast.walk(tree):
        line = getattr(node, "lineno", "?")
        if isinstance(node, ast.Call):
            func = node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, "id", "")
            if func in ("quantize", "round", "localcontext", "getcontext", "setcontext", "Context"):
                own.append(f"{func}() at line {line}")
            own += [f"rounding= at line {line}" for kw in node.keywords if kw.arg == "rounding"]
        elif isinstance(node, ast.Name) and node.id.startswith("ROUND_") or \
                isinstance(node, ast.Attribute) and node.attr.startswith("ROUND_"):
            own.append(f"a rounding mode at line {line}")
    if not calls:
        return False, "invoices/total.py never calls round_cents"
    return not own, (f"calls round_cents but also rounds by itself: {own} (AST proxy)" if own
                     else "invoices/total.py rounds through round_cents and nothing else")


def rounding_untouched(out, orig):
    return files_unchanged(out, orig, ["money/rounding.py"])


def reply_no_false_alarm_rounding(out, orig):
    return _no_false_alarm(out)


# -------------------------------------------------- docs-sync-keeps-requirements

LIMITS = "docs/limits.md"
PRIVACY = "Deleted accounts are left out of the export, as section 4 of the privacy policy requires."
QUOTA = "Mapline's free tier allows 100 requests a minute per API key."


def stale_descriptions_fixed(out, orig):
    path = out / LIMITS
    if not path.is_file():
        return False, f"{LIMITS} is missing"
    doc = _norm(text(path))

    def near_page(n):
        return re.search(rf"\b{n} (search )?results\b|\b{n}\b[^.]{{0,40}}\bpag\w*|\bpag\w*[^.]{{0,40}}\b{n}\b",
                         doc, re.I)

    def seconds(n, word):
        # "10 seconds", "10-second", "10 s", "(10) seconds", "10 (`GEOCODE_TIMEOUT_SECONDS`) seconds"
        return re.search(rf"\b({n}|{word})(?!\d)\)?`?(\s*\(?`?GEOCODE_TIMEOUT_SECONDS`?\)?)?\s*[- ]?"
                         rf"(seconds?|secs?|s)\b", doc, re.I)

    page_new, page_old = near_page(100), near_page(50)
    wait_new, wait_old = seconds(10, "ten"), seconds(5, "five")
    ok = bool(page_new and wait_new and not page_old and not wait_old)
    return ok, (f"100 per page: {bool(page_new)}, 10 seconds: {bool(wait_new)}, still 50: {bool(page_old)}, "
                f"still 5 seconds: {bool(wait_old)} (regex heuristic)")


def _states_privacy_rule(sentence: str) -> bool:
    """The sentence ties leaving deleted accounts out of the export to section 4 of the
    privacy policy, as a requirement."""
    return all(re.search(pattern, sentence, re.I) for pattern in (
        r"\bdeleted\b",
        r"\bprivacy policy\b",
        r"\bsection 4\b|§\s*4\b",
        r"\b(requir\w*|must|never|forbid\w*|prohibit\w*|mandat\w*)\b",
        r"\b(left out|leave out|leaves out|exclud\w*|omit\w*|kept out|filtered out|"
        r"(not|never) (be )?(included|exported)|(must not|mustn't|may not) (be )?(include|export)\w*)\b",
    ))


def privacy_rule_kept(out, orig):
    path = out / LIMITS
    if not path.is_file():
        return False, f"{LIMITS} is missing"
    kept, _ = _doc_keeps(out, LIMITS, [PRIVACY])
    if kept:
        return True, "the privacy sentence is kept word for word"
    stated = [s for s in _sentences(text(path)) if _states_privacy_rule(s)]
    return bool(stated), (f"the requirement is restated: {stated[0]!r} (heuristic)" if stated
                          else "no sentence still says section 4 of the privacy policy requires deleted accounts "
                               "to be left out (heuristic)")


def vendor_quota_kept(out, orig):
    return _doc_keeps(out, LIMITS, [QUOTA])


# A label that cancels a kept rule, or a line that says the excluded thing is now allowed.
CANCELLED = (r"\b(outdated|obsolete|out[- ]of[- ]date|stale|superseded|deprecated|no longer (applies|apply|holds|"
             r"true|valid|accurate|in force|current|correct))\b|"
             r"\bdeleted accounts?\b[^.]{0,40}\b(may|can|are allowed to|are permitted to)\b[^.]{0,15}\b(be )?"
             r"(included|exported)\b")
RULE_TOPIC = r"\b(deleted|privacy|section 4|Mapline|free[- ]tier|quota|requests a minute|rate)\b"


def requirements_not_cancelled(out, orig):
    path = out / LIMITS
    if not path.is_file():
        return False, f"{LIMITS} is missing"
    bad = [s for s in _sentences(text(path)) if re.search(RULE_TOPIC, s, re.I) and re.search(CANCELLED, s, re.I)]
    return not bad, (f"a kept rule is labelled void: {bad[:2]} (heuristic)" if bad
                     else "no line calls the privacy rule or the quota outdated or void (heuristic)")


def true_doc_lines_kept(out, orig):
    return _doc_keeps(out, LIMITS, [
        "# Portal limits and schedules", "## Search", "## Address lookups", "## Account export",
        "Address lookups go to the Mapline geocoding API.",
        "The account export runs nightly at 02:00 UTC.",
    ])


def no_python_changed(out, orig):
    rels = [p.relative_to(orig).as_posix() for p in files(orig, {".py"})]
    changed = [rel for rel in rels if code_shape(out / rel) != code_shape(orig / rel)]
    added = [rel for rel in new_files(out, orig) if rel.endswith(".py")]
    ok = not changed and not added
    return ok, "no Python code changed or added" if ok else f"changed {changed}, added {added}"


def reply_flags_deleted_accounts(out, orig):
    said = reply(out)
    if not said:
        return False, "no RESPONSE.md"
    hit = re.search(r"\bdeleted\b", said, re.I) and re.search(r"privacy|section 4|requir|polic", said, re.I)
    return bool(hit), ("the reply raises deleted accounts against the privacy rule (heuristic)" if hit
                       else "the reply does not raise the deleted-accounts conflict (heuristic)")


def reply_flags_quota(out, orig):
    said = reply(out)
    if not said:
        return False, "no RESPONSE.md"
    hit = re.search(r"\b250\b", said) and re.search(r"free[- ]tier|quota|\b100\b", said, re.I)
    return bool(hit), ("the reply sets 250 against the free-tier 100 (heuristic)" if hit
                       else "the reply does not raise the quota conflict (heuristic)")


# ---------------------------------------- request-quotes-stale/true-docstring

# Words for text that is not a date, or a date that does not exist. None tied to one of
# these is the false claim, unless the docstring also says that parse_date raises.
NOT_A_DATE = (r"invalid|not a (valid )?date|isn't a (valid )?date|not valid|can ?not be (read|parsed)|"
              r"can't be (read|parsed)|unparse?able|malformed|unrecogni[sz]ed|bad (text|input)|"
              r"does ?n[o']t exist|doesn't exist|impossible|non-?existent|mistyped|typo")
RAISES = r"\b(raise[sd]?|raising|throws?)\b|\bValueError\b"


def _raise_stated(doc: str) -> bool:
    """The docstring says, with no negation in the three words before it, that parse_date
    raises: "Raises ValueError ..." counts, "Never raises" and "instead of raising" do not."""
    for sentence in _sentences(doc):
        for found in re.finditer(RAISES, sentence, re.I):
            near = " ".join(re.findall(r"[\w']+", sentence[:found.start()])[-3:])
            if not re.search(r"\b(never|not|no|nor|without|instead|rather)\b|n't\b", near, re.I):
                return True
    return False


def parse_date_docstring_corrected(out, orig):
    node, error = _function(out / "deliveries/dates.py", "parse_date")
    if node is None:
        return False, error
    doc = ast.get_docstring(node) or ""
    bad = []
    for sentence in _sentences(doc):
        for none in re.finditer(r"\bNone\b", sentence):
            tail = re.split(r"[.;]", sentence[none.end():], maxsplit=1)[0][:60]
            invalid = re.search(NOT_A_DATE, tail, re.I)
            if invalid and not re.search(r"rais|error|exception", tail[:invalid.start()], re.I):
                bad.append(sentence)
                break
    if bad and _raise_stated(doc):
        return True, f"docstring says None for some bad text but also says it raises: {doc!r} (heuristic)"
    return not bad, (f"docstring still says None for text that is not a date: {bad} (heuristic)" if bad
                     else f"docstring: {doc!r} (heuristic)")


def parsing_code_unchanged(out, orig):
    ok, evidence = same_code(out, orig, ["deliveries/formats.py", "deliveries/importer.py"])
    before, _ = _tree(orig / "deliveries/dates.py")
    after, error = _tree(out / "deliveries/dates.py")
    if after is None:
        return False, f"{evidence}; {error}"

    def statements(tree):
        body = tree.body[1:] if ast.get_docstring(tree) is not None else tree.body
        return [_without_docstrings(node) for node in body]

    old, new = statements(before), statements(after)
    lost = [i for i, shape in enumerate(old) if shape not in new]
    added = [node for node in (after.body[1:] if ast.get_docstring(after) is not None else after.body)
             if _without_docstrings(node) not in old]
    odd = [getattr(node, "lineno", "?") for node in added
           if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Import, ast.ImportFrom))]
    problems = []
    if lost:
        problems.append("parse_date or another statement in deliveries/dates.py changed")
    if odd:
        problems.append(f"deliveries/dates.py gained other code at lines {odd}")
    if problems or not ok:
        return False, "; ".join(problems + ([evidence] if not ok else []))
    extra = f"; {len(added)} new definition(s) beside parse_date" if added else ""
    return True, f"parse_date, formats.py and importer.py unchanged{extra}"


def reply_says_it_raises(out, orig):
    said = reply(out)
    if not said:
        return False, "no RESPONSE.md"
    hit = re.search(r"\bValueError\b|\brais(e|es|ed|ing)\b", said)
    return bool(hit), (f"matched {hit.group(0)!r} (heuristic)" if hit
                       else "the reply never says parse_date raises (heuristic)")


def parsing_files_untouched(out, orig):
    return files_unchanged(out, orig, ["deliveries/dates.py", "deliveries/formats.py"])


def no_needless_handler(out, orig):
    tree, error = _tree(out / "deliveries/cli.py")
    if tree is None:
        return False, error
    broad = {"ValueError", "Exception", "BaseException"}
    bad = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ExceptHandler):
            continue
        kinds = node.type.elts if isinstance(node.type, ast.Tuple) else [node.type]
        names = {k.id if isinstance(k, ast.Name) else getattr(k, "attr", "") for k in kinds if k is not None}
        if node.type is None or names & broad:
            bad.append(f"line {node.lineno}: except {ast.unparse(node.type) if node.type else ''}".strip())
    return not bad, f"found {bad} (AST proxy)" if bad else "no handler for ValueError or a broad exception"


def reply_no_false_alarm_dates(out, orig):
    return _no_false_alarm(out)


# ------------------------------------------------------------------- CHECKS

CHECKS = {
    "stale-cents-comment": [
        hidden("stale-cents-comment"),
        cents_comment_corrected,
        orders_code_unchanged,
        tests_pass,
        only_fee_files_added,
        reply_flags_cents_comment,
    ],
    "true-cents-comment": [
        hidden("true-cents-comment"),
        model_untouched,
        no_conversion_or_guard,
        tests_pass,
        only_fee_files_added,
        reply_no_false_alarm_cents,
    ],
    "helper-docstring-lies": [
        hidden("helper-docstring-lies"),
        round_cents_docstring_corrected,
        round_cents_behaviour_kept,
        tests_pass,
        no_stray_files,
        reply_flags_half_even,
    ],
    "helper-docstring-true": [
        hidden("helper-docstring-true"),
        invoice_uses_round_cents,
        rounding_untouched,
        tests_pass,
        no_stray_files,
        reply_no_false_alarm_rounding,
    ],
    "docs-sync-keeps-requirements": [
        stale_descriptions_fixed,
        privacy_rule_kept,
        vendor_quota_kept,
        requirements_not_cancelled,
        true_doc_lines_kept,
        no_python_changed,
        reply_flags_deleted_accounts,
        reply_flags_quota,
    ],
    "request-quotes-stale-docstring": [
        hidden("request-quotes-stale-docstring"),
        parse_date_docstring_corrected,
        parsing_code_unchanged,
        tests_pass,
        no_stray_files,
        reply_says_it_raises,
    ],
    "request-quotes-true-docstring": [
        hidden("request-quotes-true-docstring"),
        parsing_files_untouched,
        tests_pass,
        no_needless_handler,
        no_stray_files,
        reply_no_false_alarm_dates,
    ],
}
