import contextlib
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from evaluation.skill_eval import run
from evaluation.skill_eval.adapters import ADAPTERS
from evaluation.skill_eval.comments import blocks, code_fingerprint, scopes
from evaluation.skill_eval.grade import METRICS, grade, load_cases, matches


def quiet(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = run.main(argv)
    return code, out.getvalue(), err.getvalue()


def case(case_id):
    return next(c for c in load_cases() if c.id == case_id)


class CommentParsingTests(unittest.TestCase):
    def test_adjacent_full_line_comments_form_one_block(self):
        source = "# one\n# two\nx = 1  # trailing\n\n# three\ndef f():\n    '''Doc.'''\n    return 1\n"
        found = [(b.kind, b.text) for b in blocks(source)]
        self.assertEqual(found, [("comment", "one two"), ("comment", "trailing"), ("comment", "three"), ("docstring", "doc.")])

    def test_scope_includes_comment_block_directly_above(self):
        source = "x = 1\n# why\n# more\ndef f():\n    return 1\n"
        self.assertEqual(scopes(source)["f"], (2, 5))

    def test_fingerprint_ignores_comments_and_docstrings_only(self):
        base = "def f():\n    '''Old.'''\n    return 1\n"
        self.assertEqual(code_fingerprint(base), code_fingerprint("def f():\n    # new\n    '''New.'''\n    return 1\n"))
        self.assertNotEqual(code_fingerprint(base), code_fingerprint("def f():\n    '''Old.'''\n    return 2\n"))

    def test_anchor_groups_require_every_group_and_support_regex(self):
        self.assertTrue(matches([["eight", r"re:\b8\b"], ["backend"]], "the backend accepts 8"))
        self.assertFalse(matches([[r"re:\b8\b"], ["backend"]], "the backend accepts 18"))
        self.assertFalse(matches([["eight"], ["backend"]], "accepts eight"))


class GraderTests(unittest.TestCase):
    def grade_with(self, case_id, edit):
        target = case(case_id)
        with tempfile.TemporaryDirectory() as temporary:
            workspace = run.prepare(target, Path(temporary))
            ADAPTERS["oracle"](target, workspace)
            edit(workspace)
            return grade(target, workspace)[0]

    def test_every_metric_is_reported(self):
        scores = self.grade_with("restrain-rename-helper", lambda workspace: None)
        self.assertEqual(tuple(scores), METRICS)

    def test_padding_attached_to_a_real_explanation_still_counts_as_noise(self):
        def pad(workspace):
            path = workspace / "ledger.py"
            text = path.read_text(encoding="utf-8")
            padding = "".join(f"        # Note {n}: this method updates the balance.\n" for n in range(10))
            path.write_text(text.replace("        account = event", padding + "        account = event", 1), encoding="utf-8")
        scores = self.grade_with("capture-ledger-idempotency", pad)
        self.assertEqual(scores["recall"], 1.0)
        self.assertGreater(scores["noise_lines"], 3)
        self.assertEqual(scores["pass"], 0)

    def test_correcting_a_stale_comment_costs_no_more_than_deleting_it(self):
        fixed = "    # The upgraded backend accepts at most eight retries and rejects larger values.\n"
        target = case("maintain-retry-limit")
        with tempfile.TemporaryDirectory() as temporary:
            # Reference code, but its new comment swapped for `replacement`; the stale line is gone either way.
            def score(replacement):
                workspace = run.prepare(target, Path(temporary) / str(abs(hash(replacement))))
                ADAPTERS["oracle"](target, workspace)
                path = workspace / "policy.py"
                path.write_text(path.read_text(encoding="utf-8").replace(fixed, replacement), encoding="utf-8")
                return grade(target, workspace)[0]["noise_lines"]
            deleted = score("")
            corrected = score("    # Validation follows the current backend's bound.\n")
            padded = score("    # Validation follows the current backend's bound.\n    # Extra line one.\n    # Extra line two.\n")
        self.assertEqual(deleted, corrected)
        self.assertEqual(padded, corrected + 2)

    def test_comment_only_request_rejects_code_changes(self):
        def change(workspace):
            path = workspace / "cache.py"
            path.write_text(path.read_text(encoding="utf-8").replace(">= TTL_SECONDS", "> TTL_SECONDS"), encoding="utf-8")
        scores = self.grade_with("audit-cache-ttl", change)
        self.assertEqual((scores["behavior"], scores["pass"]), (0, 0))

    def test_losing_a_protected_comment_fails(self):
        def drop(workspace):
            path = workspace / "policy.py"
            path.write_text(path.read_text(encoding="utf-8").replace("# SPDX-License-Identifier: MIT\n", ""), encoding="utf-8")
        scores = self.grade_with("maintain-retry-limit", drop)
        self.assertEqual((scores["preserved"], scores["pass"]), (0.5, 0))

    def test_fact_outside_its_owner_scope_is_misplaced(self):
        def move(workspace):
            path = workspace / "policy.py"
            text = path.read_text(encoding="utf-8").replace(
                "    # The upgraded backend accepts at most eight retries and rejects larger values.\n", "")
            path.write_text(text + "\n\n# The upgraded backend accepts at most eight retries.\n", encoding="utf-8")
        scores = self.grade_with("maintain-retry-limit", move)
        self.assertEqual((scores["recall"], scores["misplaced"]), (0.0, 1))

    def test_unparseable_or_undecodable_output_is_a_model_failure_not_a_crash(self):
        for broken in (b'def format_dollars(:\n    """unclosed\n', b"x = (\n", b"\xff\xfe junk"):
            with self.subTest(broken=broken):
                scores = self.grade_with("restrain-rename-helper", lambda w, b=broken: (w / "report.py").write_bytes(b))
                self.assertEqual((scores["behavior"], scores["pass"]), (0, 0))

    def test_workspace_that_breaks_the_checks_scores_zero_instead_of_vanishing(self):
        renamed = lambda w: (w / "report.py").write_text("def other():\n    return 1\n", encoding="utf-8")
        exits = lambda w: (w / "report.py").write_text("import sys\nsys.exit(0)\n", encoding="utf-8")
        for edit in (renamed, exits):
            scores = self.grade_with("restrain-rename-helper", edit)
            self.assertEqual((scores["behavior"], scores["pass"]), (0, 0))

    def test_workspace_cannot_forge_a_passing_check_result(self):
        forge = "print('[]', flush=True)\nimport os\nos._exit(0)\n"
        scores = self.grade_with("restrain-rename-helper", lambda w: (w / "report.py").write_text(forge, encoding="utf-8"))
        self.assertEqual(scores["behavior"], 0)

    def test_grader_material_never_appears_in_visible_workspaces(self):
        for target in load_cases():
            names = {p.name for p in target.visible.rglob("*")}
            self.assertFalse(names & {"case.json", "checks.py"}, target.id)
            self.assertFalse(any("reference" in p.parts for p in target.visible.rglob("*")), target.id)


class RunnerTests(unittest.TestCase):
    def test_selftest_passes(self):
        code, out, _ = quiet(["selftest"])
        report = json.loads(out)
        self.assertEqual(code, 0, report["problems"])
        self.assertEqual(report["model_calls"], 0)
        self.assertEqual(report["pass_rate"]["oracle"], 1.0)
        self.assertEqual(report["pass_rate"]["null"], 0.0)

    def test_init_run_resume_and_harness_gate(self):
        with tempfile.TemporaryDirectory() as temporary:
            flow = str(Path(temporary) / "flow")
            self.assertEqual(quiet(["init", "--flow-dir", flow, "--seed", "7"])[0], 0)
            self.assertEqual(quiet(["init", "--flow-dir", flow, "--seed", "8"])[0], 1, "split must be fixed once")
            state = json.loads((Path(flow) / "_state.json").read_text(encoding="utf-8"))
            ids = state["train_ids"] + state["test_ids"]
            self.assertEqual(sorted(ids), sorted(c.id for c in load_cases()))
            self.assertEqual(quiet(["run", "--flow-dir", flow, "--adapter", "oracle", "--variant", "baseline"])[0], 2, "unapproved harness")
            self.assertEqual(quiet(["run", "--flow-dir", flow, "--adapter", "oracle", "--variant", "oracle-run", "--approve-harness"])[0], 1)
            self.assertEqual(quiet(["run", "--flow-dir", flow, "--adapter", "oracle", "--variant", "baseline", "--reps", "2", "--approve-harness"])[0], 0)
            results = Path(flow) / "baseline" / "results.jsonl"
            rows = [json.loads(line) for line in results.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(rows), 2 * len(ids))
            for row in rows:
                self.assertEqual(set(row["grade"]), set(METRICS))
                self.assertEqual(row["grade"]["pass"], 1)
                self.assertTrue((Path(flow) / "baseline" / "traces" / f"{row['prompt_id']}_rep{row['rep']}.json").is_file())
            self.assertEqual(quiet(["run", "--flow-dir", flow, "--adapter", "oracle", "--variant", "baseline", "--reps", "2"])[0], 0)
            self.assertEqual(len(results.read_text(encoding="utf-8").splitlines()), len(rows), "resume must not duplicate rows")
            state = json.loads((Path(flow) / "_state.json").read_text(encoding="utf-8"))
            state["harness_sha"] = "0" * 64
            (Path(flow) / "_state.json").write_text(json.dumps(state), encoding="utf-8")
            self.assertEqual(quiet(["run", "--flow-dir", flow, "--adapter", "null", "--variant", "v1"])[0], 2, "harness change must block")

    def test_resume_drops_a_truncated_row_and_refuses_to_mix_adapters(self):
        with tempfile.TemporaryDirectory() as temporary:
            flow = str(Path(temporary) / "flow")
            quiet(["init", "--flow-dir", flow, "--seed", "7", "--reps", "1"])
            self.assertEqual(quiet(["run", "--flow-dir", flow, "--adapter", "null", "--variant", "v1", "--approve-harness"])[0], 0)
            results = Path(flow) / "v1" / "results.jsonl"
            lines = results.read_text(encoding="utf-8").splitlines()
            results.write_text("\n".join(lines[:-1]) + "\n" + lines[-1][:40], encoding="utf-8")
            self.assertEqual(quiet(["run", "--flow-dir", flow, "--adapter", "null", "--variant", "v1"])[0], 0)
            rows = [json.loads(line) for line in results.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(rows), len(lines))
            self.assertEqual(len({(r["prompt_id"], r["rep"]) for r in rows}), len(lines))
            self.assertEqual(quiet(["run", "--flow-dir", flow, "--adapter", "oracle", "--variant", "v1"])[0], 1)


if __name__ == "__main__":
    unittest.main()
