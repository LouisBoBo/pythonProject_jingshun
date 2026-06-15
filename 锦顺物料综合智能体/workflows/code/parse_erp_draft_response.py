"""解析 erp_save_draft 响应。"""

import json


def main(body: str | dict, status_code: int = 200) -> dict:
    def fail(msg: str) -> dict:
        return {"ok": "false", "draft_id": "", "message": msg}

    if status_code and int(status_code) >= 400:
        return fail(f"保存草稿失败 HTTP {status_code}")

    data = body
    if isinstance(body, str):
        try:
            data = json.loads(body.strip() or "{}")
        except json.JSONDecodeError:
            return fail("草稿响应不是 JSON")

    draft_id = ""
    if isinstance(data, dict):
        draft_id = data.get("draft_id") or ""

    if not draft_id:
        return fail("未返回 draft_id")

    return {"ok": "true", "draft_id": draft_id, "message": ""}
