"""
Dify 代码节点：校验并修复 LLM 生成的 T-SQL（锦顺物料查询场景）。

输入变量（任一即可）：
  - arg1 / sql / input_text：原始 SQL 或含 ```sql 代码块的文本

可选：
  - user_query：用户原问句，用于上下文修复（月均+明细、材料型号等）

输出变量：
  - result    — 修复后的可执行 SQL
  - fix_log   — 修复说明（多行文本，无修复则为空）
  - fix_count — 修复项数量（字符串）
"""

from __future__ import annotations

import re
from typing import Any


# ---------------------------------------------------------------------------
# SQL 提取（与「提取SQL语句」节点逻辑一致，兼容直接传入纯 SQL）
# ---------------------------------------------------------------------------

def _coerce_text(raw: Any) -> str:
    if raw is None:
        return ""
    if isinstance(raw, str):
        return raw
    if isinstance(raw, dict):
        for key in ("sql", "result", "input_text", "text", "content", "arg1", "value"):
            val = raw.get(key)
            if isinstance(val, str) and val.strip():
                return val
    return str(raw)


def extract_executable_sql(input_text: str) -> str:
    if not input_text:
        return ""
    text = (
        input_text.replace("\\r\\n", "\n")
        .replace("\\n", "\n")
        .replace("\\t", "\t")
        .strip()
    )
    fence_re = re.compile(r"```(?:sql)?\s*([\s\S]*?)```", re.IGNORECASE)
    blocks = [m.group(1).strip() for m in fence_re.finditer(text)]
    blocks = [b for b in blocks if b]
    if blocks:
        text = "\n\n".join(blocks)

    likely_sql = re.compile(
        r"\b(SELECT|INSERT|UPDATE|DELETE|FROM|WHERE|JOIN|GROUP\s+BY|ORDER\s+BY|VALUES|WITH)\b",
        re.IGNORECASE,
    )

    # CTE 须整段保留：提取器若从内部 SELECT 切块会丢掉「WITH monthly AS (」→ 102
    cte_head = re.search(r"\bWITH\s+\w+\s+AS\s*\(", text, re.IGNORECASE)
    if cte_head:
        rest = text[cte_head.start() :].strip()
        semi = rest.find(";")
        if semi != -1:
            rest = rest[: semi + 1].strip()
        if likely_sql.search(rest):
            return rest

    start_re = re.compile(
        r"\b(SELECT|INSERT|UPDATE|DELETE|WITH|CREATE|ALTER|DROP|TRUNCATE|MERGE)\b",
        re.IGNORECASE,
    )
    starts = [m.start() for m in start_re.finditer(text)]
    if not starts:
        return text

    parts: list[str] = []
    for i, start in enumerate(starts):
        end = starts[i + 1] if i + 1 < len(starts) else len(text)
        chunk = text[start:end].strip()
        semi = chunk.rfind(";")
        if semi != -1:
            chunk = chunk[: semi + 1].strip()
        if chunk and likely_sql.search(chunk):
            parts.append(chunk)
    return "\n\n".join(parts) if parts else text


# ---------------------------------------------------------------------------
# 修复规则
# ---------------------------------------------------------------------------

# 企业内部料号前缀 — 应保留 INV_PART_NUMBER 等值匹配
INTERNAL_CODE_PREFIXES = (
    "JS-",
    "D-JS-",
    "W25-",
    "JS-NZ-",
    "JS-NX-",
    "JS-V",
    "JS-H",
    "JS-O-",
)

PART_GRADE_RE = re.compile(
    r"\bm\.INV_PART_NUMBER\s*=\s*N'([^']+)'",
    re.IGNORECASE,
)


AS_YEAR_RE = re.compile(r"\bAS\s+(20\d{2}[^\[\]\s,;]+)", re.IGNORECASE)

BLACKLIST_SUBSTRINGS = (
    "d22.IsHalfStock",
    "d22.IS_PROD_STORE",
    "Data0022.IsHalfStock",
    "Data0022.IS_PROD_STORE",
    "m.LOCATION_PTR",
    "Data0017.LOCATION_PTR",
    "m.DEPT_PTR",
    "Data0017.DEPT_PTR",
    "d071.POPTR",
    "po.SUPPLIER_PTR",
)


