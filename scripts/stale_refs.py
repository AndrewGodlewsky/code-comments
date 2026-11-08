"""Flag comments and docstrings that name code which no longer exists (#44).

python scripts/stale_refs.py [ROOT]                    # every finding under ROOT
python scripts/stale_refs.py ROOT --diff BASE          # only findings a change made new
python scripts/stale_refs.py HEAD_DIR --base-dir DIR   # the same, against a directory
Options: --only PREFIX (report only these paths), --allow NAME, --allowlist FILE, --json,
--stats (counts to stderr).
Exit status: 0 when clean, 1 when there are findings, 2 on a usage or git error.

What counts as a reference, inside a comment or a docstring:
- a backticked identifier, dotted path or call, such as `resolves`, `index.names`
  or `checkout(root, rev, destination)`;
- a bare call in prose, such as "call build() first";
- an underscore-separated word in prose (every part two or more characters), such as
  "see new_findings";
- a file path with a source or config extension, such as `scripts/stale_refs.py`;
- a command-line flag, such as `--base-dir`.

A reference resolves when it names something in the project: any identifier in code
outside comments (definitions, uses and attribute names), an identifier-shaped string
literal, a file or directory name, a builtin, a keyword or a standard-library module.
A name the project's Markdown or reST docs put in backticks also counts, and so does
a plural ending in `s` whose singular resolves. A dotted path resolves when its root
is an imported third-party or stdlib name, when it is an attribute of a builtin (such
as `str.isalnum`), or when its root and last part both resolve. A flag resolves when it occurs in code or a
config file. A name ending in `_` is a prefix and resolves when some name starts
with it. A relative link that does not resolve from its own directory falls back to a
suffix match. URLs, `$...$` math, `<placeholder>` spans, paths with `...`, doctest
examples and fenced code blocks are skipped; names used in doctests and fenced code
count as known names.

Opt out on one line with `stale-refs: ignore` (or `noqa: stale-ref`) in the comment.
Python files are read with `tokenize` and `ast`. Other languages are read
heuristically: `//`, `#` and `/* */` comments, identifiers from the remaining text.
"""

from __future__ import annotations

import argparse
import ast
import builtins
from dataclasses import asdict, dataclass
import io
import json
import keyword
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tarfile
import tempfile
import tokenize


PY = {".py", ".pyi"}
HEURISTIC = {".js", ".jsx", ".ts", ".tsx", ".go", ".rs", ".java", ".kt", ".c", ".h",
             ".cc", ".cpp", ".hpp", ".cs", ".swift", ".rb", ".sh"}
CONFIG = {".toml", ".cfg", ".ini", ".yaml", ".yml", ".json"}
CONFIG_NAMES = {"Makefile", "Dockerfile", "justfile", "noxfile.py", "tox.ini"}
DOCS = {".md", ".rst"}
SKIP_DIRS = {".git", ".hg", ".svn", "node_modules", "__pycache__", ".venv", "venv",
             ".tox", ".nox", ".mypy_cache", ".ruff_cache", ".pytest_cache", "build",
             "dist", "site-packages", ".worktrees"}
FILE_EXT = "py|pyi|md|rst|txt|toml|cfg|ini|json|ya?ml|sh|js|jsx|ts|tsx|go|rs|java|c|h|cpp"

