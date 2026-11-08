"""Offline tests for the narwhals pilot runner (pilot.py) and scorer (pilot_inner.py), #41.

Nothing here calls Docker or a model: only the pure helpers, the budget, the commands the
runner would run, and the summary and decision rules over fixture results.
"""

import json
from pathlib import Path
import tempfile
import textwrap
import unittest

from evaluation.skill_eval import pilot, pilot_inner


def junit_xml(cases: list[tuple[str, str, str]]) -> str:
    """(name, file, status) -> a minimal xunit1 report."""
    body = []
    for name, file, status in cases:
        child = {"passed": "", "failed": "<failure message='x'/>", "error": "<error message='x'/>",
                 "skipped": "<skipped type='pytest.skip'/>", "xfail": "<skipped type='pytest.xfail'/>"}[status]
        body.append(f"<testcase classname='{file[:-3].replace('/', '.')}' name='{name}' file='{file}'>{child}</testcase>")
    return f"<testsuites><testsuite>{''.join(body)}</testsuite></testsuites>"


class TaskAndPromptTests(unittest.TestCase):
    def test_parse_tasks_drops_upstream_line(self):
        text = textwrap.dedent("""\
            # Title

            ### Step 1

            (Upstream: x#1.)

            Do the first thing.

            - detail

            ### Step 2

            Do the second.
            """)
        self.assertEqual(pilot.parse_tasks(text), {1: "Do the first thing.\n\n- detail", 2: "Do the second."})

    def test_real_tasks_file_has_six_steps(self):
        tasks = pilot.parse_tasks(pilot.TASKS.read_text(encoding="utf-8"))
        self.assertEqual(sorted(tasks), [1, 2, 3, 4, 5, 6])
        for statement in tasks.values():
            self.assertTrue(statement)
            self.assertNotIn("(Upstream:", statement)

    def test_base_prompt_adds_instruction_only_for_instruct_arm(self):
        plain = pilot.base_prompt("haiku-plain", "Task.", "pandas,polars[eager]")
        instruct = pilot.base_prompt("haiku-instruct", "Task.", "pandas,polars[eager]")
        self.assertTrue(plain.startswith("Task."))
        self.assertIn("--constructors=pandas,polars[eager]", plain)
        self.assertNotIn(pilot.INSTRUCT, plain)
        self.assertTrue(instruct.endswith(pilot.INSTRUCT))
        self.assertEqual(pilot.base_prompt("haiku-skill", "Task.", "pandas"),
                         pilot.base_prompt("sonnet-plain", "Task.", "pandas"))

    def test_review_prompt_truncates_long_diffs(self):
        short = pilot.review_prompt("T", "+x")
        self.assertIn("```diff\n+x\n```", short)
        self.assertIn(pilot.CHECKLIST, short)
        long = pilot.review_prompt("T", "+" * (pilot.REVIEW_DIFF_CHARS + 10))
        self.assertIn("[... diff truncated", long)
        self.assertLess(len(long), pilot.REVIEW_DIFF_CHARS + 2000)

    def test_revision_prompt_keeps_task_and_findings(self):
        text = pilot.revision_prompt("PROMPT", "FINDINGS")
        self.assertTrue(text.startswith("PROMPT"))
        self.assertTrue(text.endswith("FINDINGS"))

    def test_flagged_bash(self):
        events = [
            {"type": "assistant", "message": {"content": [
                {"type": "tool_use", "name": "Bash", "input": {"command": "pip install foo"}},
                {"type": "tool_use", "name": "Bash", "input": {"command": "python -m pytest"}},
                {"type": "tool_use", "name": "Bash", "input": {"command": "git fetch https://github.com/x"}},
                {"type": "tool_use", "name": "Read", "input": {"command": "curl x"}}]}},
            {"type": "user", "message": {"content": "curl"}},
        ]
        self.assertEqual(pilot.flagged_bash(events), ["pip install foo", "git fetch https://github.com/x"])

    def test_string_messages_do_not_crash_the_parser(self):
        # The full run (#43) crashed on a stream-json event whose `message` was a plain string.
        from evaluation.skill_eval import live
        lines = [
            {"type": "system", "subtype": "init", "tools": [], "plugins": [], "skills": []},
            {"type": "system", "subtype": "status", "message": "retrying after an API error"},
            {"type": "assistant", "message": "not a dict"},
            "a bare JSON string",
            {"type": "assistant", "message": {"model": pilot.HAIKU, "content": [
                {"type": "tool_use", "name": "Bash", "input": {"command": "uv pip install x"}}]}},
            {"type": "result", "subtype": "success", "total_cost_usd": 0.01, "num_turns": 1, "result": "done"},
        ]
        stdout = "\n".join(json.dumps(line) for line in lines)
        result = live.parse_session(stdout, "", 0, model=pilot.HAIKU, label="x", prompt="P",
                                    skill_name=None, wall=1.0)
        self.assertEqual(result["tool_calls"], 1)
        self.assertEqual(pilot.flagged_bash(result["events"]), ["uv pip install x"])


class JunitTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)

    def junit(self, cases) -> dict:
        path = Path(self.dir.name) / "r.xml"
        path.write_text(junit_xml(cases), encoding="utf-8")
        return pilot.parse_junit(path)

    def test_parse_statuses(self):
        result = self.junit([("a", "tests/test_a.py", "passed"), ("b", "tests/test_a.py", "failed"),
                             ("c", "tests/test_a.py", "error"), ("d", "tests/test_a.py", "skipped"),
                             ("e", "tests/test_a.py", "xfail")])
        self.assertEqual({k.split("::")[1]: v[0] for k, v in result.items()},
                         {"a": "passed", "b": "failed", "c": "error", "d": "skipped", "e": "xfail"})
        self.assertEqual(result["tests.test_a::a"], ("passed", "tests/test_a.py"))

    def test_test_modules_excludes_support_files(self):
        hidden = ["tests/test_a.py", "tests/conftest.py", "tests/b_test.py", "tests/utils.py",
                  "packages/test-plugin/test_x.py", "tests/data.csv"]
        self.assertEqual(pilot.test_modules(hidden), {"tests/test_a.py", "tests/b_test.py"})

    def test_step_passes(self):
        hidden = ["tests/test_a.py", "tests/conftest.py"]
        ok = self.junit([("a", "tests/test_a.py", "passed"), ("b", "tests/test_a.py", "xfail"),
                         ("z", "tests/test_other.py", "failed")])
        self.assertTrue(pilot.step_passes(ok, hidden))
        bad = self.junit([("a", "tests/test_a.py", "passed"), ("b", "tests/test_a.py", "error")])
        self.assertFalse(pilot.step_passes(bad, hidden))
        skipped_only = self.junit([("a", "tests/test_a.py", "skipped")])
        self.assertFalse(pilot.step_passes(skipped_only, hidden))
        self.assertFalse(pilot.step_passes(None, hidden))
        self.assertFalse(pilot.step_passes({}, hidden))

    def test_regressions_ignore_hidden_files_and_new_failures(self):
        before = self.junit([("a", "tests/test_a.py", "passed"), ("b", "tests/test_b.py", "passed"),
                             ("c", "tests/test_b.py", "failed"), ("h", "tests/test_h.py", "passed"),
                             ("gone", "tests/test_b.py", "passed")])
        after = self.junit([("a", "tests/test_a.py", "passed"), ("b", "tests/test_b.py", "failed"),
                            ("c", "tests/test_b.py", "failed"), ("h", "tests/test_h.py", "failed")])
        self.assertEqual(pilot.regressions(before, after, ["tests/test_h.py"]),
                         ["tests.test_b::b", "tests.test_b::gone"])
        self.assertEqual(pilot.regressions(None, after, []), [])
        self.assertEqual(pilot.regressions(before, None, ["tests/test_h.py"]),
                         ["tests.test_a::a", "tests.test_b::b", "tests.test_b::gone"])


