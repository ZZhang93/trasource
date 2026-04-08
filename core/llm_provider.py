# ============================================================
# core/llm_provider.py
# 多 AI 提供商抽象层：Gemini / Claude / OpenAI / 本地模型
# ============================================================

import logging
from abc import ABC, abstractmethod
from typing import Generator, Optional, List, Dict

logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    """所有 LLM 提供商的统一接口。"""

    @abstractmethod
    def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 8192,
    ) -> Generator[str, None, None]:
        """流式文本生成，逐块 yield 文本。"""
        ...

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 8192,
    ) -> str:
        """非流式生成，返回完整文本。"""
        ...

    @abstractmethod
    def chat_stream(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> Generator[str, None, None]:
        """流式对话。messages: [{"role": "user"|"assistant", "content": "..."}]"""
        ...


# ──────────────────────────────────────────────
# Google Gemini
# ──────────────────────────────────────────────

class GeminiProvider(LLMProvider):

    def __init__(self, api_key: str, model_name: str, proxy_url: str = ""):
        import google.generativeai as genai
        self.genai = genai
        if proxy_url:
            import os
            os.environ["HTTPS_PROXY"] = proxy_url
        genai.configure(api_key=api_key)
        self.model_name = model_name

    def _iter_text(self, response) -> Generator[str, None, None]:
        """从 Gemini 响应中提取文本，跳过 thinking 块。"""
        for chunk in response:
            try:
                parts = chunk.candidates[0].content.parts
                for part in parts:
                    if getattr(part, 'thought', False):
                        continue
                    text = getattr(part, 'text', None)
                    if text:
                        yield text
            except (AttributeError, IndexError):
                if hasattr(chunk, 'text') and chunk.text:
                    yield chunk.text

    def _extract_text(self, response) -> str:
        """从非流式 Gemini 响应中提取完整文本。"""
        try:
            parts = response.candidates[0].content.parts
            texts = []
            for part in parts:
                if getattr(part, 'thought', False):
                    continue
                text = getattr(part, 'text', None)
                if text:
                    texts.append(text)
            if texts:
                return "\n".join(texts).strip()
        except Exception:
            pass
        try:
            return response.text.strip()
        except Exception:
            raise RuntimeError("无法从 Gemini 响应中提取文本")

    def generate_stream(self, prompt, system_prompt=None, temperature=0.1, max_tokens=8192):
        model = self.genai.GenerativeModel(
            model_name=self.model_name,
            system_instruction=system_prompt,
        )
        response = model.generate_content(
            prompt,
            stream=True,
            generation_config=self.genai.types.GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=temperature,
            ),
        )
        yield from self._iter_text(response)

    def generate(self, prompt, system_prompt=None, temperature=0.1, max_tokens=8192):
        model = self.genai.GenerativeModel(
            model_name=self.model_name,
            system_instruction=system_prompt,
        )
        response = model.generate_content(
            prompt,
            generation_config=self.genai.types.GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=temperature,
            ),
        )
        return self._extract_text(response)

    def chat_stream(self, messages, system_prompt=None, temperature=0.7, max_tokens=4096):
        model = self.genai.GenerativeModel(
            model_name=self.model_name,
            system_instruction=system_prompt,
        )
        history = []
        for msg in messages[:-1]:
            role = "user" if msg["role"] == "user" else "model"
            history.append({"role": role, "parts": [msg["content"]]})
        chat = model.start_chat(history=history)
        response = chat.send_message(
            messages[-1]["content"],
            stream=True,
            generation_config=self.genai.types.GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=temperature,
            ),
        )
        yield from self._iter_text(response)


# ──────────────────────────────────────────────
# Anthropic Claude
# ──────────────────────────────────────────────

