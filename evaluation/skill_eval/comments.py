"""Extract explanatory text (comments and docstrings) and code scopes from Python source."""

import ast
from dataclasses import dataclass
import io
import re
import tokenize


@dataclass(frozen=True)
class Block:
    """One unit of explanation: a run of adjacent comment lines or one docstring."""

    kind: str
    start: int
    end: int
    lines: tuple[str, ...]

    @property
    def text(self) -> str:
        return normalize(" ".join(self.lines))


def normalize(text: str) -> str:
    # Inline-code and emphasis markup (``stock``, `x`, *x*) is formatting, not wording:
    # without this, "left in ``stock``" fails to match "left in stock".
    text = re.sub(r"[`*]", "", text.lower().lstrip("#"))
    return re.sub(r"\s+", " ", text).strip()


def _docstring_nodes(tree: ast.AST) -> list[ast.Constant]:
    nodes = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = node.body
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
                nodes.append(body[0].value)
    return nodes


def blocks(source: str) -> list[Block]:
    """Group full-line comments on adjacent lines; trailing comments stand alone."""
    found: list[Block] = []
    run: list[tuple[int, str]] = []

    def flush():
        if run:
            found.append(Block("comment", run[0][0], run[-1][0], tuple(text for _, text in run)))
            run.clear()

    lines = source.splitlines()
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        if token.type != tokenize.COMMENT:
            continue
        row = token.start[0]
        text = token.string.lstrip("#").strip()
        full_line = lines[row - 1].strip().startswith("#")
        if full_line and run and run[-1][0] == row - 1:
            run.append((row, text))
            continue
        flush()
        if full_line:
            run.append((row, text))
        else:
            found.append(Block("comment", row, row, (text,)))
    flush()
    for node in _docstring_nodes(ast.parse(source)):
        doc_lines = tuple(line.strip() for line in node.value.splitlines() if line.strip())
        found.append(Block("docstring", node.lineno, node.end_lineno or node.lineno, doc_lines))
    return sorted(found, key=lambda block: (block.start, block.kind))


def scopes(source: str) -> dict[str, tuple[int, int]]:
    """Map qualified function/class names to line spans, including the comment block directly above."""
    tree = ast.parse(source)
    comment_lines = {
        token.start[0]
        for token in tokenize.generate_tokens(io.StringIO(source).readline)
        if token.type == tokenize.COMMENT and source.splitlines()[token.start[0] - 1].strip().startswith("#")
    }
    spans: dict[str, tuple[int, int]] = {}

    def visit(node: ast.AST, prefix: str) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                name = f"{prefix}{child.name}"
                start = min([child.lineno] + [decorator.lineno for decorator in child.decorator_list])
                while start - 1 in comment_lines:
                    start -= 1
                spans[name] = (start, child.end_lineno or child.lineno)
                visit(child, f"{name}.")

    visit(tree, "")
    return spans


def code_fingerprint(source: str) -> str:
    """AST dump with docstrings removed: equal fingerprints mean comment/docstring-only differences."""
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = node.body
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
                node.body = body[1:] or [ast.Pass()]
    return ast.dump(tree, include_attributes=False)
