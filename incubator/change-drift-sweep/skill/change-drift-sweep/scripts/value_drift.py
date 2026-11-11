"""List prose lines that still state an old value after a change re-values, renames or moves something.

    python value_drift.py ROOT --old VALUE [--old VALUE ...] [--unit UNIT] [--new VALUE]
                          [--near REGEX] [--strings] [--json] [--check]

It reads, under ROOT, the comments and docstrings of code files and every line of Markdown
and text docs; with --strings, also the string literals in code (help text, error and log
messages). It reads them fresh on every run, writes nothing and stores nothing. It needs
Python 3.10 or newer and nothing outside the standard library. A line is read together
with the next line of the same comment, docstring or paragraph, so a form wrapped across
the break is found; it is listed at the line where it starts.

A numeric --old value matches prose that states it:
- in digits, with or without thousands separators (2400, 2,400). Digits are bounded, so 24
  does not match 240, 2.4, 2024 or 24,000. Dates (2026-06-30), clock times (02:30),
  version strings (1.2.0) and issue numbers (#4) are never read as values;
- in number words (nine, twenty-five, one hundred and twenty), plus "twice" for 2 and
  "a dozen" for 12;
- with a unit (--unit, or one written on the value, as in --old "9 s"), as the same
  quantity in every unit of its family where it comes out round, followed by a unit:
  7200 s also matches "120 min", "2 hours", "two-hour" and "2h". A converted quantity
  matches only with a unit beside it. Sizes are read both ways, 1 KB as 1,000 and as
  1,024 bytes. When the value has a unit, a bare number followed by a different unit is
  not a hit: for 7 s, "7 days" is not listed.
Any other --old value (a flag, config key, name or path) matches as literal text, so
--legacy does not match --legacy-mode. Write a value that starts with a dash as
--old=--legacy.

The script cannot compute derived figures (a total wait, a product, a per-day count): work
each one out and pass it as another --old. --new prints the new value in each unit and
marks the lines that already state it. A small value (under 10) matches many unrelated
lines; --near REGEX keeps only hits whose line, or the prose line just before or after it,
matches REGEX (ignoring case), such as --near "replica|shard".

Each hit prints as  path:line: where [hints]: "form" = value: text
- where: comment, docstring, string (with --strings), doc, or fenced (inside a fenced
  block of a doc);
- hints: record? (a changelog, ADR, decision, migration, incident or dated file, guessed
  from the path alone), instructions? (AGENTS.md, CLAUDE.md and the like), and
  states new.
The hints decide nothing. The script lists candidates; whoever runs it reads each one.

Exit status: 0 when it ran, whether or not any line matched; 2 on a usage error. With
--check, 1 when some line matches, for use in CI.
"""

from __future__ import annotations

import argparse
import ast
import io
import json
import os
import re
import sys
import tokenize
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable

# This skill's own folder. Its examples state numbers, so it is never scanned when it
# sits inside the repository being checked.
SELF_DIR = Path(__file__).resolve().parent.parent

SKIP_DIRS = {".git", ".hg", ".svn", "node_modules", "__pycache__", ".venv", "venv", ".tox",
             ".nox", ".mypy_cache", ".ruff_cache", ".pytest_cache", "build", "dist",
             "site-packages", ".idea"}
PY = {".py", ".pyi"}
SLASH = {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".go", ".rs", ".java", ".kt", ".c",
         ".h", ".cc", ".cpp", ".hpp", ".cs", ".swift", ".scala", ".php"}
HASH = {".sh", ".bash", ".zsh", ".rb", ".pl", ".r", ".toml", ".yaml", ".yml", ".cfg",
        ".ini", ".conf", ".env", ".ps1", ".tf"}
HASH_NAMES = {"Makefile", "makefile", "GNUmakefile", "Dockerfile", "Justfile", "justfile",
              ".env"}
DOCS = {".md", ".markdown", ".mdx", ".rst", ".txt", ".adoc"}
DOC_NAMES = {"README", "CHANGELOG", "CHANGES", "HISTORY", "NEWS", "NOTES"}
MAX_BYTES = 2_000_000


# ---------------------------------------------------------------------- units


@dataclass(frozen=True)
class Unit:
    key: str
    family: str
    factor: float  # in the family's base unit: seconds or bytes
    binary: float  # the factor when KB, MB and GB are read as powers of 1024
    names: tuple[str, ...]  # spaced or attached ("15 min", "15min")
    attached: tuple[str, ...] = ()  # only straight after the number ("15m")
    singular: str = ""  # for "an hour", "half a minute"


