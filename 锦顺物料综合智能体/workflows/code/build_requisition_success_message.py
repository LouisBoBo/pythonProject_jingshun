"""Dify Code：提交成功用户可见文案。"""


def main(requisition_no: str, status: str = "PENDING_APPROVAL") -> dict:
    no = str(requisition_no or "").strip()
    status_map = {
        "PENDING_APPROVAL": "等待仓库审核",
        "APPROVED": "已通过",
        "REJECTED": "已驳回",
    }
    label = status_map.get(str(status or ""), "等待仓库审核")
    message = (
        f"领料申请已成功提交。\n\n"
        f"- 领料单号：**{no}**\n"
        f"- 当前状态：{label}\n\n"
        f"您可以回复「查询 {no} 状态」查看最新进展。"
    )
    return {"success_message": message}
