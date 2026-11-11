"""Checks the incubator's shared eval harness and every incubator skill's grader.

Each incubator skill's references must pass every check and each unchanged input must
fail at least one, or a case cannot tell a good run from one that did nothing. Each
skill must also pass the repository's skill linter. The harness mechanics are tested on
a tiny synthetic skill built in a temporary folder.
"""

import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

_ROOT = Path(__file__).resolve().parents[1]
_SPEC = importlib.util.spec_from_file_location("incubator_harness", _ROOT / "incubator" / "harness.py")
harness = importlib.util.module_from_spec(_SPEC)
sys.modules["incubator_harness"] = harness
_SPEC.loader.exec_module(harness)
gradelib = harness.gradelib


class IncubatorSkillsTest(unittest.TestCase):
    def test_every_skill_self_test_passes(self):
        for skill in harness.skills():
            with self.subTest(skill=skill):
                self.assertEqual(harness.self_test(skill), [])

    def test_every_skill_lints_clean(self):
        for skill in harness.skills():
            with self.subTest(skill=skill):
                self.assertEqual(harness.lint(skill), [])


_GRADE = '''
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from gradelib import constant, kept, reply, has_match

def limit_is_five(out, orig):
    value = constant(out / "app.py", "LIMIT")
    return value == 5, f"LIMIT = {value!r}"

def comment_kept(out, orig):
    return kept(out, {"app.py": ["# The vendor allows ten calls a second."]})

def reply_says_done(out, orig):
    return has_match(r"done", reply(out))

CHECKS = {"raise-limit": [limit_is_five, comment_kept, reply_says_done]}
'''


