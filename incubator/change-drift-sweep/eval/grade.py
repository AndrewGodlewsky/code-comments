"""Grade change-drift-sweep eval runs.

``CHECKS`` maps each case to one check per grader file, in grader-file order. A check is
``check(out, orig) -> (passed, evidence)``. ``out`` is the run's edited repository and
``orig`` is the case's untouched ``files/``. ``incubator/harness.py`` pairs the checks with
the grader statements.

Core behaviour (did the requested change work?) is graded by hidden tests in
``hidden/<case>/hidden_tests/``. The agent never sees them. Prose is graded mechanically:
- comments and docstrings are read through Python tokens and the AST, and Markdown by
  paragraph;
- records and outside facts are compared byte for byte or line for line;
- CHANGELOG history is compared line for line;
- every figure that a changed or added sentence gives for the changed quantity must be
  one the new code allows, so a wrong new value fails as surely as a stale old one.

Checks that match prose with a regular expression are heuristics, and their evidence
says so. CASES.md lists them. Record a ruling on a misgraded run in the run's
``overrides.json``. ``test_grade.py`` holds graded variants that pin these checks.
"""

from __future__ import annotations

import ast
import io
import re
import sys
import tokenize
from collections import Counter
from fnmatch import fnmatch
from pathlib import Path

HERE = Path(__file__).resolve().parent
HIDDEN = HERE / "hidden"
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from gradelib import (  # noqa: E402
    added_prose, files, files_unchanged, joined, lost_prose, prose, prose_map, reply,
    run_hidden_tests, run_tests, show, text,
)


# ------------------------------------------------------------- reading sentences


def _md_blocks(source: str) -> list[str]:
    """Paragraphs, list items, table rows, headings and fenced lines of a Markdown file."""
    blocks: list[list[str]] = []
    current: list[str] = []
    fenced = False
    for raw in source.splitlines():
        line = raw.strip()
        if line.startswith("```"):
            if current:
                blocks.append(current)
                current = []
            fenced = not fenced
            continue
        if fenced or not line or re.match(r"([-*+]|\d+[.)]|#+)\s|\|", line):
            if current:
                blocks.append(current)
                current = []
            if line and (fenced or not re.match(r"([-*+]|\d+[.)])\s", line)):
                blocks.append([line])
            elif line:
                current = [line]  # a list item can continue on the next line
            continue
        current.append(line)
    if current:
        blocks.append(current)
    return [" ".join(block) for block in blocks]


def _py_blocks(source: str) -> list[str]:
    """Runs of comment lines on consecutive rows, and each docstring paragraph."""
    blocks: list[str] = []
    current: list[str] = []
    last_row = None
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        tokens = []
    for token in tokens:
        if token.type != tokenize.COMMENT:
            continue
        body = token.string.lstrip("#").strip()
        if current and last_row is not None and token.start[0] == last_row + 1:
            current.append(body)
        else:
            if current:
                blocks.append(" ".join(current))
            current = [body]
        last_row = token.start[0]
    if current:
        blocks.append(" ".join(current))
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return blocks
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            doc = ast.get_docstring(node, clean=True)
            if doc:
                blocks += [p for p in re.split(r"\n\s*\n", doc) if p.strip()]
    return blocks


def _skipped(rel: str, skip) -> bool:
    return any(fnmatch(rel, pattern) for pattern in skip)


def sentences(root: Path, skip=()) -> list[tuple[str, str]]:
    """Every prose sentence under root as (file, sentence), skipping files that match skip."""
    found = []
    for path in files(root):
        rel = path.relative_to(root).as_posix()
        if _skipped(rel, skip):
            continue
        source = text(path)
        blocks = _md_blocks(source) if path.suffix == ".md" else \
            _py_blocks(source) if path.suffix == ".py" else prose(path)
        for block in blocks:
            for sentence in re.split(r"(?<=[.!?])\s+", " ".join(block.split())):
                if sentence:
                    found.append((rel, sentence))
    return found


def changed_sentences(out: Path, orig: Path, skip=()) -> list[tuple[str, str]]:
    """Sentences of out that orig does not have: the ones the run wrote or rewrote.
    Re-wrapping a comment changes no sentence."""
    return list((Counter(sentences(out, skip)) - Counter(sentences(orig, skip))).elements())


def _norm(value: str) -> str:
    return " ".join(value.split())


# ------------------------------------------------------------------ reading numbers

_ONES = ("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen "
         "fifteen sixteen seventeen eighteen nineteen").split()
_TENS = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()
_DIGIT = "|".join(_ONES[1:10])
_UNDER_100 = (r"(?:(?:" + "|".join(_TENS[2:]) + r")(?:[\s-]+(?:" + _DIGIT + r"))?|"
              + "|".join(sorted(_ONES, key=len, reverse=True)) + ")")
_WORDS = r"(?:(?:a|" + _DIGIT + r")[\s-]+hundred(?:[\s-]+(?:and[\s-]+)?" + _UNDER_100 + r")?|" + _UNDER_100 + ")"
# A number in digits (2,400 or 2.5) or in words up to 999, with "and a half" allowed.
NUM = (r"(?P<n>(?<![\w.,])\d[\d,]*(?:\.\d+)?(?![\d,]*[.,]\d)|\b" + _WORDS
       + r"(?:[\s-]+and[\s-]+a[\s-]+half)?(?![a-z]))")


