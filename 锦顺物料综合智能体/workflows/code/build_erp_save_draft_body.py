"""
Dify Code：组装 erp_save_draft HTTP Body。

输入：
  - material_code: string
  - quantity: string | number
  - unit: string
  - purpose: string
  - draft_id: string  空=新建；有值=更新
  - dept_id: string   可选
"""

import json


def main(
    material_code: str,
    quantity: str,
    unit: str = "KG",
    purpose: str = "生产领用",
    draft_id: str = "",
    dept_id: str = "",
) -> dict:
    body: dict = {
        "purpose": str(purpose or "生产领用").strip(),
        "items": [
            {
                "material_code": str(material_code or "").strip(),
                "quantity": float(quantity),
                "unit": str(unit or "KG").strip(),
            }
        ],
    }
    did = str(draft_id or "").strip()
    if did:
        body["draft_id"] = did
    dept = str(dept_id or "").strip()
    if dept:
        body["dept_id"] = dept
    return {"body_json": json.dumps(body, ensure_ascii=False)}
