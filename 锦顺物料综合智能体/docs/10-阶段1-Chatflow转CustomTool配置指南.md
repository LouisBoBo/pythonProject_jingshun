# 阶段 1（Chatflow 版）：用 API Custom Tool 代替「发布为工具」

> **适用**：应用类型为 **Chatflow / advanced-chat**（如 `锦顺-数据分析子流程`）。  
> Dify 官方：**对话流不支持「发布为工具」**，用 **访问 API + 自定义工具** 实现同样效果。

---

## 锦顺现网一键配置（已实测）

| 项 | 值 |
|----|-----|
| 控制台 / 应用地址 | `http://120.238.80.70:15657/app/f728fdf3-4b1c-42d9-a520-f7e51f451f4f/workflow` |
| **API Base URL（实际可用）** | `http://120.238.80.70:15657/v1` |
| **完整接口** | `POST http://120.238.80.70:15657/v1/chat-messages` |
| API Key | `app-NxITngK2xpaL1nGYMiQFYye5`（该应用密钥） |

> ⚠️ 「访问 API」页若显示 `http://120.238.80.70/v1`（**无端口**），是部署 `APP_API_URL` 配错，**不要照抄**。80 端口是 WAF，会 404。

**curl 自测（streaming，已验证可用）**：

```bash
curl -N -X POST 'http://120.238.80.70:15657/v1/chat-messages' \
  -H 'Authorization: Bearer app-NxITngK2xpaL1nGYMiQFYye5' \
  -H 'Content-Type: application/json' \
  -d '{
    "inputs": {},
    "query": "统计2025年各月物料消耗金额",
    "response_mode": "streaming",
    "user": "test-user-001"
  }'
```

看到 `"event":"workflow_finished"` 且 `outputs.answer` 有内容即通过。查数类问题可能跑 1～3 分钟，属正常。

**blocking 说明**：锦顺现网 **`blocking` 会 timeout**（API 只 SSE ping 不返 JSON）。Custom Tool **必须用 `streaming`**（已实测可查数）。

**Custom Tool 最终配置（锦顺现网 · 已验证）**：

| 项 | 值 |
|----|-----|
| `servers.url` | `http://nginx/v1` |
| 鉴权 | `Bearer app-NxITngK2xpaL1nGYMiQFYye5` |
| `response_mode` | **`streaming`**（工具测试与 Agent 调用均填此项） |
| curl 自测（外网） | 仍用 `http://120.238.80.70:15657/v1/chat-messages` + streaming |

工具测试返回大段 SSE/分析正文即 **阶段 1 通过**。若 Agent 读到原始 SSE 难解析，再改用 [Workflow 代理方案](11-阶段1-Workflow代理Tool方案.md)。

### Custom Tool 报 `Reached maximum retries (0)` 时

**现象**：你本机 curl `120.238.80.70:15657` 正常，但 **工具 → 测试** 失败。

**原因**：Custom Tool 的 HTTP 请求由 Dify **容器内的 SSRF 代理**发出，不是浏览器。容器访问「自己的公网 IP:15657」常因 hairpin / 防火墙 **连不上**（与 curl 从 Mac 出网不是同一路径）。

**Fix A（推荐，同一套 Dify）**：OpenAPI 的 `servers.url` 改成 **Docker 内网地址**（二选一，需运维确认 compose 服务名）：

```yaml
servers:
  - url: http://nginx/v1          # 常见，nginx 反代到 api
  # 或
  - url: http://api:5001/v1        # 直连 api 容器
```

鉴权 Header 不变，仍用 `Bearer app-NxITngK2xpaL1nGYMiQFYye5`。

**Fix B（Linux 宿主机端口）**：若 A 不通，在 **ssrf_proxy 容器内**试：

