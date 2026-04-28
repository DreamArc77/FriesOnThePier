from __future__ import annotations

import importlib
import os
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch


PLUGIN_ROOT = Path(__file__).resolve().parents[1] / "plugins" / "fries-on-the-pier"
SCRIPTS = PLUGIN_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

fries_core = importlib.import_module("fries_core")


class FriesCoreTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {"FRIES_DATA_DIR": self.tmp.name}, clear=False)
        self.env.start()

    def tearDown(self) -> None:
        self.env.stop()
        self.tmp.cleanup()

    def test_meal_suggestion_requires_window_coding_context_and_once_per_window(self) -> None:
        state = fries_core.default_state()
        lunch = datetime.fromisoformat("2026-04-27T12:00:00")

        should, window_id = fries_core.should_suggest("This API has a compile error", lunch, state)
        self.assertTrue(should)
        self.assertEqual(window_id, "2026-04-27:lunch")

        fries_core.save_state(fries_core.mark_suggested(state, window_id))
        should_again, _ = fries_core.should_suggest(
            "This API has a compile error",
            lunch,
            fries_core.load_state(),
        )
        self.assertFalse(should_again)

        outside, _ = fries_core.should_suggest(
            "This API has a compile error",
            datetime.fromisoformat("2026-04-27T15:00:00"),
            fries_core.default_state(),
        )
        self.assertFalse(outside)

        non_coding, _ = fries_core.should_suggest("I am reading a novel", lunch, fries_core.default_state())
        self.assertFalse(non_coding)

    def test_stop_hook_ignores_non_meal_non_coding_replies_by_default(self) -> None:
        with patch.dict(os.environ, {"FRIES_TEST_NOW": "", "FRIES_FORCE_MEAL_WINDOW": ""}):
            result = fries_core.stop_hook(
                {
                    "now": "2026-04-27T09:00:00",
                    "last_assistant_message": "测试",
                }
            )

        self.assertEqual(result, {})
        state = fries_core.load_state()
        self.assertFalse(state["last_stop_hook"]["eligible"])
        self.assertIsNone(state["last_stop_hook"]["window_id"])

    def test_stop_hook_requests_nudge_once_per_meal_window(self) -> None:
        with patch.dict(os.environ, {"FRIES_TEST_NOW": "", "FRIES_FORCE_MEAL_WINDOW": ""}):
            result = fries_core.stop_hook(
                {
                    "now": "2026-04-27T12:00:00",
                    "last_assistant_message": "This API has a compile error.",
                }
        )

        self.assertEqual(result["decision"], "block")
        self.assertNotIn(fries_core.STOP_NUDGE_MARKER, result["reason"])
        self.assertIn("不要解释 hook", result["reason"])
        self.assertIn("回复「帮我点」", result["reason"])
        self.assertIn("不要提 MCP", result["reason"])
        self.assertIn("顺手一提", result["reason"])
        self.assertIn("先吃点东西再继续写代码", result["reason"])
        self.assertNotIn("巨无霸套餐今天 ¥30.5", result["reason"])
        state = fries_core.load_state()
        self.assertEqual(state["mode"], "suggested")
        self.assertIn("2026-04-27:lunch", state["suggested_windows"])
        self.assertTrue(state["last_stop_hook"]["eligible"])

        with patch.dict(os.environ, {"FRIES_TEST_NOW": "", "FRIES_FORCE_MEAL_WINDOW": ""}):
            repeated = fries_core.stop_hook(
                {
                    "now": "2026-04-27T12:00:01",
                    "last_assistant_message": f"测试 {fries_core.STOP_NUDGE_MARKER}",
                }
            )

        self.assertEqual(repeated, {})
        self.assertFalse(fries_core.load_state()["last_stop_hook"]["eligible"])

    def test_stop_hook_can_use_test_now_environment_override(self) -> None:
        with patch.dict(os.environ, {"FRIES_TEST_NOW": "2026-04-27T18:10:00"}):
            result = fries_core.stop_hook(
                {
                    "last_assistant_message": "The deploy API returned an error.",
                }
        )

        self.assertEqual(result["decision"], "block")
        self.assertIn("自然饭点关怀", result["reason"])
        self.assertIn("回复「帮我点」", result["reason"])

    def test_force_meal_window_environment_override_still_records_debug_context(self) -> None:
        with patch.dict(os.environ, {"FRIES_FORCE_MEAL_WINDOW": "always", "FRIES_TEST_NOW": ""}):
            result = fries_core.stop_hook(
                {
                    "now": "2026-04-27T09:00:00",
                    "last_assistant_message": "测试",
                }
            )

        self.assertEqual(result["decision"], "block")
        self.assertIn("自然饭点关怀", result["reason"])
        self.assertIn(fries_core.STOP_NUDGE_MARKER, result["reason"])
        self.assertIn("不要提 MCP", result["reason"])
        state = fries_core.load_state()
        self.assertIn("2026-04-27:always", state["suggested_windows"])
        self.assertTrue(state["last_stop_hook"]["eligible"])
        self.assertEqual(state["last_stop_hook"]["forced_window"], "always")

    def test_runtime_test_mode_ignores_time_context_and_frequency(self) -> None:
        fries_core.write_json_file(
            fries_core.test_mode_path(),
            {
                "enabled": True,
                "force_meal_window": "always",
                "ignore_frequency": True,
                "debug_marker": True,
            },
        )

        first = fries_core.stop_hook(
            {
                "now": "2026-04-27T09:00:00",
                "last_assistant_message": "普通回答，没有 coding 关键词。",
            }
        )
        second = fries_core.stop_hook(
            {
                "now": "2026-04-27T09:00:01",
                "last_assistant_message": "另一条普通回答，继续测试。",
            }
        )

        self.assertEqual(first["decision"], "block")
        self.assertEqual(second["decision"], "block")
        self.assertIn(fries_core.STOP_NUDGE_MARKER, first["reason"])
        self.assertIn(fries_core.STOP_NUDGE_MARKER, second["reason"])
        state = fries_core.load_state()
        self.assertEqual(state["last_stop_hook"]["window_id"], "2026-04-27:always")
        self.assertTrue(state["last_stop_hook"]["eligible"])

    def test_runtime_test_mode_does_not_nudge_while_ordering(self) -> None:
        fries_core.write_json_file(
            fries_core.test_mode_path(),
            {
                "enabled": True,
                "force_meal_window": "always",
                "ignore_frequency": True,
                "debug_marker": True,
            },
        )
        state = fries_core.default_state()
        state["mode"] = "ordering"
        fries_core.save_state(state)

        result = fries_core.stop_hook(
            {
                "now": "2026-04-27T09:00:00",
                "last_assistant_message": "请先获取 MCP Token。",
            }
        )

        self.assertEqual(result, {})
        saved = fries_core.load_state()
        self.assertFalse(saved["last_stop_hook"]["eligible"])
        self.assertEqual(saved["last_stop_hook"]["window_id"], "2026-04-27:test")
        self.assertEqual(saved["last_stop_hook"]["forced_window"], "always")

    def test_stop_hook_records_heartbeat_when_marker_is_already_present(self) -> None:
        with patch.dict(os.environ, {"FRIES_TEST_NOW": "", "FRIES_FORCE_MEAL_WINDOW": "always"}):
            result = fries_core.stop_hook(
                {
                    "now": "2026-04-27T09:00:00",
                    "last_assistant_message": f"测试 {fries_core.STOP_NUDGE_MARKER}",
                }
            )

        self.assertEqual(result, {})
        state = fries_core.load_state()
        self.assertFalse(state["last_stop_hook"]["eligible"])
        self.assertEqual(state["last_stop_hook"]["window_id"], "2026-04-27:always")

    def test_accept_enters_official_mcp_ordering_flow_and_cancel_resets(self) -> None:
        state = fries_core.default_state()
        state["mode"] = "suggested"
        fries_core.save_state(state)

        accepted = fries_core.user_prompt_submit_hook({"prompt": "帮我点"})

        context = accepted["hookSpecificOutput"]["additionalContext"]
        self.assertIn("mcd-mcp", context)
        self.assertIn("立即调用 delivery-query-addresses", context)
        self.assertIn("不要让用户去 App 自己点", context)
        self.assertIn("delivery-query-addresses", context)
        self.assertIn("create-order", context)
        self.assertEqual(fries_core.load_state()["mode"], "ordering")

        canceled = fries_core.user_prompt_submit_hook({"prompt": "算了"})
        self.assertIn("取消点餐", canceled["hookSpecificOutput"]["additionalContext"])
        self.assertEqual(fries_core.load_state()["mode"], "idle")

    def test_non_create_mcd_tools_are_not_blocked_by_local_token_or_address_state(self) -> None:
        state = fries_core.default_state()
        state["mode"] = "ordering"
        fries_core.save_state(state)

        result = fries_core.pre_tool_use_hook(
            {"tool_name": "mcp__mcd-mcp__query-meals", "tool_input": {}}
        )

        self.assertEqual(result, {})

    def test_create_order_requires_calculate_price_and_user_confirmation(self) -> None:
        state = fries_core.default_state()
        state["mode"] = "ordering"
        fries_core.save_state(state)

        denied_before_price = fries_core.pre_tool_use_hook(
            {
                "tool_name": "mcp__mcd-mcp__create-order",
                "tool_input": {"items": [{"sku": "meal-1"}], "storeCode": "store-1"},
            }
        )
        self.assertIn("calculate-price", denied_before_price["hookSpecificOutput"]["permissionDecisionReason"])

        fries_core.post_tool_use_hook(
            {
                "tool_name": "mcp__mcd-mcp__calculate-price",
                "tool_input": {"items": [{"sku": "meal-1"}], "storeCode": "store-1"},
                "tool_output": {"totalAmount": 30.5, "deliveryFee": 0, "discountAmount": 5},
            }
        )

        denied_without_confirm = fries_core.pre_tool_use_hook(
            {
                "tool_name": "mcp__mcd-mcp__create-order",
                "tool_input": {"items": [{"sku": "meal-1"}], "storeCode": "store-1"},
            }
        )
        self.assertIn("明确确认", denied_without_confirm["hookSpecificOutput"]["permissionDecisionReason"])

        fries_core.user_prompt_submit_hook({"prompt": "确认下单"})
        allowed = fries_core.pre_tool_use_hook(
            {
                "tool_name": "mcp__mcd-mcp__create-order",
                "tool_input": {"items": [{"sku": "meal-1"}], "storeCode": "store-1"},
            }
        )
        self.assertEqual(allowed, {})

    def test_create_order_requires_recognizable_order_payload(self) -> None:
        state = fries_core.default_state()
        state["mode"] = "ordering"
        state["awaiting_create_order_confirmation"] = True
        state["create_order_confirmed"] = True
        fries_core.save_state(state)

        denied = fries_core.pre_tool_use_hook(
            {"tool_name": "mcp__mcd-mcp__create-order", "tool_input": {"foo": "bar"}}
        )

        self.assertIn("商品或门店", denied["hookSpecificOutput"]["permissionDecisionReason"])

    def test_calculate_price_marks_summary_confirmation_required(self) -> None:
        state = fries_core.default_state()
        state["mode"] = "ordering"
        fries_core.save_state(state)

        result = fries_core.post_tool_use_hook(
            {
                "tool_name": "mcp__mcd-mcp__calculate-price",
                "tool_input": {"items": [{"sku": "meal-1"}], "storeCode": "store-1"},
                "tool_output": {"totalAmount": 30.5},
            }
        )

        self.assertIn("订单摘要", result["hookSpecificOutput"]["additionalContext"])
        saved = fries_core.load_state()
        self.assertTrue(saved["awaiting_create_order_confirmation"])
        self.assertFalse(saved["create_order_confirmed"])

    def test_post_tool_use_accepts_codex_tool_response_field(self) -> None:
        state = fries_core.default_state()
        state["mode"] = "ordering"
        fries_core.save_state(state)

        fries_core.post_tool_use_hook(
            {
                "tool_name": "mcp__mcd-mcp__calculate-price",
                "tool_input": {"items": [{"sku": "meal-1"}], "storeCode": "store-1"},
                "tool_response": {"totalAmount": 30.5},
            }
        )

        saved = fries_core.load_state()
        self.assertEqual(saved["pending_order"]["quote_output"], {"totalAmount": 30.5})

    def test_create_order_post_hook_surfaces_pay_url(self) -> None:
        state = fries_core.default_state()
        state["mode"] = "ordering"
        fries_core.save_state(state)

        result = fries_core.post_tool_use_hook(
            {
                "tool_name": "mcp__mcd-mcp__create-order",
                "tool_input": {"items": [{"sku": "meal-1"}], "storeCode": "store-1"},
                "tool_output": {"data": {"orderNo": "order-1", "payH5Url": "https://pay.example/order-1"}},
            }
        )

        self.assertIn("https://pay.example/order-1", result["hookSpecificOutput"]["additionalContext"])
        self.assertEqual(fries_core.load_state()["pending_order"]["payH5Url"], "https://pay.example/order-1")

    def test_query_order_completion_resets_state(self) -> None:
        state = fries_core.default_state()
        state["mode"] = "ordering"
        fries_core.save_state(state)

        result = fries_core.post_tool_use_hook(
            {
                "tool_name": "mcp__mcd-mcp__query-order",
                "tool_output": {"status": "paid"},
            }
        )

        self.assertIn("恢复正常 coding", result["hookSpecificOutput"]["additionalContext"])
        self.assertEqual(fries_core.load_state()["mode"], "idle")


if __name__ == "__main__":
    unittest.main()
