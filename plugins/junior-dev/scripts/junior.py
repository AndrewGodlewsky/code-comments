"""Junior-dev loop helper: keeps the loop's state and runs each junior turn in isolation.

The main agent never talks to the junior directly. It calls this script, which hands the
junior exactly two things, the artifact's current text and this loop's questions and
answers, through an isolated `claude -p` session (no tools, no plugins, no CLAUDE.md, an
empty working directory). The spike behind those flags is docs/junior-dev/spike-2026-11-12.md.

    python junior.py start <artifact> [--rounds 6] [--model sonnet] [--state-root DIR]
    python junior.py ask <state>                 # next batch of questions
    python junior.py answer <state> <answers.md> # "Q<id> [checked|decided|unknown]: ..." lines
    python junior.py teachback <state>           # a fresh junior explains the artifact back
    python junior.py verdict <state> correct|wrong [--notes FILE]
    python junior.py report <state>              # what changed, and the holes

Standard library only, so it runs wherever the plugin is installed (Python 3.10+).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
REFERENCES = HERE.parent / "skills" / "junior-dev" / "references"
JUNIOR_PROMPT = REFERENCES / "junior-prompt.md"
TEACHBACK_PROMPT = REFERENCES / "teachback-prompt.md"
TURN_BUDGET_USD = 0.25
TIMEOUT_S = 300.0

QUESTIONS_SCHEMA = {
    "type": "object",
    "properties": {
        "questions": {"type": "array", "items": {
            "type": "object",
            "properties": {"id": {"type": "string"}, "text": {"type": "string"}, "about": {"type": "string"}},
            "required": ["id", "text", "about"]}},
        "done": {"type": "boolean"},
    },
    "required": ["questions", "done"],
}
TEACHBACK_SCHEMA = {
    "type": "object",
    "properties": {"explanation": {"type": "string"}, "gaps": {"type": "array", "items": {"type": "string"}}},
    "required": ["explanation", "gaps"],
}

# The fixed framing around the artifact. The tournament embeds these constants and renders
# messages the same way, so the eval tests the text that ships (see the plan's pre-flight ruling).
ARTIFACT_HEADER = "# The document\n\n"
TRANSCRIPT_HEADER = "\n# Your earlier questions and the author's answers\n\n"
ASK_INSTRUCTION = ("\n# Your turn\n\nAsk your next batch of questions about what you do not yet understand. "
                   "If nothing you would need in order to explain how this works is still unclear, "
                   "return no questions and set done to true.\n")
TEACHBACK_HEADER = "# The document\n\n"
TEACHBACK_INSTRUCTION = ("\n# Your turn\n\nExplain how this works, step by step, in your own words, using only "
                         "the document. List anything you could not explain as gaps.\n")

ANSWER_LINE = re.compile(r"^\s*Q(\d+)\s*\[(checked|decided|unknown)\]\s*:\s*(.*)$", re.IGNORECASE)
CHANGED_LINE = re.compile(r"^\s*Changed\s*:\s*(.*)$", re.IGNORECASE)


class JuniorError(Exception):
    """A loop step that cannot proceed; the state on disk is left unchanged."""


def render_transcript(transcript: list[dict]) -> str:
    parts = []
    for rnd in transcript:
        answers = {a["id"]: a for a in rnd.get("answers", [])}
        lines = [f"## Round {rnd['round']}", ""]
        for q in rnd["questions"]:
            lines.append(f"Q{q['id']} (about: {q['about']}): {q['text']}")
            a = answers.get(q["id"])
            lines.append(f"A{q['id']} [{a['tag']}]: {a['text']}" if a else f"A{q['id']}: (no answer)")
            lines.append("")
        parts.append("\n".join(lines))
    return "\n".join(parts)


def build_junior_message(artifact: str, transcript: list[dict]) -> str:
    message = ARTIFACT_HEADER + artifact.strip() + "\n"
    if transcript:
        message += TRANSCRIPT_HEADER + render_transcript(transcript)
    return message + ASK_INSTRUCTION


def build_teachback_message(artifact: str) -> str:
    return TEACHBACK_HEADER + artifact.strip() + "\n" + TEACHBACK_INSTRUCTION


def _structured(raw: str) -> dict:
    """The parsed object from `claude -p --output-format json --json-schema` output."""
    try:
        outer = json.loads(raw)
    except (json.JSONDecodeError, TypeError) as e:
        raise JuniorError(f"junior output is not JSON: {str(raw)[:200]!r}") from e
    if not isinstance(outer, dict):
        raise JuniorError("junior output is not a JSON object")
    if outer.get("is_error"):
        raise JuniorError(f"junior session failed: {str(outer.get('result'))[:300]}")
    inner = outer.get("structured_output")
    if isinstance(inner, dict):
        return inner
    text = str(outer.get("result") or "").strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
    try:
        inner = json.loads(text)
    except json.JSONDecodeError as e:
        raise JuniorError("junior output has no structured result") from e
    if not isinstance(inner, dict):
        raise JuniorError("junior result is not a JSON object")
    return inner


def parse_questions(raw: str) -> tuple[list[dict], bool]:
    data = _structured(raw)
    questions, done = data.get("questions"), data.get("done")
    if not isinstance(questions, list) or not isinstance(done, bool):
        raise JuniorError("junior result lacks questions/done")
    out = []
    for q in questions:
        if not isinstance(q, dict) or not str(q.get("text", "")).strip():
            raise JuniorError("junior question without text")
        out.append({"text": str(q["text"]).strip(), "about": str(q.get("about", "")).strip() or "general"})
    return out, done


def parse_teachback(raw: str) -> tuple[str, list[str]]:
    data = _structured(raw)
    explanation = str(data.get("explanation", "")).strip()
    if not explanation:
        raise JuniorError("teach-back has no explanation")
    return explanation, [str(g) for g in data.get("gaps", []) if str(g).strip()]


def parse_answers(text: str) -> tuple[list[dict], list[str]]:
    answers, changes, current = [], [], None
    for line in text.splitlines():
        m, c = ANSWER_LINE.match(line), CHANGED_LINE.match(line)
        if m:
            current = {"id": m.group(1), "tag": m.group(2).lower(), "text": m.group(3).strip()}
            answers.append(current)
        elif c:
            changes.append(c.group(1).strip())
            current = None
        elif current is not None and line.strip():
            current["text"] = (current["text"] + " " + line.strip()).strip()
    return answers, changes


def junior_command(model: str, schema: dict, prompt_file: Path) -> list[str]:
    """argv for one isolated junior turn; the prompt itself goes on stdin, never here."""
    return ["claude", "-p", "--safe-mode", "--tools", "", "--system-prompt-file", str(prompt_file),
            "--model", model, "--output-format", "json", "--no-session-persistence",
            "--max-budget-usd", f"{TURN_BUDGET_USD:.2f}", "--json-schema", json.dumps(schema)]


def run_claude(argv: list[str], prompt: str, timeout_s: float = TIMEOUT_S) -> str:
    """Run one junior turn from an empty temporary directory, with the prompt on stdin."""
    env = dict(os.environ, JUNIOR_DEV_NESTED="1")
    with tempfile.TemporaryDirectory(prefix="junior-dev-") as empty:
        try:
            done = subprocess.run(argv, input=prompt, capture_output=True, text=True, encoding="utf-8",
                                  errors="replace", timeout=timeout_s, cwd=empty, env=env)
        except FileNotFoundError as e:
            raise JuniorError("the claude command was not found on PATH") from e
        except subprocess.TimeoutExpired as e:
            raise JuniorError(f"junior turn timed out after {timeout_s:.0f}s") from e
    if done.returncode != 0:
        raise JuniorError(f"claude exited {done.returncode}: {(done.stderr or done.stdout)[-400:]}")
    return done.stdout


def _cost(raw: str) -> float:
    """total_cost_usd reported by one claude -p call, or 0 when it is missing."""
    try:
        return float(json.loads(raw).get("total_cost_usd") or 0.0)
    except (json.JSONDecodeError, TypeError, ValueError, AttributeError):
        return 0.0


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


_hash = text_hash
REGISTRY = "registry.json"


def ensure_root(root: Path) -> Path:
    """The project's .junior-dev folder; it ignores itself so its scratch files are never committed."""
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    ignore = root / ".gitignore"
    if not ignore.exists():
        ignore.write_text("*\n", encoding="utf-8")
    return root