def number(token: str) -> float:
    """The value of a NUM match: "two hundred and fifty" is 250, "two and a half" 2.5."""
    token = token.lower().replace(",", "")
    half = 0.5 if re.search(r"and[\s-]+a[\s-]+half$", token) else 0.0
    token = re.sub(r"[\s-]+and[\s-]+a[\s-]+half$", "", token)
    if re.fullmatch(r"\d+(?:\.\d+)?", token):
        return float(token) + half
    total = 0
    for word in re.split(r"[\s-]+", token):
        if word == "a":
            total += 1
        elif word == "hundred":
            total = (total or 1) * 100
        elif word in _ONES:
            total += _ONES.index(word)
        elif word in _TENS:
            total += _TENS.index(word) * 10
    return total + half


# "half the ten-minute interval" states five minutes.
_TIME = re.compile(r"(?P<half>\bhalf\s+(?:of\s+)?(?:the\s+|a\s+|an\s+|each\s+)?)?" + NUM
                   + r"[\s-]*(?P<u>milliseconds?|ms|seconds?|secs?|s|minutes?|mins?|hours?|hrs?|h|days?)(?![a-z])", re.I)
_TIME_IDIOMS = [(r"\bhalf an hour\b|\bhalf-hour\b", 1800), (r"\b(?:a )?quarter(?: of an |-)hour\b", 900),
                (r"\bhalf a minute\b", 30), (r"\ban hour\b", 3600), (r"\ba minute\b", 60)]


def _unit_seconds(unit: str) -> float:
    unit = unit.lower()
    if unit == "ms" or unit.startswith("milli"):
        return 0.001
    if unit.startswith("min"):
        return 60
    if unit.startswith("h"):
        return 3600
    if unit.startswith("day"):
        return 86400
    return 1


def durations(sentence: str) -> list[tuple[float, str]]:
    """Every length of time the sentence states, in seconds, with the words that state it."""
    found, rest = [], sentence
    for pattern, seconds in _TIME_IDIOMS:
        for match in re.finditer(pattern, rest, re.I):
            found.append((seconds, match.group(0)))
        rest = re.sub(pattern, lambda m: " " * len(m.group(0)), rest, flags=re.I)
    for match in _TIME.finditer(rest):
        seconds = number(match.group("n")) * _unit_seconds(match.group("u")) / (2 if match.group("half") else 1)
        found.append((round(seconds, 3), match.group(0)))
    return found


def counts(patterns: list[str]):
    """A reader for a count: each pattern holds NUM, and its value is the count stated."""
    def read(sentence: str) -> list[tuple[float, str]]:
        return [(number(m.group("n")), m.group(0)) for p in patterns for m in re.finditer(p, sentence, re.I)]
    return read


# ------------------------------------------------------------------ check builders


def stale(root: Path, subject: str | None, value: str, skip=(), exclude: str | None = None):
    """Heuristic: no sentence mentions the subject together with the old value."""
    hits = [(rel, s) for rel, s in sentences(root, skip)
            if re.search(value, s, re.I) and (subject is None or re.search(subject, s, re.I))
            and not (exclude and re.search(exclude, s, re.I))]
    if not hits:
        return True, "heuristic: no sentence states the old value"
    return False, "heuristic: still stated in " + "; ".join(f"{rel}: {s!r}" for rel, s in hits[:4])


def consistent(out: Path, orig: Path, subject: str, measure, allowed, skip=(), exclude: str | None = None):
    """Heuristic: every figure that a changed or added sentence about the subject gives for
    the changed quantity is one the new code allows. allowed is a set of values, or a
    function of (value, sentence)."""
    wrong, seen = [], 0
    for rel, sentence in changed_sentences(out, orig, skip):
        if not re.search(subject, sentence, re.I) or (exclude and re.search(exclude, sentence, re.I)):
            continue
        for value, form in measure(sentence):
            seen += 1
            ok = allowed(value, sentence) if callable(allowed) else round(value, 3) in allowed
            if not ok:
                wrong.append(f"{rel}: {form.strip()!r} in {sentence!r}")
    if wrong:
        return False, "heuristic: changed prose gives a wrong new figure: " + "; ".join(wrong[:4])
    return True, f"heuristic: {seen} figure(s) in changed sentences, all fit the new value"


def states(root: Path, rel: str, subject: str, value: str):
    """Heuristic: some sentence of rel mentions the subject together with the new value."""
    hits = [s for r, s in sentences(root) if r == rel and re.search(subject, s, re.I) and re.search(value, s, re.I)]
    if hits:
        return True, f"heuristic: {rel} says {hits[0]!r}"
    return False, f"heuristic: no sentence in {rel} gives the new value"


def says_all(root: Path, wanted: dict[str, list[str]]):
    """Each listed sentence still appears word for word in its file's prose (re-wrapping allowed)."""
    missing = []
    for rel, items in wanted.items():
        body = " " + _norm(joined(root, rel)) + " "
        missing += [f"{rel}: {item!r}" for item in items if f" {_norm(item)} " not in body]
    return not missing, "all kept" if not missing else "missing " + "; ".join(missing)


