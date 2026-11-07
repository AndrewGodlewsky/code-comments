"""Offline tests for the live adapter: subprocess.run is replaced, so no model is called."""

import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

from evaluation.skill_eval import live
from evaluation.skill_eval.grade import load_cases


def stream(*, model="claude-sonnet-5-5", skills=("cce:code-comments",), result=True):
    events = [
        {"type": "system", "subtype": "init", "claude_code_version": "test", "tools": ["Read", "Edit"],
         "plugins": [{"name": "cce"}], "skills": list(skills)},
        {"type": "assistant", "message": {"model": model, "content": [
            {"type": "text", "text": "Reading the task."},
            {"type": "tool_use", "name": "Edit", "input": {"file_path": "report.py"}}]}},
        {"type": "user", "message": {"content": [{"type": "tool_result", "content": "edited"}]}},
        {"type": "assistant", "message": {"model": model, "content": [{"type": "text", "text": "Done."}]}},
    ]
    if result:
        events.append({"type": "result", "subtype": "success", "is_error": False, "num_turns": 2,
                       "total_cost_usd": 0.05, "duration_ms": 4200,
                       "usage": {"input_tokens": 10, "output_tokens": 20, "cache_read_input_tokens": 30,
                                 "cache_creation_input_tokens": 40}})
    return "\n".join(json.dumps(e) for e in events) + "\n"


class LiveAdapterTests(unittest.TestCase):
    def setUp(self):
        self.case = next(c for c in load_cases() if c.id == "restrain-rename-helper")
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.workspace = Path(self.temporary.name)

    def run_with(self, stdout, skill="lean"):
        completed = subprocess.CompletedProcess(args=[], returncode=0, stdout=stdout, stderr="")
        with mock.patch.object(live.subprocess, "run", return_value=completed) as fake:
            result = live.run(self.case, self.workspace, skill=skill, model="claude-sonnet-5-5", timeout_s=5, max_budget_usd=1)
        return result, fake.call_args

    def test_control_has_no_plugin_and_variants_do(self):
        with tempfile.TemporaryDirectory() as temporary:
            self.assertIsNone(live.build_plugin("control", Path(temporary)))
            plugin = live.build_plugin("lean", Path(temporary))
            self.assertTrue((plugin / ".claude-plugin" / "plugin.json").is_file())
            self.assertTrue((plugin / "skills" / "code-comments" / "SKILL.md").is_file())
            with self.assertRaises(ValueError):
                live.build_plugin("no-such-variant", Path(temporary))

    def test_success_records_trace_usage_cost_and_isolation_flags(self):
        result, call = self.run_with(stream())
        command = call.args[0]
        for flag in ("--restricted", "--strict-mcp-config", "--plugin-dir", "--max-budget-usd"):
            self.assertIn(flag, command)
        self.assertTrue(command[2].startswith("/cce:code-comments "))
        self.assertEqual(call.kwargs["env"]["CLAUDE_CODE_DISABLE_AUTO_MEMORY"], "1")
        self.assertEqual(result["usage"]["cache_creation_input_tokens"], 40)
        self.assertEqual((result["cost_usd"], result["tool_calls"], result["latency_s"]), (0.05, 1, 4.2))
        roles = [turn["role"] for turn in result["trace"]]
        self.assertEqual(roles, ["system", "user", "assistant", "tool_call", "tool_result", "assistant"])

    def test_control_prompt_has_no_skill_prefix(self):
        _, call = self.run_with(stream(skills=()), skill="control")
        self.assertEqual(call.args[0][2], live.TASK_PROMPT)
        self.assertNotIn("--plugin-dir", call.args[0])

    def test_failures_are_classified_not_scored(self):
        for stdout, expected in ((stream(model="claude-haiku-5-5"), "served_model_mismatch"),
                                 (stream(skills=()), "harness_error"),
                                 (stream(result=False), "harness_error")):
            with self.subTest(expected=expected), self.assertRaises(live.LiveError) as raised:
                self.run_with(stdout)
            self.assertEqual(raised.exception.failure_class, expected)


if __name__ == "__main__":
    unittest.main()
