"""Host runner for the narwhals long-horizon pilot (#37, #41).

    python -m evaluation.skill_eval.pilot run --out DIR --arms oracle,null --reps 1
    python -m evaluation.skill_eval.pilot run --out DIR --arms haiku-plain,...   (dry: no --live)
    python -m evaluation.skill_eval.pilot run --out DIR --arms ... --live --credential api-key --cap 60
    python -m evaluation.skill_eval.pilot run --out DIR --arms ... --live --credential oauth \
        --credential-file .env.pilot --cap 5
    python -m evaluation.skill_eval.pilot summary --out DIR
    python -m evaluation.skill_eval.pilot cleanup --out DIR

The design is in docs/evaluation/pilot-preregistration.md. Each arm and rep (a lane)
has its own narwhals tree in a Docker volume, carried from step to step. All git work
and scoring run in the runtime container (pilot_inner.py) as uid 1000 with no network.
Model sessions run in the agent container with the lane's volume and nothing else
from the host.

--live SPENDS MONEY and needs the user's approval of --cap. Without --live, the live
arms run in dry mode: they act like the null arm and record the commands they would run.
"""

import argparse
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import threading
import time
import uuid
import xml.etree.ElementTree as ElementTree

from . import live
from .pilot_inner import read_constructors, test_command


ROOT = Path(__file__).resolve().parents[2]
PILOT = ROOT / "evaluation" / "pilot"
TASKS = PILOT / "tasks.md"
SKILL_DIR = ROOT / "skill-variants" / "lean" / "code-comments"
RUNTIME_IMAGE = "code-comments-pilot:runtime"
AGENT_IMAGE = "code-comments-pilot:agent"
HAIKU, SONNET = "claude-haiku-5-5", "claude-sonnet-5-5"
STEPS = list(range(0, 7))

INSTRUCT = ("Keep the codebase clean: reuse what already exists, change only what the feature needs, "
            "and don't rewrite working code.")
CHECKLIST = """\
Review the change against this checklist, and nothing else:
1. Unnecessary rewrites: working code changed or reformatted without need.
2. Duplication: new code that repeats a helper or pattern that already exists in the repository.
3. Unrequested restructuring: moves, renames or new abstractions the task did not ask for.
4. Behaviour drift: changes to behaviour outside what the task asks for.
5. Stale comments: comments or docstrings the change made wrong.
"""
REVIEW_DIFF_CHARS = 60000

ARMS = {
    "oracle": {"kind": "oracle"},
    "null": {"kind": "null"},
    "haiku-plain": {"kind": "live", "model": HAIKU},
    "haiku-instruct": {"kind": "live", "model": HAIKU, "instruct": True},
    "haiku-skill": {"kind": "live", "model": HAIKU, "skill": True},
    "haiku-review": {"kind": "live", "model": HAIKU, "review": True},
    "sonnet-plain": {"kind": "live", "model": SONNET},
}
LIVE_ARMS = [name for name, arm in ARMS.items() if arm["kind"] == "live"]
CREDENTIALS = {"api-key": "ANTHROPIC_API_KEY", "oauth": "CLAUDE_CODE_OAUTH_TOKEN"}
IMPLEMENT_TOOLS = "Read,Edit,Write,Glob,Grep,Bash"
REVIEW_TOOLS = "Read,Glob,Grep"
# Bash commands worth a human look: installs, downloads and anything reaching GitHub.
FLAGGED_BASH = re.compile(r"\b(pip|uv|curl|wget)\b|github\.com")

HARNESS_PATHS = [
    "evaluation/skill_eval/pilot.py", "evaluation/skill_eval/pilot_inner.py", "evaluation/skill_eval/live.py",
    "evaluation/skill_eval/churn.py", "evaluation/pilot/Dockerfile", "evaluation/pilot/tasks.md",
    "evaluation/pilot/chain/1-pr3996.diff", "evaluation/pilot/chain/2-pr4001.diff",
    "evaluation/pilot/chain/3-pr3815.diff", "evaluation/pilot/chain/4-pr4038.diff",
    "evaluation/pilot/chain/5-pr4017.diff", "evaluation/pilot/chain/6-pr3915.diff",
    "evaluation/pilot/chain/constructors.env", "skill-variants/lean/code-comments/SKILL.md",
    "scripts/stale_refs.py",
]


def harness_sha(paths: list[str] = HARNESS_PATHS) -> str:
    digest = hashlib.sha256()
    for relative in sorted(paths):
        digest.update(relative.encode())
        digest.update((ROOT / relative).read_bytes().replace(b"\r\n", b"\n"))
    return digest.hexdigest()


