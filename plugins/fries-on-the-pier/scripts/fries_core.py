#!/usr/bin/env python3
"""Shared hook logic for the Fries on the Pier plugin."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, time
from pathlib import Path
from typing import Any


MCD_MCP_NAME = "mcd-mcp"
MCD_MCP_URL = "https://mcp.mcd.cn"

CODING_KEYWORDS = (
    "function",
    "bug",
    "error",
    "compile",
    "deploy",
    "api",
    "code",
)

ACCEPT_PATTERNS = (
    r"^要[。！!,.，\s]*$",
    r"^好[。！!,.，\s]*$",
    r"^可以[。！!,.，\s]*$",
    r"帮我点",
    r"就这个",
    r"来一份",
    r"看看别的",
    r"点.*(?:这个|一份|套餐|薯条|麦当劳)",
    r"order\s+it",
    r"\byes\b",
)

CANCEL_PATTERNS = (
    r"取消",
    r"算了",
    r"不点了",
    r"不点",
    r"不吃",
    r"不饿",
    r"先不吃",
    r"不用.*(?:点|吃)",
    r"退出点单",
    r"\bcancel\b",
)

CREATE_ORDER_CONFIRM_PATTERNS = (
    r"确认下单",
    r"确认创建订单",
    r"可以下单",
    r"下单吧",
    r"就按这个下单",
)

ORDER_COMPLETE_PATTERNS = (
    r"paid",
    r"completed",
    r"finished",
    r"已支付",
    r"已完成",
    r"下单成功",
    r"点完了",
    r"点完单",
    r"已下单",
    r"支付了",
    r"吃完了",
)

MCD_TOOL_MARKERS = (
    "mcd",
    "delivery-query-addresses",
    "delivery-create-address",
    "query-nearby-stores",
    "query-meals",
    "query-meal-detail",
    "calculate-price",
    "create-order",
    "query-order",
)


@dataclass(frozen=True)
class MealWindow:
    name: str
    start: time
    end: time


MEAL_WINDOWS = (
    MealWindow("lunch", time(11, 20), time(13, 30)),
    MealWindow("dinner", time(17, 20), time(20, 0)),
)


def data_dir() -> Path:
    return Path(os.environ.get("FRIES_DATA_DIR", "~/.fries-on-the-pier")).expanduser()


def state_path() -> Path:
    return data_dir() / "state.json"


def default_state() -> dict[str, Any]:
    return {
        "mode": "idle",
        "suggested_windows": [],
        "awaiting_create_order_confirmation": False,
        "create_order_confirmed": False,
        "pending_order": None,
        "last_stop_hook": None,
        "active_window_id": None,
        "pending_meal_nudge": None,
    }


def load_json_file(path: Path, fallback: Any) -> Any:
    try:
        with path.open(encoding="utf-8") as handle:
            return json.load(handle)
    except (FileNotFoundError, json.JSONDecodeError):
        return fallback


def write_json_file(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def load_state() -> dict[str, Any]:
    state = default_state()
    loaded = load_json_file(state_path(), {})
    if isinstance(loaded, dict):
        for key in state:
            if key in loaded:
                state[key] = loaded[key]
    if not isinstance(state.get("suggested_windows"), list):
        state["suggested_windows"] = []
    if state.get("pending_meal_nudge") is not None and not isinstance(state.get("pending_meal_nudge"), dict):
        state["pending_meal_nudge"] = None
    return state


def save_state(state: dict[str, Any]) -> None:
    write_json_file(state_path(), state)


def meal_window_for(now: datetime) -> str | None:
    current = now.time()
    for window in MEAL_WINDOWS:
        if window.start <= current <= window.end:
            return f"{now.date().isoformat()}:{window.name}"
    return None


def payload_now(payload: dict[str, Any]) -> datetime | None:
    raw_now = payload.get("now")
    if not isinstance(raw_now, str):
        return None
    try:
        return datetime.fromisoformat(raw_now)
    except ValueError:
        return None


def forced_window_name() -> str | None:
    value = os.environ.get("FRIES_FORCE_MEAL_WINDOW", "").strip().lower()
    return value if value in {"lunch", "dinner"} else None


def matches_any(text: str, patterns: tuple[str, ...]) -> bool:
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)


def is_coding_context(text: str) -> bool:
    lower = text.lower()
    return any(keyword in lower for keyword in CODING_KEYWORDS)


def is_cancel_intent(prompt: str) -> bool:
    return matches_any(prompt, CANCEL_PATTERNS)


def is_accept_intent(prompt: str) -> bool:
    return not is_cancel_intent(prompt) and matches_any(prompt, ACCEPT_PATTERNS)


def is_hook_prompt_leak(prompt: str) -> bool:
    return "<hook_prompt" in prompt or "hook_run_id=" in prompt


def has_create_order_confirmation(prompt: str) -> bool:
    return matches_any(prompt, CREATE_ORDER_CONFIRM_PATTERNS)


def should_suggest(
    text: str,
    now: datetime | None = None,
    state: dict[str, Any] | None = None,
) -> tuple[bool, str | None]:
    now = now or datetime.now()
    state = state or load_state()
    window_id = meal_window_for(now)
    if window_id is None:
        return False, None
    if window_id in state.get("suggested_windows", []):
        return False, window_id
    if state.get("mode") == "ordering":
        return False, window_id
    if not is_coding_context(text):
        return False, window_id
    return True, window_id


def state_window_id(state: dict[str, Any]) -> str | None:
    active = state.get("active_window_id")
    if isinstance(active, str):
        return active
    last_stop = state.get("last_stop_hook")
    if isinstance(last_stop, dict) and isinstance(last_stop.get("window_id"), str):
        return last_stop["window_id"]
    suggested = state.get("suggested_windows")
    if isinstance(suggested, list):
        for item in reversed(suggested):
            if isinstance(item, str):
                return item
    return None


def reset_stale_window_state(state: dict[str, Any], window_id: str | None) -> dict[str, Any]:
    if window_id is None:
        if state.get("mode") in {"suggested", "ordering"}:
            reset_to_idle(state)
        state["active_window_id"] = None
        state["pending_meal_nudge"] = None
        return state

    previous_window_id = state_window_id(state)
    if previous_window_id is not None and previous_window_id != window_id:
        reset_to_idle(state)
    state["active_window_id"] = window_id
    return state


def mark_suggested(state: dict[str, Any], window_id: str) -> dict[str, Any]:
    state["mode"] = "suggested"
    state["active_window_id"] = window_id
    state["pending_meal_nudge"] = None
    state["awaiting_create_order_confirmation"] = False
    state["create_order_confirmed"] = False
    return state


def mark_window_dismissed(state: dict[str, Any], window_id: str) -> dict[str, Any]:
    suggested = list(state.get("suggested_windows", []))
    if window_id not in suggested:
        suggested.append(window_id)
    state["suggested_windows"] = suggested
    state["active_window_id"] = window_id
    state["pending_meal_nudge"] = None
    return state


def mark_pending_meal_nudge(state: dict[str, Any], *, now: datetime, window_id: str) -> dict[str, Any]:
    state["active_window_id"] = window_id
    state["pending_meal_nudge"] = {
        "window_id": window_id,
        "created_at": now.isoformat(),
    }
    return state


def has_active_pending_nudge(state: dict[str, Any], window_id: str | None) -> bool:
    pending = state.get("pending_meal_nudge")
    return isinstance(pending, dict) and isinstance(window_id, str) and pending.get("window_id") == window_id


def meal_nudge_context(window_id: str | None) -> str:
    meal_name = "饭点"
    if isinstance(window_id, str):
        if window_id.endswith(":lunch"):
            meal_name = "午饭窗口"
        elif window_id.endswith(":dinner"):
            meal_name = "晚饭窗口"
    return (
        f"这轮继续正常回答用户当前问题。回答末尾自然追加 1-2 句{meal_name}关怀，"
        "提醒用户可以先垫点东西；如果想点餐，可以回复「帮我点」。"
        "不要提 hook、MCP、工具名、地址查询、门店、价格、库存、优惠或实现细节；"
        "语气像顺手提醒，不要像广告。"
    )


def mark_stop_seen(
    state: dict[str, Any],
    *,
    now: datetime,
    text: str,
    eligible: bool,
    window_id: str | None,
) -> dict[str, Any]:
    state["last_stop_hook"] = {
        "seen_at": now.isoformat(),
        "text_present": bool(text.strip()),
        "eligible": eligible,
        "window_id": window_id,
        "forced_window": forced_window_name() or None,
    }
    return state


def enter_ordering(state: dict[str, Any], window_id: str | None = None) -> dict[str, Any]:
    state["mode"] = "ordering"
    if window_id is not None:
        state["active_window_id"] = window_id
    state["pending_meal_nudge"] = None
    state["create_order_confirmed"] = False
    return state


def reset_to_idle(state: dict[str, Any]) -> dict[str, Any]:
    state["mode"] = "idle"
    state["awaiting_create_order_confirmation"] = False
    state["create_order_confirmed"] = False
    state["pending_order"] = None
    state["pending_meal_nudge"] = None
    return state


def extract_last_assistant_text(payload: dict[str, Any]) -> str:
    for key in ("last_assistant_message", "assistant_message", "message", "response"):
        value = payload.get(key)
        if isinstance(value, str):
            return value
    return ""


def extract_tool_payload(payload: dict[str, Any]) -> dict[str, Any]:
    tool_input = payload.get("tool_input")
    return tool_input if isinstance(tool_input, dict) else {}


def extract_tool_output(payload: dict[str, Any]) -> Any:
    if "tool_output" in payload:
        return payload.get("tool_output")
    return payload.get("tool_response")


def tool_name(payload: dict[str, Any]) -> str:
    return str(payload.get("tool_name") or payload.get("name") or "")


def normalized_tool_name(name: str) -> str:
    return name.lower().replace("_", "-")


def is_mcd_tool(name: str) -> bool:
    normalized = normalized_tool_name(name)
    return any(marker in normalized for marker in MCD_TOOL_MARKERS)


def is_calculate_price_tool(name: str) -> bool:
    return "calculate-price" in normalized_tool_name(name)


def is_create_order_tool(name: str) -> bool:
    return "create-order" in normalized_tool_name(name)


def is_query_order_tool(name: str) -> bool:
    return "query-order" in normalized_tool_name(name)


def output_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False) if value is not None else ""


def find_key(value: Any, wanted: str) -> Any:
    if isinstance(value, dict):
        for key, child in value.items():
            if key == wanted:
                return child
            found = find_key(child, wanted)
            if found is not None:
                return found
    if isinstance(value, list):
        for child in value:
            found = find_key(child, wanted)
            if found is not None:
                return found
    return None


def has_order_payload(tool_input: dict[str, Any]) -> bool:
    serialized = json.dumps(tool_input, ensure_ascii=False).lower()
    has_items = any(marker in serialized for marker in ("items", "products", "meal", "cart", "sku", "product"))
    has_store = any(marker in serialized for marker in ("store", "restaurant"))
    return has_items and has_store


def stop_hook(payload: dict[str, Any]) -> dict[str, Any]:
    state = load_state()
    text = extract_last_assistant_text(payload)
    now = payload_now(payload) or datetime.now()
    window_id = meal_window_for(now)
    reset_stale_window_state(state, window_id)

    should, window_id = should_suggest(text, now, state)
    mark_stop_seen(state, now=now, text=text, eligible=should, window_id=window_id)
    if should and window_id is not None:
        mark_pending_meal_nudge(state, now=now, window_id=window_id)
    save_state(state)
    return {}


def ordering_context() -> str:
    return (
        "执行指令：用户已接受饭点提醒，现在进入麦当劳点餐流程，优先点餐，暂不继续 coding。"
        f" 使用官方 MCP 服务 {MCD_MCP_NAME}（{MCD_MCP_URL}）。"
        " 不要让用户去 App 自己点；如果 mcd-mcp 工具可见，下一步立即调用 delivery-query-addresses。"
        " 如果 mcd-mcp 工具不可见、未连接或鉴权失败，再告诉用户需要打开 https://open.mcd.cn/mcp "
        "获取麦当劳中国官方 MCP Token，并直接粘贴到当前对话；拿到 Token 后帮助写入用户级环境变量或客户端 MCP 配置，"
        "不要要求用户手动编辑插件文件，也不要在回复里回显 Token。"
        " 工具可用后严格按顺序推进：delivery-query-addresses；没有合适地址再用 delivery-create-address；"
        "query-nearby-stores；query-meals；query-meal-detail；calculate-price；create-order；query-order。"
        " create-order 前必须展示商品、门店、履约方式、金额、配送费、优惠和支付影响，并得到明确确认。"
    )


def user_prompt_submit_hook(payload: dict[str, Any]) -> dict[str, Any]:
    prompt = str(payload.get("prompt") or "")
    state = load_state()
    now = payload_now(payload) or datetime.now()
    window_id = meal_window_for(now)
    reset_stale_window_state(state, window_id)

    if is_hook_prompt_leak(prompt):
        save_state(state)
        return {}

    if is_cancel_intent(prompt):
        was_ordering = state.get("mode") == "ordering"
        if window_id is not None:
            mark_window_dismissed(state, window_id)
        save_state(reset_to_idle(state))
        if was_ordering:
            return {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": "用户取消或拒绝点餐；恢复正常 coding 对话。",
                }
            }
        return {}

    if (state.get("mode") in {"suggested", "ordering"} or has_active_pending_nudge(state, window_id)) and is_accept_intent(prompt):
        save_state(enter_ordering(state, window_id))
        return {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": ordering_context(),
            }
        }

    if state.get("mode") == "ordering":
        if matches_any(prompt, ORDER_COMPLETE_PATTERNS):
            save_state(reset_to_idle(state))
            return {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": "用户表示点餐或支付已完成；恢复正常 coding 对话。",
                }
            }
        if state.get("awaiting_create_order_confirmation") and has_create_order_confirmation(prompt):
            state["create_order_confirmed"] = True
        else:
            state["create_order_confirmed"] = False
        save_state(state)
        return {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": ordering_context(),
            }
        }

    if has_active_pending_nudge(state, window_id):
        save_state(mark_suggested(state, window_id))
        return {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": meal_nudge_context(window_id),
            }
        }

    return {}


def deny_pre_tool(reason: str) -> dict[str, Any]:
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }


def pre_tool_use_hook(payload: dict[str, Any]) -> dict[str, Any]:
    state = load_state()
    name = tool_name(payload)
    tool_input = extract_tool_payload(payload)

    if not is_mcd_tool(name):
        return {}
    if not is_create_order_tool(name):
        return {}
    if state.get("mode") != "ordering":
        return deny_pre_tool("用户尚未进入点餐模式，不能创建麦当劳订单。")
    if not state.get("awaiting_create_order_confirmation"):
        return deny_pre_tool("调用 create-order 前必须先用 calculate-price 得到价格，并向用户展示订单摘要。")
    if not state.get("create_order_confirmed"):
        return deny_pre_tool("调用 create-order 前必须得到用户明确确认，例如「确认下单」或「可以下单」。")
    if not has_order_payload(tool_input):
        return deny_pre_tool("create-order 请求缺少可识别的商品或门店信息，请先补全订单后再创建。")

    state["create_order_confirmed"] = False
    save_state(state)
    return {}


def post_tool_use_hook(payload: dict[str, Any]) -> dict[str, Any]:
    state = load_state()
    name = tool_name(payload)
    tool_input = extract_tool_payload(payload)
    tool_output = extract_tool_output(payload)

    if is_calculate_price_tool(name):
        state["mode"] = "ordering"
        state["awaiting_create_order_confirmation"] = True
        state["create_order_confirmed"] = False
        state["pending_order"] = {
            "quote_input": tool_input,
            "quote_output": tool_output,
        }
        save_state(state)
        return {
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": (
                    "已获得价格计算结果。先向用户展示订单摘要：商品、门店、履约方式、金额、"
                    "配送费、优惠和支付影响；只有用户明确确认后才能调用 create-order。"
                ),
            }
        }

    if is_create_order_tool(name):
        pay_url = find_key(tool_output, "payH5Url")
        state["mode"] = "ordering"
        state["awaiting_create_order_confirmation"] = False
        state["create_order_confirmed"] = False
        state["pending_order"] = {
            "create_input": tool_input,
            "create_output": tool_output,
            "payH5Url": pay_url,
        }
        save_state(state)
        pay_hint = "展示官方支付链接 payH5Url，引导用户完成支付；支付后用 query-order 查询状态。"
        if pay_url:
            pay_hint = f"向用户展示官方支付链接 {pay_url}；用户支付后用 query-order 查询状态。"
        return {
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": pay_hint,
            }
        }

    if is_query_order_tool(name) and matches_any(output_text(tool_output), ORDER_COMPLETE_PATTERNS):
        save_state(reset_to_idle(state))
        return {
            "hookSpecificOutput": {
                "hookEventName": "PostToolUse",
                "additionalContext": "订单状态显示已完成或已支付；恢复正常 coding 对话。",
            }
        }

    return {}


def route_hook(payload: dict[str, Any]) -> dict[str, Any]:
    event = str(payload.get("hook_event_name") or "")
    if event == "Stop":
        return stop_hook(payload)
    if event == "UserPromptSubmit":
        return user_prompt_submit_hook(payload)
    if event == "PreToolUse":
        return pre_tool_use_hook(payload)
    if event == "PostToolUse":
        return post_tool_use_hook(payload)
    return {}