```bash
docker exec -it <ssrf_proxy容器名> curl -s -o /dev/null -w "%{http_code}" \
  -X POST 'http://nginx/v1/chat-messages' \
  -H 'Authorization: Bearer app-NxITngK2xpaL1nGYMiQFYye5' \
  -H 'Content-Type: application/json' \
  -d '{"inputs":{},"query":"你好","response_mode":"blocking","user":"test"}'
```

哪个 URL 在容器内返回 200，Custom Tool 就填哪个 Base URL。

**Fix C（查数超时 · 你现在的情况）**：工具测试显示 **`timed out`** 说明 `http://nginx/v1` **已连通**，但默认读超时太短（通常 **60 秒**），而「统计2025年各月物料消耗金额」要跑 SQL + LLM，常需 **1～5 分钟**。

1. **先测短句**（验证 Tool 本身 OK）：
   - query: `你好，请只回复两个字：收到`
   - response_mode: `blocking`
2. **再测查数**（需运维加超时）—— 在 Dify 服务器 `docker/.env` 增加或修改：

```env
API_TOOL_DEFAULT_CONNECT_TIMEOUT=600
API_TOOL_DEFAULT_READ_TIMEOUT=3600
```

然后重启：

```bash
cd docker && docker compose restart api worker ssrf_proxy
```

3. 若短句 OK、查数仍超时：blocking 在你环境可能只 ping 不返回 JSON（见上文 blocking 说明），让运维同时检查 `APP_API_URL`；阶段 1 验收可 **短句 Tool 测试通过 + curl streaming 查数通过**。

**Fix D（短句也 timeout → 换 Workflow 代理，推荐）**  

若 `http://nginx/v1` + 短句 `你好，请只回复两个字：收到` + `blocking` **仍然 timed out**，说明不是超时配置问题，而是 **blocking 模式不返回 JSON**（streaming 才正常）。Custom OpenAPI Tool **无法使用**。

👉 **改走 Workflow 代理 + 发布为工具**：见 **[11-阶段1-Workflow代理Tool方案.md](11-阶段1-Workflow代理Tool方案.md)**  

要点：Workflow 内 HTTP 调 `response_mode: streaming` → Code 解析 SSE → Publish as Tool，Agent 仍调用 `query_material_data`。

---

## 你要完成什么

让主 Agent 能调用 **`query_material_data`** → 背后请求你的数据分析 Chatflow API → 返回统计/分析结果。

**不必做**：`question` 变量、归一化 Code、改 `sys.query`（API 的 `query` 会自动进 Chatflow）。

---

## 第一步：发布 Chatflow 并拿到 API 信息

1. 打开应用 **`锦顺-数据分析子流程`**（或你导入的副本）
2. 右上角 **发布 → 发布更新**
3. 再点 **发布 → 访问 API**（或应用左侧 **访问 API**）
4. 记录下面三项（后面要用）：

| 项 | 在哪看 | 示例 |
|----|--------|------|
| **API 基址** | 文档页顶部 Base URL | `http://localhost/v1` 或 `https://api.dify.ai/v1` |
| **API 密钥** | 创建 API 密钥 | `app-xxxxxxxxxxxx` |
| **应用类型** | 确认是 Chatflow | 接口为 `POST /chat-messages` |

5. 用 curl 自测（**Base URL 必须带端口**，路径必须是 `/chat-messages`）：

```bash
# 锦顺现网
curl -N -X POST 'http://120.238.80.70:15657/v1/chat-messages' \
  -H 'Authorization: Bearer app-你的密钥' \
  -H 'Content-Type: application/json' \
  -d '{
    "inputs": {},
    "query": "统计2025年各月物料消耗金额",
    "response_mode": "streaming",
    "user": "test-user-001"
  }'
```

streaming 看到 `workflow_finished` + `answer` 即通过；blocking 返回 JSON `answer` 亦可。

---

## 第二步：在 Dify 创建自定义工具

### 入口

**工作室 → 工具（Tools）→ 创建自定义工具**

### 方式 A：粘贴 OpenAPI Schema（推荐）

**工具名称**：`query_material_data`

