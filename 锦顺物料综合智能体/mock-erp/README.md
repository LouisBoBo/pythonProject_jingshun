# 锦顺 ERP Mock API（FastAPI）

模拟 [04-ERP-API对接规范.md](../docs/04-ERP-API对接规范.md) 中的 **登录 + 领料** 接口，供 Dify 阶段 2～5 联调。真实 ERP 就绪后，只需把 `ERP_BASE_URL` 指向正式环境，Tool 路径保持不变。

## 快速启动

```bash
cd 锦顺物料综合智能体/mock-erp
chmod +x run.sh
./run.sh
```

或手动：

```bash
cd 锦顺物料综合智能体/mock-erp
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8900 --reload
```

- 健康检查：<http://127.0.0.1:8900/health>
- Swagger：<http://127.0.0.1:8900/docs>
- OpenAPI JSON：<http://127.0.0.1:8900/openapi.json>

**Dify 环境变量**：

```
ERP_BASE_URL = http://127.0.0.1:8900/api
```

若 Dify 在 Docker 内、Mock 在宿主机，Mac/Windows 可用：

```
ERP_BASE_URL = http://host.docker.internal:8900/api
```

### 远程 Dify + 本地 Mock（内网穿透）

Dify 在远程服务器（如 `120.238.80.70`）、Mock 跑在本机时，需 **内网穿透** 把 `8900` 暴露到公网 HTTPS。

**推荐：ngrok**（本机已装 ngrok 时）

```bash
# 终端 1：Mock
cd mock-erp && ./run.sh

# 终端 2：穿透
chmod +x tunnel-ngrok.sh
./tunnel-ngrok.sh
```

ngrok 输出示例：

```
Forwarding  https://abc123.ngrok-free.app -> http://localhost:8900
```

**Dify 环境变量**：

```
ERP_BASE_URL = https://abc123.ngrok-free.app/api
```

**每个 ERP Custom Tool 的 Header**（ngrok 免费版必加，否则返回 HTML 拦截页）：

```
ngrok-skip-browser-warning: true
```

**自测（模拟 Dify 从外网访问）**：

```bash
TUNNEL=https://abc123.ngrok-free.app
curl -s "$TUNNEL/health" -H "ngrok-skip-browser-warning: true"
curl -s -X POST "$TUNNEL/api/auth/login" \
  -H "Content-Type: application/json" \
  -H "ngrok-skip-browser-warning: true" \
  -d '{"username":"zhangsan","password":"123456"}'
```

**注意**：

| 项 | 说明 |
|----|------|
| SSRF | Custom Tool 调 **公网 HTTPS** 一般不受「内网 SSRF 拦截」影响（与 `nginx` 不同） |
| 隧道稳定性 | 本机关机或 ngrok 退出 → Dify Tool 立即失败，联调期间保持运行 |
| 地址变化 | 免费 ngrok 每次重启子域会变，需同步改 Dify `ERP_BASE_URL` 与各 Tool URL |
| 固定域名 | ngrok 付费可绑 `--domain=`，或改用 cpolar / 自建 frp |

**备选：Cloudflare Tunnel**（无 ngrok 账号时）

```bash
brew install cloudflared
cloudflared tunnel --url http://127.0.0.1:8900
# 使用输出的 https://xxx.trycloudflare.com
# ERP_BASE_URL = https://xxx.trycloudflare.com/api
```

---

## 测试账号

| 用户名 | 密码 | 部门 |
|--------|------|------|
| `zhangsan` | `123456` | 高精密事业部 |
| `lisi` | `123456` | 单面事业部 |
| `disabled` | `123456` | 账号禁用（测 403） |

---

## 预置物料

| 料号 | 名称 | 可用库存（约） |
|------|------|----------------|
| M001234 | 阻焊油墨 KB-6160 | 500 KG |
| M002001 | 覆铜板 | 110 张 |
| M003015 | 过硫酸钠 | 6 KG |
| M004088 | 锡膏 SAC305 | 15 KG |

