"""The preflight must not mistake skipped or missing checks for passing evidence."""

import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


class HashinProbeTests(unittest.TestCase):
    def summarize(self, xml, required):
        self.assertIsNotNone(importlib.util.find_spec("evaluation.hashin_probe"))
        from evaluation.hashin_probe import summarize_tests
        return summarize_tests(xml, required)

    def test_failures_and_errors_cannot_pass_the_required_set(self):
        xml = '''<testsuite>
          <testcase classname="tests.test_cli.Tests" name="test_ok"/>
          <testcase classname="tests.test_cli.Tests" name="test_bad"><failure/></testcase>
          <testcase classname="tests.test_cli.Tests" name="test_error"><error/></testcase>
        </testsuite>'''
        result = self.summarize(xml, ["tests/test_cli.py::Tests::test_ok",
                                      "tests/test_cli.py::Tests::test_bad"])
        self.assertEqual(result["passed"], ["tests/test_cli.py::Tests::test_ok"])
        self.assertEqual(result["failed"], ["tests/test_cli.py::Tests::test_bad",
                                             "tests/test_cli.py::Tests::test_error"])
        self.assertFalse(result["all_required_passed"])

    def test_skipped_or_uncollected_checks_are_not_passing(self):
        xml = '''<testsuite><testcase classname="tests.test_arg_parse"
                    name="test_minimal"><skipped/></testcase></testsuite>'''
        result = self.summarize(xml, ["tests/test_arg_parse.py::test_minimal",
                                      "tests/test_cli.py::Tests::test_run"])
        self.assertEqual(result["missing"], ["tests/test_cli.py::Tests::test_run"])
        self.assertEqual(result["skipped"], ["tests/test_arg_parse.py::test_minimal"])
        self.assertFalse(result["all_required_passed"])

    def test_all_required_checks_must_actually_pass(self):
        xml = '<testsuite><testcase classname="tests.test_cli.Tests" name="test_ok"/></testsuite>'
        result = self.summarize(xml, ["tests/test_cli.py::Tests::test_ok"])
        self.assertTrue(result["all_required_passed"])

    def test_duplicate_failure_cannot_be_masked_by_a_passing_case(self):
        xml = '''<testsuite>
          <testcase classname="tests.test_cli.Tests" name="test_same"/>
          <testcase classname="tests.test_cli.Tests" name="test_same"><failure/></testcase>
        </testsuite>'''
        self.assertFalse(self.summarize(xml, ["tests/test_cli.py::Tests::test_same"])["all_required_passed"])

    def test_wrong_dataset_is_rejected_before_optional_dependencies_or_docker(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "wrong.parquet"
            path.write_bytes(b"not the release")
            result = subprocess.run([sys.executable, "-B", "-m", "evaluation.hashin_probe", str(path)],
                                    capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("dataset SHA-256 does not match", result.stderr)

    def test_timeout_and_interrupt_remove_only_the_probe_container(self):
        from evaluation import hashin_probe
        self.assertTrue(hasattr(hashin_probe, "run_container"))
        for failure in (subprocess.TimeoutExpired("docker", 900), KeyboardInterrupt()):
            with self.subTest(failure=type(failure).__name__), patch.object(
                hashin_probe.subprocess, "run", side_effect=[failure, subprocess.CompletedProcess([], 0)]
            ) as run:
                with self.assertRaises(type(failure)):
                    hashin_probe.run_container({})
                launch = run.call_args_list[0].args[0]
                name = launch[launch.index("--name") + 1]
                self.assertTrue(name.startswith("code-comments-issue8-"))
                self.assertEqual(run.call_args_list[1].args[0], ["docker", "rm", "--force", name])
