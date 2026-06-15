# 锦顺物料综合智能体

基于 **Dify 1.13** 的 **数据分析 + 领料申请** 复合 ReAct 智能体方案。在现有 [`客户数据分析助手-正式库.yml`](../客户数据分析助手-正式库.yml)（`mode: advanced-chat` = **Chatflow**）能力之上，接入 ERP **登录 API** 与 **领料申请 API**。

> **平台对齐**：主应用采用 **Chatflow + Agent 节点**（非独立 Agent 应用），以使用 Conversation Variables 与现网追问记忆。详见 [Dify 1.13 技术对齐说明](docs/07-Dify-1.13-技术对齐说明.md)。

## 文档索引

| 文档 | 说明 |
|------|------|
| [**Dify 1.13 技术对齐说明**](docs/07-Dify-1.13-技术对齐说明.md) | **版本术语、应用形态、Tool/变量与 1.13 新特性** |
| [总体架构方案](docs/01-总体架构方案.md) | 系统分层、数据流、与现有 YAML 的关系 |
| [ReAct 复合智能体设计](docs/02-ReAct复合智能体设计.md) | 主控 Agent、Tool 划分、意图路由；**§5.2 扩展规范**；**§7 方案 C 混合编排** |
| [**主助手路由与传参一览**](docs/17-主助手路由与传参一览.md) | **阶段 3.5 配置主入口（4 类意图 + id + Fast/Agent）** |
| [**混合编排架构 · 推荐终态**](docs/13-混合编排架构-推荐终态.md) | 架构背景 |
| [记忆与会话设计](docs/03-记忆与会话设计.md) | Conversation Variables、草稿状态机、Token 管理 |
| [ERP API 对接规范](docs/04-ERP-API对接规范.md) | 登录、领料接口约定、Dify HTTP Tool 配置 |
| [Dify 落地指南](docs/05-Dify落地指南.md) | 应用形态、子工作流拆分、环境变量、改造对照 |
| [主控 Agent 系统提示词](prompts/主控Agent系统提示词.md) | 可直接粘贴到 Dify Agent 节点 |
| [**分步实施清单**](docs/08-分步实施清单.md) | **按阶段 0～8 逐步完成应用（本文档为实施主入口）** |
| [**阶段 1（Chatflow 版）Custom Tool 配置**](docs/10-阶段1-Chatflow转CustomTool配置指南.md) | **访问 API + query_material_data 自定义工具（推荐）** |
| [**阶段 3 操作手册**](docs/12-阶段3-主Chatflow与Agent操作手册.md) | 综合助手 Agent 骨架（阶段 3 过渡） |
| [**阶段 3.5 混合编排操作手册**](docs/14-阶段3.5-混合编排操作手册.md) | **Fast 查数 + Agent 领料（推荐主路径）** |
| [**阶段 4 登录与会话变量操作手册**](docs/18-阶段4-登录与会话变量操作手册.md) | **登录链 + auth_token + Agent 未登录拦截** |
| [**Dify 领料画布连线逐步操作**](docs/23-Dify领料画布连线逐步操作.md) | **阶段 5 画布拖线/绑变量（推荐先看）** |
| [**阶段 5 领料全流程操作手册**](docs/19-阶段5-领料全流程操作手册.md) | Agent Instruction + 验收 |
| [query_material_data OpenAPI 模板](../tools/query_material_data-openapi.yaml) | 导入自定义工具前改 servers.url |
| [Mock ERP 服务](../mock-erp/README.md) | **FastAPI 模拟登录/领料 API，ERP 未就绪时联调** |
| [实施计划与对接清单](docs/06-实施计划与对接清单.md) | 分阶段计划、ERP 交付物、安全合规 |

## 关联资产

| 路径 | 用途 |
|------|------|
| `../客户数据分析助手-正式库.yml` | 现有数据分析工作流（待拆为子工作流 Tool） |
| `../锦顺物料查询提示词1.md` | Text2SQL 提示词（数据分析 Tool 内使用） |
| `../锦顺判断历史数据是否可以回复用户问题.md` | 追问分支充分性判定（子工作流内保留） |
| `../锦顺帐号.md` | 客户需求摘要：领料申请 + 物料查询 |

## 核心原则

1. **写操作走 ERP API**：领料建单、提交、审批状态查询均调用 ERP，Dify 不直接 INSERT 生产表。
2. **读分析走现有链路**：统计、排名、图表等封装为 `query_material_data` Workflow Tool（Text2SQL 只读）。
3. **混合编排（推荐终态）**：纯查数走 **Fast 路径**（画布直连 Tool + Answer 绑变量）；领料/混合走 **Agent ReAct**；分析能力留在子 Chatflow。详见 [13-混合编排架构](docs/13-混合编排架构-推荐终态.md)。
4. **会话记忆 + 草稿状态机**：支持多轮补全领料单、承接上文物料与查询结果。

## 快速开始（实施顺序）

**请直接打开 [分步实施清单（阶段 0～8）](docs/08-分步实施清单.md)**，按 checkbox 逐步完成。

概要：

1. 阶段 0：Dify 1.13 环境、插件、ERP OpenAPI
2. 阶段 1：数据分析子 Chatflow → Publish as Tool
3. 阶段 2：ERP Custom Tools（登录 + 领料）
4. 阶段 3～6：主 Chatflow + Agent + 登录 + 领料 + 混合任务
5. 阶段 7～8：Human Input / SSO、回归与上线

## 版本

| 版本 | 日期 | 说明 |
|------|------|------|
| v1.0 | 2026-06-09 | 初版：架构 + ERP API + ReAct + 记忆 + Dify 落地 |
| v1.1 | 2026-06-09 | 对齐 Dify 1.13：Chatflow + Agent 节点、Human Input、部署队列 |
