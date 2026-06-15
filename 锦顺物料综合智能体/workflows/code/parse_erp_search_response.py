"""解析 erp_search_material 响应，取第一条物料。"""

import json


def main(body: str | dict, status_code: int = 200) -> dict:
    def fail(msg: str) -> dict:
        return {
            "ok": "false",
            "material_code": "",
            "material_name": "",
            "unit": "",
            "message": msg,
        }

    if status_code and int(status_code) >= 400:
        return fail(f"搜料失败 HTTP {status_code}")

    data = body
    if isinstance(body, str):
        try:
            data = json.loads(body.strip() or "{}")
        except json.JSONDecodeError:
            return fail("搜料响应不是 JSON")

    items = data.get("items") if isinstance(data, dict) else None
    if not items:
        return fail("未找到匹配物料，请换关键字")

    first = items[0]
    return {
        "ok": "true",
        "material_code": first.get("material_code") or "",
        "material_name": first.get("material_name") or "",
        "unit": first.get("unit") or "KG",
        "message": "",
    }
