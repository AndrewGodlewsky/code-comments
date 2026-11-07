"""Programmatic grader for one `comment-edit` case end state."""

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
import tokenize

from .comments import Block, blocks, code_fingerprint, normalize, scopes


CASES = Path(__file__).resolve().parent / "cases"
CHECK_RUNNER = Path(__file__).resolve().parent / "check_runner.py"
FAMILIES = ("capture", "maintain", "restrain", "audit")
METRICS = ("pass", "behavior", "recall", "misplaced", "bad_claims", "preserved", "noise_lines")
LINES_PER_FACT = 4


class GraderError(Exception):
    """The grader or a hidden check broke; this is never a model failure."""


@dataclass(frozen=True)
class Case:
    root: Path
    spec: dict

    @property
    def id(self) -> str:
        return self.spec["id"]

    @property
    def family(self) -> str:
        return self.spec["family"]

    @property
    def visible(self) -> Path:
        return self.root / "visible"

    @property
    def private(self) -> Path:
        return self.root / "private"

    @property
    def task(self) -> str:
        return (self.visible / "TASK.md").read_text(encoding="utf-8")


def load_cases(root: Path = CASES, problems: list[str] | None = None) -> list[Case]:
    """Load every case. With `problems`, record invalid cases there instead of raising."""
    cases = []
    for spec_path in sorted(root.glob("*/private/case.json")):
        try:
            spec = json.loads(spec_path.read_text(encoding="utf-8"))
            case = Case(spec_path.parents[1], spec)
            if case.id != case.root.name:
                raise ValueError(f"id {case.id!r} must match directory name")
            if case.family not in FAMILIES:
                raise ValueError(f"unknown family {case.family!r}")
            # A heredoc that eats backslashes turns "\\b" into a backspace: valid JSON, dead regex.
            if any(ord(ch) < 32 for ch in json.dumps(spec, ensure_ascii=False) if ch not in "\n\t"):
                raise ValueError("control character in case.json (a lost backslash escape?)")
        except (ValueError, KeyError) as error:
            if problems is None:
                raise ValueError(f"{spec_path}: {error}") from error
            problems.append(f"{spec_path.parents[1].name}: invalid case.json: {error}")
            continue
        cases.append(case)
    return cases


def matches(anchor_groups: list[list[str]], text: str) -> bool:
    """Every group must match one alternative; 're:' alternatives are regular expressions."""
    def hit(alternative: str) -> bool:
        if alternative.startswith("re:"):
            return re.search(alternative[3:], text) is not None
        return normalize(alternative) in text
    return all(any(hit(alternative) for alternative in group) for group in anchor_groups)


def _owner(owner: str) -> tuple[str, str | None]:
    path, _, scope = owner.partition(":")
    return path, scope or None


def _read(workspace: Path, relative: str) -> str | None:
    path = workspace / relative
    return path.read_text(encoding="utf-8") if path.is_file() else None


def _read_candidate(workspace: Path, relative: str, failures: list[str]) -> str | None:
    """Candidate output is untrusted: an unreadable file is a model failure, not a crash."""
    try:
        source = _read(workspace, relative)
    except (UnicodeDecodeError, OSError) as error:
        failures.append(f"{relative}: unreadable: {type(error).__name__}")
        return None
    if source is None:
        failures.append(f"{relative}: missing")
    return source


def run_checks(case: Case, workspace: Path, timeout_s: float = 30.0) -> list[str]:
    """Hidden-check failures. GraderError only when the checker itself could not start."""
    token = secrets.token_hex(16)
    try:
        completed = subprocess.run(
            [sys.executable, "-I", str(CHECK_RUNNER), str(case.private / "checks.py"), str(workspace)],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout_s,
            cwd=workspace, env={**os.environ, "SKILL_EVAL_TOKEN": token},
        )
    except subprocess.TimeoutExpired:
        return [f"hidden checks exceeded {timeout_s}s"]
    ours = [line[len(token) + 1:] for line in completed.stdout.splitlines() if line.startswith(token + " ")]
    if "started" not in ours:
        raise GraderError(f"{case.id}: check runner did not start (exit {completed.returncode}): {completed.stderr.strip()[-500:]}")
    results = [line for line in ours if line != "started"]
    if not results:
        return [f"workspace code ended the check process before results (exit {completed.returncode})"]
    try:
        return json.loads(results[-1])
    except json.JSONDecodeError as error:
        raise GraderError(f"{case.id}: unreadable check result: {results[-1][:500]!r}") from error


