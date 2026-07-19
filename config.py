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

# 各 AI 提供商可用模型列表 { 显示名: API ID }
# 仅作为内置默认/离线回退；设置页可从提供商 API 在线拉取最新列表。
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
        "Claude Sonnet 5":   "claude-sonnet-5",
        "Claude Opus 4.8":   "claude-opus-4-8",
    },
    "openai": {
        "GPT-4o Mini":  "gpt-4o-mini",
        "GPT-4o":       "gpt-4o",
        "GPT-5 Mini":   "gpt-5-mini",
        "GPT-5":        "gpt-5",
        "GPT-5.1":      "gpt-5.1",
    },
    "deepseek": {
        "DeepSeek Chat (V3)":     "deepseek-chat",
        "DeepSeek Reasoner (R1)": "deepseek-reasoner",
    },
    "kimi": {
        "Kimi Latest":      "kimi-latest",
        "Kimi K2":          "kimi-k2-0711-preview",
        "Kimi K2 Turbo":    "kimi-k2-turbo-preview",
        "Moonshot v1 32K":  "moonshot-v1-32k",
        "Moonshot v1 128K": "moonshot-v1-128k",
    },
}

# Provider 显示名
PROVIDER_LABELS = {
    "gemini": "Google Gemini",
    "claude": "Claude (Anthropic)",
    "openai": "ChatGPT (OpenAI)",
    "deepseek": "DeepSeek",
    "kimi": "Kimi (Moonshot AI)",
    "openai_compatible": "Local Model (Ollama / vLLM)",
}

# 设置持久化文件路径
SETTINGS_FILE = "settings.json"

# 安全阈值：超过此字符数则截断 Context（预留空间给 Prompt 和输出）
MAX_CONTEXT_CHARS = 1_500_000

# BM25 初筛：从数据库里捞出的候选记录上限
MAX_SEARCH_RESULTS = 5000

# 送给 Gemini 的记录数上限（取相关度最高的前 N 条）
TOP_K_FOR_LLM = 50

# 每个来源文件至少送给 AI 的记录数（多样性保底）
TOP_K_PER_SOURCE = 3

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

# System Prompt（内置默认，可在设置中自定义覆盖）
SYSTEM_PROMPT = """你是一位严谨的历史文献摘录员。下面提供一批带有出处信息（【文献信息】行）的历史文献片段。
你的任务：仔细阅读全部文献，把与用户查询主题相关的原文摘录出来。
必须遵守以下准则：
1. 穷尽提取：不要总结，不要概括，不要改写！发现多少条相关内容就摘录多少条，一条不漏。如果文献中有50处相关，你必须摘录50条。
2. 宽泛关联：直接相关与间接相关（背景、因果、人物、关联事件）都要提取。这批文献经过检索系统筛选，大概率包含有价值的信息，请尽力挖掘。
3. 忠实原文：摘录内容必须与原文逐字一致，不得增删改字，不得把多处原文拼接成一条。
4. 引用忠实：每条的引用信息必须逐字取自该片段的【文献信息】行，严禁自行推断、补全或编造日期、版面、标题。【文献信息】中缺哪项就写"不详"。
5. 排版：按日期先后排序；每条摘录独立成行，格式强制要求：
   原文摘录内容 ———— **[引用：日期 / 版面 / 标题]**
6. 直接输出摘录条目，不要任何开场白、结束语或总结分析。
7. 仅当所有文献与查询主题完全无关时，才输出"未找到符合要求的史料记录"。这种情况极为罕见，请慎重判断。"""

SYSTEM_PROMPT_EN = """You are a meticulous historical document transcription specialist.
Below are historical document excerpts, each with a source-information line (【文献信息】).
Your task: carefully read all documents and extract every passage relevant to the user's query.
Absolute rules:
1. Exhaustive extraction: Do NOT summarize, paraphrase, or rewrite. Extract every relevant passage verbatim — if there are 50, extract all 50.
2. Broad relevance: Extract both directly and indirectly related content (background, causation, related persons, connected events). These documents were pre-filtered by a retrieval system and very likely contain valuable information.
3. Verbatim fidelity: Excerpts must match the original text exactly; do not merge separate passages into one.
4. Citation fidelity: Citation fields must be copied verbatim from that excerpt's source-information line. Never infer, complete, or fabricate dates, pages, or titles; write "unknown" for missing fields.
5. Layout: Sort by date ascending; one excerpt per line, mandatory format:
   Verbatim excerpt ———— **[Citation: date / source / title]**
6. Output the excerpt entries directly — no preamble, closing remarks, or analysis.
7. Only output "No relevant historical records found" when ALL documents are completely unrelated. This is extremely rare — judge carefully."""

SYSTEM_PROMPT_MIXED = """你是一位严谨的历史文献摘录员，能够处理中文和英文文献。
You handle both Chinese and English historical documents.
下面提供一批带有出处信息（【文献信息】行）的历史文献片段（可能中英文混合）。
你的任务：仔细阅读全部文献，把与用户查询主题相关的原文摘录出来。
必须遵守以下准则：
1. 穷尽提取：不要总结、概括或改写，逐字摘录所有相关内容，一条不漏。
   Exhaustive extraction: extract every relevant passage verbatim.
2. 宽泛关联：直接与间接相关（背景、因果、人物、关联事件）都要提取。
   Broad relevance: include indirectly related content.
3. 引用忠实：引用信息必须逐字取自该片段的【文献信息】行，严禁编造日期、版面、标题，缺失项写"不详/unknown"。
   Citation fidelity: copy citations verbatim from the source-information line; never fabricate.
4. 排版：按日期排序，每条独立成行 / One excerpt per line, sorted by date:
   原文摘录内容 ———— **[引用：日期 / 版面 / 标题]**
5. 直接输出条目，不要开场白或总结 / No preamble or closing remarks.
6. 仅当所有文献与查询完全无关时，才输出"未找到符合要求的史料记录 / No relevant records found"。这种情况极为罕见，请慎重判断。"""
