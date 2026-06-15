# DATA_QUERY → Fast 查数：详细流程与配置

> **适用**：主 Chatflow「锦顺物料综合助手」· 问题分类器输出 **DATA_QUERY**（新问查数）  
> **同类**：**DATA_FOLLOWUP** 走 **同一套 Fast 节点**，仅 `conversation_id` 不同（见 §6）  
> **前置**：[14-阶段3.5-混合编排操作手册.md](14-阶段3.5-混合编排操作手册.md) 步骤 1～2（网关 + Workflow API Key）

---

## 1. 端到端流程（DATA_QUERY）

```
用户：「查询2025年各分类物料入库数量」
  │
  ▼
┌─────────────────────────────────────────────────────────────┐
│ 主 Chatflow · 锦顺物料综合助手                                  │
│                                                             │
│  [用户输入] sys.query = 用户原话                              │
│       │                                                     │
│       ▼                                                     │
│  [问题分类器] → class_name = DATA_QUERY  （~0.5～1s）          │
│       │                                                     │
│       ▼                                                     │
│  [If-Else / 问题分类条件分支]                                 │
│   条件：class_name is DATA_QUERY OR DATA_FOLLOWUP            │
│       │                                                     │
│       ▼  fast_query 分支                                     │
│  [HTTP] POST http://nginx/v1/workflows/run  （blocking）     │
│       inputs.question = sys.query                           │
│       inputs.conversation_id = ""  （DATA_QUERY 首次为空）     │
│       │  ~17～20s（等网关 + 子流程）                           │
│       ▼                                                     │
│  [Code] 解析网关 blocking JSON → summary/detail/id          │
│       │                                                     │
│       ▼                                                     │
│  [Variable Assigner] 写入 3 个会话变量                         │
│       │                                                     │
│       ▼                                                     │
│  [直接回复] last_query_summary + last_query_detail            │
│       （无 Agent，无 ROUND 2 抄表）                            │
└─────────────────────────────────────────────────────────────┘
  │
  ▼ HTTP workflows/run 触发
┌─────────────────────────────────────────────────────────────┐
│ 网关 Workflow · query_material_data_proxy                    │
│                                                             │
│  [开始] question / conversation_id                          │
│       │                                                     │
│       ▼                                                     │
│  [HTTP] POST http://nginx/v1/chat-messages  （streaming）    │
│       query = question                                      │
│       conversation_id = "" （新开会话）                        │
│       Authorization: Bearer app-NxITngK2xpaL1nGYMiQFYye5    │
│       │                                                     │
│       ▼                                                     │
│  [Code 解析SSE] parse_sse_and_split.py                       │
│       → summary / detail / conversation_id / answer          │
│       │                                                     │
│       ▼                                                     │
│  [结束] 输出给 workflows/run 的 data.outputs                 │
└─────────────────────────────────────────────────────────────┘
  │
  ▼ chat-messages streaming
┌─────────────────────────────────────────────────────────────┐
│ 子 Chatflow · 锦顺-数据分析子流程                              │
│  问题分类(查询) → Text2SQL → 执行SQL → 数据分析 → 表格/导出    │
└─────────────────────────────────────────────────────────────┘
```

**DATA_QUERY 与阶段 3 纯 Agent 的差别**：意图在 **问题分类器** 完成；查数结果由 **Answer 绑变量** 展示，不经 Agent Final Answer。

---

## 2. If-Else：把 DATA_QUERY 接到 Fast 分支

### 2.1 节点类型

Dify 1.13 二选一（与现网正式库一致即可）：

| 方式 | 节点 | 说明 |
|------|------|------|
| A | **If-Else** | 手动写条件 |
| B | **问题分类条件分支** | 分类器下游自动带出 class 出口 |

### 2.2 方式 A · If-Else 条件（推荐看懂逻辑时用）

添加 **If-Else** 节点，标题：`路由-查数Fast或Agent`

**IF 条件（满足任一即可，用 OR 组合）**：

| 左值 | 操作符 | 右值 |
|------|--------|------|
| `{{#问题分类器.class_name#}}` | is | `DATA_QUERY` |
| `{{#问题分类器.class_name#}}` | is | `DATA_FOLLOWUP` |

> 节点名以你画布为准，常见为 `问题分类器` / `Question Classifier`；class 字段可能是 `class_name` 或 `category`，**以运行日志里实际字段名为准**。

**分支连线**：

| 出口 | 连接 |
|------|------|
| **IF = true** | → `HTTP 调用查数网关`（Fast 链起点） |
| **ELIF** | 条件：`class_name` is `CHITCHAT` → `LLM 寒暄` |
| **ELSE** | → `Agent` 节点 |

### 2.3 方式 B · 问题分类条件分支

