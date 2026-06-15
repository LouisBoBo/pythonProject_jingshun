# Dify 1.13 技术对齐说明

> **目标版本**：Dify **1.13.x**（自建或云端）  
> **结论**：方案继续用 Dify 开发；主应用推荐 **Chatflow + Agent 节点**，而非独立 **Agent 应用**。  
> **现网基线**：`客户数据分析助手-正式库.yml` 中 `mode: advanced-chat` 即 1.13 文档所称 **Chatflow**。

---

## 1. 版本与术语对照

| 方案/现网用语 | Dify 1.13 官方用语 | 说明 |
|---------------|-------------------|------|
| Advanced Chat | **Chatflow** | 每轮用户消息触发一次流程；YAML 导出仍可能写 `advanced-chat` |
| Workflow | **Workflow** | 单次任务，Start → Output |
| Agent Chat（独立应用） | **Agent** | 独立应用类型，非画布内节点 |
| Agent 节点 | **Agent 节点** | Chatflow/Workflow 画布内的节点 |
| 会话变量 Conversation Variables | **Conversation Variables** | **仅 Chatflow** |
| Variable Assigner / assigner | **Variable Assigner 节点** | 写入会话变量 |
| 发布工作流为工具 | **Publish Workflow as Tool** | Agent 节点可挂载 |
| 问题分类 if-else | **If-Else 节点** | 现网已用 |
| 参数提取器 | **Parameter Extractor 节点** | 现网已用 |

---

## 2. 推荐应用形态（1.13 对齐后）

### ✅ 推荐：Chatflow + Agent 节点（主应用）

```
Chatflow「锦顺物料综合助手」
  Start（User Input）
    → [可选] 登录分支：HTTP + Variable Assigner 写 auth_token
    → Agent 节点（策略：Function Calling 或 ReAct）
         Tools:
           - query_material_data（已发布的 Chatflow/Workflow Tool）
           - erp_search_material / erp_check_inventory / …（Custom HTTP Tool）
    → Answer
```

**选择理由（1.13 硬性约束）**：

| 能力 | Chatflow + Agent 节点 | 独立 Agent 应用 |
|------|----------------------|-----------------|
| **Conversation Variables**（`auth_token`、`requisition_draft`、`last_query`） | ✅ | ❌ 不支持 |
| Variable Assigner 写会话状态 | ✅ | ❌ |
| ReAct / Function Calling | ✅ Agent 策略 | ✅ 内置 |
| 发布子流程为 Tool | ✅ | ✅ |
| 与现网 `advanced-chat` YAML 迁移 | ✅ 同类型 | 需重写记忆方案 |
| 数据分析追问 + `origan_data_records` | ✅ 子 Chatflow 内保留 | 难复现 |

### ⚠️ 不推荐：单独创建「Agent 应用」作为主入口

独立 Agent 应用在 1.13 中：

- 仅有内置对话记忆（约 **500 条消息 / 2000 tokens**，超出会裁最旧消息）
- 使用 **Prompt 变量**（Short Text、API-based Variable 等），**没有** Chatflow 的 Conversation Variables
- 无法沿用现网 `last_query` / `origan_data_records` / `requisition_draft` 方案，除非改由 **ERP 按 `conversation_id` 存会话状态**

若未来要做独立 Agent，需把 draft/token 全部外置到 ERP Redis，工作量更大。

---

## 3. 方案能力 ↔ Dify 1.13 映射

| 方案能力 | Dify 1.13 实现 | 对齐状态 |
|----------|----------------|----------|
| 复合 ReAct 智能体 | Agent 节点 + 策略 **ReAct** 或 **Function Calling** | ✅ |
| 智能路由（查数 / 领料） | Agent Instruction + Tool 描述；子 Chatflow 内保留查询/追问分类 | ✅ |
| 数据分析 | 子 **Chatflow** 发布为 Tool `query_material_data` | ✅ |
| Text2SQL | 插件 `rookie_text2data`（Tool 节点 `rookie_excute_sql`） | ✅ 现网已用 |
| 图表 / Excel | Code 节点 + `md_exporter` 插件 | ✅ 现网已用 |
| ERP 登录 / 领料 | **Custom Tool** 或 OpenAPI 导入 HTTP 请求 | ✅ |
| 会话记忆 `last_query` 等 | **Conversation Variables** + **Variable Assigner** | ✅ Chatflow |
| 领料 draft 状态机 | `requisition_draft` 会话变量；或 ERP draft API | ✅ |
| 领料提交前确认 | ① Agent 对话确认；② **1.13 Human Input 节点**（可选增强） | ✅ |
| 混合任务（先查后领） | Agent **Maximum Iterations** ≥ 10，多 Tool 顺序调用 | ✅ |
| 知识库 RAG | Agent 节点或子流程 LLM + Knowledge Retrieval | 可选 |
| LangChain 自研 | 不采用 | — |

