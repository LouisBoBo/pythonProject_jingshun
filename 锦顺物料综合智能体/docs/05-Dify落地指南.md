# Dify 落地指南

> **平台版本**：Dify **1.13.x**  
> **术语**：现网 YAML 中 `advanced-chat` = 1.13 文档 **Chatflow**。  
> **完整对齐说明**：见 [07-Dify-1.13-技术对齐说明.md](07-Dify-1.13-技术对齐说明.md)。

## 1. 目标应用

| 项 | 建议（1.13） |
|----|----------------|
| 应用名称 | 锦顺物料综合助手 |
| 模式 | **Chatflow** + 画布内 **Agent 节点**（推荐） |
| 不推荐 | 独立 **Agent 应用**（无 Conversation Variables，无法沿用 `last_query` / draft） |
| Agent 策略 | **Function Calling**（模型支持时）或 **ReAct** |
| 依赖插件 | `langgenius/openai_api_compatible`、`jaguarliuu/rookie_text2data`、`bowenliang123/md_exporter` |
| 1.13 可选 | **Human Input 节点**（领料确认按钮） |
| 自建运维 | Celery 队列 **`workflow_based_app_execution`** 必须启用 |

---

## 2. 目录与文件规划

```
锦顺物料综合智能体/
├── README.md
├── docs/                          # 方案文档（本目录）
├── prompts/
│   └── 主控Agent系统提示词.md
└── workflows/                     # 待导出 / 维护的 Dify YAML
    ├── 锦顺-数据分析子流程.yml      # 从正式库拆分（待实施）
    └── 锦顺物料综合助手.yml         # 主 Agent 应用（待实施）
```

**当前状态**：`workflows/` 下 YAML 为规划占位，实施阶段从 `客户数据分析助手-正式库.yml` 拆分导出。

---

## 3. 实施步骤

### Step 1：环境变量

在 Dify App → 环境变量：

```
ERP_BASE_URL = https://<测试环境>/api
ERP_TIMEOUT_MS = 30000
```

数据库连接信息保留在 **数据分析子工作流** 的 `rookie_text2data` Tool 配置中（与现网一致）。

### Step 2：Conversation Variables

在 App → 会话变量新增：

| 名称 | 类型 |
|------|------|
| `auth_token` | string |
| `token_expires_at` | string |
| `user_profile` | object |
| `requisition_draft` | object |
| `last_material` | object |

沿用现有：`last_query`、`origan_data_records`、`data_records`。

### Step 3：拆分数据分析子工作流

从 `客户数据分析助手-正式库.yml` 提取子图：

**保留节点（建议）**：

- 问题分类器 `1775787700866` → 问题分类条件分支
- 追问链：历史数据判定 `1776734787260` → 问题合并 `1776736092059`
- SQL 生成 `1773988866174` → 提取 SQL → `rookie_excute_sql`
- 数据处理 Code 节点、变量 assigner
- 数据分析 LLM、ECharts、md_exporter

**子工作流输入**：

| 输入变量 | 说明 |
|----------|------|
| `question` | 用户问题（合并后） |

**子工作流输出**：

| 输出变量 | 说明 |
|----------|------|
| `answer` | 分析正文（Markdown） |
| `chart` | 可选图表 fence |
| `data_summary` | 简要摘要（供主 Agent Observation） |

导出为 `workflows/锦顺-数据分析子流程.yml`，在主 App 中 **发布为 Tool**。

### Step 4：配置 ERP HTTP Tools

路径：**Tools → Create Custom Tool** 或导入 OpenAPI。按 [ERP API 对接规范](04-ERP-API对接规范.md) 创建：

1. `erp_login`
2. `erp_search_material`
3. `erp_check_inventory`
4. `erp_save_draft`
5. `erp_submit_requisition`
6. `erp_get_requisition`
7. `erp_list_requisition`（可选）

业务 Tool 的 Header 示例：`Authorization: Bearer {{#conversation.auth_token#}}`

**登录写 token（1.13 要点）**：HTTP Tool **不会自动** 写入 Conversation Variables。在主 Chatflow 中：

- **推荐**：Agent 前增加 If-Else（`auth_token` 为空）→ HTTP 登录 → **Variable Assigner** 写入 `auth_token` / `user_profile`；或  
- **备选**：ERP 用 `sys.conversation_id` 维护服务端 Session。

### Step 5：主 Chatflow 内 Agent 节点

