"""detect_requisition_route 自测 — 发布前执行：
python3 锦顺物料综合智能体/workflows/code/test_detect_requisition_route.py
"""
from detect_requisition_route import main

CASES = [
    # 领料（必进 Agent，不能走查数）
    ("帮我领 10KG 阻焊油墨", "true", "requisition_full"),
    ("帮我领10KG油墨", "true", "requisition"),
    ("我要领料", "true", "requisition_keyword"),
    ("确认提交", "true", "confirm"),
    ("修改数量为 5KG", "true", "modify_qty"),
    ("取消", "true", "cancel"),
    # GON / 查单
    ("查询 GON20260611003 状态", "true", "gon"),
    ("GON20260611003 到哪了", "true", "gon"),
    ("我最近的领料单", "true", "keyword"),
    # MIXED
    ("查一下油墨库存，够的话领 10KG", "true", "mixed"),
    # 仍走分类器 → Fast / 寒暄
    ("统计2025年消耗", "false", "data"),
    ("提供明细", "false", "data_followup"),
    ("查询覆铜板库存", "false", "data_inventory"),
    ("油墨库存多少", "false", "data_stock"),
    ("你好", "false", "chitchat"),
]


def run():
    ok = fail = 0
    for q, exp, note in CASES:
        r = main(q)
        good = r["use_agent"] == exp
        if good:
            ok += 1
            mark = "OK"
        else:
            fail += 1
            mark = "FAIL"
        print(f"[{mark}] {note:20} {q!r} -> {r} (expect {exp})")
    print(f"\n{ok} passed, {fail} failed")
    return fail == 0


if __name__ == "__main__":
    raise SystemExit(0 if run() else 1)