def _is_grade_part_number(code: str) -> bool:
    """KB-6160 / TG-140 等行业牌号 → 描述 LIKE；JS-CCL-* 等企业料号 → 保留等值。"""
    c = code.strip().upper()
    if not c:
        return False
    for prefix in INTERNAL_CODE_PREFIXES:
        if c.startswith(prefix.upper()):
            return False
    if re.match(r"^[A-Z]{1,4}-\d{3,5}[A-Z0-9]{0,8}$", c):
        return True
    return False


def _grade_like_clause(code: str) -> str:
    esc = code.replace("'", "''")
    return (
        f"(m.INV_PART_DESCRIPTION LIKE N'%|{esc}%' "
        f"OR m.INV_PART_DESCRIPTION LIKE N'%{esc}%' "
        f"OR m.INV_DESCRIPTION LIKE N'%|{esc}%' "
        f"OR m.INV_DESCRIPTION LIKE N'%{esc}%')"
    )


def _fix_part_number_grade_match(sql: str, log: list[str]) -> str:
    def repl(m: re.Match[str]) -> str:
        code = m.group(1)
        if _is_grade_part_number(code):
            log.append(f"牌号 {code}: INV_PART_NUMBER 等值 → 描述列 LIKE")
            return _grade_like_clause(code)
        return m.group(0)

    return PART_GRADE_RE.sub(repl, sql)


def _fix_extra_paren_114(sql: str, log: list[str]) -> str:
    if "|'))))" in sql or "|')))))" in sql:
        new = re.sub(r"\|'\)\)\)\)+", "|')))", sql)
        if new != sql:
            log.append("1.14 三联 OR: 多余右括号 |')))) → |')))")
        return new
    return sql


def _fix_blacklist_columns(sql: str, log: list[str]) -> str:
    out = sql
    replacements = {
        "d22.IsHalfStock": "d16.IsHalfStock",
        "d22.IS_PROD_STORE": "d16.IS_PROD_STORE",
        "Data0022.IsHalfStock": "d16.IsHalfStock",
        "Data0022.IS_PROD_STORE": "d16.IS_PROD_STORE",
        "d071.POPTR": "d071.PO_PTR",
        "po.SUPPLIER_PTR": "po.SUPPLIER_POINTER",
    }
    for bad, good in replacements.items():
        if bad in out:
            out = out.replace(bad, good)
            log.append(f"非法列名 {bad} → {good}")
    for bad in ("m.LOCATION_PTR", "Data0017.LOCATION_PTR", "m.DEPT_PTR", "Data0017.DEPT_PTR"):
        if bad in out:
            log.append(f"警告: 仍含非法列 {bad}，请人工检查 SQL")
    return out


def _has_join_table(sql: str, table: str) -> bool:
    return bool(re.search(rf"\bJOIN\s+{re.escape(table)}\b", sql, re.IGNORECASE))


def _insert_after_from_m(sql: str, snippet: str) -> str:
    m = re.search(r"(FROM\s+Data0017\s+\w+\s*\n)", sql, re.IGNORECASE)
    if not m:
        m = re.search(r"(FROM\s+Data0017\s+\w+)", sql, re.IGNORECASE)
    if not m:
        return sql
    pos = m.end()
    return sql[:pos] + snippet + sql[pos:]


def _fix_missing_joins(sql: str, log: list[str]) -> str:
    out = sql
    if re.search(r"\bu\.\w+", out, re.IGNORECASE) and not _has_join_table(out, "Data0002"):
        snippet = "LEFT JOIN Data0002 u ON m.STOCK_UNIT_PTR = u.RKEY\n"
        out = _insert_after_from_m(out, snippet)
        log.append("补 JOIN Data0002 u（u. 列悬空）")
    if re.search(r"\bcat\.\w+", out, re.IGNORECASE) and not _has_join_table(out, "Data0496"):
        snippet = "LEFT JOIN Data0496 cat ON m.GROUP_PTR = cat.RKEY\n"
        out = _insert_after_from_m(out, snippet)
        log.append("补 JOIN Data0496 cat（cat. 列悬空）")
    return out


