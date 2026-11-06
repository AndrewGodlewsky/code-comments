"""Validate admission declarations without downloading or executing candidates."""

import argparse
from datetime import date
import json
from pathlib import Path
import re
from urllib.parse import urlsplit


REGISTRY = Path(__file__).with_name("corpus-candidates.json")
GATES = frozenset({
    "rights", "environment", "cumulative_regressions", "fact_provenance",
    "equivalent_navigation", "hidden_checks", "known_good_and_mutants",
    "leakage_review", "independent_review",
})


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _hex(value, length):
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{%d}" % length, value) is not None


def _url(value):
    if not _text(value):
        return False
    try:
        parsed = urlsplit(value)
        return parsed.scheme == "https" and bool(parsed.hostname) and not parsed.username
    except ValueError:
        return False


def _strings(value):
    return isinstance(value, list) and bool(value) and all(_text(x) for x in value)


def validate_registry(data: object) -> list[str]:
    """Return mechanical errors; an empty list does not certify evidence or readiness."""
    if not isinstance(data, dict):
        return ["registry must be an object"]
    errors = []
    if type(data.get("schema_version")) is not int or data["schema_version"] != 1:
        errors.append("schema_version must be 1")
    if not _text(data.get("selection_policy")):
        errors.append("selection_policy is required")
    candidates = data.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        return errors + ["candidates must be a nonempty list"]

    ids, tasks, solutions = set(), set(), set()
    repository_splits = {}
    for index, c in enumerate(candidates):
        prefix = f"candidates[{index}]"

        def fail(message):
            errors.append(f"{prefix}: {message}")

        if not isinstance(c, dict):
            fail("candidate must be an object")
            continue
        for key in ("id", "benchmark"):
            if not _text(c.get(key)):
                fail(f"{key} is required")
        identity = c.get("id")
        if _text(identity):
            if identity != identity.strip():
                fail("candidate id must not have surrounding whitespace")
            if identity in ids:
                fail("duplicate candidate id")
            ids.add(identity)
        repository = c.get("repository")
        valid_repo = isinstance(repository, str) and re.fullmatch(r"[\w.-]+/[\w.-]+", repository)
        if not valid_repo:
            fail("repository must be owner/name")
        split = c.get("split")
        if split not in ("development", "pilot", "held_out"):
            fail("invalid split")
        elif valid_repo:
            repo_key = repository.casefold()
            if repo_key in repository_splits and repository_splits[repo_key] != split:
                fail("repository split leakage")
            repository_splits[repo_key] = split
        task_ids = c.get("task_ids")
        if not _strings(task_ids):
            fail("task_ids must be nonempty strings")
        elif valid_repo:
            for task in task_ids:
                if task != task.strip():
                    fail("task id must not have surrounding whitespace")
                key = (repository.casefold(), task)
                if key in tasks:
                    fail(f"duplicate task: {task}")
                tasks.add(key)
        if "steps" in c:
            steps = c["steps"]
            if not isinstance(steps, list) or not steps or not all(isinstance(s, dict) for s in steps):
                fail("steps must be nonempty objects")
            else:
                if [s.get("task_id") for s in steps] != task_ids:
                    fail("steps must match task_ids in order")
                for step in steps:
                    if not _hex(step.get("base_revision"), 40):
                        fail("step base_revision must be a full commit SHA")
                    if not _text(step.get("test_command")):
                        fail("step test_command is required")
                    for key in ("fail_to_pass_count", "pass_to_pass_count"):
                        if type(step.get(key)) is not int or step[key] < 0:
                            fail(f"step {key} must be a nonnegative integer")
        solution = c.get("solution_sha256")
        if solution is not None:
            if not _hex(solution, 64):
                fail("invalid solution_sha256")
            elif solution in solutions:
                fail("duplicate solution hash")
            else:
                solutions.add(solution)

        upstream = c.get("upstream")
        if not isinstance(upstream, dict):
            fail("upstream provenance is required")
        else:
            revision, url = upstream.get("revision"), upstream.get("artifact_url")
            if not _text(upstream.get("repository")):
                fail("upstream repository is required")
            if not _hex(revision, 40):
                fail("upstream revision must be a full commit SHA")
            if not _url(url) or (_hex(revision, 40) and revision not in urlsplit(url).path.split("/")):
                fail("artifact_url must be HTTPS and pinned to upstream revision")
            if not _hex(upstream.get("sha256"), 64):
                fail("artifact sha256 is required")
        if not _hex(c.get("base_revision"), 40):
            fail("base_revision must be a full commit SHA")

        selection = c.get("selection")
        if not isinstance(selection, dict):
            fail("selection record is required")
        else:
            if selection.get("before_outcomes") is not True:
                fail("selection must be recorded before outcomes")
            if not _text(selection.get("rationale")):
                fail("selection rationale is required")
            try:
                date.fromisoformat(selection.get("recorded_on", ""))
            except (TypeError, ValueError):
                fail("selection recorded_on must be an ISO date")
        rights = c.get("rights")
        if not isinstance(rights, dict):
            fail("rights provenance is required")
        else:
            for key in ("declaration", "notes"):
                if not _text(rights.get(key)):
                    fail(f"rights {key} is required")
            evidence = rights.get("evidence_urls")
            if not _strings(evidence) or not all(_url(x) for x in evidence):
                fail("rights evidence_urls must be nonempty HTTPS URLs")

        status = c.get("status")
        if status not in ("pending", "excluded", "admitted"):
            fail("invalid admission status")
        if status in ("pending", "excluded") and not _strings(c.get("pending_reasons")):
            fail("pending/excluded candidates need reasons")
        gates = c.get("gates")
        if not isinstance(gates, dict) or set(gates) != GATES:
            fail("gates must contain exactly the required admission gates")
            gates = {}
        verified = set()
        for name, gate in gates.items():
            if not isinstance(gate, dict) or gate.get("status") not in ("pending", "verified", "failed"):
                fail(f"invalid gate: {name}")
                continue
            evidence = gate.get("evidence")
            if not isinstance(evidence, list) or not all(_url(x) for x in evidence):
                fail(f"{name} evidence must be HTTPS URLs")
            elif gate["status"] == "verified":
                if not evidence:
                    fail(f"verified {name} requires evidence")
                else:
                    verified.add(name)
        if status == "admitted" and verified != GATES:
            fail("admitted requires every gate verified with evidence")
        environment = c.get("environment")
        if not isinstance(environment, dict):
            fail("environment record is required")
        else:
            if not _text(environment.get("declared")) or type(environment.get("execution_verified")) is not bool:
                fail("environment needs declaration and boolean execution_verified")
            digest = environment.get("image_digest")
            pinned = isinstance(digest, str) and digest.startswith("sha256:") and _hex(digest[7:], 64)
            if digest is not None and not pinned:
                fail("image_digest must be an immutable SHA-256 digest or null")
            if "environment" in verified and (not pinned or environment.get("execution_verified") is not True):
                fail("verified environment requires executed checks and immutable image digest")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("registry", type=Path, nargs="?", default=REGISTRY)
    args = parser.parse_args()
    data = None
    try:
        data = json.loads(args.registry.read_text(encoding="utf-8"))
        errors = validate_registry(data)
    except (OSError, UnicodeError, ValueError) as exc:
        errors = [f"cannot read registry: {exc}"]
    candidates = data.get("candidates", []) if isinstance(data, dict) else []
    if not isinstance(candidates, list):
        candidates = []
    counts = {status: sum(isinstance(c, dict) and c.get("status") == status for c in candidates)
              for status in ("pending", "excluded", "admitted")}
    # Corpus-level adequacy and independent review are outside schema validation.
    print(json.dumps({"valid": not errors, "errors": errors, **counts,
                      "pilot_ready": False, "model_calls": 0}, indent=2))
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
