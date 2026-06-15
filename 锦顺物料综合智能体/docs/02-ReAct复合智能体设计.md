# ReAct 复合智能体设计

## 1. 设计目标

1. **统一入口**：一个对话界面同时支持数据分析与领料申请
2. **智能路由**：根据用户自然语言自动选择 Tool，无需用户切换模式
3. **ReAct 范式**：Thought → Action → Observation 多轮推理，支持复合任务与多轮补全
4. **子能力复用**：现有 Text2SQL + 分析 + 图表作为独立 Tool，不被领料逻辑污染

---

## 2. 角色分层

| 层级 | 角色 | 职责 | Dify 实现 |
|------|------|------|-----------|
| L0 | **主控 Agent（Orchestrator）** | 理解意图、规划步骤、选 Tool、汇总 Final Answer | Agent 节点（Function Calling / ReAct） |
| L1 | **数据分析 Tool** | 封装现有 YAML 子流程 | Workflow as Tool：`query_material_data` |
| L1 | **领料 Tool 组** | 登录、检索、库存、草稿、提交、查状态 | HTTP Request Tools |
| L1 | **导出 Tool（可选）** | Markdown → XLSX | 子工作流或独立 Tool |
| L2 | **专用 LLM** | SQL 生成、分析播报、充分性判定 | 子工作流内 LLM 节点（沿用现有） |

主控 Agent **不直接生成 SQL**，也不 **直接写 ERP 表**。

---

## 3. ReAct 循环规范

### 3.1 输出结构（系统提示词约束）

```
Thought: 分析用户意图、已有记忆、缺失字段、下一步 Tool
Action: tool_name({"param": "value"})
Observation: <工具返回，由系统自动注入>
...（可多轮）
Final Answer: 面向用户的自然语言（含表格、确认卡片、单号等）
```

### 3.2 决策规则摘要

| 用户表达 | Agent 行为 |
|----------|------------|
| 统计 / 查询 / 多少 / 排名 / 占比 / 趋势 | → `query_material_data` |
| 领料 / 申请 / 要料 / 出库申请 | → 领料 Tool 链 |
| 确认 / 提交 / 取消（且存在 draft） | → `erp_submit_requisition` 或更新 draft |
| 这个 / 上面 / 它 / 够领吗 | → 读 `last_material` / `requisition_draft` 再行动 |
| 单号 / 审批到哪 / 我的申请 | → `erp_get_requisition` |
| 先查再领 | → 分析或 inventory Tool → 领料链 |

### 3.3 领料 Tool 调用顺序（标准链）

```
1. erp_search_material     （用户未给明确料号时）
2. erp_check_inventory     （建单前必做）
3. erp_save_draft          （信息齐全，未确认前）
4. [Final Answer 确认卡片，等待用户]
5. erp_submit_requisition  （用户明确「确认提交」后，仅一次）
```

库存不足时：Observation 中说明缺口，询问是否仍提交或修改数量，**不得静默提交**。

---

## 4. 意图路由（五类）

替代现有主流程「查询 / 追问」二分类（二分类 **下沉** 到数据分析子工作流）。

| 意图代码 | 含义 | 路由 |
|----------|------|------|
| `DATA_QUERY` | 新的独立取数请求 | `query_material_data` |
| `DATA_FOLLOWUP` | 承接上文追问、下钻、要明细 | `query_material_data`（子流程内处理） |
| `REQUISITION` | 新建或修改领料草稿 | ERP 领料 Tool 链 |
| `REQUISITION_Q` | 查申请单 / 审批状态 | `erp_get_requisition` 等 |
| `MIXED` | 先查后领、查库存后申请 | 多 Tool 顺序调用 |
| `CHITCHAT` | 寒暄、能力说明 | 直接 Final Answer，不调 Tool |

主控 Agent 在 **Thought** 中隐式完成五类判定，无需单独 LLM 分类节点（可选：高并发场景加轻量前置分类降 Token）。