UNITS = (
    Unit("ms", "time", 0.001, 0.001, ("milliseconds", "millisecond", "msecs", "msec", "ms"),
         singular="millisecond"),
    Unit("s", "time", 1, 1, ("seconds", "second", "secs", "sec", "s"), singular="second"),
    Unit("min", "time", 60, 60, ("minutes", "minute", "mins", "min"), ("m",), "minute"),
    Unit("h", "time", 3600, 3600, ("hours", "hour", "hrs", "hr", "h"), singular="hour"),
    Unit("day", "time", 86400, 86400, ("days", "day"), ("d",), "day"),
    Unit("week", "time", 604800, 604800, ("weeks", "week", "wks", "wk"), ("w",), "week"),
    Unit("B", "size", 1, 1, ("bytes", "byte", "B")),
    Unit("KB", "size", 1e3, 1024, ("kilobytes", "kilobyte", "KB", "kB")),
    Unit("KiB", "size", 1024, 1024, ("kibibytes", "kibibyte", "KiB")),
    Unit("MB", "size", 1e6, 1024 ** 2, ("megabytes", "megabyte", "MB")),
    Unit("MiB", "size", 1024 ** 2, 1024 ** 2, ("mebibytes", "mebibyte", "MiB")),
    Unit("GB", "size", 1e9, 1024 ** 3, ("gigabytes", "gigabyte", "GB")),
    Unit("GiB", "size", 1024 ** 3, 1024 ** 3, ("gibibytes", "gibibyte", "GiB")),
    Unit("TB", "size", 1e12, 1024 ** 4, ("terabytes", "terabyte", "TB")),
    Unit("TiB", "size", 1024 ** 4, 1024 ** 4, ("tebibytes", "tebibyte", "TiB")),
)
_EXACT = {name: u for u in UNITS for name in (u.key, *u.names, *u.attached)}
_LOWER = {name.lower(): u for name, u in reversed(list(_EXACT.items()))}


def find_unit(name: str) -> Unit | None:
    return _EXACT.get(name) or _LOWER.get(name.lower())


def _round(q: float) -> bool:
    """A quantity prose would plausibly write: at most two decimals, not vanishingly small."""
    return 0.01 <= q < 1e13 and abs(q * 100 - round(q * 100)) < 1e-6 * max(1.0, q)


def fmt(q: float) -> str:
    if abs(q - round(q)) < 1e-9:
        return str(int(round(q)))
    return f"{q:.2f}".rstrip("0").rstrip(".")


def equivalents(amount: float, unit: Unit) -> list[tuple[Unit, float, bool]]:
    """Every unit of the family where amount comes out round: (unit, quantity, 1024-based)."""
    out, seen = [], set()
    for binary in (False, True) if unit.family == "size" else (False,):
        base = amount * (unit.binary if binary else unit.factor)
        for other in UNITS:
            if other.family != unit.family:
                continue
            q = base / (other.binary if binary else other.factor)
            if not _round(q) or (other.key, fmt(q)) in seen:
                continue
            seen.add((other.key, fmt(q)))
            differs = binary and (unit.binary != unit.factor or other.binary != other.factor)
            out.append((other, q, differs))
    return out


# --------------------------------------------------------------- number words

ONES = ("zero one two three four five six seven eight nine ten eleven twelve thirteen "
        "fourteen fifteen sixteen seventeen eighteen nineteen").split()
TENS = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()
SCALES = ((10 ** 9, "billion"), (10 ** 6, "million"), (10 ** 3, "thousand"))
NUMWORD = r"(?:" + "|".join(ONES[1:] + TENS[2:] + ["zero", "hundred", "thousand", "million",
                                                  "billion"]) + r")"
_SCALE_END = re.compile(r"(?:hundred|thousand|million|billion)$", re.I)
_BEFORE_WORD = re.compile(rf"(?:\b{NUMWORD}[\s-]+|\b(?:hundred|thousand|million|billion)"
                          rf"[\s-]+and[\s-]+)$", re.I)
_AFTER_WORD = re.compile(rf"[\s-]+{NUMWORD}\b", re.I)
_AFTER_AND = re.compile(rf"[\s-]+and[\s-]+{NUMWORD}\b", re.I)


