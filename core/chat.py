# ============================================================
# core/chat.py
# AI 对话模块：与选定文献进行直接对话（通过 Provider 抽象层）
# ============================================================

import logging
from config import SETTINGS_FILE
from core.settings_manager import load_settings
from core.llm_provider import create_provider, get_extraction_model

logger = logging.getLogger(__name__)

CHAT_SYSTEM_PROMPT = """你是一位历史研究助手。用户已经通过 AI 检索引擎从历史文献中提取了一批相关摘录，
你的任务是基于这些摘录，帮助用户进行深度分析和讨论。
你可以：
1. 解释摘录中的历史术语和背景
2. 比较不同摘录之间的异同与矛盾
3. 分析摘录所反映的历史现象和规律
4. 帮助用户提炼研究论点，指出证据的强弱
5. 翻译或解释古文/专业术语
请严格基于提供的摘录内容进行讨论，明确区分原文引用与你的分析推断。
如果摘录中没有足够信息回答问题，请直接说明。"""

CHAT_SYSTEM_PROMPT_EN = """You are a historical research assistant. The user has used an AI retrieval engine to extract relevant excerpts from historical documents.
Your task is to help the user conduct in-depth analysis and discussion based on these excerpts.
You can:
1. Explain historical terminology and context in the excerpts
2. Compare similarities, differences, and contradictions across excerpts
3. Analyze historical phenomena and patterns reflected in the excerpts
4. Help the user develop research arguments and assess the strength of evidence
5. Translate or explain archaic/specialized terms
Base your discussion strictly on the provided excerpts, clearly distinguishing between quoted text and your analytical inferences.
If the excerpts don't contain enough information to answer a question, say so directly."""


def build_chat_context(selected_records: list) -> str:
    """将选中的记录格式化为对话上下文。"""
    if not selected_records:
        return ""
    from core.retriever import format_citation
    parts = []
    for i, rec in enumerate(selected_records, 1):
        citation = format_citation(rec)
        content = rec.get("content", "")
        parts.append(f"【文献 {i}】{citation}\n{content}")
    return "\n\n" + ("═" * 40 + "\n\n").join(parts)


def stream_chat(
    messages: list,
    context_text: str = "",
    model_name: str = None,
    language: str = "zh",
    system_prompt: str = None,
):
    """
    流式对话。自动根据 settings 中的 provider 选择对应的 AI 提供商。
    messages:     [{"role": "user"|"assistant", "content": str}, ...]
    context_text: AI 摘录结果文本，直接作为对话上下文
    model_name:   模型 ID（为空时从 settings 读取）
    language:     "zh", "en", "mixed"
    system_prompt: 自定义 system prompt
    """
    settings = load_settings(SETTINGS_FILE)

    if system_prompt:
        sys_prompt = system_prompt
    elif language == "en":
        sys_prompt = CHAT_SYSTEM_PROMPT_EN
    else:
        sys_prompt = CHAT_SYSTEM_PROMPT

    if context_text and context_text.strip():
        sys_prompt += f"\n\n以下是检索引擎从历史文献中提取的相关摘录（供你分析讨论用）：\n\n{context_text}"

    _model_name = model_name or get_extraction_model(settings)

    try:
        provider = create_provider(settings, model_override=_model_name)
        yield from provider.chat_stream(
            messages=messages,
            system_prompt=sys_prompt,
            temperature=0.7,
            max_tokens=4096,
        )
    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        yield f"\n\n出错了：{e}"
