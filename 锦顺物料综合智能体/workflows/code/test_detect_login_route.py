"""detect_login_route 本地自测 — 发布前在仓库根目录执行：
python3 锦顺物料综合智能体/workflows/code/test_detect_login_route.py
"""
from detect_login_route import main

CASES = [
    # (query, auth_token, login_pending, expected_should, expected_action, note)
    ("我要领料", "", "", "true", "prompt", "领料触登录，不提取"),
    ("帮我领 10KG 阻焊油墨", "", "", "true", "prompt", "领料+单位"),
    ("zhangsan 123456", "", "", "true", "authenticate", "裸凭据也要识别"),
    ("登录 zhangsan 123456", "", "", "true", "authenticate", "显式登录"),
    ("工号 zhangsan 密码 123456", "", "", "true", "authenticate", "带标签"),
    ("统计2025年消耗", "", "", "false", "skip", "查数不登录"),
    ("你好", "", "", "false", "skip", "寒暄"),
    ("登录", "", "", "true", "prompt", "仅关键词，提示补凭据"),
    ("好的", "", "true", "false", "skip", "pending但非凭据"),
    ("zhangsan 123456", "", "true", "true", "authenticate", "pending+凭据"),
    ("我要领料", "tok", "", "false", "skip", "已登录跳过"),
    ("zhangsan 123456", "tok", "", "false", "skip", "已登录不重复登"),
    ("查询 GON20260611003 状态", "", "", "true", "prompt", "GON查状态需登录"),
]


def run():
    ok = fail = 0
    for q, tok, pend, exp_should, exp_action, note in CASES:
        r = main(q, tok, pend)
        good = r["should_login"] == exp_should and r["login_action"] == exp_action
        if good:
            ok += 1
            mark = "OK"
        else:
            fail += 1
            mark = "FAIL"
        cred = ""
        if r.get("username"):
            cred = f" user={r['username']}"
        print(
            f"[{mark}] {note:20} | {q!r:28} -> "
            f"should={r['should_login']} action={r['login_action']}{cred} "
            f"(expect {exp_should}/{exp_action})"
        )
    print(f"\n{ok} passed, {fail} failed")
    return fail == 0


if __name__ == "__main__":
    import sys
    sys.exit(0 if run() else 1)
