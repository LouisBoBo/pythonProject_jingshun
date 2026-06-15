# Dify 选型多轮 · 逐步点击清单（阶段 5）

> **用途**：在 Dify 画布上 **从零配齐**「多种物料选型 → 用户回料号 → 续领料 → 确认提交」全链。  
> **架构背景**：[23-Dify领料画布连线逐步操作.md](23-Dify领料画布连线逐步操作.md) · [22-库存与领料数据源定稿.md](22-库存与领料数据源定稿.md)  
> **预计耗时**：新增/改节点约 **40～60 分钟**（已有阶段 4 登录 + 阶段 3.5 DATA Fast 的前提下）。

---

## 0. 配之前确认（5 分钟）

| # | 检查项 | 通过标准 |
|---|--------|----------|
| 1 | 阶段 4 登录链 | `zhangsan 123456` 后 `auth_token` 有值 |
| 2 | ① DATA Fast | 「覆铜板还有多少」只走 HTTP，**不进 Agent** |
| 3 | Agent Tools | **仅** `erp_save_draft` / `erp_submit_requisition` / `erp_get_requisition` |
| 4 | Agent Instruction | 已换 [阶段5领料版](../prompts/主控Agent系统提示词-阶段5领料版.md) |
| 5 | 本地 Code 自测 | `python3 workflows/code/test_requisition_fast_inventory.py` 全 OK |

---

## 1. 新增会话变量（2 分钟）

打开 **锦顺物料综合助手** → **会话变量**，若无则 **新增**（类型均为 **String**）：

| 变量名 | 说明 |
|--------|------|
| `requisition_material_code` | 唯一料号 |
| `requisition_material_name` | 物料名称 |
| `requisition_available_qty` | 可用库存数量 |
| `requisition_inventory_unit` | 单位 |
| `requisition_inventory_detail` | Fast 返回明细（可选） |
| `requisition_inventory_extract_ok` | 抽取是否成功 |
| `requisition_pick_required` | 是否需用户选型 |
| `requisition_pick_list` | 选型 Markdown（可选缓存） |
| `requisition_match_count` | 匹配行数 |
| **`requisition_intent_query`** | **选型轮保存的原话（含 10KG）** |
| **`requisition_pick_waiting`** | **`true` = 等用户回料号** |
| `requisition_draft_id` | 草稿 ID（阶段 5 已有则跳过） |

> 带 **粗体** 的两项是 **选型续单** 专用，本轮必加。

---

## 2. 更新已有节点（10 分钟）

### 2.1 Code「领料/查单路由」

1. 双击节点 → **代码** 全选删除 → 粘贴 [`detect_requisition_route.py`](../workflows/code/detect_requisition_route.py) 全文  
2. **输入变量**：

| 参数名 | 绑定 |
|--------|------|
| `query` | `sys.query` |

3. **输出变量**：保持 Dify 自动识别（含 `use_requisition_flow` / `use_agent`）  
4. 保存 → **运行测试**，输入 `JS-NZ-006`，应输出 `use_requisition_flow = true`，`reason = material_code_pick`

### 2.2 If-Else「是否领料子流程」（原「是否走 Agent」）

1. **重命名节点标题** → `是否领料子流程`（仅便于辨认）  
2. 条件不变：`领料/查单路由 / use_agent` **等于** `true`（或 `use_requisition_flow`）  
3. **true 出口** → 接到 **§3.1「已登录？」**（**不要**直接接 Agent）  
4. **false 出口** → 问题分类器

### 2.3 分类器 If-Else

1. **DATA** → ① DATA Fast → Fast Answer（**不动**）  
2. **CHITCHAT** → 寒暄 Answer（**不动**）  
3. **ELSE** 分支标签改为 **领料子流程**  
4. **ELSE 出口** → 与 §2.2 的 **true 出口接到同一个「已登录？」节点**

---

## 3. 领料子流程区块（15 分钟）

在画布空白处 **框选一块区域**，标题写 **领料子流程**。以下节点均放在块内。

### 3.1 If-Else「已登录？」（阶段 4 已有则拖入块内）

| 条件 | 出口 |
|------|------|
| `conversation.auth_token` **不为空** | → §3.2 |
| ELSE | → **直接回复「请先登录」**（沿用阶段 4 文案） |

### 3.2 Code「是否本轮要读」

