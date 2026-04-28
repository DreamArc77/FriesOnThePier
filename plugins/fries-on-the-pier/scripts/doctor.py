#!/usr/bin/env python3
"""Doctor checks for Fries on the Pier local installs."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from fries_core import (
    FORCE_WINDOW_ENV,
    MCD_MCP_NAME,
    TEST_NOW_ENV,
    load_test_mode,
    meal_window_for,
    state_path,
    test_mode_path,
)
from install_codex_hooks import verify as verify_codex_hooks


def status_line(ok: bool, message: str) -> str:
    return f"[{'OK' if ok else '!!'}] {message}"


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def check_codex_hooks(codex_home: Path) -> tuple[bool, list[str]]:
    hooks_path = codex_home / "hooks.json"
    ok, messages = verify_codex_hooks(hooks_path)
    return ok, [status_line(ok, message) for message in messages]


def check_meal_window() -> tuple[bool, list[str]]:
    now = datetime.now()
    forced = os.environ.get(FORCE_WINDOW_ENV, "").strip()
    test_now = os.environ.get(TEST_NOW_ENV, "").strip()
    test_mode = load_test_mode()
    window = meal_window_for(now)
    ok = bool(window)
    messages = [
        status_line(ok, f"meal window: {window or 'not active'}"),
        f"    now: {now.isoformat(timespec='seconds')}",
        f"    {FORCE_WINDOW_ENV}: {forced or '<unset>'}",
        f"    {TEST_NOW_ENV}: {test_now or '<unset>'}",
        f"    runtime test mode: {'enabled' if test_mode.get('enabled') else 'disabled'} ({test_mode_path()})",
    ]
    if test_mode.get("enabled"):
        messages.extend(
            [
                f"    force_meal_window: {test_mode.get('force_meal_window')}",
                f"    ignore_frequency: {test_mode.get('ignore_frequency')}",
                f"    debug_marker: {test_mode.get('debug_marker')}",
            ]
        )
    return ok, messages


def check_state() -> tuple[bool, list[str]]:
    path = state_path()
    if not path.exists():
        return False, [status_line(False, f"no runtime state yet: {path}")]
    try:
        state = load_json(path)
    except Exception as exc:
        return False, [status_line(False, f"state file is invalid: {exc}")]
    last = state.get("last_stop_hook") if isinstance(state, dict) else None
    if not isinstance(last, dict):
        return False, [status_line(False, "state exists, but no last_stop_hook heartbeat yet")]
    return True, [
        status_line(True, "Stop hook heartbeat found"),
        f"    seen_at: {last.get('seen_at')}",
        f"    eligible: {last.get('eligible')}",
        f"    window_id: {last.get('window_id')}",
        f"    text_present: {last.get('text_present')}",
    ]


def check_codex_mcp() -> tuple[bool, list[str]]:
    if shutil.which("codex") is None:
        return False, [status_line(False, "codex CLI not found on PATH")]
    try:
        result = subprocess.run(
            ["codex", "mcp", "get", MCD_MCP_NAME],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except Exception as exc:
        return False, [status_line(False, f"failed to run codex mcp get {MCD_MCP_NAME}: {exc}")]

    output = (result.stdout or result.stderr).strip()
    configured = result.returncode == 0
    token_env_set = bool(os.environ.get("MCD_MCP_TOKEN"))
    output_mentions_token_env = "MCD_MCP_TOKEN" in output
    ok = configured and (token_env_set or output_mentions_token_env)
    messages = [status_line(configured, f"codex mcp get {MCD_MCP_NAME}")]
    if output:
        messages.extend(f"    {line}" for line in output.splitlines()[:12])
    if token_env_set:
        messages.append("    MCD_MCP_TOKEN is set in this shell")
    elif output_mentions_token_env:
        messages.append("    MCP config references MCD_MCP_TOKEN; make sure the launched client can read it")
    else:
        messages.append("    MCD_MCP_TOKEN is not set in this shell")
        messages.append("    no bearer-token env var was visible in codex mcp get output")
        messages.append("    configure with: codex mcp add mcd-mcp --url https://mcp.mcd.cn --bearer-token-env-var MCD_MCP_TOKEN")
    return ok, messages


def main() -> int:
    parser = argparse.ArgumentParser(description="Diagnose Fries on the Pier installation.")
    parser.add_argument(
        "--codex-home",
        default=str(Path.home() / ".codex"),
        help="Codex home directory containing hooks.json.",
    )
    parser.add_argument(
        "--skip-mcp",
        action="store_true",
        help="Skip codex mcp get mcd-mcp.",
    )
    args = parser.parse_args()

    checks: list[tuple[str, tuple[bool, list[str]]]] = [
        ("Codex hooks", check_codex_hooks(Path(args.codex_home).expanduser())),
        ("Meal window", check_meal_window()),
        ("Runtime state", check_state()),
    ]
    if not args.skip_mcp:
        checks.append(("MCP", check_codex_mcp()))

    overall = True
    for title, (ok, messages) in checks:
        print(f"\n== {title} ==")
        for message in messages:
            print(message)
        if title in {"Codex hooks", "MCP"}:
            overall = overall and ok

    return 0 if overall else 1


if __name__ == "__main__":
    raise SystemExit(main())
