# ============================================================
# core/query_expander.py  (v5 — 多 AI 提供商支持)
# ============================================================

import json
import logging
from config import SETTINGS_FILE
from core.settings_manager import load_settings
from core.llm_provider import create_provider, get_expansion_model

logger = logging.getLogger(__name__)

EXPANSION_PROMPT = """你是一位中国近现代史研究专家，精通1949年后的中国政治史、经济史和社会史文献。

数据库内容：{sources}

用户想在上述文献中检索以下主题：
"{query}"

请先在脑中完成以下分析（不要输出分析过程），然后生成搜索词：
1. 这个查询涉及什么历史事件或政策？发生在什么时间段？
2. 相关的关键人物有哪些？（领导人、当事人、记者等）
3. 相关的地点有哪些？（省、市、县等具体地名）
4. 当时官方和媒体使用什么术语描述此事？有没有特定的政策名称或运动名称？
5. 有哪些关联事件或背景政策？

基于上述分析，生成10-20个在该类文献中实际会出现的搜索词，标注权重（1-10）。
权重10=核心事件/政策名，8-9=核心人物和地点，6-7=相关政策术语，4-5=背景词。
搜索词必须具体（优先使用专有名词、地名、人名、政策名），避免过于宽泛的通用词。
请根据文献类型调整用语风格：
- 报纸：使用当时的官方称谓和报道用语
- 书籍/论文：使用学术规范表述
- 访谈：考虑口语化和具体情景描述

直接输出JSON对象，不加任何markdown格式：
{{"intent":"检索意图一句话","time_range":"起止年份或null","terms":{{"词1":权重,"词2":权重}}}}"""

EXPANSION_PROMPT_EN = """You are an expert in modern world history, particularly post-1900 political, economic, and social history.

Database contents: {sources}

The user wants to search the above documents about:
"{query}"

Before generating search terms, mentally analyze (do not output the analysis):
1. What historical event, policy, or phenomenon does this query refer to? What time period?
2. Key figures involved? (leaders, participants, journalists, etc.)
3. Specific locations? (countries, cities, regions)
4. What terminology did contemporary media and officials use to describe this?
5. Related events or background policies?

Based on your analysis, generate 10-20 search terms that would actually appear in those document types, with weights (1-10).
Weight 10 = core event/policy names, 8-9 = key people and places, 6-7 = related policy terms, 4-5 = background terms.
Terms must be specific (prefer proper nouns, place names, person names, policy names). Avoid overly generic words.

Output a JSON object directly, no markdown formatting:
{{"intent":"search intent in one sentence","time_range":"year range or null","terms":{{"term1":weight,"term2":weight}}}}"""

EXPANSION_PROMPT_MIXED = """你是一位精通中英文历史文献的研究专家。
You are an expert in both Chinese and English historical documents.

数据库内容 / Database contents: {sources}

用户想在上述文献中检索以下主题：
"{query}"

请先在脑中完成以下分析（不要输出分析过程）/ Mentally analyze first (do not output):
1. 涉及什么历史事件或政策？/ What historical event or policy?
2. 关键人物？/ Key figures?
3. 相关地点？/ Specific locations?
4. 当时的官方术语？/ Contemporary official terminology?
5. 关联事件或背景？/ Related events or context?

生成10-20个在该类文献中实际出现过的搜索词（中英文混合），标注权重（1-10）。
Generate 10-20 search terms (mixed Chinese/English) with weights (1-10).
优先使用专有名词、地名、人名、政策名，避免通用词。
Prefer proper nouns, place names, person names, policy names. Avoid generic words.

直接输出JSON对象，不加任何markdown格式：
{{"intent":"检索意图/search intent","time_range":"时间范围或null","terms":{{"词1/term1":权重,"词2/term2":权重}}}}"""


def _parse_json(raw: str) -> dict:
    """容错 JSON 解析"""
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    start = raw.find('{')
    end   = raw.rfind('}')
    if start != -1 and end > start:
        try:
            return json.loads(raw[start:end+1])
        except json.JSONDecodeError:
            pass
    raise ValueError(f"无法解析JSON，内容：{raw[:200]}")


def expand_query(
    user_query: str,
    language: str = "zh",
    sources: str = "",
    model_name: str = None,
    prompt_template: str = None,
) -> dict:
    settings = load_settings(SETTINGS_FILE)
    _model_name = model_name or get_expansion_model(settings)
    logger.info(f"查询扩展开始：{user_query}  模型：{_model_name}  语言：{language}")

    if prompt_template and language == "zh":
        selected_template = prompt_template
    elif language == "en":
        selected_template = EXPANSION_PROMPT_EN
    elif language == "mixed":
        selected_template = EXPANSION_PROMPT_MIXED
    else:
        selected_template = EXPANSION_PROMPT

    sources_str = sources if sources else "历史文献（报纸、书籍、访谈）"

    try:
        provider = create_provider(settings, model_override=_model_name)
        raw_text = provider.generate(
            prompt=selected_template.format(query=user_query, sources=sources_str),
            temperature=0.2,
            max_tokens=8192,
        )

        result = _parse_json(raw_text)

        if "terms" not in result:
            raise ValueError(f"JSON缺少terms，收到：{list(result.keys())}")

        cleaned = {}
        for term, weight in result["terms"].items():
            try:
                w = max(1, min(10, int(float(weight))))
                if term.strip():
                    cleaned[term.strip()] = w
            except (ValueError, TypeError):
                cleaned[term.strip()] = 5

        result.update({"terms": cleaned, "raw_query": user_query, "success": True})
        logger.info(f"查询扩展成功：{cleaned}")
        return result

    except Exception as e:
        logger.error(f"查询扩展失败：{e}", exc_info=True)
        return _fallback(user_query, str(e), language)


def _fallback(user_query: str, error: str, language: str = "zh") -> dict:
    logger.warning(f"降级到分词 (language={language})：{error}")
    try:
        if language == "en":
            import re as _re
            words = [w for w in _re.findall(r"[a-zA-Z]{2,}", user_query.lower()) if len(w) >= 2]
            terms = {w: 5 for w in set(words)}
        elif language == "mixed":
            import re as _re
            import jieba
            zh_words = [w.strip() for w in jieba.cut_for_search(user_query) if len(w.strip()) >= 2]
            en_words = [w for w in _re.findall(r"[a-zA-Z]{2,}", user_query.lower()) if len(w) >= 2]
            terms = {w: 5 for w in set(zh_words + en_words)}
        else:
            import jieba
            words = [w.strip() for w in jieba.cut_for_search(user_query) if len(w.strip()) >= 2]
            terms = {w: 5 for w in set(words)}
        terms[user_query.strip()] = 8
    except Exception:
        terms = {user_query.strip(): 8}
    return {
        "intent": user_query, "time_range": None,
        "terms": terms, "raw_query": user_query,
        "success": False, "error": error,
    }
