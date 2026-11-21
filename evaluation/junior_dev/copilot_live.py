"""GitHub Copilot activation and fidelity runs for the junior-dev plugin (#52).

The user's target platform is GitHub Copilot (2026-11-19). This runs the same prompts as the
Claude Code activation runs (live_prompts.json) through the Copilot CLI with the plugin
installed, in a fresh copy of fixture/, and records whether the hook reminded the agent, whether
the agent ran the loop the way the skill says, and what it cost in Copilot AI credits.

    python -m evaluation.junior_dev.copilot_live run --models haiku,sonnet [--parallel 4] [--tag copilot-01]

Needs the `copilot` command and a Copilot login (the `gh` login is borrowed through GH_TOKEN).
The plugin is installed into a throwaway COPILOT_HOME, so the user's own Copilot setup is not
touched. Copilot prompts for permission to run a script outside the project, so the plugin's
folder is approved with --add-dir, as a user would approve it once.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time

from . import live

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "live-results" / "copilot"
MODELS = {"haiku": "claude-haiku-5.5", "sonnet": "claude-sonnet-5.5"}
COMMANDS = ("start", "ask", "answer", "teachback", "verdict", "report")
BLOCK = re.compile(r"^\s*(\$|✗|x) Shell\b", re.MULTILINE)
CALL = re.compile(r'junior\.py"?\s+(' + "|".join(COMMANDS) + r")\b")
CREDITS = re.compile(r"AI Credits\s+([0-9.]+)")


def parse(text: str) -> dict:
    """Helper calls (in order), denied calls, credits and the final message from a Copilot CLI transcript."""
    starts = [m.start() for m in BLOCK.finditer(text)]
    helper, denied = [], 0
    for i, s in enumerate(starts):
        block = text[s:starts[i + 1] if i + 1 < len(starts) else len(text)]
        tail_cut = block.find("\n\n")       # a block ends at its first blank line; the rest is the agent's text
        body = " ".join((block if tail_cut == -1 else block[:tail_cut]).split())
        calls = CALL.findall(body)
        if not calls:
            continue
        if block.lstrip().startswith(("✗", "x ")) or "Permission denied" in body:
            denied += 1
            continue
        helper += calls
    last = starts[-1] if starts else 0
    final = text[last:]
    final = final[final.find("\n\n") + 2:] if "\n\n" in final else final
    m = CREDITS.search(text)
    return {"helper": helper, "denied": denied, "credits": float(m.group(1)) if m else None,
            "final": final.split("\nChanges ")[0].strip(), "calls": []}


def fidelity(parsed: dict, state: dict | None) -> dict:
    return live.fidelity(parsed, state)


def _home(plugin_root: Path) -> Path:
    home = Path(tempfile.mkdtemp(prefix="jd-copilot-home-"))
    env = dict(os.environ, COPILOT_HOME=str(home))
    for argv in (["copilot", "plugin", "marketplace", "add", str(plugin_root.parents[1])],
                 ["copilot", "plugin", "install", "junior-dev@code-comments"]):
        subprocess.run([shutil.which(argv[0]) or argv[0], *argv[1:]], env=env, check=True,
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return home


def run_one(item: dict, model: str, home: Path, out_dir: Path, timeout_s: float = 1500) -> dict:
    project = Path(tempfile.mkdtemp(prefix="jd-copilot-proj-"))
    shutil.copytree(live.FIXTURE, project, dirs_exist_ok=True)
    env = dict(os.environ, COPILOT_HOME=str(home))
    env.pop("JUNIOR_DEV_NESTED", None)
    argv = [shutil.which("copilot") or "copilot", "-p", item["prompt"], "--model", MODELS[model],
            "--allow-all-tools", "--no-ask-user", "--add-dir", str(live.PLUGIN)]
    t0 = time.time()
    try:
        done = subprocess.run(argv, cwd=project, env=env, capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=timeout_s)
        text, code = done.stdout + "\n" + done.stderr, done.returncode
    except subprocess.TimeoutExpired as e:
        text, code = (e.stdout or "") if isinstance(e.stdout, str) else "", "timeout"
    seconds = round(time.time() - t0, 1)
    registry = {}
    reg_path = project / ".junior-dev" / "registry.json"
    if reg_path.is_file():
        registry = json.loads(reg_path.read_text(encoding="utf-8"))
    states = [json.loads(p.read_text(encoding="utf-8")) for p in (project / ".junior-dev").glob("*/state.json")]
    parsed = parse(text)
    state = states[0] if states else None
    row = {"id": item["id"], "kind": item["kind"], "model": model, "exit": code, "seconds": seconds,
           "credits": parsed["credits"], "hook_recorded": bool(registry), "registry": {Path(k).name: v.get("status")
                                                                                       for k, v in registry.items()},
           "helper": parsed["helper"], "denied": parsed["denied"], "triggered": "start" in parsed["helper"],
           "end_reason": (state or {}).get("end_reason"), "rounds": (state or {}).get("round"),
           "state_kept": reg_path.is_file()}
    if item["kind"] == "trigger":
        row["fidelity"] = fidelity(parsed, state)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{item['id']}__{model}.txt").write_text(text, encoding="utf-8", newline="\n")
    (out_dir / f"{item['id']}__{model}.json").write_text(json.dumps(row, indent=1), encoding="utf-8", newline="\n")
    shutil.rmtree(project, ignore_errors=True)
    return row


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="copilot_live")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--models", default="haiku,sonnet")
    r.add_argument("--parallel", type=int, default=4)
    r.add_argument("--tag", default="copilot-01")
    r.add_argument("--only", default="")
    args = ap.parse_args(argv)
    prompts = json.loads((HERE / "live_prompts.json").read_text(encoding="utf-8"))
    items = [dict(p, kind=k) for k in ("trigger", "skip") for p in prompts[k]]
    if args.only:
        items = [i for i in items if i["id"] in args.only.split(",")]
    home = _home(live.PLUGIN)
    out_dir = RESULTS / args.tag
    jobs = [(i, m) for m in args.models.split(",") for i in items]
    with ThreadPoolExecutor(max_workers=args.parallel) as pool:
        rows = list(pool.map(lambda j: run_one(j[0], j[1], home, out_dir), jobs))
    (out_dir / "summary.json").write_text(json.dumps(rows, indent=1), encoding="utf-8", newline="\n")
    for row in rows:
        print(json.dumps({k: row.get(k) for k in ("id", "model", "triggered", "hook_recorded", "end_reason",
                                                   "credits", "seconds")}))
    shutil.rmtree(home, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
