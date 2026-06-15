# 阶段 3 操作手册：主 Chatflow + Agent（仅查数）

> **架构说明**  
> - 阶段 3 画布为 **过渡方案**（纯 Agent），用于跑通 Tool 与意图。  
> - **推荐终态**为 [13-混合编排架构-推荐终态.md](13-混合编排架构-推荐终态.md)（Fast 查数 + Agent 领料/混合）。  
> - 阶段 3 验收通过后，按 **§ 阶段 3.5** 升级画布，不必等 ERP。

> **前置**  
> 1. 子 Chatflow **`锦顺-数据分析子流程`** 已发布 API  
> 2. **Workflow 薄代理** `query_material_data` 已 [发布为 Tool](11-阶段1-Workflow代理Tool方案.md)（**必做，勿用 Custom OpenAPI 挂 Agent**）  
>  
> **目标**：**Agent 意图识别** + 查数 Tool；领料阶段 2 再挂 `erp_*`。

---

## 总览

```
用户输入 → Agent（ReAct）
              ├─ 查数 / 追问 → query_material_data（Workflow Tool）
              └─ 寒暄 / 领料未开 → 直接回复
           → 直接回复
```

---

## 步骤 3.0 完成 Workflow 薄代理（若尚未做）

按 **[11-阶段1-Workflow代理Tool方案.md](11-阶段1-Workflow代理Tool方案.md)** 全文操作，至少完成：

- [ ] Workflow 自测：短句 `收到`  
- [ ] **发布为工具** `query_material_data`（入参 `question`，可选 `conversation_id`）  
- [ ] Agent **不要**挂 Custom OpenAPI 同名工具  

---

## 步骤 3.1 创建主应用

1. **Studio → 创建应用 → Chatflow**  
2. 名称：**`锦顺物料综合助手`**

- [ ] Chatflow 已创建  

---

## 步骤 3.2 会话变量

| 变量名 | 类型 | 默认值 | 阶段 |
|--------|------|--------|------|
| `auth_token` | String | 空 | 4 |
| `token_expires_at` | String | 空 | 4 |
| `user_profile` | Object | `{}` | 4 |
| `requisition_draft` | Object | `{}` | 5 |
| `last_material` | Object | `{}` | 5 |
| `data_analysis_conversation_id` | String | 空 | 6 追问优化 |

阶段 3 可先建前 5 个；第 6 个可选提前建。

- [ ] 会话变量已保存  

---

## 步骤 3.3 Agent Strategy

- [ ] 已安装 **ReAct** 或 **Function Calling**（阶段 0 应已完成）

---

## 步骤 3.4 画布

```
用户输入 → Agent → 直接回复
```

### Agent 配置

| 项 | 值 |
|----|-----|
| 策略 | **ReAct** |
| 模型 | **Qwen3-VL-30B-A3B-Instruct**（推荐；4B 易在查数后爆上下文） |
| Query | `sys.query` |
| 最大迭代 | **12** |
| Instruction | [主控Agent系统提示词-阶段3精简版.md](../prompts/主控Agent系统提示词-阶段3精简版.md) 全文 |
| 工具 | **Workflow 版** `query_material_data` **仅此一个** |

### Answer

- 回复 ← **Agent / text**（或最终输出）

- [ ] 已挂 Workflow Tool，未挂 Custom OpenAPI  

---

## 步骤 3.5 开场白

```
你好！我是锦顺物料助手，可以帮你查询物料用量、库存、采购与出入库等数据分析。
直接说你的问题即可，例如：统计2025年各月物料消耗金额。

（领料申请功能即将上线）
```

推荐问题：

1. 统计2025年各月物料消耗金额  
2. 查询高精密事业部油墨物料库存  
3. 你能帮我做什么  

---

## 步骤 3.6 预览测试

| # | 输入 | 期望 |
|---|------|------|
| 1 | 你好，你能做什么？ | 不调 Tool |
| 2 | 统计2025年各月物料消耗金额 | 调 Tool；1～5 分钟内有分析 |
| 3 | 提供明细（紧接 #2 同会话） | 再调 Tool；Agent 应传 conversation_id |
| 4 | 帮我领 10KG 阻焊油墨 | 提示领料未开通 |

**日志**：预览追踪中应见 `query_material_data`，且 **无** 163840 tokens 报错。

---

## 步骤 3.7 发布

- [ ] **发布 → 发布更新**

---

## 阶段 3 验收

- [ ] Agent 意图识别：查数 vs 寒暄 vs 领料拒绝  
- [ ] Workflow Tool 查数成功  
- [ ] 无 Custom OpenAPI SSE 爆 token  
- [ ] （可选）同会话追问「提供明细」  

---

## 下一步

| 阶段 | 内容 |
|------|------|
| **3.5** | **混合编排**：意图分类 + Fast 查数 + Answer 绑变量（见下节） |
| 2 | Mock ERP → `erp_*` Tools |
| 4～5 | 登录、领料；Agent 换完整版提示词 |
| 6 | 网关 `summary`/`detail` 拆分 + 追问变量优化 |

---

## 阶段 3.5：升级混合编排（推荐，阶段 3 验收后）

> **逐步操作请打开**：[14-阶段3.5-混合编排操作手册.md](14-阶段3.5-混合编排操作手册.md)  
> 目标：查数 **~18s**（无 Agent 抄表）+ 保留 Agent 扩展领料/混合任务。

### 3.5 概要（11 步）

| 步 | 内容 |
|----|------|
| 1 | 网关 Code 升级 → 输出 summary / detail / conversation_id |
| 2 | 为网关 Workflow 创建 API Key |
| 3 | 主 Chatflow 增加 3 个会话变量 |
| 4 | 问题分类器（5 类）→ [意图分类器-阶段3.5.md](../prompts/意图分类器-阶段3.5.md) |
| 5 | If-Else：fast_query / chitchat / agent |
| 6 | Fast：HTTP `workflows/run` → Code → Assigner → Answer 绑变量 |
| 7 | CHITCHAT：短 LLM |
| 8 | Agent 分支换 [阶段3.5混合版 Instruction](../prompts/主控Agent系统提示词-阶段3.5混合版.md) |
| 9～11 | 联调、验收、发布 |

### 3.5 验收

| # | 输入 | 期望 |
|---|------|------|
| 1 | 查询2025年各分类物料入库数量 | Fast 路径；~18s；追踪无 Agent |
| 2 | 提供明细（同会话） | Fast；带 conversation_id |
| 3 | 你好 | CHITCHAT |
| 4 | 帮我领 10KG 油墨 | Agent |

---

## 相关文档

- [**14-阶段3.5-混合编排操作手册.md**](14-阶段3.5-混合编排操作手册.md)  
- [**13-混合编排架构-推荐终态.md**](13-混合编排架构-推荐终态.md)  
- [11-阶段1-Workflow代理Tool方案.md](11-阶段1-Workflow代理Tool方案.md)  
- [02-ReAct复合智能体设计.md](02-ReAct复合智能体设计.md)