---

## 5. Tool 清单

| Tool 名 | 类型 | 说明 |
|---------|------|------|
| `erp_login` | HTTP | 登录，写入 `auth_token`、`user_profile` |
| `erp_search_material` | HTTP | 关键字 / 料号搜物料 |
| `erp_check_inventory` | HTTP | 查可用库存 |
| `erp_save_draft` | HTTP | 创建或更新领料草稿 |
| `erp_submit_requisition` | HTTP | 提交审批（需用户确认后） |
| `erp_get_requisition` | HTTP | 按单号查状态 |
| `erp_list_requisition` | HTTP | 我的申请列表（可选） |
| `query_material_data` | **Workflow Tool（代理）** | 内调子 Chatflow API；Code 只返 `answer`（+ `conversation_id`）。**不可**把 streaming Custom OpenAPI 直接挂 Agent（Observation 过大） |
| `export_data_xlsx` | Workflow / HTTP | Excel 导出（可选） |

### 5.1 Tool 封装原则（Agent 架构下）

主控 **Agent 负责意图识别与选 Tool**；各能力以 **Tool** 形式扩展（查数、领料、以后新功能各加一个 Tool）。

| Tool 返回形态 | 封装方式 | 示例 |
|---------------|----------|------|
| **小 JSON**（几 KB 内） | Custom OpenAPI / HTTP Tool 直连 | `erp_login`、`erp_check_inventory` |
| **大响应 / SSE 流**（子 Chatflow API） | **Workflow 薄代理**：内部 HTTP + Code 解析，Publish as Tool | `query_material_data` |
| **复杂多步** | 独立 Workflow Publish as Tool | 未来导出、审批流等 |

**Workflow 代理的用意**：不是重复造数据分析，而是 **Agent 只能调 Tool、不能拖 HTTP 节点**；子 Chatflow API 的 streaming 若原样进 Observation 会撑爆上下文。代理 Workflow 内部仍是 **HTTP 调已发布 API**，与主 Chatflow 里手写 HTTP 节点 **同源**，只是 **包成 Agent 可调的一个 Tool**。

**主 Chatflow 直接 HTTP 分支**（方案 B）：适合不用 Agent 做路由时；与「Agent 统一意图识别、可扩展多 Tool」的目标不一致，**不作为本方案主路径**。

详见 [11-阶段1-Workflow代理Tool方案.md](11-阶段1-Workflow代理Tool方案.md)。

### 5.2 扩展规范：禁止「一个能力一个代理 Workflow」

> **问题**：若每上一个 Chatflow API 就复制一份 `xxx_proxy` Workflow，Dify 里会堆一堆几乎相同的应用，难维护。  
> **原则**：**Agent Tool 可以多个，Workflow 代理应用应极少（理想 1 个）**。

#### 5.2.1 什么要 Workflow 代理，什么不要

| 后端返回 | Agent 封装 | 是否新建 Workflow 应用 |
|----------|------------|------------------------|
| 小 JSON（几 KB） | Custom OpenAPI / HTTP Tool | **否** |
| SSE / 超大正文（Chatflow streaming API） | 需 HTTP + 解析后再给 Agent | **不新建**；扩展现有网关 |
| 复杂多步编排（导出、审批链） | 独立 Workflow Publish as Tool | **是**（按**业务域**，非按每个 HTTP 接口） |

**记一条规则**：  
- **Tool 名** = Agent 意图粒度（`query_material_data`、`erp_login`…）→ 可以随功能增加。  
- **Workflow 应用** = 仅当 Dify 内无法避免的多步编排，或 **唯一的 Chatflow API 网关** → 不应与 Tool 1:1 膨胀。

#### 5.2.2 当前阶段（MVP）

