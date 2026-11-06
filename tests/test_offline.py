import json
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import tempfile
import unittest

from evaluation.offline import audit, export_workspace


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "evaluation" / "fixtures" / "retry-policy"
INITIAL_FACTS = (
    "Missing or None retries means three retries; explicit zero disables retries.",
    "The legacy backend accepts at most five retries; larger values must be rejected.",
    "Retries count additional operations, not the initial operation.",
)


class ExportTests(unittest.TestCase):
    def test_placements_keep_identical_facts_and_initial_behavior(self):
        with tempfile.TemporaryDirectory() as temporary:
            for condition in ("baseline", "inline", "external"):
                with self.subTest(condition=condition):
                    target = Path(temporary) / condition
                    export_workspace(target, condition)
                    files = {p.name for p in target.iterdir()}
                    expected = {"policy.py", "TASK.md", "README.md"}
                    if condition == "external":
                        expected.add("context.md")
                    self.assertEqual(files, expected)
                    source = (target / "policy.py").read_text(encoding="utf-8")
                    context = (target / "context.md").read_text(encoding="utf-8") if condition == "external" else source
                    for fact in INITIAL_FACTS:
                        self.assertEqual(context.count(fact), 0 if condition == "baseline" else 1)
                        if condition == "external":
                            self.assertNotIn(fact, source)
                    namespace = {}
                    exec(compile(source, "policy.py", "exec"), namespace)
                    resolve = namespace["resolve_retries"]
                    self.assertEqual(resolve({}), 3)
                    self.assertEqual(resolve({"retries": 0}), 0)
                    with self.assertRaises(ValueError):
                        resolve({"retries": 6})

    def test_export_excludes_future_requests_facts_and_evaluator_assets(self):
        with tempfile.TemporaryDirectory() as temporary:
            for condition in ("baseline", "inline", "external"):
                target = Path(temporary) / condition
                export_workspace(target, condition)
                combined = "\n".join(p.read_text(encoding="utf-8") for p in target.iterdir())
                for forbidden in ("eight retries", "retry_delays", "checks.py", "reference/", "manifest.json"):
                    self.assertNotIn(forbidden, combined)
                self.assertIn("override", (target / "TASK.md").read_text(encoding="utf-8"))
                self.assertFalse((target / ".git").exists())

    def test_existing_destination_is_untouched(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            sentinel = target / "keep.txt"
            sentinel.write_text("user work", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                export_workspace(target, "inline")
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "user work")
            self.assertEqual(list(target.iterdir()), [sentinel])

    def test_existing_empty_destination_is_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(FileExistsError):
                export_workspace(Path(temporary), "baseline")

    def test_invalid_condition_creates_nothing(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "new"
            with self.assertRaises(ValueError):
                export_workspace(target, "unknown")
            self.assertFalse(target.exists())

    def test_common_guide_and_task_are_identical_across_arms(self):
        with tempfile.TemporaryDirectory() as temporary:
            for condition in ("baseline", "inline", "external"):
                export_workspace(Path(temporary) / condition, condition)
            for name in ("README.md", "TASK.md"):
                values = [(Path(temporary) / arm / name).read_bytes() for arm in ("baseline", "inline", "external")]
                self.assertEqual(values[0], values[1])
                self.assertEqual(values[1], values[2])


class AuditTests(unittest.TestCase):
    def test_reference_checkpoints_and_mutants_are_all_accounted_for(self):
        report = audit()
        self.assertEqual(report["kind"], "offline_fixture_audit")
        self.assertEqual(report["model_calls"], 0)
        self.assertTrue(report["passed"])
        self.assertEqual([row["step"] for row in report["references"]], [0, 1, 2, 3])
        self.assertTrue(all(row["passed"] for row in report["references"]))
        self.assertEqual(report["references"][1]["fact_ids"], ["retry-default", "legacy-limit", "retry-count"])
        self.assertEqual(report["references"][2]["fact_ids"], ["retry-default", "retry-count", "upgraded-limit"])
        self.assertEqual(report["references"][3]["fact_ids"], ["retry-default", "retry-count", "upgraded-limit", "bounded-delay"])
        self.assertEqual({row["name"] for row in report["mutants"]}, {
            "zero_override_lost", "stale_cap", "prior_zero_regression", "extra_initial_delay", "uncapped_delay"
        })
        self.assertTrue(all(row["rejected"] and row["failures"] for row in report["mutants"]))

    def test_checker_rejects_syntax_and_runtime_errors(self):
        check = runpy.run_path(str(FIXTURE / "private" / "checks.py"))["check"]
        for source in ("not valid python !", "raise RuntimeError('broken')", "def resolve_retries(settings, override=None):\n    raise RuntimeError('broken')\n"):
            with self.subTest(source=source):
                self.assertTrue(check(source, 1))

    def test_checker_rejects_a_previous_checkpoint_after_contract_changes(self):
        check = runpy.run_path(str(FIXTURE / "private" / "checks.py"))["check"]
        old = (FIXTURE / "private" / "reference" / "step-1.py").read_text(encoding="utf-8")
        self.assertFalse(check(old, 1))
        self.assertTrue(check(old, 2))

    def test_cli_audit_outputs_machine_readable_report(self):
        result = subprocess.run([sys.executable, "-m", "evaluation.offline", "audit"], cwd=ROOT, capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json.loads(result.stdout)["passed"])

    def test_cli_audit_fails_when_a_reference_breaks(self):
        with tempfile.TemporaryDirectory() as temporary:
            copy = Path(temporary) / "evaluation"
            shutil.copytree(ROOT / "evaluation", copy, ignore=shutil.ignore_patterns("__pycache__"))
            initial = copy / "fixtures" / "retry-policy" / "initial" / "policy.py"
            with initial.open("a", encoding="utf-8") as output:
                output.write("\nraise RuntimeError('deliberate broken reference')\n")
            result = subprocess.run([sys.executable, "-m", "evaluation.offline", "audit"], cwd=temporary, capture_output=True, text=True, timeout=20)
            self.assertEqual(result.returncode, 1, result.stderr)
            report = json.loads(result.stdout)
            self.assertFalse(report["passed"])
            self.assertFalse(report["references"][0]["passed"])

    def test_cli_export_reports_existing_destination_without_overwriting(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "new"
            command = [sys.executable, "-m", "evaluation.offline", "export", "--condition", "inline", "--destination", str(target)]
            first = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=20)
            self.assertEqual(first.returncode, 0, first.stderr)
            before = {p.name: p.read_bytes() for p in target.iterdir()}
            second = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=20)
            self.assertNotEqual(second.returncode, 0)
            self.assertEqual({p.name: p.read_bytes() for p in target.iterdir()}, before)


if __name__ == "__main__":
    unittest.main()
