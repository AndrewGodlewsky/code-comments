"""Mechanical checks for the fold-docs-inline eval.

Each case's ``graders/`` folder holds one statement per file. ``CHECKS`` holds one check
per statement, in the same order. A check takes the run's repository (``out``) and the
case's untouched ``files/`` (``orig``) and returns ``(passed, evidence)``.

Every case retires or slims one named docs page. The checks grade only what nobody
disputes about that job:
- a claim the code contradicts reaches no added comment, docstring or other document
  line, however it is phrased: a negated or "the page said" line counts too;
- the page's restatements of the code are not copied into comments;
- a moved fact has one home: it is in the code and no longer in any document (an
  instruction file the run may not edit is set aside);
- a note with no code to sit beside stays in exactly one document;
- the code does not change (compared by AST, plus hidden behaviour tests where a stale
  claim invites "fixing" the code to match it), and no file is added;
- the reply flags each stale claim and gives every claim on the page a fate.

Placement beside the governing symbol is a secondary, heuristic check (grader weight
0.5); it accepts the symbol the fact names and the code that uses it. Where a
big-picture claim belongs (a module docstring or a document) is an open question for the
user, so no check grades it. Checks that rest on keywords say "(heuristic)" in their
evidence; a misgraded run gets an ``overrides.json`` ruling.

The stale checks of the two cases rebuilt after the derivability gate
(``stale-number-elsewhere`` and ``stale-ordering-reason``) read whole comment blocks,
docstrings and Markdown paragraphs, split into sentences, so a claim wrapped over two
docstring lines is still seen. The other cases keep their line-level checks.
"""

from __future__ import annotations

import ast
import io
import re
import sys
import tokenize
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from gradelib import (files, lost_prose, new_files, prose, reply, run_hidden_tests, show,  # noqa: E402
                      text)

HERE = Path(__file__).resolve().parent
HIDDEN = HERE / "hidden"


# --------------------------------------------------------------------- reading


def _norm(value: str) -> str:
    return re.sub(r"\s+", " ", value)


def _rels(root: Path, suffix: str) -> list[str]:
    return [p.relative_to(root).as_posix() for p in files(root, {suffix})]


def code_prose(root: Path) -> dict[str, str]:
    """Each Python file's comments and docstrings, joined into one string."""
    return {rel: _norm(" ".join(prose(root / rel))) for rel in _rels(root, ".py")}


def doc_text(root: Path) -> dict[str, str]:
    """Each Markdown file's text (the run's RESPONSE.md is not a document)."""
    return {rel: _norm(text(root / rel)) for rel in _rels(root, ".md")}


def _added(out: Path, orig: Path, suffix: str, skip: tuple[str, ...] = ()) -> list[tuple[str, str]]:
    found = []
    for rel in _rels(out, suffix):
        if rel in skip:
            continue
        before = Counter(prose(orig / rel)) if (orig / rel).is_file() else Counter()
        found += [(rel, line) for line in (Counter(prose(out / rel)) - before).elements()]
    return found


def added_code_lines(out: Path, orig: Path) -> list[tuple[str, str]]:
    """(file, line) for each comment or docstring line in out's Python that orig lacks."""
    return _added(out, orig, ".py")


def added_doc_lines(out: Path, orig: Path, page: str) -> list[tuple[str, str]]:
    """(file, line) for each Markdown line that orig lacks, outside the retired page."""
    return _added(out, orig, ".md", skip=(page,))


def _py_blocks(source: str) -> list[str]:
    """A Python file's comment blocks (comments on consecutive lines, joined) and its
    docstrings, each as one whitespace-normalised string."""
    blocks, run, last = [], [], None
    try:
        for token in tokenize.generate_tokens(io.StringIO(source).readline):
            if token.type != tokenize.COMMENT:
                continue
            row = token.start[0]
            if run and row != last + 1:
                blocks.append(" ".join(run))
                run = []
            body = token.string.lstrip("#").strip()
            if body:
                run.append(body)
            last = row
    except (tokenize.TokenError, IndentationError, SyntaxError):
        pass
    if run:
        blocks.append(" ".join(run))
    try:
        tree = ast.parse(source)
    except SyntaxError:
        tree = None
    for node in ast.walk(tree) if tree else []:
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            doc = ast.get_docstring(node, clean=True)
            if doc:
                blocks.append(doc)
    return [_norm(block).strip() for block in blocks if block.strip()]


def blocks(path: Path) -> list[str]:
    """Comment blocks and docstrings of a Python file, or the bullets and paragraphs of a
    Markdown file."""
    if path.suffix == ".py":
        return _py_blocks(text(path))
    if path.suffix == ".md":
        return [_norm(block) for block in reply_blocks(text(path))]
    return []


