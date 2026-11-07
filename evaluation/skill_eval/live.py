"""Live adapter: run headless Claude Code, with one skill variant loaded, on a case workspace.

THIS SPENDS MONEY. Each attempt is one `claude -p` session. Runs need the user's
approval (#6); the first was a pilot approved 2026-11-07.

Isolation, verified with a smoke call on Claude Code 2.1.319:
- `--restricted` removes Bash/PowerShell/WebFetch, confines the file tools to the
  workspace (a temp copy of the case's `visible/`, outside this repository), and
  ignores user/project/local settings files, so the user's plugins and hooks do not
  load. The user's global CLAUDE.md may still load, because `--bare` needs an API key.
  It is identical across arms, so it is a harness deviation, not a between-arm confound.
- `--restricted` also ignores project skills. The variant is therefore loaded as a
  session-only plugin (`--plugin-dir`) and invoked explicitly as `/cce:code-comments`.
  The control arm receives the same prompt with no skill and no prefix.
"""

import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

from .grade import Case


ROOT = Path(__file__).resolve().parents[2]
VARIANTS = ROOT / "skill-variants"
PLUGIN = "cce"
TOOLS = "Read,Edit,Write,Glob,Grep"
TASK_PROMPT = "Complete the request in TASK.md in the current directory. Do not modify TASK.md."
MAX_TOOL_RESULT = 20000


class LiveError(Exception):
    """An attempt that produced no scorable output; never a model failure."""

    def __init__(self, failure_class: str, message: str, model: str | None = None, usage: dict | None = None):
        super().__init__(message)
        self.failure_class, self.model, self.usage = failure_class, model, usage


def build_plugin(skill: str, destination: Path) -> Path | None:
    """Wrap a registered variant in a throwaway plugin directory; None for the control arm."""
    registry = {v["id"]: v for v in json.loads((VARIANTS / "variants.json").read_text(encoding="utf-8"))["variants"]}
    if skill not in registry:
        raise ValueError(f"unknown skill variant {skill!r}; see skill-variants/variants.json")
    if registry[skill].get("control"):
        return None
    plugin = destination / PLUGIN
    (plugin / ".claude-plugin").mkdir(parents=True)
    (plugin / ".claude-plugin" / "plugin.json").write_text(
        json.dumps({"name": PLUGIN, "version": "0.0.0", "description": f"Code Comments eval arm: {skill}"}), encoding="utf-8")
    shutil.copytree(VARIANTS / skill / "code-comments", plugin / "skills" / "code-comments")
    return plugin


def _trace(events: list[dict], prompt: str, skill: str, model: str) -> tuple[list[dict], int]:
    init = next((e for e in events if e.get("type") == "system" and e.get("subtype") == "init"), {})
    turns = [{"role": "system", "content": (
        f"Live adapter: Claude Code {init.get('claude_code_version')}, model {model}, skill variant `{skill}`, "
        f"tools {init.get('tools')}, plugins {[p.get('name') for p in init.get('plugins', [])]}, "
        f"skills loaded from the arm: {[s for s in init.get('skills', []) if s.startswith(PLUGIN)]}.")},
        {"role": "user", "content": prompt}]
    tool_calls = 0
    for event in events:
        content = event.get("message", {}).get("content")
        if event.get("type") == "assistant" and isinstance(content, list):
            for block in content:
                if block.get("type") == "text" and block.get("text", "").strip():
                    turns.append({"role": "assistant", "content": block["text"]})
                elif block.get("type") == "tool_use":
                    tool_calls += 1
                    turns.append({"role": "tool_call", "name": block.get("name"), "content": json.dumps(block.get("input"), indent=2)})
        elif event.get("type") == "user" and isinstance(content, list):
            for block in content:
                if block.get("type") == "tool_result":
                    text = block.get("content")
                    text = text if isinstance(text, str) else json.dumps(text)
                    turns.append({"role": "tool_result", "content": text[:MAX_TOOL_RESULT]})
    return turns, tool_calls


def run(case: Case, workspace: Path, *, skill: str, model: str, timeout_s: float, max_budget_usd: float) -> dict:
    with tempfile.TemporaryDirectory() as temporary:
        plugin = build_plugin(skill, Path(temporary))
        prompt = f"/{PLUGIN}:code-comments {TASK_PROMPT}" if plugin else TASK_PROMPT
        command = ["claude", "-p", prompt, "--model", model, "--output-format", "stream-json", "--verbose",
                   "--restricted", "--tools", TOOLS, "--permission-mode", "acceptEdits", "--strict-mcp-config",
                   "--no-session-persistence", "--max-budget-usd", str(max_budget_usd)]
        if plugin:
            command += ["--plugin-dir", str(plugin)]
        started = time.perf_counter()
        try:
            completed = subprocess.run(command, cwd=workspace, stdin=subprocess.DEVNULL, capture_output=True,
                                       text=True, encoding="utf-8", errors="replace", timeout=timeout_s)
        except subprocess.TimeoutExpired as error:
            raise LiveError("timeout", f"no result within {timeout_s}s") from error
        wall = round(time.perf_counter() - started, 2)
    events = []
    for line in completed.stdout.splitlines():
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    result = next((e for e in reversed(events) if e.get("type") == "result"), None)
    if result is None:
        raise LiveError("harness_error", f"no result event (exit {completed.returncode}): {completed.stderr.strip()[-400:]}")
    usage = {k: result.get("usage", {}).get(k, 0) for k in
             ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")}
    served = {e["message"].get("model") for e in events if e.get("type") == "assistant" and e.get("message", {}).get("model")}
    if not served:
        raise LiveError("harness_error", "no assistant turn", usage=usage)
    if served != {model}:
        raise LiveError("served_model_mismatch", f"requested {model}, served {sorted(served)}", model=",".join(sorted(served)), usage=usage)
    if plugin and not any(s == f"{PLUGIN}:code-comments" for e in events if e.get("subtype") == "init" for s in e.get("skills", [])):
        raise LiveError("harness_error", "skill variant did not load", model=model, usage=usage)
    turns, tool_calls = _trace(events, prompt, skill, model)
    return {
        "note": f"Live run of skill variant `{skill}` ({result.get('subtype')}, {result.get('num_turns')} turns).",
        "trace": turns, "model": model, "usage": usage, "cost_usd": result.get("total_cost_usd"),
        "latency_s": round(result.get("duration_ms", wall * 1000) / 1000, 2), "wall_s": wall,
        "tool_calls": tool_calls, "num_turns": result.get("num_turns"),
        "stop_reason": result.get("subtype"), "is_error": result.get("is_error"),
    }