1. **添加节点** → Code  
2. 标题：`是否本轮要读`  
3. 粘贴 [`detect_requisition_need_inventory.py`](../workflows/code/detect_requisition_need_inventory.py)  
4. **输入**：

| 参数 | 绑定 |
|------|------|
| `query` | `sys.query` |
| `reason` | `领料/查单路由 / reason` |

5. **输出**：`need_fast_inventory`、`skip_reason`  
6. 连线 → **If-Else「路由-领料读或直写」**

### 3.3 If-Else「路由-领料读或直写」

| 条件 | 出口 | 场景 |
|------|------|------|
| `是否本轮要读 / need_fast_inventory` **等于** `true` | → §4 DATA Fast 读链 | 帮我领 / 选型后续 JS-NZ-006 |
| ELSE | → **Agent「领料写单」** | 确认提交 / 查 GON / 改数量 |

---

## 4. DATA Fast 读链（复制 ①，改 6 个节点名）（15 分钟）

> **重要**：从现有 **① DATA Fast** **复制整段**（组装 → HTTP → 解析SSE），粘贴到领料子流程块内，**不要共用连线**。

按顺序创建/重命名并改绑定：

### 4.1 Code「组装领料查库存问题」

| 项 | 值 |
|----|-----|
| 代码 | [`build_requisition_inventory_query.py`](../workflows/code/build_requisition_inventory_query.py) |
| 输入 `user_query` | `sys.query` |
| 输出 | `inventory_query` |

### 4.2 Code「组装Chat请求-领料」

| 项 | 值 |
|----|-----|
| 代码 | [`build_chat_messages_body.py`](../workflows/code/build_chat_messages_body.py) |
| 输入 `query` | **`组装领料查库存问题 / inventory_query`**（不是 sys.query） |
| 输入 `conversation_id` | **留空** 或固定 `""`（领料读 **不带** 子 conversation_id） |
| 输出 | `body_json` |

### 4.3 HTTP「HTTP-领料」

