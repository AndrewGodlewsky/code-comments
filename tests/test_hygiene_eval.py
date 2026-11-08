"""Checks the hygiene eval's grader against its own cases (evaluation/hygiene, #45).

A hill climb is only as good as its scorer. Each reference must pass every check, and
each unchanged input must fail at least one, or the case cannot tell a good run from
one that did nothing.
"""

import importlib.util
from pathlib import Path
import sys
import unittest

_PATH = Path(__file__).resolve().parents[1] / "evaluation" / "hygiene" / "grade.py"
_SPEC = importlib.util.spec_from_file_location("hygiene_grade", _PATH)
grade = importlib.util.module_from_spec(_SPEC)
sys.modules["hygiene_grade"] = grade
_SPEC.loader.exec_module(grade)


class HygieneGraderTest(unittest.TestCase):
    def test_references_pass_and_inputs_fail(self):
        self.assertEqual(grade.self_test(), [])

    def test_every_case_has_checks(self):
        cases = sorted(p.name for p in grade.CASES.iterdir() if p.is_dir())
        self.assertEqual(cases, sorted(grade.CHECKS))

    def test_override_is_recorded_in_evidence(self):
        case = "no-invented-reason"
        text = grade.statements(case)[3]
        result = grade.grade(grade.REFERENCES / case, case,
                             {text: {"passed": False, "evidence": "human ruling"}})
        item = next(e for e in result["expectations"] if e["text"] == text)
        self.assertFalse(item["passed"])
        self.assertIn("human ruling", item["evidence"])


if __name__ == "__main__":
    unittest.main()
