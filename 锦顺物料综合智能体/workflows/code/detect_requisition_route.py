"""
Dify Code 节点：领料 / 查单 / 混合类请求 → 进入 **领料子流程**（先 DATA Fast 读，再 Agent 写）。

**不是**「直进 Agent」。`use_agent` 为历史字段名，与 `use_requisition_flow` 同值。

放在「登录路由」之后、「意图分类器」之前。
纯查物料/库存（无领料意图）应输出 false，交给分类器 → DATA Fast。

输入：
  - query: string  sys.query

输出（If-Else equals）：
  - use_requisition_flow: "true" | "false"  （推荐 If 绑此字段）
  - use_agent: 同上（兼容旧画布）
  - reason: string
"""

import re

_GON = re.compile(r"GON\d+", re.I)
_DRAFT = re.compile(r"DRAFT-\d", re.I)

_REQUISITION_KEYWORDS = (
    "领料",
    "我要领",
    "要领料",
    "要料",
    "帮我领",
    "申请领",
    "出库申请",
    "确认提交",
    "提交审批",
    "审批到哪",
    "我的领料",
    "我的申请",
    "领用",
    "要申请",
)

_STATUS_KEYWORDS = (
    "领料单",
    "出仓单",
    "审批状态",
    "到哪了",
    "单号状态",
)

_FLOW_KEYWORDS = (
    "确认提交",
    "修改数量",
    "修改数量为",
)

_UNITS = ("KG", "kg", "Kg", "箱", "张", "吨", "个", "卷", "桶", "包")

_MIXED_HINTS = ("够的话", "够就", "先查", "再领", "再帮我领", "帮我申请")

# 用户选型后续回复：仅料号或「领 JS-NZ-006」
_MATERIAL_CODE = re.compile(r"\b([A-Z]{2,}-[A-Z0-9-]+)\b", re.I)


def _out(use: bool, reason: str) -> dict:
    v = "true" if use else "false"
    return {"use_requisition_flow": v, "use_agent": v, "reason": reason}


def _is_requisition(text: str) -> tuple[bool, str]:
    if any(k in text for k in _REQUISITION_KEYWORDS):
        return True, "requisition_keyword"

    if any(k in text for k in _FLOW_KEYWORDS):
        return True, "requisition_flow"

    if "领" in text and any(h in text for h in _MIXED_HINTS):
        return True, "mixed_hint"

    if "领" in text and any(u in text for u in _UNITS):
        return True, "requisition_with_unit"

    return False, ""


def main(query: str) -> dict:
    t = (query or "").strip()
    if not t:
        return _out(False, "empty")

    if _GON.search(t):
        return _out(True, "gon_number")

    if _DRAFT.search(t):
        return _out(True, "draft_number")

    if any(k in t for k in _STATUS_KEYWORDS):
        return _out(True, "requisition_status_keyword")

    if "状态" in t and re.search(r"查询\s*[A-Z]{2,}\d+", t, re.I):
        return _out(True, "query_status_with_biz_no")

    ok, why = _is_requisition(t)
    if ok:
        return _out(True, why)

    if t in ("取消", "算了"):
        return _out(True, "requisition_cancel")

    # 选型后用户只发料号 / 「领 JS-NZ-006」→ 仍进领料子流程
    if _MATERIAL_CODE.search(t):
        if len(t) <= 48 and not any(k in t for k in ("统计", "查询", "多少", "消耗", "明细")):
            return _out(True, "material_code_pick")

    return _out(False, "use_classifier")