# Task statements and prompts.

def parse_tasks(text: str) -> dict[int, str]:
    """{step: statement}. The first paragraph under each heading, "(Upstream: ...)", is not sent."""
    tasks = {}
    for match in re.finditer(r"^### Step (\d+)\n(.*?)(?=^### |\Z)", text, re.MULTILINE | re.DOTALL):
        paragraphs = match.group(2).strip().split("\n\n")
        if paragraphs and paragraphs[0].startswith("(Upstream:"):
            paragraphs = paragraphs[1:]
        tasks[int(match.group(1))] = "\n\n".join(paragraphs).strip()
    return tasks


def base_prompt(arm: str, task: str, constructors: str) -> str:
    """The implementer prompt, without the skill prefix (live.py-style prefixing happens in the command)."""
    prompt = (f"{task}\n\nThe repository is narwhals, in the current directory. "
              f"Run the tests with: {' '.join(test_command(constructors))}")
    if ARMS[arm].get("instruct"):
        prompt += f"\n\n{INSTRUCT}"
    return prompt


def review_prompt(task: str, diff: str) -> str:
    if len(diff) > REVIEW_DIFF_CHARS:
        diff = diff[:REVIEW_DIFF_CHARS] + f"\n[... diff truncated at {REVIEW_DIFF_CHARS} characters]"
    return (f"You are reviewing a change to narwhals, in the current directory. Do not edit anything; "
            f"read the code as needed and reply with your findings only.\n\nThe task was:\n\n{task}\n\n"
            f"{CHECKLIST}\nFor each finding, give the file, what is wrong and what to do instead. "
            f"If there are none, say so.\n\nThe change:\n\n```diff\n{diff}\n```")


def revision_prompt(prompt: str, findings: str) -> str:
    return (f"{prompt}\n\nA change for this task is already in the working tree. A reviewer read it "
            f"and reported the findings below. Address the ones that are right, and keep the "
            f"behaviour the task asks for.\n\n{findings}")


def flagged_bash(events: list[dict]) -> list[str]:
    commands = []
    for event in events:
        content = event.get("message", {}).get("content")
        if event.get("type") == "assistant" and isinstance(content, list):
            for block in content:
                if block.get("type") == "tool_use" and block.get("name") == "Bash":
                    command = str(block.get("input", {}).get("command", ""))
                    if FLAGGED_BASH.search(command):
                        commands.append(command)
    return commands


# Test results.

def parse_junit(path: Path) -> dict[str, tuple[str, str]]:
    """{test id: (status, file)}; status is passed, failed, error, skipped or xfail."""
    results = {}
    for case in ElementTree.parse(path).getroot().iter("testcase"):
        status = "passed"
        for child in case:
            if child.tag in ("failure", "error"):
                status = "failed" if child.tag == "failure" else "error"
                break
            if child.tag == "skipped":
                status = "xfail" if child.get("type") == "pytest.xfail" else "skipped"
        results[f"{case.get('classname')}::{case.get('name')}"] = (status, case.get("file") or "")
    return results


def test_modules(hidden: list[str]) -> set[str]:
    """The hidden files that are test modules (not conftest or plugin support)."""
    names = {path for path in hidden if path.startswith("tests/") and path.endswith(".py")}
    return {path for path in names if Path(path).name.startswith("test_") or Path(path).name.endswith("_test.py")}


def step_passes(junit: dict | None, hidden: list[str]) -> bool:
    """Every test in the step's hidden test modules passes, and at least one ran."""
    if not junit:
        return False
    modules = test_modules(hidden)
    statuses = [status for status, file in junit.values() if file in modules]
    return any(s == "passed" for s in statuses) and not any(s in ("failed", "error") for s in statuses)


def regressions(before: dict | None, after: dict | None, hidden: list[str]) -> list[str]:
    """Tests that passed before the step and failed, errored or vanished after it, outside its hidden files."""
    if not before:
        return []
    after = after or {}
    hidden = set(hidden)
    return sorted(test for test, (status, file) in before.items()
                  if status == "passed" and file not in hidden and after.get(test, ("missing", ""))[0] != "passed")


# Budget.

