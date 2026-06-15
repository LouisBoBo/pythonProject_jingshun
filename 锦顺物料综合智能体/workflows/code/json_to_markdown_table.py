"""
Dify 代码节点：将 JSON 数组字符串转换为标准 Markdown 表格。

Markdown 表格须含表头行 + | --- | 分隔行 + 数据行，聊天端才能正确渲染。

输入变量（任一即可）：
  - md_text / arg1：JSON 数组字符串

输出变量：
  - md_text   — 完整 Markdown 表格
  - row_count — 行数（字符串）
"""

from __future__ import annotations

import json
from typing import Any


def _unwrap_markdown_fence(text: str) -> str:
    text = text.strip()
    if not text.startswith("```"):
        return text
    lines = text.split("\n")
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _to_rows(raw: Any) -> list[dict[str, Any]]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return [r for r in raw if isinstance(r, dict)]
    text = _unwrap_markdown_fence(str(raw))
    if not text:
        return []
    parsed = json.loads(text)
    if isinstance(parsed, list):
        return [r for r in parsed if isinstance(r, dict)]
    return []


def _escape_cell(value: Any) -> str:
    s = "" if value is None else str(value)
    return s.replace("|", "\\|").replace("\n", " ")


def main(md_text: Any = None, arg1: Any = None, **kwargs: Any) -> dict[str, str]:
    raw = md_text if md_text is not None else arg1
    if raw is None:
        raw = kwargs.get("md_text") or kwargs.get("arg1")

    rows = _to_rows(raw)
    if not rows:
        return {"md_text": "", "row_count": "0"}

    headers = list(rows[0].keys())
    head_line = "| " + " | ".join(headers) + " |"
    split_line = "| " + " | ".join(["---"] * len(headers)) + " |"
    body_lines = [
        "| " + " | ".join(_escape_cell(row.get(col, "")) for col in headers) + " |"
        for row in rows
    ]
    table = "\n".join([head_line, split_line, *body_lines])
    return {"md_text": table, "row_count": str(len(rows))}
