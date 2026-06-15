# Agent · Tool 调用参数一览（DATA Fast 读 · Agent 只写）

> **架构**：[22-库存与领料数据源定稿.md](22-库存与领料数据源定稿.md)  
> **读（料号/库存/统计）**：**仅** 画布 **DATA Fast HTTP**  
> **写（领料）**：Agent **只** 3 个 `erp_*`

---

## 1. 总原则

| 原则 | 说明 |
|------|------|
| 物料数据 | **必须** DATA Fast（Text2SQL）；**禁止** ERP search/inventory HTTP、禁止 Agent 读 Tool |
| 领料读 | Agent 前 **一次** Fast：料号+库存 → 会话变量 |
| 领料写 | Agent：`save_draft` → `submit` → `get` |
| draft 料号 | **必须** `requisition_material_code`（Fast 写入），禁止编造 |
| 鉴权 | erp_* Header `Authorization: Bearer {{#conversation.auth_token#}}` |
| ngrok | Header `ngrok-skip-browser-warning: true` |

---

## 2. Agent Tool 挂载（仅 3 个）

| 挂 Agent | 已废弃 / 不挂 |
|----------|---------------|
| `erp_save_draft` | ~~`query_material_data`~~ |
| `erp_submit_requisition` | ~~`erp_search_material`~~ |
| `erp_get_requisition` | ~~`erp_check_inventory`~~ |
| | `erp_login`（画布） |

---

## 3. erp_save_draft

| 参数名 | 位置 | 必填 | 说明 |
|--------|------|------|------|
| Authorization | Header | ✅ | Bearer token |
| ngrok-skip-browser-warning | Header | ✅ | true |
| items[] | Body | ✅ | material_code=**会话变量**；quantity=用户原话；unit=会话变量 |
| purpose | Body | 否 | 生产领用 |
| draft_id | Body | 否 | 改数量时必填 |

---

## 4. erp_submit_requisition

| 参数名 | 位置 | 必填 | 说明 |
|--------|------|------|------|
| Authorization | Header | ✅ | Bearer token |
| draft_id | Body | ✅ | save_draft 返回 |
| idempotency_key | Body | ✅ | UUID |

**行为**：创单、GON、**不扣库存**。

---

## 5. erp_get_requisition

| 参数名 | 位置 | 必填 | 说明 |
|--------|------|------|------|
| Authorization | Header | ✅ | Bearer token |
| requisition_no | Path | ✅ | GON 单号 |

---

## 6. 领料标准链

```
用户：帮我领 10KG 阻焊油墨
  ├─ DATA Fast → Assigner（M001234, 500 KG, …）
  ├─ Agent save_draft
  └─ 确认卡片

用户：确认提交
  └─ Agent submit → GON
```

---

## 7. Dify 检查

- [ ] Agent **仅** 3 个 erp_*
- [ ] 已卸载 search / check_inventory / query_material_data
- [ ] Agent 前 DATA Fast + 6 个 requisition_* 变量（见 doc22 §5）
- [ ] Instruction = [阶段5领料版](../prompts/主控Agent系统提示词-阶段5领料版.md)

---

## 8. 相关文档

| 文档 | 用途 |
|------|------|
| [19-阶段5-领料全流程操作手册.md](19-阶段5-领料全流程操作手册.md) | §5.6 Fast 链 |
| [15-DATA_QUERY-Fast查数路径配置详解.md](15-DATA_QUERY-Fast查数路径配置详解.md) | HTTP 配置 |
