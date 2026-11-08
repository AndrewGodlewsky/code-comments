"""Pilot scorer that runs inside the runtime container (#41). The host runner is pilot.py.

python -m evaluation.skill_eval.pilot_inner <command> [options]

It runs from the read-only harness mount (/harness) against one arm's narwhals tree
(/work/narwhals). Every command prints its result as JSON on the last stdout line.
Only the standard library is used, plus churn.normalized_lines and the stale-reference
lint, so nothing beyond the runtime image is needed.

Every git call disables hooks and fsmonitor, so a hook a model session plants in the
tree's .git cannot run while the tree is scored.
"""

import argparse
import ast
from collections import Counter
import difflib
import io
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tarfile
import time

from .churn import normalized_lines


HARNESS = Path(__file__).resolve().parents[2]
CHAIN = HARNESS / "evaluation" / "pilot" / "chain"
CONSTRUCTORS = CHAIN / "constructors.env"
LINT = HARNESS / "scripts" / "stale_refs.py"
TREE = Path("/work/narwhals")
ORACLE = Path("/oracle")
OUT = Path("/out")
SOURCE_PREFIX = "src/narwhals/"
HIDDEN_PREFIXES = ("tests/", "packages/test-plugin/")
STEPS = range(1, 7)
UID = 1000
PYTEST_TIMEOUT_S = 900
DUPLICATION_WINDOW = 6
GIT_SAFE = ["-c", "core.hooksPath=/dev/null", "-c", "core.fsmonitor=false"]
DIFF_HEADER = re.compile(r"^diff --git a/\S+ b/(\S+)$", re.MULTILINE)


# Pure functions (unit-tested on the host in tests/test_pilot.py).

def diff_paths(text: str) -> list[str]:
    """Paths a git diff touches (its b-side), in order, without repeats."""
    return list(dict.fromkeys(DIFF_HEADER.findall(text)))


def hidden_files(paths: list[str]) -> list[str]:
    """The paths that are hidden test support: the PR's tests, conftest and the test plugin."""
    return [p for p in paths if p.startswith(HIDDEN_PREFIXES)]


def chain_diffs() -> list[Path]:
    """The six step diffs, in order (file names start with the step number)."""
    diffs = sorted(CHAIN.glob("[1-6]-*.diff"))
    if [int(p.name.split("-")[0]) for p in diffs] != list(STEPS):
        raise SystemExit(f"expected six step diffs in {CHAIN}, found {[p.name for p in diffs]}")
    return diffs


def changed_lines(old: list[str], new: list[str]) -> int:
    return sum(1 for line in difflib.unified_diff(old, new, lineterm="")
               if line[:1] in "+-" and not line.startswith(("+++", "---")))


def churn_between(old: dict[str, str], new: dict[str, str]) -> tuple[int, list[str]]:
    """Normalised changed code lines between two {path: source} maps, and the paths that don't parse.

    A file that doesn't parse after the change is compared line by line instead.
    """
    total, unparsable = 0, []
    for path in sorted(set(old) | set(new)):
        before, after = old.get(path, ""), new.get(path, "")
        if before == after:
            continue
        old_lines, new_lines = normalized_lines(before), normalized_lines(after)
        if new_lines is None or old_lines is None:
            if new_lines is None:
                unparsable.append(path)
            total += changed_lines(before.splitlines(), after.splitlines())
        else:
            total += changed_lines(old_lines, new_lines)
    return total, unparsable


def duplication(sources: dict[str, str], window: int = DUPLICATION_WINDOW) -> int:
    """Repeated blocks of `window` consecutive normalised lines: the sum of (count - 1) over repeats."""
    counts: Counter = Counter()
    for path in sorted(sources):
        lines = normalized_lines(sources[path])
        if lines is None:
            continue
        lines = [line.strip() for line in lines]
        counts.update(tuple(lines[i:i + window]) for i in range(len(lines) - window + 1))
    return sum(n - 1 for n in counts.values() if n > 1)


_BRANCHES = (ast.If, ast.IfExp, ast.For, ast.AsyncFor, ast.While, ast.ExceptHandler, ast.match_case)


def _complexity(node: ast.AST, inside: bool) -> int:
    total = 0
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        total, inside = 1, True
    elif inside:
        if isinstance(node, _BRANCHES):
            total = 1
        elif isinstance(node, ast.comprehension):
            total = 1 + len(node.ifs)
        elif isinstance(node, ast.BoolOp):
            total = len(node.values) - 1
    return total + sum(_complexity(child, inside) for child in ast.iter_child_nodes(node))


def complexity(sources: dict[str, str]) -> int:
    """Total cyclomatic complexity: 1 per function plus its branches and extra boolean operands."""
    total = 0
    for text in sources.values():
        try:
            total += _complexity(ast.parse(text), False)
        except SyntaxError:
            continue
    return total