def _fix_tdate_in_where_for_left_join(sql: str, log: list[str]) -> str:
    """LEFT JOIN Data0207 时，把 WHERE 中的 d207.TDATE 挪到 JOIN ON。"""
    if not re.search(r"LEFT\s+JOIN\s+Data0207", sql, re.IGNORECASE):
        return sql

    alias_m = re.search(r"LEFT\s+JOIN\s+Data0207\s+(\w+)", sql, re.IGNORECASE)
    if not alias_m:
        return sql
    alias = alias_m.group(1)

    date_pat = re.compile(
        rf"\s+AND\s+{re.escape(alias)}\.TDATE\s*>=\s*'([^']+)'\s+"
        rf"AND\s+{re.escape(alias)}\.TDATE\s*<\s*'([^']+)'",
        re.IGNORECASE,
    )
    wm = date_pat.search(sql)
    if not wm:
        return sql

    lo, hi = wm.group(1), wm.group(2)
    date_on = f" AND {alias}.TDATE >= '{lo}' AND {alias}.TDATE < '{hi}'"

    lj = re.search(
        rf"(LEFT\s+JOIN\s+Data0207\s+{re.escape(alias)}\s+ON\s+)(.+?)(?=\s*(?:LEFT|INNER|JOIN|WHERE|GROUP|ORDER|$))",
        sql,
        re.IGNORECASE | re.DOTALL,
    )
    if not lj:
        return sql
    on_prefix, on_body = lj.group(1), lj.group(2).rstrip()
    if re.search(rf"{re.escape(alias)}\.TDATE\s*>=", on_body, re.IGNORECASE):
        return sql

    new_sql = sql[: wm.start()] + sql[wm.end() :]
    replacement = f"{on_prefix}{on_body}{date_on}"
    new_sql = new_sql[: lj.start()] + replacement + new_sql[lj.end() :]
    log.append(f"WHERE {alias}.TDATE 区间 → 移入 LEFT JOIN ON")
    return new_sql


def _fix_inner_join_d207_for_material_sum(sql: str, log: list[str]) -> str:
    """Data0017 领用汇总且无按月分组时，INNER JOIN d207 易致「查无数据」→ LEFT JOIN。"""
    if not re.search(r"FROM\s+Data0017\s+\w+", sql, re.IGNORECASE):
        return sql
    if not re.search(r"INNER\s+JOIN\s+Data0207", sql, re.IGNORECASE):
        return sql
    if re.search(r"GROUP\s+BY\s+FORMAT\s*\(\s*\w+\.TDATE", sql, re.IGNORECASE):
        return sql
    if re.search(r"\bWITH\s+monthly\b", sql, re.IGNORECASE):
        return sql
    if re.search(r"SUM\s*\(\s*ISNULL\s*\(\s*\w+\.QUANTITY", sql, re.IGNORECASE):
        new = re.sub(r"\bINNER\s+JOIN\s+Data0207\b", "LEFT JOIN Data0207", sql, count=1, flags=re.IGNORECASE)
        if new != sql:
            log.append("INNER JOIN Data0207 → LEFT JOIN（防无领用查无数据）")
            return new
    return sql


def _fix_as_year_brackets(sql: str, log: list[str]) -> str:
    def repl(m: re.Match[str]) -> str:
        alias = m.group(1).strip()
        if alias.startswith("["):
            return m.group(0)
        log.append(f"列别名 AS {alias} → AS [{alias}]（防 102）")
        return f"AS [{alias}]"

    return AS_YEAR_RE.sub(repl, sql)


def _fix_broken_cte_monthly_summary(sql: str, log: list[str]) -> str:
    """
    修复被截断的 monthly/summary CTE：
    「SELECT … GROUP BY … ), summary AS ( … ) SELECT … FROM monthly」
    缺少开头的 WITH monthly AS ( → 102 Incorrect syntax near ')'.
    """
    if re.search(r"\bWITH\s+monthly\s+AS\s*\(", sql, re.IGNORECASE):
        return sql
    if not re.search(r"\),\s*summary\s+AS\s*\(", sql, re.IGNORECASE):
        return sql
    if not re.search(r"\bFROM\s+monthly\b", sql, re.IGNORECASE):
        return sql
    if not re.match(r"\s*SELECT\b", sql, re.IGNORECASE):
        return sql

    log.append("补全缺失的 WITH monthly AS (（CTE 头被截断，防 102）")
    return "WITH monthly AS (\n" + sql.lstrip()


def _fix_order_by_top(sql: str, log: list[str]) -> str:
    if re.search(r"ORDER\s+BY\s+.+?\bTOP\s+\(", sql, re.IGNORECASE | re.DOTALL):
        log.append("警告: ORDER BY … TOP 语法非法(156)，需人工调整")
    return sql