class BudgetTests(unittest.TestCase):
    def test_reserve_and_settle(self):
        budget = pilot.Budget(cap=10.0, per_session=3.0)
        first = budget.reserve(2)
        self.assertEqual(first, 6.0)
        self.assertIsNone(budget.reserve(2))  # 6 reserved + 6 > 10
        self.assertEqual(budget.reserve(1), 3.0)
        budget.settle(first, 1.5)
        self.assertEqual((budget.spent, budget.reserved), (1.5, 3.0))
        self.assertEqual(budget.reserve(1), 3.0)  # 1.5 + 3 + 3 <= 10
        self.assertIsNone(budget.reserve(1))

    def test_prior_spend_counts(self):
        budget = pilot.Budget(cap=5.0, per_session=2.0, spent=2.0)
        self.assertIsNone(budget.reserve(2))
        self.assertEqual(budget.reserve(1), 2.0)


class CommandTests(unittest.TestCase):
    def test_inner_command_is_offline_and_unprivileged(self):
        command = pilot.inner_command(Path("out"), "abc", "vol", ["score", "--step", "1"])
        self.assertEqual(command[:4], ["docker", "run", "--rm", "--network"])
        self.assertEqual(command[4], "none")
        self.assertIn("1000:1000", command)
        self.assertIn(f"{pilot.volume('abc', 'oracle-chain')}:/oracle:ro", command)
        self.assertTrue(any(part.endswith(":/harness:ro") for part in command))
        self.assertEqual(command[-3:], ["score", "--step", "1"])
        root = pilot.inner_command(Path("out"), "abc", "vol", ["init-oracle"], root=True, oracle=False)
        self.assertNotIn("--user", root)
        self.assertFalse(any(part.endswith(":/oracle:ro") for part in root))

    def test_session_command_passes_credential_by_name_only(self):
        command = pilot.session_command("n", "vol", "PROMPT", model=pilot.HAIKU, tools=pilot.IMPLEMENT_TOOLS,
                                        max_budget=2.0, credential="api-key")
        self.assertIn("ANTHROPIC_API_KEY", command)
        self.assertFalse(any("=" in part and part.startswith("ANTHROPIC_API_KEY") for part in command))
        self.assertIn("vol:/work/narwhals", command)
        self.assertEqual(command[command.index("--allowedTools") + 1], "Bash")
        self.assertNotIn("--plugin-dir", command)
        self.assertEqual(pilot.redact(command)[command.index("-p") + 1], "<prompt>")
        self.assertNotIn("PROMPT", pilot.redact(command))

    def test_review_session_is_read_only_without_bash(self):
        command = pilot.session_command("n", "vol", "P", model=pilot.SONNET, tools=pilot.REVIEW_TOOLS,
                                        max_budget=1.0, credential="oauth", read_only=True)
        self.assertIn("vol:/work/narwhals:ro", command)
        self.assertNotIn("--allowedTools", command)
        self.assertIn("CLAUDE_CODE_OAUTH_TOKEN", command)

    def test_sessions_disable_package_indexes_and_every_arm_is_told(self):
        command = pilot.session_command("n", "vol", "P", model=pilot.HAIKU, tools=pilot.IMPLEMENT_TOOLS,
                                        max_budget=1.0, credential="oauth")
        image = command.index(pilot.AGENT_IMAGE)
        for setting in pilot.NO_INSTALL_ENV:  # docker options must come before the image name
            self.assertLess(command.index(setting), image)
            self.assertEqual(command[command.index(setting) - 1], "-e")
        for arm in pilot.LIVE_ARMS:
            self.assertIn(pilot.ENVIRONMENT, pilot.base_prompt(arm, "TASK", "pandas"))

    def test_skill_session_mounts_plugin(self):
        command = pilot.session_command("n", "vol", "P", model=pilot.HAIKU, tools=pilot.IMPLEMENT_TOOLS,
                                        max_budget=1.0, credential="api-key", plugin_root=Path("plug"))
        self.assertEqual(command[command.index("--plugin-dir") + 1], f"/plugin/{pilot.live.PLUGIN}")
        self.assertTrue(any(part.endswith(":/plugin:ro") for part in command))

    def test_parse_steps(self):
        self.assertEqual(pilot.parse_steps("1-6"), [1, 2, 3, 4, 5, 6])
        self.assertEqual(pilot.parse_steps("2,4"), [2, 4])
        self.assertEqual(pilot.parse_steps("3"), [3])

    def test_harness_sha_is_stable_and_covers_files(self):
        self.assertEqual(pilot.harness_sha(), pilot.harness_sha())
        self.assertNotEqual(pilot.harness_sha(), pilot.harness_sha(pilot.HARNESS_PATHS[:-1]))

    def test_main_refuses_live_without_cap(self):
        with self.assertRaises(SystemExit):
            pilot.main(["run", "--out", "x", "--arms", "haiku-plain", "--live", "--credential", "api-key"])
        with self.assertRaises(SystemExit):
            pilot.main(["run", "--out", "x", "--arms", "nope"])