def read_constructors(path: Path = CONSTRUCTORS) -> str:
    match = re.search(r"^CONSTRUCTORS=(.+)$", path.read_text(encoding="utf-8"), re.MULTILINE)
    if not match:
        raise SystemExit(f"no CONSTRUCTORS= line in {path}")
    return shlex.split(match.group(1))[0]


def test_command(constructors: str) -> list[str]:
    return ["python", "-m", "pytest", "-q", "-p", "no:randomly", "-n", "8", f"--constructors={constructors}"]


# Container side.

def git(*args: str, cwd: Path = TREE, check: bool = True, text: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *GIT_SAFE, *args], cwd=cwd, check=check, capture_output=True, text=text)


def head(cwd: Path = TREE) -> str:
    return git("rev-parse", "HEAD", cwd=cwd).stdout.strip()


def archive(rev: str, *paths: str, cwd: Path = TREE) -> tarfile.TarFile:
    data = git("archive", "--format=tar", rev, "--", *paths, cwd=cwd, text=False).stdout
    return tarfile.open(fileobj=io.BytesIO(data))


def python_sources(rev: str, cwd: Path = TREE) -> dict[str, str]:
    """{path: text} for every .py file under src/narwhals/ at `rev`."""
    with archive(rev, SOURCE_PREFIX, cwd=cwd) as tar:
        return {m.name: tar.extractfile(m).read().decode("utf-8", errors="replace")
                for m in tar.getmembers() if m.isfile() and m.name.endswith(".py")}


def extract(rev: str, destination: Path, *paths: str, cwd: Path = TREE) -> None:
    with archive(rev, *paths, cwd=cwd) as tar:
        tar.extractall(destination, filter="data")


def clean_tree() -> None:
    git("clean", "-ffdqx")
    for cache in (".hypothesis", ".pytest_cache"):
        shutil.rmtree(TREE / cache, ignore_errors=True)


def reset(sha: str) -> None:
    git("reset", "-q", "--hard", sha)
    clean_tree()


def commit(message: str) -> str:
    git("add", "-A")
    git("commit", "-q", "--allow-empty", "--no-verify", "-m", message)
    return head()


def configure() -> None:
    git("config", "user.name", "pilot")
    git("config", "user.email", "pilot@localhost")
    git("config", "commit.gpgsign", "false")
    if "origin" in git("remote").stdout.split():
        git("remote", "remove", "origin")
    git("update-index", "-q", "--refresh", check=False)


def chown_tree() -> None:
    subprocess.run(["chown", "-R", f"{UID}:{UID}", str(TREE)], check=True)


def metrics_at(rev: str, cwd: Path = TREE) -> dict:
    sources = python_sources(rev, cwd)
    return {"duplication": duplication(sources), "complexity": complexity(sources)}


def emit(result: dict, name: str | None = None) -> None:
    if name:
        (OUT / name).write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result))


def cmd_init_oracle(args) -> None:
    configure()
    git("tag", "-f", "oracle-0")
    steps = [{"step": 0, "sha": head(), "hidden": [], **metrics_at("HEAD")}]
    for k, diff in enumerate(chain_diffs(), start=1):
        git("update-index", "-q", "--refresh", check=False)
        git("apply", "--index", str(diff))
        git("commit", "-q", "--no-verify", "-m", f"oracle step {k}: {diff.stem}")
        git("tag", "-f", f"oracle-{k}")
        churn, unparsable = churn_between(python_sources(f"oracle-{k - 1}"), python_sources(f"oracle-{k}"))
        steps.append({"step": k, "diff": diff.name, "sha": head(), "churn": churn, "unparsable": unparsable,
                      "hidden": hidden_files(diff_paths(diff.read_text(encoding="utf-8"))),
                      **metrics_at("HEAD")})
    chown_tree()
    emit({"steps": steps}, "oracle.json")


def cmd_init_arm(args) -> None:
    configure()
    status = git("status", "--porcelain", "--ignored").stdout.splitlines()
    chown_tree()
    emit({"start": head(), "status": status})


def cmd_reset(args) -> None:
    reset(args.pre)
    emit({"head": head()})


def cmd_implement(args) -> None:
    reset(args.pre)
    if args.mode == "oracle":
        diff = chain_diffs()[args.step - 1]
        excludes = [f"--exclude={prefix}*" for prefix in HIDDEN_PREFIXES]
        git("apply", *excludes, str(diff))
    emit({"mode": args.mode, "status": git("status", "--porcelain").stdout.splitlines()})


def cmd_diff(args) -> None:
    git("add", "-A")
    text = git("diff", "--cached", args.pre).stdout
    path = OUT / args.to
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    emit({"path": args.to, "chars": len(text)})