def added_blocks(out: Path, orig: Path, page: str) -> list[tuple[str, str]]:
    """(file, block) for each comment block, docstring or Markdown paragraph in out that
    orig lacks, outside the retired page. An extended docstring counts as added whole."""
    found = []
    for path in files(out, {".py", ".md"}):
        rel = path.relative_to(out).as_posix()
        if rel == page:
            continue
        before = Counter(blocks(orig / rel)) if (orig / rel).is_file() else Counter()
        found += [(rel, block) for block in (Counter(blocks(path)) - before).elements()]
    return found


def sentences(block: str) -> list[str]:
    return [s for s in re.split(r"(?<=[.;!?])\s+", block) if s.strip()]


def stale_sentences(out: Path, orig: Path, page: str, always: str | None, unless: str | None = None,
                    exempt: str | None = None) -> list[str]:
    """Sentences of added blocks that match ``always``, or that match ``unless`` without
    matching ``exempt``."""
    hits = []
    for rel, block in added_blocks(out, orig, page):
        for sentence in sentences(block):
            if (always and re.search(always, sentence, re.IGNORECASE)) or (
                    unless and re.search(unless, sentence, re.IGNORECASE)
                    and not (exempt and re.search(exempt, sentence, re.IGNORECASE))):
                hits.append(f"{rel}: {sentence!r}")
    return hits


class _DropDocstrings(ast.NodeTransformer):
    """Remove docstrings without padding the body. gradelib.code_shape pads an emptied body
    with ``pass``, so a docstring added to an empty ``__init__.py`` would look like code."""

    def _strip(self, node):
        self.generic_visit(node)
        body = node.body
        if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                and isinstance(body[0].value.value, str):
            node.body = body[1:]
        return node

    visit_Module = visit_FunctionDef = visit_AsyncFunctionDef = visit_ClassDef = _strip


def code_shape(path: Path) -> str | None:
    """A Python file's code with comments and docstrings removed, or None if unreadable."""
    if not path.is_file():
        return None
    try:
        return ast.dump(_DropDocstrings().visit(ast.parse(text(path))))
    except SyntaxError:
        return None


def _find(body, name):
    for node in body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.name == name:
            return node
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
            return node
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == name:
            return node
    return None


def symbol_prose(path: Path, qualname: str) -> list[str] | None:
    """Comment lines inside a symbol or in the comment block directly above it, plus its
    docstring. None when the file or the symbol is missing."""
    if not path.is_file():
        return None
    source = text(path)
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    body, node = tree.body, None
    for part in qualname.split("."):
        node = _find(body, part)
        if node is None:
            return None
        body = getattr(node, "body", [])
    lines = source.splitlines()
    start = min([node.lineno] + [d.lineno for d in getattr(node, "decorator_list", [])])
    while start > 1 and lines[start - 2].strip().startswith("#"):
        start -= 1
    found = []
    try:
        for token in tokenize.generate_tokens(io.StringIO(source).readline):
            if token.type == tokenize.COMMENT and start <= token.start[0] <= node.end_lineno:
                comment = token.string.lstrip("#").strip()
                if comment:
                    found.append(comment)
    except (tokenize.TokenError, IndentationError, SyntaxError):
        pass
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        doc = ast.get_docstring(node, clean=True)
        if doc:
            found += [line.strip() for line in doc.splitlines() if line.strip()]
    return found


# ------------------------------------------------------------- check builders


def stale_kept_out(out: Path, orig: Path, page: str, pattern: str, label: str,
                   doc_pattern: str | None = None) -> tuple[bool, str]:
    """No added comment or docstring line, and no added line in a document other than the
    retired page, states the stale claim. There is no exemption for negated lines: the
    code never holds the stale value, and a "the page said X" note is history, which the
    not-migrated fate keeps out of the code. Documents use ``doc_pattern`` when given,
    because other documents may legitimately hold the bare number in another sense."""
    hits = [f"{rel}: {line!r}" for rel, line in added_code_lines(out, orig)
            if re.search(pattern, line, re.IGNORECASE)]
    hits += [f"{rel}: {line!r}" for rel, line in added_doc_lines(out, orig, page)
             if re.search(doc_pattern or pattern, line, re.IGNORECASE)]
    if hits:
        return False, f"{label} in an added line: {'; '.join(hits[:3])} (heuristic)"
    return True, f"no added comment, docstring or document line states {label} (heuristic)"


def one_home_in_code(out: Path, pattern: str, label: str, ignore: tuple[str, ...] = ()) -> tuple[bool, str]:
    """The fact is in some code comment or docstring and in no Markdown document, apart
    from ``ignore`` (an instruction file the run must leave alone)."""
    in_code = [rel for rel, body in code_prose(out).items() if re.search(pattern, body, re.IGNORECASE)]
    in_docs = [rel for rel, body in doc_text(out).items()
               if rel not in ignore and re.search(pattern, body, re.IGNORECASE)]
    evidence = f"{label}: in code prose {in_code or 'nowhere'}; in documents {in_docs or 'none'}"
    if ignore:
        evidence += f" (ignoring {', '.join(ignore)})"
    return bool(in_code) and not in_docs, evidence


