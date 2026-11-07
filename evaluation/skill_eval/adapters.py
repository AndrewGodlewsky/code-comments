"""Offline adapters: deterministic stand-ins for an agent, used to validate the grader.

Each adapter mutates a fresh workspace copy of a case's `visible/` directory and
returns trace turns. A live agent adapter is tracked in issue #18 and is
deliberately absent: the repository is offline-only until the budget in #6 is set.
"""

import ast
import io
from pathlib import Path
import shutil
import tokenize

from .grade import Case


def _apply_reference(case: Case, workspace: Path) -> None:
    reference = case.private / "reference"
    for path in reference.rglob("*"):
        if path.is_file():
            target = workspace / path.relative_to(reference)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)


def _graded(case: Case, workspace: Path):
    for name in case.spec["files"]:
        path = workspace / name
        if path.is_file():
            yield path


def _logical_starts(source: str) -> list[int]:
    starts, expecting = [], True
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        if token.type in (tokenize.NEWLINE,):
            expecting = True
        elif token.type in (tokenize.NL, tokenize.COMMENT, tokenize.INDENT, tokenize.DEDENT, tokenize.ENCODING, tokenize.ENDMARKER):
            continue
        elif expecting:
            starts.append(token.start[0])
            expecting = False
    return starts


def null(case: Case, workspace: Path) -> str:
    return "No changes made."


def oracle(case: Case, workspace: Path) -> str:
    _apply_reference(case, workspace)
    return "Applied the reference end state."


def strip(case: Case, workspace: Path) -> str:
    _apply_reference(case, workspace)
    for path in _graded(case, workspace):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                body = node.body
                if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
                    node.body = body[1:] or [ast.Pass()]
        path.write_text(ast.unparse(tree) + "\n", encoding="utf-8", newline="\n")
    return "Applied the reference code with every comment and docstring removed."


def spam(case: Case, workspace: Path) -> str:
    _apply_reference(case, workspace)
    for path in _graded(case, workspace):
        lines = path.read_text(encoding="utf-8").splitlines()
        for row in sorted(_logical_starts("\n".join(lines) + "\n"), reverse=True):
            line = lines[row - 1]
            indent = line[: len(line) - len(line.lstrip())]
            lines.insert(row - 1, f"{indent}# This line does: {line.strip()}")
        path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return "Applied the reference plus a restating comment above every statement."


def stale(case: Case, workspace: Path) -> str:
    _apply_reference(case, workspace)
    claims = case.spec.get("forbidden_claims", [])
    paths = list(_graded(case, workspace))
    if claims and paths:
        source = paths[0].read_text(encoding="utf-8")
        header = "".join(f"# {claim['text']}\n" for claim in claims)
        paths[0].write_text(header + source, encoding="utf-8", newline="\n")
    return "Applied the reference plus every forbidden claim as a comment."


ADAPTERS = {"null": null, "oracle": oracle, "strip": strip, "spam": spam, "stale": stale}