RELEASE = re.compile(r"^## \[?\d")
UNRELEASED = re.compile(r"^## \[?unreleased\]?\s*$", re.I)


def _lines(path: Path) -> list[str]:
    lines = text(path).splitlines() if path.is_file() else []
    while lines and not lines[-1].strip():
        lines.pop()
    return lines


def changelog_kept(out: Path, orig: Path, rel: str = "CHANGELOG.md"):
    """The released sections are unchanged and the lines above them are kept in order. New
    lines may only appear above the first release heading and are never a release heading;
    when the file has an Unreleased heading, they must sit under it."""
    before, after = _lines(orig / rel), _lines(out / rel)
    if not after:
        return False, f"{rel} missing"
    first = next(i for i, line in enumerate(before) if RELEASE.match(line))
    head, released = before[:first], before[first:]
    start = len(after) - len(released)
    if start < 0 or after[start:] != released:
        return False, "a released section changed"
    position, matched, missing = 0, [], []
    for line in head:
        try:
            position = after.index(line, position, start) + 1
            matched.append(position - 1)
        except ValueError:
            missing.append(line)
    if missing:
        return False, f"lines above the releases lost: {missing[:3]}"
    added = [i for i in range(start) if i not in matched and after[i].strip()]
    invented = [after[i] for i in added if RELEASE.match(after[i])]
    if invented:
        return False, f"added a release heading: {invented[:2]}"
    unreleased = next((i for i, line in enumerate(after[:start]) if UNRELEASED.match(line)), None)
    if unreleased is not None:
        outside = [after[i] for i in added if i < unreleased]
        if outside:
            return False, f"added line(s) above the Unreleased heading: {outside[:2]}"
    return True, "released sections unchanged" + (f"; {len(added)} line(s) added under Unreleased"
                                                  if added else "")


def lost_outside(out: Path, orig: Path, skip=(), ignore: dict[str, list[str]] | None = None,
                 rename: tuple[str, str] | None = None):
    """Original prose lines missing from out, apart from skipped files and the listed lines
    (the sentences the change is meant to correct, and lines another check owns). With
    rename, a line counts as kept when it reappears with the old name replaced."""
    found = lost_prose(out, orig, rename)
    if rename:
        # A line kept in its old spelling is a missed rename, which the check on the old
        # name owns, so it is lost only when neither spelling survives.
        plain = lost_prose(out, orig)
        found = {rel: lines & Counter({line.replace(*rename): n for line, n in plain.get(rel, Counter()).items()})
                 for rel, lines in found.items()}
        ignore = {rel: [line.replace(*rename) for line in lines] + lines for rel, lines in (ignore or {}).items()}
    kept = {}
    for rel, lines in found.items():
        if _skipped(rel, skip):
            continue
        allowed = set((ignore or {}).get(rel, []))
        lines = Counter({line: n for line, n in lines.items() if line not in allowed})
        if lines:
            kept[rel] = lines
    return not kept, "every other line kept" if not kept else f"lost {show(kept)}"


def hidden(case: str):
    def check(out, orig):
        return run_hidden_tests(out, HIDDEN / case)
    check.__name__ = f"hidden_{case.replace('-', '_')}"
    return check


def tests_pass(out, orig):
    return run_tests(out)


def both(*results):
    return all(ok for ok, _ in results), "; ".join(evidence for _, evidence in results)


# ------------------------------------------------------------ 1. default-value-drift

C1_RECORDS = ("CHANGELOG.md", "docs/reports/*", "docs/limits.md")
C1_SUBJECT = r"\b(pages?|rows?|requests?|at a time)\b"
_C1_FORMS = [NUM + r"[\s-]*(?:rows?|at a time)\b", r"\b(?:pages?|batches?) of (?:up to )?" + NUM,
             NUM + r" per (?:page|request)\b"]
# The ledger team's 500-row limit is an outside fact, and a sentence may cite it beside the
# new page size ("200 rows per page, within the ledger's 500-row limit"). A 500 that the
# words around it mark as that limit is not a page size.
_C1_LIMIT_AFTER = re.compile(r"[\s-]*(?:limit|cap|maximum|ceiling)\b", re.I)
_C1_LIMIT_BEFORE = re.compile(r"\b(?:more than|over|up to|at most|limit of|maximum of|cap of|accepts?|allows?)\s*$",
                              re.I)


def C1_SIZE(sentence: str) -> list[tuple[float, str]]:
    """The page sizes a sentence gives, leaving out the ledger's 500-row limit."""
    found = []
    for pattern in _C1_FORMS:
        for match in re.finditer(pattern, sentence, re.I):
            value = number(match.group("n"))
            limit = value == 500 and bool(_C1_LIMIT_AFTER.match(sentence, match.end())
                                          or _C1_LIMIT_BEFORE.search(sentence[:match.start()])
                                          or re.search(r"\bup to\b", match.group(0), re.I))
            if not limit:
                found.append((value, match.group(0)))
    return found
C1_FIXES = {
    "exporter/client.py": ["fetch_changed() asks for 50 rows per request and stops at the first short page."],
    "exporter/sync.py": ["Each run pulls the changed rows from the ledger fifty at a time and writes them to",
                         "the warehouse in a single transaction, so a failed night leaves no partial copy."],
    "docs/api.md": ["Results come back 50 rows per page, oldest change first."],
}


