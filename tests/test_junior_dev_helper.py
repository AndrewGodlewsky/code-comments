"""Checks the Junior-dev loop helper (plugins/junior-dev/scripts/junior.py, #52).

The helper is the only thing that talks to the junior. These tests pin the two promises the
design makes about it: the junior sees the artifact and this loop's questions and answers and
nothing else, and the loop always ends, by a correct teach-back or by the round cap. Every
test uses a fake runner; none of them calls a model.
"""

import contextlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

_PATH = Path(__file__).resolve().parents[1] / "plugins" / "junior-dev" / "scripts" / "junior.py"
_SPEC = importlib.util.spec_from_file_location("junior_dev_helper", _PATH)
junior = importlib.util.module_from_spec(_SPEC)
sys.modules["junior_dev_helper"] = junior
_SPEC.loader.exec_module(junior)

ARTIFACT = """# Password reset

1. The user asks for a reset link.
2. The API emails a one-time token.
3. The user sets a new password with the token.
"""


def questions_output(*texts, done=False):
    """What `claude -p --output-format json --json-schema` prints for one junior turn."""
    qs = [{"id": f"q{i + 1}", "text": t, "about": "step 2"} for i, t in enumerate(texts)]
    return json.dumps({"type": "result", "is_error": False, "result": "",
                       "structured_output": {"questions": qs, "done": done}})


def teachback_output(text, gaps=()):
    return json.dumps({"type": "result", "is_error": False, "result": "",
                       "structured_output": {"explanation": text, "gaps": list(gaps)}})


class FakeRunner:
    """Records every call and replies from a queue (the last reply repeats)."""

    def __init__(self, *replies):
        self.replies, self.calls = list(replies), []

    def __call__(self, argv, prompt):
        self.calls.append({"argv": list(argv), "prompt": prompt})
        return self.replies.pop(0) if len(self.replies) > 1 else self.replies[0]


class HelperTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.artifact = self.root / "docs" / "reset-plan.md"
        self.artifact.parent.mkdir(parents=True)
        self.artifact.write_text(ARTIFACT, encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def session(self, runner, rounds=6, root=None):
        return junior.JuniorSession.start(self.artifact, rounds=rounds, model="sonnet",
                                          state_root=root or self.root / ".junior-dev", runner=runner)

    def test_message_contains_only_artifact_and_transcript(self):
        transcript = [{"round": 1,
                       "questions": [{"id": "1", "text": "Who sends the email?", "about": "step 2"}],
                       "answers": [{"id": "1", "tag": "decided", "text": "The API, through the mail queue."}]}]
        message = junior.build_junior_message(ARTIFACT, transcript)
        self.assertIn("The API emails a one-time token.", message)
        self.assertIn("Who sends the email?", message)
        self.assertIn("The API, through the mail queue.", message)
        self.assertNotIn(str(self.artifact), message)
        self.assertNotIn("reset-plan.md", message)
        framing = junior.build_junior_message("", []) + junior.build_teachback_message("")
        for word in ("complete", "final", "approved"):
            self.assertNotIn(word, framing.lower())

    def test_command_is_isolated(self):
        argv = junior.junior_command("sonnet", junior.QUESTIONS_SCHEMA, junior.JUNIOR_PROMPT)
        for flag in ("--safe-mode", "--no-session-persistence", "--max-budget-usd",
                     "--system-prompt-file", "--json-schema"):
            self.assertIn(flag, argv)
        self.assertEqual(argv[argv.index("--tools") + 1], "")
        self.assertEqual(argv[argv.index("--model") + 1], "sonnet")
        self.assertTrue(Path(argv[argv.index("--system-prompt-file") + 1]).is_file())
        self.assertNotIn(ARTIFACT, " ".join(argv))

    def test_long_artifact_goes_through_stdin(self):
        long_text = "x" * 60000 + "\nEND-OF-ARTIFACT"
        self.artifact.write_text(long_text, encoding="utf-8")
        runner = FakeRunner(questions_output("What is x?"))
        self.session(runner).ask()
        self.assertIn(long_text, runner.calls[0]["prompt"])
        self.assertNotIn("END-OF-ARTIFACT", " ".join(runner.calls[0]["argv"]))

    def test_runner_sets_nested_env_and_uses_stdin(self):
        completed = mock.Mock(returncode=0, stdout="{}", stderr="")
        with mock.patch.object(junior.subprocess, "run", return_value=completed) as run:
            junior.run_claude(["claude", "-p"], "PROMPT-TEXT")
        kwargs = run.call_args.kwargs
        self.assertEqual(kwargs["env"]["JUNIOR_DEV_NESTED"], "1")
        self.assertEqual(kwargs["input"], "PROMPT-TEXT")
        self.assertEqual(kwargs["encoding"], "utf-8")
        self.assertNotIn("PROMPT-TEXT", run.call_args.args[0])
        self.assertNotEqual(Path(kwargs["cwd"]).resolve(), Path.cwd().resolve())

    def test_round_cap_ends_loop(self):
        runner = FakeRunner(questions_output("Why a token?"))
        s = self.session(runner, rounds=2)
        for _ in range(2):
            s.ask()
            qid = s.state["transcript"][-1]["questions"][0]["id"]
            s.answer(f"Q{qid} [decided]: placeholder")
        out = s.ask()
        self.assertIn("ROUND CAP REACHED", out)
        self.assertEqual(s.state["phase"], "done")
        self.assertEqual(s.state["end_reason"], "cap")

    def test_question_ids_continue_across_rounds(self):
        runner = FakeRunner(questions_output("A?", "B?"), questions_output("C?"))
        s = self.session(runner)
        s.ask()
        s.answer("Q1 [checked]: a\nQ2 [checked]: b")
        out = s.ask()
        self.assertIn("Q3", out)

    def test_ask_refuses_before_answers(self):
        runner = FakeRunner(questions_output("A?"))
        s = self.session(runner)
        s.ask()
        with self.assertRaises(junior.JuniorError):
            s.ask()

    def test_wrong_teachback_returns_to_asking(self):
        runner = FakeRunner(questions_output(done=True), teachback_output("It emails a link."))
        s = self.session(runner)
        self.assertIn("NO MORE QUESTIONS", s.ask())
        s.teachback()
        s.verdict(False, "It missed that the token expires.")
        self.assertEqual(s.state["phase"], "asking")
        self.assertEqual(s.state["teachbacks"][-1]["verdict"], "wrong")

    def test_correct_teachback_finishes(self):
        runner = FakeRunner(questions_output(done=True), teachback_output("Step by step..."))
        s = self.session(runner)
        s.ask()
        s.teachback()
        s.verdict(True)
        self.assertEqual(s.state["phase"], "done")
        self.assertEqual(s.state["end_reason"], "teachback-correct")

    def test_teachback_message_has_no_transcript(self):
        runner = FakeRunner(questions_output("Who sends the email?"), questions_output(done=True),
                            teachback_output("Explained."))
        s = self.session(runner)
        s.ask()
        s.answer("Q1 [decided]: The API.")
        s.ask()
        s.teachback()
        teach_prompt = runner.calls[-1]["prompt"]
        self.assertIn("one-time token", teach_prompt)
        self.assertNotIn("Who sends the email?", teach_prompt)
        self.assertEqual(Path(runner.calls[-1]["argv"][runner.calls[-1]["argv"].index("--system-prompt-file") + 1]).name,
                         "teachback-prompt.md")

    def test_malformed_output_retries_once_then_errors(self):
        runner = FakeRunner("not json", "still not json")
        s = self.session(runner)
        before = (s.state_dir / "state.json").read_text(encoding="utf-8")
        with self.assertRaises(junior.JuniorError):
            s.ask()
        self.assertEqual(len(runner.calls), 2)
        self.assertEqual((s.state_dir / "state.json").read_text(encoding="utf-8"), before)

    def test_unknown_answers_become_holes(self):
        runner = FakeRunner(questions_output("How long does the token last?"))
        s = self.session(runner)
        s.ask()
        s.answer("Q1 [unknown]: No expiry was decided.")
        self.assertEqual(len(s.state["holes"]), 1)
        self.assertIn("How long does the token last?", s.state["holes"][0])
        self.assertIn("ROUND", s.report().upper())
        self.assertIn("How long does the token last?", s.report())

    def test_changed_lines_become_changes(self):
        answers, changes = junior.parse_answers(
            "Q1 [checked]: The mail queue sends it.\n  It retries three times.\n"
            "Changed: step 2 now names the mail queue.\nQ2 [decided]: 15 minutes.")
        self.assertEqual([a["id"] for a in answers], ["1", "2"])
        self.assertIn("retries three times", answers[0]["text"])
        self.assertEqual(changes, ["step 2 now names the mail queue."])

    def test_unicode_and_spaces(self):
        self.artifact.write_text("Flow → Δ é\n" + ARTIFACT, encoding="utf-8")
        runner = FakeRunner(questions_output("What does Δ mean?"))
        s = self.session(runner, root=self.root / "a b" / "c d")
        s.ask()
        s.answer("Q1 [unknown]: é → not decided")
        reloaded = junior.JuniorSession(s.state_dir, runner=runner)
        self.assertIn("Δ", reloaded.state["transcript"][0]["questions"][0]["text"])
        self.assertIn("é → not decided", reloaded.report())
        self.assertIn("Flow → Δ é", runner.calls[0]["prompt"])

    def test_cost_is_accumulated(self):
        reply = json.loads(questions_output("A?"))
        reply["total_cost_usd"] = 0.0125
        runner = FakeRunner(json.dumps(reply))
        s = self.session(runner)
        s.ask()
        self.assertAlmostEqual(s.state["cost_usd"], 0.0125)
        self.assertIn("0.0125", s.report())

    def test_cli_round_trip(self):
        runner = FakeRunner(questions_output("A?"))
        root = self.root / ".junior-dev"
        with mock.patch.object(junior, "run_claude", runner), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(junior.main(["start", str(self.artifact), "--state-root", str(root)]), 0)
            state_dir = next(p for p in root.iterdir() if p.is_dir())
            self.assertEqual(junior.main(["ask", str(state_dir)]), 0)
            answers = self.root / "answers.md"
            answers.write_text("Q1 [decided]: yes", encoding="utf-8")
            self.assertEqual(junior.main(["answer", str(state_dir), str(answers)]), 0)
            self.assertEqual(junior.main(["report", str(state_dir)]), 0)
        self.assertEqual((root / ".gitignore").read_text(encoding="utf-8").strip(), "*")


if __name__ == "__main__":
    unittest.main()
