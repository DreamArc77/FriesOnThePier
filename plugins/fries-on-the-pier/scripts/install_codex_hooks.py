#!/usr/bin/env python3
"""Install Fries on the Pier hooks into Codex's config-layer hooks.json."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any


MCD_MATCHER = (
    ".*(mcd|delivery-query-addresses|delivery-create-address|query-nearby-stores|"
    "query-meals|query-meal-detail|calculate-price|create-order|query-order).*"
)
ORDER_MATCHER = ".*(mcd|calculate-price|create-order|query-order).*"


def plugin_root() -> Path:
    return Path(__file__).resolve().parents[1]


def shell_quote(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def is_windows_codex_home(path: Path) -> bool:
    parts = path.expanduser().parts
    return len(parts) >= 4 and parts[:3] == ("/", "mnt", "c") and parts[3].lower() == "users"


def hook_command(event: str, *, codex_home: Path | None = None) -> str:
    hook_path = plugin_root() / "scripts" / "hook.py"
    if codex_home is not None and is_windows_codex_home(codex_home):
        distro = os.environ.get("WSL_DISTRO_NAME") or "Ubuntu"
        return (
            f"wsl.exe -d {shell_quote(distro)} -- "
            f"python3 {shell_quote(str(hook_path))} --event {event}"
        )
    return f'python3 "{hook_path}" --event {event}'


def fries_group(event: str, matcher: str = "", *, codex_home: Path | None = None) -> dict[str, Any]:
    return {
        "matcher": matcher,
        "hooks": [
            {
                "type": "command",
                "command": hook_command(event, codex_home=codex_home),
            }
        ],
    }


def fries_hooks(codex_home: Path | None = None) -> dict[str, list[dict[str, Any]]]:
    return {
        "Stop": [fries_group("Stop", codex_home=codex_home)],
        "UserPromptSubmit": [fries_group("UserPromptSubmit", codex_home=codex_home)],
        "PreToolUse": [fries_group("PreToolUse", MCD_MATCHER, codex_home=codex_home)],
        "PostToolUse": [fries_group("PostToolUse", ORDER_MATCHER, codex_home=codex_home)],
    }


def is_fries_group(group: Any) -> bool:
    if not isinstance(group, dict):
        return False
    hooks = group.get("hooks")
    if not isinstance(hooks, list):
        return False
    for hook in hooks:
        if not isinstance(hook, dict):
            continue
        command = str(hook.get("command") or "")
        if "fries-on-the-pier" in command and "scripts/hook.py" in command:
            return True
    return False


def load_hooks(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"hooks": {}}
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    hooks = data.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise ValueError(f"{path} field 'hooks' must be a JSON object")
    return data


def install(path: Path, *, dry_run: bool) -> dict[str, Any]:
    data = load_hooks(path)
    hooks = data["hooks"]

    for event, groups in list(hooks.items()):
        if isinstance(groups, list):
            hooks[event] = [group for group in groups if not is_fries_group(group)]

    codex_home = path.parent
    for event, groups in fries_hooks(codex_home).items():
        existing = hooks.setdefault(event, [])
        if not isinstance(existing, list):
            raise ValueError(f"{path} hooks.{event} must be a list")
        existing.extend(groups)

    if not dry_run:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")

    return data


def uninstall(path: Path, *, dry_run: bool) -> dict[str, Any]:
    data = load_hooks(path)
    hooks = data["hooks"]

    for event, groups in list(hooks.items()):
        if isinstance(groups, list):
            hooks[event] = [group for group in groups if not is_fries_group(group)]

    if not dry_run:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")

    return data


def verify(path: Path) -> tuple[bool, list[str]]:
    messages: list[str] = []
    ok = True

    if not path.exists():
        return False, [f"missing hooks file: {path}"]

    try:
        data = load_hooks(path)
    except Exception as exc:
        return False, [f"invalid hooks file: {exc}"]

    hooks = data.get("hooks", {})
    expected = fries_hooks()
    for event in expected:
        groups = hooks.get(event)
        if not isinstance(groups, list) or not any(is_fries_group(group) for group in groups):
            ok = False
            messages.append(f"missing Fries hook group for {event}")

    hook_path = plugin_root() / "scripts" / "hook.py"
    if not hook_path.exists():
        ok = False
        messages.append(f"missing hook script: {hook_path}")

    if ok:
        messages.append(f"Fries hooks are installed in {path}")
        messages.append(f"Hook script exists: {hook_path}")
    return ok, messages


def main() -> int:
    parser = argparse.ArgumentParser(description="Install Fries on the Pier Codex hooks.")
    parser.add_argument(
        "--codex-home",
        default=str(Path.home() / ".codex"),
        help="Codex home directory containing hooks.json.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print the merged hooks.json.")
    parser.add_argument("--verify", action="store_true", help="Verify Fries hooks are installed.")
    parser.add_argument("--uninstall", action="store_true", help="Remove Fries hooks from hooks.json.")
    args = parser.parse_args()

    hooks_path = Path(args.codex_home).expanduser() / "hooks.json"
    if args.verify:
        ok, messages = verify(hooks_path)
        for message in messages:
            print(message)
        return 0 if ok else 1

    if args.uninstall:
        data = uninstall(hooks_path, dry_run=args.dry_run)
        if args.dry_run:
            print(json.dumps(data, ensure_ascii=False, indent=2))
        else:
            print(f"Removed Fries on the Pier hooks from {hooks_path}")
        return 0

    data = install(hooks_path, dry_run=args.dry_run)
    if args.dry_run:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(f"Installed Fries on the Pier hooks to {hooks_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
