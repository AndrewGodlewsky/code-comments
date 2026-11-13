"""Tests for value_drift.py. Run from this folder: python -m unittest"""

from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

import value_drift as vd  # noqa: E402


def forms(text: str, *olds: str, unit: str | None = None) -> list[str]:
    """The forms that the patterns for olds find in one line of prose."""
    default = vd.find_unit(unit) if unit else None
    patterns = [p for raw in olds for p in vd.patterns_for(vd.parse_value(raw, default))]
    return [m.form for m in vd.find(text, patterns)]


class Repo:
    """A throwaway repository built from {relative path: text}."""

    def __init__(self, files: dict[str, str]):
        self._dir = tempfile.TemporaryDirectory()
        self.root = Path(self._dir.name)
        for rel, text in files.items():
            path = self.root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self._dir.cleanup()

    def run(self, *args: str) -> tuple[int, str]:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = vd.main([str(self.root), *args])
        return code, out.getvalue()

    def hits(self, *args: str) -> list[dict]:
        _, out = self.run(*args, "--json")
        return json.loads(out)["hits"]

    def snapshot(self) -> dict[str, tuple[int, int]]:
        return {p.relative_to(self.root).as_posix(): (p.stat().st_size, p.stat().st_mtime_ns)
                for p in self.root.rglob("*")}


class DigitTest(unittest.TestCase):
    def test_digits_are_bounded(self):
        for text in ("Keep 24 log files.", "(24)", "It is 24.", "24-hour", "24h", "$24"):
            self.assertEqual(forms(text, "24"), ["24"], text)
        for text in ("240 rows", "2.4 s", "since 2024", "24.5 s", "24,000 rows", "v24", "MAX_24",
                     "24 thousand"):
            self.assertEqual(forms(text, "24"), [], text)

    def test_thousands_separators(self):
        self.assertEqual(forms("up to 2,400 rows", "2400"), ["2,400"])
        self.assertEqual(forms("up to 2400 rows", "2,400"), ["2400"])
        self.assertEqual(forms("up to 2,400 rows", "400"), [])

    def test_decimals(self):
        self.assertEqual(forms("a factor of 2.5", "2.5"), ["2.5"])
        self.assertEqual(forms("a factor of 2.55", "2.5"), [])

    def test_dates_times_versions_and_issue_numbers_are_not_values(self):
        for text in ("merged on 2026-06-30", "starts at 02:30 nightly", "at 23:30:00", "since 1.30.2",
                     "see issue #30", "2026/06/30"):
            self.assertEqual(forms(text, "30"), [], text)
        self.assertEqual(forms("30 rows, merged 2026-06-30", "30"), ["30"])
        self.assertEqual(forms("a 30 s wait (see #30)", "30 s"), ["30 s"])
        self.assertEqual(forms("tag 2026-06-30", "2026-06-30"), ["2026-06-30"])  # text is never masked


class WordTest(unittest.TestCase):
    def test_number_words(self):
        self.assertEqual(forms("Twelve at most", "12"), ["Twelve"])
        self.assertEqual(forms("twenty-five rows", "25"), ["twenty-five"])
        self.assertEqual(forms("twenty five rows", "25"), ["twenty five"])
        self.assertEqual(forms("retries twice", "2"), ["twice"])
        self.assertEqual(forms("about a dozen workers", "12"), ["a dozen"])
        self.assertEqual(forms("twenty-four hundred rows", "2400"), ["twenty-four hundred"])
        self.assertEqual(forms("a forty-five-minute window", "45"), ["forty-five"])

    def test_part_of_a_larger_number_is_not_a_hit(self):
        self.assertEqual(forms("twenty-five rows", "20"), [])
        self.assertEqual(forms("twenty five rows", "5"), [])
        self.assertEqual(forms("nine hundred rows", "9"), [])
        self.assertEqual(forms("one hundred and twenty rows", "100"), [])
        self.assertEqual(forms("one hundred and twenty rows", "20"), [])
        self.assertEqual(forms("between two and three", "3"), ["three"])

    def test_hundreds(self):
        self.assertEqual(forms("one hundred and twenty rows", "120"), ["one hundred and twenty"])
        self.assertEqual(forms("one hundred twenty rows", "120"), ["one hundred twenty"])
        self.assertEqual(forms("a hundred rows, one hundred rows", "100"), ["a hundred", "one hundred"])

    def test_words_inside_other_words_are_not_hits(self):
        self.assertEqual(forms("often, fourteen, tension, ninety", "10", "4", "9"), [])