| 组件 | 数量 | 说明 |
|------|------|------|
| 子 Chatflow `锦顺-数据分析子流程` | 1 | 真正干查数 |
| Workflow `query_material_data` | 1 | **Chatflow API 网关**（streaming → answer） |
| Custom OpenAPI `query_material_data_*` | 0～1 | 仅 API 调试，**不挂 Agent** |
| 主 Chatflow `锦顺物料综合助手` | 1 | Agent 意图路由 |
| `erp_*` Custom Tool | 多个 | 各接口一个 Tool，**无 Workflow** |

#### 5.2.3 以后加功能怎么做

**✅ 推荐**

| 新需求 | 做法 |
|--------|------|
| 新 ERP 接口 | 新增 **Custom OpenAPI Tool**（`erp_xxx`）+ Instruction 一条选型规则 |
| 第二个 Chatflow API（同类 streaming） | **扩展同一个** Chatflow 网关 Workflow：Start 增加 `target` / `action`，Code 或 If-Else 选 URL + Key |
| 导出 Excel、多步审批 | 单独 **业务 Workflow** Publish as Tool（一个域一个，不是每个 URL 一个） |
| 统一出站 | 可选：仓库外 **一个 FastAPI 网关**（与 `mock-erp` 并列），Dify 侧 **全部 Custom OpenAPI 收 JSON** → **Dify 内零代理 Workflow** |

**❌ 禁止**

- 为每个 Chatflow API 复制 `数据分析_proxy2`、`数据分析_proxy3`…
- 为每个 `erp_*` 接口各建 Workflow（JSON 直连即可）
- Custom OpenAPI streaming **直接挂 Agent**（Observation 撑爆上下文）

#### 5.2.4 推荐终态：通用 Chatflow 网关（一个 Workflow Tool）

当存在 **≥2 个** streaming Chatflow API 时再演进；MVP 可仍用单目标网关，但 **命名与文档** 按网关理解：

```
Tool 名（Agent 可见）：query_material_data 或 invoke_chatflow
Workflow Start 入参：
  - question（必填）
  - conversation_id（可选）
  - target（可选，默认 material_analytics）

内部：
  target = material_analytics → POST 锦顺-数据分析子流程 API
  target = xxx             → POST 未来其他 Chatflow API（配置表，非新建 Workflow）
Code：解析 SSE → { answer, conversation_id }
End：输出上述两字段
```

新增 Chatflow 后端时：**改网关配置 / 加分支**，不新建 Dify Workflow 应用。

#### 5.2.5 与「主 Chatflow 直接 HTTP」的取舍

| | Agent + Tool | 主画布 HTTP 分支 |
|--|--------------|------------------|
| 意图识别、持续扩展 | ✅ | ❌ 每加能力改画布 |
| Workflow 应用数量 | 可控（网关 1 个） | 0 |
| 是否符合本项目目标 | ✅ 主路径 | 仅作不用 Agent 时的备选 |

#### 5.2.6 评审清单（加新 Tool 前自问）

1. 返回体是否 **小 JSON**？→ Custom OpenAPI，**不要** Workflow。  
2. 是否 **另一个 streaming Chatflow**？→ **扩网关**，不要新建 `_proxy`。  
3. 是否 **多步 Dify 编排**？→ 一个 **业务域** 一个 Workflow Tool。  
4. Agent Instruction 是否 **只加选型规则**，而不是复制画布？  

---

## 6. 复合任务示例

### 示例 A：查库存 + 申请

**用户**：高精密事业部阻焊油墨还有多少？够的话帮我领 10KG。

```
Thought: 混合任务，需先查库存再可能提交领料；需已登录。
Action: erp_check_inventory({"material_keyword": "阻焊油墨", "factory": "高精密事业部"})
Observation: 可用 25 KG
Thought: 库存充足，用户已指定 10KG，可建草稿。
Action: erp_save_draft({...})
Observation: draft_id=DRAFT-001
Final Answer: 【领料确认】... 回复「确认提交」继续。
```

### 示例 B：数据分析后追问再领料

