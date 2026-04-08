# ============================================================
# 配置文件 config.py
# API Key 请通过 settings.json 或 .env 文件配置
# ============================================================

import os
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# 默认模型
GEMINI_MODEL = "gemini-3-flash-preview"
QUERY_EXPANSION_MODEL = "gemini-3-flash-preview"

# 各 AI 提供商可用模型列表 { 显示名: API ID }
AVAILABLE_MODELS = {
    "gemini": {
        "Gemini 2.5 Flash":              "gemini-2.5-flash",
        "Gemini 2.5 Pro":                "gemini-2.5-pro",
        "Gemini 3 Flash":                "gemini-3-flash-preview",
        "Gemini 3.1 Flash Lite Preview": "gemini-3.1-flash-lite-preview",
        "Gemini 3.1 Pro Preview":        "gemini-3.1-pro-preview",
    },
    "claude": {
        "Claude Haiku 4.5":  "claude-haiku-4-5-20251001",
        "Claude Sonnet 4.6": "claude-sonnet-4-6",
        "Claude Opus 4.6":   "claude-opus-4-6",
    },
    "openai": {
        "GPT-4o Mini":  "gpt-4o-mini",
        "GPT-4o":       "gpt-4o",
        "GPT-4.1":      "gpt-4.1",
        "GPT-4.1 Mini": "gpt-4.1-mini",
        "GPT-4.1 Nano": "gpt-4.1-nano",
        "o3 Mini":      "o3-mini",
    },
}

# Provider 显示名
PROVIDER_LABELS = {
    "gemini": "Google Gemini",
    "claude": "Claude (Anthropic)",
    "openai": "ChatGPT (OpenAI)",
    "openai_compatible": "Local Model (Ollama / vLLM)",
}

# 设置持久化文件路径
SETTINGS_FILE = "settings.json"

# AI 对话模型选项（向后兼容，不再用于 UI 下拉，但保留作回退）
CHAT_MODELS = {
    "Gemini 2.5 Pro": "gemini-2.5-pro",
    "Gemini 2.5 Flash": "gemini-2.5-flash",
    "Gemini 3 Flash": "gemini-3-flash-preview",
}
CHAT_DEFAULT_MODEL = "Gemini 2.5 Pro"
CHAT_MAX_HISTORY = 20

# 安全阈值：超过此字符数则截断 Context（预留空间给 Prompt 和输出）
MAX_CONTEXT_CHARS = 1_500_000

# BM25 初筛：从数据库里捞出的候选记录上限
MAX_SEARCH_RESULTS = 5000

# 送给 Gemini 的记录数上限（取相关度最高的前 N 条）
TOP_K_FOR_LLM = 50

# 每个来源文件至少送给 AI 的记录数（多样性保底）
TOP_K_PER_SOURCE = 3

# 每页显示记录数（分页浏览原始检索结果）
RECORDS_PER_PAGE = 20

# 数据库根目录
PROJECTS_DIR = "projects"

# 日志文件路径
LOG_FILE = "logs/app.log"

# CSV 列名映射（你的实际表头 → 程序内部统一名称）
CSV_COLUMN_MAP = {
    "年份": "year",
    "日期": "date",
    "报纸版次": "page",
    "标题": "title",
    "文本内容": "content",
}

# System Prompt（硬编码，不可从界面修改）
SYSTEM_PROMPT = """你是一位严谨的历史文献摘录员。以下为你提供了一批包含日期和版面信息的历史文献。
你的任务是：仔细阅读提供的所有文献，找出与用户查询主题相关的句子或段落。
必须遵守以下准则：
1. 穷尽提取：不要总结，不要概括！只要发现相关的内容，必须将原文一字不差地摘录下来。如果文献中有50处相关，你必须摘录50条，不许遗漏。
2. 宽泛关联：不仅提取直接相关的内容，也要提取间接相关的内容（如背景、因果、人物、事件关联）。用户提供的文献是经过检索系统筛选的，因此大概率包含有价值的信息，请尽力挖掘。
3. 原子化排版：每一条摘录必须独立成行。
4. 格式强制要求：
   [原文摘录内容] ———— [引用：日期 / 版面 / 标题]
5. 仅当所有文献与查询主题完全无关时，才返回"未找到符合要求的史料记录"。这种情况极为罕见，请慎重判断。"""

SYSTEM_PROMPT_EN = """You are a meticulous historical document transcription specialist.
Below are historical documents with dates and source information.
Your task: carefully read all provided documents and identify sentences or paragraphs relevant to the user's query.
Absolute rules:
1. Exhaustive extraction: Do NOT summarize or paraphrase! Extract every relevant passage verbatim. If there are 50 relevant passages, you must extract all 50. Do not omit any.
2. Broad relevance: Extract not only directly relevant content, but also indirectly related content (background, causation, related persons, connected events). The provided documents have been pre-filtered by a retrieval system and are very likely to contain valuable information — do your best to uncover it.
3. Atomic formatting: Each excerpt must be on its own line.
4. Mandatory format:
   [Verbatim excerpt] ———— [Citation: date / source / title]
5. Only return "No relevant historical records found" when ALL provided documents are completely unrelated to the query. This situation is extremely rare — judge carefully.
"""

SYSTEM_PROMPT_MIXED = """你是一位严谨的历史文献摘录员，能够处理中文和英文文献。
You handle both Chinese and English historical documents.
以下为你提供了一批包含日期和版面信息的历史文献（可能含中英文混合内容）。
你的任务是：仔细阅读提供的所有文献，找出与用户查询主题相关的句子或段落。
必须遵守以下准则：
1. 穷尽提取：不要总结，不要概括！只要发现相关的内容，必须将原文一字不差地摘录下来。如果文献中有50处相关，你必须摘录50条，不许遗漏。
   Exhaustive extraction: Do NOT summarize. Extract every relevant passage verbatim.
2. 宽泛关联：不仅提取直接相关的内容，也要提取间接相关的内容（如背景、因果、人物、事件关联）。用户提供的文献是经过检索系统筛选的，因此大概率包含有价值的信息，请尽力挖掘。
   Broad relevance: Also extract indirectly related content (background, causation, related persons, events).
3. 原子化排版：每一条摘录必须独立成行。
4. 格式强制要求 / Mandatory format:
   [原文摘录内容] ———— [引用：日期 / 版面 / 标题]
5. 仅当所有文献与查询主题完全无关时，才返回"未找到符合要求的史料记录 / No relevant records found"。这种情况极为罕见，请慎重判断。"""