def _under_100(n: int) -> str:
    if n < 20:
        return ONES[n]
    tens, ones = divmod(n, 10)
    return TENS[tens] + (" " + ONES[ones] if ones else "")


def _under_1000(n: int, conj: bool) -> str:
    hundreds, rest = divmod(n, 100)
    parts = [ONES[hundreds] + " hundred"] if hundreds else []
    if rest:
        parts.append(("and " if hundreds and conj else "") + _under_100(rest))
    return " ".join(parts)


def spell(n: int, conj: bool = False) -> str:
    """English words for 0 <= n < 10**12, words separated by single spaces."""
    if n == 0:
        return "zero"
    parts = []
    for size, name in SCALES:
        if n >= size:
            count, n = divmod(n, size)
            parts.append(f"{_under_1000(count, conj)} {name}")
    if n:
        parts.append(("and " + _under_100(n)) if parts and conj and n < 100 else _under_1000(n, conj))
    return " ".join(parts)


def number_words(n: int) -> set[str]:
    if not 0 <= n < 10 ** 12:
        return set()
    forms = {spell(n), spell(n, conj=True)}
    for form in list(forms):
        head, _, rest = form.partition(" ")
        if head == "one" and rest.split(" ")[0] in ("hundred", "thousand", "million", "billion"):
            forms.add("a " + rest)
    if 1100 <= n < 10000 and n % 100 == 0 and n % 1000:
        forms.add(spell(n // 100) + " hundred")
    forms |= {2: {"twice"}, 12: {"a dozen", "dozen"}}.get(n, set())
    return forms


def _word_regex(form: str) -> str:
    """Words joined by spaces or hyphens, so "twenty-five" and "twenty five" both match."""
    return r"[\s\xa0-]+".join(re.escape(part) for part in form.split(" "))


def _word_ok(text: str, start: int, end: int) -> bool:
    """False when the words are part of a larger number: "five" in "twenty five" or
    "five hundred", "one hundred" in "one hundred and fifty"."""
    if _BEFORE_WORD.search(text[:start]) or _AFTER_WORD.match(text, end):
        return False
    return not (_SCALE_END.search(text[start:end]) and _AFTER_AND.match(text, end))


# ------------------------------------------------------------------- patterns

DIGIT_BEFORE = r"(?<![\w.])(?<!\d,)"
DIGIT_AFTER = r"(?!\d)(?![.,]\d)"
NO_SCALE = r"(?!\s*(?:hundred|thousand|million|billion)\b)"
SEP = r"(?:[ \t\xa0]|-)?"


def _alt(items) -> str:
    return "|".join(sorted(set(items), key=len, reverse=True))


def digit_forms(q: float, given: str = "") -> set[str]:
    forms = {fmt(q)}
    if abs(q - round(q)) < 1e-9 and q >= 1000:
        forms.add(f"{int(round(q)):,}")
    if given:
        forms.add(given)
    return forms


def _unit_names(unit: Unit, spelled: bool = False) -> str:
    """Unit names; one-letter names keep their case (s, h, B; m, d and w only attached).
    After a number word the separator is required and attached names are left out, so
    "ones" is not one second and "tend" is not ten days."""
    def one(name: str) -> str:
        return f"(?-i:{re.escape(name)})" if len(name) == 1 else re.escape(name)
    spaced = (r"(?:[ \t\xa0]|-)" if spelled else SEP) + "(?:" + _alt(one(n) for n in unit.names) + ")"
    if unit.attached and not spelled:
        spaced = f"(?:{spaced}|{_alt(one(n) for n in unit.attached)})"
    return spaced + r"(?![A-Za-z])"


def _other_unit(unit: Unit | None) -> str:
    """A lookahead that refuses a bare number followed by some other unit: for 7 s,
    "7 days" states a different quantity."""
    if unit is None:
        return ""
    return "(?!" + "|".join(_unit_names(u) for u in UNITS if u is not unit) + ")"


# Words before "a second", "a day" or "an hour" that make it a length of time, as in
# "after a second" or "within an hour". Without one, "a second request" is an ordinal
# and "10,000 calls a day" is a rate, so neither is listed.
_TIME_CONTEXT = re.compile(r"\b(?:for|after|within|every|in|once|than|about|around|under|over|least"
                           r"|most|to|past|last|lasts|take|takes|wait|waits)[\s\xa0]+$", re.I)


def _in_time_context(text: str, start: int, end: int) -> bool:
    return bool(_TIME_CONTEXT.search(text[:start]))


def _idioms(unit: Unit, q: float) -> list[tuple[str, bool]]:
    """(regex, needs a time word before it) for the idioms that state q of unit."""
    s = unit.singular
    if not s:
        return []
    article = "an" if s[0] in "aeiouh" else "a"
    if q == 1:
        return [(rf"{article}[\s-]+{s}(?![\s-]+and[\s-]+a[\s-]+half)", True)]
    if q == 0.5:
        return [(rf"half[\s-]+{article}[\s-]+{s}", False), (rf"half[\s-]?{s}", False)]
    if q == 1.5:
        return [(rf"{article}[\s-]+{s}[\s-]+and[\s-]+a[\s-]+half", False),
                (rf"one[\s-]+and[\s-]+a[\s-]+half[\s-]+{s}s", False)]
    if q == 0.25 and unit.key == "h":
        return [(r"(?:a[\s-]+)?quarter[\s-]+of[\s-]+an[\s-]+hour", False),
                (r"(?:a[\s-]+)?quarter[\s-]?hour", False)]
    return []


# Numbers that are not quantities: ISO dates, clock times, version strings and issue
# numbers. They are blanked, keeping their length, before any number is matched.
_NOT_A_VALUE = re.compile(r"\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b"  # 2026-06-30
                          r"|\b\d{1,2}:\d{2}(?::\d{2})?\b"  # 02:30
                          r"|\bv?\d+(?:\.\d+){2,}\b"  # 1.2.0
                          r"|#\d+\b")  # issue #4


def mask(text: str) -> str:
    return _NOT_A_VALUE.sub(lambda m: "\x00" * len(m.group(0)), text)


@dataclass
class Value:
    raw: str
    amount: float | None = None  # None: match raw as literal text
    unit: Unit | None = None
    given: str = ""  # the digits as written

    def label(self) -> str:
        if self.amount is None:
            return self.raw
        return f"{fmt(self.amount)} {self.unit.key}" if self.unit else fmt(self.amount)


VALUE_RE = re.compile(r"^\s*(\d{1,3}(?:,\d{3})+|\d+)(\.\d+)?\s*([A-Za-z]+)?\s*$")


def parse_value(raw: str, default_unit: Unit | None) -> Value:
    match = VALUE_RE.match(raw)
    if not match:
        return Value(raw)
    unit = default_unit
    if match.group(3):
        unit = find_unit(match.group(3))
        if unit is None:
            return Value(raw)
    given = match.group(1) + (match.group(2) or "")
    return Value(raw, float(given.replace(",", "")), unit, given)


@dataclass
class Pattern:
    kind: str  # digits | word | unit | text
    means: str  # the value the form stands for, as "7200 s"
    regex: re.Pattern
    check: Callable[[str, int, int], bool] | None = None


def patterns_for(value: Value) -> list[Pattern]:
    if value.amount is None:
        text = re.escape(value.raw)
        before = r"(?<![\w-])" if re.match(r"[\w-]", value.raw) else ""
        after = r"(?![\w-])" if re.search(r"[\w-]$", value.raw) else ""
        return [Pattern("text", "", re.compile(before + text + after))]
    label = value.label()
    other = _other_unit(value.unit)
    out = [Pattern("digits", label, re.compile(
        DIGIT_BEFORE + "(?:" + _alt(map(re.escape, digit_forms(value.amount, value.given)))
        + ")" + DIGIT_AFTER + NO_SCALE + other))]
    if value.amount == int(value.amount):
        words = number_words(int(value.amount))
        if words:
            out.append(Pattern("word", label, re.compile(
                r"(?<![\w-])(?:" + _alt(map(_word_regex, words)) + r")(?!\w)" + other, re.I), _word_ok))
    if value.unit is None:
        return out
    for unit, q, binary in equivalents(value.amount, value.unit):
        means = f"{fmt(q)} {unit.key}" + (" read as 1024-based" if binary else "")
        means = label if means == label else f"{means} = {label}"
        digits = _alt(map(re.escape, digit_forms(q)))
        out.append(Pattern("unit", means, re.compile(
            DIGIT_BEFORE + "(?:" + digits + ")" + _unit_names(unit), re.I)))
        spelled = number_words(int(q)) - {"twice", "dozen"} if q == int(q) else set()
        if spelled:
            words = _alt(map(_word_regex, spelled))
            out.append(Pattern("unit", means, re.compile(
                r"(?<![\w-])(?:" + words + ")" + _unit_names(unit, spelled=True), re.I),
                lambda text, start, end: not _BEFORE_WORD.search(text[:start])))
        for idiom, needs_context in _idioms(unit, q):
            out.append(Pattern("unit", means, re.compile(r"(?<![\w-])" + idiom + r"(?!\w)", re.I),
                               _in_time_context if needs_context else None))
    return out


@dataclass
class Match:
    form: str
    kind: str
    means: str


def _spans(text: str, patterns: list[Pattern]) -> list[tuple[int, int, Match]]:
    spans = []
    numbers = mask(text)  # numeric forms never match inside a date, time, version or #N
    for pattern in patterns:
        haystack = text if pattern.kind == "text" else numbers
        for m in pattern.regex.finditer(haystack):
            if m.end() > m.start() and (pattern.check is None or pattern.check(haystack, m.start(), m.end())):
                spans.append((m.start(), m.end(), Match(text[m.start():m.end()], pattern.kind, pattern.means)))
    spans.sort(key=lambda s: (s[0], s[0] - s[1]))
    kept, end = [], -1
    for start, stop, match in spans:  # the longest form wins where forms overlap
        if start >= end:
            kept.append((start, stop, match))
            end = stop
    return kept


def find(text: str, patterns: list[Pattern]) -> list[Match]:
    return [match for _, _, match in _spans(text, patterns)]


# --------------------------------------------------------------------- prose


@dataclass
class Prose:
    line: int
    where: str  # comment | docstring | string | doc | fenced
    text: str


def _lines_of(start: int, where: str, body: str) -> list[Prose]:
    return [Prose(start + offset, where, line) for offset, line in enumerate(body.splitlines())]


def python_prose(source: str, strings: bool = False) -> list[Prose]:
    out = []
    try:
        for token in tokenize.generate_tokens(io.StringIO(source).readline):
            if token.type == tokenize.COMMENT:
                out.append(Prose(token.start[0], "comment", token.string.lstrip("#")))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        pass
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError):
        return out
    docs = set()
    for node in ast.walk(tree):
        # Docstrings and bare strings used as comments, such as one after a constant.
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) \
                and isinstance(node.value.value, str):
            docs.add(id(node.value))
            out += _lines_of(node.value.lineno, "docstring", node.value.value)
    if strings:  # help text, error and log messages: what users read about the value
        out += [p for node in ast.walk(tree) if isinstance(node, ast.Constant)
                and isinstance(node.value, str) and id(node) not in docs
                for p in _lines_of(node.lineno, "string", node.value)]
    return sorted(out, key=lambda p: p.line)