class Budget:
    """A spending cap that reserves each unit's worst case before it starts."""

    def __init__(self, cap: float, per_session: float, spent: float = 0.0):
        self.cap, self.per_session, self.spent, self.reserved = cap, per_session, spent, 0.0
        self.lock = threading.Lock()

    def reserve(self, sessions: int) -> float | None:
        amount = sessions * self.per_session
        with self.lock:
            if self.spent + self.reserved + amount > self.cap + 1e-9:
                return None
            self.reserved += amount
            return amount

    def settle(self, reserved: float, cost: float) -> None:
        with self.lock:
            self.reserved -= reserved
            self.spent += cost


# Docker.

def docker_path(path: Path) -> str:
    return path.resolve().as_posix()


def volume(run_id: str, lane: str) -> str:
    return f"ccpilot-{run_id}-{lane}"


def inner_command(out: Path, run_id: str, lane_volume: str, args: list[str], *, root: bool = False,
                  oracle: bool = True) -> list[str]:
    command = ["docker", "run", "--rm", "--network", "none"]
    if not root:
        command += ["--user", "1000:1000"]
    command += ["-e", "HOME=/tmp", "-e", "PYTHONDONTWRITEBYTECODE=1", "-e", "GIT_CONFIG_COUNT=1",
                "-e", "GIT_CONFIG_KEY_0=safe.directory", "-e", "GIT_CONFIG_VALUE_0=*",
                "-v", f"{docker_path(ROOT)}:/harness:ro", "-v", f"{lane_volume}:/work/narwhals"]
    if oracle:
        command += ["-v", f"{volume(run_id, 'oracle-chain')}:/oracle:ro"]
    command += ["-v", f"{docker_path(out)}:/out", "-w", "/harness", RUNTIME_IMAGE,
                "python", "-m", "evaluation.skill_eval.pilot_inner", *args]
    return command


def run_inner(out: Path, run_id: str, lane_volume: str, args: list[str], **kwargs) -> dict:
    env = {**os.environ, "MSYS_NO_PATHCONV": "1"}
    completed = subprocess.run(inner_command(out, run_id, lane_volume, args, **kwargs), capture_output=True,
                               text=True, encoding="utf-8", errors="replace", env=env)
    if completed.returncode != 0:
        raise RuntimeError(f"inner {args[0]} failed ({completed.returncode}): "
                           f"{(completed.stderr or completed.stdout).strip()[-2000:]}")
    return json.loads(completed.stdout.strip().splitlines()[-1])


def session_command(name: str, lane_volume: str, prompt: str, *, model: str, tools: str, max_budget: float,
                    credential: str, read_only: bool = False, plugin_root: Path | None = None) -> list[str]:
    command = ["docker", "run", "--rm", "-i", "--name", name,
               "-v", f"{lane_volume}:/work/narwhals" + (":ro" if read_only else ""),
               "-e", "CLAUDE_CODE_DISABLE_AUTO_MEMORY=1", "-e", CREDENTIALS[credential]]
    if plugin_root:
        command += ["-v", f"{docker_path(plugin_root)}:/plugin:ro"]
    command += ["-w", "/work/narwhals", AGENT_IMAGE,
                "claude", "-p", prompt, "--model", model, "--output-format", "stream-json", "--verbose",
                "--tools", tools, "--permission-mode", "acceptEdits", "--strict-mcp-config",
                "--no-session-persistence", "--max-budget-usd", str(max_budget)]
    if "Bash" in tools.split(","):
        command += ["--allowedTools", "Bash"]
    if plugin_root:
        command += ["--plugin-dir", f"/plugin/{live.PLUGIN}"]
    return command


def redact(command: list[str]) -> list[str]:
    """The command as recorded: the prompt is stored separately, and no secret is ever in it."""
    return ["<prompt>" if i and command[i - 1] == "-p" else part for i, part in enumerate(command)]


# The run.

