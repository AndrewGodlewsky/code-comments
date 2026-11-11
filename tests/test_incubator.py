"""Checks the incubator's shared eval harness and every incubator skill's grader.

Each incubator skill's references must pass every check and each unchanged input must
fail at least one, or a case cannot tell a good run from one that did nothing. Each
skill must also pass the repository's skill linter. The harness mechanics are tested on
a tiny synthetic skill built in a temporary folder.

This module also loads change-drift-sweep's script tests (test_value_drift.py), so the
documented suite runs them. That skill's graded variants (eval/test_grade.py) include
held-out variants and are run separately; see incubator/README.md.
"""

import contextlib
import importlib.util
import io
import json
import shutil
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
_VALUE_DRIFT_TESTS = (_ROOT / "incubator" / "change-drift-sweep" / "skill" / "change-drift-sweep" / "scripts"
                      / "test_value_drift.py")


def load_tests(loader, standard_tests, pattern):
    spec = importlib.util.spec_from_file_location("incubator_test_value_drift", _VALUE_DRIFT_TESTS)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    standard_tests.addTests(loader.loadTestsFromModule(module))
    return standard_tests


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
        self.home = Path(self._tmp.name) / "incubator home"  # a space, as in "C:/Users/First Last"
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

    def test_verify_reads_counts_copied_calls_once(self):
        entry = harness.prepare("toy", "it-1", ["with_skill"], 1, None, False)[0]
        skill_md = entry["prompt"].split("read ")[1].split(" in full")[0]
        read = {"type": "tool_use", "id": "toolu_1", "name": "Read", "input": {"file_path": skill_md}}
        edit = {"type": "tool_use", "id": "toolu_2", "name": "Edit", "input": {"file_path": entry["outputs"] + "/app.py"}}
        events = [{"type": "user", "message": {"content": entry["prompt"]}},
                  {"type": "assistant", "message": {"content": [read]}},
                  {"type": "assistant", "message": {"content": [edit]}},
                  # A later record that repeats both earlier calls, as real transcripts do.
                  {"type": "assistant", "message": {"content": [read, edit]}}]
        transcripts = Path(self._tmp.name) / "transcripts"
        _write(transcripts / "agent-0.jsonl", "\n".join(json.dumps(e) for e in events) + "\n")
        run = harness.verify_reads("toy", "it-1", [transcripts])["runs"][entry["id"]]
        self.assertEqual(run["tool_calls"], 2)
        self.assertTrue(run["read_before_edit"])

    # --------------------------------------------------- grading refusals

    def _iteration(self) -> Path:
        return self.home / "toy" / "eval" / "iterations" / "it-1"

    def test_grade_refuses_a_run_without_outputs(self):
        entries = harness.prepare("toy", "it-1", ["without_skill"], 2, None, False)
        harness.grade_iteration("toy", "it-1")
        before = (self._iteration() / "benchmark.json").read_bytes()
        shutil.rmtree(entries[1]["outputs"])  # as a clone has it: outputs/ is gitignored
        with self.assertRaises(SystemExit) as raised:
            harness.grade_iteration("toy", "it-1", force=True)
        self.assertIn("no outputs/", str(raised.exception))
        self.assertEqual((self._iteration() / "benchmark.json").read_bytes(), before)

    def test_grade_refuses_without_runs_json(self):
        harness.prepare("toy", "it-1", ["without_skill"], 1, None, False)
        (self._iteration() / "runs.json").unlink()
        with self.assertRaises(SystemExit):
            harness.grade_iteration("toy", "it-1", force=True)
        self.assertFalse((self._iteration() / "benchmark.json").exists())

    def test_grade_refuses_changed_inputs_unless_forced(self):
        harness.prepare("toy", "it-1", ["without_skill"], 1, None, False)
        _write(self.home / "toy" / "eval" / "cases" / "raise-limit" / "files" / "app.py", "LIMIT = 4\n")
        with self.assertRaises(SystemExit) as raised:
            harness.grade_iteration("toy", "it-1")
        self.assertIn("files/ or hidden tests", str(raised.exception))
        self.assertFalse((self._iteration() / "benchmark.json").exists())
        with contextlib.redirect_stderr(io.StringIO()):
            bench = harness.grade_iteration("toy", "it-1", force=True)
        self.assertTrue(bench["forced"])

    def test_grade_refuses_changed_checks_unless_forced(self):
        harness.prepare("toy", "it-1", ["without_skill"], 1, None, False)
        first = harness.grade_iteration("toy", "it-1")
        self.assertIn("eval/grade.py", first["fingerprints"]["checks"])
        harness.grade_iteration("toy", "it-1")  # the same checks: regrading is allowed
        grade_py = self.home / "toy" / "eval" / "grade.py"
        _write(grade_py, grade_py.read_text(encoding="utf-8") + "\n# a grader fix\n")
        with self.assertRaises(SystemExit) as raised:
            harness.grade_iteration("toy", "it-1")
        self.assertIn("eval/grade.py", str(raised.exception))
        with contextlib.redirect_stderr(io.StringIO()):
            bench = harness.grade_iteration("toy", "it-1", force=True)
        self.assertEqual(bench["previous_fingerprints"], first["fingerprints"])
        self.assertNotEqual(bench["fingerprints"]["checks"]["eval/grade.py"],
                            first["fingerprints"]["checks"]["eval/grade.py"])
        again = harness.grade_iteration("toy", "it-1")  # a plain regrade keeps that record
        self.assertEqual(again["previous_fingerprints"], first["fingerprints"])

    def test_grade_refuses_a_benchmark_without_fingerprints(self):
        harness.prepare("toy", "it-1", ["without_skill"], 1, None, False)
        bench = self._iteration() / "benchmark.json"
        bench.write_text(json.dumps({"arms": {}}), encoding="utf-8")  # graded before fingerprints
        with self.assertRaises(SystemExit):
            harness.grade_iteration("toy", "it-1")

    def test_fingerprint_ignores_line_endings(self):
        before = harness.inputs_fingerprint("toy", "raise-limit")
        app = self.home / "toy" / "eval" / "cases" / "raise-limit" / "files" / "app.py"
        app.write_bytes(app.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))
        self.assertEqual(harness.inputs_fingerprint("toy", "raise-limit"), before)

    # ------------------------------------------------------------ rulings

    def test_a_ruling_that_matches_no_grader_stops_grading(self):
        entries = harness.prepare("toy", "it-1", ["without_skill"], 1, None, False)
        run = Path(entries[0]["outputs"]).parent
        _write(run / "overrides.json", json.dumps({"A reworded check.": {"passed": True, "evidence": "x"}}))
        with self.assertRaises(SystemExit) as raised:
            harness.grade_iteration("toy", "it-1")
        self.assertIn("matches no grader text", str(raised.exception))
        self.assertFalse((run / "grading.json").exists())
        self.assertTrue(any("matches no grader text" in p for p in harness.self_test("toy")))

    def test_a_ruling_must_be_a_json_boolean(self):
        entries = harness.prepare("toy", "it-1", ["without_skill"], 1, None, False)
        run = Path(entries[0]["outputs"]).parent
        text = harness.statements("toy", "raise-limit")[2]
        _write(run / "overrides.json", json.dumps({text: {"passed": "false", "evidence": "x"}}))
        with self.assertRaises(SystemExit):
            harness.grade_iteration("toy", "it-1")
        self.assertTrue(any("JSON true or false" in p for p in harness.self_test("toy")))

    # ---------------------------------------------------------- metadata

    def test_a_focus_typo_stops(self):
        _write(self.home / "toy" / "eval" / "cases" / "raise-limit" / "graders" / "03-check.md",
               "---\ntype: llm\nfocus: preservaton\n---\n\nThe reply says done.\n")
        with self.assertRaises(SystemExit):
            harness.graders("toy", "raise-limit")

    def test_an_unclosed_frontmatter_names_the_file(self):
        _write(self.home / "toy" / "eval" / "cases" / "raise-limit" / "graders" / "03-check.md",
               "---\ntype: llm\n\nThe reply says done.\n")
        with self.assertRaises(SystemExit) as raised:
            harness.graders("toy", "raise-limit")
        self.assertIn("03-check.md", str(raised.exception))

    def test_held_out_values(self):
        yaml = self.home / "toy" / "eval" / "cases" / "raise-limit" / "case.yaml"
        for value, held in (("True", True), ("yes", True), ("true  # final pair", True), ("false", False)):
            _write(yaml, f"name: raise-limit\nheld_out: {value}\n")
            self.assertEqual(harness.is_held_out("toy", "raise-limit"), held, value)
        _write(yaml, "name: raise-limit\nheld_out: maybe\n")
        with self.assertRaises(SystemExit):
            harness.case_names("toy", "train")
        self.assertTrue(any("held_out must be" in p for p in harness.self_test("toy")))

    def test_snapshot_notices_a_deleted_file(self):
        script = self.home / "toy" / "skill" / "toy" / "scripts" / "x.py"
        _write(script, "X = 1\n")
        harness.prepare("toy", "it-1", ["with_skill"], 1, None, False)
        # Bytecode a run writes into the snapshot does not count as a change.
        _write(self._iteration() / "skill-snapshot" / "toy" / "scripts" / "__pycache__" / "x.pyc", "")
        harness.prepare("toy", "it-1", ["with_skill"], 1, None, False, first_run=2)
        script.unlink()
        with self.assertRaises(SystemExit):
            harness.prepare("toy", "it-1", ["with_skill"], 1, None, False, first_run=3)

    # ------------------------------------------------------- other paths

    def test_prepare_fresh_replaces_outputs(self):
        entry = harness.prepare("toy", "it-1", ["without_skill"], 1, None, False)[0]
        _write(Path(entry["outputs"]) / "stray.txt", "left over\n")
        harness.prepare("toy", "it-1", ["without_skill"], 1, None, True)
        self.assertFalse((Path(entry["outputs"]) / "stray.txt").exists())
        runs = json.loads((self._iteration() / "runs.json").read_text(encoding="utf-8"))
        self.assertEqual([e["id"] for e in runs], [entry["id"]])

    def test_summary_and_main(self):
        harness.prepare("toy", "it-1", ["without_skill"], 1, None, False)
        harness.grade_iteration("toy", "it-1")
        bench = self._iteration() / "benchmark.json"
        data = json.loads(bench.read_text(encoding="utf-8"))
        data["arms"]["reminder"] = {"runs": 0, "mean_pass_rate": None, "checks_passed": 0, "checks_total": 0}
        bench.write_text(json.dumps(data), encoding="utf-8")
        table = harness.summary("toy", ["it-1"])
        self.assertIn("| it-1 | without_skill | 1 | 33.3% | 1/3 |", table)
        self.assertIn("| it-1 | reminder | 0 | n/a | 0/0 |", table)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(harness.main(["self-test", "toy"]), 0)
            self.assertEqual(harness.main(["summary", "toy", "it-1"]), 0)
        self.assertIn("self-test ok", out.getvalue())
        self.assertIn("| it-1 | without_skill |", out.getvalue())

    def test_lint_finds_case_text_in_a_script(self):
        case = self.home / "toy" / "eval" / "cases" / "raise-limit" / "files"
        _write(case / "notes.md", "The nightly export waits for the warehouse lock before it starts.\n")
        _write(case / "walk.py", "for node in ast.walk(tree):\n    if isinstance(node, ast.Name):\n        pass\n")
        script = self.home / "toy" / "skill" / "toy" / "scripts" / "check.py"
        _write(script, "import ast\n\ndef names(tree):\n    for node in ast.walk(tree):\n"
                       "        if isinstance(node, ast.Name):\n            yield node.id\n")
        self.assertEqual(harness.lint("toy"), [])  # a shared code idiom is not a copy
        _write(script, 'NOTE = "the nightly export waits for the warehouse lock before it starts"\n')
        problems = harness.lint("toy")
        self.assertTrue(any("scripts/check.py: shares eval case text" in p for p in problems), problems)

    def test_verify_reads_own_snapshot_partial_reads_and_bad_lines(self):
        entries = harness.prepare("toy", "it-1", ["with_skill", "shipped_skill"], 1, None, False)
        own = {e["arm"]: e["prompt"].split("read ")[1].split(" in full")[0] for e in entries}
        self.assertIn(" ", entries[0]["outputs"])  # the path has a space and is still found
        transcripts = Path(self._tmp.name) / "transcripts"
        # with_skill reads the other arm's snapshot only; shipped_skill reads its own in a chunk.
        reads = {"with_skill": {"file_path": own["shipped_skill"]},
                 "shipped_skill": {"file_path": own["shipped_skill"], "limit": 20}}
        for i, entry in enumerate(entries):
            lines = [json.dumps({"type": "user", "message": {"content": entry["prompt"]}}),
                     json.dumps({"type": "progress", "message": None}),
                     json.dumps({"type": "assistant", "message": {"content": [
                         {"type": "tool_use", "id": f"t{i}a", "name": "Read", "input": reads[entry["arm"]]},
                         {"type": "tool_use", "id": f"t{i}b", "name": "Edit",
                          "input": {"file_path": entry["outputs"] + "/app.py"}}]}}),
                     '{"type": "assistant", "mess']  # a transcript still being written
            _write(transcripts / f"agent-{i}.jsonl", "\n".join(lines) + "\n")
        result = harness.verify_reads("toy", "it-1", [transcripts])
        ids = {e["arm"]: e["id"] for e in entries}
        self.assertEqual(result["checked"], 2)
        self.assertEqual(result["skipped_skill"], [ids["with_skill"]])
        self.assertEqual(result["partial_reads"], [ids["shipped_skill"]])
        self.assertEqual(result["transcripts_with_unparsable_lines"], {"agent-0.jsonl": 1, "agent-1.jsonl": 1})


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


    def test_fixture_tests_and_snippets_run_on_a_copy(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp, "out")
            _write(root / "tests" / "__init__.py", "")
            _write(root / "tests" / "test_w.py", "import unittest\n\nclass T(unittest.TestCase):\n"
                   "    def test_w(self):\n        open('out.csv', 'w').write('x')\n")
            ok, evidence = gradelib.run_tests(root)
            self.assertTrue(ok, evidence)
            value, error = gradelib.run_snippet(root, "open('snip.txt', 'w').write('x'); print(7)")
            self.assertEqual(value, 7, error)
            self.assertEqual(sorted(p.name for p in root.iterdir()), ["tests"])

    def test_code_shape_refuses_other_file_types_and_tells_broken_files_apart(self):
        with tempfile.TemporaryDirectory() as tmp:
            orig, out = Path(tmp, "orig"), Path(tmp, "out")
            _write(orig / "a.py", "def f(:\n    return 1\n")
            _write(out / "a.py", "def f(:\n    return 2\n")
            self.assertFalse(gradelib.same_code(out, orig, ["a.py"])[0])
            _write(out / "a.py", "def f(:\n    return 1\n")
            self.assertTrue(gradelib.same_code(out, orig, ["a.py"])[0])
            _write(orig / "a.sh", "echo keep\n")
            with self.assertRaises(ValueError):
                gradelib.code_shape(orig / "a.sh")


if __name__ == "__main__":
    unittest.main()
