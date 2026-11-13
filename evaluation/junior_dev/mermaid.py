"""Check that Mermaid diagrams in an artifact still parse (a guardrail: clarifying must not break them).

With the pinned Node checker installed (tools/mermaid-check: `npm install --ignore-scripts`
there), each ```mermaid block is parsed by Mermaid 11 itself. Without it, a heuristic lint
checks for a known diagram header, balanced brackets outside labels, paired edge-label pipes
and no dangling arrows. The spike (docs/junior-dev/spike-2026-11-12.md, item 6) chose this.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import shutil
import subprocess

TOOL = Path(__file__).resolve().parent / "tools" / "mermaid-check"
FENCE = re.compile(r"```mermaid[^\n]*\n(.*?)```", re.S)
HEADERS = ("flowchart", "graph", "sequenceDiagram", "stateDiagram", "erDiagram", "classDiagram", "gantt", "journey",
           "pie", "gitGraph", "mindmap", "timeline", "quadrantChart", "requirementDiagram", "C4")
ARROW_END = re.compile(r"(-->|---|==>|-\.->|->>|-->>|->|--x|--o)\s*(\|[^|]*\|)?\s*$")
ER_CARDINALITY = re.compile(r"[|}][|o]--|--[|o][|{]|[|}][|o]\.\.|\.\.[|o][|{]")
QUOTED = re.compile(r'"[^"]*"')
PAIRS = {"(": ")", "[": "]", "{": "}"}


def blocks(text: str) -> list[str]:
    return FENCE.findall(text)


def heuristic_errors(src: str) -> list[str]:
    lines = [l for l in src.splitlines() if l.strip() and not l.strip().startswith("%%")]
    if not lines:
        return ["empty diagram"]
    header = lines[0].strip()
    if not header.startswith(HEADERS):
        return [f"unknown diagram header: {header[:40]!r}"]
    kind = header.split()[0]
    errors = []
    for n, line in enumerate(lines[1:], start=2):
        text = QUOTED.sub('""', line)
        if kind.startswith(("sequenceDiagram", "stateDiagram")) and ":" in text:
            text = text.split(":", 1)[0]
        if kind == "erDiagram":
            text = ER_CARDINALITY.sub(" ", text)
        elif "|" in text and text.count("|") % 2:
            errors.append(f"line {n}: unpaired | in an edge label")
        stack = []
        for ch in text:
            if ch in PAIRS:
                stack.append(PAIRS[ch])
            elif ch in PAIRS.values():
                if not stack or stack.pop() != ch:
                    stack = ["!"]
                    break
        if stack and kind != "erDiagram":
            errors.append(f"line {n}: unbalanced brackets")
        if ARROW_END.search(text.rstrip()) and kind.startswith(("flowchart", "graph", "stateDiagram")):
            errors.append(f"line {n}: arrow with no target")
    if kind == "erDiagram":
        body = ER_CARDINALITY.sub(" ", "\n".join(lines[1:]))
        if body.count("{") != body.count("}"):
            errors.append("unbalanced entity braces")
    return errors


def node_available() -> bool:
    return bool(shutil.which("node")) and (TOOL / "node_modules" / "mermaid").is_dir()


def _node_check(sources: list[str]) -> list[list[str]]:
    done = subprocess.run([shutil.which("node"), str(TOOL / "check.mjs"), str(TOOL)], input=json.dumps(sources),
                          capture_output=True, text=True, encoding="utf-8", timeout=600)
    if done.returncode != 0:
        raise RuntimeError(done.stderr[-1000:])
    return [[] if r["ok"] else [r["error"]] for r in json.loads(done.stdout)]


def check_many(texts: list[str]) -> list[list[str]]:
    """Errors per artifact (an empty list means every diagram in it parses, or it has none)."""
    per_text = [blocks(t) for t in texts]
    flat = [b for bs in per_text for b in bs]
    if not flat:
        return [[] for _ in texts]
    try:
        results = _node_check(flat) if node_available() else [heuristic_errors(b) for b in flat]
    except (RuntimeError, OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
        results = [heuristic_errors(b) for b in flat]
    out, i = [], 0
    for bs in per_text:
        errs = [e for r in results[i:i + len(bs)] for e in r]
        out.append(errs)
        i += len(bs)
    return out


def check(text: str) -> list[str]:
    return check_many([text])[0]
