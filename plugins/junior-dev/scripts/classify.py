"""Decide whether a written file is a plan or diagram worth a junior-dev review.

Text files only. A Mermaid or ASCII diagram counts once it has at least 4 edges. A Markdown
document counts when its path or headings say it is a plan, spec or design (or it has at
least 5 numbered or checklist steps) and it has at least `min_words` words. Smaller ones are
"tiny" and skipped, as the user asked: a five-line checklist does not need a junior. The
thresholds start here and the activation eval tunes them (docs/junior-dev/design.md).
"""

from __future__ import annotations

from pathlib import PurePath
import re

TEXT_SUFFIXES = {".md", ".markdown", ".mmd", ".txt"}
NOT_PLANS = {"readme", "changelog", "license", "contributing", "code_of_conduct", "security", "history", "authors"}
MIN_EDGES = 4
PLAN_PATH = re.compile(r"plan|spec|design|architect|adr|rfc|proposal|diagram|flow|runbook|migration|rollout|roadmap", re.I)
PLAN_HEADING = re.compile(r"^#{1,4}\s.*\b(plan|steps|design|architecture|approach|rollout|migration|phases?|flow|"
                          r"sequence|proposal)\b", re.I | re.M)
STEP_LINE = re.compile(r"^\s*(\d+[.)]\s|[-*]\s+\[[ xX]\]|step\s+\d+)", re.I | re.M)
FENCE = re.compile(r"```([\w-]*)[^\n]*\n(.*?)```", re.S)
EDGE = re.compile(r"-->|->>|-\.->|==>|--[xo]|<--|<<-|\|\|--|\|o--|\}o--|\}\|--|--\|\{|--o\{|->|<-|=>|[│─▶►▼]")


def edges(block: str) -> int:
    """Lines of a diagram that draw at least one connection."""
    return sum(1 for line in block.splitlines() if not line.strip().startswith("%%") and EDGE.search(line))


def is_artifact(path: str, text: str, min_words: int = 120) -> tuple[bool, str]:
    p = PurePath(str(path).replace("\\", "/"))
    if p.suffix.lower() not in TEXT_SUFFIXES:
        return False, "not a text file"
    if p.stem.lower() in NOT_PLANS:
        return False, "not a plan or diagram"
    if p.suffix.lower() == ".mmd":
        return (True, "mermaid diagram") if edges(text) >= MIN_EDGES else (False, "tiny")
    diagram_seen = False
    for lang, block in FENCE.findall(text):
        count = edges(block)
        if count >= MIN_EDGES:
            return True, "mermaid diagram" if lang.lower() == "mermaid" else "ascii diagram"
        diagram_seen = diagram_seen or (lang.lower() == "mermaid" or count > 0)
    planish = bool(PLAN_PATH.search(str(p)) or PLAN_HEADING.search(text) or len(STEP_LINE.findall(text)) >= 5)
    if planish:
        return (True, "plan document") if len(re.findall(r"\w+", text)) >= min_words else (False, "tiny")
    if diagram_seen:
        return False, "tiny"
    return False, "not a plan or diagram"
