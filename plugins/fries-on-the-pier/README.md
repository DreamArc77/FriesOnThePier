# Fries on the Pier

去码头整点薯条 is a Codex and Claude Code plugin. It gently adds a meal-time nudge at the end of coding answers, then guides a real McDonald's China ordering flow through the official `mcd-mcp` service when the user accepts.

The plugin is the experience layer: reminder, conversation guidance, MCP orchestration, and safety confirmation. Real address lookup, menus, price calculation, order creation, payment link creation, and order status come from McDonald's China official MCP.

## Official MCP

- Repository: <https://github.com/M-China/mcd-mcp-server>
- Server name: `mcd-mcp`
- Transport: `streamablehttp`
- URL: `https://mcp.mcd.cn`
- Auth: `Authorization: Bearer <MCP Token>`

The plugin declares:

```json
{
  "mcpServers": {
    "mcd-mcp": {
      "type": "streamablehttp",
      "url": "https://mcp.mcd.cn",
      "headers": {
        "Authorization": "Bearer ${MCD_MCP_TOKEN}"
      }
    }
  }
}
```

Do not put tokens, phone numbers, or full delivery addresses in the plugin directory. Tokens belong in the client or user-level environment/config.

## Product Flow

1. User codes normally.
2. During lunch (`11:20-13:30`) or dinner (`17:20-20:00`), after a coding answer, the hook asks the model to append one natural meal nudge.
3. User says `帮我点`, `来一份`, `可以`, or a similar acceptance.
4. The assistant enters ordering mode and tries to use `mcd-mcp`.
5. If `mcd-mcp` is missing or unauthorized, the assistant stays in the current chat, asks the user to get a McDonald's China MCP Token from `open.mcd.cn` / `https://mcp.mcd.cn`, and lets the user paste the token into the chat.
6. After token configuration, the assistant continues ordering in the same conversation when the client has reloaded MCP.
7. Ordering uses official tools: `delivery-query-addresses`, `delivery-create-address`, `query-nearby-stores`, `query-meals`, `query-meal-detail`, `calculate-price`, `create-order`, `query-order`.
8. Before `create-order`, the assistant must show item, store, fulfillment, amount, delivery fee, discounts, and payment impact, then wait for an explicit confirmation such as `确认下单`, `可以下单`, or `下单吧`.
9. After `create-order`, the assistant shows the official `payH5Url`. The user pays manually, then the assistant uses `query-order`.

## Codex Hook Bridge

Current Codex App/CLI builds do not reliably execute plugin-local `hooks.json` for automatic end-of-answer injection. For real users, the plugin exposes default prompts such as `启用自动饭点提醒` and `修复 Codex App 自动提醒`; the assistant should run setup in the conversation.

Manual development equivalent:

```bash
python3 plugins/fries-on-the-pier/scripts/install_codex_hooks.py --codex-home ~/.codex
python3 plugins/fries-on-the-pier/scripts/install_codex_hooks.py --codex-home ~/.codex --verify
```

Useful options:

```bash
python3 plugins/fries-on-the-pier/scripts/install_codex_hooks.py --codex-home ~/.codex --uninstall
python3 plugins/fries-on-the-pier/scripts/install_codex_hooks.py --codex-home ~/.codex --dry-run
```

For repeatable injection tests, use runtime test mode instead of changing system time or process environment. Test mode ignores meal time, coding keywords, and once-per-window frequency. It also requires `[fries-stop-hook]` in the appended nudge so you can prove the hook ran. Production meal-window nudges do not include that marker.

```bash
python3 plugins/fries-on-the-pier/scripts/fries_test_mode.py --enable --reset-state
python3 plugins/fries-on-the-pier/scripts/fries_test_mode.py --status
python3 plugins/fries-on-the-pier/scripts/fries_test_mode.py --disable --reset-state
```

Doctor:

```bash
python3 plugins/fries-on-the-pier/scripts/doctor.py --codex-home ~/.codex
```

The doctor checks Codex hook installation, meal-window/force mode, latest Stop hook heartbeat, and `codex mcp get mcd-mcp`.

## Codex App Real User Flow

1. Install the plugin in Codex App.
2. Click the plugin prompt `启用自动饭点提醒`, or type it in the current chat.
3. The assistant runs `scripts/setup_codex_app.py` from the plugin and installs the hook bridge into the user-level Codex home. For acceptance testing it may run with `--force-meal-window`.
4. Fully quit and reopen Codex App.
5. For repeated injection testing, click/type `开启饭点提醒测试模式`; the assistant runs `scripts/fries_test_mode.py --enable --reset-state`.
6. Ask a normal question without `@fries-on-the-pier`.
7. At meal time, or immediately in runtime test mode, the answer ends with a short meal nudge.
8. Reply `帮我点`.
9. If `mcd-mcp` needs a Token, the assistant asks you to open `open.mcd.cn` / `https://mcp.mcd.cn`, paste the Token into the current chat, then runs `scripts/configure_mcd_mcp.py --token-stdin` without echoing the Token.
10. Fully quit and reopen Codex App if the client cannot hot-load MCP/environment changes.
11. Continue in chat: address, store, menu, price, order summary, explicit confirmation, `create-order`, `payH5Url`, and `query-order`.
12. After testing, click/type `关闭饭点提醒测试模式`; the assistant runs `scripts/fries_test_mode.py --disable --reset-state`.