def _context_hints(user_query: str) -> dict[str, Any]:
    q = (user_query or "").strip()
    code_m = re.search(r"([A-Z]{1,4}-\d{3,5}[A-Z0-9]{0,8})", q, re.IGNORECASE)
    return {
        "monthly_avg": bool(re.search(r"月均|月平均|平均每月", q)),
        "with_detail": bool(re.search(r"明细|及其明细|各月明细|提供明细", q)),
        "grade_in_query": bool(re.search(r"材料型号|牌号|原材料规格", q)),
        "short_code": code_m.group(1) if code_m else None,
    }


def _fix_short_code_in_query(sql: str, user_query: str, log: list[str]) -> str:
    m = re.search(r"([A-Z]{1,4}-\d{3,5}[A-Z0-9]{0,8})", user_query or "", re.IGNORECASE)
    if not m:
        return sql
    code = m.group(1)
    if not _is_grade_part_number(code):
        return sql
    if _grade_like_clause(code).upper() in sql.upper():
        return sql
    # 仍用 INV_PART_NUMBER 等值
    esc = re.escape(code)
    if re.search(rf"INV_PART_NUMBER\s*=\s*N'{esc}'", sql, re.IGNORECASE):
        clause = _grade_like_clause(code)
        sql = re.sub(rf"\bm\.INV_PART_NUMBER\s*=\s*N'{esc}'", clause, sql, flags=re.IGNORECASE)
        log.append(f"结合问句牌号 {code}: 替换 INV_PART_NUMBER 等值为 LIKE")
    return sql


def _monthly_qty_column(sql: str) -> str:
    """Detect quantity column alias inside monthly CTE / GROUP BY month query."""
    for name in ("每月使用量", "使用数量", "领用数量", "月领用数量"):
        if re.search(rf"\bAS\s+{re.escape(name)}\b", sql, re.IGNORECASE):
            return name
    return "每月使用量"


def _monthly_avg_single_row_sql(alias: str, qty_col: str) -> str:
    return f"""SELECT
    ISNULL(SUM({alias}.{qty_col}) / NULLIF(COUNT(*), 0), 0) AS 月均使用量,
    ISNULL(SUM({alias}.{qty_col}), 0) AS 期间领用数量合计,
    MAX({alias}.单位) AS 单位
FROM monthly {alias}"""


def _fix_monthly_avg_only_single_row(sql: str, user_query: str, log: list[str]) -> str:
    """
    仅问「月均使用量」、未问明细/提供明细时，SQL 必须 1 行均值，禁止逐月多行表。
    """
    hints = _context_hints(user_query)
    if not hints["monthly_avg"] or hints["with_detail"]:
        return sql

    qty_col = _monthly_qty_column(sql)

    # Case 1: CROSS JOIN summary → 单行 summary
    cross = re.search(
        r"FROM\s+monthly\s+\w+\s+CROSS\s+JOIN\s+summary\s+\w+",
        sql,
        re.IGNORECASE,
    )
    if cross and re.search(r"\bsummary\s+AS\s*\(", sql, re.IGNORECASE):
        before = sql[: cross.start()]
        selects = list(re.finditer(r"\bSELECT\b", before, re.IGNORECASE))
        if selects:
            log.append("仅问月均（无明细）：CROSS JOIN 多行 → summary 单行")
            single = """SELECT
    s.月均使用量,
    s.期间领用数量合计,
    (SELECT MAX(mo.单位) FROM monthly mo) AS 单位
FROM summary s"""
            return before[: selects[-1].start()] + single

    # Case 2: WITH monthly + 外层 FROM monthly 逐月输出
    if re.search(r"\bWITH\s+monthly\s+AS\s*\(", sql, re.IGNORECASE):
        from_monthly = re.search(
            r"\)\s*,?\s*SELECT[\s\S]+?\bFROM\s+monthly\s+(\w+)\b",
            sql,
            re.IGNORECASE,
        )
        if not from_monthly:
            from_monthly = re.search(
                r"\)\s*SELECT[\s\S]+?\bFROM\s+monthly\s+(\w+)\b",
                sql,
                re.IGNORECASE,
            )
        if from_monthly and re.search(r"月份", from_monthly.group(0), re.IGNORECASE):
            if not re.search(r"\bCROSS\s+JOIN\s+summary\b", sql, re.IGNORECASE):
                outer_select = re.search(
                    r"\bSELECT\b[\s\S]+$",
                    sql[from_monthly.start() :],
                    re.IGNORECASE,
                )
                if outer_select:
                    alias = from_monthly.group(1)
                    log.append("仅问月均（无明细）：monthly 逐月多行 → 单行聚合")
                    return (
                        sql[: from_monthly.start() + outer_select.start()]
                        + _monthly_avg_single_row_sql(alias, qty_col)
                    )

    # Case 3: 无 CTE，直接 GROUP BY 月份
    if (
        not re.search(r"\bWITH\s+monthly\b", sql, re.IGNORECASE)
        and re.search(r"\bGROUP\s+BY\s+FORMAT\s*\(\s*\w+\.TDATE", sql, re.IGNORECASE)
        and re.search(r"\bAS\s+月份\b", sql, re.IGNORECASE)
    ):
        inner = sql.strip().rstrip(";")
        log.append("仅问月均（无明细）：逐月 GROUP BY → monthly CTE + 单行聚合")
        return f"""WITH monthly AS (
{inner}
)
{_monthly_avg_single_row_sql("mo", qty_col)}"""

    return sql


