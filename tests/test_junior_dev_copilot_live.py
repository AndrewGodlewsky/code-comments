"""Checks the GitHub Copilot activation runner offline (evaluation/junior_dev/copilot_live.py, #52).

The runner reads the Copilot CLI's printed transcript, so these tests feed it recorded text.
"""

import unittest

from evaluation.junior_dev import copilot_live

LOG = '''Starting the junior-dev review loop on the plan.

 $ Shell Start the loop 1 line
   python
   "C:/x/plugins/junior-dev/scripts/junior.py" start
   "C:/p/docs/plan.md"

 $ Shell Ask 20 lines
   python "C:/x/plugins/junior-dev/scripts/junior.py" ask "C:/p/.junior-dev/plan-1"

 $ Shell Answer then ask
   python "C:/x/scripts/junior.py"
   answer "C:/p/.junior-dev/plan-1" "C:/p/.junior-dev/plan-1/answers.md";
   python "C:/x/scripts/junior.py" ask "C:/p/.junior-dev/plan-1"

 $ Shell teach-back
   python "C:/x/scripts/junior.py" teachback "C:/p/.junior-dev/plan-1"

 $ Shell verdict and report
   python "C:/x/scripts/junior.py" verdict "C:/p/.junior-dev/plan-1" correct; python "C:/x/scripts/junior.py" report "C:/p/.junior-dev/plan-1"

What changed: step 2 now names the provider. Holes: the refund window is unknown.

Changes    +233 -36
AI Credits 3.87 (3m 44s)
Tokens     up 1.5m
'''

DENIED = ''' ✗ Shell  Permission denied because no interactive user response was available.
   python
   "C:/x/scripts/junior.py" start
   "C:/p/a.md"

I could not run it.

AI Credits 0.94 (27s)
'''


class CopilotLiveParseTest(unittest.TestCase):
    def test_helper_calls_are_read_in_order_across_wrapped_lines(self):
        parsed = copilot_live.parse(LOG)
        self.assertEqual(parsed["helper"], ["start", "ask", "answer", "ask", "teachback", "verdict", "report"])
        self.assertAlmostEqual(parsed["credits"], 3.87)

    def test_a_denied_helper_call_is_not_a_start(self):
        parsed = copilot_live.parse(DENIED)
        self.assertEqual(parsed["helper"], [])
        self.assertEqual(parsed["denied"], 1)

    def test_fidelity_uses_the_shared_checks(self):
        result = copilot_live.fidelity(copilot_live.parse(LOG), {"end_reason": "teachback-correct", "round": 2})
        self.assertTrue(result["ok"], result["problems"])


if __name__ == "__main__":
    unittest.main()
