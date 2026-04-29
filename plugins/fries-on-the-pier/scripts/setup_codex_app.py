#!/usr/bin/env python3
"""Conversation-friendly Codex App setup for Fries on the Pier."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from pathlib import Path

from install_codex_hooks import install, verify


def windows_codex_candidates() -> list[Path]:
    candidates: list[Path] = []
    users_root = Path("/mnt/c/Users")
    if users_root.exists():
        for child in sorted(users_root.iterdir()):
            if child.name.lower() in {"all users", "default", "default user", "public"}:
                continue
            codex_home = child / ".codex"
            try:
                exists = codex_home.exists()
            except PermissionError:
                continue
            if exists:
                candidates.append(codex_home)
    return candidates


def detect_codex_home(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit).expanduser()

    env_home = os.environ.get("CODEX_HOME")
    if env_home:
        return Path(env_home).expanduser()

    windows_candidates = windows_codex_candidates()
    if len(windows_candidates) == 1:
        return windows_candidates[0]
    if len(windows_candidates) > 1:
        choices = "\n".join(f"  - {candidate}" for candidate in windows_candidates)
        raise SystemExit(
            "Found multiple Windows Codex homes. Re-run with --codex-home:\n"
            f"{choices}"
        )

    return Path.home() / ".codex"


def set_windows_user_env(name: str, value: str | None) -> bool:
    powershell = shutil.which("powershell.exe")
    if powershell is None:
        return False

    command = (
        "$value = [Console]::In.ReadToEnd().Trim(); "
        f"if ($value.Length -eq 0) {{ [Environment]::SetEnvironmentVariable('{name}', $null, 'User') }} "
        f"else {{ [Environment]::SetEnvironmentVariable('{name}', $value, 'User') }}"
    )
    subprocess.run(
        [powershell, "-NoProfile", "-Command", command],
        input=value or "",
        text=True,
        check=True,
    )
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Set up Fries on the Pier for Codex App.")
    parser.add_argument("--codex-home", help="Codex home used by the Windows App, e.g. /mnt/c/Users/name/.codex.")
    parser.add_argument("--verify", action="store_true", help="Only verify hook installation.")
    args = parser.parse_args()

    codex_home = detect_codex_home(args.codex_home)
    hooks_path = codex_home / "hooks.json"

    if args.verify:
        ok, messages = verify(hooks_path)
    else:
        install(hooks_path, dry_run=False)
        ok, messages = verify(hooks_path)

    for message in messages:
        print(message)

    print(f"Codex home: {codex_home}")
    print("Fully quit and reopen Codex App so it reloads hooks and environment.")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
