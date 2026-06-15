"""
领料 Fast 路径 · 将用户领料原话转为 DATA Fast question。

领料场景若名称模糊（如「阻焊油墨」），要求 SQL 侧优先缩小范围，避免一次 50 行。
"""

import re

_QTY_IN_QUERY = re.compile(
    r"([\d,]+(?:\.\d+)?)\s*(KG|kg|Kg|箱|张|吨|个|卷|桶|包)",
    re.I,
)
_CODE_IN_QUERY = re.compile(r"\b([A-Z]{2,}-[A-Z0-9-]+)\b", re.I)


def main(query: str, dept_name: str = "") -> dict:
    raw = (query or "").strip()
    if not raw:
        return {"inventory_query": "", "error": "query 为空"}

    dept = (dept_name or "").strip()
    dept_hint = f"（部门/事业部：{dept}）" if dept else ""

    code_m = _CODE_IN_QUERY.search(raw)
    code_hint = f"用户已指定料号 **{code_m.group(1).upper()}**，只查这一条。" if code_m else ""

    qty_m = _QTY_IN_QUERY.search(raw)
    qty_hint = f"用户申请数量约 **{qty_m.group(1)}{qty_m.group(2)}**。" if qty_m else ""

    inventory_query = (
        f"【领料查库存】用户原话：{raw}{dept_hint}。{qty_hint}{code_hint}\n"
        f"请查询 material_code、物料名称、当前可用库存数量、单位。\n"
        f"要求：\n"
        f"1. 若用户已给料号，只返回该料号一行；\n"
        f"2. 若名称模糊且匹配多条，**只返回可用库存>0** 的物料，按库存从高到低 **最多10行**；\n"
        f"3. 表格列名保持：material_code | 物料名称 | 当前可用库存数量 | 单位；\n"
        f"4. 若仍无法唯一确定要领哪一种，在表格下用一句话说明「需用户指定料号」。"
    )
    return {"inventory_query": inventory_query, "error": ""}
