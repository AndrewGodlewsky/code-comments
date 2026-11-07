from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import check_distillation  # noqa: E402
import lint_skills  # noqa: E402


PASSAGES = """# Source
<a id="src-001"></a>
## src-001 — First
```text
Comments should describe things that are not obvious
from the code itself.
```
<a id="src-002"></a>
## src-002 — Second
```text
Keep documentation close to the code it describes.
```
"""

GOOD_SKILL = """---
name: code-comments
description: Keep explanatory comments accurate while editing code. Use when changing code whose reasons are not obvious.
---

# Code Comments

Explain why, not what. See [examples](references/examples.md).
"""


class CheckDistillationTests(unittest.TestCase):
    def run_check(self, citation_line):
        with tempfile.TemporaryDirectory(dir=ROOT) as temporary:
            base = Path(temporary)
            (base / "src").mkdir()
            (base / "src" / "passages.md").write_text(PASSAGES, encoding="utf-8")
            (base / "out").mkdir()
            note = base / "out" / "group.md"
            note.write_text(citation_line + "\n", encoding="utf-8")
            return check_distillation.check([note])

    def test_verbatim_quote_across_line_break_and_ellipsis_passes(self):
        checked, problems = self.run_check(
            '- [src-001](../src/passages.md#src-001) — supports — "describe things that are not obvious ... the code itself" — evidence: expert-opinion')
        self.assertEqual((checked, problems), (1, []))

    def test_quote_from_a_different_passage_fails(self):
        _, problems = self.run_check(
            '- [src-001](../src/passages.md#src-001) — supports — "Keep documentation close to the code" — evidence: expert-opinion')
        self.assertEqual(len(problems), 1)
        self.assertIn("quote not found", problems[0])

    def test_unknown_passage_id_fails(self):
        _, problems = self.run_check('- [src-404](../src/passages.md#src-404) — supports — "anything" — evidence: x')
        self.assertIn("passage id not found", problems[0])

    def test_curly_quotes_and_dashes_are_normalized(self):
        checked, problems = self.run_check(
            '- [src-002](../src/passages.md#src-002) — supports — “Keep documentation close to the code” — evidence: x')
        self.assertEqual((checked, problems), (1, []))


class LintSkillTests(unittest.TestCase):
    def make(self, text, extra=None):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        skill = Path(temporary.name) / "code-comments"
        (skill / "references").mkdir(parents=True)
        (skill / "SKILL.md").write_text(text, encoding="utf-8")
        (skill / "references" / "examples.md").write_text("# Examples\n", encoding="utf-8")
        for name, content in (extra or {}).items():
            (skill / name).write_text(content, encoding="utf-8")
        return skill

    def test_portable_skill_passes(self):
        self.assertEqual(lint_skills.lint_skill(self.make(GOOD_SKILL)), [])

    def test_name_must_match_directory(self):
        problems = lint_skills.lint_skill(self.make(GOOD_SKILL.replace("name: code-comments", "name: comments")))
        self.assertTrue(any("must equal directory name" in p for p in problems))

    def test_missing_frontmatter_and_long_description(self):
        self.assertTrue(lint_skills.lint_skill(self.make("# No frontmatter\n")))
        long = GOOD_SKILL.replace("Keep explanatory", "x" * 1100)
        self.assertTrue(any("1..1024" in p for p in lint_skills.lint_skill(self.make(long))))

    def test_non_portable_content_is_flagged(self):
        for snippet, label in (("Install to C:\\Users\\me", "Windows"), ("Copy to ~/.claude/skills", "home"),
                               ("Run !`git diff`", "injection"), ("[x](../outside.md)", "resolve inside")):
            with self.subTest(label=label):
                problems = lint_skills.lint_skill(self.make(GOOD_SKILL + "\n" + snippet + "\n"))
                self.assertTrue(problems, label)

    def test_body_line_limit(self):
        problems = lint_skills.lint_skill(self.make(GOOD_SKILL + "line\n" * 501))
        self.assertTrue(any("max 500" in p for p in problems))

    def test_case_text_leakage_is_detected(self):
        shingles = {tuple("the payment gateway delivers webhooks at least once so".split()[:8])}
        skill = self.make(GOOD_SKILL + "\nThe payment gateway delivers webhooks at least once, so dedupe.\n")
        self.assertTrue(lint_skills.leaked(skill, shingles))
        self.assertFalse(lint_skills.leaked(self.make(GOOD_SKILL), shingles))


if __name__ == "__main__":
    unittest.main()