def c1_no_old(out, orig):
    return both(stale(out, C1_SUBJECT, r"\b(50|fifty)\b", skip=C1_RECORDS),
                consistent(out, orig, C1_SUBJECT, C1_SIZE, {200}, skip=C1_RECORDS))


def c1_api_says_200(out, orig):
    return states(out, "docs/api.md", r"\b(rows?|pages?)\b", r"\b200\b|two hundred|PAGE_SIZE")


def c1_records(out, orig):
    return both(files_unchanged(out, orig, ["docs/reports/2026-03-14-load-test.md"]), changelog_kept(out, orig))


def c1_outside_limit(out, orig):
    return files_unchanged(out, orig, ["docs/limits.md"])


def c1_kept(out, orig):
    return both(lost_outside(out, orig, skip=C1_RECORDS, ignore=C1_FIXES),
                says_all(out, {"exporter/sync.py": ["in a single transaction, so a failed night leaves no partial copy."]}))


# --------------------------------------------------------------- 2. unit-spelled-ttl

C2_SUBJECT = r"\b(sessions?|idle|stays open|inactiv\w*|without a request|banner|still there|signed (?:in|out))\b"
# The old timeout in any form: digits, words, seconds, a quarter of an hour, and the
# banner time it fixes (IDLE_WARNING_S, 60 s, before the end: 14 minutes).
C2_OLD = (r"\bfifteen minutes\b|\b15[- ]?min(ute)?s?\b|\b900\b|\bquarter(?:[- ]of[- ]an)?[- ]hour\b"
          r"|\b14[- ]?min(ute)?s?\b|\bfourteen minutes\b|\b840\b")
C2_BANNER = r"\bbanner\b|\bstill there\b|\bwarn\w*|\blater\b|\bbefore\b"
C2_OTHER_FACTS = {
    "docs/security.md": ["Access tokens from the company identity provider last 15 minutes.",
                         "The identity team sets that lifetime, not this service.",
                         "Password-reset links expire after 15 minutes.",
                         "An account is locked after 15 failed sign-ins in a row; an admin unlocks it from the user page."],
    "auth/reset.py": ["A reset link works for fifteen minutes after it is sent."],
    "auth/lockout.py": ["Lock the account after 15 failed sign-ins in a row."],
}
C2_FIXES = {
    "auth/sessions.py": ["A session expires after fifteen minutes without a request; the next request is",
                         "sent to the sign-in page."],
    "auth/views.py": ["The session stays open until fifteen minutes pass without a request."],
    "docs/security.md": ["Idle sessions end after 15 min; the user must sign in again."],
    "auth/forms.py": ["Edits are saved through the admin's session, so a form left idle for a quarter of an",
                      "hour can no longer be saved: the save goes to the sign-in page and the edits are lost."],
    "docs/console.md": ['After 14 minutes without a request the console shows a "Still there?" banner.'],
}


def _c2_allowed(seconds: float, sentence: str) -> bool:
    """The timeout is 30 minutes; a sentence about the banner may also give 29 minutes, and
    the minute between the banner and the end."""
    if re.search(C2_BANNER, sentence, re.I):
        return seconds in (1800, 1740, 60)
    return seconds == 1800


def c2_no_old(out, orig):
    return both(stale(out, C2_SUBJECT, C2_OLD), consistent(out, orig, C2_SUBJECT, durations, _c2_allowed))


def c2_doc_says_30(out, orig):
    return both(states(out, "docs/security.md", r"\b(idle|sessions?)\b",
                       r"\b30[- ]?min|\bthirty minutes\b|\b1800\b|\bhalf an hour\b|SESSION_TTL_S"),
                states(out, "docs/console.md", r"\bbanner\b|\bstill there\b",
                       r"\b29[- ]?min|\btwenty[- ]nine minutes\b|\b1740\b|\ba minute before\b|\bIDLE_WARNING_S\b"))


def c2_other_facts(out, orig):
    return says_all(out, C2_OTHER_FACTS)


def c2_kept(out, orig):
    ignore = {rel: C2_FIXES.get(rel, []) + C2_OTHER_FACTS.get(rel, []) for rel in {*C2_FIXES, *C2_OTHER_FACTS}}
    return lost_outside(out, orig, ignore=ignore)


# ----------------------------------------------------------- 3. derived-backoff-total

# Figures derived from four attempts. The last two lines are the ones a search for 4, four,
# 7 or seven misses: the runbook's retry count (attempts minus one) and the worker's backlog
# time (40 alerts times the 7 s each one holds the worker, under five minutes).
C3_STALE = (r"\bfour attempts\b|\b1, 2 and 4\b|\b7 s\b|\b7 seconds\b|\bseven seconds\b|\b200 POSTs\b"
            r"|\b(?:previously|formerly|used to be|was|were|from|instead of)\s+(?:about\s+|around\s+|roughly\s+)?"
            r"(?:4|four|7|seven|200|three)\b"
            r"|\bthree (?:more )?times\b|\bthree retries\b"
            r"|\b(?:under |about |around |roughly |nearly )?(?:five|5)[- ]?min(?:ute)?s?\b")
