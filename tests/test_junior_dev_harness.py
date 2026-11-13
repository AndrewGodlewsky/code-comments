"""Checks the Junior-dev tournament harness offline (evaluation/junior_dev, #52).

The tournament is only a fair test if each role sees what the design says it sees: the junior
gets the artifact and its own questions and answers (plus the brief only in the JuniorFull
arm), readers get the final artifact alone, and the shipped prompt text is what runs. These
tests build real batches from fixture cases and execute them under a Node dry run with stub
agents, so they check the script that actually runs, without calling a model.
"""

import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

from evaluation.junior_dev import arms, build, cases, collect, mermaid, score

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "junior-dev"
_SPEC = importlib.util.spec_from_file_location("junior_dev_helper_h", PLUGIN / "scripts" / "junior.py")
junior = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(junior)
NODE = shutil.which("node")

BRIEF = "BRIEF-MARKER: plan the login flow for the shop as a numbered plan."


def _fixture_cases(root: Path):
    quiz = [{"id": f"q{i}", "kind": "brief" if i <= 4 else "design", "question": f"QUESTION-{i}?", "key": f"key {i}",
             "why": "w"} for i in range(1, 9)]
    items = []
    for cid, fam, split in (("fx-01", "fam-a", "dev"), ("fx-02", "fam-b", "heldout")):
        items.append({"slot": {"id": cid, "split": split, "family": fam, "complexity": "simple", "format": "prose-steps",
                               "existing": True, "undecided": True, "topic": "t"},
                      "case": {"brief": BRIEF, "existing_files": [{"path": "existing/app.py", "content": "EXISTING-MARKER\n"}],
                               "undecided": [{"point": "session length", "how_brief_says_it": "not decided"}],
                               "quiz": quiz, "requirements": [{"id": f"r{i}", "text": "req"} for i in range(1, 5)],
                               "reference_artifact": "1. REFERENCE-MARKER step.\n",
                               "seeded_presentation": "SEEDED-P-MARKER", "seeded_implicit": "SEEDED-I-MARKER"},
                      "notes": [], "rewritten": False})
    out = root / "out.json"
    out.write_text(json.dumps({"cases": items}), encoding="utf-8")
    cases.write(out, root=root / "cases")
    return root / "cases"


