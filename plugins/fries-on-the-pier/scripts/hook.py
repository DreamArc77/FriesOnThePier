#!/usr/bin/env python3
"""CLI entrypoint for Claude Code and Codex hooks."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from fries_core import (
    post_tool_use_hook,
    pre_tool_use_hook,
    route_hook,
    stop_hook,
    user_prompt_submit_hook,
)


HOOKS = {
    "Stop": stop_hook,
    "UserPromptSubmit": user_prompt_submit_hook,
    "PreToolUse": pre_tool_use_hook,
    "PostToolUse": post_tool_use_hook,
}


def read_payload() -> dict[str, Any]:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise TypeError("Hook payload must be a JSON object.")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a Fries on the Pier hook.")
    parser.add_argument("--event", choices=sorted(HOOKS), help="Hook event name.")
    args = parser.parse_args()

    try:
        payload = read_payload()
        if args.event:
            payload.setdefault("hook_event_name", args.event)
            result = HOOKS[args.event](payload)
        else:
            result = route_hook(payload)
        if result:
            print(json.dumps(result, ensure_ascii=False))
        return 0
    except Exception as exc:  # Hooks must fail closed, especially around ordering.
        print(
            json.dumps(
                {
                    "decision": "block",
                    "reason": f"fries-on-the-pier hook failed closed: {exc}",
                },
                ensure_ascii=False,
            )
        )
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
