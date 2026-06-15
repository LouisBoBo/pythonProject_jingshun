"""
Dify Code：领料分支动作识别（确定性路由，不依赖 LLM 分类）。

放在 use_agent=true 之后、Agent 之前。

输入：
  - query: string
  - requisition_draft_id: string  conversation.requisition_draft_id

输出（string，If-Else equals）：
  - action: confirm_submit | modify_quantity | cancel | new_requisition | agent
  - quantity, unit, material_keyword, purpose（new/modify 时可能有）
  - reason: string
"""

import re

_UNITS = ("KG", "kg", "Kg", "箱", "张", "吨", "个", "卷", "桶", "包")
_QTY_UNIT = re.compile(
    r"(\d+(?:\.\d+)?)\s*(KG|kg|Kg|箱|张|吨|个|卷|桶|包)"
)


def _norm_unit(u: str) -> str:
    u = (u or "KG").strip()
    return "KG" if u.lower() == "kg" else u


def _parse_new_requisition(text: str) -> dict | None:
    m = _QTY_UNIT.search(text)
    if not m:
        return None
    qty = m.group(1)
    unit = _norm_unit(m.group(2))
    material = re.sub(
        r"^.*?(?:帮我领|我要领|要领料|要料|申请领|领用|帮我申请|领)",
        "",
        text,
        count=1,
    )
    material = _QTY_UNIT.sub("", material).strip(" 的，,、")
    if not material:
        return None
    return {
        "quantity": qty,
        "unit": unit,
        "material_keyword": material,
        "purpose": "生产领用",
    }


def main(query: str, requisition_draft_id: str = "") -> dict:
    t = (query or "").strip()
    if not t:
        return {"action": "agent", "reason": "empty"}

    if t in ("确认提交", "确认", "好的提交", "提交"):
        return {"action": "confirm_submit", "reason": "user_confirm"}

    if t in ("取消", "算了", "不领了"):
        return {"action": "cancel", "reason": "user_cancel"}

    mod = re.match(r"修改数量(?:为)?\s*(\d+(?:\.\d+)?)\s*(KG|kg|Kg|箱|张|吨|个|卷|桶|包)?", t)
    if mod:
        unit = _norm_unit(mod.group(2) or "KG")
        return {
            "action": "modify_quantity",
            "quantity": mod.group(1),
            "unit": unit,
            "reason": "user_modify",
        }

    if any(k in t for k in ("GON", "领料单", "出仓单", "到哪了", "审批")):
        return {"action": "agent", "reason": "status_query"}

    parsed = _parse_new_requisition(t)
    if parsed:
        return {"action": "new_requisition", "reason": "parsed_new", **parsed}

    if requisition_draft_id and t:
        return {"action": "agent", "reason": "has_draft_fallback"}

    return {"action": "agent", "reason": "unparsed"}