def grade(case: Case, workspace: Path) -> tuple[dict, dict]:
    """Return (grade dict over METRICS, explanation dict) for the workspace end state."""
    spec = case.spec
    files = spec["files"]
    failures: list[str] = []
    finals: dict[str, str | None] = {name: _read_candidate(workspace, name, failures) for name in files}
    initials: dict[str, str | None] = {name: _read(case.visible, name) for name in files}
    parsed: dict[str, list[Block]] = {}
    spans: dict[str, dict[str, tuple[int, int]]] = {}
    for name, source in finals.items():
        if source is None:
            continue
        try:
            parsed[name], spans[name] = blocks(source), scopes(source)
        except (SyntaxError, ValueError, tokenize.TokenError, IndexError, RecursionError) as error:
            failures.append(f"{name}: does not parse: {type(error).__name__}: {error}")

    if spec["behavior"] == "checks":
        failures += run_checks(case, workspace)
    elif spec["behavior"] == "ast_unchanged":
        for name in parsed:
            if initials[name] is not None and code_fingerprint(finals[name]) != code_fingerprint(initials[name]):
                failures.append(f"{name}: code changed during a comment-only request")
    else:
        raise ValueError(f"{case.id}: unknown behavior mode {spec['behavior']!r}")

    found, missing, misplaced = [], [], []
    for fact in spec.get("required_facts", []):
        # `owner` may list several acceptable homes (e.g. a method or its class).
        owners = fact["owner"] if isinstance(fact["owner"], list) else [fact["owner"]]
        in_scope = []
        for owner in owners:
            path, scope = _owner(owner)
            span = spans.get(path, {}).get(scope) if scope else None
            if scope and span is None:
                continue
            in_scope += [
                block for block in parsed.get(path, [])
                if matches(fact["anchors"], block.text) and (span is None or (block.start <= span[1] and block.end >= span[0]))
            ]
        if in_scope:
            found.append(fact["id"])
        elif any(matches(fact["anchors"], block.text) for other in parsed.values() for block in other):
            misplaced.append(fact["id"])
        else:
            missing.append(fact["id"])

    bad = [
        claim["id"] for claim in spec.get("forbidden_claims", [])
        if any(matches(claim["anchors"], block.text) for file_blocks in parsed.values() for block in file_blocks)
    ]

    lost = []
    for item in spec.get("protected_comments", []):
        text = " ".join(block.text for block in parsed.get(item["file"], []))
        if normalize(item["text"]) not in text:
            lost.append(item["text"])

    noise = 0
    initial_lines: dict[str, int] = {}
    stale_lines: dict[str, int] = {}
    claims = spec.get("forbidden_claims", [])
    for name, source in initials.items():
        if source is None:
            continue
        for block in blocks(source):
            is_stale = any(matches(claim["anchors"], block.text) for claim in claims)
            for line in block.lines:
                initial_lines[normalize(line)] = initial_lines.get(normalize(line), 0) + 1
                if is_stale:
                    stale_lines[normalize(line)] = stale_lines.get(normalize(line), 0) + 1
    for file_blocks in parsed.values():
        for block in file_blocks:
            # Adjacent comment lines merge into one block, so cap how many new lines a fact
            # can excuse; otherwise padding attached to a real explanation would be free.
            excused = LINES_PER_FACT * sum(matches(fact["anchors"], block.text) for fact in spec.get("required_facts", []))
            for line in block.lines:
                key = normalize(line)
                if initial_lines.get(key):
                    initial_lines[key] -= 1
                elif excused > 0:
                    excused -= 1
                elif key:
                    noise += 1
    # Each removed stale line pays for one replacement line, so correcting a false
    # comment in place costs no more than deleting it (otherwise climbing learns to delete).
    removed_stale = sum(min(initial_lines.get(key, 0), count) for key, count in stale_lines.items())
    noise = max(0, noise - removed_stale)

    required =len(spec.get("required_facts", []))
    protected = len(spec.get("protected_comments", []))
    result = {
        "behavior": int(not failures),
        "recall": round(len(found) / required, 4) if required else 1.0,
        "misplaced": len(misplaced),
        "bad_claims": len(bad),
        "preserved": round((protected - len(lost)) / protected, 4) if protected else 1.0,
        "noise_lines": noise,
    }
    result["pass"] = int(
        result["behavior"] == 1 and result["recall"] == 1.0 and not bad and not lost and noise <= spec["noise_budget"]
    )
    explanation = {
        "behavior": "; ".join(failures[:8]) or "ok",
        "recall": f"found {found}; misplaced {misplaced}; missing {missing}",
        "bad_claims": f"present: {bad}" if bad else "none",
        "preserved": f"lost: {lost}" if lost else "all kept",
        "noise_lines": f"{noise} unexplained added lines (budget {spec['noise_budget']})",
    }
    return {metric: result[metric] for metric in METRICS}, explanation