- 位置：User Input → [可选登录分支] → **Agent 节点** → Answer
- Agent Strategy：Marketplace 安装 **Function Calling** 或 **ReAct**
- Model：需支持 Tool Call（现网 Qwen3 需在 1.13 实测；不支持则用 ReAct）
- Instruction：粘贴 `prompts/主控Agent系统提示词.md`（可用 Jinja 引用 conversation 变量）
- Query：`sys.query`
- Tools：ERP Custom Tools + 已发布的 `query_material_data` Workflow Tool
- **Maximum Iterations**：建议 **10～15**

### Step 6：开场与推荐问题

**opening_statement**：

```
你好！我是锦顺物料助手，可以帮你查数据分析，也可以提交领料申请。
使用前请先登录（发送：登录 工号 密码），或由门户自动带入登录态。
```

**suggested_questions**：

```
统计2025年各月物料消耗金额
查询高精密事业部油墨物料库存
帮我申请领 10KG 阻焊油墨
我最近的领料单审批到哪了
```

---

## 4. 现有 YAML 节点改造对照

| 现有节点 ID / 名称 | 改造动作 |
|--------------------|----------|
| 问题分类器 `1775787700866` | 保留在 **子工作流** 内 |
| 生成SQL `1773988866174` | 保留在子工作流，提示词仍引用 `锦顺物料查询提示词1.md` |
| rookie_excute_sql | 子工作流内，**只读账号** |
| 数据分析 / ECharts | 子工作流内 |
| App 根 Start | 主 App：用户输入 → Agent |
| 无 | 主 App 新增 ERP Tools + 会话变量 |

---

## 5. 登录两种接入方式

### 方式 A：对话内登录

用户：`登录 zhangsan xxx`  
Agent 解析 → `erp_login` → Assigner 写 token

### 方式 B：SSO 预注入（推荐生产）

1. 门户页先调 ERP 登录 API
2. 嵌入 Dify Chat 时 URL 带 `?token=xxx` 或 Start 变量 `sso_token`
3. 首节点 Code：若 `sso_token` 有值则写入 `auth_token` 并调 ERP 用户信息接口

---

## 6. 确认卡片格式（Final Answer 模板）

Agent 在 submit 前应输出：

```markdown
### 领料申请确认

| 项目 | 内容 |
|------|------|
| 部门 | 高精密事业部 |
| 物料 | 阻焊油墨（M001234） |
| 数量 | 10 KG |
| 当前库存 | 25 KG（充足） |
| 用途 | 生产补料 |

请回复 **「确认提交」** 或 **「修改数量为 X」** / **「取消」**
```

---

## 7. 调试检查清单

- [ ] 未登录时领料 Tool 返回 401，Agent 引导登录
- [ ] 登录后 `user_profile.dept_name` 自动填入 draft
- [ ] 库存不足时不会自动 submit
- [ ] 连续两次「确认提交」不产生两张单（幂等）
- [ ] 数据分析 Tool 仍正确排除外发物料（原提示词铁律）
- [ ] 追问「提供明细」仍走子工作流充分性判定
- [ ] Token 过期后重新登录可继续

---

## 8. 方案 B 备选（不用 Agent 节点）

若 Agent 节点或 Tool Call 模型暂不可用，保留 **纯 Chatflow 分支**（与现网类似）：

```
User Input
  → LLM 意图五分法（DATA / FOLLOWUP / REQUISITION / MIXED / CHITCHAT）
  → If-Else 分支
      ├─ DATA* → 现有完整 YAML 流程（或调用数据分析 Tool）
      ├─ REQUISITION → HTTP + Parameter Extractor + Variable Assigner
      └─ MIXED → 串行 + Assigner 传递 last_material
```

无 Agent 节点时需手写多轮领料逻辑，体验弱于 **Chatflow + Agent 节点**。

## 9. 1.13 Human Input（领料确认，可选）

在领料提交前插入 **Human Input 节点**：

- 表单展示 draft 摘要（引用 `requisition_draft` 或上游变量）
- 按钮：`确认提交` / `修改` / `取消`
- Approve 分支 → `erp_submit_requisition`

需自建环境配置 Celery 队列 `workflow_based_app_execution`。

---

## 10. 相关文档

- [Dify 1.13 技术对齐说明](07-Dify-1.13-技术对齐说明.md)
- [总体架构方案](01-总体架构方案.md)
- [ReAct 复合智能体设计](02-ReAct复合智能体设计.md)
- [ERP API 对接规范](04-ERP-API对接规范.md)
- [实施计划与对接清单](06-实施计划与对接清单.md)
