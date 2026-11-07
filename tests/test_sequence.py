import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from evaluation.skill_eval import sequence
from evaluation.skill_eval.adapters import ADAPTERS


def quiet(argv):
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return sequence.main(argv)


def ledger():
    return next(s for s in sequence.load_sequences() if s.id == "seq-ledger-refund")


class TransformTests(unittest.TestCase):
    def test_evidence_moves_out_of_docs_and_hand_off_removes_it(self):
        with tempfile.TemporaryDirectory() as temporary:
            workspace = sequence.prepare_writer(ledger(), Path(temporary))
            self.assertFalse((workspace / "docs").exists(), "docs/ must be free for the docs-folder arm")
            self.assertTrue((workspace / "evidence" / "ticket-412.md").is_file())
            self.assertIn("evidence/ticket-412.md", (workspace / "TASK.md").read_text(encoding="utf-8"))
            (workspace / "docs").mkdir()
            (workspace / "docs" / "ledger.md").write_text("maintained by the arm", encoding="utf-8")
            sequence.hand_off(ledger(), workspace)
            self.assertFalse((workspace / "evidence").exists())
            self.assertTrue((workspace / "docs" / "ledger.md").is_file(), "the arm's own docs must survive the hand-off")
            self.assertEqual((workspace / "TASK.md").read_text(encoding="utf-8"), ledger().reader_task)

    def test_arms(self):
        self.assertIsNone(sequence.arm_skill_dir("code-only"))
        self.assertTrue((sequence.arm_skill_dir("docs-folder") / "SKILL.md").is_file())
        self.assertTrue((sequence.arm_skill_dir("inline:lean") / "SKILL.md").is_file())
        for bad in ("inline:missing", "wiki"):
            with self.assertRaises(ValueError):
                sequence.arm_skill_dir(bad)


class MeasureTests(unittest.TestCase):
    def test_context_found_in_docs_as_well_as_comments(self):
        with tempfile.TemporaryDirectory() as temporary:
            workspace = sequence.prepare_writer(ledger(), Path(temporary))
            ADAPTERS["strip"](ledger().case, workspace)  # correct code, no comments
            self.assertEqual(sequence.writer_measures(ledger(), workspace)["context_recall"], 0.0)
            (workspace / "docs").mkdir()
            (workspace / "docs" / "ledger.md").write_text(
                "# Ledger\n\nThe payment gateway delivers webhooks at least once.\n\n"
                "Deduplicate on event_id, not amount: repeat payments share amounts.\n", encoding="utf-8")
            measures = sequence.writer_measures(ledger(), workspace)
            self.assertEqual((measures["context_recall"], measures["inline_recall"], measures["docs_files"]), (1.0, 0.0, 1))
            self.assertEqual(measures["writer_behavior"], 1)

    def test_reader_measures(self):
        trace = [{"role": "tool_call", "name": "Read", "content": '{"file_path": "docs/ledger.md"}'},
                 {"role": "tool_call", "name": "Grep", "content": "{}"}]
        self.assertEqual(sequence.reader_measures(trace), {"reader_opened_docs": 1, "reader_searches": 1})
        self.assertEqual(sequence.reader_measures([])["reader_opened_docs"], 0)

    def test_leak_guard_flags_a_task_that_states_the_fact(self):
        leaky = sequence.Sequence(ledger().root, dict(ledger().spec), ledger().case)
        original = sequence.Sequence.reader_task
        try:
            sequence.Sequence.reader_task = property(lambda self: "Webhooks from the gateway are delivered at least once.")
            self.assertTrue(any("leaks" in p for p in sequence.validity_problems(leaky)))
        finally:
            sequence.Sequence.reader_task = original


class RunnerTests(unittest.TestCase):
    def test_selftest_passes(self):
        self.assertEqual(quiet(["selftest"]), 0)

    def test_offline_run_writes_rows_and_reports(self):
        from evaluation.skill_eval import report
        with tempfile.TemporaryDirectory() as temporary:
            flow = str(Path(temporary) / "flow")
            self.assertEqual(quiet(["init", "--flow-dir", flow, "--reps", "1"]), 0)
            self.assertEqual(quiet(["run", "--flow-dir", flow, "--variant", "baseline", "--writer", "oracle", "--reader", "null"]), 0)
            self.assertEqual(quiet(["run", "--flow-dir", flow, "--variant", "v1", "--writer", "oracle", "--reader", "oracle", "--arm", "inline:lean"]), 0)
            rows = [json.loads(l) for l in (Path(flow) / "v1" / "results.jsonl").read_text(encoding="utf-8").splitlines()]
            self.assertTrue(rows and all(r["grade"]["pass"] == 1 for r in rows))
            baseline = [json.loads(l) for l in (Path(flow) / "baseline" / "results.jsonl").read_text(encoding="utf-8").splitlines()]
            self.assertTrue(all(r["grade"]["pass"] == 0 for r in baseline))
            self.assertEqual(quiet(["run", "--flow-dir", flow, "--variant", "v1", "--writer", "null", "--reader", "oracle"]), 1,
                             "a variant must not mix configurations")
            out = Path(temporary) / "report.md"
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(report.main([flow, "--out", str(out)]), 0)
            self.assertIn("context_recall", out.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