IDENT = r"[A-Za-z_][A-Za-z0-9_]*"
DOTTED = rf"{IDENT}(?:\.{IDENT})*"
BACKTICK = re.compile(r"(`{1,2})([^`\n]+?)\1")
BACKTICK_REF = re.compile(rf"^({DOTTED})(\(.*\))?$")
PROSE_CALL = re.compile(rf"(?<![\w.`])({DOTTED})\(\)")
# Every part has two or more characters, so math such as x_0 and w_i is not a name.
SNAKE = re.compile(r"(?<![\w.`/-])(_{0,2}[a-z][a-z0-9]+(?:_[a-z0-9]{2,})+_{0,2})(?![\w(`/=-])")
FILE = re.compile(rf"(?<![\w/.:-])((?:[\w.-]+/)*[\w-]+\.(?:{FILE_EXT}))(?![\w/])")
FLAG = re.compile(r"(?<![\w-])(--[a-z][a-z0-9]*(?:-[a-z0-9]+)*)(?![\w-])")
URL = re.compile(r"\b(?:https?|ftp|file)://\S+|\bwww\.\S+")
MATH = re.compile(r"\$[^$\n]+\$")
PLACEHOLDER_DIR = re.compile(r"^[A-Z][A-Z0-9]*_[A-Z0-9_]+$")
# A placeholder takes the text joined to it, as in Native<Thing> or Implementation.<BACKEND>.
PLACEHOLDER = re.compile(r"[\w.]*<([^<>\s]+)>\w*")
OPT_OUT = re.compile(r"stale-refs:\s*ignore|noqa:\s*stale-ref", re.I)
DIRECTIVE = re.compile(r"^\s*(type|noqa|pragma|pyright|mypy|fmt|ruff|pylint|isort)\b.*")
IDENT_LITERAL = re.compile(rf"^{DOTTED}$")
WORD = re.compile(IDENT)
DOCTEST = re.compile(r"^\s*(>>>|\.\.\.)(\s|$)")
FENCE = re.compile(r"^\s*(```|~~~)")

ALWAYS_KNOWN = (set(dir(builtins)) | set(keyword.kwlist) | set(keyword.softkwlist)
                | set(sys.stdlib_module_names) | {"self", "cls", "args", "kwargs"})


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    kind: str  # identifier | call | dotted | file | flag
    ref: str
    text: str

    def key(self) -> tuple[str, str, str, str]:
        """Identity across commits: line numbers move, so they are left out."""
        return (self.path, self.kind, self.ref, " ".join(self.text.split()))


@dataclass
class Comment:
    line: int
    text: str


@dataclass
class Index:
    names: set[str]
    external: set[str]
    flags: set[str]
    files: set[str]  # repository-relative POSIX paths


# ---------------------------------------------------------------- collection


def iter_files(root: Path) -> list[Path]:
    out = []
    stack = [root]
    while stack:
        directory = stack.pop()
        try:
            entries = sorted(directory.iterdir())
        except OSError:
            continue
        for entry in entries:
            if entry.is_dir():
                if entry.name not in SKIP_DIRS and not entry.name.endswith(".egg-info"):
                    stack.append(entry)
            elif entry.is_file():
                out.append(entry)
    return sorted(out)


def read(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def python_parts(source: str) -> tuple[list[Comment], list[str], list[str], ast.AST | None]:
    """Return comments, code identifiers, string literal values and the parsed tree."""
    comments: list[Comment] = []
    names: list[str] = []
    strings: list[str] = []
    try:
        for token in tokenize.generate_tokens(io.StringIO(source).readline):
            if token.type == tokenize.COMMENT:
                comments.append(Comment(token.start[0], token.string[1:]))
            elif token.type == tokenize.NAME:
                names.append(token.string)
            elif token.type == tokenize.STRING or token.type == getattr(tokenize, "FSTRING_MIDDLE", -1):
                strings.append(token.string)
    except (tokenize.TokenError, IndentationError, SyntaxError):
        pass
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError):
        tree = None
    if tree is not None:
        strings = [node.value for node in ast.walk(tree)
                   if isinstance(node, ast.Constant) and isinstance(node.value, str)]
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                doc = docstring_node(node)
                if doc is not None:
                    comments.extend(docstring_comments(doc, names))
    return comments, names, strings, tree


def docstring_node(node: ast.AST) -> ast.Constant | None:
    body = getattr(node, "body", None)
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
            and isinstance(body[0].value.value, str):
        return body[0].value
    return None


