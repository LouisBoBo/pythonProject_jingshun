"""
Dify Code：生成领料确认卡片 Markdown（Fast 链 Answer 直接用）。
"""


def main(
    dept_name: str,
    material_name: str,
    material_code: str,
    quantity: str,
    unit: str,
    available_qty: str,
    purpose: str = "生产领用",
) -> dict:
    qty = float(quantity)
    avail = float(available_qty)
    insufficient = qty > avail

    lines = [
        "### 领料申请确认",
        "",
        "| 项目 | 内容 |",
        "|------|------|",
        f"| 申请部门 | {dept_name} |",
        f"| 物料 | {material_name}（{material_code}） |",
        f"| 申请数量 | {quantity} {unit} |",
        f"| 当前可用库存 | {available_qty} {unit} |",
        f"| 用途 | {purpose} |",
        "",
    ]
    if insufficient:
        lines.append(
            f"**当前可用库存不足（申请 {quantity} {unit}，可用 {available_qty} {unit}），"
            f"暂无法提交。请回复「修改数量为 X」或「取消」。**"
        )
    else:
        lines.append(
            "请回复 **「确认提交」**；修改请说 **「修改数量为 X」**；取消请说 **「取消」**。"
        )

    card = "\n".join(lines)
    return {
        "confirm_card": card,
        "can_submit": "false" if insufficient else "true",
    }
