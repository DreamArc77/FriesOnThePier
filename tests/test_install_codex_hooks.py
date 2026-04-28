from __future__ import annotations

import importlib
import json
import sys
import tempfile
import unittest
from pathlib import Path


PLUGIN_ROOT = Path(__file__).resolve().parents[1] / "plugins" / "fries-on-the-pier"
SCRIPTS = PLUGIN_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

install_codex_hooks = importlib.import_module("install_codex_hooks")


class InstallCodexHooksTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.hooks_path = Path(self.tmp.name) / "hooks.json"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def read_hooks(self) -> dict:
        with self.hooks_path.open(encoding="utf-8") as handle:
            return json.load(handle)

    def test_verify_fails_when_missing(self) -> None:
        ok, messages = install_codex_hooks.verify(self.hooks_path)

        self.assertFalse(ok)
        self.assertIn("missing hooks file", messages[0])

    def test_install_writes_all_required_codex_hook_groups(self) -> None:
        install_codex_hooks.install(self.hooks_path, dry_run=False)

        ok, messages = install_codex_hooks.verify(self.hooks_path)
        data = self.read_hooks()

        self.assertTrue(ok, messages)
        for event in ("Stop", "UserPromptSubmit", "PreToolUse", "PostToolUse"):
            groups = data["hooks"][event]
            self.assertTrue(any(install_codex_hooks.is_fries_group(group) for group in groups))
        self.assertIn("scripts/hook.py", data["hooks"]["Stop"][0]["hooks"][0]["command"])

    def test_reinstall_does_not_duplicate_fries_groups(self) -> None:
        install_codex_hooks.install(self.hooks_path, dry_run=False)
        install_codex_hooks.install(self.hooks_path, dry_run=False)

        data = self.read_hooks()

        for event in ("Stop", "UserPromptSubmit", "PreToolUse", "PostToolUse"):
            count = sum(
                1
                for group in data["hooks"][event]
                if install_codex_hooks.is_fries_group(group)
            )
            self.assertEqual(count, 1, event)

    def test_uninstall_removes_only_fries_groups(self) -> None:
        original = {
            "hooks": {
                "Stop": [
                    {
                        "matcher": "",
                        "hooks": [{"type": "command", "command": "echo keep-me"}],
                    }
                ]
            }
        }
        self.hooks_path.write_text(json.dumps(original), encoding="utf-8")
        install_codex_hooks.install(self.hooks_path, dry_run=False)

        install_codex_hooks.uninstall(self.hooks_path, dry_run=False)
        data = self.read_hooks()

        self.assertEqual(data["hooks"]["Stop"], original["hooks"]["Stop"])
        for event in ("UserPromptSubmit", "PreToolUse", "PostToolUse"):
            self.assertEqual(data["hooks"].get(event), [])


if __name__ == "__main__":
    unittest.main()
