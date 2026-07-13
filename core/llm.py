# ============================================================
# core/llm.py
# LLM 调用模块：流式输出 + 异常处理（通过 Provider 抽象层）
# ============================================================

import logging
import time
from config import SYSTEM_PROMPT, SYSTEM_PROMPT_EN, SYSTEM_PROMPT_MIXED, SETTINGS_FILE
from core.settings_manager import load_settings
from core.llm_provider import create_provider, get_extraction_model

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """带用户可读信息的 LLM 调用错误（由路由层转为 SSE error 事件）。"""


def classify_llm_error(e: Exception, language: str = "zh") -> str:
    """将底层异常翻译为用户可读的错误信息。"""
    s = str(e)
    sl = s.lower()
    zh = language != "en"
    if "429" in s or "quota" in sl or "rate" in sl:
        return ("API 调用超限（429），请稍后再试或检查配额。" if zh
                else "API rate limit exceeded (429). Please retry later or check your quota.")
    if "timeout" in sl or "deadline" in sl:
        return ("网络超时，请检查网络连接后重试。" if zh
                else "Network timeout. Please check your connection and retry.")
    if "api_key" in sl or "401" in s or "authentication" in sl or "invalid" in sl:
        return ("API Key 无效，请在设置中检查配置。" if zh
                else "Invalid API key. Please check it in Settings.")
    if "safety" in sl or "blocked" in sl:
        return ("查询内容被安全过滤器拦截，请调整关键词。" if zh
                else "The request was blocked by a safety filter. Please adjust your query.")
    return (f"AI 调用失败：{s[:200]}" if zh else f"AI request failed: {s[:200]}")


def build_prompt(user_query: str, context: str) -> str:
    """将检索结果拼装成发送给 LLM 的完整 Prompt"""
    prompt = f"""以下是从历史文献数据库中检索到的相关记录：

{'=' * 60}
{context}
{'=' * 60}

用户查询主题：{user_query}

请根据上方提供的历史文献，严格按照要求进行摘录。"""
    return prompt


def stream_query(
    user_query: str,
    context: str,
    language: str = "zh",
    model_name: str = None,
    system_prompt: str = None,
):
    """
    调用 LLM API，以流式方式返回结果。
    自动根据 settings 中的 provider 选择对应的 AI 提供商。
    限速错误（429）在未输出任何内容前自动重试；最终失败抛 LLMError。
    """
    settings = load_settings(SETTINGS_FILE)

    if system_prompt:
        sys_prompt = system_prompt
    elif language == "en":
        sys_prompt = SYSTEM_PROMPT_EN
    elif language == "mixed":
        sys_prompt = SYSTEM_PROMPT_MIXED
    else:
        sys_prompt = SYSTEM_PROMPT

    _model_name = model_name or get_extraction_model(settings)

    full_prompt = build_prompt(user_query, context)
    logger.info(f"发送 Prompt，总长度: {len(full_prompt)} 字符，模型: {_model_name}")

    MAX_RETRIES = 2
    RETRY_WAIT = 10

    for attempt in range(MAX_RETRIES + 1):
        yielded = False
        try:
            provider = create_provider(settings, model_override=_model_name)
            for chunk in provider.generate_stream(
                prompt=full_prompt,
                system_prompt=sys_prompt,
                temperature=0.1,
                max_tokens=8192,
            ):
                yielded = True
                yield chunk
            return
        except Exception as e:
            error_str = str(e)
            logger.error(f"LLM API 错误 (第{attempt+1}次): {error_str}", exc_info=True)
            is_rate_limit = "429" in error_str or "quota" in error_str.lower() or "rate" in error_str.lower()
            # 未输出任何内容且是限速错误 → 等待后重试；否则直接报错
            if is_rate_limit and not yielded and attempt < MAX_RETRIES:
                logger.info(f"限速，{RETRY_WAIT}s 后重试 ({attempt+1}/{MAX_RETRIES})")
                time.sleep(RETRY_WAIT)
                continue
            raise LLMError(classify_llm_error(e, language)) from e
