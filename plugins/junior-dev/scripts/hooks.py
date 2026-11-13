"""Claude Code hooks that make sure a new plan or diagram gets a junior-dev review.

    python hooks.py post-write   # PostToolUse on Write|Edit|MultiEdit: record the file, remind once
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
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import classify  # noqa: E402
import junior  # noqa: E402

CHANGE_RATIO = 0.7  # a reviewed file whose text is less similar than this is reviewed again


def _nested() -> bool:
    return os.environ.get("JUNIOR_DEV_NESTED") == "1"


def _target(event: dict) -> Path | None:
    raw = (event.get("tool_input") or {}).get("file_path")
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
    return {"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": (
        f"junior-dev: {shown.as_posix()} looks like a {reason}. When you have finished writing it, and before you "
        f"act on it or report it done, run the junior-dev skill on it: a junior developer who sees only this file "
        f"will question you until a fresh junior can explain it back.")}}


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
          "really a plan or diagram, or the user asked you not to review it, say so in one line and stop.")}


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