class Runner:
    def __init__(self, args):
        self.args, self.out = args, Path(args.out).resolve()
        self.lock = threading.Lock()
        self.tasks = parse_tasks(TASKS.read_text(encoding="utf-8"))
        self.constructors = read_constructors()
        self.live = getattr(args, "live", False)
        self.finished: set[tuple] = set()

    # Records.

    def append(self, name: str, record: dict) -> None:
        with self.lock, (self.out / name).open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record) + "\n")

    def done(self) -> dict[tuple, dict]:
        path = self.out / "results.jsonl"
        if not path.exists():
            return {}
        records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        return {(r["arm"], r["rep"], r["step"]): r for r in records}

    def log(self, message: str) -> None:
        with self.lock:
            print(f"[{time.strftime('%H:%M:%S')}] {message}", flush=True)

    # Setup.

    def setup(self) -> None:
        self.out.mkdir(parents=True, exist_ok=True)
        config_path = self.out / "run.json"
        if config_path.exists():
            config = json.loads(config_path.read_text(encoding="utf-8"))
            if config["harness_sha"] != harness_sha():
                raise SystemExit("the harness changed since this run started; use a new --out")
        else:
            config = {"run_id": uuid.uuid4().hex[:8], "started": time.strftime("%Y-%m-%dT%H:%M:%S"),
                      "harness_sha": harness_sha(), "arms": self.args.arms, "reps": self.args.reps,
                      "steps": self.args.steps, "live": self.live, "cap": getattr(self.args, "cap", None),
                      "max_budget": getattr(self.args, "max_budget", None),
                      "timeout": getattr(self.args, "timeout", None),
                      "images": {image: image_id(image) for image in self.images()}}
            config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
        self.config, self.run_id = config, config["run_id"]
        chain = volume(self.run_id, "oracle-chain")
        if not (self.out / "oracle.json").exists():
            self.log("building the oracle chain")
            subprocess.run(["docker", "volume", "rm", "-f", chain], capture_output=True)
            subprocess.run(["docker", "volume", "create", chain], check=True, capture_output=True)
            run_inner(self.out, self.run_id, chain, ["init-oracle"], root=True, oracle=False)
        self.oracle = json.loads((self.out / "oracle.json").read_text(encoding="utf-8"))
        if any(ARMS[a].get("skill") for a in self.args.arms) and not (self.out / "plugin" / live.PLUGIN).exists():
            live.build_plugin_dir(SKILL_DIR, self.out / "plugin", "lean")

    def images(self) -> list[str]:
        return [RUNTIME_IMAGE] + ([AGENT_IMAGE] if self.live else [])

    def init_lane(self, lane: str) -> str:
        name = volume(self.run_id, lane)
        state = self.out / "lanes" / f"{lane}.json"
        if state.exists():
            return json.loads(state.read_text(encoding="utf-8"))["start"]
        subprocess.run(["docker", "volume", "rm", "-f", name], capture_output=True)
        subprocess.run(["docker", "volume", "create", name], check=True, capture_output=True)
        result = run_inner(self.out, self.run_id, name, ["init-arm"], root=True, oracle=False)
        if result["status"]:
            raise RuntimeError(f"lane {lane} did not start clean: {result['status'][:5]}")
        state.parent.mkdir(parents=True, exist_ok=True)
        state.write_text(json.dumps(result), encoding="utf-8")
        return result["start"]

    # One step of one lane.

    def step(self, arm: str, rep: int, k: int, pre: str) -> dict:
        lane, label = f"{arm}-r{rep}", f"{arm}-r{rep}-s{k}"
        name = volume(self.run_id, lane)
        record = {"arm": arm, "rep": rep, "step": k, "label": label, "pre": pre, "sessions": [],
                  "harness_failed": False, "retries": 0}
        kind = ARMS[arm]["kind"]
        if k == 0:
            run_inner(self.out, self.run_id, name, ["reset", "--pre", pre])
        elif kind == "oracle" or kind == "null" or not self.live:
            mode = "oracle" if kind == "oracle" else "null"
            run_inner(self.out, self.run_id, name, ["implement", "--mode", mode, "--step", str(k), "--pre", pre])
            if kind == "live":
                self.dry_sessions(arm, k, label, name, pre)
        else:
            self.live_step(arm, k, label, name, pre, record)
        score = run_inner(self.out, self.run_id, name, ["score", "--step", str(k), "--pre", pre, "--label", label])
        record.update(score)
        record["pass"] = None if k == 0 else (not record["harness_failed"] and step_passes(
            self.junit(label), score["hidden"]))
        return record

    def junit(self, label: str) -> dict | None:
        path = self.out / "junit" / f"{label}.xml"
        return parse_junit(path) if path.exists() else None

    def prompts(self, arm: str, k: int) -> str:
        return base_prompt(arm, self.tasks[k], self.constructors)

    def plugin_root(self, arm: str) -> Path | None:
        return self.out / "plugin" if ARMS[arm].get("skill") else None

    def implementer_prompt(self, arm: str, k: int) -> str:
        prompt = self.prompts(arm, k)
        return f"/{live.PLUGIN}:{SKILL_DIR.name} {prompt}" if ARMS[arm].get("skill") else prompt

    def dry_sessions(self, arm: str, k: int, label: str, name: str, pre: str) -> None:
        """Record what a live step would run, without running a model."""
        arm_spec, credential = ARMS[arm], getattr(self.args, "credential", None) or "api-key"
        budget = getattr(self.args, "max_budget", None) or 2.0
        prompt = self.implementer_prompt(arm, k)
        sessions = [{"role": "implement", "prompt": prompt, "command": redact(session_command(
            f"ccpilot-{label}", name, prompt, model=arm_spec["model"], tools=IMPLEMENT_TOOLS, max_budget=budget,
            credential=credential, plugin_root=self.plugin_root(arm)))}]
        if arm_spec.get("review"):
            diff = run_inner(self.out, self.run_id, name, ["diff", "--pre", pre, "--to", f"reviews/{label}.diff"])
            text = (self.out / diff["path"]).read_text(encoding="utf-8")
            prompt = review_prompt(self.tasks[k], text)
            sessions.append({"role": "review", "prompt": prompt, "command": redact(session_command(
                f"ccpilot-{label}-review", name, prompt, model=SONNET, tools=REVIEW_TOOLS, max_budget=budget,
                credential=credential, read_only=True))})
            prompt = revision_prompt(self.prompts(arm, k), "<the reviewer's findings>")
            sessions.append({"role": "revise", "prompt": prompt, "command": redact(session_command(
                f"ccpilot-{label}-revise", name, prompt, model=HAIKU, tools=IMPLEMENT_TOOLS, max_budget=budget,
                credential=credential))})
        path = self.out / "sessions" / f"{label}.dry.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(sessions, indent=2), encoding="utf-8")

    def session(self, label: str, role: str, name: str, prompt: str, *, model: str, tools: str,
                read_only: bool = False, plugin_root: Path | None = None, pre: str) -> dict:
        """One live session. Raises live.LiveError for a harness failure."""
        container = f"ccpilot-{self.run_id}-{label}-{role}"
        command = session_command(container, name, prompt, model=model, tools=tools,
                                  max_budget=self.args.max_budget, credential=self.args.credential,
                                  read_only=read_only, plugin_root=plugin_root)
        started = time.perf_counter()
        try:
            completed = subprocess.run(command, stdin=subprocess.DEVNULL, capture_output=True, text=True,
                                       encoding="utf-8", errors="replace", timeout=self.args.timeout,
                                       env={**os.environ, "MSYS_NO_PATHCONV": "1"})
        except subprocess.TimeoutExpired as error:
            subprocess.run(["docker", "kill", container], capture_output=True)
            if role == "review":
                raise live.LiveError("timeout", f"review exceeded {self.args.timeout}s") from error
            changed = run_inner(self.out, self.run_id, name,
                                ["diff", "--pre", pre, "--to", f"sessions/{label}-{role}.timeout.diff"])
            if not changed["chars"]:
                raise live.LiveError("timeout", f"no edit within {self.args.timeout}s") from error
            return {"role": role, "stop_reason": "timeout", "cost_usd": None, "wall_s": self.args.timeout}
        wall = round(time.perf_counter() - started, 2)
        result = live.parse_session(completed.stdout, completed.stderr, completed.returncode, model=model,
                                    label=label, prompt=prompt,
                                    skill_name=SKILL_DIR.name if plugin_root else None, wall=wall)
        path = self.out / "sessions" / f"{label}-{role}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result), encoding="utf-8")
        return {"role": role, "model": model, "cost_usd": result["cost_usd"], "usage": result["usage"],
                "stop_reason": result["stop_reason"], "is_error": result["is_error"],
                "num_turns": result["num_turns"], "tool_calls": result["tool_calls"], "wall_s": wall,
                "flagged_bash": flagged_bash(result["events"]), "result_text": result["result_text"]}

    def charge(self, reservation: float, entry: dict) -> None:
        cost = entry.get("cost_usd")
        self.budget.settle(reservation, self.args.max_budget if cost is None else cost)

    def attempt(self, arm: str, k: int, label: str, name: str, pre: str, record: dict) -> None:
        """One try at a live step: the implementer, and for the review arm a review and a revision."""
        spec = ARMS[arm]
        for role in ["implement", "review", "revise"] if spec.get("review") else ["implement"]:
            if role == "review":
                diff = run_inner(self.out, self.run_id, name, ["diff", "--pre", pre, "--to", f"reviews/{label}.diff"])
                text = (self.out / diff["path"]).read_text(encoding="utf-8")
                prompt, model, tools, read_only, plugin_root = (review_prompt(self.tasks[k], text), SONNET,
                                                                REVIEW_TOOLS, True, None)
            elif role == "revise":
                findings = record["sessions"][-1].get("result_text") or "(The reviewer reported nothing.)"
                prompt, model, tools, read_only, plugin_root = (revision_prompt(self.prompts(arm, k), findings),
                                                                HAIKU, IMPLEMENT_TOOLS, False, None)
            else:
                prompt, model, tools, read_only, plugin_root = (self.implementer_prompt(arm, k), spec["model"],
                                                                IMPLEMENT_TOOLS, False, self.plugin_root(arm))
            reservation = self.budget.reserve(1)
            if reservation is None:
                raise BudgetExhausted(label)
            try:
                entry = self.session(label, role, name, prompt, model=model, tools=tools, read_only=read_only,
                                     plugin_root=plugin_root, pre=pre)
            except live.LiveError:
                self.budget.settle(reservation, self.args.max_budget)
                raise
            self.charge(reservation, entry)
            record["sessions"].append(entry)

    def live_step(self, arm: str, k: int, label: str, name: str, pre: str, record: dict) -> None:
        for attempt in range(2):
            run_inner(self.out, self.run_id, name, ["reset", "--pre", pre])
            try:
                self.attempt(arm, k, label, name, pre, record)
                return
            except live.LiveError as error:
                failure = {"label": label, "attempt": attempt + 1, "class": error.failure_class,
                           "message": str(error), "model": error.model, "usage": error.usage}
                self.append("errors.jsonl", failure)
                self.log(f"{label}: harness failure {error.failure_class} (attempt {attempt + 1})")
                record["sessions"].append({"role": "failed", **failure})
                record["retries"] = attempt + 1
        run_inner(self.out, self.run_id, name, ["reset", "--pre", pre])
        record["harness_failed"] = True

    # Scheduling.

    def run(self) -> None:
        self.setup()
        if self.live:
            spent = sum(s.get("cost_usd") or 0 for r in self.done().values() for s in r["sessions"])
            self.budget = Budget(self.args.cap, self.args.max_budget, spent)
        done = self.done()
        lanes = [(arm, rep) for arm in self.args.arms for rep in range(1, self.args.reps + 1)]
        pres = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.args.jobs) as pool:
            for arm, rep in lanes:
                pres[(arm, rep)] = self.init_lane(f"{arm}-r{rep}")
            for k in [0] + [s for s in self.args.steps if s]:
                pending = []
                for lane in lanes:
                    key = (*lane, k)
                    if key in done:
                        pres[lane] = done[key]["after"]
                        continue
                    if k and (*lane, k - 1) not in done and not self.completed_now(lane, k - 1):
                        continue  # an earlier step of this lane stopped (budget); keep lanes aligned
                    pending.append((lane, pool.submit(self.step, *lane, k, pres[lane])))
                stopped = False
                for lane, future in pending:
                    try:
                        record = future.result()
                    except BudgetExhausted as error:
                        self.log(f"budget exhausted before {error}; stopping after step {k - 1}")
                        stopped = True
                        continue
                    self.append("results.jsonl", record)
                    pres[lane] = record["after"]
                    self.finished.add((*lane, k))
                    self.log(f"{record['label']}: pass={record['pass']} churn={record['churn']} "
                             f"pytest={record['pytest_exit']} {record['wall_s']}s")
                if stopped:
                    break
        print(json.dumps(summarise(self.out), indent=2)[:4000])

    def completed_now(self, lane: tuple, k: int) -> bool:
        return (*lane, k) in self.finished


