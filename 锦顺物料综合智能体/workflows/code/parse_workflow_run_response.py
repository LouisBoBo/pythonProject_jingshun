"""
主 Chatflow Fast 路径 · Code 节点
解析 Workflow Run API blocking 响应，提取 summary / detail / conversation_id。

输入变量：raw（HTTP 请求 / body 或 text）
用于：锦顺物料综合助手 · Fast 查数分支
"""
import json


def main(raw: str) -> dict:
    text = (raw or "").strip()
    summary = ""
    detail = ""
    conversation_id = ""

    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        return {
            "summary": "查询失败：响应不是有效 JSON",
            "detail": text[:2000] if text else "",
            "conversation_id": "",
        }

    # Workflow API blocking: data.outputs
    data = obj.get("data") or obj
    outputs = data.get("outputs") or obj.get("outputs") or {}

    summary = (
        outputs.get("summary")
        or outputs.get("answer")
        or ""
    )
    detail = outputs.get("detail") or outputs.get("answer") or summary
    conversation_id = outputs.get("conversation_id") or ""

    if data.get("status") == "failed" or obj.get("code") not in (None, "success", 200):
        err = (data.get("error") or obj.get("message") or "工作流执行失败")
        return {
            "summary": str(err)[:300],
            "detail": "",
            "conversation_id": conversation_id,
        }

    if not detail and not summary:
        summary = "数据分析未返回结果，请稍后重试。"

    return {
        "summary": summary,
        "detail": detail,
        "conversation_id": conversation_id,
    }