**Schema 类型**：OpenAPI / Swagger

**重要**：`servers.url` = **实际可 curl 通的 Base URL**。锦顺现网填 `http://120.238.80.70:15657/v1`（勿用无端口的 `http://120.238.80.70/v1`）。

```yaml
openapi: 3.0.0
info:
  title: query_material_data
  description: 查询锦顺物料数据库并做数据分析。用户问统计/查询/排名/占比/库存/明细时使用。
  version: 1.0.0
servers:
  - url: http://localhost/v1
paths:
  /chat-messages:
    post:
      operationId: query_material_data
      summary: 查询并分析锦顺物料数据
      description: |
        调用「锦顺-数据分析子流程」Chatflow。
        当用户问题涉及：统计、查询、多少、排名、占比、趋势、库存、采购、出入库、明细时使用。
        不要用于领料申请。
        参数 question 传入用户完整自然语言问题。
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required:
                - query
                - response_mode
                - user
              properties:
                query:
                  type: string
                  description: 用户完整问题，如「统计2025年各月物料消耗金额」
                inputs:
                  type: object
                  description: Chatflow 开始变量，无额外变量可传空对象
                  default: {}
                response_mode:
                  type: string
                  description: 固定 blocking，等分析跑完再返回
                  enum:
                    - blocking
                  default: blocking
                user:
                  type: string
                  description: 终端用户标识，同一用户追问时可保持一致
                  default: agent-user
                conversation_id:
                  type: string
                  description: 可选。同一 conversation_id 可延续 Chatflow 内追问上下文
      responses:
        '200':
          description: Chatflow 阻塞模式完整响应，含 answer 字段
          content:
            application/json:
              schema:
                type: object
                properties:
                  answer:
                    type: string
                  conversation_id:
                    type: string
```

### 鉴权配置

在工具 **认证 / Authorization** 中：

| 项 | 值 |
|----|-----|
| 类型 | Bearer / API Key |
| Header 名 | `Authorization` |
| 值 | `Bearer app-你的密钥` |

（若 Dify 工具页是「凭据」单独配置，在工作区 **工具 → 凭据** 里建一条 Bearer Token。）

### 保存并测试工具

1. **保存** 自定义工具
2. 进入工具 **测试** 页
3. 填参数：

| 参数 | 值 |
|------|-----|
| query | `统计2025年各月物料消耗金额` |
| response_mode | `blocking` |
| user | `test-user-001` |
| inputs | `{}` |

4. 执行后应返回含 **`answer`** 的 JSON

---

## 方式 B：界面手工建（没有 OpenAPI 粘贴框时）

1. **创建自定义工具** → 名称 `query_material_data`
2. **添加 API**：
   - 方法：`POST`
   - URL：`{Base URL}/chat-messages`（例：`http://localhost/v1/chat-messages`）
3. **Header**：
   - `Authorization`: `Bearer app-你的密钥`
   - `Content-Type`: `application/json`
4. **Body（JSON）**，参数化：

```json
{
  "inputs": {},
  "query": "{{question}}",
  "response_mode": "blocking",
  "user": "{{user_id}}"
}
```

5. **参数定义**：

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| question | string | 是 | 用户完整问题 |
| user_id | string | 否 | 默认 `agent-user` |

6. **工具描述**（给 Agent 看，复制）：

```text
查询锦顺物料 SQL Server 数据库：统计、排名、库存、采购、出入库、用量分析，返回 Markdown 表格与图表说明。
当用户问统计/查询/多少/排名/占比/趋势/明细/库存时使用。
参数 question 为完整自然语言问题。不处理领料申请。
```

---

## 第三步：Tool 描述优化（Agent 选型用）

在工具设置里 **Description** 建议包含：

- **何时用**：统计、查询、排名、占比、库存、明细…
- **何时不用**：领料、登录、提交申请
- **参数**：question = 用户原话或合并后的完整问题

Agent Instruction 里可写一句：