class BudgetExhausted(Exception):
    pass


def image_id(image: str) -> str:
    completed = subprocess.run(["docker", "image", "inspect", "-f", "{{.Id}}", image], capture_output=True, text=True)
    if completed.returncode != 0:
        raise SystemExit(f"image {image} is not built; see evaluation/pilot/README.md")
    return completed.stdout.strip()


# Summary.

def summarise(out: Path) -> dict:
    out = Path(out)
    records = [json.loads(line) for line in (out / "results.jsonl").read_text(encoding="utf-8").splitlines()
               if line.strip()]
    oracle = {s["step"]: s for s in json.loads((out / "oracle.json").read_text(encoding="utf-8"))["steps"]}
    by_lane: dict[tuple, dict[int, dict]] = {}
    for record in records:
        by_lane.setdefault((record["arm"], record["rep"]), {})[record["step"]] = record
    reference_dup = oracle[6]["duplication"] - oracle[0]["duplication"] if 6 in oracle else None
    reference_cx = oracle[6]["complexity"] - oracle[0]["complexity"] if 6 in oracle else None
    arms: dict[str, dict] = {}
    for (arm, rep), steps in sorted(by_lane.items()):
        totals = arms.setdefault(arm, {"step_attempts": 0, "failed": 0, "regression_events": 0,
                                       "regression_tests": 0, "high_churn": 0, "excess_churn": 0,
                                       "stale_refs": 0, "cost_usd": 0.0, "passing": 0, "harness_failed": 0,
                                       "duplication_growth": [], "complexity_growth": [], "steps": [],
                                       "flagged_bash": 0})
        previous = None
        failed_before = False
        for k in sorted(steps):
            record = steps[k]
            junit = parse_junit(out / "junit" / f"{record['label']}.xml") \
                if (out / "junit" / f"{record['label']}.xml").exists() else None
            cost = sum(s.get("cost_usd") or 0 for s in record["sessions"])
            totals["cost_usd"] += cost
            totals["flagged_bash"] += sum(len(s.get("flagged_bash", [])) for s in record["sessions"])
            if k == 0:
                previous = junit
                continue
            passed = not record["harness_failed"] and step_passes(junit, record["hidden"])
            regressed = regressions(previous, junit, record["hidden"])
            excess = record["churn"] - oracle[k]["churn"]
            high = excess >= max(10, oracle[k]["churn"])
            stale = len([f for f in record["lint"] if "error" not in f])
            totals["step_attempts"] += 1
            totals["passing"] += passed
            totals["failed"] += not passed
            totals["harness_failed"] += record["harness_failed"]
            totals["regression_events"] += bool(regressed)
            totals["regression_tests"] += len(regressed)
            totals["high_churn"] += high
            totals["excess_churn"] += excess
            totals["stale_refs"] += stale
            totals["steps"].append({"rep": rep, "step": k, "pass": passed, "regressions": len(regressed),
                                    "regressed_sample": regressed[:5], "excess_churn": excess, "high_churn": high,
                                    "churn": record["churn"], "stale_refs": stale,
                                    "after_earlier_failure": failed_before and not passed,
                                    "cost_usd": round(cost, 4), "harness_failed": record["harness_failed"],
                                    "unparsable": record["unparsable"]})
            failed_before = failed_before or not passed
            previous = junit
        if 0 in steps and 6 in steps:
            totals["duplication_growth"].append(steps[6]["duplication"] - steps[0]["duplication"])
            totals["complexity_growth"].append(steps[6]["complexity"] - steps[0]["complexity"])
    for totals in arms.values():
        totals["E"] = totals["failed"] + totals["regression_events"] + totals["high_churn"]
        totals["cost_per_passing_step"] = round(totals["cost_usd"] / totals["passing"], 4) if totals["passing"] else None
        totals["cost_usd"] = round(totals["cost_usd"], 4)
    return {"reference": {"duplication_growth": reference_dup, "complexity_growth": reference_cx,
                          "pr_churn": {k: oracle[k]["churn"] for k in oracle if k}},
            "arms": arms, "decision": decide(arms), "self_test": self_test(arms, reference_dup, reference_cx)}


