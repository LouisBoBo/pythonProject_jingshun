"""
Dify Code 节点：解析 erp_login HTTP 响应。

输出均为 string（login_ok 为 "true"/"false"，供 If-Else 等于 判断）。
"""


def main(body: str | dict, status_code: int = 200) -> dict:
    import json
    from datetime import datetime, timedelta, timezone

    def fail(msg: str) -> dict:
        return {
            "auth_token": "",
            "token_expires_at": "",
            "user_profile": {},
            "login_ok": "false",
            "login_message": msg,
        }

    if status_code and int(status_code) >= 400:
        return fail(f"登录失败（HTTP {status_code}），请检查工号密码。")

    data = body
    if isinstance(body, str):
        body = body.strip()
        if not body:
            return fail("登录失败：ERP 返回为空。")
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            return fail("登录失败：响应不是合法 JSON。")

    if not isinstance(data, dict):
        return fail("登录失败：响应格式异常。")

    token = data.get("access_token") or ""
    user = data.get("user") or {}
    if not token or not user:
        msg = data.get("message") or data.get("detail") or "用户名或密码错误。"
        if isinstance(msg, dict):
            msg = msg.get("message") or str(msg)
        return fail(str(msg))

    expires_in = int(data.get("expires_in") or 7200)
    expires_at = (
        datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    ).isoformat()

    name = user.get("name") or user.get("username") or ""
    dept = user.get("dept_name") or ""
    login_message = (
        f"登录成功，{name}（{dept}）。"
        f"您可以直接说：查库存、统计用量、或帮我领 XX 物料。"
    )

    return {
        "auth_token": token,
        "token_expires_at": expires_at,
        "user_profile": user,
        "login_ok": "true",
        "login_message": login_message,
    }
