"""解析 erp_check_inventory 响应。"""

import json


def main(body: str | dict, status_code: int = 200) -> dict:
    def fail(msg: str) -> dict:
        return {
            "ok": "false",
            "available_qty": "0",
            "on_hand_qty": "0",
            "material_code": "",
            "material_name": "",
            "unit": "",
            "message": msg,
        }

    if status_code and int(status_code) >= 400:
        return fail(f"查库存失败 HTTP {status_code}")

    data = body
    if isinstance(body, str):
        try:
            data = json.loads(body.strip() or "{}")
        except json.JSONDecodeError:
            return fail("库存响应不是 JSON")

    if not isinstance(data, dict) or not data.get("material_code"):
        return fail("未返回库存数据")

    avail = float(data.get("available_qty") or 0)
    return {
        "ok": "true",
        "available_qty": str(avail),
        "on_hand_qty": str(data.get("on_hand_qty") or 0),
        "material_code": data.get("material_code") or "",
        "material_name": data.get("material_name") or "",
        "unit": data.get("unit") or "KG",
        "message": "",
    }
