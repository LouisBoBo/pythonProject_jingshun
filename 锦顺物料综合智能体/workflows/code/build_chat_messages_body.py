"""
Fast 路径 · HTTP 前组装 chat-messages 请求体

节点：「组装Chat请求」Code（放在 HTTP 之前）
输入：
  query          ← sys.query / 用户输入
  conversation_id ← conversation.data_analysis_conversation_id
输出：
  body_json      ← 给 HTTP Body（整段 JSON 字符串）
  has_conversation_id ← 是否带 id（调试用）

规则：
  - 新问：conversation_id 为空 → Body **不含** conversation_id 字段
  - 追问：conversation_id 非空 → Body **必须带** conversation_id
  - user 固定 fast-path-user（首问/追问必须相同）
"""
import json


def main(query: str, conversation_id: str = "") -> dict:
    q = (query or "").strip()
    if not q:
        return {
            "body_json": "",
            "has_conversation_id": "false",
            "error": "query 为空",
        }

    payload = {
        "inputs": {},
        "query": q,
        "response_mode": "streaming",
        "user": "fast-path-user",
    }
    cid = (conversation_id or "").strip()
    if cid and cid not in ("null", "undefined", "{{conversation.data_analysis_conversation_id}}"):
        payload["conversation_id"] = cid

    return {
        "body_json": json.dumps(payload, ensure_ascii=False),
        "has_conversation_id": "true" if cid else "false",
        "error": "",
    }
