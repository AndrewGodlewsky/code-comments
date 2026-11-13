"""Shared grading helpers for the incubator skills' evals.

Each incubator skill keeps its own ``eval/grade.py``, which defines ``CHECKS``: for each
case, one check per grader file, in the same order. A check is a function
``check(out, orig) -> (passed, evidence)``. ``out`` is the run's edited repository and
``orig`` is the case's untouched ``files/``. The helpers here read comment text and code
shape the same way for every skill. They are adapted from ``evaluation/hygiene/grade.py``
and add JavaScript and TypeScript comments.

``harness.py`` loads the checks, pairs them with the grader statements and runs them.
"""

from __future__ import annotations

import ast
import contextlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import tokenize
from collections import Counter
from pathlib import Path

# Tool caches a run can leave behind (pytest writes a README.md into its cache).
SKIP_DIRS = {"__pycache__", ".git", ".pytest_cache", ".mypy_cache", ".ruff_cache", "node_modules"}
SKIP_FILES = {"RESPONSE.md"}  # the run's reply to the user, not repository prose
HASH_COMMENT = {".toml", ".yaml", ".yml", ".cfg", ".ini", ".sh"}
SLASH_COMMENT = {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}
PROSE_SUFFIXES = {".py", ".md"} | HASH_COMMENT | SLASH_COMMENT


# ---------------------------------------------------------------- reading files


def files(root: Path, suffixes=PROSE_SUFFIXES):
    """Every graded file under root, in a stable order, skipping caches and the reply.
    Pass suffixes=None for every file."""
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.name in SKIP_FILES:
            continue
        if any(part in SKIP_DIRS for part in path.relative_to(root).parts):
            continue
        if suffixes is None or path.suffix in suffixes:
            yield path


def text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")


def reply(out: Path) -> str:
    """The run's message to the user, or an empty string if it wrote none."""
    path = out / "RESPONSE.md"
    return text(path) if path.is_file() else ""


# ---------------------------------------------------------------- reading prose


def _python_prose(source: str) -> list[str]:
    lines: list[str] = []
    try:
        for token in tokenize.generate_tokens(io.StringIO(source).readline):
            if token.type == tokenize.COMMENT:
                body = token.string.lstrip("#").strip()
                if body:
                    lines.append(body)
    except (tokenize.TokenError, IndentationError, SyntaxError):
        pass
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return lines
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            doc = ast.get_docstring(node, clean=True)
            if doc:
                lines += [line.strip() for line in doc.splitlines() if line.strip()]
    return lines


def slash_comments(source: str) -> list[tuple[str, str]]:
    """Split JavaScript/TypeScript source into ("code" | "comment", text) pieces.

    A small scanner, not a parser: it skips string and template literals so that a
    "//" inside a URL string is not taken for a comment. Regex literals are not
    recognised, which is acceptable for small fixtures.
    """
    pieces: list[tuple[str, str]] = []
    i, n, start = 0, len(source), 0
    while i < n:
        ch = source[i]
        if ch in "'\"`":
            quote, i = ch, i + 1
            while i < n and source[i] != quote:
                i += 2 if source[i] == "\\" else 1
            i += 1
        elif source.startswith("//", i):
            pieces.append(("code", source[start:i]))
            end = source.find("\n", i)
            end = n if end == -1 else end
            pieces.append(("comment", source[i + 2:end]))
            i = start = end
        elif source.startswith("/*", i):
            pieces.append(("code", source[start:i]))
            end = source.find("*/", i + 2)
            end = n if end == -1 else end
            pieces.append(("comment", source[i + 2:end]))
            i = start = min(n, end + 2)
        else:
            i += 1
    pieces.append(("code", source[start:]))
    return [(kind, body) for kind, body in pieces if body]


def _slash_prose(source: str) -> list[str]:
    lines = []
    for kind, body in slash_comments(source):
        if kind != "comment":
            continue
        for line in body.splitlines():
            line = line.strip().lstrip("*").strip()
            if line:
                lines.append(line)
    return lines


def prose(path: Path) -> list[str]:
    """Return the comment, docstring or Markdown lines of one file, stripped."""
    source = text(path)
    if path.suffix == ".md":
        return [line.strip() for line in source.splitlines() if line.strip()]
    if path.suffix == ".py":
        return _python_prose(source)
    if path.suffix in SLASH_COMMENT:
        return _slash_prose(source)
    if path.suffix in HASH_COMMENT:
        return [line.strip().lstrip("#").strip() for line in source.splitlines()
                if line.strip().startswith("#") and line.strip().lstrip("#").strip()]
    return []