与 ① DATA HTTP **完全相同**（见 [15 §12](15-DATA_QUERY-Fast查数路径配置详解.md#12-推荐fast-路径直连-chat-messages锦顺现网)）：

| 项 | 值 |
|----|-----|
| Method | POST |
| URL | `http://nginx/v1/chat-messages` |
| Header Authorization | `Bearer app-NxITngK2xpaL1nGYMiQFYye5`（你的子 Chatflow Key） |
| Body 类型 | JSON |
| Body | `{{#组装Chat请求-领料.body_json#}}` |
| 超时 | ≥ 120s |

### 4.4 Code「解析SSE-领料」

| 项 | 值 |
|----|-----|
| 代码 | [`parse_sse_and_split.py`](../workflows/code/parse_sse_and_split.py) |
| 输入 `raw_sse` | `HTTP-领料 / body`（或 HTTP 响应体变量名） |
| 输出 | `detail`、`summary` 等 |

### 4.5 Code「解析领料查数结果」★

| 项 | 值 |
|----|-----|
| 代码 | [`extract_requisition_material_from_detail.py`](../workflows/code/extract_requisition_material_from_detail.py) |
| 输入 `detail` | `解析SSE-领料 / detail` |
| 输入 `user_query` | `sys.query` |
| 输入 **`pending_intent_query`** | **`conversation.requisition_intent_query`** |
| 输出 | `material_code`、`pick_required`、`extract_ok`、`pick_list` 等 |

> **`pending_intent_query` 必绑**：用户第 2 轮只发 `JS-NZ-006` 时，数量从第 1 轮「10KG」继承。

### 4.6 读链串联

```
是否本轮要读(true)
  → 组装领料查库存问题
  → 组装Chat请求-领料
  → HTTP-领料
  → 解析SSE-领料
  → 解析领料查数结果
  → If-Else「路由-选型或写单」（§5）
```

---

## 5. If-Else「路由-选型或写单」★ 核心分叉（10 分钟）

接在 **解析领料查数结果** 之后，**3 个出口**：

| 优先级 | 条件 | 出口 |
|--------|------|------|
| 1 | `解析领料查数结果 / pick_required` **等于** `true` | → §6 选型分支 |
| 2 | **ELSE IF** `解析领料查数结果 / extract_ok` **等于** `true` | → §7 唯一物料 → Agent |
| 3 | ELSE | → §8 未能识别 Answer |

Dify 操作：

1. 添加 **If-Else** 节点，标题 `路由-选型或写单`  
2. **CASE 1**：变量选 Code 节点输出 → `pick_required` → 运算符 **is** → 值 `true`  
3. **CASE 2**：**ELSE IF** → `extract_ok` **is** `true`  
4. **ELSE** → 未能识别

---

## 6. 选型分支（pick_required = true）（8 分钟）

**不进 Agent**。按顺序：

### 6.1 Code「保存领料意图」

| 项 | 值 |
|----|-----|
| 代码 | [`save_requisition_intent.py`](../workflows/code/save_requisition_intent.py) |
| 输入 `user_query` | `sys.query` |
| 输出 | `requisition_intent_query`、`requisition_pick_waiting` |

### 6.2 变量赋值「写入选型变量」

**Assigner** 节点，**写入会话变量**：

| 会话变量 | 值来源 |
|----------|--------|
| `requisition_pick_required` | 固定 `true` |
| `requisition_pick_list` | `解析领料查数结果 / pick_list` |
| `requisition_match_count` | `解析领料查数结果 / match_count` |
| `requisition_intent_query` | `保存领料意图 / requisition_intent_query` |
| `requisition_pick_waiting` | `保存领料意图 / requisition_pick_waiting` |
| `requisition_inventory_detail` | `解析SSE-领料 / detail`（可选） |

**不要写** `requisition_material_code`（此时料号未确定）。

### 6.3 直接回复「选型 Answer」

| 项 | 值 |
|----|-----|
| 回复内容 | 见下方模板 |

**回复模板（复制粘贴）**：

```markdown
{{#解析领料查数结果.pick_list#}}
```

`pick_list` 已含表格 +「请直接回复料号」提示，**无需再包一层标题**。

### 6.4 连线

```
路由-选型或写单(CASE1)
  → 保存领料意图
  → 写入选型变量
  → 选型 Answer（结束本轮）
```

---

## 7. 唯一物料分支（extract_ok = true）（8 分钟）

### 7.1 变量赋值「写入领料物料变量」

| 会话变量 | 值来源 |
|----------|--------|
| `requisition_material_code` | `解析领料查数结果 / material_code` |
| `requisition_material_name` | `解析领料查数结果 / material_name` |
| `requisition_available_qty` | `解析领料查数结果 / available_qty` |
| `requisition_inventory_unit` | `解析领料查数结果 / unit` |
| `requisition_inventory_extract_ok` | 固定 `true` |
| `requisition_inventory_detail` | `解析SSE-领料 / detail`（可选） |
| `requisition_pick_required` | 固定 `false` |
| **`requisition_pick_waiting`** | **固定 `false`** |

### 7.2 连线到 Agent

```
路由-选型或写单(CASE2)
  → 写入领料物料变量
  → Agent「领料写单」
  → 直接回复「Agent Answer」
```

### 7.3 Agent Answer 模板

```markdown
{{#Agent.text#}}
```

---

## 8. 未能识别分支（ELSE）（2 分钟）

**直接回复「未能识别物料」**：

```markdown
未能从查数结果中确定要领的物料，请补充 **更具体的名称** 或 **料号**（如 JS-NZ-006）。
```

---

## 9. Agent「领料写单」（确认 §3.3 ELSE 也接到此节点）

| 项 | 值 |
|----|-----|
| Instruction | [主控Agent系统提示词-阶段5领料版.md](../prompts/主控Agent系统提示词-阶段5领料版.md) 全文 |
| Tools | 仅 3 个 erp_* |
| 最大迭代 | 12～15 |

Instruction 中已含：

```jinja
领料原话：{{#conversation.requisition_intent_query#}}
料号：{{#conversation.requisition_material_code#}}
可用库存：{{#conversation.requisition_available_qty#}} ...
```

**Agent 共用一个节点**，入口有两条：

1. **§7** 唯一物料 Assigner 之后（save_draft）  
2. **§3.3** `need_fast_inventory=false`（确认提交 / get GON）

---

## 10. 全链路连线核对表

打勾表示 **必须有这根线**：

| 从 | 到 | ✓ |
|----|----|---|
| 登录路由 false | 领料/查单路由 | ☐ |
| 领料路由 true | 已登录？ | ☐ |
| 领料路由 false | 问题分类器 | ☐ |
| 分类器 DATA | ① DATA Fast | ☐ |
| 分类器 ELSE | **已登录？**（与 true 汇合） | ☐ |
| 已登录 true | 是否本轮要读 | ☐ |
| 是否本轮要读 true | 组装领料查库存问题 | ☐ |
| 解析领料查数结果 | 路由-选型或写单 | ☐ |
| 选型 CASE1 | 保存领料意图 → Assigner → 选型 Answer | ☐ |
| 唯一 CASE2 | 写入领料物料变量 → Agent | ☐ |
| 是否本轮要读 false | Agent | ☐ |
| Agent | Agent Answer | ☐ |
| **选型 Answer** | **（无后续，等用户下一句）** | ☐ |

**禁止出现的线**：

- ❌ 分类器 DATA → 领料子流程  
- ❌ 选型分支 → Agent  
- ❌ ① DATA Fast 与 ② 领料读链 **共用** HTTP 出口线

---

## 11. 三轮回归测试（必做）

同一对话窗口，**不要新开对话**。

### 测试 A：纯查数不进领料

| 步骤 | 输入 | 期望 |
|------|------|------|
| 1 | `覆铜板还有多少` | 仅 ① Fast Answer；追踪 **无** Agent、**无** 领料 HTTP |

### 测试 B：多物料选型（核心）

| 步骤 | 输入 | 期望 |
|------|------|------|
| 1 | 登录 | token 有值 |
| 2 | `帮我领 10KG 阻焊油墨` | 追踪：领料 HTTP → **选型 Answer**（表格多行）；**无 Agent** |
| 3 | 检查会话变量 | `requisition_intent_query` = 原话；`requisition_pick_waiting` = true |
| 4 | `JS-NZ-006` | 追踪：领料 HTTP → **Agent** → 确认卡片含 **10KG**、料号 JS-NZ-006 |
| 5 | `确认提交` | 追踪：**无** HTTP → Agent submit → GON 单号 |

### 测试 C：一句话带料号（跳过选型）

| 输入 | 期望 |
|------|------|
| `领 JS-NZ-006 10KG` | 直接 extract_ok → Agent 确认卡片 |

### 测试 D：确认提交不重复读库存

| 输入 | 期望 |
|------|------|
| `确认提交` | `need_fast_inventory=false`；追踪 **无** HTTP-领料 |

---

## 12. 追踪里对照节点名（排错）

| 用户轮次 | 应出现的节点（顺序） |
|----------|----------------------|
| 帮我领10KG阻焊油墨 | 领料路由 → 已登录 → 是否本轮要读(true) → 组装… → HTTP-领料 → 解析… → **路由-选型** → 保存意图 → 选型 Answer |
| JS-NZ-006 | 领料路由(material_code_pick) → … → **路由-选型** extract_ok → 写入物料变量 → **Agent** |
| 确认提交 | 领料路由 → 是否本轮要读(**false**) → **Agent**（无 HTTP） |

### 常见故障

| 现象 | 原因 | 处理 |
|------|------|------|
| 多种物料直接进 Agent | 缺 §5 If-Else 或 CASE 顺序错 | 先判 `pick_required`，再判 `extract_ok` |
| 选型后回 JS-NZ-006 走了 DATA 查数 | 路由 Code 未更新 | 重贴 `detect_requisition_route.py` |
| 第 2 轮数量变成 1 或空 | 未绑 `pending_intent_query` | §4.5 绑 `conversation.requisition_intent_query` |
| 第 2 轮未进领料 | `requisition_pick_waiting` 未写 | 检查 §6 Assigner |
| 选型 Answer 空白 | pick_list 未引用对节点 | 用 `{{#解析领料查数结果.pick_list#}}` |

---

## 13. 相关文档

| 文档 | 用途 |
|------|------|
| [23-Dify领料画布连线逐步操作.md](23-Dify领料画布连线逐步操作.md) | 架构总图 |
| [19-阶段5-领料全流程操作手册.md](19-阶段5-领料全流程操作手册.md) | Agent / Tool 验收 |
| [20-Agent-ERP-Tool调用参数一览.md](20-Agent-ERP-Tool调用参数一览.md) | erp_* 参数 |
| [15-DATA_QUERY-Fast查数路径配置详解.md](15-DATA_QUERY-Fast查数路径配置详解.md) | HTTP 字段 |