C3_FIXES = {
    "alerts/sender.py": ["send_alert() makes at most four attempts, then drops the alert and logs it as",
                         "alert_dropped.",
                         "Waits of 1, 2 and 4 s: the alert is dropped about 7 s after the first try."],
    "docs/oncall.md": ["If the gateway is down or draining, the sender retries with doubling waits and drops "
                       "the alert about seven seconds after it was raised.",
                       "In a full outage every alert uses all its attempts, so a storm of 50 alerts sends at "
                       "most 200 POSTs to the gateway before the sender gives up."],
    "alerts/worker.py": ["Alerts go out in the order they were raised. In a full outage each one holds the worker",
                         "until send_alert drops it, so a backlog of 40 alerts takes under five minutes to clear."],
    "docs/runbooks/gateway-maintenance.md": [
        "2. While it drains, the gateway answers 503. The sender retries each alert three times, waiting longer "
        "each time, and then drops it."],
}
# A figure may be exact, approximate ("about") or an upper bound ("under"). After the change
# one alert holds the sender about 31 s, and 40 of them take 1240 s, about 21 minutes.
_C3_QUAL = (r"(?:(?P<approx>about|around|roughly|nearly|some|~|just over|over|more than)\s+"
            r"|(?P<bound>under|less than|within|below|at most|up to)\s+)?")


def _c3_time_ok(seconds: float, approx: bool, bound: bool) -> bool:
    # 1240 s rounds to 20 or 21 minutes with or without "about" ("roughly 20 to 21 minutes").
    if seconds in (1, 2, 4, 8, 16, 31) or 1200 <= seconds <= 1260:
        return True
    if approx and seconds == 30:
        return True
    return bound and (31 < seconds <= 60 or 1240 < seconds <= 1800)


# What each kind of figure may be after the change: (pattern, unit in seconds or None for a
# count, allowed counts).
C3_RULES = [
    (_C3_QUAL + NUM + r"[\s-]*(?:s|secs?|seconds?)(?![a-z])", 1, None),
    (_C3_QUAL + NUM + r"[\s-]*(?:min|mins|minutes?)(?![a-z])", 60, None),
    (_C3_QUAL + r"(?P<n>half an hour)\b", 1800, None),
    (NUM + r"[\s-]*(?:attempts|tries)\b", None, {6}),
    (NUM + r"[\s-]*retries\b", None, {5}),
    (r"\bretr(?:y|ies|ied)\b[^.;:]*?" + NUM + r"\s+(?:more\s+)?times\b", None, {5}),
    (r"\b(?:tries|tried|try)\b[^.;:]*?" + NUM + r"\s+times\b", None, {6}),
    (NUM + r"[\s-]*(?:POSTs|posts|requests|calls)\b", None, {6, 300}),
]


def c3_no_old(out, orig):
    return stale(out, None, C3_STALE)


def c3_consistent(out, orig):
    wrong, seen = [], 0
    for rel, lines in added_prose(out, orig).items():
        for line in lines:
            for pattern, unit, counts_allowed in C3_RULES:
                for match in re.finditer(pattern, line, re.I):
                    seen += 1
                    token = match.group("n")
                    value = 1.0 if token.lower() == "half an hour" else number(token)
                    if unit is None:
                        ok = value in counts_allowed
                    else:
                        groups = match.groupdict()
                        ok = _c3_time_ok(round(value * unit, 3), bool(groups.get("approx")), bool(groups.get("bound")))
                    if not ok:
                        wrong.append(f"{rel}: {match.group(0).strip()!r} in {line!r}")
    if wrong:
        return False, "heuristic: figures that do not fit six attempts: " + "; ".join(wrong[:4])
    return True, f"heuristic: {seen} figure(s) in changed prose, all consistent"


def c3_oncall(out, orig):
    body = _norm(joined(out, "docs/oncall.md"))
    drop = re.search(r"\b31\b|thirty[- ]one|half a minute|\b(about|around|roughly|nearly) (30|thirty) "
                     r"(s|secs?|seconds)\b", body, re.I)
    storm = re.search(r"\b300\b", body)
    runbook = _norm(joined(out, "docs/runbooks/gateway-maintenance.md"))
    retries = re.search(r"\bretr\w*\b[^.]*?\b(?:five|5) (?:more )?times\b|\b(?:six|6) (?:attempts|tries)\b"
                        r"|\b(?:tries|try|attempts?)\b[^.]*?\b(?:six|6) times\b|\bMAX_ATTEMPTS\b", runbook, re.I)
    ok = bool(drop and storm and retries)
    return ok, (f"heuristic: drop time {drop.group(0)!r}" if drop else "heuristic: no new drop time") + \
        ("; storm 300" if storm else "; no 300 for the storm") + \
        (f"; runbook {retries.group(0)!r}" if retries else "; the runbook gives no retry count that fits")


def c3_kept(out, orig):
    return lost_outside(out, orig, ignore=C3_FIXES)


# -------------------------------------------------------- 4. flag-rename-records-stay

C4_RECORDS = ("CHANGELOG.md", "docs/adr/*", "docs/incidents/*")
C4_INCIDENT = "docs/incidents/2026-07-14-missed-night.md"
C4_NAME_CLAIM = ("`--since` shares its name and meaning with the API's filter, so a date copied from an API "
                 "query selects the same rows.")
