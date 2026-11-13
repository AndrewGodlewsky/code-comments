"""Headless plugin runs for Junior-dev: does it trigger, and does a main agent really run the loop? (#52)

THIS SPENDS MONEY against the user's $10 cap for headless runs (docs/junior-dev/design.md,
"Two layers of runs"). Every session is one `claude -p` with the plugin loaded from a copy of
plugins/junior-dev (with or without its hooks), in a throwaway copy of fixture/. The ledger
in spend.json is checked before each session and refuses one that could cross the cap. The
nested junior sessions the helper starts are billed separately, so their cost is read from
the loop's state files and recorded too.

    python -m evaluation.junior_dev.live run <prompt-id> --model haiku --hooks yes|no [--budget 0.40]
"""

from __future__ import annotations

from datetime import date
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PLUGIN = ROOT / "plugins" / "junior-dev"
SPEND = HERE / "spend.json"
FIXTURE = HERE / "fixture"
ALLOWED = "Read,Write,Edit,Glob,Grep,Bash(python *),Bash(python3 *)"
HELPER = re.compile(r"junior\.py[\"']?\s+(start|ask|answer|teachback|verdict|report)\b")


class SpendCapError(Exception):
    pass


def _ledger(ledger: Path) -> dict:
    return json.loads(Path(ledger).read_text(encoding="utf-8"))


def spent(ledger: Path = SPEND) -> float:
    return sum(e["usd"] for e in _ledger(ledger)["entries"])


def guard(max_usd: float, ledger: Path = SPEND) -> None:
    data = _ledger(ledger)
    if spent(ledger) + max_usd > data["cap_usd"] + 1e-9:
        raise SpendCapError(f"${spent(ledger):.3f} spent; a ${max_usd:.2f} run could cross the ${data['cap_usd']:.2f} cap")


def record(what: str, usd: float, ledger: Path = SPEND) -> None:
    data = _ledger(ledger)
    data["entries"].append({"when": date.today().isoformat(), "what": what, "usd": round(float(usd), 6)})
    Path(ledger).write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8", newline="\n")


def plugin_copy(dest: Path, hooks: bool) -> Path:
    """A copy of the plugin, without its hooks for the description-only arm."""
    target = Path(dest) / "junior-dev"
    shutil.copytree(PLUGIN, target, ignore=shutil.ignore_patterns("__pycache__", ".junior-dev"))
    if not hooks:
        shutil.rmtree(target / "hooks")
    return target


def command(model: str, plugin_dir: Path, max_usd: float) -> list[str]:
    return ["claude", "-p", "--plugin-dir", str(plugin_dir), "--setting-sources", "project", "--model", model,
            "--output-format", "stream-json", "--verbose", "--no-session-persistence", "--strict-mcp-config",
            "--max-budget-usd", f"{max_usd:.2f}", "--permission-mode", "acceptEdits", "--allowedTools", ALLOWED]


def parse(stdout: str) -> dict:
    events = []
    for line in stdout.splitlines():
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(e, dict):
            events.append(e)
    calls, helper, results = [], [], {}
    for e in events:
        content = (e.get("message") or {}).get("content")
        for c in content if isinstance(content, list) else []:
            if c.get("type") == "tool_use":
                calls.append({"id": c.get("id"), "name": c.get("name"), "input": c.get("input", {})})
                cmd = str((c.get("input") or {}).get("command", ""))
                m = HELPER.search(cmd)
                if c.get("name") in ("Bash", "PowerShell") and m:
                    helper.append(m.group(1))
            elif c.get("type") == "tool_result":
                results[c.get("tool_use_id")] = c.get("content")
    result = next((e for e in reversed(events) if e.get("type") == "result"), {})
    blob = json.dumps(events)
    return {"events": events, "calls": calls, "helper": helper, "results": results,
            "skill_loaded": any(c["name"] == "Skill" and "junior-dev" in json.dumps(c["input"]) for c in calls),
            "hook_reminder": "junior-dev: " in blob and "looks like a" in blob,
            "final": str(result.get("result") or ""), "cost_usd": float(result.get("total_cost_usd") or 0.0),
            "num_turns": result.get("num_turns"), "is_error": result.get("is_error")}


def activation(parsed: dict) -> dict:
    started = "start" in parsed["helper"]
    return {"skill_loaded": parsed["skill_loaded"], "helper_started": started, "hook_reminder": parsed["hook_reminder"],
            "triggered": parsed["skill_loaded"] or started}