_SLASH_TOKEN = re.compile(r"(?P<comment>//[^\n]*|/\*.*?\*/)|(?P<string>\"(?:\\.|[^\"\\\n])*\""
                          r"|'(?:\\.|[^'\\\n])*'|`(?:\\.|[^`\\])*`)", re.S)
_HASH_TOKEN = re.compile(r"(?P<comment>(?<![^\s])#[^\n]*|^[ \t]*;[^\n]*)|(?P<string>\"(?:\\.|[^\"\\\n])*\""
                         r"|'[^'\n]*')", re.M)


def scanned_prose(source: str, token: re.Pattern, strings: bool = False) -> list[Prose]:
    """Comments (and, with strings, string literals) found by one left-to-right scan, so a
    quote inside a comment does not open a string and a comment marker inside a string is
    not a comment."""
    out = []
    for match in token.finditer(source):
        start = source.count("\n", 0, match.start()) + 1
        if match.group("comment") is None:
            if strings:
                out += _lines_of(start, "string", match.group("string")[1:-1])
            continue
        body = re.sub(r"^\s*(//+|/\*+|#+|;+)|\*+/$", "", match.group("comment"))
        for offset, line in enumerate(body.splitlines()):
            out.append(Prose(start + offset, "comment", re.sub(r"^\s*\*\s?", "", line)))
    return out


