"""Audit a trusted development fixture and export its first task."""

import argparse
import json
from pathlib import Path
import runpy


FIXTURE = Path(__file__).resolve().parent / "fixtures" / "retry-policy"
CONDITIONS = ("baseline", "inline", "external")
GUIDE = "# Task workspace\n\nRead TASK.md, inspect policy.py, and consult context.md if present.\n"


def _facts_at_step(manifest: dict, step: int) -> list[dict]:
    return [
        fact for fact in manifest["facts"]
        if fact["available_from"] <= step
        and (fact["valid_until"] is None or step < fact["valid_until"])
    ]


def export_workspace(destination: Path, condition: str) -> None:
    if condition not in CONDITIONS:
        raise ValueError(f"condition must be one of {CONDITIONS}")
    manifest = json.loads((FIXTURE / "manifest.json").read_text(encoding="utf-8"))
    source = (FIXTURE / "initial" / "policy.py").read_text(encoding="utf-8")
    facts = _facts_at_step(manifest, 1)
    files = {
        "policy.py": source,
        "TASK.md": (FIXTURE / "private" / "step-1.md").read_text(encoding="utf-8"),
        "README.md": GUIDE,
    }
    if condition == "inline":
        files["policy.py"] = "".join(f"# {fact['text']}\n" for fact in facts) + source
    elif condition == "external":
        files["context.md"] = "# policy.py:resolve_retries\n\n" + "".join(f"- {fact['text']}\n" for fact in facts)
    # An allowlist keeps the public development answers out of exported inputs.
    destination.mkdir(parents=True, exist_ok=False)
    for name, text in files.items():
        with (destination / name).open("x", encoding="utf-8", newline="\n") as output:
            output.write(text)


def audit() -> dict:
    manifest = json.loads((FIXTURE / "manifest.json").read_text(encoding="utf-8"))
    check = runpy.run_path(str(FIXTURE / "private" / "checks.py"))["check"]
    paths = [FIXTURE / "initial" / "policy.py"] + [
        FIXTURE / "private" / "reference" / f"step-{step}.py" for step in (1, 2, 3)
    ]
    sources = [path.read_text(encoding="utf-8") for path in paths]
    references = []
    for step, source in enumerate(sources):
        failures = check(source, step)
        references.append({
            "step": step,
            "passed": not failures,
            "failures": failures,
            "fact_ids": [fact["id"] for fact in _facts_at_step(manifest, step)],
        })
    mutations = (
        ("zero_override_lost", 1, 'settings.get("retries") if override is None else override', 'override or settings.get("retries")'),
        ("stale_cap", 2, "<= 8", "<= 5"),
        ("prior_zero_regression", 2, "if retries is None:", "if not retries:"),
        ("extra_initial_delay", 3, "range(count)", "range(count + 1)"),
        ("uncapped_delay", 3, "min(2 ** index, 4)", "2 ** index"),
    )
    mutants = []
    for name, step, old, new in mutations:
        if sources[step].count(old) != 1:
            raise ValueError(f"mutation {name} no longer matches one reference expression")
        failures = check(sources[step].replace(old, new, 1), step)
        mutants.append({"name": name, "step": step, "rejected": bool(failures), "failures": failures})
    return {
        "kind": "offline_fixture_audit",
        "fixture_id": manifest["id"],
        "model_calls": 0,
        "passed": all(row["passed"] for row in references) and all(row["rejected"] for row in mutants),
        "references": references,
        "mutants": mutants,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("audit", help="check trusted fixture references and diagnostic mutants")
    export = commands.add_parser("export", help="export the first task; this does not isolate agent execution")
    export.add_argument("--condition", choices=CONDITIONS, required=True)
    export.add_argument("--destination", type=Path, required=True)
    arguments = parser.parse_args()
    try:
        if arguments.command == "audit":
            report = audit()
            print(json.dumps(report, indent=2))
            return 0 if report["passed"] else 1
        export_workspace(arguments.destination, arguments.condition)
        print(f"Exported {arguments.condition} first-task inputs to {arguments.destination}")
        return 0
    except (OSError, ValueError) as error:
        parser.exit(2, f"error: {error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