@unittest.skipUnless(NODE, "node is required for the dry-run harness")
class BuildAndDryRunTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.tmp = Path(cls._tmp.name)
        cls.case_root = _fixture_cases(cls.tmp)
        all_arms = list(arms.CONTROLS) + [arms.DEFAULT_JUNIOR, arms.Arm(name="junior-same", review="junior", teachback="same")]
        cls.files = build.build_batch(["fx-01", "fx-02"], all_arms, ["haiku"], 1, "natural", cls.tmp / "built",
                                      "fixture", cases_root=cls.case_root)
        cls.dry = build.dry_run(cls.files[0])

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def prompts(self, role, arm=None):
        return [p for p in self.dry["prompts"] if p["role"] == role and (arm is None or p["arm"] == arm)]

    def test_built_batch_runs(self):
        runs = self.dry["result"]["runs"]
        self.assertEqual(len(runs), 2 * (len(arms.CONTROLS) + 2))
        self.assertTrue(all(r and r["artifact_final"] for r in runs))
        self.assertTrue(all(not r["errors"] for r in runs), [r["errors"] for r in runs if r["errors"]])

    def test_author_answers_are_recorded(self):
        # Real authors label answers "Q1"; the pilot lost every answer when the harness expected "1".
        juniors = [r for r in self.dry["result"]["runs"] if r["arm"] in ("junior", "junior-full", "junior-same")]
        self.assertTrue(juniors)
        for run in juniors:
            answers = [a for rnd in run["transcript"] for a in rnd["answers"]]
            self.assertEqual([a["id"] for a in answers], ["1", "2"], run["run_id"])
            self.assertEqual(len(run["holes"]), 1)
        second = [p for p in self.dry["prompts"] if p["role"] == "junior" and p["arm"] == "junior"][1]["prompt"]
        self.assertIn("A1 [checked]: ans one", second)
        self.assertNotIn("(no answer)", second)

    def test_embedded_prompts_match_plugin(self):
        data = build.embedded_data(self.files[0])
        refs = PLUGIN / "skills" / "junior-dev" / "references"
        self.assertEqual(data["prompts"]["junior"], (refs / "junior-prompt.md").read_text(encoding="utf-8"))
        self.assertEqual(data["prompts"]["teachback"], (refs / "teachback-prompt.md").read_text(encoding="utf-8"))
        self.assertEqual(data["prompts"]["skill"], (PLUGIN / "skills" / "junior-dev" / "SKILL.md").read_text(encoding="utf-8"))
        self.assertEqual(data["framing"]["ask"], junior.ASK_INSTRUCTION)

    def test_only_junior_full_sees_brief(self):
        juniors = self.prompts("junior")
        self.assertTrue(juniors)
        for p in juniors:
            self.assertEqual("BRIEF-MARKER" in p["prompt"], p["arm"] == "junior-full", p["arm"])
            self.assertNotIn("EXISTING-MARKER", p["prompt"])

    def test_readers_never_see_brief_or_transcript(self):
        readers = self.prompts("reader")
        self.assertTrue(readers)
        for p in readers:
            self.assertNotIn("BRIEF-MARKER", p["prompt"])
            self.assertNotIn("EXISTING-MARKER", p["prompt"])
            self.assertNotIn("STUB-QUESTION", p["prompt"])
            self.assertNotIn("key 1", p["prompt"])

    def test_fresh_teachback_has_no_transcript(self):
        fresh = self.prompts("teachback", "junior")
        same = self.prompts("teachback", "junior-same")
        self.assertTrue(fresh and same)
        self.assertTrue(all("STUB-QUESTION" not in p["prompt"] for p in fresh))
        self.assertTrue(all("STUB-QUESTION" in p["prompt"] for p in same))

    def test_author_sees_brief_and_existing_files(self):
        for p in self.prompts("draft"):
            self.assertIn("BRIEF-MARKER", p["prompt"])
            self.assertIn("EXISTING-MARKER", p["prompt"])

    def test_junior_prompt_arm_adds_the_instruction(self):
        prompt_arm = [p for p in self.prompts("draft") if p["arm"] == "junior-prompt"]
        others = [p for p in self.prompts("draft") if p["arm"] != "junior-prompt"]
        self.assertTrue(all(build.JUNIOR_PROMPT_LINE in p["prompt"] for p in prompt_arm))
        self.assertTrue(all(build.JUNIOR_PROMPT_LINE not in p["prompt"] for p in others))

    def test_models_follow_the_arm(self):
        for p in self.prompts("junior"):
            self.assertEqual(p["opts"]["model"], "sonnet")
        for p in self.prompts("draft"):
            self.assertEqual(p["opts"]["model"], "haiku")

    def test_js_render_matches_python(self):
        transcript = [{"round": 1, "questions": [{"id": "1", "text": "Who → sends?", "about": "step 2"},
                                                 {"id": "2", "text": "When?", "about": "step 3"}],
                       "answers": [{"id": "1", "tag": "checked", "text": "The API é."}]}]
        artifact = "# Plan\n\n1. Ask Δ.\n"
        self.assertEqual(build.js_render("junior", artifact, transcript), junior.build_junior_message(artifact, transcript))
        self.assertEqual(build.js_render("teachback", artifact, []), junior.build_teachback_message(artifact))

    def test_judge_batch_is_blind_and_order_swapped(self):
        out = self.tmp / "wf-output-judge.json"
        out.write_text(json.dumps({"result": self.dry["result"]}), encoding="utf-8")
        it = self.tmp / "iteration-judge"
        collect.collect(out, it)
        files = build.build_judge_batch(it, [("junior", "self-review")], self.tmp / "built-judge", "judge-test")
        data = build.embedded_data(files[0])
        self.assertEqual(len(data["pairs"]), 2 * 2)          # 2 cases x 1 author x 1 rep x 2 orders
        self.assertEqual({p["order"] for p in data["pairs"]}, {"ab", "ba"})
        dry = build.dry_run(files[0])
        for p in dry["prompts"]:
            self.assertEqual(p["role"], "judge")
            for name in ("junior", "self-review", "Junior", "SelfReview"):
                self.assertNotIn(name, p["prompt"].split("# Document A", 1)[1])
        judged = collect.collect_judgments(self.tmp / "judge-out.json", it, result=dry["result"])
        summary = score.judge_summary(it)
        row = summary[("junior", "self-review", "haiku", "natural")]
        self.assertEqual(row["pairs"], 2)
        self.assertIn("preference", row)
        self.assertIn("position_consistency", row)
        self.assertTrue(judged.is_file())

    def test_judge_batch_pairs_against_a_baseline_iteration(self):
        out = self.tmp / "wf-output-judge-b.json"
        out.write_text(json.dumps({"result": self.dry["result"]}), encoding="utf-8")
        base = self.tmp / "iteration-base"
        collect.collect(out, base)
        climb = self.tmp / "iteration-climb"
        for run in (r for r in self.dry["result"]["runs"] if r["arm"] == "junior"):
            src = base / run["case"] / "junior" / run["author"] / run["mode"] / f"run-{run['rep']}"
            dst = climb / run["case"] / "junior-v1" / run["author"] / run["mode"] / f"run-{run['rep']}"
            shutil.copytree(src, dst)
            meta = json.loads((dst / "run.json").read_text(encoding="utf-8"))
            (dst / "run.json").write_text(json.dumps(dict(meta, arm="junior-v1")), encoding="utf-8")
        files = build.build_judge_batch(climb, [("junior-v1", "self-review")], self.tmp / "built-judge-b", "cross",
                                        baseline_dir=base)
        pairs = build.embedded_data(files[0])["pairs"]
        self.assertEqual(len(pairs), 4)
        self.assertEqual({p["arm_a"] for p in pairs}, {"junior-v1"})

    def test_collect_writes_tree_and_refuses_overwrite(self):
        out = self.tmp / "wf-output.json"
        out.write_text(json.dumps({"summary": "x", "result": self.dry["result"]}), encoding="utf-8")
        it = self.tmp / "iteration-test"
        paths = collect.collect(out, it)
        self.assertEqual(len(paths), len(self.dry["result"]["runs"]))
        run = it / "fx-01" / "junior" / "haiku" / "natural" / "run-1"
        for name in ("artifact-initial.md", "artifact-final.md", "transcript.json", "report.md", "author-key.json",
                     "readers.json", "grades.json", "checks.json", "usage.json"):
            self.assertTrue((run / name).is_file(), name)
        with self.assertRaises(FileExistsError):
            collect.collect(out, it)


