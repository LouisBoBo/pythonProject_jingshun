"""
Dify 代码节点：LLM 文字摘要 + 检索图片 Markdown 合并为最终 Answer。

输入：
  - llm_answer       — LLM 节点 text / answer
  - images_markdown  — 提取节点 images_markdown（勿传裸 URL）
  - context_text     — 可选，无 images_markdown 时从中提取 ![](...)

输出：
  - answer           — 绑定到 Answer 节点
"""

from __future__ import annotations

import re
from typing import Any

IMG_MD_RE = re.compile(r"!\[[^\]]*\]\([^\)]+\)")


def _extract_images(*sources: Any) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for src in sources:
        text = str(src or "")
        for m in IMG_MD_RE.findall(text):
            if m not in seen:
                seen.add(m)
                out.append(m)
    return out


def main(
    llm_answer: str = "",
    images_markdown: str = "",
    context_text: str = "",
    arg1: Any = None,
    **kwargs: Any,
) -> dict[str, str]:
    if not llm_answer:
        llm_answer = str(arg1 or kwargs.get("llm_answer") or "")

    imgs = _extract_images(images_markdown, context_text)
    parts = [llm_answer.strip()] if llm_answer and llm_answer.strip() else []
    if imgs:
        parts.append("\n\n### 相关原文截图\n\n" + "\n\n".join(imgs))

    return {"answer": "\n\n".join(parts) if parts else "未检索到相关内容。"}
