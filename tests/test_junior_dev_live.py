"""Checks the Junior-dev headless runner offline (evaluation/junior_dev/live.py, #52).

The headless runs spend real money against a $10 cap the user set, so the ledger guard is
tested before any run: a call that could push the total over the cap must be refused. The
fidelity grader reads a recorded stream and decides whether a main agent really ran the loop
as the skill describes; these tests feed it synthetic streams.
"""

import json
from pathlib import Path
import tempfile
import unittest

from evaluation.junior_dev import live

H = '"C:/plugin/scripts/junior.py"'


def _events(*commands, final="## Junior-dev review\nWhat changed: step 2. Holes: token expiry.", ask_user=False):
    events = [{"type": "system", "subtype": "init", "skills": ["junior-dev:junior-dev"], "model": "claude-haiku-5-5"}]
    for i, cmd in enumerate(commands):
        events.append({"type": "assistant", "message": {"model": "claude-haiku-5-5", "content": [
            {"type": "tool_use", "id": f"t{i}", "name": "Bash", "input": {"command": f"python {H} {cmd}"}}]}})
        events.append({"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": f"t{i}", "content": "ok"}]}})
    if ask_user:
        events.append({"type": "assistant", "message": {"model": "claude-haiku-5-5", "content": [
            {"type": "tool_use", "id": "q", "name": "AskUserQuestion", "input": {}}]}})
    events.append({"type": "result", "subtype": "success", "result": final, "total_cost_usd": 0.05, "num_turns": 9})
    return "\n".join(json.dumps(e) for e in events)


FULL = ("start docs/plan.md", "ask .junior-dev/plan-1", "answer .junior-dev/plan-1 a.md", "ask .junior-dev/plan-1",
        "teachback .junior-dev/plan-1", "verdict .junior-dev/plan-1 correct", "report .junior-dev/plan-1")


class LedgerTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.ledger = Path(self._tmp.name) / "spend.json"
        self.ledger.write_text(json.dumps({"cap_usd": 10.0, "entries": [{"when": "x", "what": "y", "usd": 9.95}]}),
                               encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def test_guard_refuses_over_cap(self):
        with self.assertRaises(live.SpendCapError):
            live.guard(0.10, ledger=self.ledger)
        live.guard(0.05, ledger=self.ledger)

    def test_record_appends(self):
        live.record("run", 0.01, ledger=self.ledger)
        self.assertAlmostEqual(live.spent(ledger=self.ledger), 9.96)


class CommandTest(unittest.TestCase):
    def test_command_has_plugin_budget_and_no_prompt(self):
        argv = live.command("haiku", Path("/tmp/plugin"), 0.40)
        self.assertEqual(argv[:2], ["claude", "-p"])
        self.assertEqual(argv[argv.index("--plugin-dir") + 1], str(Path("/tmp/plugin")))
        self.assertEqual(argv[argv.index("--max-budget-usd") + 1], "0.40")
        self.assertEqual(argv[argv.index("--setting-sources") + 1], "project")
        self.assertIn("--no-session-persistence", argv)

    def test_plugin_copy_with_and_without_hooks(self):
        with tempfile.TemporaryDirectory() as tmp:
            with_hooks = live.plugin_copy(Path(tmp) / "a", hooks=True)
            without = live.plugin_copy(Path(tmp) / "b", hooks=False)
            self.assertTrue((with_hooks / "hooks" / "hooks.json").is_file())
            self.assertFalse((without / "hooks").exists())
            self.assertTrue((without / "skills" / "junior-dev" / "SKILL.md").is_file())
            self.assertTrue((without / "scripts" / "junior.py").is_file())


class FidelityTest(unittest.TestCase):
    def test_full_loop_passes(self):
        parsed = live.parse(_events(*FULL))
        state = {"end_reason": "teachback-correct", "round": 1, "rounds_cap": 6}
        result = live.fidelity(parsed, state)
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["helper_calls"], ["start", "ask", "answer", "ask", "teachback", "verdict", "report"])

    def test_missing_teachback_fails(self):
        parsed = live.parse(_events(*[c for c in FULL if not c.startswith(("teachback", "verdict"))]))
        result = live.fidelity(parsed, {"end_reason": None, "round": 1, "rounds_cap": 6})
        self.assertFalse(result["ok"])
        self.assertIn("no teach-back", result["problems"])

    def test_answer_before_ask_fails(self):
        parsed = live.parse(_events("start docs/plan.md", "answer .junior-dev/p a.md", "ask .junior-dev/p", "report .junior-dev/p"))
        self.assertFalse(live.fidelity(parsed, {"end_reason": "cap", "round": 1, "rounds_cap": 6})["ok"])

    def test_asking_the_user_fails(self):
        parsed = live.parse(_events(*FULL, ask_user=True))
        result = live.fidelity(parsed, {"end_reason": "teachback-correct", "round": 1, "rounds_cap": 6})
        self.assertIn("asked the user mid-loop", result["problems"])

    def test_report_must_reach_the_user(self):
        parsed = live.parse(_events(*FULL, final="Done."))
        result = live.fidelity(parsed, {"end_reason": "teachback-correct", "round": 1, "rounds_cap": 6})
        self.assertIn("final message lacks the changes and holes", result["problems"])

    def test_parse_tolerates_string_messages(self):
        stream = _events(*FULL) + "\n" + json.dumps({"type": "system", "subtype": "hook", "message": "a plain string"})
        self.assertEqual(live.parse(stream)["helper"][0], "start")

    def test_session_records_spend_even_if_parsing_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "spend.json"
            ledger.write_text(json.dumps({"cap_usd": 10.0, "entries": []}), encoding="utf-8")
            stream = Path(tmp) / "s.jsonl"
            stream.write_text(json.dumps({"type": "result", "total_cost_usd": 0.123}) + "\n{broken", encoding="utf-8")
            self.assertAlmostEqual(live.cost_from_stream(stream.read_text(encoding="utf-8")), 0.123)

    def test_activation(self):
        self.assertTrue(live.activation(live.parse(_events("start docs/plan.md")))["triggered"])
        self.assertFalse(live.activation(live.parse(_events()))["triggered"])


if __name__ == "__main__":
    unittest.main()