def stays_in_one_doc(out: Path, notes: dict[str, str]) -> tuple[bool, str]:
    """Each note is in exactly one Markdown document and in no code comment or docstring."""
    problems, homes = [], []
    code, docs = code_prose(out), doc_text(out)
    for label, pattern in notes.items():
        in_docs = [rel for rel, body in docs.items() if re.search(pattern, body, re.IGNORECASE)]
        in_code = [rel for rel, body in code.items() if re.search(pattern, body, re.IGNORECASE)]
        if len(in_docs) != 1:
            problems.append(f"{label} in {len(in_docs)} documents {in_docs}")
        if in_code:
            problems.append(f"{label} in code prose {in_code}")
        homes.append(f"{label} -> {in_docs}")
    return not problems, "; ".join(problems) if problems else "; ".join(homes)


def not_in_code(out: Path, notes: dict[str, str]) -> tuple[bool, str]:
    code = code_prose(out)
    hits = [f"{label} in {rel}" for label, pattern in notes.items()
            for rel, body in code.items() if re.search(pattern, body, re.IGNORECASE)]
    return not hits, f"found {hits}" if hits else "no code comment or docstring carries them"


def beside(out: Path, homes: list[tuple[str, str]], pattern: str, label: str) -> tuple[bool, str]:
    """The fact is in one of the homes' own comments or docstring, or in a comment line of
    the home's file that names the symbol (heuristic placement). A home is the symbol the
    fact names or the code that uses it."""
    seen = []
    for rel, symbol in homes:
        lines = symbol_prose(out / rel, symbol)
        if lines is None:
            seen.append(f"{symbol} not found in {rel}")
            continue
        if re.search(pattern, " ".join(lines), re.IGNORECASE):
            return True, f"{label} is at {symbol} in {rel} (heuristic)"
        name = symbol.split(".")[-1]
        naming = [line for line in prose(out / rel) if name in line and re.search(pattern, line, re.IGNORECASE)]
        if naming:
            return True, f"{label} is in a {rel} line naming {name}: {naming[0]!r} (heuristic)"
        seen.append(f"{symbol} in {rel} has {lines[:3]}")
    return False, f"{label} at none of {[s for _, s in homes]}: {'; '.join(seen)} (heuristic)"


def symbols_quiet(out: Path, orig: Path, rel: str, symbols: list[str], allow: str | None = None) -> tuple[bool, str]:
    """No comment or docstring line was added in or directly above these symbols, apart from
    lines matching ``allow``."""
    added, allowed = [], []
    for symbol in symbols:
        after = symbol_prose(out / rel, symbol)
        if after is None:
            return False, f"{symbol} not found in {rel}"
        new = Counter(after) - Counter(symbol_prose(orig / rel, symbol) or [])
        for line in new.elements():
            (allowed if allow and re.search(allow, line, re.IGNORECASE) else added).append(f"{symbol}: {line!r}")
    note = f"; allowed {allowed}" if allowed else ""
    return not added, (f"added {added[:3]}" if added else f"nothing added in {', '.join(symbols)}") + note


def no_restatement(out: Path, orig: Path, anchors: dict[str, str], quiet_files: tuple[str, ...] = (),
                   quiet_symbols: tuple[str, list[str], str | None] | None = None) -> tuple[bool, str]:
    """No added comment or docstring line carries one of the page's restating clauses
    (narrow anchors), quiet files gain no comment or docstring line at all, and quiet
    symbols gain none apart from lines matching their allow pattern."""
    problems = []
    added = added_code_lines(out, orig)
    for label, pattern in anchors.items():
        hits = [f"{rel}: {line!r}" for rel, line in added if re.search(pattern, line, re.IGNORECASE)]
        if hits:
            problems.append(f"{label} restated: {hits[0]}")
    for rel in quiet_files:
        hits = [line for where, line in added if where == rel]
        if hits:
            problems.append(f"{rel} gained {hits[:2]}")
    if quiet_symbols:
        rel, symbols, allow = quiet_symbols
        ok, evidence = symbols_quiet(out, orig, rel, symbols, allow)
        if not ok:
            problems.append(evidence)
    if problems:
        return False, "; ".join(problems[:3]) + " (heuristic)"
    scope = f"; {', '.join(quiet_files)} gained nothing" if quiet_files else ""
    return True, f"no restating clause copied{scope} (heuristic)"


def code_unchanged(out: Path, orig: Path, case: str | None = None) -> tuple[bool, str]:
    """Every original Python file's code (comments and docstrings aside) is unchanged, and
    the case's hidden behaviour tests pass when it has any."""
    changed = [rel for rel in _rels(orig, ".py") if code_shape(out / rel) != code_shape(orig / rel)]
    evidence = f"code changed in {changed}" if changed else "code unchanged"
    ok = not changed
    if case is not None:
        passed, detail = run_hidden_tests(out, HIDDEN / case)
        ok = ok and passed
        evidence += f"; {detail}"
    return ok, evidence


