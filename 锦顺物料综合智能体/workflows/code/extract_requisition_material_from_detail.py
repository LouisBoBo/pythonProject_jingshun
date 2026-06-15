"""
领料 Fast · 解析 DATA Fast 表格：唯一物料 vs 需用户选型。

pick_required=true 时 **不产出**有效 material_code；画布走选型 Answer，**不进 Agent**。
extract_ok=true 时料号唯一；画布 Assigner → Agent。

输入：detail, user_query
输出：material_code, material_name, available_qty, unit, extract_ok,
      pick_required, pick_list, match_count
"""

from __future__ import annotations

import json
import re
from typing import NamedTuple

_CODE_IN_QUERY = re.compile(r"\b([A-Z]{2,}-[A-Z0-9-]+)\b", re.I)
_QTY_IN_QUERY = re.compile(
    r"([\d,]+(?:\.\d+)?)\s*(KG|kg|Kg|箱|张|吨|个|卷|桶|包)",
    re.I,
)
_TABLE_ROW = re.compile(
    r"^\|\s*([A-Z0-9-]+)\s*\|\s*([^|]+?)\s*\|\s*([\d,]+(?:\.\d+)?)\s*\|\s*([^|]+?)\s*\|",
    re.I | re.M,
)


class MaterialRow(NamedTuple):
    code: str
    name: str
    qty: float
    unit: str


def _norm_qty(s: str) -> float:
    return float(str(s or "").replace(",", "").strip() or 0)


def _parse_requested(user_query: str, fallback_query: str = "") -> tuple[float, str]:
    for src in (user_query, fallback_query):
        m = _QTY_IN_QUERY.search(src or "")
        if m:
            unit = (m.group(2) or "KG").strip()
            return _norm_qty(m.group(1)), unit.upper() if unit.upper() == "KG" else unit
    return 0.0, "KG"


def _parse_code_in_query(user_query: str) -> str:
    m = _CODE_IN_QUERY.search(user_query or "")
    return m.group(1).upper() if m else ""


def _parse_table(text: str) -> list[MaterialRow]:
    rows: list[MaterialRow] = []
    for m in _TABLE_ROW.finditer(text):
        code = m.group(1).strip().upper()
        if code.upper() in ("MATERIAL_CODE", "料号", "---"):
            continue
        if set(code) <= {"-", " "}:
            continue
        name = m.group(2).strip()
        qty = _norm_qty(m.group(3))
        unit = m.group(4).strip()
        rows.append(MaterialRow(code=code, name=name, qty=qty, unit=unit))
    return rows


def _pick_list_markdown(rows: list[MaterialRow], limit: int = 10) -> str:
    top = rows[:limit]
    lines = [
        "### 请选择要领的料号",
        "",
        "| 料号 | 物料名称 | 可用库存 | 单位 |",
        "|------|----------|----------|------|",
    ]
    for r in top:
        lines.append(f"| {r.code} | {r.name} | {r.qty:g} | {r.unit} |")
    lines.extend(
        [
            "",
            "请直接回复 **料号**（例如 `JS-NZ-006`），或说「领 JS-NZ-006 10KG」。",
        ]
    )
    return "\n".join(lines)


def _pick_cache_json(rows: list[MaterialRow]) -> str:
    payload = [
        {"code": r.code, "name": r.name, "qty": r.qty, "unit": r.unit}
        for r in rows
    ]
    return json.dumps(payload, ensure_ascii=False)


def _result(
    *,
    code: str = "",
    name: str = "",
    qty: str = "",
    unit: str = "",
    ok: bool = False,
    pick: bool = False,
    pick_list: str = "",
    match_count: int = 0,
    pick_cache_json: str = "",
) -> dict:
    return {
        "material_code": code,
        "material_name": name,
        "available_qty": qty,
        "unit": unit,
        "extract_ok": "true" if ok else "false",
        "pick_required": "true" if pick else "false",
        "pick_list": pick_list,
        "match_count": str(match_count),
        "pick_cache_json": pick_cache_json,
    }


def main(detail: str, user_query: str = "", pending_intent_query: str = "") -> dict:
    text = (detail or "").strip()
    if not text:
        return _result()

    intent = (pending_intent_query or "").strip()
    rows = _parse_table(text)
    if not rows:
        return _result(pick_list="未能解析物料表格，请补充更具体的物料名称或料号。")

    req_qty, req_unit = _parse_requested(user_query, intent)
    explicit = _parse_code_in_query(user_query)
    if explicit:
        for r in rows:
            if r.code == explicit:
                return _result(
                    code=r.code,
                    name=r.name,
                    qty=str(r.qty).rstrip("0").rstrip(".") if r.qty % 1 else str(int(r.qty)),
                    unit=r.unit or req_unit,
                    ok=True,
                    match_count=len(rows),
                )

    in_stock = [r for r in rows if r.qty > 0]
    if not in_stock:
        return _result(
            pick=True,
            pick_list="匹配到的物料 **当前均无可用库存**，请更换物料或联系仓库。",
            match_count=len(rows),
        )

    if len(in_stock) == 1:
        r = in_stock[0]
        q = str(r.qty).rstrip("0").rstrip(".") if r.qty % 1 else str(int(r.qty))
        return _result(
            code=r.code,
            name=r.name,
            qty=q,
            unit=r.unit or req_unit,
            ok=True,
            match_count=len(rows),
        )

    # 多条有库存：仅当「够领」的唯一一条时自动选中
    if req_qty > 0:
        enough = [r for r in in_stock if r.qty >= req_qty]
        if len(enough) == 1:
            r = enough[0]
            q = str(r.qty).rstrip("0").rstrip(".") if r.qty % 1 else str(int(r.qty))
            return _result(
                code=r.code,
                name=r.name,
                qty=q,
                unit=r.unit or req_unit,
                ok=True,
                match_count=len(rows),
            )

    ranked = sorted(in_stock, key=lambda x: x.qty, reverse=True)
    return _result(
        pick=True,
        pick_list=_pick_list_markdown(ranked),
        match_count=len(rows),
        pick_cache_json=_pick_cache_json(ranked),
    )