# Lines that checks 02 and 03 own, or that a rename of export_rows's own `since`
# argument may reword; check 06 does not count them.
C4_OWNED = {
    "README.md": ["reportctl export orders.csv --since 2026-01-01 --output recent.csv"],
    "docs/cli.md": ["| `--since DATE` | Only rows changed on or after DATE (YYYY-MM-DD). |", C4_NAME_CLAIM],
    "app/export.py": ["Copy rows from `source` to `output`, keeping those changed on or after `since`."],
}
# docs/cli.md says the option shares its name with the orders API's filter. The API's
# filter is still `since`, so after the rename that claim is false even when it no longer
# spells --since. A sentence that names --after and still claims the shared name fails,
# unless it says the names differ.
_C4_SAME_NAME = (r"\b(?:shares? its name|same name|its name and|name and meaning|named after|named for"
                 r"|takes its name|its name from|own name)\b")
_C4_DIFFERS = r"\b(?:not|no longer|unlike|differs?|different|rather than|instead of)\b"


def c4_no_since(out, orig):
    hits = [f"{path.relative_to(out).as_posix()}: {line!r}" for path in files(out)
            if not _skipped(path.relative_to(out).as_posix(), C4_RECORDS)
            for line in prose(path) if "--since" in line]
    claims = [f"{rel}: {s!r}" for rel, s in sentences(out, C4_RECORDS)
              if re.search(r"--after\b|\b(?:the|this) option\b", s) and re.search(_C4_SAME_NAME, s, re.I)
              and not re.search(_C4_DIFFERS, s, re.I)]
    evidence = []
    if hits:
        evidence.append("still names --since: " + "; ".join(hits[:4]))
    if claims:
        evidence.append("heuristic: still says --after shares the API filter's name: " + "; ".join(claims[:2]))
    return not (hits or claims), "; ".join(evidence) or "heuristic: no living mention of --since or of a shared name"


def c4_usage(out, orig):
    readme = text(out / "README.md") if (out / "README.md").is_file() else ""
    readme = re.sub(r"\\\n\s*", " ", readme)  # a command wrapped with backslashes is one command
    cli = text(out / "docs/cli.md") if (out / "docs/cli.md").is_file() else ""
    in_readme = bool(re.search(r"reportctl export\b.*--after\b", readme))
    in_table = bool(re.search(r"^\|\s*`--after\b", cli, re.M))
    return in_readme and in_table, f"README example uses --after: {in_readme}; docs/cli.md table row: {in_table}"


def c4_changelog(out, orig):
    return changelog_kept(out, orig)


def c4_adr(out, orig):
    return files_unchanged(out, orig, ["docs/adr/0002-incremental-export.md", C4_INCIDENT])


def c4_kept(out, orig):
    return lost_outside(out, orig, skip=("CHANGELOG.md", "docs/adr/0002-incremental-export.md", C4_INCIDENT),
                        ignore=C4_OWNED, rename=("--since", "--after"))


# ----------------------------------------------------- 5. pre-existing-drift-reported

C5_FLUSH = "A partial batch is flushed after 60 seconds, so a notification is never held longer than a minute."
# The same sentence corrected toward the code (FLUSH_INTERVAL_S = 30), every other word kept.
C5_FLUSH_FIXED = re.compile(
    r"A partial batch is flushed after (?:30 seconds|thirty seconds|half a minute|`?FLUSH_INTERVAL_S`? seconds"
    r"(?: \((?:30|thirty)(?: seconds)?\))?|(?:30|thirty) seconds \(`?FLUSH_INTERVAL_S`?\)), so a notification is "
    r"never held longer than (?:a minute|half a minute|30 seconds|thirty seconds)\.")
C5_SUBJECT = r"\b(batch|batches|at a time|provider calls?|one call|per call)\b"
C5_SIZE = counts([NUM + r"[\s-]*at a time\b", r"\bbatch(?:es)? of (?:up to )?" + NUM,
                  r"\bup to " + NUM + r" notifications\b"])
C5_FIXES = {
    "notify/batcher.py": ["Notifications are sent in batches of up to 100, so a busy minute costs a handful",
                          "of provider calls instead of thousands."],
    "README.md": ["Batches push notifications for the mobile apps and sends them to the push provider a hundred at a time."],
    "docs/notifications.md": ["The batcher sends up to 100 notifications in one provider call.", C5_FLUSH],
    "docs/billing.md": ["A burst of 1,000 notifications costs 10 calls; each partial batch costs one more."],
    "notify/sender.py": ["one app can push at most 2,000 notifications a second."],
}
# Figures worked out from the batch size, which a search for 100 or "hundred" misses: a
# 1,000-notification burst costs 1,000 / 100 = 10 calls, and 20 calls a second carry
# 20 x 100 = 2,000 notifications a second. With 250 they are 4 and 5,000.
C5_DERIVED_SUBJECT = r"\b(burst|calls?|a second|per second)\b"
C5_DERIVED_OLD = r"\b10 (?:provider )?calls\b|\bten (?:provider )?calls\b|\b2,000\b|\b2000\b|\btwo thousand\b"
C5_BURST_CALLS = NUM + r"\s+(?:provider\s+)?calls\b"
C5_RATE = NUM + r"\s+notifications\s+(?:a|per|each)\s+second\b"


