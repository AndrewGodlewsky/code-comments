import json
import os
from pathlib import Path
import unittest

from evaluation.grading import compare_results, grade


FIXTURE = Path(__file__).resolve().parents[1] / "evaluation" / "fixtures" / "retry-policy"


class ProtocolTests(unittest.TestCase):
    def test_result_protocol_rejects_forged_incomplete_or_wrong_typed_results(self):
        expected = [{"value": 1}, {"exception": "ValueError"}]
        self.assertEqual(compare_results(json.dumps(expected), expected), [])
        for output in ("PASS", "{}", "[]", json.dumps([{"value": True}, expected[1]]), json.dumps(expected + expected), '[{"value":1,"value":2},{"exception":"ValueError"}]'):
            with self.subTest(output=output):
                self.assertTrue(compare_results(output, expected))


@unittest.skipUnless(os.environ.get("CODE_COMMENTS_DOCKER") == "1", "opt-in Docker integration")
class GradingTests(unittest.TestCase):
    def test_reference_passes_and_stale_limit_fails(self):
        source = (FIXTURE / "private" / "reference" / "step-2.py").read_text(encoding="utf-8")
        self.assertTrue(grade({"policy.py": source}, 2)["passed"])
        self.assertFalse(grade({"policy.py": source.replace("<= 8", "<= 5")}, 2)["passed"])

    def test_candidate_pass_claims_and_import_failure_do_not_pass(self):
        for source in ("print('PASS')", "raise RuntimeError('broken')", "import os; os._exit(0)"):
            with self.subTest(source=source):
                self.assertFalse(grade({"policy.py": source}, 1)["passed"])

    def test_candidate_cannot_modify_host_evaluator(self):
        source = "from pathlib import Path\nPath('/private/checks.py').write_text('PASS')\n"
        self.assertFalse(grade({"policy.py": source}, 1)["passed"])

    def test_printing_a_correct_function_result_does_not_corrupt_protocol(self):
        source = (FIXTURE / "private" / "reference" / "step-1.py").read_text(encoding="utf-8")
        source = source.replace("return retries", "print('diagnostic'); return retries")
        self.assertTrue(grade({"policy.py": source}, 1)["passed"])