搜索关键字示例：`油墨`、`覆铜板`、`M001234`

---

## 接口列表与用途

| 方法 | 路径 | Dify Tool 名 | 用途 | 何时调用 | 鉴权 |
|------|------|--------------|------|----------|------|
| GET | `/health` | — | **健康检查**：确认服务在线 | 部署探活、本地自检 | 否 |
| GET | `/` | — | **服务信息**：文档地址、测试账号 | 人工排查 | 否 |
| POST | `/api/auth/login` | `erp_login` | **用户登录**：校验工号密码，返回 `access_token` 与 `user_profile` | 用户说「登录」；领料前未登录；401 后重新登录 | 否 |
| POST | `/api/auth/refresh` | `erp_refresh`（可选） | **刷新令牌**：token 快过期时换新 token | 401 且为过期；SSO 续期 | 是 |
| GET | `/api/materials/search` | `erp_search_material` | **物料检索**：按关键字搜料号、名称、规格 | 用户描述模糊（如「阻焊油墨」无量号）；多物料需用户选型 | 是 |
| GET | `/api/inventory/check` | `erp_check_inventory` | **库存校验**（Mock） | Tool 测试；**生产读库存走 Fast HTTP** | 是 |
| POST | `/api/requisition/draft` | `erp_save_draft` | **保存领料草稿**：创建或更新未提交申请 | 数量部门已齐但未确认；改数量/加行 | 是 |
| POST | `/api/requisition/submit` | `erp_submit_requisition` | **提交审批**：草稿转正式领料单，返回 GON 单号 | 用户明确「确认提交」后 | 是 |
| GET | `/api/requisition/{no}` | `erp_get_requisition` | **查单详情**：按单号查状态与明细 | 「GONxxx 到哪了」；提交后查详情 | 是 |
| GET | `/api/requisition/list` | `erp_list_requisition`（可选） | **我的申请列表**：当前用户全部/按状态筛选 | 「我最近的领料单」「待审批有哪些」 | 是 |

鉴权 Header（除 login 外）：`Authorization: Bearer <access_token>`

---

## 领料标准调用链（Fast HTTP 读 + Agent 写）

```
画布 erp_login（未登录时）
    ↓
DATA Fast（料号 + 名称 + 可用库存 + 单位 · 与纯查数同源）
    ↓
Agent erp_save_draft → 确认卡片
    ↓
Agent erp_submit_requisition（确认后 · 不扣 Mock 库存）
    ↓
Agent erp_get_requisition（查 GON，按需）
```

**禁止**领料链调用 `erp_search_material` / `erp_check_inventory`（物料读只走 DATA Fast）。

---

## 各接口详细说明

### 1. POST `/api/auth/login` — 用户登录

| 项 | 说明 |
|----|------|
| **用途** | 验证身份，获取后续接口所需的 Bearer Token |
| **请求** | `{ "username": "zhangsan", "password": "123456" }` |
| **响应要点** | `access_token`、`expires_in`(7200)、`user`（含 dept_id、dept_name） |
| **Dify 后续** | Variable Assigner 写入 `auth_token`、`user_profile` |
| **错误** | 401 密码错；403 账号禁用 |

### 2. POST `/api/auth/refresh` — 刷新令牌

| 项 | 说明 |
|----|------|
| **用途** | 延长会话，避免频繁让用户输密码 |
| **场景** | Token 过期前续期；可选 Tool，非 MVP 必须 |

### 3. GET `/api/materials/search` — 物料检索

| 项 | 说明 |
|----|------|
| **用途** | 把口语描述映射到 ERP 物料主数据（料号、规格、单位） |
| **参数** | `keyword`（必填）、`page`、`page_size` |
| **示例** | `?keyword=油墨` → 返回 M001234 阻焊油墨等 |
| **Agent** | 多条结果时让用户选一条再继续 |

### 4. GET `/api/inventory/check` — 库存校验

