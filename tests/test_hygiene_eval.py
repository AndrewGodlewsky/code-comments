"""Checks the hygiene eval's grader against its own cases (evaluation/hygiene, #45).

A hill climb is only as good as its scorer. Each reference must pass every check, and
each unchanged input must fail at least one, or the case cannot tell a good run from
one that did nothing.
"""

import importlib.util
from pathlib import Path
import sys
import tempfile
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

    def test_rewrapped_comment_is_not_lost(self):
        with tempfile.TemporaryDirectory() as tmp:
            orig, out = Path(tmp, "orig"), Path(tmp, "out")
            orig.mkdir(), out.mkdir()
            (orig / "a.py").write_text("# Rows are rounded first, so the total\n"
                                       "# can differ by a cent.\nX = 1\n", encoding="utf-8")
            (out / "a.py").write_text("# Rows are rounded first,\n"
                                      "# so the total can differ by a cent.\nX = 1\n",
                                      encoding="utf-8")
            self.assertEqual(grade.lost_prose(out, orig), {})
            (out / "a.py").write_text("# Rows are rounded first.\nX = 1\n", encoding="utf-8")
            self.assertIn("a.py", grade.lost_prose(out, orig))


    def test_not_none_clause_is_not_stale(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            (out / "tags").mkdir()
            doc = '''def parse_tags(text):
    """Split text on commas.

    Returns [] if text is None. Raises ValueError if text is not None and holds no tags.
    """
'''
            (out / "tags" / "parse.py").write_text(doc, encoding="utf-8")
            self.assertTrue(grade.no_none_raises(out, out)[0])
            (out / "tags" / "parse.py").write_text(doc.replace("is not None and", "is None or"),
                                                   encoding="utf-8")
            self.assertFalse(grade.no_none_raises(out, out)[0])


if __name__ == "__main__":
    unittest.main()