1. 问题分类器节点拖出 **「添加分支」**  
2. 为 `DATA_QUERY`、`DATA_FOLLOWUP` 各建一条线，**合并**接到同一 HTTP 节点（或加 **变量聚合** 再进 HTTP）  
3. `CHITCHAT` → LLM；`REQUISITION` / `MIXED` → Agent  

---

## 3. 节点 ① HTTP「调用查数网关」

### 3.1 基本配置

| 配置项 | 值 |
|--------|-----|
| 节点标题 | `调用查数网关` |
| 方法 | **POST** |
| URL | 见下方 **§3.1.1 SSRF 与 URL 选型**（勿盲目用 `http://nginx/...`） |
| 连接超时 | **600** 秒 |
| 读取超时 | **3600** 秒 |
| 失败时重试 | 关（或 0 次） |

#### 3.1.1 SSRF 与 URL 选型（锦顺现网实测）

| URL | 现象 | 结论 |
|-----|------|------|
| `http://nginx/v1/workflows/run` | SSRF blocked | Chatflow HTTP **不可用** |
| `http://120.238.80.70:15657/v1/workflows/run` | Reached maximum retries (0) | 容器 **hairpin** 访问本机公网 IP 失败 |
| **`http://nginx/v1/chat-messages`** | 需运维 NO_PROXY 后可用 | **推荐终态**（与网关同源） |
| **`http://120.238.80.70:15657/v1/chat-messages`** | 若仍 max retries | 与上相同，必须 **NO_PROXY + nginx** |