def kept_except(out: Path, orig: Path, page: str, frozen: tuple[str, ...] = ()) -> tuple[bool, str]:
    """No original prose line is lost outside the retired page, and frozen files (such as
    instruction files) are byte-for-byte unchanged."""
    lost = {rel: lines for rel, lines in lost_prose(out, orig).items() if rel != page}
    changed = [rel for rel in frozen if not (out / rel).is_file() or text(out / rel) != text(orig / rel)]
    problems = ([f"lost {show(lost)}"] if lost else []) + ([f"changed {changed}"] if changed else [])
    return not problems, "; ".join(problems) if problems else "every original line kept" + \
        (f"; {', '.join(frozen)} unchanged" if frozen else "")


def no_new_files(out: Path, orig: Path) -> tuple[bool, str]:
    added = new_files(out, orig)
    return not added, f"added {added}" if added else "no file added"


# ------------------------------------------------------------------ the reply

_BULLET = re.compile(r"^([-*+]|\d+[.)])\s+")


def reply_blocks(body: str) -> list[str]:
    """The reply split into bullets, table rows and paragraphs. An indented bullet joins
    the bullet above it, so a sub-point stays with its claim."""
    blocks, current = [], []
    for raw in body.splitlines():
        line = raw.strip()
        indented = raw[:1].isspace()
        starts = not line or line.startswith(("#", "|")) or (_BULLET.match(line) and not indented)
        if starts:
            if current:
                blocks.append(" ".join(current))
            current = [line] if line else []
        else:
            current.append(line)
    if current:
        blocks.append(" ".join(current))
    return [b for b in blocks if b]


def reply_block(out: Path, *patterns: str) -> tuple[bool, str]:
    """One bullet, table row or paragraph of the reply matches every pattern."""
    body = reply(out)
    if not body:
        return False, "no RESPONSE.md"
    for block in reply_blocks(body):
        if all(re.search(p, block, re.IGNORECASE) for p in patterns):
            return True, f"reply block matches: {block[:120]!r} (heuristic)"
    return False, f"no single reply block matches all of {list(patterns)} (heuristic)"


def reply_each(out: Path, claims: dict[str, str]) -> tuple[bool, str]:
    """The reply mentions every claim on the page, by one anchor per claim."""
    body = reply(out)
    if not body:
        return False, "no RESPONSE.md"
    missing = [label for label, pattern in claims.items() if not re.search(pattern, body, re.IGNORECASE)]
    if missing:
        return False, f"reply gives no fate for {missing} (heuristic)"
    return True, f"reply names all {len(claims)} claims (heuristic)"


def reply_matches(out: Path, *patterns: str) -> tuple[bool, str]:
    body = reply(out)
    if not body:
        return False, "no RESPONSE.md"
    missing = [p for p in patterns if not re.search(p, body, re.IGNORECASE)]
    return not missing, (f"reply lacks {missing}" if missing else "reply matches every pattern") + " (heuristic)"


# ---------------------------------------------------- 1. stale-number-elsewhere

S1_PAGE = "docs/order-sync.md"
# The page says the attempts are "2 seconds apart"; pause_after() in orders/backoff.py
# doubles each pause (2, 4, 8, 16). A sentence states the stale spacing when it says
# "apart", "every 2 seconds" or "a fixed pause", or when it puts 2 seconds (or
# PAUSE_SECONDS) between attempts without saying the pauses grow or that 2 is the first.
FIXED_GAP = (r"\bapart\b|\b(every|each)\s+(2|two)\s+seconds?\b|\b(2|two)[- ]second (spacing|intervals?|gaps?)\b"
             r"|\b(fixed|constant|flat|steady|equal|same|uniform|regular)\b[^.]{0,20}"
             r"\b(pauses?|delays?|waits?|intervals?|gaps?|spacing)\b")
TWO_BETWEEN = (r"\b(PAUSE_SECONDS|(2|two)[- ]seconds?)\b[^.]{0,40}\b(between|after each|after every|before each"
               r"|before every)\b|\b(between|after each|after every|before each|before every)\b[^.]{0,40}"
               r"\b(PAUSE_SECONDS|(2|two)[- ]seconds?)\b")
GROWING = r"doubl|\bgrows?\b|increas|exponential|back-?off|\*\*|\bfirst\b|longer|\blater\b|\b(4|8|16)\b|pause_after"
OPS19 = r"OPS-19|maintenance|(one|1) (request )?in (a|one|1) ?(thousand|1,?000)|1/1,?000"
PAGE_SIZE_RULE = r"\b250\b"


def s1_no_fixed_gap(out, orig):
    hits = stale_sentences(out, orig, S1_PAGE, FIXED_GAP, TWO_BETWEEN, GROWING)
    if hits:
        return False, f"the fixed 2-second spacing in an added sentence: {'; '.join(hits[:3])} (heuristic)"
    return True, "no added comment, docstring or document sentence states a fixed 2-second spacing (heuristic)"


