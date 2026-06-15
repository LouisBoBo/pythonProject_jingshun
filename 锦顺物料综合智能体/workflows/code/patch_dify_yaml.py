#!/usr/bin/env python3
"""One-shot patcher: restore 客户数据分析助手-正式库.yml from backup and apply workflow fixes."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BACKUP = Path("/Users/hebo/Desktop/中软项目/锦顺项目/客户数据分析助手-正式库.yml")
YML = ROOT / "客户数据分析助手-正式库.yml"
VALIDATE_CODE = ROOT / "锦顺物料综合智能体/workflows/code/validate_and_fix_sql.py"
PREVIEW_CODE = ROOT / "锦顺物料综合智能体/workflows/code/json_to_markdown_table.py"

NODE_ID = "1776761234567"
USER_QUERY_NODE = "1776736092059"
EXTRACT_NODE = "1773990480876"


def _require(content: str, needle: str, label: str) -> None:
    if needle not in content:
        raise SystemExit(f"PATCH FAIL: {label} not found")


def patch_json_preview(content: str) -> str:
    preview_code_yaml = json.dumps(PREVIEW_CODE.read_text(encoding="utf-8"))[1:-1]
    anchor = "      id: '1776752569164'"
    pos = content.find(anchor)
    if pos == -1:
        raise SystemExit("1776752569164 node not found")

    # Walk back to node start
    node_start = content.rfind("    - data:", 0, pos)
    preview_node = f"""    - data:
        code: "{preview_code_yaml}"
        code_language: python3
        outputs:
          md_text:
            children: null
            type: string
          row_count:
            children: null
            type: string
        selected: false
        title: json转markdown预览
        type: code
        variables:
        - value_selector:
          - '1776749793446'
          - data_first_50
          value_type: string
          variable: arg1
      height: 52
      id: '1776752569165'
      position:
        x: 5792
        y: -220
      positionAbsolute:
        x: 5792
        y: -220
      selected: false
      sourcePosition: right
      targetPosition: left
      type: custom
      width: 242