**现网 Fast 路径请按 [§12 直连 chat-messages](#12-推荐fast-路径直连-chat-messages锦顺现网)** 配置；运维完成 §13 后可将 URL 改为 `http://nginx/v1/chat-messages`。

### 3.2 Headers

| Key | Value |
|-----|-------|
| `Authorization` | `Bearer app-xxxxxxxx` ← **网关 Workflow 的 API Key**（不是子 Chatflow Key） |
| `Content-Type` | `application/json` |

### 3.3 Body（JSON）— DATA_QUERY 专用绑定

在 Dify HTTP 节点选 **JSON**，用变量选择器绑定（不要手打错变量名）：

```json
{
  "inputs": {
    "question": "{{#sys.query#}}",
    "conversation_id": "{{#conversation.data_analysis_conversation_id#}}"
  },
  "response_mode": "blocking",
  "user": "fast-path-user"
}
```

| 字段 | DATA_QUERY（新问） | 说明 |
|------|-------------------|------|
| `inputs.question` | `sys.query` | **用户原话**，不要改写 |
| `inputs.conversation_id` | 会话变量（通常为空） | 首次查数应为 `""`；Assigner 写入后追问才有值 |
| `response_mode` | `blocking` | Workflow Run 用 blocking；内部网关仍 streaming 调子 Chatflow |
| `user` | 固定字符串 | 区分调用来源，任意即可 |

### 3.4 HTTP 输出映射

运行一次预览后，在 **Code 节点** 输入里选：

- 优先：**HTTP 请求 / body**  
- 若无内容：选 **HTTP 请求 / text** 或 **response body**（以追踪日志为准）

---

## 4. 节点 ② Code「解析网关响应」

### 4.1 配置

| 项 | 值 |
|----|-----|
| 标题 | `解析网关响应` |
| 代码 | 粘贴 [`workflows/code/parse_workflow_run_response.py`](../workflows/code/parse_workflow_run_response.py) 全文 |

### 4.2 输入变量

| Code 入参 | 绑定来源 |
|-----------|----------|
| `raw` | `调用查数网关` / **body**（或 text） |

### 4.3 输出变量（在 Code 节点声明）

| 输出名 | 类型 |
|--------|------|
| `summary` | String |
| `detail` | String |
| `conversation_id` | String |

### 4.4 期望解析结果示例（DATA_QUERY 成功后）

blocking 响应结构（节选）：

```json
{
  "data": {
    "status": "succeeded",
    "outputs": {
      "summary": "查询完成，明细如下。",
      "detail": "| 材料类别 | 入库数量 | …",
      "conversation_id": "a1b2c3d4-....",
      "answer": "…全文…"
    }
  }
}
```

Code 输出：

```json
{
  "summary": "查询完成，明细如下。",
  "detail": "| 材料类别 | 入库数量 | …\n| … | … |",
  "conversation_id": "a1b2c3d4-...."
}
```

---

## 5. 节点 ③ Variable Assigner「写入查数会话」

### 5.1 配置

| 项 | 值 |
|----|-----|
| 标题 | `写入查数会话` |
| 写入模式 | **Overwrite**（覆盖） |

### 5.2 赋值表（3 行）

| 会话变量 | 值来源 |
|----------|--------|
| `conversation.data_analysis_conversation_id` | `解析网关响应` / **conversation_id** |
| `conversation.last_query_summary` | `解析网关响应` / **summary** |
| `conversation.last_query_detail` | `解析网关响应` / **detail** |

> **DATA_QUERY 跑完后**：`data_analysis_conversation_id` 变为非空，供同会话 **DATA_FOLLOWUP**（如「提供明细」）使用。

### 5.3 会话变量定义（应用级，先建好）

| 变量名 | 类型 | 初始值 |
|--------|------|--------|
| `data_analysis_conversation_id` | String | （空） |
| `last_query_summary` | String | （空） |
| `last_query_detail` | String | （空） |

路径：**应用设置 → 会话变量**（Conversation Variables）。

---

## 6. 节点 ④ 直接回复「Fast Answer」

### 6.1 配置

| 项 | 值 |
|----|-----|
| 标题 | `Fast Answer` |
| 回复类型 | 文本 / Markdown |

### 6.2 回复模板（原样粘贴）

```
{{#conversation.last_query_detail#}}
```

`detail` 已按 **表格 → 要点速览 → ECharts** 顺序组装；Assigner 仍可写 `last_query_summary`，Answer **只绑 detail** 即可。

### 6.3 不要绑定的内容

- ❌ `{{#Agent.text#}}`  
- ❌ HTTP raw body  
- ❌ 问题分类器输出  

---

## 7. DATA_QUERY vs DATA_FOLLOWUP（同链不同参）

| 项 | DATA_QUERY | DATA_FOLLOWUP |
|----|------------|---------------|
| 分类示例 | 统计2025年各月消耗 | 提供明细 |
| `sys.query` | 完整新问 | **用户原话**（不扩写） |
| HTTP `conversation_id` | 通常 `""` | **必须**有值（来自 Assigner） |
| 子流程路由 | 问题分类 → **查询** | 问题分类 → **追问** |
| Fast 节点 | **完全相同** | **完全相同** |

追问验收：第二条消息追踪里 HTTP body 的 `conversation_id` 应为第一条返回的 uuid。

---

## 8. 网关 Workflow 内部（被 Fast HTTP 触发）

Fast 路径 **不直接** 调子 Chatflow，只调 **已发布的网关 Workflow**。网关内配置见 [11-阶段1-Workflow代理Tool方案.md](11-阶段1-Workflow代理Tool方案.md)。

### 8.1 开始节点入参（与 HTTP body.inputs 对应）

| 变量 | 类型 | 必填 |
|------|------|------|
| `question` | 短文本 | 是 |
| `conversation_id` | 短文本 | 否 |

### 8.2 网关 HTTP → 子 Chatflow

| 项 | 值 |
|----|-----|
| URL | `http://nginx/v1/chat-messages` |
| Authorization | `Bearer app-NxITngK2xpaL1nGYMiQFYye5`（**子 Chatflow** API Key） |
| `query` | `{{#开始.question#}}` |
| `conversation_id` | `{{#开始.conversation_id#}}` |
| `response_mode` | **streaming** |

### 8.3 网关 Code + 结束

- Code：[`parse_sse_and_split.py`](../workflows/code/parse_sse_and_split.py)  
- End 输出：`summary`、`detail`、`conversation_id`、`answer`

---

## 9. 预览追踪：如何确认走了 DATA_QUERY Fast 链

| 检查项 | 期望 |
|--------|------|
| 问题分类器 class | `DATA_QUERY` |
| 是否出现 Agent 节点 | **否** |
| HTTP URL | `.../v1/workflows/run` |
| HTTP body.question | 与用户输入一致 |
| HTTP body.conversation_id | 首次为空字符串 |
| Code 输出 detail | 含 `\|` 表格或下载 div |
| Assigner | 三个变量均有值 |
| 总耗时 | ~18～22s（含子流程 ~17s） |

---

## 10. 常见问题（DATA_QUERY 专用）

| 现象 | 原因 | 处理 |
|------|------|------|
| **SSRF blocked nginx** | Chatflow HTTP 禁止内网 host | 改用 **`http://120.238.80.70:15657/v1/workflows/run`** 或 §12 直连 chat-messages；或运维放行 Squid |
| 公网 URL timed out | 容器 hairpin | Squid 白名单 `nginx` / `NO_PROXY`（见下） |
| 404 workflows/run | URL 缺端口或错 host | 必须带 `:15657` |
| 401 | Workflow API Key 错 | 用 **网关应用** 的 Key，不是子 Chatflow Key |
| outputs 为空 | 网关 End 未映射 summary/detail | 检查网关 End + 重新发布 |
| summary 有、detail 空 | Code 解析字段名不对 | 看 blocking JSON 里 `data.outputs` 键名 |
| 仍走 Agent | If-Else 未接 DATA_QUERY 出口 | 查 class_name 字段名与分支条件 |
| 耗时仍 ~30s+ | 误走 Agent 或 ROUND 2 | 追踪确认无 Agent |
| 表格无下载链接 | 子流程问题 | 直连子 Chatflow 对比；与 Fast 配置无关 |

---

## 11. 最小连线清单（复制核对）

```
用户输入
  → 问题分类器（含 DATA_QUERY 类）
  → If-Else [DATA_QUERY ∨ DATA_FOLLOWUP → true]
       true  → HTTP 调用查数网关
              → Code 解析网关响应
              → Variable Assigner 写入查数会话
              → Fast Answer
       elif CHITCHAT → LLM → Answer
       else → Agent → Agent Answer
```

---

## 12. 推荐：Fast 路径直连 chat-messages（锦顺现网）

> **适用**：`nginx` 被 SSRF 拦、公网 `workflows/run` **max retries** 时。  
> **不再调用** `workflows/run`，与网关 Workflow 内部第二步 **完全同源**。

### 12.1 改 HTTP 节点「调用数据分析」

| 项 | 值 |
|----|-----|
| URL（运维 NO_PROXY **前**，可先试公网） | `http://120.238.80.70:15657/v1/chat-messages` |
| URL（运维 NO_PROXY **后**，推荐） | `http://nginx/v1/chat-messages` |
| 方法 | POST |
| 连接/读取超时 | 600 / **3600** |
| 重试 | **0** |

**Headers**

| Key | Value |
|-----|-------|
| Authorization | `Bearer app-NxITngK2xpaL1nGYMiQFYye5` ← **子 Chatflow** API Key |
| Content-Type | application/json |

**Body（JSON）— streaming**

> ⚠️ **400 常见原因**：`query` 为空、`conversation_id` 传了空字符串 `""`、或仍用 workflows/run 的 `inputs.question` 格式。  
> **首次查数（DATA_QUERY）** 与 curl 完全一致，**不要带 conversation_id 字段**：

```json
{
  "inputs": {},
  "query": "{{#sys.query#}}",
  "response_mode": "streaming",
  "user": "fast-path-user"
}
```

追问时再带 id（且 id 必须非空，否则仍 400）：

```json
{
  "inputs": {},
  "query": "{{#sys.query#}}",
  "response_mode": "streaming",
  "user": "fast-path-user",
  "conversation_id": "{{#conversation.data_analysis_conversation_id#}}"
}
```

或用 Code [`build_chat_messages_body.py`](../workflows/code/build_chat_messages_body.py) 自动省略空 id。

### 12.2 改 Code 节点（替换原 parse_workflow_run_response）

| 项 | 值 |
|----|-----|
| 代码 | [`parse_sse_and_split.py`](../workflows/code/parse_sse_and_split.py) 全文 |
| 输入 `raw` | HTTP / **body**（或 text，以日志为准） |
| 输出 | `summary`、`detail`、`conversation_id`（可选 `answer`） |

### 12.3 Assigner + Answer

**与 §5、§6 完全相同**，无需 Workflow Run API Key。

### 12.4 若公网 chat-messages 仍 max retries

**必须** 做 §13 运维（NO_PROXY 或 Squid），然后把 URL 改为 `http://nginx/v1/chat-messages` 再测。

在 Dify 服务器上验证（运维执行）：

```bash
# 从 api 容器测 nginx（NO_PROXY 后应通）
docker exec -it $(docker ps -qf name=api) curl -sS -m 10 \
  -X POST 'http://nginx/v1/chat-messages' \
  -H 'Authorization: Bearer app-NxITngK2xpaL1nGYMiQFYye5' \
  -H 'Content-Type: application/json' \
  -d '{"query":"请只回复：收到","response_mode":"streaming","user":"test"}' | head -c 500
```

---

## 13. 运维：SSRF 放行（可选，内网 URL 想用 nginx 时）

在 Dify 部署机编辑 `docker/ssrf_proxy/squid.conf`（或 `squid.conf.template`），在 `http_access deny all` **之前**增加：

```
acl docker_hosts dstdomain .nginx .api
acl docker_net src 172.16.0.0/12
http_access allow docker_hosts
http_access allow docker_net
```

或在 `docker-compose` / `.env` 的 **api**、**worker** 服务加：

```
NO_PROXY=nginx,api,127.0.0.1,localhost,120.238.80.70
no_proxy=nginx,api,127.0.0.1,localhost,120.238.80.70
```

改完后：`docker compose restart ssrf_proxy api worker`

> 仅在内网可信环境放宽 SSRF。

---

## 14. 相关文档

- [14-阶段3.5-混合编排操作手册.md](14-阶段3.5-混合编排操作手册.md)  
- [prompts/意图分类器-阶段3.5.md](../prompts/意图分类器-阶段3.5.md)  
- [11-阶段1-Workflow代理Tool方案.md](11-阶段1-Workflow代理Tool方案.md)  
