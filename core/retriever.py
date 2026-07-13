# ============================================================
# core/retriever.py — AI 查询扩展 + 加权全文检索
# 说明：检索用 DuckDB 向量化 LIKE 扫描 + 字段加权计分。
# 实测（2026-07）：100 万行 10 关键词约 0.3s，快于 DuckDB FTS 扩展的
# 中文单字索引方案（更慢且相关性差），故不引入 FTS。
# ============================================================

import re as _re
import logging
import os
import duckdb
import jieba
from config import MAX_SEARCH_RESULTS, MAX_CONTEXT_CHARS, TOP_K_FOR_LLM, TOP_K_PER_SOURCE

logger = logging.getLogger(__name__)

# 英文停用词
ENGLISH_STOPWORDS = {
    "the", "a", "an", "is", "was", "were", "are", "been", "be",
    "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "shall", "can",
    "of", "in", "to", "for", "with", "on", "at", "from", "by",
    "and", "or", "but", "not", "no", "nor", "so", "yet",
    "this", "that", "these", "those", "it", "its",
    "as", "if", "than", "then", "also", "very", "just",
    "about", "into", "through", "during", "before", "after",
    "above", "below", "between", "under", "over",
}

_RECORD_COLS = [
    "id","source_file","file_type","doc_type",
    "year","date","page","title",
    "author","pub_year","publisher",
    "chapter","section","page_num",
    "interviewee","interview_date","interview_location",
    "content","relevance_score",
]


def _tokenize_zh(query: str) -> list:
    stopwords = set("的了是在和与以及或但也都已从对于关于等这那")
    words = jieba.cut_for_search(query)
    tokens = [w.strip() for w in words if len(w.strip()) >= 2 and w not in stopwords]
    tokens.append(query.strip())
    return list(set(tokens))


def _tokenize_en(query: str) -> list:
    words = _re.findall(r"[a-zA-Z]{2,}", query.lower())
    tokens = [w for w in words if w not in ENGLISH_STOPWORDS and len(w) >= 2]
    raw_words = _re.findall(r"[a-zA-Z]+", query.lower())
    for i in range(len(raw_words) - 1):
        bigram = f"{raw_words[i]} {raw_words[i+1]}"
        if raw_words[i] not in ENGLISH_STOPWORDS or raw_words[i+1] not in ENGLISH_STOPWORDS:
            tokens.append(bigram)
    tokens.append(query.strip())
    return list(set(tokens))


def tokenize_query(query: str, language: str = "zh") -> list:
    if language == "en":
        return _tokenize_en(query)
    elif language == "mixed":
        return list(set(_tokenize_zh(query) + _tokenize_en(query)))
    else:
        return _tokenize_zh(query)


def build_weighted_search_sql(
    weighted_tokens: list,
    date_from: str = "",
    date_to: str = "",
    file_filter: list = None,
    allowed_files: list = None,
) -> tuple:
    """
    构建加权搜索 SQL（全参数化，无字符串拼接）。

    file_filter:   文件名列表（多选筛选）
    allowed_files: 项目文件白名单（列表）
    """
    if not weighted_tokens:
        return "", []

    conditions = []
    params = []
    score_parts = []

    for token, word_weight in weighted_tokens:
        like_pattern = f"%{token}%"
        conditions.append(
            "(title LIKE ? OR content LIKE ? OR chapter LIKE ? OR author LIKE ?)"
        )
        params.extend([like_pattern, like_pattern, like_pattern, like_pattern])

        score_parts.append(
            f"(CASE WHEN title   LIKE ? THEN {word_weight * 3} ELSE 0 END"
            f" + CASE WHEN chapter LIKE ? THEN {word_weight * 2} ELSE 0 END"
            f" + CASE WHEN content LIKE ? THEN {word_weight * 1} ELSE 0 END)"
        )
        params.extend([like_pattern, like_pattern, like_pattern])

    where_clause = " OR ".join(conditions)
    score_expr   = " + ".join(score_parts)

    # ── 参数化日期过滤 ──
    # 按字段优先级取值：date > year > pub_year。
    # 不能用 OR（记录同时有 date 和 year 时，宽松的 year 条件会吞掉精确的 date 过滤）。
    extra_conditions = []
    _date_case = (
        "CASE WHEN NULLIF(date,'') IS NOT NULL THEN date {op} ? "
        "WHEN NULLIF(year,'') IS NOT NULL THEN year {op} ? "
        "WHEN NULLIF(pub_year,'') IS NOT NULL THEN pub_year {op} ? "
        "ELSE FALSE END"
    )
    if date_from:
        extra_conditions.append("(" + _date_case.format(op=">=") + ")")
        params.extend([date_from, date_from[:4], date_from[:4]])
    if date_to:
        extra_conditions.append("(" + _date_case.format(op="<=") + ")")
        params.extend([date_to, date_to[:4], date_to[:4]])

    # ── 参数化文件筛选 ──
    if file_filter:
        placeholders = ", ".join(["?" for _ in file_filter])
        extra_conditions.append(f"source_file IN ({placeholders})")
        params.extend(file_filter)

    # ── 参数化项目白名单 ──
    if allowed_files:
        placeholders = ", ".join(["?" for _ in allowed_files])
        extra_conditions.append(f"source_file IN ({placeholders})")
        params.extend(allowed_files)

    # 组装 WHERE
    all_where_parts = [f"({where_clause})"]
    if extra_conditions:
        all_where_parts.append(" AND ".join(extra_conditions))
    final_where = " AND ".join(all_where_parts)

    sql = f"""
        SELECT id, source_file, file_type, doc_type,
               year, date, page, title,
               author, pub_year, publisher,
               chapter, section, page_num,
               interviewee, interview_date, interview_location,
               content,
               ({score_expr}) AS relevance_score
        FROM documents
        WHERE {final_where}
        ORDER BY relevance_score DESC
        LIMIT {MAX_SEARCH_RESULTS}
    """
    return sql, params