class ScorerTests(unittest.TestCase):
    def test_diff_paths_and_hidden_files(self):
        diff = ("diff --git a/src/narwhals/a.py b/src/narwhals/a.py\n+x\n"
                "diff --git a/tests/test_a.py b/tests/test_a.py\n+y\n"
                "diff --git a/src/narwhals/a.py b/src/narwhals/a.py\n"
                "diff --git a/packages/test-plugin/p.py b/packages/test-plugin/p.py\n")
        paths = pilot_inner.diff_paths(diff)
        self.assertEqual(paths, ["src/narwhals/a.py", "tests/test_a.py", "packages/test-plugin/p.py"])
        self.assertEqual(pilot_inner.hidden_files(paths), ["tests/test_a.py", "packages/test-plugin/p.py"])

    def test_chain_has_six_hidden_test_sets(self):
        diffs = pilot_inner.chain_diffs()
        self.assertEqual(len(diffs), 6)
        for diff in diffs:
            hidden = pilot_inner.hidden_files(pilot_inner.diff_paths(diff.read_text(encoding="utf-8")))
            self.assertTrue(pilot.test_modules(hidden), diff.name)

    def test_churn_ignores_docstrings_and_formatting(self):
        old = {"a.py": 'def f(x):\n    """Doc."""\n    return x\n'}
        reformatted = {"a.py": 'def f( x ):\n    """Another doc."""\n    return (x)\n'}
        self.assertEqual(pilot_inner.churn_between(old, reformatted), (0, []))
        changed = {"a.py": "def f(x):\n    return x + 1\n"}
        self.assertEqual(pilot_inner.churn_between(old, changed), (2, []))

    def test_churn_counts_new_and_deleted_files(self):
        self.assertEqual(pilot_inner.churn_between({}, {"b.py": "x = 1\ny = 2\n"}), (2, []))
        self.assertEqual(pilot_inner.churn_between({"b.py": "x = 1\n"}, {}), (1, []))

    def test_churn_reports_unparsable_files_and_counts_raw_lines(self):
        churn, bad = pilot_inner.churn_between({"a.py": "x = 1\n"}, {"a.py": "x = (\n"})
        self.assertEqual((churn, bad), (2, ["a.py"]))

    def test_duplication(self):
        block = "".join(f"v{i} = {i}\n" for i in range(6))
        self.assertEqual(pilot_inner.duplication({"a.py": block}), 0)
        self.assertEqual(pilot_inner.duplication({"a.py": block, "b.py": block}), 1)
        self.assertEqual(pilot_inner.duplication({"a.py": block, "b.py": block, "c.py": "x = (\n"}), 1)
        self.assertEqual(pilot_inner.duplication({"a.py": block * 2}), 1)  # only the first and last windows match

    def test_complexity(self):
        source = textwrap.dedent("""\
            X = 1 if True else 2

            def f(x):
                if x and x > 1 or x < -1:
                    return [y for y in x if y if y > 0]
                for _ in x:
                    pass
                try:
                    pass
                except ValueError:
                    pass
                return lambda: 1 if x else 2

            class C:
                def m(self):
                    while True:
                        break
            """)
        # f: 1 + if 1 + BoolOps (and: 1, or: 1) + comprehension 1+2 + for 1 + except 1 + IfExp 1 = 10
        # C.m: 1 + while 1 = 2; the module-level IfExp is outside any function.
        self.assertEqual(pilot_inner.complexity({"a.py": source}), 12)
        self.assertEqual(pilot_inner.complexity({"a.py": source, "bad.py": "def ("}), 12)

    def test_read_constructors_and_test_command(self):
        constructors = pilot_inner.read_constructors()
        self.assertIn("pandas", constructors.split(","))
        self.assertNotIn("'", constructors)
        command = pilot_inner.test_command(constructors)
        self.assertEqual(command[-1], f"--constructors={constructors}")


