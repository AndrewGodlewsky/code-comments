"""Checks that the Claude Code plugin stays a faithful copy of its sources.

The plugin ships copies, not links, because a plugin is installed by copying its
directory. These tests are what stop the copies drifting from the lean variant and
the repository's stale-reference lint.
"""

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "code-comments"
sys.path.insert(0, str(ROOT / "scripts"))

import lint_skills  # noqa: E402


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


class PluginSyncTest(unittest.TestCase):
    def test_skill_matches_lean_variant(self):
        self.assertEqual(
            _text(PLUGIN / "skills" / "code-comments" / "SKILL.md"),
            _text(ROOT / "skill-variants" / "lean" / "code-comments" / "SKILL.md"),
            "Edit skill-variants/lean and copy it into the plugin.",
        )

    def test_stale_refs_matches_repository_script(self):
        self.assertEqual(
            _text(PLUGIN / "scripts" / "stale_refs.py"),
            _text(ROOT / "scripts" / "stale_refs.py"),
            "Edit scripts/stale_refs.py and copy it into the plugin.",
        )

    def test_plugin_skill_passes_lint(self):
        directory = PLUGIN / "skills" / "code-comments"
        problems = lint_skills.lint_skill(directory)
        problems += lint_skills.leaked(directory, lint_skills.case_shingles())
        self.assertEqual(problems, [])


class PluginManifestTest(unittest.TestCase):
    def test_manifest_and_marketplace_agree(self):
        manifest = json.loads(_text(PLUGIN / ".claude-plugin" / "plugin.json"))
        market = json.loads(_text(ROOT / ".claude-plugin" / "marketplace.json"))
        self.assertEqual(manifest["name"], "code-comments")
        entries = {p["name"]: p for p in market["plugins"]}
        self.assertIn(manifest["name"], entries)
        source = entries[manifest["name"]]["source"]
        self.assertEqual((ROOT / source).resolve(), PLUGIN.resolve())

    def test_command_uses_plugin_root(self):
        command = _text(PLUGIN / "commands" / "stale-refs.md")
        self.assertIn("${CLAUDE_PLUGIN_ROOT}/scripts/stale_refs.py", command)
        self.assertTrue((PLUGIN / "scripts" / "stale_refs.py").is_file())


if __name__ == "__main__":
    unittest.main()