def prose_map(root: Path) -> dict[str, Counter]:
    return {path.relative_to(root).as_posix(): Counter(prose(path)) for path in files(root)}


def added_prose(out: Path, orig: Path) -> dict[str, Counter]:
    """Comment, docstring and Markdown lines present in out but not in orig, per file."""
    before, after = prose_map(orig), prose_map(out)
    found = {rel: lines - before.get(rel, Counter()) for rel, lines in after.items()}
    return {rel: lines for rel, lines in found.items() if lines}


def joined(root: Path, rel: str) -> str:
    path = root / rel
    return " ".join(prose(path)) if path.is_file() else ""


def lost_prose(out: Path, orig: Path, rename: tuple[str, str] | None = None) -> dict[str, Counter]:
    """Lines of orig prose missing from out. Re-wrapping a comment is not a loss: a line
    still counts as kept when its words appear, in order, in the file's prose."""
    before, after = prose_map(orig), prose_map(out)
    found = {}
    for rel, lines in before.items():
        if rename:
            lines = Counter({line.replace(*rename): n for line, n in lines.items()})
        missing = lines - after.get(rel, Counter())
        if missing:
            body = " " + " ".join(joined(out, rel).split()) + " "
            missing = Counter({line: n for line, n in missing.items()
                               if f" {' '.join(line.split())} " not in body})
        if missing:
            found[rel] = missing
    return found


def prose_text(root: Path) -> str:
    """All prose under root as one whitespace-normalised string."""
    joined_text = " ".join(line for lines in prose_map(root).values() for line in lines.elements())
    return re.sub(r"\s+", " ", joined_text)


def added_text(out: Path, orig: Path) -> str:
    """All added prose lines as one whitespace-normalised string."""
    found = added_prose(out, orig)
    return re.sub(r"\s+", " ", " ".join(line for lines in found.values() for line in lines.elements()))


def count(found: dict[str, Counter]) -> int:
    return sum(sum(lines.values()) for lines in found.values())


def show(found: dict[str, Counter], limit: int = 4) -> str:
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
    """The file's code with comments and docstrings removed, for "code unchanged" checks.
    Python is compared by AST; JavaScript/TypeScript by comment-free, whitespace-free text.
    A missing file gives None. Python that does not parse gives its whitespace-normalised
    text, so two different broken files do not compare as equal. Any other suffix raises
    ValueError: use a file-type check such as a grader's shell or SQL check instead."""
    if path.suffix not in SLASH_COMMENT and path.suffix != ".py":
        raise ValueError(f"code_shape compares Python and JS/TS only, not {path.suffix or path.name}")
    if not path.is_file():
        return None
    if path.suffix in SLASH_COMMENT:
        code = "".join(body for kind, body in slash_comments(text(path)) if kind == "code")
        return re.sub(r"\s+", "", code)
    try:
        tree = ast.parse(text(path))
    except SyntaxError:
        return "<unparsable>" + re.sub(r"\s+", " ", text(path))
    return ast.dump(_DropDocstrings().visit(tree))


def constant(path: Path, name: str):
    """The literal value a module-level Python assignment gives name, or a <reason>."""
    if not path.is_file():
        return "<missing file>"
    try:
        tree = ast.parse(text(path))
    except SyntaxError as error:
        return f"<syntax error: {error}>"
    for node in tree.body:
        targets = node.targets if isinstance(node, ast.Assign) else \
            [node.target] if isinstance(node, ast.AnnAssign) and node.value is not None else []
        if any(isinstance(t, ast.Name) and t.id == name for t in targets):
            try:
                return ast.literal_eval(node.value)
            except ValueError:
                return f"<not a literal: {ast.unparse(node.value)}>"
    return "<not assigned>"


def raw_lines(path: Path) -> set[str]:
    return {line.strip() for line in text(path).splitlines()} if path.is_file() else set()


def keeps(path: Path, lines: list[str]) -> list[str]:
    """The lines from `lines` that no longer appear (stripped) in path."""
    present = raw_lines(path)
    return [line for line in lines if line not in present]


def _env() -> dict[str, str]:
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    env.pop("PYTHONPATH", None)
    return env


@contextlib.contextmanager
def _scratch(root: Path, extra: Path | None = None):
    """A throwaway copy of root (with extra laid over it), so a grader's subprocess never
    changes the files it grades. SKIP_DIRS, .git included, are not copied: a fixture
    whose tests need git history would need .git kept."""
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp) / "repo"
        shutil.copytree(root, repo, ignore=shutil.ignore_patterns(*SKIP_DIRS))
        if extra is not None:
            shutil.copytree(extra, repo, dirs_exist_ok=True)
        yield repo


