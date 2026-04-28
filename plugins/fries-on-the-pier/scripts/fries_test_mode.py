#!/usr/bin/env python3
"""Toggle Fries on the Pier runtime test mode."""

from __future__ import annotations

import argparse
import json

from fries_core import default_state, load_json_file, state_path, test_mode_path, write_json_file


def enable(*, debug_marker: bool) -> None:
    write_json_file(
        test_mode_path(),
        {
            "enabled": True,
            "force_meal_window": "always",
            "ignore_frequency": True,
            "debug_marker": debug_marker,
        },
    )


def disable() -> None:
    write_json_file(
        test_mode_path(),
        {
            "enabled": False,
            "force_meal_window": None,
            "ignore_frequency": False,
            "debug_marker": False,
        },
    )


def reset_state() -> None:
    write_json_file(state_path(), default_state())


def status() -> None:
    mode = load_json_file(test_mode_path(), {})
    state = load_json_file(state_path(), {})
    print("test_mode:")
    print(json.dumps(mode, ensure_ascii=False, indent=2))
    print("state:")
    print(json.dumps(state, ensure_ascii=False, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser(description="Toggle Fries on the Pier runtime test mode.")
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--enable", action="store_true", help="Force every Stop hook to be eligible for testing.")
    action.add_argument("--disable", action="store_true", help="Disable runtime test mode.")
    action.add_argument("--status", action="store_true", help="Print test mode and state.")
    parser.add_argument("--reset-state", action="store_true", help="Clear suggestion/order runtime state.")
    parser.add_argument(
        "--no-debug-marker",
        action="store_true",
        help="Do not require [fries-stop-hook] in generated test nudges.",
    )
    args = parser.parse_args()

    if args.enable:
        enable(debug_marker=not args.no_debug_marker)
        if args.reset_state:
            reset_state()
        print(f"Enabled Fries test mode at {test_mode_path()}")
        print("Every Stop hook is treated as a meal-window candidate and frequency is ignored.")
        return 0

    if args.disable:
        disable()
        if args.reset_state:
            reset_state()
        print(f"Disabled Fries test mode at {test_mode_path()}")
        return 0

    if args.reset_state:
        reset_state()
    status()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