def _fix_monthly_detail_no_repeated_summary(
    sql: str, user_query: str, log: list[str]
) -> str:
    """
    月维明细（提供明细 / 及其明细）不应 CROSS JOIN summary 重复汇总列。
    仅在有明细意图时保留逐月三列。
    """
    hints = _context_hints(user_query)
    if not hints["with_detail"]:
        return sql
    cross = re.search(
        r"FROM\s+monthly\s+(\w+)\s+CROSS\s+JOIN\s+summary\s+\w+",
        sql,
        re.IGNORECASE,
    )
    if not cross:
        return sql

    before = sql[: cross.start()]
    selects = list(re.finditer(r"\bSELECT\b", before, re.IGNORECASE))
    if not selects:
        return sql

    outer = sql[selects[-1].start() :]
    if not re.search(r"月份", outer, re.IGNORECASE):
        return sql

    alias = cross.group(1)
    log.append("月维明细：去掉每行重复的 月均使用量/期间领用数量合计，仅保留 月份+每月使用量+单位")
    detail = f"""SELECT
    {alias}.月份,
    {alias}.每月使用量,
    {alias}.单位
FROM monthly {alias}
ORDER BY {alias}.月份"""
    return before[: selects[-1].start()] + detail


def _ensure_monthly_avg_detail_structure(sql: str, user_query: str, log: list[str]) -> str:
    hints = _context_hints(user_query)
    if not (hints["monthly_avg"] and hints["with_detail"]):
        return sql
    if re.search(r"\bWITH\s+monthly\b", sql, re.IGNORECASE):
        return sql
    if re.search(r"GROUP\s+BY\s+FORMAT\s*\(\s*\w+\.TDATE", sql, re.IGNORECASE) and "月均" in sql:
        return sql

    # 误生成物料分列或流水
    if re.search(r"GROUP\s+BY\s+m\.INV_PART_NUMBER", sql, re.IGNORECASE):
        log.append("警告: 月均+明细 却 GROUP BY 物料，建议改用 monthly/summary CTE（需 LLM 重写）")
    if re.search(r"\bd207\.RKEY\s+AS\b", sql, re.IGNORECASE):
        log.append("警告: 月均+明细 却输出领用流水，建议改用月维 GROUP BY")
    return sql


def validate_and_fix_sql(sql: str, user_query: str = "") -> tuple[str, list[str]]:
    log: list[str] = []
    out = extract_executable_sql(_coerce_text(sql))
    if not out:
        return "", ["输入为空，无法提取 SQL"]

    out = _fix_broken_cte_monthly_summary(out, log)
    out = _fix_monthly_avg_only_single_row(out, user_query, log)
    out = _fix_monthly_detail_no_repeated_summary(out, user_query, log)
    out = _fix_extra_paren_114(out, log)
    out = _fix_blacklist_columns(out, log)
    out = _fix_part_number_grade_match(out, log)
    out = _fix_short_code_in_query(out, user_query, log)
    out = _fix_missing_joins(out, log)
    out = _fix_tdate_in_where_for_left_join(out, log)
    out = _fix_inner_join_d207_for_material_sum(out, log)
    out = _fix_as_year_brackets(out, log)
    out = _fix_order_by_top(out, log)
    out = _ensure_monthly_avg_detail_structure(out, user_query, log)

    # 去掉首尾空白，保留单条语句末尾可选分号
    out = out.strip()
    if out.endswith(";"):
        out = out.rstrip().rstrip(";").strip() + ";"
    return out, log


