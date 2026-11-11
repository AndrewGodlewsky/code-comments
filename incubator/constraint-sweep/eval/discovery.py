"""Did each run find its case's evidence before its first edit?

ADR 0001's revisit clause is about runs where "the agent never opens or searches the
file that holds the fact". The hidden tests cannot tell "never found it" from "found it
and ignored it", so this script reads the agent transcripts. For each run in an
iteration's runs.json, and for each file in its case's ``evidence_in``, it reports what
happened before the run's first file edit:

- ``read``: the agent opened the file (a Read of it, or a shell command that names it);
- ``hit``: a search (Grep, or rg, grep, findstr or Select-String in a shell) printed
  the file's path, so the agent saw that the file matched (and, unless the search
  listed file names only, the matching line);
- ``null``: neither.

Listing files (Glob, ls, find) does not count: it shows a name, not what the file says.
An edit made only through the shell (sed -i, a redirect) is not recognised, so such a
run is reported with no first edit and every call counts. A grep run from inside a
subfolder prints paths relative to that folder, which this script does not match.

It reads the transcripts each time and stores nothing; the report goes to stdout.
From the repository root:

    python incubator/constraint-sweep/eval/discovery.py --iteration NAME TRANSCRIPT_DIR [...]
    python incubator/constraint-sweep/eval/discovery.py --runs-json PATH TRANSCRIPT_DIR [...]

TRANSCRIPT_DIR is searched recursively for ``*.jsonl`` agent transcripts (Claude Code's
format). A transcript belongs to a run when its first user message starts with the
harness prompt "You are working in the repository at <outputs>".
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
SHELL_TOOLS = {"Bash", "PowerShell"}
SHELL_SEARCH = re.compile(r"(?:^|[\s|;&(])(?:rg|grep|egrep|fgrep|findstr|select-string|sls)(?:\.exe)?\b",
                          re.IGNORECASE)
PROMPT = re.compile(r"You are working in the repository at (\S+)")


def _norm(value: str) -> str:
    return value.replace("\\", "/").lower()


def evidence_in(case: str) -> list[str]:
    """The case's evidence_in list from case.yaml."""
    path = HERE / "cases" / case / "case.yaml"
    if not path.is_file():
        return []
    match = re.search(r"^evidence_in:\s*\[(.*?)\]\s*$", path.read_text(encoding="utf-8"), re.M)
    return [item.strip().strip("'\"") for item in match.group(1).split(",") if item.strip()] if match else []


def _text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(item.get("text", "") for item in content if isinstance(item, dict))
    return ""


def read_transcript(path: Path) -> tuple[str | None, list[tuple[str, dict, str]]]:
    """The first user message, and every tool call as (name, input, result text) in order.
    Only assistant and user events are read; other event types repeat the same calls."""
    first, calls, results = None, [], {}
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            kind = event.get("type")
            message = event.get("message")
            content = message.get("content") if isinstance(message, dict) else None
            if first is None and kind == "user":
                if isinstance(content, str):
                    first = content
                elif isinstance(content, list):
                    texts = [i.get("text", "") for i in content if isinstance(i, dict) and i.get("type") == "text"]
                    first = "\n".join(texts) or None
            if not isinstance(content, list):
                continue
            for item in content:
                if not isinstance(item, dict):
                    continue
                if kind == "assistant" and item.get("type") == "tool_use":
                    calls.append(item)
                elif kind == "user" and item.get("type") == "tool_result":
                    results[item.get("tool_use_id")] = _text(item.get("content"))
    return first, [(c.get("name", ""), c.get("input") or {}, results.get(c.get("id"), "")) for c in calls]


def _names(target: str, rel: str) -> bool:
    return target == rel or target.endswith("/" + rel)


def classify(calls: list[tuple[str, dict, str]], evidence: list[str]) -> dict:
    """For each evidence file: "read", "hit" or None before the first edit."""
    first_edit = next((i for i, (name, _, _) in enumerate(calls) if name in EDIT_TOOLS), None)
    found: dict[str, str | None] = {rel: None for rel in evidence}
    for name, args, result in calls[:first_edit]:
        for rel in evidence:
            key = _norm(rel)
            if found[rel] == "read":
                continue
            if name == "Read" and _names(_norm(str(args.get("file_path", ""))), key):
                found[rel] = "read"
            elif name in SHELL_TOOLS:
                command = _norm(str(args.get("command", "")))
                if key in command:
                    found[rel] = "read"
                elif SHELL_SEARCH.search(command) and key in _norm(result):
                    found[rel] = "hit"
            elif name == "Grep" and (_names(_norm(str(args.get("path", ""))), key) or key in _norm(result)):
                found[rel] = "hit"
    return {"tool_calls": len(calls), "first_edit": first_edit, "evidence": found,
            "found_before_edit": any(found.values())}


def discovery(entries: list[dict], transcript_dirs: list[Path]) -> dict:
    wanted = {_norm(e["outputs"]).rstrip("/"): e for e in entries}
    runs: dict[str, dict] = {}
    for directory in transcript_dirs:
        for path in sorted(Path(directory).rglob("*.jsonl")):
            first, calls = read_transcript(path)
            match = PROMPT.search((first or "").replace("\\", "/"))
            entry = wanted.get(_norm(match.group(1)).rstrip("/")) if match else None
            if entry is None:
                continue
            if entry["id"] in runs:
                runs[entry["id"]].setdefault("other_transcripts", []).append(path.name)
                continue
            runs[entry["id"]] = {"case": entry["case"], "arm": entry["arm"], "transcript": path.name,
                                 **classify(calls, evidence_in(entry["case"]))}
    summary: dict[str, dict] = {}
    for run in runs.values():
        cell = summary.setdefault(run["case"], {}).setdefault(run["arm"], {"runs": 0, "found_before_edit": 0})
        cell["runs"] += 1
        cell["found_before_edit"] += run["found_before_edit"]
        for rel, how in run["evidence"].items():
            counts = cell.setdefault(rel, {"read": 0, "hit": 0})
            if how:
                counts[how] += 1
    missing = sorted(e["id"] for e in entries if e["id"] not in runs)
    return {"checked": len(runs), "missing_transcripts": missing, "summary": summary, "runs": runs}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--iteration", help="an iteration under eval/iterations/")
    source.add_argument("--runs-json", type=Path, help="a runs.json written by harness.py prepare")
    parser.add_argument("transcripts", nargs="+", type=Path)
    args = parser.parse_args(argv)
    path = args.runs_json or HERE / "iterations" / args.iteration / "runs.json"
    entries = json.loads(path.read_text(encoding="utf-8"))
    print(json.dumps(discovery(entries, args.transcripts), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