def decide(arms: dict) -> dict:
    """The pre-registered decision rules, applied to whichever arms are present."""
    E = {arm: t["E"] for arm, t in arms.items()}
    if not all(a in arms for a in LIVE_ARMS):
        return {"complete": False, "E": E}
    hp, sp, hi, hs, hr = (arms[a] for a in ("haiku-plain", "sonnet-plain", "haiku-instruct", "haiku-skill",
                                              "haiku-review"))
    gap = hp["E"] - sp["E"]
    rule1 = gap <= 2 and all(hp[c] - sp[c] <= 1 for c in ("failed", "regression_events", "high_churn"))
    rule2 = hs["E"] <= hi["E"] - 3 and any(
        hi[c] >= 2 and hs[c] <= hi[c] / 2 for c in ("high_churn", "regression_events"))
    review_cost, sonnet_cost = hr["cost_per_passing_step"], sp["cost_per_passing_step"]
    rule3 = (gap >= 3 and hr["E"] <= sp["E"] + gap / 2 and review_cost is not None and sonnet_cost is not None
             and review_cost < 0.6 * sonnet_cost)
    outcome = ("1: Haiku within noise of Sonnet" if rule1 else "2: comments beat instruction-only" if rule2
               else "3: review closes the gap cheaply" if rule3 else "4: hygiene skill only")
    return {"complete": True, "E": E, "gap": gap, "rule1": rule1, "rule2": rule2, "rule3": rule3,
            "outcome": outcome, "stop_comments_research": hs["E"] >= hi["E"] - 1}