**用户1**：统计 2025 年油墨类物料消耗  
**用户2**：消耗最多的那个，帮我领 5 箱

```
Thought: 追问型领料，需从上次分析结果或重新 search 解析物料。
Action: erp_search_material({...}) 或读 last_material
...
```

---

## 7. Dify 落地形态（三方案）

### 方案 C：混合编排（**推荐终态**，Dify 1.13）

> 全文见 [13-混合编排架构-推荐终态.md](13-混合编排架构-推荐终态.md)

- 主应用：**Chatflow** + **意图 Router** + **双执行器** + **Presenter 绑变量**
- **纯查数 / 纯追问** → Fast 路径：画布直连 `invoke_chatflow` 网关 → Assigner → Answer 绑 `summary` + `detail`（**无 Agent ROUND 2 抄表**）
- **领料 / 混合 / 寒暄** → Agent 路径：ReAct/FC + `erp_*` + 网关 Tool；查数结果 **detail 仍走变量直连**
- **分析能力** 留在子 Chatflow；主 Agent **不** Text2SQL、**不**二次分析、**不**重生成大段表格

```
User Input → 意图分类（五类）
  ├─ DATA_QUERY / DATA_FOLLOWUP → 网关 Tool → Assigner → Answer（变量）
  └─ REQUISITION / MIXED / …     → Agent → Assigner → Answer（短文案 + 变量）
```

**实施节奏**：阶段 3 可用方案 A 验收；**阶段 3.5 升级至方案 C**（不必等 ERP）。

### 方案 A：Chatflow + Agent 节点 + Tools（阶段 3 过渡）

- 画布：`User Input → Agent → Answer`；Agent 做意图识别并调 Tool
- **查数**：`query_material_data` = Workflow 薄代理
- **领料**：`erp_*` = Custom OpenAPI
- **局限**：查数后 Agent 需 Final Answer，易 **多 ~10s 抄表**（见方案 C）

> 子 Chatflow **不能** Publish as Tool（advanced-chat）；Custom OpenAPI streaming **不能**直接挂 Agent。

### 方案 B：纯 Chatflow 意图分支（备选，不为主路径）

```
User Input → 意图分类 → If-Else
  ├─ 数据分析 → 现有 YAML 流程
  ├─ 领料     → HTTP + Parameter Extractor + Variable Assigner
  └─ 混合     → 串联 + Assigner 传递 last_material
```

**不采纳为主路径**：每加能力需改画布，难以承载「查数 + 领料 + 未来 N 个 Tool」的统一编排。

**建议**：阶段 3 用 **方案 A** 跑通；**阶段 3.5 起以方案 C 为架构主路径**；1.13 自建需 Celery 队列 `workflow_based_app_execution`。

---

## 8. 模型策略

| 节点 | 建议 | 说明 |
|------|------|------|
| 主控 Agent | 较强模型 | 规划、Tool 选择、确认交互 |
| Text2SQL | 现有 Qwen3-VL-30B 或专用模型 | temperature 偏低 |
| 问题分类 / 充分性判定 | 小模型 / 低 temperature | 子工作流内保留 |
| 领料参数提取 | temperature = 0 | 结构化 JSON |

---

## 9. 失败与降级

| 情况 | Agent 行为 |
|------|------------|
| Tool 超时 | 告知用户稍后重试，draft 已保存则提示 draft_id |
| 401 Unauthorized | 清空 token，引导重新登录 |
| 库存不足 | 展示缺口，询问修改数量或取消 |
| SQL 执行失败 | 子工作流返回错误信息，Agent 转述，不编造数据 |
| 用户重复「确认提交」 | 依赖 ERP 幂等键，避免重复建单 |

---

## 10. 相关文档

- [主控 Agent 系统提示词](../prompts/主控Agent系统提示词.md)
- [记忆与会话设计](03-记忆与会话设计.md)
- [Dify 落地指南](05-Dify落地指南.md)