## Codex CLI Real-Device Test

Inside Codex CLI, add the local marketplace with a path that starts with `./`:

```text
/plugin marketplace add ./.agents/plugins
```

Then install the plugin from the marketplace:

```text
/plugin install fries-on-the-pier@fries-on-the-pier-local
```

Install and verify automatic hooks:

```bash
python3 plugins/fries-on-the-pier/scripts/install_codex_hooks.py --codex-home ~/.codex
python3 plugins/fries-on-the-pier/scripts/install_codex_hooks.py --codex-home ~/.codex --verify
```

Enable runtime test mode:

```bash
python3 plugins/fries-on-the-pier/scripts/fries_test_mode.py --enable --reset-state
codex
```

In Codex, do not mention `@fries-on-the-pier`. Ask a normal coding question:

```text
帮我看一下这个 function 里的 API error 可能是什么问题
```

Expected: the answer ends with a short meal nudge containing `[fries-stop-hook]`. Then run:

```bash
python3 plugins/fries-on-the-pier/scripts/doctor.py --codex-home ~/.codex --skip-mcp
```

When testing real ordering, say:

```text
帮我点
```

If MCP is not configured, paste the official token when the assistant asks. The assistant should avoid echoing it and help configure:

```bash
export MCD_MCP_TOKEN='YOUR_MCP_TOKEN'
codex mcp add mcd-mcp --url https://mcp.mcd.cn --bearer-token-env-var MCD_MCP_TOKEN
```

If your Codex build cannot hot-load MCP changes, restart Codex CLI from a shell where `MCD_MCP_TOKEN` is set, then continue the same ordering test.

## Codex App Real-Device Test

1. Open this repository in Codex App as a trusted workspace.
2. Install or refresh the local marketplace entry for `fries-on-the-pier`.
3. In Codex App, use the plugin prompt:

```text
启用自动饭点提醒
```

The assistant should run the setup script in the conversation. Manual development fallback from WSL:

```bash
python3 plugins/fries-on-the-pier/scripts/setup_codex_app.py --codex-home /mnt/c/Users/ndh/.codex --force-meal-window
python3 plugins/fries-on-the-pier/scripts/setup_codex_app.py --codex-home /mnt/c/Users/ndh/.codex --verify
```

Use your actual Windows user path if it is different.

4. Fully quit Codex App and reopen it.
5. Ask any normal question without `@fries-on-the-pier`.

Expected: the answer ends with a short nudge containing `[fries-stop-hook]`. Run doctor against the App Codex home if it does not:

```bash
python3 plugins/fries-on-the-pier/scripts/doctor.py --codex-home /mnt/c/Users/ndh/.codex --skip-mcp
```

6. Say `帮我点`. If `mcd-mcp` is not ready, paste the official token into the chat when asked. The assistant should run `scripts/configure_mcd_mcp.py --token-stdin`, configure user-level MCP/environment, and avoid plugin files.

Fully quit and restart Codex App after changing user-level environment variables. Then continue by saying `帮我点` again.

## Claude Code Real-Device Test

From the repository root:

```bash
claude
```

Inside Claude Code, add the local marketplace using an explicit relative path:

```text
/plugin marketplace add ./.claude-plugin
/plugin install fries-on-the-pier@fries-on-the-pier-local
```

If you previously installed an older copy, uninstall it first or refresh the plugin cache before reinstalling.

For forced injection testing:

```bash
export FRIES_FORCE_MEAL_WINDOW=always
claude
```

Ask a normal coding question without mentioning the plugin. Expected: the end of the answer gets a natural meal nudge, with `[fries-stop-hook]` only in forced/debug mode.

For real ordering, say `帮我点`. If `mcd-mcp` is not connected, paste the official token when asked. The assistant should configure Claude's user-level MCP connection or user environment, then continue ordering after Claude Code reloads the MCP client.

## Local Tests

Run unit tests:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests
```

Validate JSON manifests:

```bash
python3 -m json.tool plugins/fries-on-the-pier/.codex-plugin/plugin.json >/dev/null
python3 -m json.tool plugins/fries-on-the-pier/.claude-plugin/plugin.json >/dev/null
python3 -m json.tool plugins/fries-on-the-pier/.mcp.json >/dev/null
python3 -m json.tool plugins/fries-on-the-pier/hooks.json >/dev/null
python3 -m json.tool plugins/fries-on-the-pier/hooks/hooks.json >/dev/null
```

## Acceptance Checklist

- Plugin appears as `去码头整点薯条` / `fries-on-the-pier`.
- Codex answers get automatic nudges without `@fries-on-the-pier` after config-layer hooks are installed.
- Forced mode shows `[fries-stop-hook]`; normal mode does not.
- Same meal window nudges only once.
- User accepts in chat and enters ordering mode.
- Missing token is handled in chat by asking the user to paste an official MCP Token.
- Token and address details are not written into the plugin directory.
- `mcd-mcp` official tools are visible after configuration.
- Address, store, menu, detail, price, order, pay link, and order status use official MCP tools.
- `create-order` is blocked until price summary and explicit confirmation.
- `payH5Url` is shown after order creation, and payment remains user-controlled.
