# ERP API 对接规范

本文约定 Dify 与锦顺 ERP 之间的 **登录** 与 **领料** 接口形态。实际路径、字段名以 ERP 提供的 OpenAPI 为准；对接时按本文映射到 Dify HTTP Tool。

---

## 1. 基础配置

### 1.1 环境变量（Dify App 级）

| 变量名 | 说明 | 示例 |
|--------|------|------|
| `ERP_BASE_URL` | API 根地址 | `https://erp.example.com/api` |
| `ERP_CLIENT_ID` | 可选，OAuth 客户端 ID | — |
| `ERP_TIMEOUT_MS` | HTTP 超时 | `30000` |

### 1.2 通用请求头

```
Content-Type: application/json
Authorization: Bearer {{#conversation.auth_token#}}
```

登录接口 **除外**（无 Bearer）。

---

## 2. 登录 API

### 2.1 登录

| 项 | 值 |
|----|-----|
| 方法 | `POST` |
| 路径 | `{ERP_BASE_URL}/auth/login` |
| Tool 名 | `erp_login` |

**请求体**：

```json
{
  "username": "工号",
  "password": "密码"
}
```

**响应体（成功）**：

```json
{
  "access_token": "eyJhbG...",
  "expires_in": 7200,
  "token_type": "Bearer",
  "user": {
    "user_id": "U001",
    "username": "zhangsan",
    "name": "张三",
    "dept_id": "D001",
    "dept_name": "高精密事业部",
    "factory_id": "F001",
    "factory_name": "高精密事业部",
    "roles": ["material_request"]
  }
}
```

**Dify 后续处理**：Assigner 写入 `auth_token`、`token_expires_at`、`user_profile`。

### 2.2 刷新 Token（可选）

| 项 | 值 |
|----|-----|
| 方法 | `POST` |
| 路径 | `{ERP_BASE_URL}/auth/refresh` |
| 请求体 | `{ "refresh_token": "..." }` |

### 2.3 错误码

| HTTP | 含义 | Agent 处理 |
|------|------|------------|
| 401 | 用户名或密码错误 | 提示重新输入 |
| 403 | 账号禁用 | 联系管理员 |
| 429 | 限流 | 稍后重试 |

---

## 3. 领料 API

### 3.1 物料检索

| 项 | 值 |
|----|-----|
| 方法 | `GET` |
| 路径 | `{ERP_BASE_URL}/materials/search` |
| Tool 名 | `erp_search_material` |

**Query 参数**：

| 参数 | 必填 | 说明 |
|------|------|------|
| `keyword` | 是 | 物料名、料号、规格片段 |
| `page` | 否 | 页码，默认 1 |
| `page_size` | 否 | 默认 10 |

**响应示例**：

```json
{
  "items": [
    {
      "material_code": "M001234",
      "material_name": "阻焊油墨",
      "spec": "KB-6160",
      "unit": "KG",
      "category": "油墨"
    }
  ],
  "total": 1
}
```

### 3.2 库存校验

| 项 | 值 |
|----|-----|
| 方法 | `GET` |
| 路径 | `{ERP_BASE_URL}/inventory/check` |
| Tool 名 | `erp_check_inventory` |

**Query 参数**：

| 参数 | 必填 | 说明 |
|------|------|------|
| `material_code` | 是* | 料号（与 keyword 二选一） |
| `material_keyword` | 是* | 模糊物料 |
| `warehouse_id` | 否 | 仓库，默认用户默认仓 |
| `factory_id` | 否 | 工厂 / 事业部 |

**响应示例**：

```json
{
  "material_code": "M001234",
  "material_name": "阻焊油墨",
  "unit": "KG",
  "available_qty": 25,
  "on_hand_qty": 30,
  "reserved_qty": 5,
  "warehouse_name": "原材料仓",
  "sufficient": true
}
```

**业务规则**：口径与数据分析一致（排除外发/外协、半成品仓等），由 **ERP 侧实现**。

### 3.3 创建 / 更新草稿

| 项 | 值 |
|----|-----|
| 方法 | `POST` |
| 路径 | `{ERP_BASE_URL}/requisition/draft` |
| Tool 名 | `erp_save_draft` |

**请求体**：

```json
{
  "draft_id": null,
  "dept_id": "D001",
  "warehouse_id": "W001",
  "purpose": "生产补料",
  "remark": "AI助手代填",
  "items": [
    {
      "material_code": "M001234",
      "quantity": 10,
      "unit": "KG"
    }
  ]
}
```

