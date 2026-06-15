"""
[已废弃] 请改用 detect_login_route.py（被动登录 · 不要求用户先说「我要登录」）。

Dify Code 节点：判断当前用户消息是否为「显式登录」意图。

输入：
  - query: string  用户当前一句话（绑 sys.query）

输出：
  - is_login: boolean  是否走登录链
  - reason: string     调试说明
"""


def main(query: str) -> dict:
    text = (query or "").strip()
    if not text:
        return {"is_login": False, "reason": "empty"}

    lower = text.lower()
    if lower.startswith("login "):
        return {"is_login": True, "reason": "prefix_login_en"}

    if not text.startswith("登录"):
        return {"is_login": False, "reason": "no_login_prefix"}

    # 「登录 zhangsan 123456」或「登录：zhangsan 123456」
    rest = text[2:].lstrip("：: \t")
    if not rest:
        return {"is_login": True, "reason": "login_only"}

    parts = rest.split()
    if len(parts) >= 2:
        return {"is_login": True, "reason": "login_with_credentials"}

    if "密码" in rest or "工号" in rest:
        return {"is_login": True, "reason": "login_with_keywords"}

    return {"is_login": True, "reason": "login_prefix"}
