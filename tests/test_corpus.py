"""Admission guards for a metadata registry, without downloading its artifacts."""

import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class CorpusTests(unittest.TestCase):
    def validator(self):
        self.assertIsNotNone(importlib.util.find_spec("evaluation.corpus"))
        from evaluation.corpus import validate_registry
        return validate_registry

    def registry(self):
        path = Path(__file__).resolve().parents[1] / "evaluation/corpus-candidates.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def test_checked_in_registry_is_valid_and_all_candidates_pending(self):
        validate = self.validator()
        data = self.registry()
        self.assertEqual(validate(data), [])
        self.assertGreaterEqual(len(data["candidates"]), 6)
        self.assertEqual({c["status"] for c in data["candidates"]}, {"pending"})

    def test_duplicate_identity_and_task_are_rejected(self):
        validate = self.validator()
        for field in ("id", "task_ids"):
            with self.subTest(field=field):
                data = self.registry()
                data["candidates"][1][field] = copy.deepcopy(data["candidates"][0][field])
                self.assertTrue(any("duplicate" in e for e in validate(data)))

    def test_repository_split_leakage_is_case_insensitive(self):
        validate = self.validator()
        data = self.registry()
        data["candidates"][1]["repository"] = data["candidates"][0]["repository"].upper()
        data["candidates"][1]["split"] = "held_out"
        self.assertTrue(any("repository split leakage" in e for e in validate(data)))

    def test_duplicate_solution_hash_is_rejected_across_repositories(self):
        validate = self.validator()
        data = self.registry()
        data["candidates"][1]["repository"] = "different/repo"
        for c in data["candidates"][:2]:
            c["solution_sha256"] = "a" * 64
        self.assertTrue(any("duplicate solution" in e for e in validate(data)))

    def test_unpinned_or_missing_provenance_is_rejected(self):
        validate = self.validator()
        for field, value in (("revision", "main"), ("artifact_url", "https://example.org/main/data"),
                             ("artifact_url", "file:///tmp/data"), ("sha256", None)):
            with self.subTest(field=field, value=value):
                data = self.registry()
                data["candidates"][0]["upstream"][field] = value
                self.assertTrue(validate(data))

    def test_pending_artifacts_cannot_be_admitted(self):
        validate = self.validator()
        data = self.registry()
        data["candidates"][0]["status"] = "admitted"
        self.assertTrue(any("admitted requires" in e for e in validate(data)))

    def test_every_admission_gate_needs_verified_evidence(self):
        validate = self.validator()
        data = self.registry()
        c = data["candidates"][0]
        c["status"] = "admitted"
        c["environment"].update(execution_verified=True, image_digest="sha256:" + "b" * 64)
        for gate in c["gates"].values():
            gate.update(status="verified", evidence=["https://example.org/audit"])
        self.assertEqual(validate(data), [])
        for name in c["gates"]:
            with self.subTest(gate=name):
                bad = copy.deepcopy(data)
                bad["candidates"][0]["gates"][name]["evidence"] = []
                self.assertTrue(validate(bad))

    def test_missing_unknown_gates_and_outcome_selected_candidates_fail(self):
        validate = self.validator()
        for change in ("missing", "unknown", "outcomes"):
            data = self.registry()
            c = data["candidates"][0]
            if change == "missing":
                c["gates"].pop("rights")
            elif change == "unknown":
                c["gates"]["almost_verified"] = {"status": "verified", "evidence": []}
            else:
                c["selection"]["before_outcomes"] = False
            self.assertTrue(validate(data))

    def test_repeated_tasks_and_whitespace_aliases_fail(self):
        validate = self.validator()
        for suffix in ("", " "):
            data = self.registry()
            c = data["candidates"][0]
            c["task_ids"].append(c["task_ids"][0] + suffix)
            self.assertTrue(validate(data))

    def test_step_records_must_match_task_order_and_pin_revisions(self):
        validate = self.validator()
        for change in ("order", "revision", "count", "command"):
            data = self.registry()
            c = data["candidates"][3]
            if change == "order":
                c["steps"].reverse()
            elif change == "revision":
                c["steps"][0]["base_revision"] = "main"
            elif change == "count":
                c["steps"][0]["fail_to_pass_count"] = -1
            else:
                c["steps"][0]["test_command"] = None
            self.assertTrue(validate(data))

    def test_malformed_shapes_return_errors(self):
        validate = self.validator()
        for value in (None, [], {}, {"schema_version": 1, "candidates": []}):
            self.assertTrue(validate(value))
        for key in ("id", "repository", "task_ids", "upstream", "gates", "selection", "rights", "environment"):
            data = self.registry()
            data["candidates"][0][key] = None
            with self.subTest(key=key):
                self.assertTrue(validate(data))

    def test_verified_environment_needs_execution_and_immutable_image(self):
        validate = self.validator()
        for digest, executed in ((None, True), ("image:latest", True), ("sha256:" + "b" * 64, False)):
            data = self.registry()
            c = data["candidates"][0]
            c["gates"]["environment"].update(status="verified", evidence=["https://example.org/run"])
            c["environment"].update(image_digest=digest, execution_verified=executed)
            self.assertTrue(validate(data))

    def test_cli_reports_readiness_separately_from_validity(self):
        self.validator()
        result = subprocess.run([sys.executable, "-B", "-m", "evaluation.corpus"],
                                capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertTrue(report["valid"])
        self.assertEqual(report["admitted"], 0)
        self.assertFalse(report["pilot_ready"])
        self.assertEqual(report["model_calls"], 0)

    def test_cli_reports_bad_json_without_traceback(self):
        self.validator()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            path.write_text("{", encoding="utf-8")
            result = subprocess.run([sys.executable, "-B", "-m", "evaluation.corpus", str(path)],
                                    capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(json.loads(result.stdout)["valid"])
        self.assertNotIn("Traceback", result.stderr)
