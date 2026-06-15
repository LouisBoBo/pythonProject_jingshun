# Dify 领料画布连线 · 逐步操作（阶段 5 · 三层路由）

> **适用**：**锦顺物料综合助手** Chatflow。  
> **架构**：[22-库存与领料数据源定稿.md](22-库存与领料数据源定稿.md)  
> **HTTP 配置**：与 DATA 相同 → [15-DATA_QUERY §12](15-DATA_QUERY-Fast查数路径配置详解.md#12-推荐fast-路径直连-chat-messages锦顺现网)

---

## 0. 先懂「三层」，就不乱

以前文档写「是否走 Agent」，容易理解成 **一进来就进 Agent 节点**——这是错的。

正确只有 **三层**：

| 层 | 干什么 | 走什么节点 |
|----|--------|------------|
| **① 纯读** | 查物料、查库存、统计、明细、追问 | **仅** 分类器 **DATA** → **DATA Fast** → Answer |
| **② 领料读** | 要领料时，先查料号+库存 | **领料子流程** 里的 **DATA Fast 读链**（在 Agent **之前**） |
| **③ 领料写** | 草稿、提交、查 GON | **Agent**（只 3 个 erp_* Tool） |

**铁律**：

- **纯查物料/库存** → 永远在 **①**，**不经过** 领料路由、**不经过** Agent。  
- **领料** → 先进 **②**（如需）再 **③**；**不是**「先判 Agent 再查库存」。  
- 画布上的 If `use_agent` / `use_requisition_flow` = **「进入领料子流程」**，**不是**「直进 Agent」。

---

## 1. 重排后的总图（推荐按此改画布）

```
用户输入
  │
  ▼
Code「登录路由」                         ← 不动
  │
  ▼
If should_login …                        ← 不动
  │
  └─ false
        │
        ▼
Code「领料/查单路由」                      ← detect_requisition_route.py
        │
        ▼
If use_requisition_flow == "true"        ← 建议改绑新字段（与 use_agent 同值）
  │
  ├─ true ──────────────┐
  │                     │
  └─ false              │
        │               │
        ▼               │
   问题分类器            │
        │               │
        ├─ DATA ──→ 【① DATA Fast】→ Fast Answer     ← 纯查物料/库存只走这
        ├─ CHITCHAT → 寒暄 Answer
        └─ ELSE ───→──┘   （领料/混合，与上面 true 汇合）
                          │
                          ▼
              ╔═══════════════════════════╗
              ║   领料子流程（② + ③）       ║
              ║                           ║
              ║  If 已登录?               ║
              ║    false → 提示登录        ║
              ║    true ↓                 ║
              ║  Code「是否本轮要读」       ║
              ║    true  → DATA Fast读链   ║
              ║    false →（跳过读）        ║
              ║         ↓                 ║
              ║       Agent（只写）        ║
              ║         ↓                 ║
              ║     Agent Answer          ║
              ╚═══════════════════════════╝
```

**一句话**：画布上拖一个 **「领料子流程」区块**；领料路由 true **和** 分类器 ELSE **都进这个区块**；**DATA 分支不要进这个区块**。

---

## 2. 各层举例

| 用户说 | 走哪一层 | 追踪里看到 |
|--------|----------|------------|
| `覆铜板还有多少` | ① 领料路由 **false** → 分类器 **DATA** → Fast | **无** 领料子流程、**无** Agent |
| `统计2025消耗` | ① 同上 | 仅 DATA Fast |
| `帮我领 10KG 油墨` | 领料路由 **true** → 领料子流程 → ② Fast读 → ③ Agent draft | 先 HTTP 再 Agent |
| `确认提交` | 领料路由 **true** → 领料子流程 → **跳过②** → ③ Agent submit | **无** HTTP |
| `查询 GONxxx 状态` | 领料路由 **true** → 跳过② → ③ Agent get | **无** HTTP |

---

## 3. 改画布：第一步（理顺 If 含义）

### 3.1 领料/查单路由 Code

粘贴最新 [`detect_requisition_route.py`](../workflows/code/detect_requisition_route.py)（含 `use_requisition_flow` 输出）。

### 3.2 改 If-Else 标题与条件（建议）

| 旧理解 | 新理解 |
|--------|--------|
| If `use_agent == true` → Agent | If `use_requisition_flow == true` → **领料子流程** |

Dify 条件可继续用 `use_agent`（值相同），**心里和节点标题改成「领料子流程」**。

- **true 出口**：接到 **§4 领料子流程入口**（不是 Agent）  
- **false 出口**：接到 **问题分类器**

### 3.3 分类器 If-Else 的 ELSE 分支

| 旧标签 | 建议改标签 |
|--------|------------|
| `agent` / 其他 | **领料子流程** |

**ELSE 出口** → 与 §3.2 的 **true 出口接到同一个「已登录？」节点**（两根线进同一节点）。

**DATA 出口** → 仍接 **① DATA Fast**，**不要**接到领料子流程。

---

## 4. 领料子流程内部（② 读 + ③ 写）

在画布上 **框一块区域**，标题可写「领料子流程」，内部顺序：

### 4.1 If-Else「已登录？」（阶段 4 已有，挪进块内或保持）

| 条件 | 出口 |
|------|------|
| `auth_token` 不为空 | → §4.2 |
| ELSE | → 提示验证身份 Answer |

### 4.2 Code「是否本轮要读」

| 项 | 值 |
|----|-----|
| 代码 | [`detect_requisition_need_inventory.py`](../workflows/code/detect_requisition_need_inventory.py) |
| query | `sys.query` |
| reason | `领料/查单路由 / reason`（从分类器进来的线 reason 为空即可） |

### 4.3 If-Else「路由-领料读或直写」

| 条件 | 出口 | 含义 |
|------|------|------|
| `need_fast_inventory == true` | → §5 DATA Fast 读链 | ② 先查料号+库存 |
| ELSE | → **Agent** | ③ 确认提交/查 GON，不再读 |

读链在「抽取」之后 **分叉**（§5.1）：**多条物料不进 Agent**。

---

## 5. DATA Fast 读链（仅领料子流程内 · ②）

```
组装领料查库存问题 → 组装Chat请求-领料 → HTTP-领料 → 解析SSE-领料
  → Code「解析领料查数结果」   ← extract_requisition_material_from_detail.py
  → If-Else（见 §5.1）
       ├─ pick_required=true  → Assigner(选型) → 选型 Answer  【结束，不进 Agent】
       ├─ extract_ok=true     → Assigner(物料) → Agent
       └─ 否则                → 提示 Answer
```

### 5.1 If-Else「路由-选型或写单」（★ 必配，接在抽取节点后）

| 条件 | 出口 | 说明 |
|------|------|------|
| `解析领料查数结果 / pick_required` **等于** `true` | → §5.2 选型分支 | 多种阻焊油墨等，**让用户选料号** |
| **ELSE IF** `extract_ok` **等于** `true` | → §5.3 Assigner → Agent | 料号已唯一确定 |
| **ELSE** | → Answer「未能识别物料」 | 表格解析失败等 |

> **多条物料时不要进 Agent**：选型由画布 Answer 完成；用户回复料号后 **下一轮** 再走本读链，通常 `extract_ok=true`。

### 5.2 选型分支（pick_required = true）

```
解析领料查数结果
  → Code「保存领料意图」save_requisition_intent.py（user_query=sys.query）
  → Assigner「写入选型变量」
  → 直接回复「选型 Answer」
```

**Assigner 写入**：

| 会话变量 | 来源 |
|----------|------|
| `requisition_pick_required` | `true` |
| `requisition_pick_list` | `pick_list` |
| `requisition_match_count` | `match_count` |
| `requisition_intent_query` | `保存领料意图 / requisition_intent_query` |
| `requisition_pick_waiting` | `true` |
| `requisition_inventory_detail` | 可选 |

**选型 Answer**：`{{#解析领料查数结果.pick_list#}}`  
**不进 Agent**。用户回复 `JS-NZ-006` 后见 §5.5 续流程。

### 5.3 唯一物料分支（extract_ok = true）

**Assigner「写入领料物料变量」**（并 **清空选型态**）：

| 会话变量 | 来源 |
|----------|------|
| `requisition_material_code` | `material_code` |
| `requisition_material_name` | `material_name` |
| `requisition_available_qty` | `available_qty` |
| `requisition_inventory_unit` | `unit` |
| `requisition_inventory_extract_ok` | `true` |
| `requisition_pick_required` | `false` |
| `requisition_pick_waiting` | `false` |
| `requisition_inventory_detail` | `解析SSE-领料 / detail`（可选） |

`extract` 节点增加入参：`pending_intent_query` ← `conversation.requisition_intent_query`（选型续单时带上一轮 10KG）

→ **Agent**（§6）

> **逐步点击**：[24-Dify选型多轮逐步点击清单.md](24-Dify选型多轮逐步点击清单.md)

### 5.4 各 Code 节点配置

| 节点 | 代码 / 绑定 |
|------|-------------|
| 组装领料查库存问题 | `build_requisition_inventory_query.py` |
| 组装Chat请求-领料 | `build_chat_messages_body.py`（conversation_id **空**） |
| HTTP-领料 | **复制 DATA HTTP 配置** |
| 解析SSE-领料 | `parse_sse_and_split.py` |
| **解析领料查数结果** | `extract_requisition_material_from_detail.py`；`detail` + **`user_query=sys.query`** |

不写 `data_analysis_conversation_id`。

会话变量全集：

| 变量 |
|------|
| `requisition_material_code` / `requisition_material_name` |
| `requisition_available_qty` / `requisition_inventory_unit` |
| `requisition_inventory_detail` / `requisition_inventory_extract_ok` |
| `requisition_pick_required` / `requisition_pick_list` / `requisition_match_count` |
| `requisition_intent_query` / `requisition_pick_waiting`（选型续单） |

---

## 5.5 多轮选型 + 续领料（Agent 是否共用）

| 轮次 | 用户 | 画布 | Agent |
|------|------|------|-------|
| 1 | 帮我领10KG阻焊油墨 | Fast → 多种 → **选型 Answer** | **不进** |
| 2 | JS-NZ-006 | 领料路由识别料号 → Fast 查一条 → extract_ok | **进** → save_draft |
| 3 | 确认提交 | 跳过 Fast | **进** → submit |

- **Agent 仍共用一个节点**，但 **只在 extract_ok 或确认提交/GON 时** 才执行。  
- 选型提醒 = 画布 **选型 Answer**（`pick_list`），不靠 Agent。  
- 第 1 轮 Assigner 写 `requisition_intent_query` 保留「10KG」；第 2 轮 extract 读 `pending_intent_query` + Agent Instruction 读同一变量。

---

## 6. Agent（仅 ③ 写）

- Tools：**仅** `erp_save_draft` / `erp_submit_requisition` / `erp_get_requisition`  
- Instruction：[阶段5领料版](../prompts/主控Agent系统提示词-阶段5领料版.md)  
- Answer：`{{#Agent.text#}}`

---

## 7. 发布前核对（防乱）

| # | 检查 |
|---|------|
| 1 | `查询覆铜板库存` → **仅** ① DATA Fast，**不出现** 领料子流程 |
| 2 | `帮我领10KG` → 领料子流程 → **先** HTTP **再** Agent |
| 3 | `确认提交` → 领料子流程 → **无** HTTP，**有** Agent submit |
| 4 | 分类器 **DATA** 线 **未** 接到领料子流程 |
| 5 | 领料路由 true 与分类器 ELSE **汇到同一** 已登录节点 |

---

## 8. 常见问题

**Q：为什么还要领料/查单路由 Code？分类器不够吗？**  
A：「帮我领」「确认提交」「GON」必须 **不进 ① DATA**；Code **确定性** 拦截，避免 LLM 把领料判成 DATA。

**Q：MIXED「查库存够的话领10KG」走哪？**  
A：领料路由或分类器 ELSE → **领料子流程** → ② 一次 Fast 查齐 → ③ Agent。

**Q：和 ① 的 DATA Fast 是不是两套 HTTP？**  
A：HTTP 配置相同；**①** 后接 Fast Answer；**②** 后接 Assigner → Agent。画布上 **复制两组节点**，不要共用一条线。

---

## 9. 相关文档

| 文档 | 用途 |
|------|------|
| [23-Dify领料画布连线逐步操作.md](23-Dify领料画布连线逐步操作.md) | 架构总图 |
| [24-Dify选型多轮逐步点击清单.md](24-Dify选型多轮逐步点击清单.md) | **逐步点击配画布** |
| [17-主助手路由与传参一览.md](17-主助手路由与传参一览.md) | 路由总览 |
| [15-DATA_QUERY-Fast查数路径配置详解.md](15-DATA_QUERY-Fast查数路径配置详解.md) | HTTP 字段 |