def run_tests(root: Path) -> tuple[bool, str]:
    """Run the fixture's unittest suite (tests/ under root), on a copy of root."""
    with _scratch(root) as repo:
        result = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-t", "."],
                                cwd=repo, capture_output=True, text=True, timeout=120, env=_env())
    tail = (result.stderr or result.stdout).strip().splitlines()[-1:] or [""]
    return result.returncode == 0, f"unittest exit {result.returncode}: {tail[0]}"


def run_hidden_tests(out: Path, hidden: Path) -> tuple[bool, str]:
    """Run tests the agent never saw against the run's repository.

    ``hidden`` is a folder laid out like the repository (usually holding a
    ``hidden_tests/`` package). Both are copied into a scratch folder, so the run's own
    files are never changed, and every ``hidden_tests/test_*.py`` is run with unittest.
    """
    with _scratch(out, hidden) as repo:
        package = repo / "hidden_tests"
        if not package.is_dir():
            return False, f"no hidden_tests/ folder in {hidden}"
        (package / "__init__.py").touch()
        result = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "hidden_tests", "-t", "."],
                                cwd=repo, capture_output=True, text=True, timeout=120, env=_env())
    lines = (result.stderr or result.stdout).strip().splitlines()
    failures = [line for line in lines if line.startswith(("FAIL:", "ERROR:"))]
    detail = "; ".join(failures[:3]) or (lines[-1] if lines else "")
    return result.returncode == 0, f"hidden tests exit {result.returncode}: {detail}"


def run_snippet(root: Path, code: str) -> tuple[object, str]:
    """Run Python code in a copy of root; it must print one JSON value on its last line."""
    with _scratch(root) as repo:
        result = subprocess.run([sys.executable, "-c", code], cwd=repo, capture_output=True, text=True,
                                timeout=120, env=_env())
    if result.returncode != 0:
        return None, (result.stderr.strip().splitlines() or ["<no output>"])[-1]
    try:
        return json.loads(result.stdout.strip().splitlines()[-1]), ""
    except (json.JSONDecodeError, IndexError):
        return None, f"unreadable output: {result.stdout[-200:]!r}"


# ------------------------------------------------------------- check builders


def no_match(pattern: str, haystack: str) -> tuple[bool, str]:
    hits = sorted({m.group(0) for m in re.finditer(pattern, haystack, re.IGNORECASE)})
    return not hits, f"found {hits}" if hits else "no match"


def has_match(pattern: str, haystack: str) -> tuple[bool, str]:
    match = re.search(pattern, haystack, re.IGNORECASE)
    return bool(match), f"matched {match.group(0)!r}" if match else "no match"


def kept(out: Path, wanted: dict[str, list[str]]) -> tuple[bool, str]:
    """Every listed line (stripped) still appears verbatim in its file."""
    missing = [f"{rel}: {line!r}" for rel, lines in wanted.items() for line in keeps(out / rel, lines)]
    return not missing, "missing " + "; ".join(missing) if missing else "all kept"


def at_most(found: dict[str, Counter], limit: int) -> tuple[bool, str]:
    n = count(found)
    return n <= limit, f"{n} added line(s)" + (f": {show(found)}" if n else "")


def nothing_lost(out: Path, orig: Path, rename: tuple[str, str] | None = None,
                 ignore: dict[str, list[str]] | None = None) -> tuple[bool, str]:
    """No prose line of orig is missing from out, apart from lines listed in ignore."""
    found = lost_prose(out, orig, rename)
    for rel, lines in (ignore or {}).items():
        if rel in found:
            for line in lines:
                found[rel].pop(line, None)
            if not found[rel]:
                del found[rel]
    return not found, "all kept" if not found else f"lost {show(found)}"


def same_code(out: Path, orig: Path, rels: list[str]) -> tuple[bool, str]:
    """Each listed file's code (ignoring comments and docstrings) is unchanged."""
    changed = [rel for rel in rels if code_shape(out / rel) != code_shape(orig / rel)]
    return not changed, f"code changed in {changed}" if changed else "code unchanged"


def files_unchanged(out: Path, orig: Path, rels: list[str]) -> tuple[bool, str]:
    """Each listed file is byte-for-byte unchanged (line endings normalised)."""
    changed = [rel for rel in rels if not (out / rel).is_file() or text(out / rel) != text(orig / rel)]
    return not changed, f"changed {changed}" if changed else "unchanged"


def new_files(out: Path, orig: Path) -> list[str]:
    """Files present in out but not in orig (caches and the reply excluded)."""
    before = {p.relative_to(orig).as_posix() for p in files(orig, None)}
    return [p.relative_to(out).as_posix() for p in files(out, None)
            if p.relative_to(out).as_posix() not in before]
