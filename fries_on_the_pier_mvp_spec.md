# 🐦 去码头整点薯条.skill（Fries on the pier.skill）

> 别人只关心你写得快不快
> 我更关心你累不累

---

# 一、产品定位（MVP）

一个面向 vibe coding 用户的“轻关怀 + 轻决策”插件。

核心目标：

👉 在合适的时机，用克制的方式提醒用户该吃饭了
👉 同时提供一个**具体可点的推荐选项**（而不是空泛询问）
👉 用户接受后，进入“点单模式”，完成点单流程

---

# 二、核心体验原则

## 1. 不打断 flow
- 不在生成中插入
- 不抢主回答
- 仅在回答完成后追加

## 2. 像人而不是广告

✔ 风格示例（不是固定文案；真实价格、门店、库存必须来自官方 MCP）：

> 写挺久了，晚饭要不要顺手安排一下？
> 我可以先看看附近麦当劳现在能点什么。

❌ 反例：

> 推荐您购买麦当劳套餐

---

## 3. 推荐要具体，选择要轻
- 必须给一个明确推荐（价格 + 品类）
- 不展开复杂菜单
- 不超过 2 行

---

## 4. 用户始终有控制权
- 不自动下单
- 所有行为需要确认
- 可随时退出

---

# 三、MVP 功能范围

## ✅ 必做功能

### 1. 饭点感知

时间窗口：
- 午餐：11:20 – 13:30
- 晚餐：17:20 – 20:00

---

### 2. 编程场景检测（弱）

关键词：

```
function / bug / error / compile / deploy / API / code
```

---

### 3. 输出末尾关怀（核心）

原则：

- 不固定复读模板
- 不在未调用官方 MCP 前编造实时价格、门店、库存或优惠
- 由 Skill 指导模型生成符合风格的自然文案

---

### 4. 用户接受后进入点单模式

触发词：

```
要 / 帮我点 / 就这个 / 来一份 / 看看别的
```

---

### 5. MCP 点单流程

能力：
- 推荐套餐
- 查看门店
- 创建订单
- 确认订单

---

## ❌ 不做（MVP阶段）

- 自动下单
- 个性化推荐（复杂画像）
- 多品牌扩展
- UI 弹窗

---

# 四、状态机设计（关键）

```
IDLE
  ↓ 饭点触发
SUGGESTED
  ↓ 用户接受
ORDERING
  ↓ 完成 / 取消
IDLE
```

---

## 状态存储

本地文件：

```
~/.fries-on-the-pier/state.json
```

示例：

```json
{
  "mode": "ordering",
  "recommended_item": "巨无霸套餐",
  "price": 30.5
}
```

---

# 五、技术架构

```
Plugin
├── Hook（控制注入 & 状态）
├── Skill（控制语气 & 行为）
└── MCP（麦当劳能力）
```

---

# 六、Hook 设计（核心）

## 1. Stop Hook（注入推荐）

作用：
- 判断饭点
- 判断是否已触发
- 在回答末尾追加推荐

逻辑：

```pseudo
if meal_time && not_triggered:
    return decision = "block"
    return reason = "追加饭点推荐"
```

---

## 2. UserPromptSubmit Hook（模式切换）

作用：
- 判断用户是否接受推荐
- 切换 ordering mode

```pseudo
if user_input in accept_intents:
    state.mode = "ordering"
```

---

## 3. Ordering Mode 注入

在 ordering 状态下，注入：

```
用户已接受点单建议。
优先完成点单流程。
暂不继续 coding。
```

---

## 4. PreToolUse Hook（安全控制）

- 下单前必须确认
- 防止误触

---

## 5. PostToolUse Hook（恢复状态）

```pseudo
if order_complete or cancel:
    state.mode = "idle"
```

---

# 七、MCP 接入

Server：

```
https://mcp.mcd.cn
```

协议与鉴权以麦当劳中国官方 MCP 为准：

```json
{
  "mcd-mcp": {
    "type": "streamablehttp",
    "url": "https://mcp.mcd.cn",
    "headers": {
      "Authorization": "Bearer <MCP Token>"
    }
  }
}
```

---

## 官方 Tool 能力

```json
[
  "delivery-query-addresses",
  "delivery-create-address",
  "query-nearby-stores",
  "query-meals",
  "query-meal-detail",
  "calculate-price",
  "create-order",
  "query-order"
]
```

---

## 调用策略

| 场景 | 是否调用 MCP |
|------|-------------|
| 推荐提示 | ❌ |
| 用户想看 | ✅ |
| 用户点单 | ✅ |
| 未展示价格摘要或未确认 | ❌ create-order |

---

# 八、Skill 设计（语气控制）

核心规则：

```
- 仅在回答结束后追加
- 不超过2句话
- 语气自然
- 不像广告
- 不强推
```

---

## 示例语气

- “好像到饭点了，要不要整点薯条？”
- “写挺久了吧，要不要先吃点东西？”

---

# 九、Claude Code 实现路径（优先）

结构：

```
fries-on-the-pier/
├── plugin.json
├── hooks/
├── scripts/
└── skills/
```

---

# 十、Codex 实现路径（第二阶段）

- 开启 hooks
- 接 MCP
- 复用同一状态机逻辑

---

# 十一、成功标准

## 🎯 核心指标

- 用户不觉得被打扰
- 用户记住“去码头整点薯条”
- 有一定转化但不侵入

---

## ❌ 失败信号

- 被当广告
- 用户关闭插件
- 打断 coding flow

---

# 十二、产品本质

👉 不是点餐插件

👉 是一个在你写代码的时候，突然有人问：

> “你是不是该吃饭了？”