class VariantTest(unittest.TestCase):
    def test_variant_prompts_from_markers(self):
        base = build.load_prompts()
        free = build.junior_prompt_for(arms.Arm(name="x", review="junior", procedure="free"), base)
        self.assertNotIn("Pick one concrete request", free)
        wide = build.junior_prompt_for(arms.Arm(name="x", review="junior", batch="6-10"), base)
        self.assertIn("between 6 and 10 questions", wide)
        self.assertEqual(build.junior_prompt_for(arms.DEFAULT_JUNIOR, base), base["junior"])
        tfree = build.teachback_prompt_for(arms.Arm(name="x", review="junior", teachback_form="free"), base)
        self.assertNotIn("Follow one concrete request", tfree)

    def test_batch_limits(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _fixture_cases(Path(tmp))
            many = [arms.Arm(name=f"j{i}", review="junior") for i in range(40)]
            files = build.build_batch(["fx-01", "fx-02"], many, ["haiku", "sonnet"], 1, "natural", Path(tmp) / "b",
                                      "limits", cases_root=root)
            self.assertGreaterEqual(len(files), 3)
            for f in files:
                self.assertLessEqual(len(build.embedded_data(f)["runs"]), build.MAX_RUNS)
                self.assertLess(f.stat().st_size, build.MAX_BYTES)

    def test_skill_rev_changes_with_prompt_text(self):
        base = build.load_prompts()
        changed = dict(base, junior=base["junior"] + "\nOne more line.")
        self.assertNotEqual(arms.skill_rev(base), arms.skill_rev(changed))


class ScoreTest(unittest.TestCase):
    def _summary(self, diff, opus_gap=0.0, cheaper=True):
        rows = []
        for i in range(12):
            base = 0.5 + 0.02 * (i % 5)
            for rep in (1, 2):
                rows.append({"case": f"c{i}", "arm": "self-review", "author": "haiku", "mode": "natural", "rep": rep,
                             "comprehension": base, "cost_usd": 0.01})
                rows.append({"case": f"c{i}", "arm": "junior", "author": "haiku", "mode": "natural", "rep": rep,
                             "comprehension": base + diff, "cost_usd": 0.02 if cheaper else 0.5})
                rows.append({"case": f"c{i}", "arm": "no-review", "author": "opus", "mode": "natural", "rep": rep,
                             "comprehension": base + diff + opus_gap, "cost_usd": 0.1})
        return {"runs": rows}

    def test_paired_bootstrap_recovers_known_diff(self):
        result = score.paired(self._summary(0.12), "junior", "self-review", "haiku")
        self.assertAlmostEqual(result["mean_diff"], 0.12, places=2)
        self.assertLessEqual(result["ci95"][0], 0.12)
        self.assertGreaterEqual(result["ci95"][1], 0.12)
        self.assertEqual(result["n_cases"], 12)

    def test_decide_thresholds(self):
        self.assertTrue(score.decide(self._summary(0.10))["haiku"]["useful"])
        self.assertFalse(score.decide(self._summary(0.09))["haiku"]["useful"])
        self.assertTrue(score.decide(self._summary(0.10, opus_gap=0.05))["haiku"]["worth_it"])
        self.assertFalse(score.decide(self._summary(0.10, opus_gap=0.06))["haiku"]["worth_it"])
        self.assertFalse(score.decide(self._summary(0.10, cheaper=False))["haiku"]["worth_it"])

    def test_run_comprehension_excludes_undecided_items(self):
        grades = {"haiku-low": [{"id": "q1", "correct": True}, {"id": "q2", "correct": False}],
                  "sonnet": [{"id": "q1", "correct": True}, {"id": "q2", "correct": True}]}
        self.assertAlmostEqual(score.comprehension(grades, excluded={"q2"}), 1.0)
        self.assertAlmostEqual(score.comprehension(grades, excluded=set()), 0.75)

    def test_cost_counts_product_roles_only(self):
        usage = {"roles": {"draft": {"model": "haiku", "in": 4000, "out": 4000, "calls": 1},
                           "reader": {"model": "sonnet", "in": 400000, "out": 4000, "calls": 2}}}
        self.assertAlmostEqual(score.run_cost(usage), 1000 * 0.10 / 1e6 + 1000 * 0.50 / 1e6)


class ValidationGateTest(unittest.TestCase):
    def _rows(self, ref=0.9, implicit=0.6, padded=0.9, presentation_low=0.75):
        rows = []
        for i in range(10):
            for mode, value, low in (("null", ref, ref), ("seeded-implicit", implicit, implicit),
                                     ("padded", padded, padded), ("seeded-presentation", 0.85, presentation_low)):
                rows.append({"case": f"c{i}", "arm": "no-review", "author": "none", "mode": mode, "rep": 1,
                             "comprehension": value, "per_reader": {"haiku-low": low, "sonnet": value}})
        return rows

    def test_gates_pass_on_a_good_grader(self):
        gates = score.validation_gates({"runs": self._rows()}, agreement=0.95)
        self.assertTrue(all(g["passed"] for g in gates.values()), gates)

    def test_gates_catch_each_failure(self):
        self.assertFalse(score.validation_gates({"runs": self._rows(ref=0.8)}, 0.95)["reference_high"]["passed"])
        self.assertFalse(score.validation_gates({"runs": self._rows(implicit=0.8)}, 0.95)["implicit_lower"]["passed"])
        self.assertFalse(score.validation_gates({"runs": self._rows(padded=0.97)}, 0.95)["padding_neutral"]["passed"])
        self.assertFalse(score.validation_gates({"runs": self._rows()}, 0.85)["grader_agreement"]["passed"])
        self.assertFalse(score.validation_gates({"runs": self._rows(presentation_low=0.85)}, 0.95)
                         ["hurried_reader_separates"]["passed"])

    def test_grader_agreement_counts_items(self):
        by_model = {"sonnet": {"r": [{"id": "q1", "correct": True}, {"id": "q2", "correct": False}]},
                    "opus": {"r": [{"id": "q1", "correct": True}, {"id": "q2", "correct": True}]}}
        self.assertEqual(score.grader_agreement([by_model]), (1, 2))


class MermaidTest(unittest.TestCase):
    GOOD = "```mermaid\nflowchart TD\n  A[User] -->|login| B(API)\n  B --> C{Valid?}\n```\n"
    BAD = "```mermaid\nflowchart TD\n  A[User] -->|login B(API\n  B --> \n```\n"

    def test_heuristic_flags_broken(self):
        self.assertEqual(mermaid.heuristic_errors("flowchart TD\n  A[User] -->|login| B(API)\n"), [])
        self.assertTrue(mermaid.heuristic_errors("flowchart TD\n  A[User] -->|login B(API\n  B --> \n"))
        self.assertTrue(mermaid.heuristic_errors("not a diagram\n A-->B"))

    def test_check_flags_broken(self):
        self.assertEqual(mermaid.check(self.GOOD), [])
        self.assertTrue(mermaid.check(self.BAD))
        self.assertEqual(mermaid.check("No diagram here."), [])


if __name__ == "__main__":
    unittest.main()