def record(arm, rep, step, *, churn=0, lint=(), harness_failed=False, cost=0.0, dup=0, cx=0, hidden=None):
    return {"arm": arm, "rep": rep, "step": step, "label": f"{arm}-r{rep}-s{step}", "churn": churn,
            "lint": list(lint), "harness_failed": harness_failed, "unparsable": [], "duplication": dup,
            "complexity": cx, "hidden": hidden if hidden is not None else ([] if step == 0 else [f"tests/test_{step}.py"]),
            "sessions": [{"cost_usd": cost, "flagged_bash": []}]}


class SummaryTests(unittest.TestCase):
    """summarise() over two steps: the oracle passes, null fails, and a live arm regresses."""

    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.out = Path(self.dir.name)
        (self.out / "junit").mkdir()
        (self.out / "oracle.json").write_text(json.dumps({"steps": [
            {"step": 0, "churn": 0, "duplication": 3, "complexity": 100},
            {"step": 1, "churn": 20, "duplication": 3, "complexity": 104},
            {"step": 6, "churn": 5, "duplication": 4, "complexity": 110}]}), encoding="utf-8")
        records = []
        base = [("old", "tests/test_old.py", "passed")]
        for arm, step1_status, old_status, churn in (("oracle", "passed", "passed", 20),
                                                     ("null", "failed", "passed", 0),
                                                     ("haiku-plain", "passed", "failed", 45)):
            self.write_junit(f"{arm}-r0-s0", base)
            self.write_junit(f"{arm}-r0-s1", [("old", "tests/test_old.py", old_status),
                                               ("new", "tests/test_1.py", step1_status)])
            records.append(record(arm, 0, 0, dup=3, cx=100))
            records.append(record(arm, 0, 1, churn=churn, cost=0.5 if arm == "haiku-plain" else 0.0,
                                  lint=[{"ref": "gone"}] if arm == "haiku-plain" else []))
        (self.out / "results.jsonl").write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")

    def write_junit(self, label, cases):
        (self.out / "junit" / f"{label}.xml").write_text(junit_xml(cases), encoding="utf-8")

    def test_summary(self):
        summary = pilot.summarise(self.out)
        arms = summary["arms"]
        self.assertEqual(summary["reference"], {"duplication_growth": 1, "complexity_growth": 10,
                                                "pr_churn": {1: 20, 6: 5}})
        self.assertEqual((arms["oracle"]["passing"], arms["oracle"]["E"]), (1, 0))
        self.assertEqual((arms["null"]["failed"], arms["null"]["E"]), (1, 1))
        hp = arms["haiku-plain"]
        self.assertEqual((hp["passing"], hp["regression_events"], hp["regression_tests"]), (1, 1, 1))
        self.assertEqual((hp["excess_churn"], hp["high_churn"], hp["stale_refs"]), (25, 1, 1))
        self.assertEqual(hp["E"], 2)
        self.assertEqual(hp["cost_per_passing_step"], 0.5)
        self.assertFalse(summary["decision"]["complete"])
        checks = summary["self_test"]
        self.assertTrue(checks["oracle_passes_every_step"])
        self.assertTrue(checks["oracle_zero_excess_churn"])
        self.assertEqual(checks["null_fails_steps"], [1])
        self.assertTrue(checks["null_zero_churn"])

    def test_missing_junit_counts_as_failure(self):
        (self.out / "junit" / "oracle-r0-s1.xml").unlink()
        self.assertEqual(pilot.summarise(self.out)["arms"]["oracle"]["failed"], 1)