def load_registry(root: Path) -> dict:
    """Which plan and diagram files the hooks have seen: {absolute path: {status, hash, snapshot}}."""
    path = Path(root) / REGISTRY
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def mark(root: Path, artifact: Path, status: str, text: str | None = None) -> None:
    """Set an artifact's status (pending, reminded, reviewing, done); text records the reviewed version."""
    registry = load_registry(root)
    key = str(Path(artifact).resolve())
    entry = registry.get(key, {})
    entry["status"] = status
    if text is not None:
        entry["hash"], entry["snapshot"] = text_hash(text), text
    registry[key] = entry
    path = ensure_root(root) / REGISTRY
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(registry, indent=1, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)


def _slug(path: Path) -> str:
    return re.sub(r"[^a-z0-9]+", "-", path.stem.lower()).strip("-") or "artifact"


class JuniorSession:
    def __init__(self, state_dir: Path, runner=None):
        self.state_dir = Path(state_dir)
        self.runner = runner or run_claude
        path = self.state_dir / "state.json"
        if not path.is_file():
            raise JuniorError(f"no loop state at {self.state_dir}")
        self.state = json.loads(path.read_text(encoding="utf-8"))

    @classmethod
    def start(cls, artifact: Path, rounds: int = 6, model: str = "sonnet", state_root: Path | None = None,
              runner=None) -> "JuniorSession":
        artifact = Path(artifact).resolve()
        if not artifact.is_file():
            raise JuniorError(f"artifact not found: {artifact}")
        if rounds < 1:
            raise JuniorError("--rounds must be at least 1")
        text = artifact.read_text(encoding="utf-8")
        root = ensure_root(Path(state_root) if state_root else Path.cwd() / ".junior-dev")
        state_dir = root / f"{_slug(artifact)}-{_hash(str(artifact))[:8]}"
        state_dir.mkdir(parents=True, exist_ok=True)
        state = {"artifact": str(artifact), "artifact_hash": _hash(text), "model": model, "rounds_cap": rounds,
                 "round": 0, "phase": "asking", "transcript": [], "teachbacks": [], "changes": [], "holes": [],
                 "end_reason": None, "cost_usd": 0.0}
        session = cls.__new__(cls)
        session.state_dir, session.runner, session.state = state_dir, runner or run_claude, state
        session._save()
        mark(root, artifact, "reviewing")
        return session

    def _save(self) -> None:
        path = self.state_dir / "state.json"
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(self.state, indent=1, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, path)

    def _artifact_text(self) -> str:
        return Path(self.state["artifact"]).read_text(encoding="utf-8")

    def _call(self, argv: list[str], prompt: str, parse):
        """One junior call, retried once if its output cannot be parsed."""
        last = None
        for _ in range(2):
            raw = self.runner(argv, prompt)
            self.state["cost_usd"] = self.state.get("cost_usd", 0.0) + _cost(raw)
            try:
                return parse(raw)
            except JuniorError as e:
                last = e
        raise last

    def ask(self) -> str:
        s = self.state
        if s["phase"] == "done":
            return f"LOOP FINISHED ({s['end_reason']}): run report"
        if s["phase"] == "teachback":
            return "NO MORE QUESTIONS: run teachback"
        if s["transcript"] and not s["transcript"][-1].get("answers"):
            raise JuniorError(f"answer round {s['transcript'][-1]['round']} first")
        if s["round"] >= s["rounds_cap"]:
            s["phase"], s["end_reason"] = "done", "cap"
            self._save()
            return "ROUND CAP REACHED: run report"
        message = build_junior_message(self._artifact_text(), s["transcript"])
        argv = junior_command(s["model"], QUESTIONS_SCHEMA, JUNIOR_PROMPT)
        questions, done = self._call(argv, message, parse_questions)
        if not questions:
            s["phase"] = "teachback"
            self._save()
            return "NO MORE QUESTIONS: run teachback"
        next_id = 1 + sum(len(r["questions"]) for r in s["transcript"])
        numbered = [{"id": str(next_id + i), **q} for i, q in enumerate(questions)]
        s["round"] += 1
        s["transcript"].append({"round": s["round"], "questions": numbered, "answers": []})
        self._save()
        lines = [f"Round {s['round']} of at most {s['rounds_cap']}. Answer every question, then run ask again.", ""]
        lines += [f"Q{q['id']} (about: {q['about']}): {q['text']}" for q in numbered]
        return "\n".join(lines)

    def answer(self, text: str) -> str:
        s = self.state
        if not s["transcript"] or s["phase"] != "asking":
            raise JuniorError("there are no open questions to answer")
        rnd = s["transcript"][-1]
        answers, changes = parse_answers(text)
        asked = {q["id"]: q for q in rnd["questions"]}
        answers = [a for a in answers if a["id"] in asked]
        if not answers:
            raise JuniorError("no answer lines matched this round's questions; use 'Q<id> [checked|decided|unknown]: ...'")
        rnd["answers"] = answers
        s["changes"].extend(changes)
        for a in answers:
            if a["tag"] == "unknown":
                s["holes"].append(f"Q{a['id']}: {asked[a['id']]['text']} (author: {a['text']})")
        self._save()
        missing = sorted(set(asked) - {a["id"] for a in answers}, key=int)
        note = f" Unanswered: {', '.join('Q' + m for m in missing)}." if missing else ""
        return f"Recorded {len(answers)} answers and {len(changes)} changes.{note}"

    def teachback(self) -> str:
        s = self.state
        if s["phase"] != "teachback":
            raise JuniorError("the junior still has questions: run ask" if s["phase"] == "asking"
                              else f"the loop has finished ({s['end_reason']})")
        argv = junior_command(s["model"], TEACHBACK_SCHEMA, TEACHBACK_PROMPT)
        explanation, gaps = self._call(argv, build_teachback_message(self._artifact_text()), parse_teachback)
        s["teachbacks"].append({"text": explanation, "gaps": gaps, "verdict": None, "notes": ""})
        self._save()
        out = ["A fresh junior, reading only the artifact, explains it back:", "", explanation]
        if gaps:
            out += ["", "It could not explain:"] + [f"- {g}" for g in gaps]
        out += ["", "Compare this with what you intended, then run verdict correct or verdict wrong."]
        return "\n".join(out)

    def verdict(self, correct: bool, notes: str = "") -> str:
        s = self.state
        if not s["teachbacks"] or s["teachbacks"][-1]["verdict"] is not None:
            raise JuniorError("there is no teach-back waiting for a verdict")
        s["teachbacks"][-1].update(verdict="correct" if correct else "wrong", notes=notes.strip())
        if correct:
            s["phase"], s["end_reason"] = "done", "teachback-correct"
        elif s["round"] >= s["rounds_cap"]:
            s["phase"], s["end_reason"] = "done", "cap"
        else:
            s["phase"] = "asking"
        self._save()
        if correct:
            return "Teach-back correct. Run report."
        if s["phase"] == "done":
            return "Teach-back wrong and the round cap is reached. Fix the artifact where it was misread, then run report."
        return "Teach-back wrong. Fix the artifact where it was misread, then run ask."

    def report(self) -> str:
        s = self.state
        artifact = Path(s["artifact"])
        if artifact.is_file():
            mark(self.state_dir.parent, artifact, "done", artifact.read_text(encoding="utf-8"))
        reason = {"teachback-correct": "a fresh junior explained it back correctly",
                  "cap": "the round cap was reached", None: "the loop has not finished"}[s["end_reason"]]
        lines = [f"## Junior-dev review of {Path(s['artifact']).name}", "",
                 f"Rounds used: {s['round']} of {s['rounds_cap']}. Ended because {reason}. "
                 f"Junior cost: ${s.get('cost_usd', 0.0):.4f}.", "",
                 "### What changed"]
        lines += [f"- {c}" for c in s["changes"]] or ["- Nothing was changed."]
        lines += ["", "### Holes (questions the author could not answer, or is unsure about)"]
        lines += [f"- {h}" for h in s["holes"]] or ["- None."]
        return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(prog="junior.py", description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("start")
    p.add_argument("artifact")
    p.add_argument("--rounds", type=int, default=6)
    p.add_argument("--model", default="sonnet")
    p.add_argument("--state-root")
    for name in ("ask", "teachback", "report"):
        sub.add_parser(name).add_argument("state")
    p = sub.add_parser("answer")
    p.add_argument("state")
    p.add_argument("answers_file")
    p = sub.add_parser("verdict")
    p.add_argument("state")
    p.add_argument("result", choices=["correct", "wrong"])
    p.add_argument("--notes")
    args = parser.parse_args(argv)
    try:
        if args.command == "start":
            s = JuniorSession.start(Path(args.artifact), rounds=args.rounds, model=args.model,
                                    state_root=Path(args.state_root) if args.state_root else None,
                                    runner=run_claude)
            print(s.state_dir)
            return 0
        s = JuniorSession(Path(args.state), runner=run_claude)
        if args.command == "ask":
            print(s.ask())
        elif args.command == "answer":
            print(s.answer(Path(args.answers_file).read_text(encoding="utf-8")))
        elif args.command == "teachback":
            print(s.teachback())
        elif args.command == "verdict":
            notes = Path(args.notes).read_text(encoding="utf-8") if args.notes else ""
            print(s.verdict(args.result == "correct", notes))
        elif args.command == "report":
            print(s.report())
        return 0
    except JuniorError as e:
        print(f"junior-dev: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