| 项 | 说明 |
|----|------|
| **用途** | Tool 测试；**生产读库存走主 Chatflow Fast HTTP** |
| **参数** | `material_code` 或 `material_keyword`（二选一） |
| **响应要点** | `available_qty`、`sufficient` |
| **错误** | 404 物料不存在 |

### 5. POST `/api/requisition/draft` — 保存草稿

| 项 | 说明 |
|----|------|
| **用途** | 多轮对话中暂存领料意图，尚未进入审批 |
| **请求要点** | `items[]`（material_code、quantity）；`draft_id` 空=新建，有值=更新 |
| **响应要点** | `draft_id`、`summary`（确认卡片可展示） |
| **注意** | 不等于正式提交，用户未确认前勿调 submit |

### 6. POST `/api/requisition/submit` — 提交审批

| 项 | 说明 |
|----|------|
| **用途** | 生成正式领料单（Mock 为 GON 号），状态 `PENDING_APPROVAL` |
| **请求** | `{ "draft_id": "...", "idempotency_key": "uuid" }` |
| **幂等** | 相同 idempotency_key 重复调用返回同一单号 |
| **库存** | **不校验、不扣减**（doc22；真实 ERP submit 同样只创单+审批） |
| **Agent 铁律** | 必须用户确认后才调用 |

### 7. GET `/api/requisition/{requisition_no}` — 查单详情

| 项 | 说明 |
|----|------|
| **用途** | 单笔单的 status、明细、申请人、审批信息 |
| **示例** | `/api/requisition/GON20260309001` |

### 8. GET `/api/requisition/list` — 我的申请列表

| 项 | 说明 |
|----|------|
| **用途** | 不指定单号时查「我提交过的所有单」 |
| **参数** | `status`（如 PENDING_APPROVAL）、分页 |

---

Swagger 文档（`/docs`）中每个接口也附有相同用途说明，导入 Dify OpenAPI 时会带入 description。

---

## curl 自测

```bash
BASE=http://127.0.0.1:8900/api

# 登录
TOKEN=$(curl -s -X POST "$BASE/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"zhangsan","password":"123456"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# 搜物料
curl -s "$BASE/materials/search?keyword=油墨" -H "Authorization: Bearer $TOKEN"

# 查库存
curl -s "$BASE/inventory/check?material_code=M001234" -H "Authorization: Bearer $TOKEN"

# 建草稿
curl -s -X POST "$BASE/requisition/draft" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"purpose":"生产补料","items":[{"material_code":"M001234","quantity":10,"unit":"KG"}]}'

# 提交（将 DRAFT-xxx 换成上一步返回的 draft_id）
curl -s -X POST "$BASE/requisition/submit" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"draft_id":"DRAFT-20260309-001","idempotency_key":"test-001"}'
```

---

## Dify Custom Tool 配置要点

1. **Tools → Create Custom Tool**，或 **Import from URL**：`http://127.0.0.1:8900/openapi.json`
2. 若导入 OpenAPI，注意 base path 为 `/api`
3. 业务 Tool Header：`Authorization: Bearer {{#conversation.auth_token#}}`（登录 Tool 除外）
4. Tool 名称建议与方案一致：`erp_login`、`erp_search_material`、`erp_check_inventory` 等

---

## 业务规则（Mock · doc22）

- Token 有效期 **7200 秒**，过期返回 401
- `submit` 支持 **idempotency_key** 幂等
- **`submit` 不校验库存、不扣减 `reserved_qty`**（读库存走查数；真实 ERP 对接时 submit 同样只创单+审批）
- `GET /api/inventory/check` 保留供 Tool 测试；**生产读库存走 Fast HTTP**
- 数据存内存，**重启服务后清空**

---

## 切换到真实 ERP

1. 将 Dify `ERP_BASE_URL` 改为真实地址
2. 按真实 OpenAPI 微调字段（若有差异）
3. 停用或保留 Mock 服务作回归测试
