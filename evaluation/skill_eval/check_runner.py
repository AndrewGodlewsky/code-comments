"""Run one case's hidden checks against a workspace in a separate `python -I` process.

Usage: python -I check_runner.py <checks.py> <workspace>, with SKILL_EVAL_TOKEN set.
Prints `<token> started` before any workspace code runs, then `<token> <JSON failures>`.
The grader treats a missing start line as a broken checker, and a start line without
a result as a candidate failure (the workspace code killed or hijacked the process).
The token makes it harder for workspace code to forge a passing result; this is
process separation, not a security sandbox (see docs/evaluation/skill-evals.md).
"""

import importlib
import json
import os
from pathlib import Path
import runpy
import sys


def _describe(error: BaseException) -> str:
    return f"{type(error).__name__}: {error}"


def load(module: str, failures: list[str]):
    """Import a workspace module; record a failure instead of raising."""
    try:
        return importlib.import_module(module)
    except KeyboardInterrupt:
        raise
    except BaseException as error:
        failures.append(f"load {module}: {_describe(error)}")
        return None


def expect(failures: list[str], label: str, call, expected) -> None:
    try:
        actual = call()
    except KeyboardInterrupt:
        raise
    except BaseException as error:
        failures.append(f"{label}: expected {expected!r}, raised {_describe(error)}")
        return
    if type(actual) is not type(expected) or actual != expected:
        failures.append(f"{label}: expected {expected!r}, got {actual!r}")


def expect_raises(failures: list[str], label: str, call, error_type: type[BaseException]) -> None:
    try:
        actual = call()
    except error_type:
        return
    except KeyboardInterrupt:
        raise
    except BaseException as error:
        failures.append(f"{label}: expected {error_type.__name__}, raised {type(error).__name__}")
        return
    failures.append(f"{label}: expected {error_type.__name__}, got {actual!r}")


def main() -> None:
    token = os.environ.pop("SKILL_EVAL_TOKEN")
    checks, workspace = Path(sys.argv[1]), Path(sys.argv[2])
    write = sys.stdout.write
    helpers = {"load": load, "expect": expect, "expect_raises": expect_raises}
    check = runpy.run_path(str(checks), init_globals=helpers)["check"]
    sys.path.insert(0, str(workspace))
    sys.dont_write_bytecode = True
    write(f"{token} started\n")
    sys.stdout.flush()
    try:
        failures = check()
    except KeyboardInterrupt:
        raise
    except BaseException as error:
        # The checks passed against the reference (selftest), so an escape here is
        # caused by the candidate workspace: a renamed API, an exit on import, etc.
        failures = [f"checks aborted by workspace code: {_describe(error)}"]
    write(f"{token} {json.dumps(failures)}\n")
    sys.stdout.flush()


if __name__ == "__main__":
    main()
