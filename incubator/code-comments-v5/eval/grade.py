"""Checks for the code-comments-v5 hill-climb: the copied cases keep the checks of the
evals they came from, and the cases built for this climb have checks of their own.

Most cases under ``cases/`` are whole copies of a case from one of three evals:
``incubator/verify-before-relying``, ``incubator/constraint-sweep`` and
``evaluation/hygiene``. This module loads each source eval's ``grade.py`` by file path,
under a module name of its own, and builds ``CHECKS = {case: source.CHECKS[case]}`` for
every copied case. A copied case is therefore graded here exactly as in its source eval.
The other cases were built for this climb; see the last paragraph.

Copied checks resolve hidden tests from their source folders
(``incubator/<skill>/eval/hidden/<case>/``), not from ``hidden/`` here. The two hold
identical files. The copy here is what ``harness.py prepare`` fingerprints.

The hygiene copies differ from their source in two lines, both for the harness:
- ``case.yaml`` gains ``held_out: false``;
- each grader drops its ``focus: trace`` line, a ``claude plugin eval`` field that the
  harness rejects. With no focus line, every hygiene check counts as core.
Statement text is unchanged, so a ruling written for the source case still matches.

The harness fingerprints this file, not the source ``grade.py`` files or local modules
it loads. ``drift()`` lists any copied file that no longer matches its source, and any
pinned check file that changed since it was pinned. tests/test_incubator.py fails while
it lists anything.

Cases written for this climb keep their checks in the optional local modules named in
``LOCAL``, each defining ``CHECKS``. They are merged in when they exist. A local module
may not redefine a copied case. Those modules describe held-out cases, so candidate
writers do not open them.
"""

from __future__ import annotations

import hashlib
import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
INCUBATOR = HERE.parents[1]
ROOT = INCUBATOR.parent

SOURCES = {
    "verify-before-relying": INCUBATOR / "verify-before-relying" / "eval",
    "constraint-sweep": INCUBATOR / "constraint-sweep" / "eval",
    "hygiene": ROOT / "evaluation" / "hygiene",
}
LOCAL = ("heldout_fm1", "heldout_fm2")

# sha256 (line endings normalised) of each file the checks run beside this one. The
# source files were pinned when the climb was pre-registered; the two local modules on
# 2026-11-11, after the build review's fixes and before any run. A grader fix changes one
# of these on purpose: record the fix in README.md and update the pin in the same commit.
PINNED = {
    "incubator/verify-before-relying/eval/grade.py": "baae2553f99082aecad6b58affe74e7904fcb1d0ef2e7c6b58f9c23a52216dcc",
    "incubator/constraint-sweep/eval/grade.py": "c103d9f1add3be2a049f039a7aec79501b09a9178925e25a837775db86fdf3e2",
    "evaluation/hygiene/grade.py": "3a5aa2c1781efefa9df466d6495bf21ab6600810dd63bef6805c5eed4a465a07",
    "scripts/stale_refs.py": "95062c677f1f1920dd86f226122a1d746eabdff89211bf6889cd40977b16e042",
    "incubator/code-comments-v5/eval/heldout_fm1.py": "e40f4c675ce2b67b2d11c86ba8231b0ec0b360a8a39e1ab879f32ad278a26f36",
    "incubator/code-comments-v5/eval/heldout_fm2.py": "0072e99537a9f536046a392bcf710068169b64c0b8ec36af70d70e65bd69a3e3",
}

CACHES = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


MODULES = {source: _load(f"code_comments_v5_source_{source.replace('-', '_')}", folder / "grade.py")
           for source, folder in SOURCES.items()}


def _copied_cases() -> dict[str, str]:
    """{case: source} for every folder under cases/ that a source eval also holds."""
    found = {}
    for case in sorted(p.name for p in (HERE / "cases").iterdir() if p.is_dir()):
        owners = [source for source, folder in SOURCES.items()
                  if (folder / "cases" / case).is_dir() and case in MODULES[source].CHECKS]
        if len(owners) > 1:
            raise SystemExit(f"code-comments-v5: case {case} is in more than one source eval: {owners}")
        if owners:
            found[case] = owners[0]
    return found


SOURCE_OF = _copied_cases()
CHECKS = {case: MODULES[source].CHECKS[case] for case, source in SOURCE_OF.items()}

for _name in LOCAL:
    _path = HERE / f"{_name}.py"
    if _path.is_file():
        _local = _load(f"code_comments_v5_{_name}", _path).CHECKS
        _clash = sorted(set(_local) & set(CHECKS))
        if _clash:
            raise SystemExit(f"code-comments-v5: {_path.name} redefines checks for {_clash}")
        CHECKS.update(_local)


# ------------------------------------------------------------------ drift


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _tree(folder: Path) -> dict[str, bytes]:
    if not folder.is_dir():
        return {}
    return {p.relative_to(folder).as_posix(): p.read_bytes().replace(b"\r\n", b"\n")
            for p in folder.rglob("*")
            if p.is_file() and p.suffix != ".pyc" and not CACHES & set(p.relative_to(folder).parts)}


def _hygiene_view(part: str, rel: str, body: bytes, copy: bool) -> bytes:
    """A hygiene file as it would read without this climb's two harness edits."""
    if part == "cases" and rel == "case.yaml" and copy:
        return body.replace(b"held_out: false\n", b"", 1)
    if part == "cases" and rel.startswith("graders/") and rel.endswith(".md") and not copy:
        return body.replace(b"focus: trace\n", b"", 1)
    return body


def drift() -> list[str]:
    """Copied files that differ from their source, and source check files that differ
    from the pins taken at pre-registration. Empty when the copies are faithful."""
    problems = []
    for case, source in sorted(SOURCE_OF.items()):
        for part in ("cases", "references", "hidden"):
            mine, theirs = _tree(HERE / part / case), _tree(SOURCES[source] / part / case)
            if source == "hygiene":
                mine = {rel: _hygiene_view(part, rel, body, True) for rel, body in mine.items()}
                theirs = {rel: _hygiene_view(part, rel, body, False) for rel, body in theirs.items()}
            for rel in sorted(set(mine) | set(theirs)):
                if mine.get(rel) != theirs.get(rel):
                    what = "missing here" if rel not in mine else "not in the source" if rel not in theirs \
                        else "differs from the source"
                    problems.append(f"{part}/{case}/{rel}: {what} ({source})")
    for rel, pin in PINNED.items():
        path = ROOT / rel
        if not path.is_file():
            problems.append(f"{rel}: missing")
        elif _digest(path) != pin:
            problems.append(f"{rel}: changed since pre-registration (sha256 {_digest(path)[:12]})")
    return problems
