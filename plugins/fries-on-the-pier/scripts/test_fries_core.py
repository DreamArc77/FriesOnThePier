#!/usr/bin/env python3
"""Focused tests for Fries on the Pier hook state transitions."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import fries_core


class FriesCoreStateTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.previous_data_dir = os.environ.get("FRIES_DATA_DIR")
        os.environ["FRIES_DATA_DIR"] = self.tmpdir.name

    def tearDown(self) -> None:
        if self.previous_data_dir is None:
            os.environ.pop("FRIES_DATA_DIR", None)
        else:
            os.environ["FRIES_DATA_DIR"] = self.previous_data_dir
        self.tmpdir.cleanup()

    def state(self) -> dict:
        return fries_core.load_state()

    def write_state(self, state: dict) -> None:
        fries_core.write_json_file(Path(self.tmpdir.name) / "state.json", state)

    def stop_payload(self, now: str) -> dict:
        return {
            "last_assistant_message": "This API bug causes an error in code.",
            "now": now,
        }

    def test_stop_hook_records_eligibility_without_blocking(self) -> None:
        result = fries_core.stop_hook(self.stop_payload("2026-04-29T12:00:00"))
        state = self.state()

        self.assertEqual(result, {})
        self.assertEqual(state["mode"], "idle")
        self.assertEqual(state["suggested_windows"], [])
        self.assertEqual(state["active_window_id"], "2026-04-29:lunch")
        self.assertTrue(state["last_stop_hook"]["eligible"])
        self.assertEqual(state["pending_meal_nudge"]["window_id"], "2026-04-29:lunch")

        second = fries_core.stop_hook(self.stop_payload("2026-04-29T12:05:00"))
        self.assertEqual(second, {})

    def test_user_prompt_submit_injects_pending_nudge_context(self) -> None:
        fries_core.stop_hook(self.stop_payload("2026-04-29T12:00:00"))

        result = fries_core.user_prompt_submit_hook(
            {"prompt": "这个 API bug 继续怎么排查？", "now": "2026-04-29T12:01:00"}
        )

        self.assertIn("hookSpecificOutput", result)
        output = result["hookSpecificOutput"]
        self.assertEqual(output["hookEventName"], "UserPromptSubmit")
        self.assertIn("回答末尾自然追加", output["additionalContext"])
        state = self.state()
        self.assertEqual(state["mode"], "suggested")
        self.assertIsNone(state["pending_meal_nudge"])

    def test_decline_marks_current_window_as_reminded(self) -> None:
        fries_core.stop_hook(self.stop_payload("2026-04-29T12:00:00"))
        result = fries_core.user_prompt_submit_hook(
            {"prompt": "不吃了", "now": "2026-04-29T12:01:00"}
        )

        state = self.state()
        self.assertEqual(result, {})
        self.assertEqual(state["mode"], "idle")
        self.assertEqual(state["suggested_windows"], ["2026-04-29:lunch"])

        blocked = fries_core.stop_hook(self.stop_payload("2026-04-29T12:05:00"))
        self.assertEqual(blocked, {})
        self.assertFalse(self.state()["last_stop_hook"]["eligible"])

    def test_new_window_resets_stale_ordering(self) -> None:
        state = fries_core.default_state()
        state["mode"] = "ordering"
        state["active_window_id"] = "2026-04-29:lunch"
        self.write_state(state)

        result = fries_core.stop_hook(self.stop_payload("2026-04-29T17:30:00"))

        self.assertEqual(result, {})
        state = self.state()
        self.assertEqual(state["mode"], "idle")
        self.assertEqual(state["active_window_id"], "2026-04-29:dinner")
        self.assertTrue(state["last_stop_hook"]["eligible"])
        self.assertEqual(state["pending_meal_nudge"]["window_id"], "2026-04-29:dinner")

    def test_user_completion_exits_ordering(self) -> None:
        state = fries_core.default_state()
        state["mode"] = "ordering"
        state["active_window_id"] = "2026-04-29:lunch"
        self.write_state(state)

        result = fries_core.user_prompt_submit_hook(
            {"prompt": "我点完单了", "now": "2026-04-29T12:10:00"}
        )

        self.assertIn("hookSpecificOutput", result)
        self.assertEqual(self.state()["mode"], "idle")

    def test_leaked_hook_prompt_does_not_start_ordering(self) -> None:
        state = fries_core.default_state()
        state["pending_meal_nudge"] = {"window_id": "2026-04-29:lunch", "created_at": "2026-04-29T12:00:00"}
        state["active_window_id"] = "2026-04-29:lunch"
        self.write_state(state)

        result = fries_core.user_prompt_submit_hook(
            {
                "prompt": '<hook_prompt hook_run_id="stop:3">想点餐就回复「帮我点」。</hook_prompt>',
                "now": "2026-04-29T12:01:00",
            }
        )

        self.assertEqual(result, {})
        self.assertEqual(self.state()["mode"], "idle")


if __name__ == "__main__":
    unittest.main()