def lint_new(pre: str, sha: str) -> list[dict]:
    work = Path("/tmp/lint")
    shutil.rmtree(work, ignore_errors=True)
    extract(pre, work / "pre")
    extract(sha, work / "head")
    completed = subprocess.run([sys.executable, str(LINT), str(work / "head"), "--base-dir", str(work / "pre"),
                                "--only", SOURCE_PREFIX.rstrip("/"), "--json"], capture_output=True, text=True)
    shutil.rmtree(work, ignore_errors=True)
    if completed.returncode not in (0, 1):
        return [{"error": completed.stderr.strip()[-400:]}]
    return json.loads(completed.stdout or "[]")


def oracle_paths(tag: str, paths: list[str]) -> list[str]:
    """The subset of `paths` (files or directories) that exist at the oracle tag."""
    present = []
    for path in paths:
        if git("cat-file", "-e", f"{tag}:{path.rstrip('/')}", cwd=ORACLE, check=False).returncode == 0:
            present.append(path)
    return present


def cmd_score(args) -> None:
    started = time.perf_counter()
    k, label = args.step, args.label
    sha = commit(f"pilot {label}")
    churn, unparsable = churn_between(python_sources(args.pre), python_sources(sha))
    lint = lint_new(args.pre, sha)
    metrics = metrics_at(sha)
    diffs = OUT / "diffs"
    diffs.mkdir(parents=True, exist_ok=True)
    (diffs / f"{label}.diff").write_text(git("diff", args.pre, sha).stdout, encoding="utf-8")

    # Score against the oracle's tests at this step, whatever the session did to the tests.
    tag = f"oracle-{k}"
    for prefix in HIDDEN_PREFIXES:
        shutil.rmtree(TREE / prefix, ignore_errors=True)
    extract(tag, TREE, *oracle_paths(tag, [p.rstrip("/") for p in HIDDEN_PREFIXES]), cwd=ORACLE)
    junit = OUT / "junit" / f"{label}.xml"
    junit.parent.mkdir(parents=True, exist_ok=True)
    junit.unlink(missing_ok=True)
    command = test_command(read_constructors()) + ["-p", "no:cacheprovider", f"--junitxml={junit}",
                                                   "-o", "junit_family=xunit1"]
    try:
        completed = subprocess.run(command, cwd=TREE, capture_output=True, text=True, timeout=PYTEST_TIMEOUT_S)
        exit_code, output = completed.returncode, completed.stdout + completed.stderr
    except subprocess.TimeoutExpired as error:
        partial = error.stdout or ""  # TimeoutExpired carries bytes even when run with text=True
        if isinstance(partial, bytes):
            partial = partial.decode("utf-8", "replace")
        exit_code, output = "timeout", f"pytest exceeded {PYTEST_TIMEOUT_S}s\n{partial}"
    logs = OUT / "pytest"
    logs.mkdir(parents=True, exist_ok=True)
    (logs / f"{label}.txt").write_text(output[-20000:] if isinstance(output, str) else "", encoding="utf-8")

    # Keep the session's tree, plus this step's hidden files, for the next step.
    reset(sha)
    hidden = []
    if k:
        hidden = hidden_files(diff_paths(chain_diffs()[k - 1].read_text(encoding="utf-8")))
        for path in hidden:
            shown = git("show", f"{tag}:{path}", cwd=ORACLE, check=False, text=False)
            target = TREE / path
            if shown.returncode == 0:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(shown.stdout)
            else:
                target.unlink(missing_ok=True)
    after = commit(f"pilot {label} + hidden tests")
    emit({"step": k, "label": label, "pre": args.pre, "sha": sha, "after": after, "churn": churn,
          "unparsable": unparsable, "lint": lint, **metrics, "hidden": hidden, "pytest_exit": exit_code,
          "pytest_tail": output.strip().splitlines()[-1:] if isinstance(output, str) else [],
          "wall_s": round(time.perf_counter() - started, 1)})


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init-oracle").set_defaults(func=cmd_init_oracle)
    sub.add_parser("init-arm").set_defaults(func=cmd_init_arm)
    p = sub.add_parser("reset")
    p.add_argument("--pre", required=True)
    p.set_defaults(func=cmd_reset)
    p = sub.add_parser("implement")
    p.add_argument("--mode", choices=["oracle", "null"], required=True)
    p.add_argument("--step", type=int, required=True)
    p.add_argument("--pre", required=True)
    p.set_defaults(func=cmd_implement)
    p = sub.add_parser("diff")
    p.add_argument("--pre", required=True)
    p.add_argument("--to", required=True, help="path under /out")
    p.set_defaults(func=cmd_diff)
    p = sub.add_parser("score")
    p.add_argument("--step", type=int, required=True)
    p.add_argument("--pre", required=True)
    p.add_argument("--label", required=True)
    p.set_defaults(func=cmd_score)
    args = parser.parse_args(argv)
    os.environ.setdefault("GIT_TERMINAL_PROMPT", "0")
    args.func(args)


if __name__ == "__main__":
    main()