class ClaudeProvider(LLMProvider):

    def __init__(self, api_key: str, model_name: str, proxy_url: str = ""):
        import anthropic
        kwargs = {"api_key": api_key}
        if proxy_url:
            import httpx
            kwargs["http_client"] = httpx.Client(proxy=proxy_url)
        self.client = anthropic.Anthropic(**kwargs)
        self.model_name = model_name

    def generate_stream(self, prompt, system_prompt=None, temperature=0.1, max_tokens=8192):
        kwargs = {
            "model": self.model_name,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system_prompt:
            kwargs["system"] = system_prompt
        with self.client.messages.stream(**kwargs) as stream:
            for text in stream.text_stream:
                yield text

    def generate(self, prompt, system_prompt=None, temperature=0.1, max_tokens=8192):
        kwargs = {
            "model": self.model_name,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system_prompt:
            kwargs["system"] = system_prompt
        response = self.client.messages.create(**kwargs)
        return response.content[0].text

    def chat_stream(self, messages, system_prompt=None, temperature=0.7, max_tokens=4096):
        kwargs = {
            "model": self.model_name,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": messages,
        }
        if system_prompt:
            kwargs["system"] = system_prompt
        with self.client.messages.stream(**kwargs) as stream:
            for text in stream.text_stream:
                yield text


# ──────────────────────────────────────────────
# OpenAI (ChatGPT) / OpenAI-Compatible (Ollama, vLLM, LM Studio)
# ──────────────────────────────────────────────

class OpenAIProvider(LLMProvider):
    """
    支持 OpenAI 官方 API 和任何兼容 API（Ollama, vLLM, LM Studio 等）。
    通过 base_url 参数区分：
      - 官方 ChatGPT: base_url=None (使用默认)
      - 本地模型:     base_url="http://localhost:11434/v1" 等
    """

    def __init__(self, api_key: str, model_name: str, base_url: str = None, proxy_url: str = ""):
        from openai import OpenAI
        import httpx
        kwargs = {}
        if base_url:
            kwargs["base_url"] = base_url
        kwargs["api_key"] = api_key or "not-needed"
        if proxy_url:
            kwargs["http_client"] = httpx.Client(proxy=proxy_url)
        self.client = OpenAI(**kwargs)
        self.model_name = model_name

    def _build_messages(self, prompt: str, system_prompt: str = None) -> list:
        msgs = []
        if system_prompt:
            msgs.append({"role": "system", "content": system_prompt})
        msgs.append({"role": "user", "content": prompt})
        return msgs

    def generate_stream(self, prompt, system_prompt=None, temperature=0.1, max_tokens=8192):
        messages = self._build_messages(prompt, system_prompt)
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    def generate(self, prompt, system_prompt=None, temperature=0.1, max_tokens=8192):
        messages = self._build_messages(prompt, system_prompt)
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content

    def chat_stream(self, messages, system_prompt=None, temperature=0.7, max_tokens=4096):
        oai_messages = []
        if system_prompt:
            oai_messages.append({"role": "system", "content": system_prompt})
        oai_messages.extend(messages)
        response = self.client.chat.completions.create(
            model=self.model_name,
            messages=oai_messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


# ──────────────────────────────────────────────
# 工厂函数
# ──────────────────────────────────────────────

def create_provider(settings: dict, model_override: str = None) -> LLMProvider:
    """
    根据 settings 创建对应的 LLM Provider 实例。

    settings["provider"] 取值:
      - "gemini"            → GeminiProvider
      - "claude"            → ClaudeProvider
      - "openai"            → OpenAIProvider (ChatGPT 官方)
      - "openai_compatible" → OpenAIProvider (本地模型, 自定义 base_url)
    """
    provider_type = settings.get("provider", "gemini")
    proxy_url = settings.get("proxy_url", "")

    if provider_type == "claude":
        return ClaudeProvider(
            api_key=settings.get("claude_api_key", ""),
            model_name=model_override or settings.get("claude_model", "claude-sonnet-4-6"),
            proxy_url=proxy_url,
        )

    elif provider_type == "openai":
        return OpenAIProvider(
            api_key=settings.get("openai_api_key", ""),
            model_name=model_override or settings.get("openai_model", "gpt-4o"),
            proxy_url=proxy_url,
        )

    elif provider_type == "openai_compatible":
        return OpenAIProvider(
            api_key=settings.get("local_api_key", ""),
            model_name=model_override or settings.get("local_model", ""),
            base_url=settings.get("local_base_url", "http://localhost:11434/v1"),
            proxy_url=proxy_url,
        )

    else:  # "gemini" (default)
        from config import GEMINI_API_KEY
        return GeminiProvider(
            api_key=settings.get("gemini_api_key") or GEMINI_API_KEY,
            model_name=model_override or settings.get("gemini_model", "gemini-3-flash-preview"),
            proxy_url=proxy_url,
        )


def get_expansion_model(settings: dict) -> str:
    """获取当前 provider 的扩展模型名。"""
    p = settings.get("provider", "gemini")
    if p == "gemini":
        return settings.get("gemini_expansion_model") or settings.get("gemini_model", "gemini-3-flash-preview")
    elif p == "claude":
        return settings.get("claude_expansion_model") or settings.get("claude_model", "claude-sonnet-4-6")
    elif p == "openai":
        return settings.get("openai_expansion_model") or settings.get("openai_model", "gpt-4o")
    elif p == "openai_compatible":
        return settings.get("local_expansion_model") or settings.get("local_model", "")
    return ""


def get_extraction_model(settings: dict) -> str:
    """获取当前 provider 的提取模型名。"""
    p = settings.get("provider", "gemini")
    if p == "gemini":
        return settings.get("gemini_extraction_model") or settings.get("gemini_model", "gemini-3-flash-preview")
    elif p == "claude":
        return settings.get("claude_extraction_model") or settings.get("claude_model", "claude-sonnet-4-6")
    elif p == "openai":
        return settings.get("openai_extraction_model") or settings.get("openai_model", "gpt-4o")
    elif p == "openai_compatible":
        return settings.get("local_extraction_model") or settings.get("local_model", "")
    return ""