def self_test(arms: dict, reference_dup: int | None, reference_cx: int | None) -> dict:
    checks = {}
    if "oracle" in arms:
        o = arms["oracle"]
        checks["oracle_passes_every_step"] = o["failed"] == 0 and o["step_attempts"] > 0
        checks["oracle_no_regressions"] = o["regression_tests"] == 0
        checks["oracle_zero_excess_churn"] = all(s["excess_churn"] == 0 for s in o["steps"])
        checks["oracle_duplication_matches"] = all(g == reference_dup for g in o["duplication_growth"])
        checks["oracle_complexity_matches"] = all(g == reference_cx for g in o["complexity_growth"])
    if "null" in arms:
        n = arms["null"]
        checks["null_fails_steps"] = [s["step"] for s in n["steps"] if not s["pass"]]
        checks["null_zero_churn"] = all(s["churn"] == 0 for s in n["steps"])
        checks["null_no_regressions"] = n["regression_tests"] == 0
    return checks


def cleanup(out: Path) -> None:
    run_id = json.loads((Path(out) / "run.json").read_text(encoding="utf-8"))["run_id"]
    names = subprocess.run(["docker", "volume", "ls", "-q", "--filter", f"name=ccpilot-{run_id}-"],
                           capture_output=True, text=True, check=True).stdout.split()
    if names:
        subprocess.run(["docker", "volume", "rm", *names], check=True, capture_output=True)
    print(f"removed {len(names)} volumes")