class UnitTest(unittest.TestCase):
    def test_seconds_as_minutes_and_hours(self):
        line = ("45 min, 45min, 45-minute, forty-five minutes, forty-five-minute, 0.75 h, 2700 s, "
                "2,700,000 ms, 45m")
        self.assertEqual(forms(line, "2700", unit="s"),
                         ["45 min", "45min", "45-minute", "forty-five minutes", "forty-five-minute",
                          "0.75 h", "2700 s", "2,700,000 ms", "45m"])

    def test_a_converted_quantity_needs_its_unit(self):
        self.assertEqual(forms("Keep 45 log files.", "2700", unit="s"), [])
        self.assertEqual(forms("45 M rows", "2700", unit="s"), [])
        self.assertEqual(forms("45 sets", "45", unit="min"), ["45"])  # the old value itself, bare

    def test_a_bare_number_with_another_unit_is_not_the_value(self):
        for text in ("kept for 7 days", "a 7-day window", "7d of logs", "7 MB", "seven days", "7 hours"):
            self.assertEqual(forms(text, "7 s"), [], text)
        self.assertEqual(forms("7 retries, 7 seconds, 7s, seven seconds", "7 s"),
                         ["7", "7 seconds", "7s", "seven seconds"])
        self.assertEqual(forms("kept for 7 days", "7"), ["7"])  # no unit given: still listed

    def test_number_words_need_a_space_or_hyphen_before_the_unit(self):
        for text, old in (("pick the ones that failed", "1 s"), ("in tens", "10 s"), ("they tend to", "10 day"),
                          ("sevens", "7 s")):
            self.assertEqual(forms(text, old), [], text)
        self.assertEqual(forms("one second, a ten-second wait", "1 s", "10 s"), ["one second", "ten-second"])

    def test_a_singular_unit_needs_a_time_word_before_it(self):
        self.assertEqual(forms("sends a second request", "1 s"), [])
        self.assertEqual(forms("allows 10,000 calls a day", "1 day"), [])
        self.assertEqual(forms("runs twice a day", "1 day"), [])
        self.assertEqual(forms("retries after a second", "1 s"), ["a second"])
        self.assertEqual(forms("runs once a day; never held longer than a minute", "1 day", "1 min"),
                         ["a day", "a minute"])

    def test_idioms(self):
        self.assertEqual(forms("half an hour, a half-hour, 30 minutes", "0.5", unit="h"),
                         ["half an hour", "half-hour", "30 minutes"])
        self.assertEqual(forms("a quarter of an hour, a quarter-hour", "15", unit="min"),
                         ["a quarter of an hour", "a quarter-hour"])
        self.assertEqual(forms("within an hour", "60", unit="min"), ["an hour"])
        self.assertEqual(forms("an hour and a half", "60", unit="min"), [])
        self.assertEqual(forms("an hourly job", "60", unit="min"), [])
        self.assertEqual(forms("an hour and a half, one and a half hours", "90", unit="min"),
                         ["an hour and a half", "one and a half hours"])

    def test_unit_written_on_the_value(self):
        self.assertEqual(forms("9 seconds, nine seconds, 9000 ms", "9 s"),
                         ["9 seconds", "nine seconds", "9000 ms"])
        self.assertEqual(forms("3000 ms", "3"), [])

    def test_sizes_read_both_ways(self):
        self.assertEqual(forms("a 64 KB buffer, or 65,536 bytes; 64 KiB", "64", unit="KiB"),
                         ["64 KB", "65,536 bytes", "64 KiB"])
        self.assertEqual(forms("a 1 MB cap, 1,000 KB, 1,000,000 bytes", "1", unit="MB"),
                         ["1 MB", "1,000 KB", "1,000,000 bytes"])

    def test_unknown_unit_on_a_value_is_text(self):
        self.assertIsNone(vd.parse_value("3x", None).amount)
        self.assertEqual(forms("a 3x speed-up", "3x"), ["3x"])

    def test_a_whole_number_and_a_half(self):
        self.assertEqual(forms("the job waits two and a half minutes", "150 s"), ["two and a half minutes"])
        self.assertEqual(forms("the job waits two and a half minutes", "2.5 min"), ["two and a half minutes"])
        self.assertEqual(forms("a two-and-a-half-minute wait", "150 s"), ["two-and-a-half-minute"])
        self.assertEqual(forms("two and a half hours", "2.5 h"), ["two and a half hours"])
        self.assertEqual(forms("seven and a half hours", "27000 s"), ["seven and a half hours"])
        self.assertEqual(forms("one and a half minutes", "90 s"), ["one and a half minutes"])
        self.assertEqual(forms("two minutes", "150 s"), [])
        self.assertEqual(forms("the job waits two and a half minutes", "2 min"), [])  # not "two"

    def test_one_letter_units_keep_their_case(self):
        for name in ("M", "S", "b"):
            self.assertIsNone(vd.find_unit(name), name)
        self.assertEqual(vd.find_unit("MINUTES").key, "min")
        self.assertEqual(vd.find_unit("kb").key, "KB")
        self.assertEqual(vd.find_unit("m").key, "min")
        self.assertIsNone(vd.parse_value("5 M", None).amount)  # matched as literal text


