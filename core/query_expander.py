# ============================================================
# core/query_expander.py — 多 AI 提供商支持
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

基于上述分析，生成10-20个搜索词，标注权重（1-10）。
权重10=核心事件/政策名，8-9=核心人物和地点，6-7=相关政策术语，4-5=背景词。

重要：搜索词将用于全文逐字匹配（不是语义检索），必须遵守——
- 每个词必须是文献原文中会连续出现的字串，中文以2-6字为宜；禁止整句，禁止标点和空格
- 优先专有名词：地名、人名、机构名、政策名、运动名；避免"历史""发展""情况"这类宽泛词
- 同一实体的不同写法分别列出（全称/简称、今名/当时称谓），如"计划生育"与"计生"
- 按文献类型调整用语：报纸用当时的官方称谓和报道用语，书籍/论文用学术表述，访谈考虑口语说法

直接输出合法JSON对象（英文双引号，权重为数字），不加任何markdown代码块标记：
{{"intent":"检索意图一句话","time_range":"起止年份如1958-1962，不确定则null","terms":{{"词1":权重,"词2":权重}}}}"""

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

Based on your analysis, generate 10-20 search terms with weights (1-10).
Weight 10 = core event/policy names, 8-9 = key people and places, 6-7 = related policy terms, 4-5 = background terms.

Important: terms are matched as literal substrings in full text (not semantic search) —
- Each term must be a word or short phrase (1-3 words) that would literally appear in the documents; no full sentences, no punctuation
- Prefer proper nouns: places, persons, institutions, policy/campaign names; avoid generic words like "history" or "development"
- List different spellings/forms of the same entity separately (full name vs. abbreviation, modern vs. contemporary name)
- Match the register of the document types: period-appropriate press terminology for newspapers, academic phrasing for books/papers

Output a valid JSON object directly (double quotes, numeric weights), no markdown code fences:
{{"intent":"search intent in one sentence","time_range":"year range like 1958-1962, or null","terms":{{"term1":weight,"term2":weight}}}}"""

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

生成10-20个搜索词（中英文混合），标注权重（1-10）。
Generate 10-20 search terms (mixed Chinese/English) with weights (1-10).

重要 / Important：搜索词用于全文逐字匹配（非语义检索）——
- 中文词以2-6字为宜，英文为1-3个单词的短语；禁止整句和标点
  Terms must literally appear in documents; no full sentences or punctuation
- 优先专有名词（地名、人名、机构、政策名），避免宽泛词；同一实体的中英文写法分别列出
  Prefer proper nouns; list Chinese and English forms of the same entity separately

直接输出合法JSON对象（英文双引号），不加任何markdown代码块标记：
{{"intent":"检索意图/search intent","time_range":"起止年份或null","terms":{{"词1/term1":权重,"词2/term2":权重}}}}"""


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