def docstring_comments(node: ast.Constant, code_names: list[str] | None = None) -> list[Comment]:
    """Split a docstring into lines, dropping doctest examples and fenced code.

    Names used in the dropped code are added to code_names: an example that defines
    a helper makes the helper a known name for the prose around it.
    """
    out = []
    in_fence = in_output = False
    for offset, line in enumerate(node.value.splitlines()):
        if FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence or DOCTEST.match(line):
            if code_names is not None:
                code_names.extend(WORD.findall(line))
            in_output = in_output or not in_fence
            continue
        if in_output:
            if line.strip():
                continue
            in_output = False
        out.append(Comment(node.lineno + offset, line))
    return out


def external_names(tree: ast.AST | None, project_roots: set[str]) -> set[str]:
    """Names bound by imports of modules outside the project."""
    out: set[str] = set()
    if tree is None:
        return out
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] not in project_roots:
                    out.add(alias.asname or alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            if node.module.split(".")[0] not in project_roots:
                out.update(alias.asname or alias.name for alias in node.names)
    return out


C_COMMENT = r"//[^\n]*|/\*.*?\*/|(?<![$\w])#(?![!{\[])[^\n]*"
C_STRING = r"\"(?:\\.|[^\"\\\n])*\"|'(?:\\.|[^'\\\n])*'|`(?:\\.|[^`\\])*`"
# One left-to-right scan, so whichever starts first wins: a quote inside a comment
# ("don't", `name`) does not open a string, and // inside a string is not a comment.
C_TOKEN = re.compile(rf"(?P<comment>{C_COMMENT})|(?P<string>{C_STRING})", re.S)


def heuristic_parts(source: str) -> tuple[list[Comment], list[str], list[str]]:
    comments: list[Comment] = []
    strings: list[str] = []
    code_parts: list[str] = []
    position = 0
    for match in C_TOKEN.finditer(source):
        code_parts.append(source[position:match.start()])
        position = match.end()
        if match.group("string") is not None:
            strings.append(match.group(0)[1:-1])
            code_parts.append(re.sub(r"[^\n]", " ", match.group(0)))
            continue
        start = source.count("\n", 0, match.start()) + 1
        body = re.sub(r"^(//+|/\*+|#+)|\*+/$", "", match.group(0))
        for offset, line in enumerate(body.splitlines() or [""]):
            comments.append(Comment(start + offset, re.sub(r"^\s*\*\s?", "", line)))
        code_parts.append(" ")
    code = "".join(code_parts) + source[position:]
    # The code itself joins the strings so that flags used in commands count as known.
    return comments, WORD.findall(code), strings + [code]


@dataclass
class Parsed:
    rel: str
    comments: list[Comment]


def build(root: Path) -> tuple[Index, list[Parsed]]:
    files = iter_files(root)
    rels = {f: f.relative_to(root).as_posix() for f in files}
    project_roots = {PurePosixPath(r).parts[0].removesuffix(".py") for r in rels.values()}
    for rel in rels.values():  # src/ layouts: src/<pkg>/...
        parts = PurePosixPath(rel).parts
        if len(parts) > 2 and parts[0] in {"src", "lib"}:
            project_roots.add(parts[1])
    names: set[str] = set()
    external: set[str] = set()
    flags: set[str] = set()
    parsed: list[Parsed] = []
    for path, rel in rels.items():
        for part in PurePosixPath(rel).parts:
            names.add(part)
            names.add(part.split(".")[0])
        suffix = path.suffix
        if suffix in PY or suffix in HEURISTIC:
            source = read(path)
            if source is None:
                continue
            if suffix in PY:
                comments, idents, strings, tree = python_parts(source)
                external |= external_names(tree, project_roots)
            else:
                comments, idents, strings = heuristic_parts(source)
            names.update(idents)
            for value in strings:
                flags.update(FLAG.findall(value))
                stripped = value.strip()
                if IDENT_LITERAL.match(stripped):
                    names.update(stripped.split("."))
            parsed.append(Parsed(rel, comments))
        elif suffix in DOCS:
            # A name the project's own docs put in code formatting, such as a field of an
            # external API, is a known term even when no code uses it.
            text = read(path)
            for inner in BACKTICK.findall(text or ""):
                if IDENT_LITERAL.match(inner[1].strip()):
                    names.update(inner[1].strip().split("."))
        elif suffix in CONFIG or path.name in CONFIG_NAMES or suffix in {".cfg"}:
            text = read(path)
            if text is not None:
                flags.update(FLAG.findall(text))
                names.update(WORD.findall(text) if suffix in {".toml", ".cfg", ".ini"} else [])
    return Index(names | ALWAYS_KNOWN, external, flags, set(rels.values())), parsed


# ---------------------------------------------------------------- extraction


def references(text: str) -> list[tuple[str, str]]:
    """(kind, ref) pairs found in one comment line."""
    text = MATH.sub(" ", URL.sub(" ", text))
    # A word inside a placeholder names it for the rest of the line, as in
    # "Implementation.<BACKEND> with BACKEND being ...".
    placeholders = {word for inner in PLACEHOLDER.findall(text) for word in WORD.findall(inner)}
    text = PLACEHOLDER.sub(" ", text)
    found: list[tuple[str, str]] = []
    spans = []
    for match in BACKTICK.finditer(text):
        spans.append(match.span())
        inner = match.group(2).strip()
        if FILE.fullmatch(inner):
            found.append(("file", inner))
        elif FLAG.fullmatch(inner.split("=")[0]):
            found.append(("flag", inner.split("=")[0]))
        else:
            ref = BACKTICK_REF.match(inner)
            if ref:
                kind = "call" if ref.group(2) else ("dotted" if "." in ref.group(1) else "identifier")
                found.append((kind, ref.group(1)))
    prose = list(text)
    for start, end in spans:
        prose[start:end] = " " * (end - start)
    prose_text = "".join(prose)
    for match in FILE.finditer(prose_text):
        found.append(("file", match.group(1)))
    prose_text = FILE.sub(lambda m: " " * len(m.group(0)), prose_text)
    found.extend(("call", m.group(1)) for m in PROSE_CALL.finditer(prose_text))
    found.extend(("identifier", m.group(1)) for m in SNAKE.finditer(prose_text))
    found.extend(("flag", m.group(1)) for m in FLAG.finditer(prose_text))
    seen = set()
    return [x for x in found
            if not (x[0] == "file" and placeholder_path(x[1])) and x[1] not in placeholders
            and not (x in seen or seen.add(x))]


def placeholder_path(ref: str) -> bool:
    """A path with `...` or an all-caps directory such as OUT_DIR stands for any path."""
    return "..." in ref or any(PLACEHOLDER_DIR.match(part) for part in ref.split("/")[:-1])


def resolves(kind: str, ref: str, index: Index, here: str, allow: set[str]) -> bool:
    if ref in allow:
        return True
    if kind == "flag":
        return ref in index.flags
    if kind == "file":
        candidate = PurePosixPath(ref)
        if ref.startswith("./") or ref.startswith("../"):
            joined = PurePosixPath(here).parent / candidate
            parts: list[str] = []
            for part in joined.parts:
                if part == "..":
                    if parts:
                        parts.pop()
                elif part != ".":
                    parts.append(part)
            if "/".join(parts) in index.files:
                return True
            ref = str(candidate)
            while ref.startswith(("./", "../")):
                ref = ref.split("/", 1)[1]
        return any(f == ref or f.endswith("/" + ref) for f in index.files)
    parts = ref.split(".")
    if parts[0] in index.external or parts[0] in sys.stdlib_module_names:
        return True
    if len(parts) == 1:
        if ref.endswith("_") and not ref.endswith("__") and len(ref) > 1:
            return any(name.startswith(ref) for name in index.names)
        # A plural in prose ("the event_ids seen so far") names the singular.
        return ref in index.names or (ref.endswith("s") and ref[:-1] in index.names)
    if hasattr(builtins, parts[0]):  # str.isalnum, dict.setdefault
        target = getattr(builtins, parts[0])
        for part in parts[1:]:
            target = getattr(target, part, None)
            if target is None:
                break
        else:
            return True
    return parts[0] in index.names and parts[-1] in index.names


def lint(root: Path, allow: set[str] = frozenset(), only: list[str] | None = None,
         stats: dict[str, int] | None = None) -> list[Finding]:
    """Findings under root. If stats is given, it receives files and references counts."""
    index, parsed = build(root)
    findings = []
    checked = files = 0
    for item in parsed:
        if only and not any(item.rel == p or item.rel.startswith(p.rstrip("/") + "/") for p in only):
            continue
        files += 1
        for comment in item.comments:
            if OPT_OUT.search(comment.text) or DIRECTIVE.match(comment.text):
                continue
            for kind, ref in references(comment.text):
                checked += 1
                if not resolves(kind, ref, index, item.rel, allow):
                    findings.append(Finding(item.rel, comment.line, kind, ref, comment.text.strip()))
    if stats is not None:
        stats.update(files=files, references=checked, findings=len(findings))
    return findings


def new_findings(base: Path, head: Path, allow: set[str] = frozenset(),
                 only: list[str] | None = None) -> list[Finding]:
    """Findings in HEAD that BASE did not already have."""
    before: dict[tuple, int] = {}
    for finding in lint(base, allow, only):
        before[finding.key()] = before.get(finding.key(), 0) + 1
    out = []
    for finding in lint(head, allow, only):
        if before.get(finding.key(), 0):
            before[finding.key()] -= 1
        else:
            out.append(finding)
    return out


def checkout(root: Path, rev: str, destination: Path) -> None:
    archive = subprocess.run(["git", "-C", str(root), "archive", "--format=tar", rev],
                             capture_output=True, check=True).stdout
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        tar.extractall(destination, filter="data")


def load_allow(values: list[str], files: list[str]) -> set[str]:
    allow = set(values)
    for name in files:
        for line in Path(name).read_text(encoding="utf-8").splitlines():
            line = line.split("#", 1)[0].strip()
            if line:
                allow.add(line)
    return allow


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("root", nargs="?", default=".", type=Path)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--diff", metavar="BASE", help="git revision to compare against")
    group.add_argument("--base-dir", type=Path, help="directory to compare against")
    parser.add_argument("--only", action="append", default=[], metavar="PREFIX")
    parser.add_argument("--allow", action="append", default=[], metavar="NAME")
    parser.add_argument("--allowlist", action="append", default=[], metavar="FILE")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--stats", action="store_true",
                        help="print files and references checked to stderr (full lint only)")
    args = parser.parse_args(argv)
    if not args.root.is_dir():
        parser.error(f"not a directory: {args.root}")
    allow = load_allow(args.allow, args.allowlist)
    only = args.only or None
    try:
        if args.diff:
            with tempfile.TemporaryDirectory() as tmp:
                checkout(args.root, args.diff, Path(tmp))
                findings = new_findings(Path(tmp), args.root, allow, only)
        elif args.base_dir:
            findings = new_findings(args.base_dir, args.root, allow, only)
        else:
            stats: dict[str, int] = {}
            findings = lint(args.root, allow, only, stats)
            if args.stats:
                print(f"{stats['files']} files, {stats['references']} references checked, "
                      f"{stats['findings']} findings", file=sys.stderr)
    except subprocess.CalledProcessError as error:
        print(f"git failed: {error.stderr.decode(errors='replace').strip()}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps([asdict(f) for f in findings], indent=2))
    else:
        for f in findings:
            print(f"{f.path}:{f.line}: {f.kind} `{f.ref}` not found: {f.text}")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
