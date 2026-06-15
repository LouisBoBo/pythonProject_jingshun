#!/usr/bin/env python3
"""自测：领料 DATA Fast 读链 Code 节点。"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def _load(name: str):
    path = ROOT / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    return mod


build_q = _load("build_requisition_inventory_query")
extract = _load("extract_requisition_material_from_detail")
need_inv = _load("detect_requisition_need_inventory")
resolve_cache = _load("resolve_requisition_from_pick_cache")

SAMPLE_DETAIL = """| material_code | 物料名称 | 当前可用库存数量 | 单位 |
| --- | --- | --- | --- |
| JS-NZ-001 | 液态感光阻焊油墨 | 0.0 | KG |
| JS-NZ-006 | 液态感光阻焊油墨 | 200.0 | KG |
| JS-NZ-045 | 液态感光阻焊油墨 | 2420.0 | KG |
| JS-NZ-046 | 液态感光阻焊油墨 | 1720.0 | KG |
"""


def test_build_query_limits_rows():
    out = build_q.main("帮我领 10KG 阻焊油墨")
    assert "最多10行" in out["inventory_query"]
    assert "可用库存>0" in out["inventory_query"]


def test_multi_pick_required():
    out = extract.main(SAMPLE_DETAIL, "帮我领 10KG 阻焊油墨")
    assert out["pick_required"] == "true"
    assert out["extract_ok"] == "false"
    assert "JS-NZ-045" in out["pick_list"]
    cache = json.loads(out["pick_cache_json"])
    codes = {r["code"] for r in cache}
    assert "JS-NZ-045" in codes
    assert "JS-NZ-006" in codes


def test_skip_fast_when_code_in_pick_cache():
    cache = json.dumps(
        [
            {"code": "JS-NZ-117", "name": "液态感光阻焊油墨", "qty": 1460, "unit": "KG"},
            {"code": "JS-NZ-006", "name": "x", "qty": 200, "unit": "KG"},
        ]
    )
    out = need_inv.main("JS-NZ-117", pick_waiting="true", pick_cache_json=cache)
    assert out["need_fast_inventory"] == "false"
    assert out["use_pick_cache"] == "true"
    assert out["skip_reason"] == "pick_cache_hit"


def test_still_fast_when_code_not_in_cache():
    cache = json.dumps([{"code": "JS-NZ-006", "name": "x", "qty": 200, "unit": "KG"}])
    out = need_inv.main("JS-NZ-117", pick_waiting="true", pick_cache_json=cache)
    assert out["need_fast_inventory"] == "true"
    assert out["use_pick_cache"] == "false"


def test_resolve_from_pick_cache():
    cache = json.dumps(
        [{"code": "JS-NZ-117", "name": "液态感光阻焊油墨", "qty": 1460, "unit": "KG"}]
    )
    out = resolve_cache.main(
        "JS-NZ-117",
        pick_cache_json=cache,
        pending_intent_query="帮我领 10KG 阻焊油墨",
    )
    assert out["extract_ok"] == "true"
    assert out["material_code"] == "JS-NZ-117"
    assert out["available_qty"] == "1460"


def test_explicit_code_picks_one():
    out = extract.main(SAMPLE_DETAIL, "领 JS-NZ-006 10KG")
    assert out["extract_ok"] == "true"
    assert out["material_code"] == "JS-NZ-006"
    assert out["available_qty"] == "200"


def test_pick_continuation_uses_pending_intent():
    """选型后只发料号，数量从 pending_intent_query 继承。"""
    detail = """| material_code | 物料名称 | 当前可用库存数量 | 单位 |
| --- | --- | --- | --- |
| JS-NZ-006 | 液态感光阻焊油墨 | 200.0 | KG |
"""
    out = extract.main(
        detail,
        "JS-NZ-006",
        pending_intent_query="帮我领 10KG 阻焊油墨",
    )
    assert out["extract_ok"] == "true"
    assert out["material_code"] == "JS-NZ-006"


def test_single_in_stock_auto():
    detail = """| material_code | 物料名称 | 当前可用库存数量 | 单位 |
| --- | --- | --- | --- |
| JS-NZ-001 | x | 0.0 | KG |
| JS-NZ-006 | y | 200.0 | KG |
"""
    out = extract.main(detail, "帮我领 10KG")
    assert out["extract_ok"] == "true"
    assert out["material_code"] == "JS-NZ-006"


def main() -> int:
    for fn in (
        test_build_query_limits_rows,
        test_multi_pick_required,
        test_skip_fast_when_code_in_pick_cache,
        test_still_fast_when_code_not_in_cache,
        test_resolve_from_pick_cache,
        test_explicit_code_picks_one,
        test_pick_continuation_uses_pending_intent,
        test_single_in_stock_auto,
    ):
        fn()
        print(f"OK {fn.__name__}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
