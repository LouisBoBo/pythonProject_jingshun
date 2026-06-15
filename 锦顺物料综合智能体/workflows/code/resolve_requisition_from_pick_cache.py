"""
选型续单 · 从上一轮 pick_cache_json 取物料，跳过 Fast HTTP。

接在 need_fast=false 且 use_pick_cache=true 分支。

输入：
  user_query           ← sys.query（如 JS-NZ-117）
  pick_cache_json      ← conversation.requisition_pick_cache_json
  pending_intent_query ← conversation.requisition_intent_query

输出：与 extract_requisition_material_from_detail 相同字段。
"""

from __future__ import annotations

import json
import re

_CODE_IN_QUERY = re.compile(r"\b([A-Z]{2,}-[A-Z0-9-]+)\b", re.I)


def _result(
    *,
    code: str = "",
    name: str = "",
    qty: str = "",
    unit: str = "",
    ok: bool = False,
    pick_list: str = "",
) -> dict:
    return {
        "material_code": code,
        "material_name": name,
        "available_qty": qty,
        "unit": unit,
        "extract_ok": "true" if ok else "false",
        "pick_required": "false",
        "pick_list": pick_list,
        "match_count": "0",
    }


def _fmt_qty(n: float) -> str:
    return str(n).rstrip("0").rstrip(".") if n % 1 else str(int(n))


def main(
    user_query: str,
    pick_cache_json: str = "",
    pending_intent_query: str = "",
) -> dict:
    code = ""
    m = _CODE_IN_QUERY.search(user_query or "")
    if m:
        code = m.group(1).upper()

    if not code:
        return _result(pick_list="未能识别料号，请直接回复料号，如 JS-NZ-006。")

    raw = (pick_cache_json or "").strip()
    if not raw:
        return _result(
            pick_list=f"选型缓存为空，无法匹配 {code}，将需重新查库存。"
        )

    try:
        rows = json.loads(raw)
    except json.JSONDecodeError:
        return _result(pick_list="选型缓存格式异常，请重新发起领料。")

    if not isinstance(rows, list):
        return _result(pick_list="选型缓存无效，请重新发起领料。")

    for row in rows:
        if not isinstance(row, dict):
            continue
        row_code = str(row.get("code", "")).strip().upper()
        if row_code != code:
            continue
        qty_val = float(row.get("qty", 0) or 0)
        unit = str(row.get("unit", "KG") or "KG").strip()
        name = str(row.get("name", "") or row_code).strip()
        return _result(
            code=row_code,
            name=name,
            qty=_fmt_qty(qty_val),
            unit=unit,
            ok=True,
        )

    intent = (pending_intent_query or "").strip()
    hint = f"（原申请：{intent}）" if intent else ""
    return _result(
        pick_list=f"料号 **{code}** 不在上一轮选型列表中{hint}，需重新查库存。"
    )