```text
查数据统计、SQL 分析、图表时，必须调用 query_material_data，并将用户问题完整传入 question（或 query）。
```

---

## 第四步：挂到综合助手 Agent（阶段 3 预览，可先试）

1. 新建 Chatflow **`锦顺物料综合助手`**
2. **User Input → Agent 节点 → Answer**
3. Agent **工具箱 → +** → 选 **`query_material_data`**
4. Instruction 可先写简单版：

```text
你是锦顺物料助手。
- 用户问统计、查询、数据、排名、占比、库存 → 调用 query_material_data，把用户问题作为 question 传入。
- 领料相关 → 调用 erp_* 工具（阶段 2 配置后）。
只根据工具返回回答，不要编造数字。
```

5. 预览：`统计2025年各月物料消耗金额` → Agent 应调 Tool 并返回分析

---

## 追问与 conversation_id（进阶，可后做）

Chatflow 内「提供明细」等追问，依赖 **同一会话**。

API 调用时：

1. **首次**请求：`conversation_id` 留空或不传  
2. 响应里会有 **`conversation_id`**  
3. **追问**时同一 `user` + 同一 `conversation_id`，只改 `query` 为追问内容  

主 Agent 多轮追问要在 Tool 参数里传 `conversation_id`，或把追问合并成一句完整 `question` 再调 Tool（更简单，阶段 6 再优化）。

阶段 1 验收：**单次查数** 通过即可。

---

## 自建 Dify 地址对照

| 部署 | Base URL 示例 |
|------|----------------|
| **锦顺现网** | `http://120.238.80.70:15657/v1` |
| 本地 Docker | `http://localhost/v1` 或 `http://127.0.0.1/v1` |
| 内网服务器 | `http://192.168.x.x:端口/v1`（端口与浏览器控制台一致） |
| Dify 云端 | `https://api.dify.ai/v1` |

Agent 和 Chatflow **同一套 Dify** 时，Custom Tool 的 URL 填内网可达地址；Docker 内调宿主机有时要用 `host.docker.internal`。

**运维修正（可选）**：Docker `.env` 中设 `APP_API_URL=http://120.238.80.70:15657`，重启后「访问 API」页 Base URL 才会正确。

---

## 阶段 1 验收清单（Chatflow 版）

- [ ] Chatflow 已 **发布更新**
- [ ] curl / 工具测试 `query=统计2025年各月物料消耗` 有 `answer`
- [ ] 自定义工具 **`query_material_data`** 已创建
- [ ] （可选）综合助手 Agent 已挂载并预览成功
- [ ] （可选）导出 DSL 到 `workflows/锦顺-数据分析子流程.yml`

---

## 常见问题

**Q：返回 401**  
A：检查 API Key 是否为 **该 Chatflow 应用** 的密钥，Header 是否为 `Bearer app-xxx`。

**Q：404 page not found**  
A：URL 缺端口或缺路径。正确：`http://120.238.80.70:15657/v1/chat-messages`，不是 `/v1`  alone，也不是 80 端口。

**Q：返回空 answer 或超时**  
A：SQL 查数慢，等 1～3 分钟；curl 自测用 `streaming`。blocking 若只 ping 不结束，见上文 blocking 说明。

**Q：「访问 API」页地址和 curl 不一致**  
A：`APP_API_URL` 环境变量配错，以 **浏览器控制台端口** 为准。

**Q：和 Mock ERP 的 URL 混淆**  
A：Mock ERP 是 `http://127.0.0.1:8900/api`（领料）；Chatflow API 是 Dify 的 `/v1/chat-messages`（查数），两套不同。

**Q：还要改正式库 YAML 吗**  
A：不需要。副本发布 + API Tool 即可。

---

## 相关文档

- [09-阶段1操作手册.md](09-阶段1操作手册.md)（Workflow 发布为 Tool 版，Chatflow 可忽略 question 部分）
- [08-分步实施清单.md](08-分步实施清单.md)
