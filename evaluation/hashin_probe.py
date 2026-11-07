"""Reproduce a bounded public Hashin reference audit, without downloads or models.

Requires the pinned ChainSWE parquet locally, PyArrow on the host, and the image
already pulled. This development probe is not a hidden grader or model runner.
"""

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import uuid
import xml.etree.ElementTree as ET


DATASET_SHA256 = "f7de0d66b64a9d5c28921fba2bbd51b5131dae8d5c789e03e61c09e67fc355fe"
IMAGE = ("swerebench/sweb.eval.x86_64.peterbe_1776_hashin-74@"
         "sha256:e9675431487c5b7f0bcf1a4ece9f4fbc671ade1404160e44ef2f57ff6ad5d053")
PYTHON = "/opt/miniconda3/envs/testbed/bin/python"


def summarize_tests(xml, required):
    """Map pytest JUnit cases to this candidate's module/class node IDs."""
    result = {key: [] for key in ("passed", "failed", "skipped")}
    for case in ET.fromstring(xml).iter("testcase"):
        parts = case.attrib["classname"].split(".")
        # This candidate has only tests/test_*.py modules and optional Tests class.
        module_end = next(i for i, part in enumerate(parts) if part.startswith("test_"))
        node = "/".join(parts[:module_end + 1]) + ".py"
        node += "::" + "::".join(parts[module_end + 1:] + [case.attrib["name"]])
        status = ("failed" if case.find("failure") is not None or case.find("error") is not None
                  else "skipped" if case.find("skipped") is not None else "passed")
        result[status].append(node)
    seen = set(result["passed"] + result["failed"] + result["skipped"])
    result["missing"] = sorted(set(required) - seen)
    blocked = set(result["failed"] + result["skipped"])
    result["all_required_passed"] = (bool(required) and set(required) <= set(result["passed"])
                                     and not set(required) & blocked)
    return result


def inside(row):
    """Run only in the disposable pinned container; upstream commands are inert."""
    os.chdir("/testbed")
    report = {"commands": [], "phases": []}

    def command(args):
        completed = subprocess.run(args, capture_output=True, text=True, timeout=120)
        record = {"argv": args, "returncode": completed.returncode,
                  "stdout": completed.stdout, "stderr": completed.stderr}
        report["commands"].append(record)
        return record

    def apply(step, field):
        path = Path("/tmp") / (step["swebench_instance_id"] + "-" + field + ".patch")
        path.write_text(step[field], encoding="utf-8")
        checked = command(["git", "apply", "--check", str(path)])
        return checked["returncode"] == 0 and command(["git", "apply", str(path)])["returncode"] == 0

    def check(name, required, test_directory="tests"):
        junit = Path("/tmp/results.xml")
        junit.unlink(missing_ok=True)
        result = command([PYTHON, "-m", "pytest", "--no-header", "-rA", "--tb=line",
                          "--color=no", "-p", "no:cacheprovider", "-W", "ignore::DeprecationWarning",
                          "--rootdir=" + str(Path(test_directory).resolve().parent),
                          "--junitxml=" + str(junit), test_directory])
        evidence = summarize_tests(junit.read_text(), required) if junit.exists() else None
        report["phases"].append({"name": name, "required": sorted(set(required)),
                                 "returncode": result["returncode"], "tests": evidence})

    head = command(["git", "rev-parse", "HEAD"])
    if head["stdout"].strip() != row["base_commit"]:
        raise ValueError("image checkout differs from pinned candidate base")
    if command(["git", "status", "--porcelain"])["stdout"].strip():
        raise ValueError("image checkout has pre-existing changes")
    command([PYTHON, "--version"])
    command([PYTHON, "-m", "pip", "freeze"])
    steps = row["bug_fixes"]
    required = steps[0]["FAIL_TO_PASS"] + steps[0]["PASS_TO_PASS"]
    check("original_base_tests", required)
    if not apply(steps[0], "test_patch"):
        return report
    check("first_task_unpatched", required)
    if not apply(steps[0], "patch"):
        return report
    check("first_task_reference", required)
    snapshots = []

    def snapshot(index, required):
        directory = Path("/tmp/regressions") / ("step_" + str(index)) / "tests"
        shutil.copytree("tests", directory, ignore=shutil.ignore_patterns("__pycache__"))
        snapshots.append((index, str(directory), list(required)))

    snapshot(1, required)
    source = Path("hashin.py")
    reference = source.read_text()
    for name, old, new in (
        ("digest_branch_false_download_label", "_verbose('Found hash for', found['url'])",
         "_verbose('Found URL', found['url'])"),
        ("fallback_branch_false_cached_label", "_verbose('Found URL', url)",
         "_verbose('Found hash for', url)"),
    ):
        if reference.count(old) != 1:
            raise ValueError("mutation target is not unique: " + name)
        source.write_text(reference.replace(old, new))
        check(name, required)
        source.write_text(reference)
    for index, step in enumerate(steps[1:], start=2):
        if not apply(step, "patch") or not apply(step, "test_patch"):
            report["cumulative_stop"] = {"step": index, "reason": "patch does not apply unchanged"}
            break
        required += step["FAIL_TO_PASS"] + step["PASS_TO_PASS"]
        check("cumulative_reference_step_" + str(index), required)
        for prior_index, directory, prior_required in snapshots:
            check("step_{}_frozen_step_{}".format(index, prior_index), prior_required, directory)
        snapshot(index, required)
    return report


