"""
Dify Code：组装 requisition_pending 会话变量（Object）供 Assigner 写入。

输入来自搜料/库存/草稿前的解析结果。
"""

import json


def main(
    material_code: str,
    material_name: str,
    quantity: str,
    unit: str,
    available_qty: str,
    purpose: str = "生产领用",
) -> dict:
    pending = {
        "material_code": str(material_code or "").strip(),
        "material_name": str(material_name or "").strip(),
        "quantity": float(quantity),
        "unit": str(unit or "KG").strip(),
        "available_qty": float(available_qty),
        "purpose": str(purpose or "生产领用").strip(),
    }
    return {"pending_json": json.dumps(pending, ensure_ascii=False)}