def fidelity(parsed: dict, state: dict | None) -> dict:
    """Did the main agent run the loop the way the skill says? `state` is the loop's state.json, if any."""
    seq, problems = parsed["helper"], []
    if not seq or seq[0] != "start":
        problems.append("did not start with the helper")
    asked = False
    for step in seq:
        if step == "ask":
            asked = True
        if step == "answer" and not asked:
            problems.append("answered before asking")
            break
    if "teachback" not in seq and (state or {}).get("end_reason") != "cap":
        problems.append("no teach-back")
    if "teachback" in seq and "verdict" not in seq[seq.index("teachback"):]:
        problems.append("teach-back without a verdict")
    if "report" not in seq:
        problems.append("no report")
    if state and state.get("round", 0) > state.get("rounds_cap", 6):
        problems.append("ran past the round cap")
    if any(c["name"] == "AskUserQuestion" for c in parsed["calls"]):
        problems.append("asked the user mid-loop")
    final = parsed["final"].lower()
    if not ("chang" in final and ("hole" in final or "open question" in final or "unsure" in final or "unknown" in final)):
        problems.append("final message lacks the changes and holes")
    return {"ok": not problems, "problems": problems, "helper_calls": seq, "end_reason": (state or {}).get("end_reason"),
            "rounds": (state or {}).get("round")}


def run_session(prompt: str, model: str, hooks: bool, max_usd: float, label: str, timeout_s: float = 1200) -> dict:
    """One headless session in a fresh copy of the fixture project. Records its spend, nested juniors included."""
    guard(max_usd)
    with tempfile.TemporaryDirectory(prefix="jd-live-") as tmp:
        workspace = Path(tmp) / "project"
        shutil.copytree(FIXTURE, workspace)
        plugin = plugin_copy(Path(tmp) / "plugin", hooks)
        env = {**os.environ, "CLAUDE_CODE_DISABLE_AUTO_MEMORY": "1"}
        env.pop("JUNIOR_DEV_NESTED", None)
        started = time.perf_counter()
        try:
            done = subprocess.run(command(model, plugin, max_usd), input=prompt, cwd=workspace, capture_output=True,
                                  text=True, encoding="utf-8", errors="replace", timeout=timeout_s, env=env)
            stdout = done.stdout
        except subprocess.TimeoutExpired as e:
            stdout = (e.stdout or b"").decode("utf-8", "replace") if isinstance(e.stdout, bytes) else (e.stdout or "")
        wall = round(time.perf_counter() - started, 1)
        parsed = parse(stdout)
        states = [json.loads(p.read_text(encoding="utf-8")) for p in (workspace / ".junior-dev").glob("*/state.json")]
        junior_cost = sum(s.get("cost_usd", 0.0) for s in states)
        artifacts = {str(p.relative_to(workspace)): p.read_text(encoding="utf-8", errors="replace")
                     for p in workspace.rglob("*.md") if ".junior-dev" not in p.parts and p.stat().st_mtime > 0}
    record(f"{label}: main session ({model}, hooks={hooks})", parsed["cost_usd"])
    if junior_cost:
        record(f"{label}: nested junior turns", junior_cost)
    state = states[0] if states else None
    return {"label": label, "model": model, "hooks": hooks, "wall_s": wall, "cost_usd": parsed["cost_usd"],
            "junior_cost_usd": junior_cost, "num_turns": parsed["num_turns"], "is_error": parsed["is_error"],
            "activation": activation(parsed), "fidelity": fidelity(parsed, state), "state": state,
            "final": parsed["final"], "helper": parsed["helper"], "artifacts": artifacts,
            "tool_names": [c["name"] for c in parsed["calls"]]}


PROMPTS = HERE / "live_prompts.json"
RESULTS = HERE / "live-results"


def prompt_by_id(pid: str) -> tuple[str, str]:
    data = json.loads(PROMPTS.read_text(encoding="utf-8"))
    for kind in ("trigger", "skip"):
        for p in data[kind]:
            if p["id"] == pid:
                return kind, p["prompt"]
    raise KeyError(pid)


def main(argv: list[str]) -> int:
    import argparse
    parser = argparse.ArgumentParser(prog="live")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("run")
    p.add_argument("prompt_id")
    p.add_argument("--model", default="haiku")
    p.add_argument("--hooks", choices=["yes", "no"], default="yes")
    p.add_argument("--budget", type=float, default=0.40)
    p.add_argument("--tag", default="")
    sub.add_parser("spent")
    args = parser.parse_args(argv)
    if args.cmd == "spent":
        print(f"${spent():.4f} of ${_ledger(SPEND)['cap_usd']:.2f}")
        return 0
    kind, prompt = prompt_by_id(args.prompt_id)
    label = f"{args.tag + '-' if args.tag else ''}{args.prompt_id}-{args.model}-{'hooks' if args.hooks == 'yes' else 'desc'}"
    result = run_session(prompt, args.model, args.hooks == "yes", args.budget, label)
    result.update(prompt_id=args.prompt_id, kind=kind, prompt=prompt)
    RESULTS.mkdir(exist_ok=True)
    out = RESULTS / f"{label}.json"
    if out.exists():
        raise FileExistsError(out)
    out.write_text(json.dumps(result, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    a, f = result["activation"], result["fidelity"]
    print(f"{label}: triggered={a['triggered']} (skill={a['skill_loaded']}, helper={a['helper_started']}, "
          f"reminder={a['hook_reminder']}) fidelity_ok={f['ok']} {f['problems']} cost=${result['cost_usd']:.3f}"
          f"+${result['junior_cost_usd']:.3f} wall={result['wall_s']}s")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main(sys.argv[1:]))
