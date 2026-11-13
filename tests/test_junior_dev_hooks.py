"""Checks the junior-dev trigger hooks (plugins/junior-dev/scripts/hooks.py and classify.py, #52).

The hooks exist because skills rarely load on their own (Haiku loaded the code-comments skill
in 0 of 18 runs). They must fire on a real plan or diagram, stay quiet on everything else,
and never loop: the review's own edits, the loop's scratch files and a nested junior session
must not trigger them again, and the Stop hook must let the agent stop.
"""

import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1] / "plugins" / "junior-dev" / "scripts"


def _load(name, filename):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


classify = _load("junior_dev_classify", "classify.py")
hooks = _load("junior_dev_hooks", "hooks.py")
junior = sys.modules.get("junior") or _load("junior", "junior.py")

MERMAID = """# Checkout flow

```mermaid
flowchart TD
  Cart[Cart service] -->|place order| Orders[Order service]
  Orders -->|reserve| Inventory
  Orders -->|charge| Payments
  Payments -->|result| Orders
  Inventory -->|reserved| Orders
```
"""
PLAN = "# Rollout plan\n\n" + "\n".join(
    f"{i}. Step {i}: move the next batch of tenants to the new billing engine, check the "
    f"invoices against the old engine, and keep the flag ready to roll back." for i in range(1, 6)) + "\n"
CHECKLIST = "- [ ] a\n- [ ] b\n- [ ] c\n- [ ] d\n- [ ] e\n"
README = "# Ledger\n\n" + ("Ledger is a small library for keeping accounts. It is written in Python. " * 12) + "\n"


class ClassifyTest(unittest.TestCase):
    def test_mermaid_fence_with_four_edges_is_artifact(self):
        ok, reason = classify.is_artifact("docs/checkout.md", MERMAID)
        self.assertTrue(ok)
        self.assertIn("diagram", reason)

    def test_plan_path_with_numbered_steps_is_artifact(self):
        self.assertTrue(classify.is_artifact("docs/plans/billing.md", PLAN)[0])

    def test_five_line_checklist_is_tiny(self):
        self.assertEqual(classify.is_artifact("docs/plans/todo.md", CHECKLIST), (False, "tiny"))

    def test_prose_readme_is_not_artifact(self):
        self.assertFalse(classify.is_artifact("README.md", README)[0])

    def test_python_file_is_not_artifact(self):
        self.assertFalse(classify.is_artifact("src/plan.py", PLAN)[0])

    def test_mmd_file_with_four_edges_is_artifact(self):
        text = "sequenceDiagram\n  A->>B: one\n  B->>C: two\n  C-->>B: three\n  B-->>A: four\n"
        self.assertTrue(classify.is_artifact("docs/login.mmd", text)[0])

    def test_small_mermaid_is_tiny(self):
        self.assertEqual(classify.is_artifact("docs/x.md", "```mermaid\nflowchart LR\n A-->B\n```\n"), (False, "tiny"))


class HookTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.project = Path(self._tmp.name) / "my project"
        (self.project / "docs").mkdir(parents=True)
        self.root = self.project / ".junior-dev"
        self.plan = self.project / "docs" / "checkout.md"
        self.plan.write_text(MERMAID, encoding="utf-8")
        self._env = mock.patch.dict(os.environ, {}, clear=False)
        self._env.start()
        os.environ.pop("JUNIOR_DEV_NESTED", None)

    def tearDown(self):
        self._env.stop()
        self._tmp.cleanup()

    def write_event(self, path, tool="Write"):
        return {"hook_event_name": "PostToolUse", "tool_name": tool, "cwd": str(self.project),
                "session_id": "s1", "tool_input": {"file_path": str(path)}}

    def stop_event(self, active=False):
        return {"hook_event_name": "Stop", "cwd": str(self.project), "session_id": "s1", "stop_hook_active": active}

    def registry(self):
        return junior.load_registry(self.root)

    def test_post_write_records_pending_and_reminds(self):
        out = hooks.post_write(self.write_event(self.plan), self.root)
        context = out["hookSpecificOutput"]["additionalContext"]
        self.assertEqual(out["hookSpecificOutput"]["hookEventName"], "PostToolUse")
        self.assertIn("checkout.md", context)
        self.assertIn("junior-dev", context)
        self.assertEqual(self.registry()[str(self.plan.resolve())]["status"], "pending")
        self.assertEqual((self.root / ".gitignore").read_text(encoding="utf-8").strip(), "*")

    def test_post_write_skips_when_nested(self):
        os.environ["JUNIOR_DEV_NESTED"] = "1"
        self.assertIsNone(hooks.post_write(self.write_event(self.plan), self.root))
        self.assertEqual(self.registry(), {})

    def test_post_write_quiet_while_pending(self):
        hooks.post_write(self.write_event(self.plan), self.root)
        self.assertIsNone(hooks.post_write(self.write_event(self.plan, "Edit"), self.root))

    def test_post_write_skips_reviewing_and_done_same_hash(self):
        junior.mark(self.root, self.plan, "reviewing")
        self.assertIsNone(hooks.post_write(self.write_event(self.plan, "Edit"), self.root))
        junior.mark(self.root, self.plan, "done", self.plan.read_text(encoding="utf-8"))
        self.assertIsNone(hooks.post_write(self.write_event(self.plan, "Edit"), self.root))

    def test_post_write_small_change_after_done_is_quiet(self):
        junior.mark(self.root, self.plan, "done", self.plan.read_text(encoding="utf-8"))
        self.plan.write_text(MERMAID.replace("place order", "place the order"), encoding="utf-8")
        self.assertIsNone(hooks.post_write(self.write_event(self.plan, "Edit"), self.root))

    def test_post_write_rerecords_after_big_change(self):
        junior.mark(self.root, self.plan, "done", self.plan.read_text(encoding="utf-8"))
        self.plan.write_text(PLAN + MERMAID.replace("Cart", "Basket").replace("Orders", "Sales"), encoding="utf-8")
        self.assertIsNotNone(hooks.post_write(self.write_event(self.plan, "Edit"), self.root))
        self.assertEqual(self.registry()[str(self.plan.resolve())]["status"], "pending")

    def test_post_write_ignores_state_folder(self):
        scratch = self.root / "checkout-1234" / "answers.md"
        scratch.parent.mkdir(parents=True)
        scratch.write_text(PLAN, encoding="utf-8")
        self.assertIsNone(hooks.post_write(self.write_event(scratch), self.root))

    def test_post_write_relative_path_uses_cwd(self):
        self.assertIsNotNone(hooks.post_write(self.write_event("docs/checkout.md"), self.root))

    def test_post_write_ignores_non_artifacts_and_missing_files(self):
        notes = self.project / "README.md"
        notes.write_text(README, encoding="utf-8")
        self.assertIsNone(hooks.post_write(self.write_event(notes), self.root))
        self.assertIsNone(hooks.post_write(self.write_event(self.project / "gone.md"), self.root))

    def test_stop_blocks_with_pending_paths(self):
        hooks.post_write(self.write_event(self.plan), self.root)
        out = hooks.stop(self.stop_event(), self.root)
        self.assertEqual(out["decision"], "block")
        self.assertIn("checkout.md", out["reason"])

    def test_stop_skips_when_active(self):
        hooks.post_write(self.write_event(self.plan), self.root)
        self.assertIsNone(hooks.stop(self.stop_event(active=True), self.root))

    def test_stop_skips_when_nothing_pending(self):
        self.assertIsNone(hooks.stop(self.stop_event(), self.root))

    def test_stop_blocks_once_per_file(self):
        hooks.post_write(self.write_event(self.plan), self.root)
        self.assertIsNotNone(hooks.stop(self.stop_event(), self.root))
        self.assertIsNone(hooks.stop(self.stop_event(), self.root))

    def test_start_marks_reviewing_and_report_marks_done(self):
        hooks.post_write(self.write_event(self.plan), self.root)
        session = junior.JuniorSession.start(self.plan, state_root=self.root, runner=lambda a, p: "")
        self.assertEqual(self.registry()[str(self.plan.resolve())]["status"], "reviewing")
        self.assertIsNone(hooks.stop(self.stop_event(), self.root))
        session.report()
        entry = self.registry()[str(self.plan.resolve())]
        self.assertEqual(entry["status"], "done")
        self.assertEqual(entry["snapshot"], MERMAID)

    def test_hook_cli_never_fails_on_bad_input(self):
        for mode in ("post-write", "stop"):
            done = subprocess.run([sys.executable, str(SCRIPTS / "hooks.py"), mode], input="not json",
                                  capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(done.returncode, 0)
            self.assertEqual(done.stdout.strip(), "")

    def test_hook_cli_prints_reminder(self):
        event = json.dumps(self.write_event(self.plan))
        env = {k: v for k, v in os.environ.items() if k not in ("JUNIOR_DEV_NESTED", "CLAUDE_PROJECT_DIR")}
        done = subprocess.run([sys.executable, str(SCRIPTS / "hooks.py"), "post-write"], input=event,
                              capture_output=True, text=True, encoding="utf-8", env=env)
        self.assertEqual(done.returncode, 0)
        self.assertIn("additionalContext", json.loads(done.stdout)["hookSpecificOutput"])


class HooksJsonTest(unittest.TestCase):
    def test_hooks_json_shape(self):
        config = json.loads((SCRIPTS.parent / "hooks" / "hooks.json").read_text(encoding="utf-8"))["hooks"]
        post = config["PostToolUse"][0]
        self.assertEqual(set(post["matcher"].split("|")), {"Write", "Edit", "MultiEdit"})
        self.assertIn('${CLAUDE_PLUGIN_ROOT}/scripts/hooks.py" post-write', post["hooks"][0]["command"])
        self.assertIn('${CLAUDE_PLUGIN_ROOT}/scripts/hooks.py" stop', config["Stop"][0]["hooks"][0]["command"])


if __name__ == "__main__":
    unittest.main()
