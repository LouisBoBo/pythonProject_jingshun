"""
选型轮 · 保存用户原始领料意图，供下一轮只回复料号时续流程。

接在 pick_required=true 分支的 Assigner 前（或与 Assigner 同轮写入）。

输入：
  user_query ← sys.query（如「帮我领 10KG 阻焊油墨」）
输出：
  requisition_intent_query  原话
  requisition_pick_waiting  "true"
"""


def main(user_query: str) -> dict:
    q = (user_query or "").strip()
    return {
        "requisition_intent_query": q,
        "requisition_pick_waiting": "true" if q else "false",
    }