_FENCE = re.compile(r"^\s*(```|~~~)")


def doc_prose(source: str) -> list[Prose]:
    out, fenced = [], False
    for number, line in enumerate(source.split("\n"), 1):
        if _FENCE.match(line):
            fenced = not fenced
            continue
        out.append(Prose(number, "fenced" if fenced else "doc", line))
    return out


def prose_of(path: Path, strings: bool = False) -> list[Prose]:
    suffix, name = path.suffix.lower(), path.name
    if suffix in PY:
        kind = "py"
    elif suffix in SLASH:
        kind = "slash"
    elif suffix in HASH or name in HASH_NAMES:
        kind = "hash"
    elif suffix in DOCS or (not path.suffix and name.upper() in DOC_NAMES):
        kind = "doc"
    else:
        return []
    try:
        if path.stat().st_size > MAX_BYTES:
            return []
        source = path.read_bytes().decode("utf-8-sig").replace("\r\n", "\n")
    except (OSError, UnicodeDecodeError):
        return []
    if kind == "py":
        return python_prose(source, strings)
    if kind == "doc":
        return doc_prose(source)
    return scanned_prose(source, _SLASH_TOKEN if kind == "slash" else _HASH_TOKEN, strings)


def iter_files(root: Path) -> list[Path]:
    if root.is_file():
        return [root]
    out = []
    top = root.resolve()
    for directory, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS and not d.endswith(".egg-info")
                         and not (Path(directory, d).resolve() == SELF_DIR and SELF_DIR != top))
        out += [Path(directory, f) for f in sorted(files)]
    return out