def s1_retry_reason(out, orig):
    return one_home_in_code(out, OPS19, "the OPS-19 retry reason")


def s1_page_size(out, orig):
    return one_home_in_code(out, PAGE_SIZE_RULE, "the 250 page-size limit")


def s1_placement(out, orig):
    a = beside(out, [("orders/client.py", "ShopClient.get_page"), ("orders/settings.py", "ATTEMPTS"),
                     ("orders/settings.py", "PAUSE_SECONDS"), ("orders/backoff.py", "pause_after")],
               OPS19, "the OPS-19 reason")
    b = beside(out, [("orders/client.py", "PAGE_SIZE"), ("orders/client.py", "ShopClient.get_page")],
               PAGE_SIZE_RULE, "the page-size rule")
    return a[0] and b[0], f"{a[1]}; {b[1]}"


def s1_restatement(out, orig):
    return no_restatement(out, orig, {
        "one page at a time": r"page at a time",
        "the empty page": r"empty page|no more orders",
        "up to 5 tries": r"\bup to (5|five)\b|\b(5|five) (times|tries|attempts)\b",
        "upsert by id": r"same order id|replaces? (any|the|an?) (stored|existing) order",
    }, quiet_files=("orders/sync.py", "orders/store.py"))


def s1_code(out, orig):
    return code_unchanged(out, orig, "stale-number-elsewhere")


def s1_kept(out, orig):
    return kept_except(out, orig, S1_PAGE)


def s1_reply_stale(out, orig):
    return reply_block(out, r"\bapart\b|\b(2|two)[- ]seconds?\b|PAUSE_SECONDS|spacing|fixed (pause|delay|gap)",
                       r"doubl|exponential|\bgrows?\b|increas|\b(4|8|16)\b|longer|\*\*")


def s1_reply_each(out, orig):
    # "empty-page" and "page-by-page" were added after the gate: a Haiku reply named the
    # claim with the hyphenated words and was failed.
    return reply_each(out, {
        "paging and the empty page": r"page at a time|empty[- ](page|list)|no more orders|last page|if not orders"
                                     r"|page[- ]by[- ]page",
        "the retries": r"OPS-19|retr|attempt|\btries\b",
        "the page-size rule": r"\b250\b|PAGE_SIZE",
        "upsert": r"upsert",
    })


# ----------------------------------------------------- 2. restatement-only-page


def s2_no_prose(out, orig):
    added = added_code_lines(out, orig)
    return not added, f"added {[f'{rel}: {line!r}' for rel, line in added][:4]}" if added else "no line added"


def s2_page_removed(out, orig):
    gone = not (out / "docs/ingest.md").exists()
    return gone, "docs/ingest.md deleted" if gone else "docs/ingest.md still exists"


def s2_kept(out, orig):
    lost = {rel: lines for rel, lines in lost_prose(out, orig).items() if rel.endswith(".py")}
    changed = [rel for rel in ("README.md", "docs/deploy.md")
               if not (out / rel).is_file() or text(out / rel) != text(orig / rel)]
    problems = ([f"lost {show(lost)}"] if lost else []) + ([f"changed {changed}"] if changed else [])
    return not problems, "; ".join(problems) if problems else "docstrings kept; README.md and docs/deploy.md unchanged"


def s2_code(out, orig):
    return code_unchanged(out, orig)


def s2_reply(out, orig):
    return reply_matches(out, r"already (says?|shows?|states?|covers?|documents?|in|there|does)"
                              r"|restat\w*|duplicat\w*|repeat\w*|redundant|derivable|visible in|same as"
                              r"|nothing (new|to move|worth|needed|that needed)|no (new )?information"
                              r"|(code|docstrings?|function|body|bodies|imports?|signatures?) (already )?"
                              r"(says?|shows?|covers?|states?|reads?|gives?)\b")


def s2_reply_each(out, orig):
    return reply_each(out, {"read_rows": r"read_rows", "is_blank": r"is_blank", "parse_price": r"parse_price",
                            "clean": r"\bclean\b", "the csv-only note": r"\bcsv\b|standard library|stdlib"})


# --------------------------------------------------------- 3. slim-page-one-home

S3_PAGE = "docs/billing.md"
FIN88 = r"FIN-88|validator"


def s3_rounding(out, orig):
    return one_home_in_code(out, FIN88, "the FIN-88 rounding reason", ignore=("AGENTS.md",))


def s3_packing(out, orig):
    return one_home_in_code(out, r"packing[ -]?slip", "the packing-slip reason")


def s3_placement(out, orig):
    a = beside(out, [("billing/totals.py", "invoice_total"), ("billing/totals.py", "CENT")], FIN88,
               "the rounding reason")
    b = beside(out, [("billing/lines.py", "invoice_lines")], r"packing[ -]?slip", "the packing-slip reason")
    return a[0] and b[0], f"{a[1]}; {b[1]}"


def s3_contacts(out, orig):
    return stays_in_one_doc(out, {"FINQ": r"\bFINQ\b", "accounts-receivable lead": r"accounts[- ]receivable"})


