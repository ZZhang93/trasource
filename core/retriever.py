# ============================================================
# core/retriever.py  (v3 — 支持 AI 查询扩展 + 加权 BM25)
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
    extra_where: list = None,
) -> tuple:
    """
    构建加权搜索 SQL。
    extra_where: 额外的 WHERE 条件列表（如文件筛选、项目白名单），会直接嵌入 SQL。
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

    date_filter = ""
    if date_from:
        date_filter += (
            f" AND (NULLIF(date,'') >= '{date_from}'"
            f" OR NULLIF(year,'') >= '{date_from[:4]}'"
            f" OR NULLIF(pub_year,'') >= '{date_from[:4]}')"
        )
    if date_to:
        date_filter += (
            f" AND (NULLIF(date,'') <= '{date_to}'"
            f" OR NULLIF(year,'') <= '{date_to[:4]}'"
            f" OR NULLIF(pub_year,'') <= '{date_to[:4]}')"
        )

    # 额外过滤条件（文件筛选、项目白名单等）直接嵌入 WHERE
    extra_filter = ""
    if extra_where:
        extra_filter = " AND " + " AND ".join(extra_where)
        logger.info(f"SQL 额外过滤条件: {extra_filter}")

    sql = f"""
        SELECT id, source_file, file_type, doc_type,
               year, date, page, title,
               author, pub_year, publisher,
               chapter, section, page_num,
               interviewee, interview_date, interview_location,
               content,
               ({score_expr}) AS relevance_score
        FROM documents
        WHERE ({where_clause}){date_filter}{extra_filter}
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


def _run_search_raw(db_path: str, sql: str, params: list,
                    extra_conditions: list = None, id_prefix: str = "") -> list:
    """在指定 DB 上执行搜索 SQL，返回 records 列表。"""
    try:
        conn = duckdb.connect(db_path)
        final_sql = sql
        if extra_conditions:
            extra = " AND ".join(extra_conditions)
            final_sql = sql.replace("WHERE (", f"WHERE {extra} AND (")
        rows = conn.execute(final_sql, params).fetchall()
        records = [dict(zip(_RECORD_COLS, row)) for row in rows]
        conn.close()
        # 防止跨库 id 冲突
        if id_prefix:
            for r in records:
                r["id"] = f"{id_prefix}{r['id']}"
        return records
    except Exception as e:
        logger.error(f"检索失败 ({db_path}): {e}", exc_info=True)
        return []


def search(
    db_path: str,
    query: str,
    date_from: str = "",
    date_to: str = "",
    file_filter: str = "",
    doc_type_filter: str = "",
    top_k: int = None,
    weighted_tokens: list = None,
    language: str = "zh",
    allowed_files: list = None,
) -> dict:
    """
    执行加权检索。
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

    # ── 构建额外过滤条件（直接嵌入 SQL，而非后期字符串替换） ──
    extra_where = []
    if file_filter:
        # 支持字符串（单个文件名）或列表（多选文件）
        if isinstance(file_filter, list) and len(file_filter) > 0:
            safe = [f.replace("'", "''") for f in file_filter]
            escaped = ", ".join([f"'{f}'" for f in safe])
            extra_where.append(f"source_file IN ({escaped})")
            logger.info(f"文件筛选（多选）: {file_filter}")
        elif isinstance(file_filter, str) and file_filter.strip():
            safe = file_filter.replace("'", "''")
            extra_where.append(f"source_file = '{safe}'")
            logger.info(f"文件筛选（单文件）: {file_filter}")
    if doc_type_filter:
        safe = doc_type_filter.replace("'", "''")
        extra_where.append(f"doc_type = '{safe}'")
    # 仅搜索项目引用的文件（白名单过滤）
    if allowed_files:
        safe_files = [f.replace("'", "''") for f in allowed_files]
        escaped = ", ".join([f"'{f}'" for f in safe_files])
        extra_where.append(f"source_file IN ({escaped})")
        logger.info(f"项目白名单文件数: {len(allowed_files)}")

    logger.info(f"extra_where 条件数: {len(extra_where)}, 条件: {extra_where}")

    sql, params = build_weighted_search_sql(
        weighted_tokens, date_from, date_to,
        extra_where=extra_where or None,
    )
    # 直接执行 SQL（过滤条件已嵌入 SQL 中，无需字符串替换）
    if sql:
        logger.info(f"最终 SQL (前300字符): {sql[:300]}")
    records = _run_search_raw(db_path, sql, params)

    total_found_raw = len(records)
    logger.info(f"SQL 检索到 {total_found_raw} 条记录")

    # ── Python 层安全过滤（防止 SQL 过滤失效） ──
    if file_filter:
        if isinstance(file_filter, list) and len(file_filter) > 0:
            filter_set = set(file_filter)
            before = len(records)
            records = [r for r in records if r.get("source_file") in filter_set]
            after = len(records)
            if before != after:
                # 如果 SQL 过滤没生效，在这里兜底
                sample_files = set()
                for r in records[:5]:
                    sample_files.add(r.get("source_file", "?"))
                logger.warning(
                    f"⚠️ SQL筛选未完全生效！Python后置过滤: {before} → {after} 条, "
                    f"目标文件: {file_filter}, 结果样本: {sample_files}"
                )
            else:
                logger.info(f"SQL筛选已生效，{after} 条记录全部在目标文件范围内")
        elif isinstance(file_filter, str) and file_filter.strip():
            before = len(records)
            records = [r for r in records if r.get("source_file") == file_filter.strip()]
            after = len(records)
            if before != after:
                logger.warning(f"⚠️ SQL筛选未完全生效！Python后置过滤: {before} → {after} 条")

    total_found = len(records)
    logger.info(f"最终返回 {total_found} 条记录")

    k = top_k if top_k is not None else TOP_K_FOR_LLM
    records_for_llm = _apply_diversity(records, k, TOP_K_PER_SOURCE)

    context_parts = []
    for r in records_for_llm:
        citation = format_citation(r)
        part = (
            f"【文献信息】{citation}\n"
            f"【内容】{r.get('content','')}\n"
            f"{'─' * 60}"
        )
        context_parts.append(part)

    full_context  = "\n\n".join(context_parts)
    context_chars = len(full_context)
    truncated     = False

    if context_chars > MAX_CONTEXT_CHARS:
        full_context = full_context[:MAX_CONTEXT_CHARS]
        truncated    = True
        logger.warning(f"Context 超限，已截断至 {MAX_CONTEXT_CHARS} 字符")

    return {
        "records":       records,
        "total_found":   total_found,
        "context":       full_context,
        "context_chars": context_chars,
        "truncated":     truncated,
        "tokens":        tokens_display,
    }


def get_db_context_summary(db_path: str) -> str:
    try:
        conn = duckdb.connect(db_path)
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

    return "、".join(parts) + yr_str


def get_all_source_files(db_path: str) -> list:
    conn = duckdb.connect(db_path)
    rows = conn.execute(
        "SELECT DISTINCT source_file FROM documents ORDER BY source_file"
    ).fetchall()
    conn.close()
    return [r[0] for r in rows]


def get_doc_type_stats(db_path: str) -> dict:
    conn = duckdb.connect(db_path)
    rows = conn.execute(
        "SELECT doc_type, COUNT(*) FROM documents GROUP BY doc_type ORDER BY doc_type"
    ).fetchall()
    conn.close()
    return {(r[0] or "未分类"): r[1] for r in rows}