---

## 4. Agent 节点配置（1.13）

在 **Studio → Chatflow → Agent 节点**：

| 配置项 | 建议值 | 说明 |
|--------|--------|------|
| Agent Strategy | **Function Calling**（模型支持时）或 **ReAct** | 从 Marketplace → Agent Strategies 安装 |
| Model | 支持 Tool Call 的模型（如 Qwen3 指令版 + openai_api_compatible 插件） | 与现网 `Qwen3-VL-30B-A3B-Instruct` 需验证 FC 支持 |
| Instruction | `prompts/主控Agent系统提示词.md` | 可用 Jinja 引用 `{{#conversation.user_profile#}}` 等 |
| Query | `sys.query` | 当前用户消息 |
| Maximum Iterations | **10～15** | 领料多步 + 混合任务 |
| Tools | ERP HTTP Tools + `query_material_data` | 见下节 |

**ReAct 说明**：1.13 的 ReAct 策略在 Agent 节点/独立 Agent 中由平台封装 Thought→Action→Observation，**无需**在画布手写循环。

---

## 5. Tool 类型与配置（1.13）

### 5.1 数据分析子流程 → Workflow Tool

1. 从 `客户数据分析助手-正式库.yml` 拆出 **Chatflow** `锦顺-数据分析子流程`
2. 在 **Start / User Input** 定义输入变量 `question`（String）
3. 末端 **Answer** 输出分析正文；可增加 Output 变量 `data_summary`
4. **Publish → Publish as Tool**
5. 在主 Chatflow 的 Agent 节点 **Tools** 中添加该 Tool，参数 `question` 由 Agent 自动填充或映射 `sys.query`

修改 Start 输入后需 **重新发布 Tool 并在 Agent 节点重新添加** 以同步 schema。

### 5.2 ERP 接口 → Custom Tool / OpenAPI

路径：**Tools → Create Custom Tool** 或导入 OpenAPI。

| Tool | 方法 | 鉴权 |
|------|------|------|
| erp_login | POST | 无 Bearer |
| erp_* 业务 | GET/POST | Header: `Authorization: Bearer {{#conversation.auth_token#}}` |

**注意**：HTTP Tool 执行后 **不会自动** 写入 Conversation Variables。登录写 token 需：

- **方式 A（推荐）**：主 Chatflow 在 Agent 前增加 **If-Else**（检测 `auth_token` 为空）→ HTTP 登录 → **Variable Assigner** 写入变量；或  
- **方式 B**：`erp_login` 做成 **子 Chatflow Tool**，Tool 输出 token 字符串，Agent 后再接 Code/Assigner（较绕）；或  
- **方式 C**：ERP 用 `sys.conversation_id` 维护服务端 Session，HTTP Tool 仅带 `X-Conversation-Id`

### 5.3 现网插件（1.13 兼容）

| 插件 | 用途 | 对齐 |
|------|------|------|
| `langgenius/openai_api_compatible` | 模型接入 | ✅ 现网 dependencies |
| `jaguarliuu/rookie_text2data` | SQL 执行 | ✅ 子 Chatflow 内 Tool 节点 |
| `bowenliang123/md_exporter` | MD→XLSX | ✅ 子 Chatflow 内 |

---

## 6. Conversation Variables（1.13 Chatflow）

在 **Chatflow → Variables → Conversation Variables** 创建：

| 变量 | 类型 | 写入方式 |
|------|------|----------|
| `last_query` | string | Variable Assigner（现网已有） |
| `origan_data_records` | string | 子 Chatflow 内 Assigner |
| `data_records` | string | 子 Chatflow 内 Assigner |
| `auth_token` | string | 登录分支 Variable Assigner |
| `token_expires_at` | string | 登录分支 Variable Assigner |
| `user_profile` | object | 登录分支 Variable Assigner |
| `requisition_draft` | object | Agent 调 `erp_save_draft` 后，由 **Code + Assigner** 或 ERP 回写同步 |
| `last_material` | object | search/inventory 后 Assigner |