def s3_restatement(out, orig):
    return no_restatement(out, orig, {
        "invoice_total adds and returns a Decimal": r"line amounts|adds? up the|returns? a .?Decimal",
        "invoice_lines returns the lines": r"returns? the order's lines",
    })


def s3_code(out, orig):
    return code_unchanged(out, orig)


def s3_kept(out, orig):
    return kept_except(out, orig, S3_PAGE, frozen=("AGENTS.md",))


def s3_reply(out, orig):
    return reply_matches(out, r"totals\.py|invoice_total", r"lines\.py|invoice_lines")


def s3_reply_agents(out, orig):
    return reply_block(out, r"AGENTS\.md",
                       r"FIN-88|half[- ]up|round|duplicat|repeat|also (states?|says?|has|holds|mentions|carries)")


def s3_reply_each(out, orig):
    # The "what invoice_total does ... already" anchors were added after the gate: a Sonnet
    # reply dropped the claim as "the description of what invoice_total() and
    # invoice_lines() do was already in their docstrings" and was failed.
    return reply_each(out, {
        "the invoice_total restatement": r"line amounts|\badds?\b|\bsums?\b|Decimal|rounded to the cent"
                                         r"|what\W+invoice_total|invoice_total[^.\n]{0,80}\balready\b",
        "the FIN-88 reason": r"FIN-88|half[- ]up",
        "the packing-slip reason": r"packing[- ]?slip",
        "Who to ask": r"FINQ|who to ask|accounts[- ]receivable",
    })


# ------------------------------------------------ 4. ops-notes-in-file-sections

S4_PAGE = "docs/refunds.md"
OPS_NOTES = {"#fin-ops": r"fin-ops", "90-day key rotation": r"\b90\b|ninety|rotat"}


def s4_not_in_code(out, orig):
    return not_in_code(out, OPS_NOTES)


def s4_in_one_doc(out, orig):
    return stays_in_one_doc(out, OPS_NOTES)


def s4_moved(out, orig):
    a = one_home_in_code(out, r"PAY-31|four[- ]eyes", "the PAY-31 rule")
    b = one_home_in_code(out, r"idempoten", "the idempotency-key reason")
    return a[0] and b[0], f"{a[1]}; {b[1]}"


def s4_placement(out, orig):
    a = beside(out, [("refunds/approval.py", "SECOND_APPROVER_THRESHOLD"),
                     ("refunds/approval.py", "needs_second_approver")], r"PAY-31|four[- ]eyes", "the PAY-31 rule")
    b = beside(out, [("refunds/provider.py", "send_refund")], r"idempoten", "the idempotency-key reason")
    return a[0] and b[0], f"{a[1]}; {b[1]}"


def s4_restatement(out, orig):
    # No anchor on "posts the refund": a good send_refund comment about the idempotency
    # key may use the same verb.
    return no_restatement(out, orig, {
        "the 500 EUR threshold": r"500 EUR or more|refunds of 500",
        "send_refund's return value": r"provider's refund id|returns? the (provider's )?refund id",
    })


def s4_code(out, orig):
    return code_unchanged(out, orig)


def s4_kept(out, orig):
    return kept_except(out, orig, S4_PAGE)


def s4_reply_each(out, orig):
    # The send_refund "returns" anchors were added after the gate: a Haiku reply gave the
    # claim a fate as "docstring of send_refund(): what it returns" and was failed.
    return reply_each(out, {
        "the threshold": r"needs_second_approver|\b500\b",
        "PAY-31": r"PAY-31|four[- ]eyes",
        "#fin-ops": r"fin-ops",
        "send_refund posts and returns": r"\bposts?\b|refund id|provider's id|send_refund[^.\n]{0,80}\breturns?\b"
                                         r"|\bwhat it (does and )?returns\b",
        "the idempotency key": r"idempoten",
        "the sandbox reset": r"sandbox|Monday",
        "the key rotation": r"\b90\b|rotat",
    })


# ------------------------------------------------- 5. spec-claim-code-disagrees

S5_PAGE = "docs/accounts.md"
CASE_CLAIM = (r"ACC-12|case[- ]?insensitiv|not case[- ]?sensitiv|case\W+(is\W+)?ignored"
              r"|ignor\w*\s+(the\s+)?(letter\s+)?case|regardless of case|without regard to case"
              r"|lower[- ]?cas|casefold|\.lower\(\)|same account")


def s5_no_claim(out, orig):
    return stale_kept_out(out, orig, S5_PAGE, CASE_CLAIM, "case-insensitive names")


def s5_acc30(out, orig):
    return one_home_in_code(out, r"ACC-30|spam", "the ACC-30 reason")


def s5_restatement(out, orig):
    return no_restatement(out, orig, {
        "spaces ignored": r"spaces? (before|after|around)|surrounding (white)?spaces?|(leading|trailing) (white)?spaces?"
                          r"|whitespace",
        "NameTaken": r"raises? .?NameTaken|already in use",
        "the member role": r"new accounts get|get the .?member.? role",
    })