"""
    return content[:node_start] + preview_node + content[node_start:]


def patch_edges_and_answer(content: str) -> str:
    old_edge = """      id: 1776750177124-true-1776758746308-target
      source: '1776750177124'
      sourceHandle: 'true'
      target: '1776758746308'
      targetHandle: target
      type: custom
      zIndex: 0
    - data:
        isInIteration: false
        isInLoop: false
        sourceType: llm
        targetType: code
      id: 1776758746308-source-1776752569164-target
      source: '1776758746308'
      sourceHandle: source
      target: '1776752569164'"""

    new_edge = """      id: 1776750177124-true-1776752569165-target
      source: '1776750177124'
      sourceHandle: 'true'
      target: '1776752569165'
      targetHandle: target
      type: custom
      zIndex: 0
    - data:
        isInIteration: false
        isInLoop: false
        sourceType: if-else
        targetType: code
      id: 1776750177124-true-1776752569164-target
      source: '1776750177124'
      sourceHandle: 'true'
      target: '1776752569164'"""

    _require(content, old_edge, "old >50 edge block")
    content = content.replace(old_edge, new_edge, 1)

    old_answer = """        answer: '{{#1776758746308.text#}}


          📥【温馨提示】：当前只显示前50条数据点击下载查看更多


          {{#1778291346533.card_html#}}

          '"""
    new_answer = """        answer: '{{#1776752569165.md_text#}}


          📥【温馨提示】：查询共 {{#1776752569164.row_count#}} 条，当前仅展示前 50 条，点击下载查看更多


          {{#1778291346533.card_html#}}

          '"""
    _require(content, old_answer, "direct reply 4 answer")
    return content.replace(old_answer, new_answer, 1)


def patch_validate_node(content: str) -> str:
    old_edge = """    - data:
        isInLoop: false
        sourceType: code
        targetType: tool
      id: 1773990480876-source-1772707916454-target
      source: '1773990480876'
      sourceHandle: source
      target: '1772707916454'
      targetHandle: target
      type: custom
      zIndex: 0"""

    new_edges = """    - data:
        isInLoop: false
        sourceType: code
        targetType: code
      id: 1773990480876-source-1776761234567-target
      source: '1773990480876'
      sourceHandle: source
      target: '1776761234567'
      targetHandle: target
      type: custom
      zIndex: 0
    - data:
        isInLoop: false
        sourceType: code
        targetType: tool
      id: 1776761234567-source-1772707916454-target
      source: '1776761234567'
      sourceHandle: source
      target: '1772707916454'
      targetHandle: target
      type: custom
      zIndex: 0"""

    _require(content, old_edge, "extract->sql edge")
    content = content.replace(old_edge, new_edges, 1)

    content = content.replace(
        "value: '{{#1773990480876.result#}}'",
        "value: '{{#1776761234567.result#}}'",
        1,
    )

    code_yaml = json.dumps(VALIDATE_CODE.read_text(encoding="utf-8"))[1:-1]
    new_node = f"""    - data:
        code: "{code_yaml}"
        code_language: python3
        outputs:
          fix_count:
            children: null
            type: string
          fix_log:
            children: null
            type: string
          result:
            children: null
            type: string
        selected: false
        title: 校验修复SQL
        type: code
        variables:
        - value_selector:
          - '{EXTRACT_NODE}'
          - result
          value_type: string
          variable: arg1
        - value_selector:
          - '{USER_QUERY_NODE}'
          - text
          value_type: string
          variable: user_query
      height: 52
      id: '{NODE_ID}'
      position:
        x: 2965
        y: 305
      positionAbsolute:
        x: 2965
        y: 305
      selected: false
      sourcePosition: right
      targetPosition: left
      type: custom
      width: 242
"""

    marker = "      id: '1773990480876'\n      position:"
    insert_pos = content.find(marker)
    if insert_pos == -1:
        raise SystemExit("extract node marker not found")
    end_marker = "      width: 242\n    - data:"
    idx = content.find(end_marker, insert_pos)
    if idx == -1:
        raise SystemExit("extract node end marker not found")
    insert_at = idx + len("      width: 242\n")
    return content[:insert_at] + new_node + content[insert_at:]


def patch_extract_sql_cte(content: str) -> str:
    """Add CTE-aware extraction to 提取SQL语句 node (optional)."""
    import re

    if "CTE 须整段保留" in content or "cte_head = re.search" in content:
        print("extract SQL already has CTE patch, skip")
        return content

    pattern = re.compile(
        r'(if sql_blocks:\\n\s+return \\"\\\\n\\\\n\\"\.join\(sql_blocks\))\\n\\n\s+#\\',
        re.DOTALL,
    )
    if not pattern.search(content):
        print("WARN: extract SQL CTE patch skipped (anchor not found)")
        return content

    insert = (
        r'if sql_blocks:\\n        text = \\"\\\\n\\\\n\\"\.join\(sql_blocks\)\\n\\n    likely_sql_re = re.compile(\\n'
        r'        r\\"\\\\b(SELECT|INSERT|UPDATE|DELETE|FROM|WHERE|JOIN|GROUP\\\\s+BY|ORDER\\\\s+BY|VALUES|WITH)\\\\b\\",\\n'
        r'        re.IGNORECASE,\\n    )\\n\\n    cte_head = re.search(r\\"\\\\bWITH\\\\s+\\\\w+\\\\s+AS\\\\s*\\\\(\\", text, re.IGNORECASE)\\n'
        r'    if cte_head:\\n        rest = text[cte_head.start():].strip()\\n        semi = rest.find(\\";\\")\\n'
        r'        if semi != -1:\\n            rest = rest[: semi + 1].strip()\\n        if likely_sql_re.search(rest):\\n'
        r'            return rest\\n\\n    #\\'
    )
    new_content, n = pattern.subn(insert, content, count=1)
    print(f"extract SQL CTE patch applied: {n}")
    return new_content


def main() -> None:
    if not BACKUP.is_file():
        raise SystemExit(f"Backup missing: {BACKUP}")

    shutil.copy2(BACKUP, YML)
    content = YML.read_text(encoding="utf-8")

    _require(content, "app:", "yaml header")
    _require(content, "  edges:", "edges section")

    content = patch_json_preview(content)
    content = patch_edges_and_answer(content)
    content = patch_validate_node(content)
    content = patch_extract_sql_cte(content)

    _require(content, "1776761234567", "validate node id")
    _require(content, "1776752569165", "json preview node id")
    _require(content, "{{#1776761234567.result#}}", "sql tool wired to validate")
    _require(content, "WITH monthly AS", "validate code cte fix")

    YML.write_text(content, encoding="utf-8")
    print(f"Patched OK: {len(content.splitlines())} lines -> {YML}")


if __name__ == "__main__":
    main()
