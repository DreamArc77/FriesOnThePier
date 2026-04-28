#!/usr/bin/env python3
"""Configure the official McDonald's China MCP for Codex without echoing tokens."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

from fries_core import MCD_MCP_NAME, MCD_MCP_URL
from setup_codex_app import detect_codex_home, set_windows_user_env


TOKEN_ENV = "MCD_MCP_TOKEN"


def run_codex_mcp_add(codex_home: Path) -> None:
    if shutil.which("codex") is None:
        print("codex CLI is not on PATH; skipped codex mcp add.")
        return

    codex_home.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["CODEX_HOME"] = str(codex_home)
    command = [
        "codex",
        "mcp",
        "add",
        MCD_MCP_NAME,
        "--url",
        MCD_MCP_URL,
        "--bearer-token-env-var",
        TOKEN_ENV,
    ]
    result = subprocess.run(command, env=env, check=False, capture_output=True, text=True)
    if result.stdout.strip():
        print(result.stdout.strip())
    if result.stderr.strip():
        print(result.stderr.strip())
    if result.returncode != 0:
        raise SystemExit(f"codex mcp add failed with exit code {result.returncode}.")


def read_token_from_stdin() -> str:
    token = sys.stdin.read().strip()
    if not token:
        raise SystemExit("No token was provided on stdin.")
    if any(char.isspace() for char in token):
        raise SystemExit("Token looks invalid because it contains whitespace.")
    return token


def main() -> int:
    parser = argparse.ArgumentParser(description="Configure mcd-mcp for Codex.")
    parser.add_argument("--codex-home", help="Codex home to update, e.g. /mnt/c/Users/name/.codex.")
    parser.add_argument(
        "--token-stdin",
        action="store_true",
        help="Read the MCP token from stdin and write it to the Windows user environment.",
    )
    parser.add_argument(
        "--skip-token-env",
        action="store_true",
        help="Only configure codex mcp; do not write MCD_MCP_TOKEN to Windows user env.",
    )
    args = parser.parse_args()

    codex_home = detect_codex_home(args.codex_home)

    if args.token_stdin:
        token = read_token_from_stdin()
        if not args.skip_token_env:
            if set_windows_user_env(TOKEN_ENV, token):
                print(f"Stored {TOKEN_ENV} in the Windows user environment.")
            else:
                print(f"Could not write Windows user env automatically; configure {TOKEN_ENV} in the client environment.")

    run_codex_mcp_add(codex_home)
    print(f"Configured {MCD_MCP_NAME} -> {MCD_MCP_URL} for Codex home: {codex_home}")
    print("Fully quit and reopen Codex App so it reloads MCP and environment.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