def s5_code(out, orig):
    return code_unchanged(out, orig, "spec-claim-code-disagrees")


def s5_kept(out, orig):
    return kept_except(out, orig, S5_PAGE)


def s5_reply(out, orig):
    return reply_block(out, r"\bcase|ACC-12|capital|upper",
                       r"(?<!in)sensitiv|exact|\bstrips?\b|separate|different|distinct|two accounts|contradict"
                       r"|mismatch|out of date|stale|wrong|incorrect|inaccurate|keeps? (the )?capitals"
                       r"|(doesn't|does not|don't|do not) (lower|ignore|fold|match|do)")


def s5_reply_each(out, orig):
    return reply_each(out, {"case-insensitivity": r"\bcase|ACC-12", "spaces": r"spaces?|strip|whitespace",
                            "NameTaken": r"NameTaken", "the ACC-30 editor rule": r"ACC-30|editor|spam"})


# ---------------------------------------------------- 6. stale-ordering-reason (held out)

S6_PAGE = "docs/stock-feed.md"
# write_feed() really is a merge pass, but it sorts both of its inputs first, so nothing
# needs stock_rows() to sort. Any line added at stock_rows that ties its sort to
# write_feed, the merge or a requirement is the stale coupling, negated or not: the sort's
# real reason is unknown. Elsewhere a sentence is stale when it says the rows must arrive
# sorted or that a row out of order is skipped; a negated sentence, or one about
# write_feed sorting its own input ("itself", "here"), is a true statement of the code.
AT_SORT = (r"write_feed|merge|\bjoin|price list|single pass|one pass|out[- ]of[- ]order|silently"
           r"|\b(must|has to|have to|needs?|required?|requires|rel(y|ies)|depends?|expects?|assumes?)\b")
NEEDS_SORTED = (r"\b(must|has to|have to|needs? to|needs|should|required?|requires|rel(y|ies) on|depends? on"
                r"|expects?|assumes?)\b[^.]{0,60}\b(sorted|in (sku )?order|sku order|ordered)\b"
                r"|\bsort\w*\b[^.]{0,80}\b(because|since|so that|for)\b[^.]{0,60}"
                r"\b(merge|join|write_feed|single pass|one pass)"
                r"|\bsort\w*\b[^.]{0,60}\bwrite_feed\b[^.]{0,30}\b(needs?|requires?|relies|depends|expects|assumes)\b"
                r"|\b(merge|join|single pass|one pass)\w*\b[^.]{0,80}\b(so|therefore|hence|which is why)\b[^.]{0,40}"
                r"\b(sort|order)"
                r"|out[- ]of[- ]order[^.]{0,40}\b(skip|dropp|lost|ignor|miss)\w*"
                r"|\b(skip|dropp|lost|ignor|miss)\w*[^.]{0,40}\bout[- ]of[- ]order|\bsilently\b")
TRUE_OF_CODE = (r"\bnot\b|n't\b|\bno longer\b|\bnever\b|\bany order\b|\bneed not\b|\bregardless\b"
                r"|\bwhatever order\b|\bitself\b|\bhere\b|\binternally\b|\bown\b|\bbefore (the )?(merge|walk)")
MKT204 = r"MKT-204|four[- ]digit|4[- ]digit"


def s6_no_claim(out, orig):
    after = symbol_prose(out / "stock/rows.py", "stock_rows")
    if after is None:
        return False, "stock_rows not found in stock/rows.py"
    at_sort = [line for line in (Counter(after) - Counter(symbol_prose(orig / "stock/rows.py", "stock_rows"))).elements()
               if re.search(AT_SORT, line, re.IGNORECASE)]
    hits = [f"at stock_rows: {line!r}" for line in at_sort]
    hits += stale_sentences(out, orig, S6_PAGE, None, NEEDS_SORTED, TRUE_OF_CODE)
    if hits:
        return False, f"the sorted-rows coupling in an added line: {'; '.join(hits[:3])} (heuristic)"
    return True, "stock_rows gained nothing about the coupling, and no added sentence says rows must be sorted (heuristic)"


def s6_cap(out, orig):
    return one_home_in_code(out, MKT204, "the MKT-204 cap reason")


def s6_placement(out, orig):
    return beside(out, [("stock/format.py", "MAX_FEED_QTY"), ("stock/format.py", "feed_line")], MKT204,
                  "the cap reason")


def s6_restatement(out, orig):
    return no_restatement(out, orig, {
        "the no-stock filter": r"no[- ]stock|leaves? out SKUs|without stock",
        "the tab-separated line": r"tab[- ]separated",
    }, quiet_symbols=("stock/rows.py", ["stock_rows"], None))


def s6_code(out, orig):
    return code_unchanged(out, orig, "stale-ordering-reason")


def s6_kept(out, orig):
    return kept_except(out, orig, S6_PAGE)