def run_container(row):
    name = "code-comments-issue8-" + uuid.uuid4().hex
    # No host mounts, credentials, Docker socket, package installs, or dataset shell commands.
    args = ["docker", "run", "--name", name, "--rm", "--pull", "never", "--network", "none",
            "--cap-drop", "ALL", "--security-opt", "no-new-privileges", "--pids-limit", "128",
            "--memory", "2g", "--cpus", "2", "-i", "--entrypoint", PYTHON, IMAGE,
            "-c", Path(__file__).read_text(encoding="utf-8"), "--inside"]
    try:
        return subprocess.run(args, input=json.dumps(row), capture_output=True, text=True, timeout=900)
    finally:
        try:
            cleanup = subprocess.run(["docker", "rm", "--force", name],
                                     capture_output=True, text=True, timeout=30)
            if cleanup.returncode and "No such container" not in (cleanup.stderr or ""):
                print("Cannot confirm probe cleanup: " + name + " " + (cleanup.stderr or ""), file=sys.stderr)
        except (OSError, subprocess.SubprocessError) as exc:
            print("Cannot confirm probe cleanup: " + name + " " + str(exc), file=sys.stderr)


def main():
    if sys.argv[-1:] == ["--inside"]:
        print(json.dumps(inside(json.load(sys.stdin)), indent=2))
        return 0
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("parquet", type=Path)
    args = parser.parse_args()
    data = args.parquet.read_bytes()
    if hashlib.sha256(data).hexdigest() != DATASET_SHA256:
        parser.error("dataset SHA-256 does not match the pinned release")
    import pyarrow.parquet as parquet
    row = parquet.read_table(io.BytesIO(data)).to_pylist()[1]
    report = {"candidate": row["continuous_id"], "dataset_sha256": DATASET_SHA256,
              "probe_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "image": IMAGE, "model_calls": 0, "admission_verified": False,
              "patch_sha256": [{field: hashlib.sha256(step[field].encode()).hexdigest()
                                for field in ("patch", "test_patch")} for step in row["bug_fixes"]]}
    completed = run_container(row)
    report["container_returncode"] = completed.returncode
    report["container_stderr"] = completed.stderr
    report["execution"] = json.loads(completed.stdout) if completed.returncode == 0 else completed.stdout
    print(json.dumps(report, indent=2))
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