# --------------------------------------------------------------------- hints

RECORD_NAME = re.compile(r"^(changelog|changes|history|news|releases?|release[-_ ]?notes|upgrading"
                         r"|migrating)\b", re.I)
RECORD_WORD = re.compile(r"migration|postmortem|post-mortem|incident", re.I)  # doc names only
RECORD_DIRS = {"adr", "adrs", "decisions", "decision-records", "migrations", "postmortems",
               "post-mortems", "incidents", "changelog", "changelogs", "release-notes", "releases"}
DATED = re.compile(r"(?<!\d)(?:19|20)\d\d[-_.]?(?:0[1-9]|1[0-2])(?:[-_.]?(?:0[1-9]|[12]\d|3[01]))?(?!\d)")
INSTRUCTION_NAMES = {"agents.md", "claude.md", "gemini.md", "copilot-instructions.md",
                     ".cursorrules", ".windsurfrules"}


def path_hints(rel: str) -> list[str]:
    """A guess from the path alone. A record is true about its own date or version; the
    guess cannot see that, so it only says where to look twice."""
    parts = rel.split("/")
    name = parts[-1]
    is_doc = Path(name).suffix.lower() in DOCS or not Path(name).suffix
    if name.lower() in INSTRUCTION_NAMES or "/".join(parts[:2]).lower() == ".github/instructions":
        return ["instructions?"]
    if RECORD_NAME.search(name) or (is_doc and RECORD_WORD.search(name)) \
            or any(p.lower() in RECORD_DIRS for p in parts[:-1]) or any(DATED.search(p) for p in parts):
        return ["record?"]
    return []


# ---------------------------------------------------------------------- scan


@dataclass
class Hit:
    path: str
    line: int
    where: str
    text: str
    matches: list[Match]
    hints: list[str] = field(default_factory=list)


def _near(proses: list[Prose], i: int, near: re.Pattern) -> bool:
    """The line, or the prose line straight before or after it, matches near. A wrapped
    comment or docstring often names its subject on the neighbouring line."""
    line = proses[i].line
    around = [p.text for p in proses[max(0, i - 1):i + 2] if abs(p.line - line) <= 1]
    return any(near.search(text) for text in around)


# A line that opens a new Markdown block (list item, quote, table row, heading) does not
# continue the sentence on the line before it, and nothing continues a heading or a row.
_BLOCK_START = re.compile(r"^\s*(?:[-*+>|]|#{1,6}|\d+[.)])(?:\s|$)")
_ONE_LINE_BLOCK = re.compile(r"^\s*(?:\||#{1,6}(?:\s|$))")


def _found_on_line(proses: list[Prose], i: int, patterns: list[Pattern]) -> list[Match]:
    """The forms that start on line i. When the next prose line continues the same
    sentence, the two are read as one, so a form wrapped across the break ("half an" /
    "hour") is found, and a number is judged by the unit that follows it there."""
    here = proses[i]
    there = proses[i + 1] if i + 1 < len(proses) else None
    head = here.text.rstrip()
    if there is None or there.line != here.line + 1 or there.where != here.where or not head \
            or not there.text.strip() or _BLOCK_START.match(there.text) or _ONE_LINE_BLOCK.match(here.text):
        return find(here.text, patterns)
    joined = head + ("" if head.endswith("-") else " ") + there.text.strip()
    return [match for start, _, match in _spans(joined, patterns) if start < len(head)]


