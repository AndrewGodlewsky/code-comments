"""Checks the Junior-dev case set (evaluation/junior_dev/cases, #52).

A case is only fair if a clear artifact can answer its quiz, if the brief does not hand the
quiz to the author, and if no case family straddles the development and held-out sets (a
climb tuned on one auth case must not be "confirmed" on another).
"""

import json
from pathlib import Path
import tempfile
import unittest

from evaluation.junior_dev import cases


def _quiz(n_brief=4, n_design=4):
    items = [{"id": f"q{i + 1}", "kind": "brief", "question": f"What happens at step {i}?", "key": "x", "why": "y"}
             for i in range(n_brief)]
    items += [{"id": f"q{n_brief + i + 1}", "kind": "design", "question": f"Where is state {i} kept?", "key": "db",
               "why": "y"} for i in range(n_design)]
    return items


def _case(cid="c-01", family="fam", split="dev", quiz=None, fmt="prose-steps"):
    return {"slot": {"id": cid, "split": split, "family": family, "complexity": "simple", "format": fmt,
                     "existing": False, "undecided": False, "topic": "t"},
            "case": {"brief": "Write a numbered plan for the thing.", "existing_files": [], "undecided": [],
                     "quiz": quiz if quiz is not None else _quiz(),
                     "requirements": [{"id": f"r{i}", "text": "must"} for i in range(1, 5)],
                     "reference_artifact": "1. Do it.\n", "seeded_presentation": "do it", "seeded_implicit": "it"},
            "notes": [], "rewritten": False}


class CasesTest(unittest.TestCase):
    def test_committed_cases_validate(self):
        self.assertTrue(cases.load(), "no committed cases")
        self.assertEqual(cases.validate(), [])

    def test_committed_split_sizes(self):
        splits = [c.split for c in cases.load()]
        self.assertGreaterEqual(splits.count("dev"), 10)
        self.assertGreaterEqual(splits.count("heldout"), 6)

    def test_write_then_load_round_trips(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "out.json"
            c = _case(fmt="mermaid-flowchart")
            c["case"]["existing_files"] = [{"path": "existing/app.py", "content": "print('hi')\n"}]
            c["case"]["reference_artifact"] = "```mermaid\nflowchart TD\n A-->B\n```\n"
            out.write_text(json.dumps({"cases": [c], "dropped": []}), encoding="utf-8")
            root = Path(tmp) / "cases"
            cases.write(out, root=root)
            [loaded] = cases.load(root=root)
            self.assertEqual(loaded.id, "c-01")
            self.assertEqual(loaded.existing, {"existing/app.py": "print('hi')\n"})
            self.assertEqual(len(loaded.quiz), 8)
            self.assertTrue((root / "c-01" / "visible" / "brief.md").is_file())
            self.assertTrue((root / "c-01" / "private" / "quiz.json").is_file())
            self.assertEqual(cases.validate(root=root), [])

    def test_broken_fixture_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "out.json"
            short = _quiz(n_brief=3, n_design=4)            # 7 items
            nokey = _quiz()
            nokey[0]["key"] = ""
            out.write_text(json.dumps({"cases": [_case("a-01", quiz=short), _case("b-01", quiz=nokey)]}),
                           encoding="utf-8")
            root = Path(tmp) / "cases"
            cases.write(out, root=root)
            dup = root / "b-01-copy"
            (dup / "private").mkdir(parents=True)
            (dup / "visible").mkdir()
            for part in ("private", "visible"):
                for f in (root / "b-01" / part).iterdir():
                    (dup / part / f.name).write_text(f.read_text(encoding="utf-8"), encoding="utf-8")
            problems = "\n".join(cases.validate(root=root))
            self.assertIn("a-01: quiz has 7 items", problems)
            self.assertIn("b-01: q1 has no key", problems)
            self.assertIn("duplicate case id b-01", problems)

    def test_splits_disjoint_by_family(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "out.json"
            out.write_text(json.dumps({"cases": [_case("a-01", "auth", "dev"), _case("a-02", "auth", "heldout")]}),
                           encoding="utf-8")
            root = Path(tmp) / "cases"
            cases.write(out, root=root)
            self.assertTrue(any("family auth is in both" in p for p in cases.validate(root=root)))

    def test_quiz_not_in_brief(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "out.json"
            c = _case()
            c["case"]["brief"] = "Plan it. Also: where is state 0 kept?"
            out.write_text(json.dumps({"cases": [c]}), encoding="utf-8")
            root = Path(tmp) / "cases"
            cases.write(out, root=root)
            self.assertTrue(any("appears in the brief" in p for p in cases.validate(root=root)))

    def test_mermaid_format_needs_a_mermaid_reference(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "out.json"
            out.write_text(json.dumps({"cases": [_case(fmt="mermaid-sequence")]}), encoding="utf-8")
            root = Path(tmp) / "cases"
            cases.write(out, root=root)
            self.assertTrue(any("no mermaid block" in p for p in cases.validate(root=root)))

    def test_existing_paths_stay_inside(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "out.json"
            c = _case()
            c["case"]["existing_files"] = [{"path": "../escape.py", "content": "x"}]
            out.write_text(json.dumps({"cases": [c]}), encoding="utf-8")
            with self.assertRaises(ValueError):
                cases.write(out, root=Path(tmp) / "cases")


if __name__ == "__main__":
    unittest.main()