def main(
    arg1: Any = None,
    sql: Any = None,
    input_text: Any = None,
    user_query: Any = None,
    **kwargs: Any,
) -> dict[str, str]:
    raw = arg1 if arg1 is not None else sql if sql is not None else input_text
    if raw is None:
        raw = kwargs.get("arg1") or kwargs.get("sql") or kwargs.get("input_text")

    uq = user_query if user_query is not None else kwargs.get("user_query") or ""
    fixed, log = validate_and_fix_sql(raw or "", str(uq or ""))
    return {
        "result": fixed,
        "fix_log": "\n".join(log) if log else "",
        "fix_count": str(len(log)),
    }


if __name__ == "__main__":
    cte_sql = """
    SELECT FORMAT(d207.TDATE, N'yyyy-MM') AS 月份, SUM(ISNULL(d207.QUANTITY, 0)) AS 每月使用量, MAX(u.UNIT_NAME) AS 单位
    FROM Data0017 m
    LEFT JOIN Data0496 cat ON m.GROUP_PTR = cat.RKEY
    INNER JOIN Data0207 d207 ON m.RKEY = d207.INVENTORY_PTR AND d207.TDATE >= '2026-01-01' AND d207.TDATE < '2027-01-01'
    LEFT JOIN Data0002 u ON m.STOCK_UNIT_PTR = u.RKEY
    WHERE m.ACTIVE_FLAG = 'Y' AND (cat.ttype IS NULL OR cat.ttype <> N'T')
      AND ( m.INV_PART_DESCRIPTION LIKE N'%|KB-6160%' OR m.INV_PART_DESCRIPTION LIKE N'%KB-6160%'
         OR m.INV_DESCRIPTION LIKE N'%|KB-6160%' OR m.INV_DESCRIPTION LIKE N'%KB-6160%' )
    GROUP BY FORMAT(d207.TDATE, N'yyyy-MM')
    ), summary AS (
    SELECT ISNULL(SUM(每月使用量), 0) AS 期间领用数量合计,
           ISNULL(SUM(每月使用量) / NULLIF(COUNT(*), 0), 0) AS 月均使用量
    FROM monthly
    )
    SELECT mo.月份, mo.每月使用量, s.月均使用量, s.期间领用数量合计, mo.单位
    FROM monthly mo CROSS JOIN summary s ORDER BY mo.月份
    """

    r1, lg1 = validate_and_fix_sql(cte_sql, "统计2026年材料型号KB-6160的月均使用量及其明细")
    assert "WITH monthly AS (" in r1
    assert "CROSS JOIN summary" not in r1
    assert "FROM monthly mo" in r1
    assert "s.月均使用量" not in r1
    print("detail OK:", lg1)

    r2, lg2 = validate_and_fix_sql(
        "WITH monthly AS (\n" + cte_sql.strip(),
        "统计2026年材料型号KB-6160月均使用量",
    )
    assert "CROSS JOIN summary" not in r2
    assert "mo.月份" not in r2
    assert "ORDER BY mo.月份" not in r2
    assert "月均使用量" in r2
    print("avg-only cross OK:", lg2)

    monthly_only = """
WITH monthly AS (
    SELECT FORMAT(d207.TDATE, N'yyyy-MM') AS 月份,
           SUM(ISNULL(d207.QUANTITY, 0)) AS 每月使用量,
           MAX(u.UNIT_NAME) AS 单位
    FROM Data0017 m
    INNER JOIN Data0207 d207 ON m.RKEY = d207.INVENTORY_PTR
        AND d207.TDATE >= '2026-01-01' AND d207.TDATE < '2027-01-01'
    LEFT JOIN Data0002 u ON m.STOCK_UNIT_PTR = u.RKEY
    WHERE m.INV_PART_DESCRIPTION LIKE N'%KB-6160%'
    GROUP BY FORMAT(d207.TDATE, N'yyyy-MM')
)
SELECT mo.月份, mo.每月使用量, mo.单位 FROM monthly mo ORDER BY mo.月份
"""
    r3, lg3 = validate_and_fix_sql(monthly_only, "统计2026年材料型号KB-6160月均使用量")
    assert "mo.月份" not in r3
    assert "月均使用量" in r3
    assert lg3
    print("avg-only monthly-only OK:", lg3)

    r4, _ = validate_and_fix_sql(monthly_only, "提供明细")
    assert "mo.月份" in r4 or "月份" in r4
    print("provide detail keeps monthly OK")
