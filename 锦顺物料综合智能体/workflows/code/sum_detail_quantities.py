"""
Dify 代码节点：对明细 JSON 数组中的数量字段求合计。

适用场景：上游 SQL/Tool 返回多行明细（按物料分列），用户问「加总/总量/合计」时，
在渲染表格前或后对本节点传入的 JSON 做 SUM。

输入变量（任选其一绑定上游）：
  - arg1 / output / data：JSON 数组字符串，或 {"output": "[...]"} 包裹

可选输入：
  - quantity_field：指定加总列名（如「总用量」「领用数量」）；留空则自动识别

输出变量（与 return 键名一致）：
  - total_text   — 可读合计文案（供 Answer / LLM 引用）
  - totals_json  — 结构化合计 JSON 字符串
  - row_count    — 明细行数
  - quantity_field — 实际使用的数量列名（多列时为逗号分隔）
"""

from __future__ import annotations

import json
import re
from decimal import Decimal, InvalidOperation
from typing import Any


# 优先匹配的列名（完全相等时优先）
PREFERRED_QTY_KEYS = (
    "总用量",
    "领用数量",
    "入库数量",
    "使用数量",
    "出库数量",
    "库存数量",
    "采购入库数量",
    "领用数量合计",
    "入库数量合计",
    "期间领用数量合计",
    "每月使用量",
    "月均使用量",
    "数量",
)

QTY_KEY_PATTERN = re.compile(r"(数量|用量|合计)$")


def _unwrap_fence(text: str) -> str:
    text = text.strip()
    if not text.startswith("```"):
        return text
    lines = text.split("\n")
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip().replace(",", "")
    if not s:
        return None
    try:
        return float(Decimal(s))
    except (InvalidOperation, ValueError):
        return None


def _parse_rows(raw: Any) -> list[dict[str, Any]]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return [r for r in raw if isinstance(r, dict)]
    if isinstance(raw, dict):
        for key in ("output", "data", "records", "rows", "list", "items", "result"):
            inner = raw.get(key)
            if inner is not None:
                return _parse_rows(inner)
        return []
    text = _unwrap_fence(str(raw))
    if not text:
        return []
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return []
    if isinstance(parsed, list):
        return [r for r in parsed if isinstance(r, dict)]
    if isinstance(parsed, dict):
        return _parse_rows(parsed)
    return []


def _detect_qty_keys(rows: list[dict[str, Any]], override: str | None) -> list[str]:
    if override:
        key = override.strip()
        return [key] if key else []

    if not rows:
        return []

    sample = rows[0]
    candidates: list[str] = []

    for key in PREFERRED_QTY_KEYS:
        if key in sample and _to_float(sample.get(key)) is not None:
            candidates.append(key)

    for key in sample:
        if key in candidates:
            continue
        if key in ("单位", "原材料代码", "原材料描述", "物料编号", "物料名称", "材料名称"):
            continue
        if QTY_KEY_PATTERN.search(key) and _to_float(sample.get(key)) is not None:
            candidates.append(key)

    # 去重保序
    seen: set[str] = set()
    ordered: list[str] = []
    for k in candidates:
        if k not in seen:
            seen.add(k)
            ordered.append(k)
    return ordered


def _format_num(n: float) -> str:
    if abs(n - round(n)) < 1e-9:
        return f"{int(round(n)):,}"
    return f"{n:,.2f}".rstrip("0").rstrip(".")


def _sum_by_unit(rows: list[dict[str, Any]], qty_key: str) -> dict[str, float]:
    buckets: dict[str, float] = {}
    for row in rows:
        val = _to_float(row.get(qty_key))
        if val is None:
            continue
        unit = str(row.get("单位") or "").strip() or "（未标注单位）"
        buckets[unit] = buckets.get(unit, 0.0) + val
    return buckets


def _build_total_text(
    qty_keys: list[str],
    all_totals: dict[str, dict[str, float]],
    row_count: int,
) -> str:
    if row_count == 0:
        return "明细为空，无法加总。"

    parts: list[str] = [f"共 {row_count} 条明细，加总结果如下："]
    for qty_key in qty_keys:
        by_unit = all_totals.get(qty_key, {})
        if not by_unit:
            parts.append(f"- **{qty_key}**：无有效数值")
            continue
        if len(by_unit) == 1:
            unit, total = next(iter(by_unit.items()))
            parts.append(f"- **{qty_key}合计**：{_format_num(total)} {unit}")
        else:
            parts.append(f"- **{qty_key}**（按单位分别合计，不可跨单位直接相加）：")
            for unit, total in sorted(by_unit.items(), key=lambda x: -abs(x[1])):
                parts.append(f"  - {_format_num(total)} {unit}")
    return "\n".join(parts)


def main(
    arg1: Any = None,
    output: Any = None,
    data: Any = None,
    quantity_field: str = "",
    **kwargs: Any,
) -> dict[str, str]:
    raw = arg1 if arg1 is not None else output
    if raw is None:
        raw = data
    if raw is None:
        raw = kwargs.get("arg1") or kwargs.get("output") or kwargs.get("data")

    field_override = (quantity_field or kwargs.get("quantity_field") or "").strip()

    rows = _parse_rows(raw)
    qty_keys = _detect_qty_keys(rows, field_override or None)

    if not qty_keys and rows:
        return {
            "total_text": "未识别到可加总的数量列（列名需含「数量/用量/合计」，或传入 quantity_field）。",
            "totals_json": "[]",
            "row_count": str(len(rows)),
            "quantity_field": "",
        }

    all_totals: dict[str, dict[str, float]] = {}
    totals_list: list[dict[str, Any]] = []

    for qty_key in qty_keys:
        by_unit = _sum_by_unit(rows, qty_key)
        all_totals[qty_key] = by_unit
        for unit, total in by_unit.items():
            totals_list.append(
                {
                    "数量字段": qty_key,
                    "合计": round(total, 4),
                    "单位": unit,
                }
            )

    return {
        "total_text": _build_total_text(qty_keys, all_totals, len(rows)),
        "totals_json": json.dumps(totals_list, ensure_ascii=False),
        "row_count": str(len(rows)),
        "quantity_field": ",".join(qty_keys),
    }