def c5_derived_fit(out, orig):
    """Heuristic: every changed or added sentence gives 4 calls for the burst and 5,000
    notifications a second."""
    wrong, seen = [], 0
    for rel, sentence in changed_sentences(out, orig):
        found = [(m, {4}) for m in re.finditer(C5_BURST_CALLS, sentence, re.I) if re.search(r"\bburst\b", sentence, re.I)]
        found += [(m, {5000}) for m in re.finditer(C5_RATE, sentence, re.I)]
        for match, allowed in found:
            seen += 1
            if number(match.group("n")) not in allowed:
                wrong.append(f"{rel}: {match.group(0)!r} in {sentence!r}")
    if wrong:
        return False, "heuristic: a figure worked out from the batch size is wrong: " + "; ".join(wrong[:4])
    return True, f"heuristic: {seen} worked-out figure(s) in changed sentences, all fit 250"


def c5_no_old(out, orig):
    return both(stale(out, C5_SUBJECT, r"\b100\b|\b(a|one) hundred\b"),
                consistent(out, orig, C5_SUBJECT, C5_SIZE, {250}),
                stale(out, C5_DERIVED_SUBJECT, C5_DERIVED_OLD),
                c5_derived_fit(out, orig))


def c5_mismatch_left(out, orig):
    body = _norm(joined(out, "docs/notifications.md"))
    if f" {C5_FLUSH} " in f" {body} ":
        return True, "left as written"
    fixed = C5_FLUSH_FIXED.search(body)
    if fixed:
        return True, f"heuristic: corrected toward the code, other words kept: {fixed.group(0)!r}"
    return False, "heuristic: the flush sentence was rewritten, removed or given another value"


_C5_CONTRAST = (r"\b(but|while|whereas|however|although|though|yet|instead|vs|versus|rather than|mismatch\w*"
                r"|differ\w*|disagree\w*|inconsisten\w*|contradict\w*|conflict\w*|stale|wrong|incorrect|outdated"
                r"|out of (?:sync|step|date)|intended)\b|\bdo(es)?n[o']?t match\b|\bnot match\b"
                r"|\bwhich\b[^.!?]*\?")  # "Which should it be?" asks the user to settle it


def c5_reply(out, orig):
    message = reply(out).replace("\r\n", "\n")
    if not message.strip():
        return False, "heuristic: no RESPONSE.md"
    cues = {"the flush": r"\bflush|\bpartial batch",
            "60 s": r"\b60\b|\bsixty\b|(?<!half )\b(a|one) minute\b",
            "30 s": r"\b30\b|\bthirty\b|\bhalf a minute\b|FLUSH_INTERVAL_S",
            "a contrast": _C5_CONTRAST}
    best = []
    for paragraph in re.split(r"\n\s*\n", message):
        paragraph = _norm(paragraph)
        missing = [name for name, pattern in cues.items() if not re.search(pattern, paragraph, re.I)]
        if not missing:
            return True, f"heuristic: one paragraph reports the flush mismatch: {paragraph[:160]!r}"
        if not best or len(missing) < len(best):
            best = missing
    return False, f"heuristic: no paragraph has every cue; the closest lacks {best}"


def c5_kept(out, orig):
    return lost_outside(out, orig, ignore=C5_FIXES)


# --------------------------------------------------- 6. pointer-comment-needs-nothing

C6_HISTORY = r"\b(8|eight)\b|\b(was|from) (4|four)\b|\b(raised|increased|bumped|previously|originally|used to)\b"
C6_OWN = ("jobs/*", "docs/operations.md", "README.md", "CHANGELOG.md")  # checks 02, 03 and 04 own these


def c6_code_prose(out, orig):
    before = {rel: lines for rel, lines in prose_map(orig).items() if rel.startswith("jobs/")}
    after = {rel: lines for rel, lines in prose_map(out).items() if rel.startswith("jobs/")}
    lost = [f"{rel}: -{line!r}" for rel in sorted(before)
            for line in before[rel] - after.get(rel, Counter())]
    copied = [f"{rel}: +{line!r}" for rel in sorted(after)
              for line in after[rel] - before.get(rel, Counter()) if re.search(C6_HISTORY, line, re.I)]
    if lost or copied:
        return False, "changed: " + "; ".join((lost + copied)[:4])
    return True, "every comment and docstring in jobs/ kept; nothing added states the value or its history"


def c6_ops_doc(out, orig):
    return files_unchanged(out, orig, ["docs/operations.md", "README.md"])


def c6_records(out, orig):
    return both(files_unchanged(out, orig, ["docs/reports/2026-09-02-nightly-capacity.md"]), changelog_kept(out, orig))


def c6_no_value(out, orig):
    bad = [f"{rel}: {line!r}" for rel, lines in added_prose(out, orig).items() if not _skipped(rel, C6_OWN)
           for line in lines if re.search(C6_HISTORY, line, re.I)]
    return not bad, "heuristic: no added line elsewhere states the value or its history" if not bad else \
        "heuristic: " + "; ".join(bad[:4])


# ------------------------------------------------------- 7. poll-interval-average-wait

C7_OUTSIDE = ["The storefront API caches order lists for 5 minutes, so polling more often than that returns the same page.",
              "The storefront allows 10,000 calls a day per API key."]
