"""
领料 Fast 路径 · 从 detail 抽取库存（旧版，仅数量）。

已 supersede：请用 extract_requisition_material_from_detail.py（料号+名称+库存）。
"""

import re

_QTY_UNIT_PATTERNS = (
    re.compile(
        r"可用(?:库存|量)?[：:\s]*([\d,]+(?:\.\d+)?)\s*(KG|kg|Kg|箱|张|吨|个|卷|桶|包)?",
        re.I,
    ),
    re.compile(
        r"([\d,]+(?:\.\d+)?)\s*(KG|kg|Kg|箱|张|吨|个|卷|桶|包)\s*(?:可用|库存)",
        re.I,
    ),
    re.compile(
        r"\|\s*([\d,]+(?:\.\d+)?)\s*\|\s*(KG|kg|Kg|箱|张|吨|个|卷|桶|包)\s*\|",
        re.I,
    ),
)


def _norm_qty(s: str) -> str:
    return str(s or "").replace(",", "").strip()


def main(detail: str) -> dict:
    text = (detail or "").strip()
    if not text:
        return {
            "available_qty": "",
            "unit": "",
            "extract_ok": "false",
        }

    for pat in _QTY_UNIT_PATTERNS:
        m = pat.search(text)
        if m:
            qty = _norm_qty(m.group(1))
            unit = (m.group(2) or "KG").strip()
            if qty:
                return {
                    "available_qty": qty,
                    "unit": unit.upper() if unit.upper() == "KG" else unit,
                    "extract_ok": "true",
                }

    # 兜底：表格行内第一个合理数字
    nums = re.findall(r"([\d,]+(?:\.\d+)?)", text)
    for n in nums:
        v = float(_norm_qty(n))
        if 0 < v < 1e9:
            return {
                "available_qty": _norm_qty(n),
                "unit": "KG",
                "extract_ok": "true",
            }

    return {
        "available_qty": "",
        "unit": "",
        "extract_ok": "false",
    }