引用语法（Instruction / HTTP Header）：`{{#conversation.auth_token#}}`

系统变量（Chatflow 内置）：`sys.query`、`sys.conversation_id`、`sys.dialogue_count`、`sys.user_id` 等。

---

## 7. Dify 1.13 新能力：Human Input（领料确认增强）

1.13 新增 **Human Input 节点**，可在流程中 **暂停**，展示表单与按钮（Approve / Reject 等），适合领料「确认提交」。

**两种确认方式（可并存）**：

| 方式 | 实现 | 适用 |
|------|------|------|
| 对话确认 | Agent Final Answer 展示表格，用户回复「确认提交」 | 与现方案一致，纯 Chat |
| Human Input | 领料子分支：Agent 生成 draft → Human Input 节点 → Approve 才调 submit | 更防误操作，需 1.13 部署正确 |

Human Input 依赖 **Celery 暂停/恢复**，见第 8 节运维要求。

---

## 8. 自建部署运维（1.13 升级必查）

若自建 Docker/Helm **1.13 升级**，官方要求：

1. Celery Worker 必须监听新队列：**`workflow_based_app_execution`**
2. Chatflow / Advanced Chat **流式执行** 走 Celery + Redis Pub/Sub
3. Human Input 恢复任务依赖同一队列
4. 高并发建议配置 `PUBSUB_REDIS_URL`、`PUBSUB_REDIS_CHANNEL_TYPE=sharded`

**未配置该队列时**：Chatflow 流式对话、HITL 暂停恢复可能 **无响应**。

---

## 9. 方案修正摘要（相对初版文档）

| 初版表述 | 1.13 对齐后 |
|----------|-------------|
| 主应用 **Agent Chat** | 主应用 **Chatflow**，核心推理用 **Agent 节点** |
| Advanced Chat + Agent 节点 | 即 **Chatflow + Agent 节点**（推荐写法） |
| Conversation Variables 在 Agent 应用 | 仅在 **Chatflow**；独立 Agent 改用 Prompt/API 变量或 ERP 存状态 |
| ReAct 手写循环 | 使用 Agent 策略 **ReAct** / **Function Calling** |
| 领料仅文字确认 | 可选用 **Human Input 节点**（1.13） |

---

## 10. 推荐模型与 Agent 模式

在 Agent 节点 **Agent Settings** 中查看自动识别的模式：

- 模型支持原生 Tool Call → **Function Calling**（优先）
- 否则 → **ReAct**

现网 `Qwen3-VL-30B-A3B-Instruct` 需在 1.13 中 **实测** Function Calling；若不支持，选 **ReAct** 策略并适当提高 Maximum Iterations。

---

## 11. 验收清单（1.13 专用）

- [ ] 主应用类型为 **Chatflow**（非独立 Agent App）
- [ ] Agent 节点已选 ReAct 或 Function Calling 策略
- [ ] `query_material_data` 已 Publish as Tool 并挂到 Agent
- [ ] Conversation Variables 可在调试面板看到更新
- [ ] ERP HTTP Tool Header 能引用 `{{#conversation.auth_token#}}`
- [ ] Celery 队列 `workflow_based_app_execution` 已配置（自建）
- [ ] 子 Chatflow 追问逻辑与现网 10+ 用例回归一致

---

## 12. 相关文档

- [Dify 落地指南](05-Dify落地指南.md)（已按 1.13 修订）
- [总体架构方案](01-总体架构方案.md)
- [记忆与会话设计](03-记忆与会话设计.md)

**官方参考**：

- [Agent 节点](https://docs.dify.ai/en/use-dify/nodes/agent)
- [Agent 应用（独立）](https://docs.dify.ai/en/use-dify/build/agent)
- [Chatflow / Workflow](https://docs.dify.ai/en/use-dify/build/workflow-chatflow)
- [Variable Assigner](https://docs.dify.ai/en/use-dify/nodes/variable-assigner)
- [Human Input](https://docs.dify.ai/en/use-dify/nodes/human-input)
- [1.13.0 Release](https://github.com/langgenius/dify/releases/tag/1.13.0)