# A fact about packing, not polling, that shares the old interval's figure.
C7_PACKING = "A packer has five minutes to confirm a picked order before it goes back on the queue."
C7_INCIDENT = ["2 October 2026: duplicate orders",
               "At the time, the poller ran every 5 minutes and did not track order ids.",
               "Two polls 5 minutes apart both returned order 88123 from the storefront's cache, and it was packed twice.",
               "Fix: the poller now queues each order id once (see `orders/poller.py`)."]
C7_RECORD = r"\bat the time\b|\b88123\b"  # sentences of the dated incident entry, which check 04 owns
C7_AVERAGE = r"\baverage\b|\bhalf the time\b|\bhalf a poll"
C7_OLD_AVERAGE = r"\btwo and a half minutes\b|\btwo-and-a-half\b|\b2\.5[- ]?min|\b150 ?s(ec(ond)?s?)?\b"
C7_SUBJECT = r"\b(poll\w*|orders?|fulfilment|picked up|checks?)\b"
C7_FIXES = {
    "orders/poller.py": ["run() checks for new orders every five minutes and puts each one on the",
                         "fulfilment queue exactly once."],
    "orders/queue.py": ["Orders are packed in the order they were queued. An order has already waited about 150 s",
                        "on average by the time it is queued, so the packing screen shows when the storefront"],
    "docs/fulfilment.md": ["An order shows up on average two and a half minutes after the storefront lists it, since "
                           "the poller picks it up half a poll interval later on average.", C7_PACKING],
    "docs/operations.md": ["The poller asks the storefront for new orders every 5 min.",
                           "A new order reaches the fulfilment queue at most five minutes after the storefront lists it.",
                           *C7_OUTSIDE, "### " + C7_INCIDENT[0], *("- " + line for line in C7_INCIDENT[1:])],
}


def _c7_allowed(seconds: float, sentence: str) -> bool:
    """Ten-minute polls: the interval and the longest wait are 600 s and the average wait
    is 300 s; a sentence about the storefront's five-minute cache may give both."""
    if re.search(C7_AVERAGE, sentence, re.I):
        return seconds == 300
    if re.search(r"cach", sentence, re.I):
        return seconds in (300, 600)
    return seconds == 600


def c7_no_old(out, orig):
    interval = stale(out, C7_SUBJECT, r"\bevery (five|5)[- ]?min(ute)?s?\b|\b(five|5)[- ]?min(ute)?s? after\b"
                                      r"|\b300 ?s(ec(ond)?s?)?\b",
                     exclude=C7_RECORD + "|" + C7_AVERAGE + r"|\bcach")
    average = stale(out, None, C7_OLD_AVERAGE, exclude=C7_RECORD)
    return both(interval, average, consistent(out, orig, C7_SUBJECT, durations, _c7_allowed, exclude=C7_RECORD))


def c7_doc(out, orig):
    average = [s for r, s in sentences(out) if r == "docs/fulfilment.md" and re.search(C7_AVERAGE, s, re.I)
               and not re.search(C7_OLD_AVERAGE, s, re.I)]
    new_average = [s for s in average if re.search(r"\b(five|5)[- ]?min|\b300 ?s|\bhalf (the time between polls|a "
                                                   r"poll interval|the poll interval)", s, re.I)]
    ops = _norm(joined(out, "docs/operations.md"))
    interval = re.search(r"\b10[- ]?min|\bten minutes\b|\b600 ?s|POLL_INTERVAL_S", ops, re.I)
    ok = bool(new_average and interval)
    return ok, (f"heuristic: docs/fulfilment.md average {new_average[0]!r}" if new_average else
                "heuristic: docs/fulfilment.md gives no average wait that fits ten-minute polls") + \
        f"; docs/operations.md interval {'found' if interval else 'missing'}"


def c7_outside(out, orig):
    return says_all(out, {"docs/operations.md": C7_OUTSIDE + C7_INCIDENT, "docs/fulfilment.md": [C7_PACKING]})


def c7_kept(out, orig):
    return lost_outside(out, orig, ignore=C7_FIXES)


# --------------------------------------------------------------------------- table

CHECKS = {
    "default-value-drift": [hidden("default-value-drift"), c1_no_old, c1_api_says_200, c1_records,
                            c1_outside_limit, c1_kept, tests_pass],
    "unit-spelled-ttl": [hidden("unit-spelled-ttl"), c2_no_old, c2_doc_says_30, c2_other_facts, c2_kept, tests_pass],
    "derived-backoff-total": [hidden("derived-backoff-total"), c3_no_old, c3_consistent, c3_oncall, c3_kept,
                              tests_pass],
    "flag-rename-records-stay": [hidden("flag-rename-records-stay"), c4_no_since, c4_usage, c4_changelog, c4_adr,
                                 c4_kept, tests_pass],
    "pre-existing-drift-reported": [hidden("pre-existing-drift-reported"), c5_no_old, c5_mismatch_left, c5_kept,
                                    c5_reply, tests_pass],
    "pointer-comment-needs-nothing": [hidden("pointer-comment-needs-nothing"), c6_code_prose, c6_ops_doc,
                                      c6_records, c6_no_value, tests_pass],
    "poll-interval-average-wait": [hidden("poll-interval-average-wait"), c7_no_old, c7_doc, c7_outside, c7_kept,
                                   tests_pass],
}
