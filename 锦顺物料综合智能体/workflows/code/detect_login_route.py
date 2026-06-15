"""
Dify Code 节点：登录路由（被动登录 · 单节点决策 + 可选直出凭据）。

输入：
  - query: string
  - auth_token: string
  - login_pending: string

输出（**全部为 string**，If-Else 用「等于」比较）：
  - should_login: "true" | "false"
  - login_action: "authenticate" | "prompt" | "skip"
  - username: string   authenticate 时可直绑 HTTP，空则再走 Extractor
  - password: string
  - reason: string
"""


import re

_GON = re.compile(r"GON\d+", re.I)
_DRAFT = re.compile(r"DRAFT-\d", re.I)


def _norm_flag(value: str) -> bool:
    return str(value or "").strip().lower() in {"true", "1", "yes", "是"}


def _result(
    should: bool,
    action: str,
    reason: str,
    username: str = "",
    password: str = "",
) -> dict:
    return {
        "should_login": "true" if should else "false",
        "login_action": action,
        "username": username or "",
        "password": password or "",
        "reason": reason,
    }


def _looks_like_credential_pair(text: str) -> tuple[str, str] | None:
    """「zhangsan 123456」类：两段 token，无业务动词。"""
    import re

    parts = text.strip().split()
    if len(parts) != 2:
        return None
    biz_markers = (
        "领", "查", "帮", "申请", "统计", "多少", "物料", "油墨", "消耗",
        "KG", "kg", "箱", "张", "吨", "个", "覆铜", "明细",
    )
    if any(m in text for m in biz_markers):
        return None
    user, pwd = parts[0], parts[1]
    if re.match(r"^[a-zA-Z0-9_\-]+$", user) and pwd:
        return user, pwd
    return None


def _extract_credentials(text: str) -> tuple[str, str] | None:
    import re

    t = text.strip()
    if not t:
        return None

    m = re.search(
        r"(?:工号|账号|用户名|账户)\s*[：:]?\s*(\S+)\s*(?:密码|口令)\s*[：:]?\s*(\S+)",
        t,
        re.I,
    )
    if m:
        return m.group(1), m.group(2)

    m = re.search(
        r"(?:密码|口令)\s*[：:]?\s*(\S+)\s*(?:工号|账号|用户名)\s*[：:]?\s*(\S+)",
        t,
        re.I,
    )
    if m:
        return m.group(2), m.group(1)

    if t.lower().startswith("login "):
        parts = t.split()
        if len(parts) >= 3:
            return parts[1], parts[2]

    if t.startswith("登录"):
        rest = t[2:].lstrip("：: \t")
        parts = rest.split()
        if len(parts) >= 2:
            return parts[0], parts[1]

    return _looks_like_credential_pair(t)


def _needs_erp_auth(text: str) -> bool:
    t = text.strip()
    if not t:
        return False

    requisition_keywords = (
        "领料", "我要领", "要领料", "要料", "帮我领", "申请领",
        "出库申请", "确认提交", "提交审批", "审批到哪", "我的领料",
        "我的申请", "领用", "要申请",
    )
    if any(k in t for k in requisition_keywords):
        return True

    if _GON.search(t) or _DRAFT.search(t):
        return True

    if "领" in t and any(
        x in t for x in ("够的话", "够就", "先查", "再领", "再帮我领", "帮我申请")
    ):
        return True

    if "领" in t and any(u in t for u in ("KG", "kg", "箱", "张", "吨", "个")):
        return True

    return False


def _is_login_keyword_only(text: str) -> bool:
    t = text.strip()
    if t in {"登录", "登陆"}:
        return True
    if t.startswith("登录") and _extract_credentials(t) is None:
        rest = t[2:].lstrip("：: \t")
        return not rest
    return False


def main(query: str, auth_token: str = "", login_pending: str = "") -> dict:
    text = (query or "").strip()

    if (auth_token or "").strip():
        return _result(False, "skip", "already_logged_in")

    creds = _extract_credentials(text)
    if creds:
        return _result(
            True, "authenticate", "explicit_credentials", creds[0], creds[1]
        )

    if _is_login_keyword_only(text):
        return _result(True, "prompt", "login_keyword_only")

    if _needs_erp_auth(text):
        return _result(True, "prompt", "need_erp_auth")

    if _norm_flag(login_pending):
        pair = _looks_like_credential_pair(text)
        if pair:
            return _result(
                True, "authenticate", "pending_two_tokens", pair[0], pair[1]
            )

    return _result(False, "skip", "normal_flow")
