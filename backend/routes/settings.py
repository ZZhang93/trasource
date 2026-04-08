"""
/api/settings — 全局设置读写端点（支持多 AI 提供商）
"""

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

import config
import core.settings_manager as sm

router = APIRouter()
logger = logging.getLogger("backend.settings")

SETTINGS_FILE = "settings.json"

# 默认值
_DEFAULTS = {
    "provider": "gemini",

    # Gemini
    "gemini_api_key": config.GEMINI_API_KEY,
    "gemini_model": config.GEMINI_MODEL,
    "gemini_expansion_model": "gemini-3-flash-preview",
    "gemini_extraction_model": "gemini-3-flash-preview",

    # Claude
    "claude_api_key": "",
    "claude_model": "claude-sonnet-4-6",
    "claude_expansion_model": "claude-haiku-4-5-20251001",
    "claude_extraction_model": "claude-sonnet-4-6",

    # OpenAI (ChatGPT)
    "openai_api_key": "",
    "openai_model": "gpt-4o",
    "openai_expansion_model": "gpt-4o-mini",
    "openai_extraction_model": "gpt-4o",

    # 本地模型 (OpenAI-compatible)
    "local_base_url": "http://localhost:11434/v1",
    "local_api_key": "",
    "local_model": "",
    "local_expansion_model": "",
    "local_extraction_model": "",

    "proxy_url": "",
    "top_k": config.TOP_K_FOR_LLM,
    "system_prompt_override": "",
    "expansion_prompt_override": "",
}

# 旧 settings.json 字段到新字段的迁移映射
_MIGRATION_MAP = {
    "api_key": "gemini_api_key",
    "model": "gemini_model",
    "expansion_model": "gemini_expansion_model",
    "extraction_model": "gemini_extraction_model",
}


def _get_settings() -> dict:
    s = sm.load_settings(SETTINGS_FILE)
    # 迁移旧字段名
    for old_key, new_key in _MIGRATION_MAP.items():
        if old_key in s and new_key not in s:
            s[new_key] = s.pop(old_key)
        elif old_key in s:
            s.pop(old_key)
    merged = {**_DEFAULTS, **s}
    return merged


def _mask_key(key: str) -> str:
    """脱敏显示 API Key"""
    if key and len(key) > 8:
        return key[:8] + "•" * (len(key) - 8)
    return key or ""


@router.get("/api/settings")
async def get_settings():
    """返回当前设置（所有 API Key 脱敏显示）"""
    s = _get_settings()
    s["gemini_api_key_masked"] = _mask_key(s.get("gemini_api_key", ""))
    s["claude_api_key_masked"] = _mask_key(s.get("claude_api_key", ""))
    s["openai_api_key_masked"] = _mask_key(s.get("openai_api_key", ""))
    s["local_api_key_masked"] = _mask_key(s.get("local_api_key", ""))
    # 不返回明文 key
    for k in ["gemini_api_key", "claude_api_key", "openai_api_key", "local_api_key"]:
        s.pop(k, None)
    return s


@router.get("/api/settings/models")
async def get_models():
    """返回各提供商的可用模型列表"""
    result = {}
    for provider, models in config.AVAILABLE_MODELS.items():
        result[provider] = [
            {"label": label, "value": value}
            for label, value in models.items()
        ]
    result["providers"] = [
        {"value": k, "label": v}
        for k, v in config.PROVIDER_LABELS.items()
    ]
    return result


class SettingsUpdateRequest(BaseModel):
    provider: Optional[str] = None

    gemini_api_key: Optional[str] = None
    gemini_model: Optional[str] = None
    gemini_expansion_model: Optional[str] = None
    gemini_extraction_model: Optional[str] = None

    claude_api_key: Optional[str] = None
    claude_model: Optional[str] = None
    claude_expansion_model: Optional[str] = None
    claude_extraction_model: Optional[str] = None

    openai_api_key: Optional[str] = None
    openai_model: Optional[str] = None
    openai_expansion_model: Optional[str] = None
    openai_extraction_model: Optional[str] = None

    local_base_url: Optional[str] = None
    local_api_key: Optional[str] = None
    local_model: Optional[str] = None
    local_expansion_model: Optional[str] = None
    local_extraction_model: Optional[str] = None

    proxy_url: Optional[str] = None
    top_k: Optional[int] = None
    system_prompt_override: Optional[str] = None
    expansion_prompt_override: Optional[str] = None


@router.put("/api/settings")
async def update_settings(req: SettingsUpdateRequest):
    """保存设置到 settings.json"""
    current = sm.load_settings(SETTINGS_FILE)
    merged = {**_DEFAULTS, **current}

    update = req.model_dump(exclude_none=True)
    for key, value in update.items():
        if key == "top_k":
            merged[key] = max(10, min(500, value))
        elif isinstance(value, str):
            merged[key] = value.strip()
        else:
            merged[key] = value

    # 清理旧字段
    for old_key in _MIGRATION_MAP:
        merged.pop(old_key, None)

    try:
        sm.save_settings(SETTINGS_FILE, merged)
    except Exception as e:
        logger.error(f"save_settings error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

    return {"saved": True}


@router.get("/api/settings/default-prompts")
async def get_default_prompts():
    """返回内置默认提示词，供前端展示参考"""
    from core.query_expander import EXPANSION_PROMPT
    return {
        "extraction_prompt": config.SYSTEM_PROMPT,
        "expansion_prompt": EXPANSION_PROMPT,
    }


class TestConnectionRequest(BaseModel):
    provider: str
    gemini_api_key: Optional[str] = None
    claude_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    local_base_url: Optional[str] = None
    local_api_key: Optional[str] = None
    model: Optional[str] = None


@router.post("/api/settings/test-connection")
async def test_connection(req: TestConnectionRequest):
    """测试 LLM 连接：发送一个简单请求验证配置是否正确"""
    from core.llm_provider import create_provider

    # 构建临时 settings 用于创建 provider
    temp_settings = {"provider": req.provider}
    if req.provider == "gemini":
        temp_settings["gemini_api_key"] = req.gemini_api_key or ""
        temp_settings["gemini_model"] = req.model or "gemini-2.5-flash"
    elif req.provider == "claude":
        temp_settings["claude_api_key"] = req.claude_api_key or ""
        temp_settings["claude_model"] = req.model or "claude-haiku-4-5-20251001"
    elif req.provider == "openai":
        temp_settings["openai_api_key"] = req.openai_api_key or ""
        temp_settings["openai_model"] = req.model or "gpt-4o-mini"
    elif req.provider == "openai_compatible":
        temp_settings["local_base_url"] = req.local_base_url or "http://localhost:11434/v1"
        temp_settings["local_api_key"] = req.local_api_key or ""
        temp_settings["local_model"] = req.model or ""

    try:
        provider = create_provider(temp_settings)
        result = provider.generate("Say hello in one word.", temperature=0.1, max_tokens=50)
        return {"success": True, "message": f"连接成功！模型回复：{result[:100]}"}
    except Exception as e:
        logger.error(f"Test connection failed: {e}", exc_info=True)
        return {"success": False, "message": f"连接失败：{str(e)[:200]}"}
