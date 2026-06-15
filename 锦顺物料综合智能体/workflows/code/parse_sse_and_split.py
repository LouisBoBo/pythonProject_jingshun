"""
Fast / 网关 · 解析 chat-messages 响应并拆分 / 组装展示内容

展示顺序（detail）：表格 → 要点速览 → ECharts
"""
import json
import re

SUMMARY_MARKERS = ("📊 要点速览", "▸ 简要分析", "💡 建议")
ECHARTS_RE = re.compile(r"```echarts\s*\n([\s\S]*?)```", re.IGNORECASE)
TABLE_RE = re.compile(r"(\|[^\n]+\|\s*\n(?:\|[^\n]+\|\s*\n?)+)")


def normalize_answer(text: str) -> str:
    t = (text or "").strip()
    t = re.sub(r"```\s*\|", "```\n\n|", t)
    return t


def extract_parts(answer: str) -> tuple[str, str, str]:
    """拆出 table / summary（含表前表后分析 + 要点速览）/ echarts。"""
    text = normalize_answer(answer)
    if not text:
        return "", "", ""

    echarts = ""
    m = ECHARTS_RE.search(text)
    if m:
        echarts = f"```echarts\n{m.group(1).strip()}\n```"
    rest = ECHARTS_RE.sub("", text).strip()

    marker_summary = ""
    cut = len(rest)
    for marker in SUMMARY_MARKERS:
        idx = rest.find(marker)
        if idx != -1:
            cut = min(cut, idx)
            marker_summary = rest[idx:].strip()

    body = rest[:cut].strip() if cut < len(rest) else rest

    table = ""
    prose = ""
    tm = TABLE_RE.search(body)
    if tm:
        table = tm.group(1).strip()
        before = body[: tm.start()].strip()
        after = body[tm.end() :].strip()
        prose = "\n\n".join(p for p in (before, after) if p)
    elif body:
        # 无 markdown 管道表时，正文留给 summary（如纯文字结论）
        prose = body

    summary = "\n\n".join(p for p in (prose, marker_summary) if p)

    return table, summary, echarts


def assemble_display(table: str, summary: str, echarts: str) -> str:
    """列表 → 要点速览 → ECHARTS"""
    parts = [p for p in (table, summary, echarts) if p]
    if parts:
        return "\n\n".join(parts)
    return ""


def split_answer(answer: str) -> tuple[str, str]:
    """summary=要点速览；detail=按展示顺序组装后的全文。"""
    table, summary, echarts = extract_parts(answer)
    display = assemble_display(table, summary, echarts)
    if display:
        return summary or "查询完成，明细如下。", display
    text = normalize_answer(answer)
    if len(text) <= 300:
        return text, text
    return text[:300] + "…", text


def parse_sse(raw: str) -> tuple[str, str]:
    text = raw or ""
    chunks = []
    final_answer = ""
    conversation_id = ""

    stripped = text.strip()
    if stripped.startswith("{"):
        try:
            obj = json.loads(stripped)
            data = obj.get("data") or obj
            outputs = data.get("outputs") or obj.get("outputs") or {}
            final_answer = (
                outputs.get("answer")
                or data.get("answer")
                or obj.get("answer")
                or ""
            )
            conversation_id = (
                outputs.get("conversation_id")
                or data.get("conversation_id")
                or obj.get("conversation_id")
                or ""
            )
            if final_answer:
                return normalize_answer(final_answer), conversation_id
        except json.JSONDecodeError:
            pass

    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("data:"):
            continue
        payload = line[5:].strip()
        if not payload or payload == "[DONE]":
            continue
        try:
            obj = json.loads(payload)
        except json.JSONDecodeError:
            continue

        cid = obj.get("conversation_id")
        if cid:
            conversation_id = cid
        # workflow_finished 嵌套
        data_top = obj.get("data") or {}
        if isinstance(data_top, dict):
            cid2 = data_top.get("conversation_id")
            if cid2:
                conversation_id = cid2

        event = obj.get("event")
        if event == "message":
            part = obj.get("answer") or ""
            if part:
                chunks.append(part)
        elif event == "workflow_finished":
            data = obj.get("data") or {}
            outputs = data.get("outputs") or {}
            final_answer = outputs.get("answer") or final_answer
            cid = obj.get("conversation_id") or conversation_id
            if cid:
                conversation_id = cid

    answer = normalize_answer((final_answer or "".join(chunks)).strip())
    if not answer:
        answer = "数据分析未返回结果，请稍后重试或联系管理员。"
    return answer, conversation_id or ""


def main(raw: str) -> dict:
    answer, conversation_id = parse_sse(raw)
    table, summary, echarts = extract_parts(answer)
    display = assemble_display(table, summary, echarts)
    if not display:
        display = answer

    return {
        "answer": answer,
        "summary": summary,
        "detail": display,
        "table": table,
        "echarts": echarts,
        "conversation_id": conversation_id,
    }