def format_citation(rec: dict) -> str:
    doc_type = rec.get("doc_type", "") or rec.get("file_type", "")

    if doc_type == "newspaper":
        date_str  = rec.get("date") or rec.get("year") or "日期不详"
        page_str  = rec.get("page") or "版次不详"
        title_str = rec.get("title") or "无标题"
        return f"[日期：{date_str} / 版面：{page_str} / 标题：{title_str}]"
    elif doc_type == "book":
        parts = []
        if rec.get("author"):    parts.append(rec["author"])
        if rec.get("title"):     parts.append(f"《{rec['title']}》")
        if rec.get("publisher"): parts.append(rec["publisher"])
        if rec.get("pub_year"):  parts.append(rec["pub_year"])
        if rec.get("chapter"):   parts.append(rec["chapter"])
        if rec.get("section"):   parts.append(rec["section"])
        if rec.get("page_num"):  parts.append(rec["page_num"])
        return "[" + "，".join(parts) + "]"
    elif doc_type == "paper":
        parts = []
        if rec.get("author"):   parts.append(rec["author"])
        if rec.get("title"):    parts.append(f"〈{rec['title']}〉")
        if rec.get("pub_year"): parts.append(rec["pub_year"])
        if rec.get("page_num"): parts.append(rec["page_num"])
        return "[" + "，".join(parts) + "]"
    elif doc_type == "interview":
        parts = []
        if rec.get("interviewee"):        parts.append(f"受访：{rec['interviewee']}")
        if rec.get("interview_date"):     parts.append(f"时间：{rec['interview_date']}")
        if rec.get("interview_location"): parts.append(f"地点：{rec['interview_location']}")
        if rec.get("title"):              parts.append(f"来源：{rec['title']}")
        return "[" + "，".join(parts) + "]"
    else:
        parts = []
        for k, label in [("title","来源"),("author","作者"),("date","日期"),
                          ("chapter","章节"),("page_num","页码")]:
            if rec.get(k): parts.append(f"{label}：{rec[k]}")
        return "[" + "，".join(parts) + "]" if parts else "[来源不详]"


def _apply_diversity(records: list, k: int, min_per_source: int) -> list:
    if not records or k <= 0 or min_per_source <= 0:
        return records[:k]

    from collections import defaultdict

    top_slice = records[:k]
    source_counts: dict = defaultdict(int)
    for r in top_slice:
        source_counts[r["source_file"]] += 1

    selected = list(top_slice)
    selected_ids = {r["id"] for r in selected}

    for r in records[k:]:
        src = r["source_file"]
        if source_counts[src] < min_per_source and r["id"] not in selected_ids:
            selected.append(r)
            selected_ids.add(r["id"])
            source_counts[src] += 1

    selected.sort(key=lambda x: x["relevance_score"], reverse=True)
    return selected


def _run_search_raw(db_path: str, sql: str, params: list) -> list:
    """在指定 DB 上执行搜索 SQL，返回 records 列表。"""
    try:
        conn = duckdb.connect(db_path, read_only=True)
        rows = conn.execute(sql, params).fetchall()
        conn.close()
        return [dict(zip(_RECORD_COLS, row)) for row in rows]
    except Exception as e:
        logger.error(f"检索失败 ({db_path}): {e}", exc_info=True)
        return []