def _write(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


class HarnessTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.home = Path(self._tmp.name) / "incubator"
        self._old_here = harness.HERE
        harness.HERE = self.home
        base = self.home / "toy"
        _write(base / "skill" / "toy" / "SKILL.md", "---\nname: toy\ndescription: A toy skill.\n---\n\n# Toy\n")
        _write(base / "eval" / "arms.json", json.dumps({"reminder": "Keep it tidy."}))
        _write(base / "eval" / "grade.py", _GRADE)
        case = base / "eval" / "cases" / "raise-limit"
        _write(case / "prompt.md", "---\nmax_turns: 5\n---\n\nRaise LIMIT to 5.\n")
        _write(case / "case.yaml", "name: raise-limit\n")
        _write(case / "place-files.sh", "cp -R files/. .\n")
        for i, text in enumerate(["LIMIT is 5.", "The vendor comment is kept.", "The reply says done."], 1):
            _write(case / "graders" / f"0{i}-check.md", f"---\ntype: llm\n---\n\n{text}\n")
        source = "# The vendor allows ten calls a second.\nLIMIT = 3\n"
        _write(case / "files" / "app.py", source)
        _write(base / "eval" / "references" / "raise-limit" / "app.py", source.replace("3", "5"))
        _write(base / "eval" / "references" / "raise-limit" / "RESPONSE.md", "Done: LIMIT is 5.\n")

    def tearDown(self):
        harness.HERE = self._old_here
        self._tmp.cleanup()

    def test_self_test_passes_and_catches_a_broken_reference(self):
        self.assertEqual(harness.self_test("toy"), [])
        _write(self.home / "toy" / "eval" / "references" / "raise-limit" / "app.py", "LIMIT = 5\n")
        problems = harness.self_test("toy")
        self.assertTrue(any("reference fails" in p for p in problems), problems)

    def test_prepare_then_grade(self):
        entries = harness.prepare("toy", "it-1", ["with_skill", "reminder", "without_skill"], 2, None, False)
        self.assertEqual(len(entries), 6)
        by_arm = {e["arm"]: e["prompt"] for e in entries}
        self.assertIn("skill-snapshot/toy/SKILL.md", by_arm["with_skill"])
        self.assertIn("Keep it tidy.", by_arm["reminder"])
        self.assertNotIn("SKILL.md", by_arm["without_skill"])
        self.assertNotIn("Keep it tidy.", by_arm["without_skill"])
        # One with-skill run does the task well; the rest do nothing.
        good = Path(entries[0]["outputs"])
        _write(good / "app.py", "# The vendor allows ten calls a second.\nLIMIT = 5\n")
        _write(good / "RESPONSE.md", "Done.\n")
        bench = harness.grade_iteration("toy", "it-1")
        self.assertEqual(bench["arms"]["with_skill"]["checks_passed"], 3 + 1)
        self.assertEqual(bench["arms"]["without_skill"]["no_reply"], 2)
        run = good.parent
        self.assertIn("+LIMIT = 5", (run / "changes.diff").read_text(encoding="utf-8"))
        self.assertTrue((run / "RESPONSE.md").is_file())
        with self.assertRaises(SystemExit):
            harness.prepare("toy", "it-1", ["without_skill"], 1, None, False)

    def test_override_is_recorded(self):
        entries = harness.prepare("toy", "it-1", ["without_skill"], 1, None, False)
        run = Path(entries[0]["outputs"]).parent
        text = harness.statements("toy", "raise-limit")[2]
        _write(run / "overrides.json", json.dumps({text: {"passed": True, "evidence": "ruled by hand"}}))
        bench = harness.grade_iteration("toy", "it-1")
        self.assertEqual(bench["runs"][0]["passed"], 2)
        grading = json.loads((run / "grading.json").read_text(encoding="utf-8"))
        self.assertIn("ruled by hand", grading["expectations"][2]["evidence"])

    def test_shipped_skill_arm_reads_the_shipped_skill(self):
        entries = harness.prepare("toy", "it-1", ["shipped_skill"], 1, None, False)
        self.assertIn("skill-snapshot/code-comments/SKILL.md", entries[0]["prompt"])
        snapshot = self.home / "toy" / "eval" / "iterations" / "it-1" / "skill-snapshot" / "code-comments"
        self.assertEqual((snapshot / "SKILL.md").read_text(encoding="utf-8"),
                         (harness.SHIPPED / "SKILL.md").read_text(encoding="utf-8"))
        with self.assertRaises(SystemExit):
            harness.prepare("toy", "it-1", ["nope"], 1, None, False)

    def test_focus_is_reported(self):
        _write(self.home / "toy" / "eval" / "cases" / "raise-limit" / "graders" / "03-check.md",
               "---\ntype: llm\nfocus: reply\n---\n\nThe reply says done.\n")
        self.assertEqual([g["focus"] for g in harness.graders("toy", "raise-limit")], ["core", "core", "reply"])
        harness.prepare("toy", "it-1", ["without_skill"], 1, None, False)
        bench = harness.grade_iteration("toy", "it-1")
        self.assertEqual(bench["arms"]["without_skill"]["by_focus"]["reply"], [0, 1])
        self.assertEqual(bench["arms"]["without_skill"]["by_focus"]["core"], [1, 2])

    def test_held_out_split(self):
        self.assertEqual(harness.case_names("toy", "train"), ["raise-limit"])
        _write(self.home / "toy" / "eval" / "cases" / "raise-limit" / "case.yaml",
               "name: raise-limit\nheld_out: true\n")
        self.assertEqual(harness.case_names("toy", "train"), [])
        self.assertEqual(harness.case_names("toy", "held-out"), ["raise-limit"])
        self.assertEqual(harness.case_names("toy"), ["raise-limit"])

    def test_snapshot_refuses_a_changed_skill(self):
        harness.prepare("toy", "it-1", ["with_skill"], 1, None, False)
        _write(self.home / "toy" / "skill" / "toy" / "SKILL.md", "---\nname: toy\ndescription: Changed.\n---\n")
        with self.assertRaises(SystemExit):
            harness.prepare("toy", "it-1", ["with_skill"], 1, None, False, first_run=2)

    def test_verify_reads(self):
        entries = harness.prepare("toy", "it-1", ["with_skill"], 2, None, False)
        transcripts = Path(self._tmp.name) / "transcripts"
        for i, entry in enumerate(entries):
            events = [{"type": "user", "message": {"content": entry["prompt"]}}]
            if i == 0:
                skill_md = entry["prompt"].split("read ")[1].split(" in full")[0]
                events.append({"type": "assistant", "message": {"content": [
                    {"type": "tool_use", "name": "Read", "input": {"file_path": skill_md}}]}})
            events.append({"type": "assistant", "message": {"content": [
                {"type": "tool_use", "name": "Edit", "input": {"file_path": entry["outputs"] + "/app.py"}}]}})
            _write(transcripts / f"agent-{i}.jsonl", "\n".join(json.dumps(e) for e in events) + "\n")
        result = harness.verify_reads("toy", "it-1", [transcripts])
        self.assertEqual(result["checked"], 2)
        self.assertEqual(result["skipped_skill"], [entries[1]["id"]])


class GradelibTest(unittest.TestCase):
    def test_hidden_tests_run_on_a_copy(self):
        with tempfile.TemporaryDirectory() as tmp:
            out, hidden = Path(tmp, "out"), Path(tmp, "hidden")
            _write(out / "pkg" / "__init__.py", "")
            _write(out / "pkg" / "calc.py", "def double(x):\n    return x * 2\n")
            _write(hidden / "hidden_tests" / "test_calc.py",
                   "import unittest\nfrom pkg.calc import double\n\n"
                   "class T(unittest.TestCase):\n    def test_double(self):\n        self.assertEqual(double(3), 6)\n")
            ok, evidence = gradelib.run_hidden_tests(out, hidden)
            self.assertTrue(ok, evidence)
            self.assertFalse((out / "hidden_tests").exists())
            _write(out / "pkg" / "calc.py", "def double(x):\n    return x + 2\n")
            ok, evidence = gradelib.run_hidden_tests(out, hidden)
            self.assertFalse(ok)
            self.assertIn("test_double", evidence)

    def test_slash_comments_skip_strings(self):
        source = 'const url = "http://x"; // real comment\n/** Block\n * line two */\nlet a = 1;\n'
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "a.ts"
            path.write_text(source, encoding="utf-8")
            self.assertEqual(gradelib.prose(path), ["real comment", "Block", "line two"])
            shape = gradelib.code_shape(path)
            self.assertIn('"http://x"', shape)
            self.assertNotIn("real", shape)

    def test_rewrapped_comment_is_not_lost(self):
        with tempfile.TemporaryDirectory() as tmp:
            orig, out = Path(tmp, "orig"), Path(tmp, "out")
            orig.mkdir(), out.mkdir()
            (orig / "a.py").write_text("# Rows are rounded first, so the total\n"
                                       "# can differ by a cent.\nX = 1\n", encoding="utf-8")
            (out / "a.py").write_text("# Rows are rounded first,\n"
                                      "# so the total can differ by a cent.\nX = 1\n", encoding="utf-8")
            self.assertEqual(gradelib.lost_prose(out, orig), {})
            (out / "a.py").write_text("# Rows are rounded first.\nX = 1\n", encoding="utf-8")
            self.assertIn("a.py", gradelib.lost_prose(out, orig))


if __name__ == "__main__":
    unittest.main()
