"""
领料 Agent 前 · 判断本轮是否需 Fast HTTP 查库存。

输入：
  query              ← sys.query
  reason             ← 领料路由 Code 的 reason（可选）
  pick_waiting       ← conversation.requisition_pick_waiting（可选）
  pick_cache_json    ← conversation.requisition_pick_cache_json（可选）

输出（If-Else equals）：
  need_fast_inventory: "true" | "false"
  use_pick_cache: "true" | "false"   # false 时直进 Agent（确认提交等）
  skip_reason: string
"""

import json
import re

_SKIP_REASONS = frozenset(
    {
        "gon_number",
        "requisition_status_keyword",
        "query_status_with_biz_no",
        "draft_number",
    }
)

_FLOW_SKIP = (
    "确认提交",
    "提交审批",
    "取消",
    "算了",
)


def _is_modify_qty(text: str) -> bool:
    return "修改数量" in text or bool(re.search(r"改(?:成|为)\s*[\d.]+\s*(?:KG|kg|箱|张|吨|个|卷|桶|包)?", text))


_CODE_IN_QUERY = re.compile(r"\b([A-Z]{2,}-[A-Z0-9-]+)\b", re.I)


def _code_in_pick_cache(code: str, pick_cache_json: str) -> bool:
    if not code or not (pick_cache_json or "").strip():
        return False
    try:
        rows = json.loads(pick_cache_json)
    except json.JSONDecodeError:
        return False
    if not isinstance(rows, list):
        return False
    upper = code.upper()
    return any(str(r.get("code", "")).strip().upper() == upper for r in rows if isinstance(r, dict))


def _out(need_fast: bool, use_cache: bool, reason: str) -> dict:
    return {
        "need_fast_inventory": "true" if need_fast else "false",
        "use_pick_cache": "true" if use_cache else "false",
        "skip_reason": reason,
    }


def main(
    query: str,
    reason: str = "",
    pick_waiting: str = "",
    pick_cache_json: str = "",
) -> dict:
    t = (query or "").strip()
    r = (reason or "").strip()

    if not t:
        return _out(False, False, "empty_query")

    if r in _SKIP_REASONS:
        return _out(False, False, r)

    if t in _FLOW_SKIP or any(k in t for k in ("确认提交", "提交审批")):
        return _out(False, False, "confirm_or_cancel")

    if _is_modify_qty(t):
        return _out(False, False, "modify_qty_only")

    if re.search(r"GON\d+", t, re.I):
        return _out(False, False, "gon_in_query")

    # 选型后续：料号在上一轮 list 中 → 走缓存，不 HTTP
    if (pick_waiting or "").strip().lower() == "true":
        m = _CODE_IN_QUERY.search(t)
        if m and _code_in_pick_cache(m.group(1), pick_cache_json):
            return _out(False, True, "pick_cache_hit")

    return _out(True, False, "")