def parse_steps(text: str) -> list[int]:
    if "-" in text:
        low, high = (int(part) for part in text.split("-"))
        return list(range(low, high + 1))
    return [int(part) for part in text.split(",")]


def load_credential_file(path: Path, name: str) -> str:
    """Read NAME=value from an env file, without the value ever reaching a log or an error.

    The runner loads the token itself so an agent driving it never has to read the file.
    """
    try:
        lines = path.read_text(encoding="utf-8-sig").splitlines()  # -sig: tolerate a PowerShell BOM
    except OSError as error:
        raise ValueError(f"cannot read credential file {path}: {error.strerror}") from None
    for line in lines:
        key, sep, value = line.strip().partition("=")
        if sep and key.strip() == name:
            value = value.strip().strip('"').strip("'")
            if not value:
                raise ValueError(f"{name} is empty in {path}")
            return value
    raise ValueError(f"{name} is not set in {path}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Narwhals long-horizon pilot runner (#41).")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("run")
    p.add_argument("--out", required=True)
    p.add_argument("--arms", required=True, type=lambda s: s.split(","))
    p.add_argument("--reps", type=int, default=1)
    p.add_argument("--steps", type=parse_steps, default=list(range(1, 7)))
    p.add_argument("--jobs", type=int, default=2)
    p.add_argument("--live", action="store_true", help="run real model sessions (SPENDS MONEY)")
    p.add_argument("--credential", choices=sorted(CREDENTIALS))
    p.add_argument("--credential-file", type=Path,
                   help="env file holding the credential; the runner reads it so no agent has to")
    p.add_argument("--cap", type=float, help="total USD cap for this run (needs the user's approval)")
    p.add_argument("--max-budget", type=float, default=2.0, help="per-session --max-budget-usd")
    p.add_argument("--timeout", type=float, default=1800, help="per-session timeout in seconds")
    p = sub.add_parser("summary")
    p.add_argument("--out", required=True)
    p = sub.add_parser("cleanup")
    p.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    if args.command == "summary":
        print(json.dumps(summarise(Path(args.out)), indent=2))
        return
    if args.command == "cleanup":
        cleanup(Path(args.out))
        return
    unknown = [a for a in args.arms if a not in ARMS]
    if unknown:
        parser.error(f"unknown arms {unknown}; choose from {sorted(ARMS)}")
    if args.live:
        if not args.credential or args.cap is None:
            parser.error("--live needs --credential and --cap")
        if args.credential_file:
            name = CREDENTIALS[args.credential]
            try:
                # Only the session containers get it, via `-e NAME`; scoring containers never do.
                os.environ[name] = load_credential_file(args.credential_file, name)
            except ValueError as error:
                parser.error(str(error))
            print(f"loaded {name} from {args.credential_file} ({len(os.environ[name])} characters)",
                  file=sys.stderr)
        if not os.environ.get(CREDENTIALS[args.credential]):
            parser.error(f"{CREDENTIALS[args.credential]} is not set in this shell")
        if args.max_budget > args.cap:
            parser.error("--max-budget is larger than --cap")
    Runner(args).run()


if __name__ == "__main__":
    main()