class TextTest(unittest.TestCase):
    def test_flags_are_bounded(self):
        self.assertEqual(forms("Use `--legacy`; app run --legacy now", "--legacy"), ["--legacy", "--legacy"])
        self.assertEqual(forms("--legacy-mode is different", "--legacy"), [])

    def test_paths_and_names(self):
        self.assertEqual(forms("[rules](../pkg/old_mod.py)", "pkg/old_mod.py"), ["pkg/old_mod.py"])
        self.assertEqual(forms("see pkg/old_mod.py.", "pkg/old_mod.py"), ["pkg/old_mod.py"])
        self.assertEqual(forms("see pkg/old_mod.pyc", "pkg/old_mod.py"), [])
        self.assertEqual(forms("see load_rows_fast", "load_rows"), [])


class ProseTest(unittest.TestCase):
    def test_python_reads_comments_and_docstrings_not_code(self):
        source = ('"""Module: workers restart after 2700 s."""\n'
                  "RESTART_S = 2700  # 2700 s between restarts\n"
                  '"""Restart interval, 2700 s."""\n'
                  "\n"
                  "def f():\n"
                  '    """First line.\n'
                  "\n"
                  "    Waits 2700 s.\n"
                  '    """\n'
                  '    return "2700 seconds"\n')
        with Repo({"app/workers.py": source}) as repo:
            found = [(h["line"], h["where"]) for h in repo.hits("--old", "2700")]
        self.assertEqual(found, [(1, "docstring"), (2, "comment"), (3, "docstring"), (8, "docstring")])

    def test_slash_comments_skip_strings(self):
        source = ('// Restarts after 2700 s.\n'
                  'const url = "http://x // 2700 s"; /* 2700 s\n'
                  ' * still 2700 s */\n')
        with Repo({"web/a.ts": source}) as repo:
            found = [(h["line"], h["text"]) for h in repo.hits("--old", "2700")]
        self.assertEqual(found, [(1, "Restarts after 2700 s."), (2, "2700 s"), (3, "still 2700 s")])

    def test_hash_comments_skip_strings(self):
        source = 'restart: 2700  # forty-five minutes\nname: "a # forty-five minutes"\n# 45 min\n'
        with Repo({"conf/app.yaml": source}) as repo:
            found = [h["line"] for h in repo.hits("--old", "2700", "--unit", "s")]
        self.assertEqual(found, [1, 3])

    def test_markdown_fenced_lines_are_labelled(self):
        source = "Use --legacy.\n```sh\napp run --legacy\n```\n"
        with Repo({"README.md": source}) as repo:
            found = [(h["line"], h["where"]) for h in repo.hits("--old=--legacy")]
        self.assertEqual(found, [(1, "doc"), (3, "fenced")])

    def test_strings_are_read_only_when_asked(self):
        source = ('"""Waits 2700 s."""\n'
                  'import argparse\n'
                  'p = argparse.ArgumentParser()\n'
                  'p.add_argument("--wait", help="Seconds to wait (default 2700).")\n'
                  'raise SystemExit("gave up after 2700 s")\n')
        with Repo({"app/cli.py": source, "web/a.ts": 'const m = "wait 2700 s"; // 2700 s\n'}) as repo:
            self.assertEqual([(h["path"], h["where"]) for h in repo.hits("--old", "2700")],
                             [("app/cli.py", "docstring"), ("web/a.ts", "comment")])
            found = [(h["path"], h["line"], h["where"]) for h in repo.hits("--old", "2700", "--strings")]
        self.assertEqual(found, [("app/cli.py", 1, "docstring"), ("app/cli.py", 4, "string"),
                                 ("app/cli.py", 5, "string"), ("web/a.ts", 1, "string"), ("web/a.ts", 1, "comment")])

    def test_a_form_wrapped_onto_the_next_line_is_found(self):
        files = {"app/jobs.py": ('"""Run the import jobs.\n\nA job that stalls for half an\n'
                                 'hour is stopped and its lock is freed.\n"""\n'
                                 "# Workers rest for a two-\n# hour window each night.\n"),
                 "docs/jobs.md": ("Workers sleep for forty-five\nminutes between runs.\n\n"
                                  "The old loader keeps a stale\ncopy of the index.\n")}
        with Repo(files) as repo:
            found = [(h["path"], h["line"], h["where"], [m["form"] for m in h["matches"]])
                     for h in repo.hits("--old", "30", "--unit", "min", "--old", "2 h", "--old", "2700 s",
                                        "--old", "stale copy")]
        self.assertEqual(found, [("app/jobs.py", 3, "docstring", ["half an hour"]),
                                 ("app/jobs.py", 6, "comment", ["two-hour"]),
                                 ("docs/jobs.md", 1, "doc", ["forty-five minutes"]),
                                 ("docs/jobs.md", 4, "doc", ["stale copy"])])

    def test_the_next_line_also_decides_the_unit(self):
        with Repo({"docs/ops.md": "Builds are kept for 7\ndays, then deleted.\n"}) as repo:
            self.assertEqual(repo.hits("--old", "7 s"), [])
            self.assertEqual([h["line"] for h in repo.hits("--old", "7 day")], [1])

    def test_no_join_across_a_blank_line_a_new_item_or_a_heading(self):
        source = ("Keep the stale\n\ncopy apart.\n\n- keep the stale\n- copy apart\n\n"
                  "## The stale\ncopy is gone.\n")
        with Repo({"docs/ops.md": source}) as repo:
            self.assertEqual(repo.hits("--old", "stale copy"), [])
        with Repo({"docs/ops.md": "- keep the stale\n  copy apart\n"}) as repo:
            self.assertEqual([h["line"] for h in repo.hits("--old", "stale copy")], [1])

    def test_other_files_are_not_read(self):
        with Repo({"data.json": '{"note": "2700 s"}', "logo.png": "2700 s"}) as repo:
            self.assertEqual(repo.hits("--old", "2700"), [])

    def test_skips_cache_folders(self):
        with Repo({"node_modules/x/README.md": "2700 s", ".git/notes.md": "2700 s"}) as repo:
            self.assertEqual(repo.hits("--old", "2700"), [])

    def test_skipped_files_and_folders_are_named(self):
        files = {"scripts/build/release.py": "# Waits 2700 s\n", "docs/dist/guide.md": "2700 s\n",
                 "node_modules/x/README.md": "2700 s\n", "docs/big.md": "2700 s\n" + "x\n" * 60}
        with Repo(files) as repo:
            (repo.root / "docs" / "latin1.md").write_bytes("Caf\xe9 waits 2700 s.\n".encode("latin-1"))
            saved = vd.MAX_BYTES
            vd.MAX_BYTES = 100
            try:
                _, out = repo.run("--old", "2700", "--json")
                _, text = repo.run("--old", "2700")
            finally:
                vd.MAX_BYTES = saved
        report = json.loads(out)
        self.assertEqual([(h["path"], h["line"]) for h in report["hits"]], [("docs/latin1.md", 1)])
        self.assertEqual(sorted(n["path"] for n in report["not_read"]),
                         ["docs/big.md", "docs/dist", "scripts/build"])  # node_modules is not named
        self.assertEqual(report["read_with_replacement"], ["docs/latin1.md"])
        self.assertIn("3 files or folders not read: ", text)
        self.assertIn("1 file not UTF-8, read with replacement characters: docs/latin1.md.", text)

    def test_terraform_comments_in_every_style(self):
        source = ('# restart after 2700 s\nlocals {\n  // restart after 2700 s\n  wait = 2700 /* 2700 s */\n'
                  '  note = "2700 s // not a comment"\n}\n')
        with Repo({"infra/main.tf": source}) as repo:
            self.assertEqual([h["line"] for h in repo.hits("--old", "2700")], [1, 3, 4])

    def test_line_numbers_after_block_comments(self):
        source = "/* one\n * two\n * three */\nconst a = 1; // 2700 s\n" + "let b = 'x'; // y\n" * 4000 + "// 2700 s\n"
        started = time.perf_counter()
        with Repo({"web/a.js": source}) as repo:
            lines = [h["line"] for h in repo.hits("--old", "2700")]
        self.assertEqual(lines, [4, 4005])
        self.assertLess(time.perf_counter() - started, 5)  # line counting is linear in file size


