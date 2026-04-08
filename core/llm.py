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
        try:
            provider = create_provider(settings, model_override=_model_name)
            yield from provider.generate_stream(
                prompt=full_prompt,
                system_prompt=sys_prompt,
                temperature=0.1,
                max_tokens=8192,
            )
            return

        except Exception as e:
            error_str = str(e)
            logger.error(f"LLM API 错误 (第{attempt+1}次): {error_str}", exc_info=True)

            if "429" in error_str or "quota" in error_str.lower() or "rate" in error_str.lower():
                if attempt < MAX_RETRIES:
                    yield f"\n\n⏳ **API 请求过于频繁（429 限速），{RETRY_WAIT} 秒后自动重试（第 {attempt+1}/{MAX_RETRIES} 次）...**\n\n"
                    time.sleep(RETRY_WAIT)
                    continue
                else:
                    yield "\n\n❌ **错误：API 调用次数超限（429 Too Many Requests）**\n\n请等待几分钟后再试，或检查你的 API 配额。"
                    return
            elif "timeout" in error_str.lower() or "deadline" in error_str.lower():
                yield "\n\n❌ **错误：网络超时**\n\n请检查你的网络连接，然后重试。"
                return
            elif "api_key" in error_str.lower() or "invalid" in error_str.lower() or "401" in error_str or "authentication" in error_str.lower():
                yield "\n\n❌ **错误：API Key 无效**\n\n请在设置中检查 API Key 是否填写正确。"
                return
            elif "safety" in error_str.lower() or "blocked" in error_str.lower():
                yield "\n\n⚠️ **提示：本次查询内容被安全过滤器拦截。**\n\n请尝试调整查询关键词。"
                return
            else:
                yield f"\n\n❌ **发生未知错误：**\n```\n{error_str}\n```\n\n请查看 `logs/app.log` 获取详细信息。"
                return
