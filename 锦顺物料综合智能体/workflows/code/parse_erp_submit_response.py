"""解析 erp_submit_requisition 响应。"""

import json


def main(body: str | dict, status_code: int = 200) -> dict:
    def fail(msg: str, code: str = "") -> dict:
        return {
            "ok": "false",
            "requisition_no": "",
            "status": "",
            "message": msg,
            "error_code": code,
        }

    if status_code == 404:
        return fail("草稿不存在或已过期", "DRAFT_EXPIRED")
    if status_code == 409:
        msg = "库存不足，无法提交"
        if isinstance(body, str):
            try:
                data = json.loads(body)
                msg = data.get("message") or msg
            except json.JSONDecodeError:
                pass
        elif isinstance(body, dict):
            msg = body.get("message") or msg
        return fail(str(msg), "INSUFFICIENT_STOCK")
    if status_code and int(status_code) >= 400:
        return fail(f"提交失败 HTTP {status_code}")

    data = body
    if isinstance(body, str):
        try:
            data = json.loads(body.strip() or "{}")
        except json.JSONDecodeError:
            return fail("提交响应不是 JSON")

    if not isinstance(data, dict):
        return fail("提交响应格式异常")

    no = data.get("requisition_no") or ""
    if not no:
        return fail("未返回领料单号")

    status = data.get("status") or "PENDING_APPROVAL"
    return {
        "ok": "true",
        "requisition_no": no,
        "status": status,
        "message": data.get("message") or "已提交，等待仓库审核",
        "error_code": "",
    }
