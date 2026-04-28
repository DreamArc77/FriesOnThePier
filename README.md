# Fries on the Pier

去码头整点薯条 is a dual Codex and Claude Code plugin for coding sessions: it adds a gentle meal-time nudge at the end of answers, then guides a guarded McDonald's China ordering flow through the official `mcd-mcp` service when the user accepts.

The plugin lives at:

```text
plugins/fries-on-the-pier
```

See the plugin README for installation, Codex App hook setup, MCP token configuration, real-device testing, and acceptance steps:

[plugins/fries-on-the-pier/README.md](plugins/fries-on-the-pier/README.md)

## Quick Shape

- Codex manifest: `plugins/fries-on-the-pier/.codex-plugin/plugin.json`
- Claude Code manifest: `plugins/fries-on-the-pier/.claude-plugin/plugin.json`
- Shared skill: `plugins/fries-on-the-pier/skills/fries-on-the-pier/SKILL.md`
- Shared hooks: `plugins/fries-on-the-pier/scripts/`
- Official MCP config: `plugins/fries-on-the-pier/.mcp.json`

## Official MCP

- Repository: <https://github.com/M-China/mcd-mcp-server>
- Server name: `mcd-mcp`
- URL: `https://mcp.mcd.cn`
- Transport: `streamablehttp`
- Auth: `Authorization: Bearer <MCP Token>`

The plugin does not store McDonald's MCP tokens, phone numbers, or full addresses in the plugin directory. Tokens belong in the user's client-level MCP config or user environment.

## Local Test

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests
```

For repeatable Codex App injection testing, enable runtime test mode:

```bash
python3 plugins/fries-on-the-pier/scripts/fries_test_mode.py --enable --reset-state
```

Disable it after acceptance testing:

```bash
python3 plugins/fries-on-the-pier/scripts/fries_test_mode.py --disable --reset-state
```
