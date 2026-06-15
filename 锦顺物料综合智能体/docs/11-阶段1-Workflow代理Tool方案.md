# Workflow 薄代理 Tool：`query_material_data`（Agent 必用）

> **定位**：主控 **Agent 做意图识别**；查数能力仍由 **`锦顺-数据分析子流程`** API 提供。  
> 本 Workflow **不重复分析逻辑**，是 **Chatflow API 网关**（HTTP → 解析 SSE → 精简结果）。  
> **扩展规范**：禁止每加一个 API 就复制一个 proxy；见 [02-ReAct §5.2 扩展规范](02-ReAct复合智能体设计.md#52-扩展规范禁止一个能力一个代理-workflow)。

---

## 为什么需要这一层？

| 问题 | 说明 |
|------|------|
| Agent 只能调 Tool | 不能在 Agent 节点内拖 HTTP |
| Custom OpenAPI + streaming | Observation = 整段 SSE（10 万+ token）→ 模型爆上下文 |
| Custom OpenAPI + blocking | 锦顺现网 timeout |
| **Workflow 薄代理** | 内部 HTTP + Code，Tool 只返 `answer` + `conversation_id` |

与「主 Chatflow 手写 HTTP 节点」**同源**（都调 `/v1/chat-messages`），差别是 **包成 Agent 可选的 Tool**，便于以后加 `erp_*` 等扩展。

---

## 架构

```
锦顺物料综合助手（Chatflow）
  User Input → Agent（意图：查数 / 领料 / …）
                ↓ 查数
              query_material_data（Workflow Tool）
                → HTTP POST http://nginx/v1/chat-messages (streaming)
                → Code 解析 SSE
                → 输出 { answer, conversation_id }
                ↓
              子 Chatflow「锦顺-数据分析子流程」（已发布 API）
```

**追问**：同一 `conversation_id` 再次调 Tool → 子 Chatflow 内「查询/追问」分类与 `last_query` 等逻辑仍生效。

---

## 步骤 0：前置确认

- [ ] 子 Chatflow **`锦顺-数据分析子流程`** 已发布  
- [ ] API Key：`app-NxITngK2xpaL1nGYMiQFYye5`（或你的密钥）  
- [ ] 容器内 URL：`http://nginx/v1/chat-messages`（工具页用 `:15657` 外网仅作 curl 调试）

---

## 步骤 1：新建 Workflow

1. **Studio → 创建应用 → Workflow**
2. 名称：`query_material_data_proxy`（发布 Tool 后显示为 `query_material_data`）
3. **开始** 节点 → 输入变量：

| 变量名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `question` | 短文本 | 是 | 用户完整问题 |
| `conversation_id` | 短文本 | 否 | 追问时传入；首次留空 |

---

## 步骤 2：HTTP 请求节点

标题：`调用数据分析Chatflow`

| 项 | 值 |
|----|-----|
| 方法 | POST |
| URL | `http://nginx/v1/chat-messages` |
| 连接超时 | 600（秒，按 UI 可配项） |
| 读取超时 | 3600 |

**Headers**：

| Key | Value |
|-----|-------|
| Authorization | `Bearer app-NxITngK2xpaL1nGYMiQFYye5` |
| Content-Type | application/json |

**Body（JSON）**——用变量选择器绑定，示例：

```json
{
  "inputs": {},
  "query": "{{#开始.question#}}",
  "response_mode": "streaming",
  "user": "agent-tool-user",
  "conversation_id": "{{#开始.conversation_id#}}"
}
```

> - `query` ← **开始 / question**  
> - `conversation_id` ← **开始 / conversation_id**（首次为空字符串即可，API 会开新会话）  
> - 若 Dify 不允许空字段，可在 Code 前加条件分支：有 id 才带 `conversation_id` 字段（多数环境空字符串可工作）

---

## 步骤 3：Code 解析 SSE

标题：`解析SSE`

**输入**：

| 变量 | 来源 |
|------|------|
| `raw` | HTTP 请求 / **body**（或 text，以运行日志为准） |

**代码**：

```python
import json


def main(raw: str) -> dict:
    text = raw or ""
    chunks = []
    final_answer = ""
    conversation_id = ""

    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("data:"):
            continue
        payload = line[5:].strip()
        if not payload or payload == "[DONE]":
            continue
        try:
            obj = json.loads(payload)
        except json.JSONDecodeError:
            continue

        cid = obj.get("conversation_id")
        if cid:
            conversation_id = cid

        event = obj.get("event")
        if event == "message":
            part = obj.get("answer") or ""
            if part:
                chunks.append(part)
        elif event == "workflow_finished":
            data = obj.get("data") or {}
            outputs = data.get("outputs") or {}
            final_answer = outputs.get("answer") or final_answer
            cid = obj.get("conversation_id") or conversation_id
            if cid:
                conversation_id = cid

    answer = (final_answer or "".join(chunks)).strip()
    if not answer:
        answer = "数据分析未返回结果，请稍后重试或联系管理员。"

    summary, detail = _split_answer(answer)
    return {
        "answer": answer,
        "summary": summary,
        "detail": detail,
        "conversation_id": conversation_id or "",
    }


def _split_answer(answer: str) -> tuple[str, str]:
    """阶段 3.5+：拆分导语与全文。完整实现见 workflows/code/parse_sse_and_split.py"""
    import re
    text = (answer or "").strip()
    if not text:
        return "未返回结果，请稍后重试。", ""
    table_match = re.search(r"\n\s*\|", text)
    if table_match:
        head = text[: table_match.start()].strip()
        if head and len(head) >= 8:
            summary = head if len(head) <= 500 else head[:500] + "…"
            return summary, text
        return "查询完成，明细如下。", text
    if len(text) <= 300:
        return text, text
    return text[:300] + "…", text
```

**输出变量**：`answer`、`summary`、`detail`、`conversation_id`（string）

> **阶段 3.5**：请直接使用仓库 [`workflows/code/parse_sse_and_split.py`](../workflows/code/parse_sse_and_split.py) 全文替换，逻辑更完整。操作见 [14-阶段3.5-混合编排操作手册.md](14-阶段3.5-混合编排操作手册.md)。

---

## 步骤 4：结束节点

| 输出字段 | 来源 |
|----------|------|
| `summary` | 解析SSE / summary |
| `detail` | 解析SSE / detail |
| `conversation_id` | 解析SSE / conversation_id |
| `answer` | 解析SSE / answer（兼容 Agent Tool） |

Publish as Tool 时，Agent 会在 Observation 里看到 `summary`、`detail`、`conversation_id`（及兼容字段 `answer`），体积远小于 raw SSE。

---

## 步骤 5：Workflow 内自测

| 次序 | question | conversation_id | 期望 |
|------|----------|-----------------|------|
| 1 | `你好，请只回复两个字：收到` | 空 | answer=收到，conversation_id 非空 |
| 2 | `统计2025年各月物料消耗金额` | 空 | answer 含分析（1～5 分钟） |
| 3 | `提供明细` | **填步骤 1/2 返回的 id** | 子 Chatflow 追问链路生效 |

- [ ] 测试 1 通过  
- [ ] 测试 2 通过  
- [ ] （可选）测试 3 通过  

---

## 步骤 6：发布为 Tool

1. **发布 → 发布更新**  
2. **发布 → 发布为工具**  
3. 配置：

| 项 | 值 |
|----|-----|
| Tool 名称 | `query_material_data` |
| 描述 | 查询锦顺物料数据库：统计、排名、库存、采购、出入库、明细。用户问统计/查询/多少/排名/占比/趋势/明细/追问时使用。参数 question 为完整问题；追问时传入 conversation_id。不处理领料。 |
| 入参 | `question`（必填）、`conversation_id`（可选） |
| 出参 | `answer`、`conversation_id`（以 Dify 发布界面为准） |

4. **工具** 列表中确认来源为 **Workflow**，非 Custom OpenAPI

---

## 步骤 7：与 Custom OpenAPI 共存

| 工具 | 用途 |
|------|------|
| Custom OpenAPI `query_material_data` | 工具页 / curl 调试 API；**不要挂 Agent** |
| Workflow `query_material_data` | **Agent 专用** |

若两个同名，Agent 只勾选 **Workflow 版**；或把 OpenAPI 版改名为 `query_material_data_api_debug`。

---

## 步骤 8：挂到综合助手 Agent

见 [12-阶段3-主Chatflow与Agent操作手册.md](12-阶段3-主Chatflow与Agent操作手册.md)。

要点：

- Agent 工具：**Workflow 版** `query_material_data`  
- 模型建议：**Qwen3-VL-30B-A3B-Instruct**（勿用 4B 扛长 Observation）  
- Instruction：`prompts/主控Agent系统提示词-阶段3精简版.md`

---

## 步骤 9（阶段 6）：主应用存 conversation_id

主 Chatflow **会话变量** 增加：

| 变量 | 类型 | 说明 |
|------|------|------|
| `data_analysis_conversation_id` | String | 子 Chatflow API 会话 id |

**方式 A（推荐）**：Agent 调 Tool 后，在 Agent 与 Answer 之间加 **Variable Assigner**（或阶段 6 用 Code 从 Agent 最后一轮 Observation 解析）写入该变量；下次用户追问时 Instruction 要求 Agent 把 `conversation.data_analysis_conversation_id` 传入 Tool。

**方式 B（简单）**：Instruction 要求 Agent 从 **上一轮 Tool 返回 JSON** 中记住 `conversation_id` 并在追问时传入（依赖模型多轮记忆，不如 A 稳）。

阶段 3 可只做 Tool 侧 `conversation_id` 透传；主应用 Assigner 阶段 6 再加。

---

## 验收清单

- [ ] Workflow 短句 / 查数自测通过  
- [ ] 发布为 Tool，入参 `question` + 可选 `conversation_id`  
- [ ] 综合助手 Agent 挂 Workflow 版，**不挂** Custom OpenAPI 版  
- [ ] Agent 查数不再报 163840 tokens  
- [ ] （可选）Workflow 内 `提供明细` + conversation_id 追问通过  

---

## 常见问题

**Q：HTTP body 为空 / Code 无 answer**  
A：检查 HTTP 输出字段映射；临时在 Code 前加「模板转换」打印 `raw[:500]`。

**Q：HTTP timeout**  
A：加大 HTTP 节点超时；`docker/.env` 增加 `HTTP_REQUEST_MAX_READ_TIMEOUT=3600` 并重启 worker/api。

**Q：nginx 不通**  
A：改为 `http://api:5001/v1/chat-messages`。

**Q：和主 Chatflow HTTP 节点重复吗？**  
A：内部同样调 API；Workflow 版是为 **Agent 选 Tool** 服务，不是第二套分析。

---

## 相关文档

- [02-ReAct复合智能体设计.md](02-ReAct复合智能体设计.md) §5.2 **扩展规范（禁止 N 个代理 Workflow）**
- [10-阶段1-Chatflow转CustomTool配置指南.md](10-阶段1-Chatflow转CustomTool配置指南.md)
- [12-阶段3-主Chatflow与Agent操作手册.md](12-阶段3-主Chatflow与Agent操作手册.md)
