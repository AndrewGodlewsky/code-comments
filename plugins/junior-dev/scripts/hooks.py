"""Hooks that make sure a new plan or diagram gets a junior-dev review, in Claude Code and GitHub Copilot.

    python hooks.py post-write   # PostToolUse on a file write (Claude Code or Copilot tool names): record, remind once
    python hooks.py stop         # Stop: if a recorded file was never reviewed, block once and say so

They exist because a skill's description alone rarely loads it: in this repository Haiku
loaded the code-comments skill in 0 of 18 runs where it should have. Hooks fire every time.
They read the hook's JSON on stdin, keep a registry in <project>/.junior-dev/, and never
fail the session: any error means "say nothing".
"""

from __future__ import annotations

import difflib
import json
import os
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import classify  # noqa: E402
import junior  # noqa: E402

CHANGE_RATIO = 0.7  # a reviewed file whose text is less similar than this is reviewed again


def _nested() -> bool:
    return os.environ.get("JUNIOR_DEV_NESTED") == "1"


HELPER = (HERE / "junior.py").resolve()
PATCH_FILE = re.compile(r"^\*\*\* (?:Add|Update) File: (.+?)\s*$", re.MULTILINE)


def _copilot(event: dict) -> bool:
    """GitHub Copilot sends tool_result / toolResult where Claude Code sends tool_response."""
    return "tool_response" not in event and ("tool_result" in event or "toolResult" in event or "toolArgs" in event)


def _tool_input(event: dict) -> dict:
    raw = event.get("tool_input", event.get("toolArgs")) or {}
    if isinstance(raw, str):    # Copilot's camelCase toolArgs is a JSON string
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            return {"input": raw}
    return raw if isinstance(raw, dict) else {}


def _target(event: dict) -> Path | None:
    args = _tool_input(event)
    # Claude Code: file_path. Copilot create / edit / str_replace_editor: path. apply_patch: in the patch text.
    raw = args.get("file_path") or args.get("path") or args.get("filePath")
    if not raw:
        patch = next((v for v in args.values() if isinstance(v, str) and "*** " in v), "")
        found = PATCH_FILE.findall(patch)
        raw = found[0] if found else None
    if not raw:
        return None
    path = Path(raw)
    if not path.is_absolute():
        path = Path(event.get("cwd") or os.getcwd()) / path
    return path.resolve()


def post_write(event: dict, root: Path) -> dict | None:
    if _nested():
        return None
    path = _target(event)
    if path is None or ".junior-dev" in path.parts or not path.is_file():
        return None
    text = path.read_text(encoding="utf-8", errors="replace")
    ok, reason = classify.is_artifact(str(path), text)
    if not ok:
        return None
    entry = junior.load_registry(root).get(str(path))
    if entry:
        if entry["status"] in ("pending", "reminded", "reviewing"):
            return None
        if entry["status"] == "done":
            if entry.get("hash") == junior.text_hash(text):
                return None
            if difflib.SequenceMatcher(None, entry.get("snapshot") or "", text).ratio() >= CHANGE_RATIO:
                return None
    junior.mark(root, path, "pending")
    try:
        shown = path.relative_to(Path(event.get("cwd") or os.getcwd()).resolve())
    except ValueError:
        shown = path
    context = (
        f"junior-dev: {shown.as_posix()} looks like a {reason}. When you have finished writing it, and before you "
        f"act on it or report it done, run the junior-dev skill on it: a junior developer who sees only this file "
        f"will question you until a fresh junior can explain it back. The skill's helper is: python \"{HELPER}\"")
    if _copilot(event):
        return {"additionalContext": context}
    return {"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": context}}


def stop(event: dict, root: Path) -> dict | None:
    if _nested() or event.get("stop_hook_active"):
        return None
    registry = junior.load_registry(root)
    pending = [p for p, e in registry.items() if e.get("status") == "pending"]
    if not pending:
        return None
    for p in pending:
        junior.mark(root, Path(p), "reminded")
    cwd = Path(event.get("cwd") or os.getcwd()).resolve()

    def shown(p: str) -> str:
        try:
            return Path(p).relative_to(cwd).as_posix()
        except ValueError:
            return p

    return {"decision": "block", "reason": (
        "junior-dev: these plan or diagram files were written in this session but not reviewed: "
        + ", ".join(shown(p) for p in pending)
        + ". Run the junior-dev skill on each one now, then report what changed and the holes. If a file is not "
          "really a plan or diagram, or the user asked you not to review it, say so in one line and stop. "
          f"The skill's helper is: python \"{HELPER}\"")}


def main(argv: list[str]) -> int:
    try:
        mode = argv[0]
        event = json.loads(sys.stdin.buffer.read().decode("utf-8"))
        root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or event.get("cwd") or os.getcwd()) / ".junior-dev"
        out = post_write(event, root) if mode == "post-write" else stop(event, root) if mode == "stop" else None
        if out:
            sys.stdout.buffer.write(json.dumps(out).encode("utf-8"))
    except Exception as e:  # a hook must never break the session
        print(f"junior-dev hook: {type(e).__name__}: {e}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