- `draft_id` 为空：新建；有值：更新
- `dept_id` 缺省时 ERP 可用 Token 内用户默认部门

**响应**：

```json
{
  "draft_id": "DRAFT-20260309-001",
  "status": "DRAFT",
  "summary": "阻焊油墨 × 10 KG · 高精密事业部"
}
```

### 3.4 提交审批

| 项 | 值 |
|----|-----|
| 方法 | `POST` |
| 路径 | `{ERP_BASE_URL}/requisition/submit` |
| Tool 名 | `erp_submit_requisition` |

**请求体**：

```json
{
  "draft_id": "DRAFT-20260309-001",
  "idempotency_key": "uuid-v4"
}
```

**响应**：

```json
{
  "success": true,
  "requisition_no": "GON20260309001",
  "status": "PENDING_APPROVAL",
  "message": "已提交，等待仓库审核"
}
```

**幂等**：同一 `idempotency_key` 重复提交应返回同一单号，不重复建单。

### 3.5 查询申请单

| 项 | 值 |
|----|-----|
| 方法 | `GET` |
| 路径 | `{ERP_BASE_URL}/requisition/{requisition_no}` |
| Tool 名 | `erp_get_requisition` |

**响应字段建议**：

| 字段 | 说明 |
|------|------|
| `requisition_no` | 出仓单号（对应 Data0457.GON_NUMBER） |
| `status` | 见状态枚举 |
| `create_date` | 创建时间 |
| `applicant` | 申请人 |
| `items` | 明细行 |
| `audit_by` / `audit_date` | 审核信息 |

### 3.6 我的申请列表（可选）

| 项 | 值 |
|----|-----|
| 方法 | `GET` |
| 路径 | `{ERP_BASE_URL}/requisition/list` |
| Tool 名 | `erp_list_requisition` |

**Query**：`status`, `start_date`, `end_date`, `page`, `page_size`

---

## 4. 状态枚举（与 Data0457 对齐）

请 ERP 提供与 `Data0457.STATUS` 一致的映射表，建议 AI 侧展示文案：

| 代码 | 展示 |
|------|------|
| `DRAFT` | 草稿 |
| `PENDING_APPROVAL` | 待审批 |
| `APPROVED` | 已通过 |
| `REJECTED` | 已驳回 |
| `CANCELLED` | 已取消 |
| `COMPLETED` | 已发料 |

---

## 5. Dify HTTP Tool 配置模板

### 5.1 erp_check_inventory 示例

| 配置项 | 值 |
|--------|-----|
| URL | `{{ERP_BASE_URL}}/inventory/check` |
| Method | GET |
| Headers | `Authorization: Bearer {{#conversation.auth_token#}}` |
| Query | `material_code`, `warehouse_id`（Agent 传参） |

### 5.2 erp_submit_requisition 示例

| 配置项 | 值 |
|--------|-----|
| URL | `{{ERP_BASE_URL}}/requisition/submit` |
| Method | POST |
| Body | JSON，`draft_id` + `idempotency_key` |

Tool **描述**（供 Agent 选型）应写清：

- 何时调用
- 必填参数
- **submit 前必须经用户口头确认**

---

## 6. ERP 数据表参考（只读对照）

领料写入由 ERP API 封装，Agent 不直接操作表。对照理解：

| 表 | 用途 |
|----|------|
| `Data0457` | 材料出仓单主表（GON_NUMBER、领料人、STATUS） |
| `Data0207` | 材料出库明细 |
| `Data0017` | 物料主数据 |
| `Data0022` | 库存 / 入库明细（库存校验口径） |

---

## 7. 错误处理约定

| ERP 业务码 | 含义 | Agent 回复要点 |
|------------|------|----------------|
| `INSUFFICIENT_STOCK` | 库存不足 | 展示可用量，询问是否改数量 |
| `MATERIAL_NOT_FOUND` | 物料不存在 | 建议换关键词 search |
| `DEPT_NOT_ALLOWED` | 无权限替该部门领料 | 说明权限限制 |
| `DRAFT_EXPIRED` | 草稿过期 | 重新 save_draft |
| `ALREADY_SUBMITTED` | 重复提交 | 返回已有单号 |

---

## 8. 相关文档

- [记忆与会话设计](03-记忆与会话设计.md)
- [Dify 落地指南](05-Dify落地指南.md)
- [实施计划与对接清单](06-实施计划与对接清单.md)