def scan(root: Path, patterns: list[Pattern], new_patterns: list[Pattern] | None = None,
         near: re.Pattern | None = None, strings: bool = False) -> list[Hit]:
    hits = []
    base = root.parent if root.is_file() else root
    for path in iter_files(root):
        rel = path.relative_to(base).as_posix()
        proses = prose_of(path, strings)
        for i, prose in enumerate(proses):
            matches = _found_on_line(proses, i, patterns)
            if not matches or (near and not _near(proses, i, near)):
                continue
            hints = path_hints(rel)
            if new_patterns and _found_on_line(proses, i, new_patterns):
                hints.append("states new")
            hits.append(Hit(rel, prose.line, prose.where, " ".join(prose.text.split()), matches, hints))
    return sorted(hits, key=lambda h: (h.path, h.line))


def describe(value: Value) -> str:
    if value.amount is None:
        return f"text {value.raw!r}"
    if value.unit is None:
        return value.label()
    others = [f"{fmt(q)} {u.key}" + (" (1024-based)" if b else "")
              for u, q, b in equivalents(value.amount, value.unit) if not (u is value.unit and not b)]
    return " = ".join([value.label()] + others)


def render(hit: Hit) -> str:
    hints = f" [{', '.join(hit.hints)}]" if hit.hints else ""
    forms = ", ".join(dict.fromkeys(f'"{m.form}"' + (f" = {m.means}" if m.means else "")
                                    for m in hit.matches))
    text = hit.text if len(hit.text) <= 200 else hit.text[:197] + "..."
    return f"{hit.path}:{hit.line}: {hit.where}{hints}: {forms}: {text}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="value_drift.py", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("root", type=Path, help="the repository root, or one file")
    parser.add_argument("--old", action="append", required=True, metavar="VALUE",
                        help="an old value, a figure derived from it, or an old name; repeat it")
    parser.add_argument("--new", metavar="VALUE", help="the new value, to print its units and mark lines that state it")
    parser.add_argument("--unit", metavar="UNIT", help="the unit of numeric values that carry none: "
                        + ", ".join(u.key for u in UNITS))
    parser.add_argument("--near", metavar="REGEX",
                        help="keep only hits whose line or a neighbouring prose line matches REGEX "
                             "(ignoring case); use it for small values")
    parser.add_argument("--strings", action="store_true",
                        help="also read string literals in code, such as help text and error messages")
    parser.add_argument("--json", action="store_true", help="print the hits as JSON")
    parser.add_argument("--check", action="store_true", help="exit 1 when any line matches, for CI")
    args = parser.parse_args(argv)
    unit = None
    if args.unit:
        unit = find_unit(args.unit)
        if unit is None:
            parser.error(f"unknown unit {args.unit!r}; use one of {', '.join(u.key for u in UNITS)}")
    if not args.root.exists():
        parser.error(f"{args.root} does not exist")
    near = None
    if args.near:
        try:
            near = re.compile(args.near, re.I)
        except re.error as error:
            parser.error(f"--near is not a regular expression: {error}")
    olds = [parse_value(raw, unit) for raw in args.old]
    new = parse_value(args.new, unit) if args.new else None
    hits = scan(args.root, [p for v in olds for p in patterns_for(v)], patterns_for(new) if new else None,
                near, args.strings)
    status = 1 if hits and args.check else 0

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    if args.json:
        print(json.dumps({"old": [describe(v) for v in olds], "new": describe(new) if new else None,
                          "near": args.near, "hits": [asdict(h) for h in hits]}, indent=1))
        return status
    for value in olds:
        print(f"old {describe(value)}")
    if new:
        print(f"new {describe(new)}")
    for hit in hits:
        print(render(hit))
    narrowed = f" near /{args.near}/" if args.near else ""
    if hits:
        files = len({h.path for h in hits})
        print(f"Prose lines with an old form{narrowed}: {len(hits)}, in {files} file{'s' * (files != 1)}. "
              "These are candidates: read each in context and decide.")
    else:
        print(f"No comment, docstring or doc line{narrowed} states an old form. The search covers digits, "
              "number words and round unit conversions, not paraphrase or figures you did not pass.")
    return status


if __name__ == "__main__":
    sys.exit(main())