class HintTest(unittest.TestCase):
    def test_record_hints_from_the_path(self):
        for rel in ("CHANGELOG.md", "HISTORY", "docs/adr/0007-queue.md", "docs/reviews/2025-07-01-review.md",
                    "docs/migration-guide.md", "migrations/0001_init.py", "docs/postmortem-cache.md"):
            self.assertEqual(vd.path_hints(rel), ["record?"], rel)
        for rel in ("README.md", "docs/api.md", "app/incident_handler.py", "app/workers.py"):
            self.assertEqual(vd.path_hints(rel), [], rel)
        self.assertEqual(vd.path_hints("AGENTS.md"), ["instructions?"])
        self.assertEqual(vd.path_hints("pkg/CLAUDE.md"), ["instructions?"])

    def test_states_new(self):
        with Repo({"CHANGELOG.md": "- Raised from 3 to 5 workers.\n- Runs three workers.\n"}) as repo:
            hints = [h["hints"] for h in repo.hits("--old", "3", "--new", "5")]
        self.assertEqual(hints, [["record?", "states new"], ["record?"]])


class CliTest(unittest.TestCase):
    def test_exit_status(self):
        with Repo({"README.md": "Keeps three copies.\n"}) as repo:
            self.assertEqual(repo.run("--old", "3")[0], 0)  # hits are output, not a failure
            self.assertEqual(repo.run("--old", "3", "--check")[0], 1)
            self.assertEqual(repo.run("--old", "5", "--check")[0], 0)
            with contextlib.redirect_stderr(io.StringIO()):
                for bad in (["--old", "3", "--unit", "parsec"], [], ["--old", "3", "--near", "("],
                            ["--old", "5", "--unit", "M"]):
                    with self.assertRaises(SystemExit) as raised:
                        repo.run(*bad)
                    self.assertEqual(raised.exception.code, 2)

    def test_near_keeps_hits_beside_a_subject_word(self):
        files = {"app/store.py": ('"""Store blobs.\n\nEach blob is written to three replicas,\nthen it is acked.\n'
                                  'Three regions share one bucket.\n"""\n'),
                 "docs/ops.md": "Replicas: three.\n\nKeep three copies of the log.\n"}
        with Repo(files) as repo:
            self.assertEqual(len(repo.hits("--old", "3")), 4)
            found = [(h["path"], h["line"]) for h in repo.hits("--old", "3", "--near", "replica|shard")]
        self.assertEqual(found, [("app/store.py", 3), ("docs/ops.md", 1)])

    def test_text_output(self):
        with Repo({"docs/ops.md": "Workers restart every 45 min.\n"}) as repo:
            _, out = repo.run("--old", "2700", "--unit", "s", "--new", "3600")
        self.assertIn("old 2700 s = 2700000 ms = 45 min = 0.75 h", out)
        self.assertIn("new 3600 s = 3600000 ms = 60 min = 1 h", out)
        self.assertIn('docs/ops.md:1: doc: "45 min" = 45 min = 2700 s: Workers restart every 45 min.', out)

    def test_writes_nothing(self):
        files = {"app/a.py": "# 2700 s\nX = 2700\n", "docs/b.md": "45 min\n", "CHANGELOG.md": "2700 s\n"}
        with Repo(files) as repo:
            before = repo.snapshot()
            repo.run("--old", "2700", "--unit", "s")
            repo.run("--old", "2700", "--json")
            self.assertEqual(repo.snapshot(), before)

    def test_skips_its_own_folder(self):
        with Repo({"skills/drift/SKILL.md": "45 min\n", "docs/b.md": "45 min\n"}) as repo:
            saved = vd.SELF_DIR
            vd.SELF_DIR = (repo.root / "skills" / "drift").resolve()
            try:
                self.assertEqual([h["path"] for h in repo.hits("--old", "45")], ["docs/b.md"])
                with contextlib.redirect_stdout(io.StringIO()):
                    code = vd.main([str(vd.SELF_DIR), "--old", "45", "--check"])
                self.assertEqual(code, 1)  # scanned when it is the root itself
            finally:
                vd.SELF_DIR = saved


if __name__ == "__main__":
    unittest.main()