def s6_reply(out, orig):
    return reply_block(out, r"\bsort|\border",
                       r"write_feed[^\n]{0,120}\bsorts?\b|sorted\(rows\)|\bitself\b|\bany order\b|out of date|stale"
                       r"|outdated|no longer|incorrect|wrong|inaccurate|contradict|(not|n't) (need|rely|depend|requir)\w*"
                       r"|redundant|unnecessary|not needed")


def s6_reply_each(out, orig):
    return reply_each(out, {
        "the no-stock filter": r"no[- ]stock|qty\s*>\s*0|out[- ]of[- ]stock|zero stock|in stock|without stock",
        "the sort": r"merge|\bsort",
        "the tab-separated line": r"\btab",
        "the MKT-204 cap": r"MKT-204|MAX_FEED_QTY|9999",
    })


# --------------------------------------------------------- 7. four-fates-page (held out)

S7_PAGE = "docs/digests.md"
DAY_GAP = r"\b24\b|twenty-four|once a day|(one|a) (digest )?(a|per) day|\bdaily\b|\bper day\b"
NOTIF9 = r"NOTIF-9|\bfloods?\b"
MAIL71 = r"MAIL-71|mail relay|\bfolds?\b"


def s7_no_24(out, orig):
    return stale_kept_out(out, orig, S7_PAGE, DAY_GAP, "the 24-hour gap")


def s7_notif9(out, orig):
    return one_home_in_code(out, NOTIF9, "the NOTIF-9 reason")


def s7_subject(out, orig):
    return one_home_in_code(out, MAIL71, "the MAIL-71 subject reason")


def s7_placement(out, orig):
    a = beside(out, [("notify/digest.py", "due"), ("notify/settings.py", "MIN_HOURS_BETWEEN_DIGESTS")], NOTIF9,
               "the NOTIF-9 reason")
    b = beside(out, [("notify/mail.py", "SUBJECT_LIMIT"), ("notify/mail.py", "subject")], MAIL71,
               "the subject reason")
    return a[0] and b[0], f"{a[1]}; {b[1]}"


def s7_incident(out, orig):
    return stays_in_one_doc(out, {"#mail-ops": r"mail-ops"})


def s7_restatement(out, orig):
    # The big-picture sentence about the nightly cleanup may land in code; its placement is
    # an open question for the user, so a cleanup line is allowed at build_digest unless it
    # also restates the grouping.
    return no_restatement(out, orig, {"the grouping": r"by project|groups? (a user's )?unread"},
                          quiet_symbols=("notify/digest.py", ["build_digest"],
                                         r"^(?!.*(group|project|unread)).*clean.?up"))


def s7_code(out, orig):
    return code_unchanged(out, orig, "four-fates-page")


def s7_kept(out, orig):
    return kept_except(out, orig, S7_PAGE, frozen=("AGENTS.md",))


def s7_reply(out, orig):
    return reply_block(out, r"\b24\b|twenty-four|\ba day\b|daily", r"\b(6|six)\b|MIN_HOURS_BETWEEN_DIGESTS")


def s7_reply_each(out, orig):
    return reply_each(out, {
        "the nightly cleanup": r"clean.?up",
        "the grouping": r"build_digest|by project|group",
        "the due() gap and NOTIF-9": r"NOTIF-9|due\(|\b24\b|flood",
        "the MAIL-71 limit": r"MAIL-71|SUBJECT_LIMIT|\b78\b",
        "the #mail-ops note": r"mail-ops|incident|paus",
    })


CHECKS = {
    "stale-number-elsewhere": [s1_no_fixed_gap, s1_retry_reason, s1_page_size, s1_placement, s1_restatement, s1_code,
                               s1_kept, no_new_files, s1_reply_stale, s1_reply_each],
    "restatement-only-page": [s2_no_prose, s2_page_removed, s2_kept, s2_code, no_new_files, s2_reply,
                              s2_reply_each],
    "slim-page-one-home": [s3_rounding, s3_packing, s3_placement, s3_contacts, s3_restatement, s3_code, s3_kept,
                           no_new_files, s3_reply, s3_reply_agents, s3_reply_each],
    "ops-notes-in-file-sections": [s4_not_in_code, s4_in_one_doc, s4_moved, s4_placement, s4_restatement, s4_code,
                                   s4_kept, no_new_files, s4_reply_each],
    "spec-claim-code-disagrees": [s5_no_claim, s5_acc30, s5_restatement, s5_code, s5_kept, no_new_files, s5_reply,
                                  s5_reply_each],
    "stale-ordering-reason": [s6_no_claim, s6_cap, s6_placement, s6_restatement, s6_code, s6_kept, no_new_files,
                              s6_reply, s6_reply_each],
    "four-fates-page": [s7_no_24, s7_notif9, s7_subject, s7_placement, s7_incident, s7_restatement, s7_code,
                        s7_kept, no_new_files, s7_reply, s7_reply_each],
}
