"""
Dify 代码节点：从知识库检索 HTTP 响应提取文本 + 图片。

支持两种响应格式：
  1. RAGFlow：{"code":0,"data":{"chunks":[...]}}
  2. 旧格式：{"records":[...]}

输入变量：
  - body            — HTTP 响应 body
  - status_code     — HTTP 状态码（可选）
  - image_base_url  — 图片服务根地址，默认 http://192.168.60.2:15409

输出变量：
  - context_text      — 检索上下文（绑 LLM 输入，供阅读理解）
  - images_markdown   — 仅 Markdown 图片（绑 Answer，用于展示）
  - records_json / record_count / image_count / ok / message

Dify 连线（方式一，推荐）：
  HTTP 检索 → Code 本节点 → LLM（context_text 作参考上下文）
                          ↘ Answer 节点内容：

    {{#LLM.text#}}

    ### 相关原文截图

    {{#提取records / images_markdown#}}

  注意：Answer 必须绑 images_markdown（![](url) 语法），不要绑裸 URL。
"""

from __future__ import annotations

import html
import json
import re
from typing import Any

DEFAULT_IMAGE_BASE = "http://192.168.60.2:15409"
PUA_RE = re.compile(r"[\ue000-\uf8ff]")


def _fail(msg: str) -> dict[str, str]:
    return {
        "ok": "false",
        "message": msg,
        "context_text": "",
        "records_json": "[]",
        "record_count": "0",
        "image_count": "0",
        "images_markdown": "",
    }


def _parse_body(body: Any) -> dict[str, Any]:
    if isinstance(body, dict):
        return body
    if not isinstance(body, str):
        return {}
    text = body.strip()
    if not text:
        return {}
    return json.loads(text)