def totals(E, failed=0, regression_events=0, high_churn=0, cost=None):
    return {"E": E, "failed": failed, "regression_events": regression_events, "high_churn": high_churn,
            "cost_per_passing_step": cost}


class DecisionTests(unittest.TestCase):
    def arms(self, **overrides):
        arms = {"haiku-plain": totals(10, 4, 3, 3, 0.2), "sonnet-plain": totals(4, 2, 1, 1, 1.0),
                "haiku-instruct": totals(9, 3, 3, 3, 0.2), "haiku-skill": totals(9, 3, 3, 3, 0.2),
                "haiku-review": totals(6, 2, 2, 2, 0.5)}
        arms.update(overrides)
        return arms

    def test_incomplete(self):
        self.assertEqual(pilot.decide({"oracle": totals(0)}), {"complete": False, "E": {"oracle": 0}})

    def test_rule1_haiku_within_noise(self):
        decision = pilot.decide(self.arms(**{"haiku-plain": totals(6, 3, 2, 1, 0.2)}))
        self.assertTrue(decision["rule1"])
        self.assertTrue(decision["outcome"].startswith("1:"))

    def test_rule1_fails_if_one_component_gap_is_large(self):
        decision = pilot.decide(self.arms(**{"haiku-plain": totals(6, 4, 1, 1, 0.2)}))
        self.assertFalse(decision["rule1"])

    def test_rule2_comments_beat_instruction(self):
        decision = pilot.decide(self.arms(**{"haiku-skill": totals(5, 3, 1, 1, 0.2)}))
        self.assertTrue(decision["rule2"])
        self.assertTrue(decision["outcome"].startswith("2:"))
        self.assertFalse(decision["stop_comments_research"])

    def test_rule3_review_closes_gap_cheaply(self):
        decision = pilot.decide(self.arms())
        self.assertEqual(decision["gap"], 6)
        self.assertTrue(decision["rule3"])  # 6 <= 4 + 3 and 0.5 < 0.6
        self.assertTrue(decision["stop_comments_research"])

    def test_rule3_needs_cost_advantage(self):
        decision = pilot.decide(self.arms(**{"haiku-review": totals(6, 2, 2, 2, 0.7)}))
        self.assertFalse(decision["rule3"])
        self.assertTrue(decision["outcome"].startswith("4:"))


class CredentialFileTests(unittest.TestCase):
    NAME = "CLAUDE_CODE_OAUTH_TOKEN"
    SECRET = "sk-ant-oat01-not-a-real-token"

    def load(self, text: str, encoding: str = "utf-8") -> str:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / ".env.pilot"
            path.write_text(text, encoding=encoding)
            return pilot.load_credential_file(path, self.NAME)

    def test_reads_value_skipping_comments_and_quotes(self):
        text = f"# paste below\nOTHER=x\n{self.NAME}=\"{self.SECRET}\"\n"
        self.assertEqual(self.load(text), self.SECRET)

    def test_tolerates_powershell_bom(self):
        self.assertEqual(self.load(f"{self.NAME}={self.SECRET}", encoding="utf-8-sig"), self.SECRET)

    def test_errors_never_contain_the_value(self):
        for text in (f"{self.NAME}=\n", f"OTHER={self.SECRET}\n"):
            with self.assertRaises(ValueError) as caught:
                self.load(text)
            self.assertNotIn(self.SECRET, str(caught.exception))

    def test_missing_file(self):
        with self.assertRaises(ValueError):
            pilot.load_credential_file(Path("does-not-exist.env"), self.NAME)


if __name__ == "__main__":
    unittest.main()