def search(
    db_path: str,
    query: str,
    date_from: str = "",
    date_to: str = "",
    file_filter: list = None,
    top_k: int = None,
    weighted_tokens: list = None,
    language: str = "zh",
    allowed_files: list = None,
) -> dict:
    """
    执行加权检索。
    file_filter:   可选文件名列表（用户多选筛选）。
    allowed_files: 可选文件白名单（项目引用列表），为 None 时搜索全库。
    """
    if weighted_tokens:
        tokens_display = [w for w, _ in weighted_tokens]
        logger.info(f"使用 AI 扩展关键词: {weighted_tokens}")
    else:
        plain_tokens = tokenize_query(query, language=language)
        weighted_tokens = [(t, 1) for t in plain_tokens]
        tokens_display = plain_tokens
        logger.info(f"退回分词 (language={language}): {plain_tokens}")

    if not weighted_tokens:
        return {
            "records": [], "total_found": 0,
            "context": "", "context_chars": 0,
            "truncated": False, "tokens": [],
        }

    sql, params = build_weighted_search_sql(
        weighted_tokens,
        date_from=date_from,
        date_to=date_to,
        file_filter=file_filter,
        allowed_files=allowed_files,
    )
    records = _run_search_raw(db_path, sql, params)
    total_found = len(records)
    logger.info(f"检索到 {total_found} 条记录")

    k = top_k if top_k is not None else TOP_K_FOR_LLM
    records_for_llm = _apply_diversity(records, k, TOP_K_PER_SOURCE)

    # 按记录边界累积 context，超限时丢弃后续整条记录（不把史料拦腰砍断）
    context_parts = []
    context_chars = 0
    truncated     = False
    for r in records_for_llm:
        citation = format_citation(r)
        part = (
            f"【文献信息】{citation}\n"
            f"【内容】{r.get('content','')}\n"
            f"{'─' * 60}"
        )
        if context_chars + len(part) + 2 > MAX_CONTEXT_CHARS:
            truncated = True
            logger.warning(f"Context 超限，保留前 {len(context_parts)} 条记录")
            break
        context_parts.append(part)
        context_chars += len(part) + 2

    full_context = "\n\n".join(context_parts)
    context_chars = len(full_context)

    return {
        "records":       records,
        "total_found":   total_found,
        "context":       full_context,
        "context_chars": context_chars,
        "truncated":     truncated,
        "tokens":        tokens_display,
    }


# 库概况缓存：{db_path: (mtime, summary)}，导入/删除会改变文件 mtime 自动失效
_summary_cache: dict = {}


def get_db_context_summary(db_path: str) -> str:
    try:
        mtime = os.path.getmtime(db_path)
        cached = _summary_cache.get(db_path)
        if cached and cached[0] == mtime:
            return cached[1]
        conn = duckdb.connect(db_path, read_only=True)
        type_rows = conn.execute(
            "SELECT doc_type, COUNT(*) AS n FROM documents GROUP BY doc_type ORDER BY n DESC"
        ).fetchall()
        yr = conn.execute(
            "SELECT MIN(year), MAX(year) FROM documents WHERE year != '' AND year IS NOT NULL"
        ).fetchone()
        conn.close()
    except Exception:
        return ""

    type_map = {"newspaper": "报纸", "book": "书籍", "paper": "学术论文", "interview": "访谈"}
    parts = []
    for doc_type, n in type_rows:
        label = type_map.get(doc_type or "", doc_type or "其他")
        parts.append(f"{label} {n:,} 条")

    yr_str = ""
    if yr and yr[0] and yr[1]:
        yr_str = f"，时间跨度 {yr[0]}-{yr[1]} 年"

    summary = "、".join(parts) + yr_str
    _summary_cache[db_path] = (mtime, summary)
    return summary


def get_record_by_id(db_path: str, record_id: int) -> dict | None:
    """按 id 取单条完整记录（记录列表只带预览，详情弹窗用此接口取全文）。"""
    conn = duckdb.connect(db_path, read_only=True)
    row = conn.execute(
        f"SELECT {', '.join(c for c in _RECORD_COLS if c != 'relevance_score')} "
        "FROM documents WHERE id = ?", [record_id]
    ).fetchone()
    conn.close()
    if not row:
        return None
    rec = dict(zip([c for c in _RECORD_COLS if c != 'relevance_score'], row))
    rec["relevance_score"] = 0
    return rec


def get_all_source_files(db_path: str) -> list:
    conn = duckdb.connect(db_path, read_only=True)
    rows = conn.execute(
        "SELECT DISTINCT source_file FROM documents ORDER BY source_file"
    ).fetchall()
    conn.close()
    return [r[0] for r in rows]