def _html_to_text(content: str) -> str:
    if not content:
        return ""

    text = html.unescape(content)
    text = re.sub(r"<caption[^>]*>(.*?)</caption>", r"\n【\1】\n", text, flags=re.I | re.S)
    text = re.sub(r"</tr\s*>", "\n", text, flags=re.I)
    text = re.sub(r"</t[dh]\s*>", " ", text, flags=re.I)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"[ \t\u3000]+", " ", text)
    text = re.sub(r"\n[ \t]+", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _clean_text(content: str) -> str:
    text = PUA_RE.sub("", content or "")
    return text.strip()


def _image_url(image_base: str, image_id: str) -> str:
    if not image_id:
        return ""
    base = (image_base or DEFAULT_IMAGE_BASE).rstrip("/")
    return f"{base}/v1/document/image/{image_id}"


def _extract_raw_items(data: dict[str, Any]) -> tuple[list[dict[str, Any]], str]:
    inner = data.get("data")
    if isinstance(inner, dict):
        chunks = inner.get("chunks")
        if isinstance(chunks, list):
            return [c for c in chunks if isinstance(c, dict)], "chunks"

    records = data.get("records")
    if isinstance(records, list):
        return [r for r in records if isinstance(r, dict)], "records"

    return [], ""


def _score_of(raw: dict[str, Any]) -> float:
    for key in ("similarity", "score"):
        val = raw.get(key)
        if val is not None:
            try:
                return float(val)
            except (TypeError, ValueError):
                pass
    return 0.0


def _normalize_item(
    raw: dict[str, Any],
    index: int,
    image_base: str,
    fmt: str,
) -> dict[str, Any]:
    metadata = raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {}

    content = _clean_text(_html_to_text(str(raw.get("content") or "")))
    title = (
        str(raw.get("document_keyword") or raw.get("title") or metadata.get("title") or f"片段{index}")
    )
    doc_id = str(raw.get("document_id") or metadata.get("doc_id") or "")
    doc_type = str(raw.get("doc_type_kwd") or "")
    image_id = str(raw.get("image_id") or "")
    score = _score_of(raw)
    image_url = _image_url(image_base, image_id)

    parts: list[str] = []
    if image_url:
        alt = title if doc_type == "image" else f"{title} 原文区域"
        parts.append(f"![{alt}]({image_url})")
    if content:
        parts.append(content)

    display = "\n\n".join(parts) if parts else "（无正文）"

    item: dict[str, Any] = {
        "index": index,
        "title": title,
        "content": content,
        "display": display,
        "doc_type": doc_type,
    }
    if doc_id:
        item["doc_id"] = doc_id
    if score:
        item["score"] = round(score, 4)
    if image_id:
        item["image_id"] = image_id
        item["image_url"] = image_url
    if fmt:
        item["source_format"] = fmt
    return item


def _dedupe_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """按正文去重，保留相关度最高的一条。"""
    best: dict[str, dict[str, Any]] = {}
    order: list[str] = []

    for item in items:
        key = item.get("content") or item.get("display") or str(item.get("index"))
        if key not in best:
            order.append(key)
            best[key] = item
            continue
        prev_score = float(best[key].get("score") or 0)
        cur_score = float(item.get("score") or 0)
        if cur_score > prev_score:
            best[key] = item

    deduped = [best[k] for k in order]
    for i, item in enumerate(deduped, 1):
        item["index"] = i
    return deduped


def _build_context(records: list[dict[str, Any]]) -> str:
    if not records:
        return ""

    blocks: list[str] = []
    for rec in records:
        header = f"【片段 {rec['index']}】"
        if rec.get("title"):
            header += f" 来源：{rec['title']}"
        if rec.get("doc_type"):
            header += f"  类型：{rec['doc_type']}"
        if rec.get("score") is not None:
            header += f"  相关度：{rec['score']}"
        if rec.get("doc_id"):
            header += f"  doc_id={rec['doc_id']}"

        body = rec.get("display") or rec.get("content") or "（无正文）"
        blocks.append(f"{header}\n{body}")

    return "\n\n---\n\n".join(blocks)


def _build_images_markdown(records: list[dict[str, Any]], max_images: int = 5) -> str:
    """仅输出 Markdown 图片行，供 Answer 直接渲染（勿传裸 URL）。"""
    lines: list[str] = []
    seen: set[str] = set()
    for rec in records:
        url = rec.get("image_url") or ""
        if not url or url in seen:
            continue
        seen.add(url)
        title = str(rec.get("title") or f"片段{rec.get('index', '')}")
        lines.append(f"![{title}]({url})")
        if len(lines) >= max_images:
            break
    return "\n\n".join(lines)


def main(
    body: Any = None,
    status_code: int | str = 200,
    image_base_url: str = DEFAULT_IMAGE_BASE,
    arg1: Any = None,
    **kwargs: Any,
) -> dict[str, str]:
    if body is None:
        body = arg1 or kwargs.get("body")
    if not image_base_url:
        image_base_url = kwargs.get("image_base_url") or DEFAULT_IMAGE_BASE

    try:
        http_code = int(status_code) if status_code not in (None, "") else 200
    except (TypeError, ValueError):
        http_code = 200

    if http_code >= 400:
        return _fail(f"检索失败 HTTP {http_code}")

    try:
        data = _parse_body(body)
    except json.JSONDecodeError:
        return _fail("响应体不是合法 JSON")

    api_code = data.get("code")
    if api_code is not None and int(api_code) != 0:
        return _fail(f"检索 API 返回错误 code={api_code}")

    raw_items, fmt = _extract_raw_items(data)
    if not raw_items:
        return _fail("未检索到相关片段")

    normalized = [
        _normalize_item(raw, i + 1, image_base_url, fmt) for i, raw in enumerate(raw_items)
    ]
    normalized = _dedupe_items(normalized)
    context_text = _build_context(normalized)
    images_markdown = _build_images_markdown(normalized)
    image_count = sum(1 for r in normalized if r.get("image_url"))

    slim = []
    for rec in normalized:
        slim.append(
            {
                k: rec[k]
                for k in ("index", "title", "content", "display", "doc_type", "doc_id", "score", "image_id", "image_url")
                if k in rec
            }
        )

    return {
        "ok": "true",
        "message": "",
        "context_text": context_text,
        "images_markdown": images_markdown,
        "records_json": json.dumps(slim, ensure_ascii=False),
        "record_count": str(len(normalized)),
        "image_count": str(image_count),
    }
