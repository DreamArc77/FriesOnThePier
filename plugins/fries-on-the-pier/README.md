# 去码头整点薯条

去码头整点薯条是一个同时支持 Codex 和 Claude Code 的饭点关怀插件。

它会在你写代码写到午饭或晚饭时间时，在回答末尾自然地提醒一句。你如果回复“帮我点”，插件会进入点单模式，通过麦当劳中国官方 MCP 服务 `mcd-mcp` 帮你完成从查地址、选门店、看菜单、算价到创建订单和查询订单状态的流程。

插件只负责提醒、引导、编排和安全确认。真实地址、门店、菜单、价格、订单和支付链接都来自麦当劳中国官方 MCP。插件不会保存 MCP Token、手机号或完整地址，也不会自动下单或代替你支付。

## 安装

### Codex App

1. 在 Codex App 中安装插件 `fries-on-the-pier`。
2. 安装后，在当前对话中输入或点击插件默认提示：

```text
启用自动饭点提醒
```

插件会在对话里完成自动提醒配置。完成后，完全退出并重新打开 Codex App。

3. 正常使用 Codex。到午饭或晚饭时间时，插件会在回答末尾补上一句轻提醒。
4. 如果想点餐，回复：

```text
帮我点
```

5. 首次点餐时，如果 `mcd-mcp` 还不可用，插件会引导你打开 `open.mcd.cn` 或 `https://mcp.mcd.cn` 获取麦当劳中国官方 MCP Token。获取后直接粘贴到当前对话，插件会帮你写入用户级配置并继续点单。

### Codex CLI

在 Codex CLI 中添加并安装插件：

```text
/plugin marketplace add DreamArc77/FriesOnThePier
/plugin install fries-on-the-pier
```

安装后输入：

```text
启用自动饭点提醒
```

随后按对话提示完成自动提醒和麦当劳 MCP Token 配置。

### Claude Code

在 Claude Code 中添加并安装插件：

```text
/plugin marketplace add DreamArc77/FriesOnThePier
/plugin install fries-on-the-pier
```

安装后正常使用 Claude Code。饭点时插件会在回答末尾追加轻提醒；你回复“帮我点”后，插件会在当前对话中引导你配置麦当劳中国官方 MCP Token，并继续完成点单流程。

### 麦当劳 MCP Token

插件使用麦当劳中国官方 MCP 服务：

```text
Server name: mcd-mcp
URL: https://mcp.mcd.cn
Transport: streamablehttp
Auth: Authorization: Bearer <MCP Token>
```

Token 只应保存到 Codex / Claude Code 的用户级 MCP 配置或用户环境变量中，不应写入插件目录。
