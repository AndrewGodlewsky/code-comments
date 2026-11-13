"""Checks the junior-dev plugin's packaging (plugins/junior-dev, #52).

The skill tells the main agent which helper commands to run, so a command named in SKILL.md
that the helper does not have would strand a weaker model mid-loop. The leakage check keeps
the skill and the junior's prompts from copying the eval's case text, which would let the
hill climb teach to the test.
"""

import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "junior-dev"
SKILL = PLUGIN / "skills" / "junior-dev"
HELPER = PLUGIN / "scripts" / "junior.py"

_SPEC = importlib.util.spec_from_file_location("lint_skills_jd", ROOT / "scripts" / "lint_skills.py")
lint_skills = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(lint_skills)


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class JuniorDevPluginTest(unittest.TestCase):
    def test_plugin_manifest(self):
        manifest = json.loads(_text(PLUGIN / ".claude-plugin" / "plugin.json"))
        self.assertEqual(manifest["name"], "junior-dev")
        self.assertTrue(manifest.get("version"))
        self.assertTrue(manifest.get("description"))

    def test_marketplace_lists_both_plugins(self):
        market = json.loads(_text(ROOT / ".claude-plugin" / "marketplace.json"))
        entries = {p["name"]: p for p in market["plugins"]}
        self.assertEqual(set(entries), {"code-comments", "junior-dev"})
        self.assertEqual((ROOT / entries["junior-dev"]["source"]).resolve(), PLUGIN.resolve())

    def test_skill_passes_lint(self):
        self.assertEqual(lint_skills.lint_skill_dir(SKILL, portable=False), [])

    def test_relaxed_lint_keeps_format_rules(self):
        # portable=False drops only the host-specific rules (a plugin skill may name
        # ${CLAUDE_PLUGIN_ROOT}); a wrong name is still a problem.
        with tempfile.TemporaryDirectory() as tmp:
            skill = Path(tmp) / "some-skill"
            skill.mkdir()
            (skill / "SKILL.md").write_text("---\nname: other-name\ndescription: x\n---\nSee C:\\Users\\me\\file.\n",
                                            encoding="utf-8")
            strict = lint_skills.lint_skill(skill)
            relaxed = lint_skills.lint_skill(skill, portable=False)
        self.assertTrue(any("absolute Windows path" in p for p in strict))
        self.assertFalse(any("absolute Windows path" in p for p in relaxed))
        self.assertTrue(any("must equal directory name" in p for p in relaxed))

    def test_skill_commands_exist(self):
        named = set(re.findall(r"junior\.py\"?\s+([a-z]+)", _text(SKILL / "SKILL.md")))
        self.assertTrue(named, "SKILL.md names no helper commands")
        usage = subprocess.run([sys.executable, str(HELPER), "-h"], capture_output=True, text=True,
                               encoding="utf-8").stdout
        available = set(re.search(r"\{([a-z,]+)\}", usage).group(1).split(","))
        self.assertLessEqual(named, available)
        self.assertEqual(available, {"start", "ask", "answer", "teachback", "verdict", "report"})

    def test_skill_uses_plugin_root(self):
        self.assertIn('${CLAUDE_PLUGIN_ROOT}/scripts/junior.py', _text(SKILL / "SKILL.md"))

    def test_prompts_do_not_leak_cases(self):
        self.assertIn(ROOT / "evaluation/junior_dev/cases", lint_skills.CASES)
        self.assertEqual(lint_skills.leaked(SKILL, lint_skills.case_shingles()), [])


if __name__ == "__main__":
    unittest.main()
