"""detect_requisition_action 自测"""
from detect_requisition_action import main

CASES = [
    ("确认提交", "", "confirm_submit"),
    ("修改数量为 5KG", "DRAFT-1", "modify_quantity"),
    ("取消", "DRAFT-1", "cancel"),
    ("帮我领 10KG 阻焊油墨", "", "new_requisition"),
    ("查询 GON20260611003 状态", "", "agent"),
    ("我要领覆铜板 5 张", "", "new_requisition"),
]

for q, draft, exp in CASES:
    r = main(q, draft)
    ok = r["action"] == exp
    print(f"[{'OK' if ok else 'FAIL'}] {q!r:30} -> {r['action']} (expect {exp})")
