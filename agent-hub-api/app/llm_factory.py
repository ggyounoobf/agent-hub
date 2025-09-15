# app/llm_factory.py

from __future__ import annotations

from typing import Union, Optional
from llama_index.llms.azure_openai import AzureOpenAI
from llama_index.llms.ollama import Ollama
from llama_index.core.callbacks import CallbackManager

from app.config import (
    LLMProvider, LLM_PROVIDER,
    # Azure configs
    AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT,
    AZURE_OPENAI_DEPLOYMENT, AZURE_OPENAI_API_VERSION,
    # Llama/Ollama configs
    OLLAMA_BASE_URL, LLAMA3_MODEL, LLAMA3_CONTEXT_WINDOW,
    # Common configs
    LLM_TEMPERATURE, LLM_MAX_TOKENS, LLM_MAX_RETRIES, LLM_REQUEST_TIMEOUT,
)

from app.utils.logging import setup_logging

logger = setup_logging(__name__)

LLMLike = Union[AzureOpenAI, Ollama]


def _clamp(val: Optional[float | int], lo: float | int, hi: float | int, default: float | int):
    """Clamp config values with a sensible default if None/invalid."""
    try:
        if val is None:
            return default
        if isinstance(val, bool):  # avoid bools sneaking in
            return default
        return max(lo, min(hi, val))
    except Exception:
        return default


def create_llm(callback_manager: Optional[CallbackManager]) -> LLMLike:
    """Factory: build the configured LLM instance."""
    if LLM_PROVIDER == LLMProvider.AZURE_OPENAI:
        return create_azure_openai_llm(callback_manager)
    elif LLM_PROVIDER in (LLMProvider.LLAMA3, LLMProvider.OLLAMA):
        return create_llama3_llm(callback_manager)
    else:
        raise ValueError(f"Unsupported LLM provider: {LLM_PROVIDER}")


def create_azure_openai_llm(callback_manager: Optional[CallbackManager]) -> AzureOpenAI:
    """Create Azure OpenAI LLM instance (chat-completions) with rate limit optimization."""
    missing = [k for k, v in {
        "AZURE_OPENAI_API_KEY": AZURE_OPENAI_API_KEY,
        "AZURE_OPENAI_ENDPOINT": AZURE_OPENAI_ENDPOINT,
        "AZURE_OPENAI_DEPLOYMENT": AZURE_OPENAI_DEPLOYMENT,
        "AZURE_OPENAI_API_VERSION": AZURE_OPENAI_API_VERSION,
    }.items() if not v]
    if missing:
        raise ValueError(f"Missing Azure OpenAI config: {', '.join(missing)}")

    # 🚀 Rate limit optimized settings
    temp = float(_clamp(LLM_TEMPERATURE, 0.0, 2.0, 0.1))  # Lower temp for consistency
    max_tokens = int(_clamp(LLM_MAX_TOKENS, 1, 4096, 2048))  # Reduced from 8192
    timeout = int(_clamp(LLM_REQUEST_TIMEOUT, 10, 600, 120))  # Increased timeout for retries
    retries = int(_clamp(LLM_MAX_RETRIES, 1, 10, 5))  # More retries for rate limits

    # Do not log secrets
    logger.info("🔑 Using Azure OpenAI | endpoint=%s | deployment=%s | version=%s",
                AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_DEPLOYMENT, AZURE_OPENAI_API_VERSION)

    # Keep kwargs tight to avoid version drift issues
    llm = AzureOpenAI(
        model=AZURE_OPENAI_DEPLOYMENT,          # LlamaIndex accepts model=deployment for Azure
        engine=AZURE_OPENAI_DEPLOYMENT,         # engine kept for older versions
        temperature=temp,
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_key=AZURE_OPENAI_API_KEY,
        api_version=AZURE_OPENAI_API_VERSION,
        timeout=timeout,
        max_retries=retries,
        max_tokens=max_tokens,
        # Keep additional_kwargs minimal and standard
        additional_kwargs={
            "top_p": 0.95,
        },
        callback_manager=callback_manager,
    )
    return llm


def create_llama3_llm(callback_manager: Optional[CallbackManager]) -> Ollama:
    """Create Llama 3 LLM instance via Ollama."""
    if not (OLLAMA_BASE_URL and LLAMA3_MODEL):
        raise ValueError("Missing Ollama config: OLLAMA_BASE_URL and LLAMA3_MODEL must be set")

    temp = float(_clamp(LLM_TEMPERATURE, 0.0, 2.0, 0.2))
    max_tokens = int(_clamp(LLM_MAX_TOKENS, 1, 8192, 1024))
    timeout = int(_clamp(LLM_REQUEST_TIMEOUT, 5, 600, 60))

    logger.info("🦙 Using Ollama | base=%s | model=%s | context_window=%s",
                OLLAMA_BASE_URL, LLAMA3_MODEL, LLAMA3_CONTEXT_WINDOW or "default")

    # num_predict corresponds to output tokens in Ollama
    llm = Ollama(
        model=LLAMA3_MODEL,
        base_url=OLLAMA_BASE_URL,
        temperature=temp,
        context_window=LLAMA3_CONTEXT_WINDOW,
        request_timeout=timeout,
        callback_manager=callback_manager,
        additional_kwargs={
            "num_predict": max_tokens,
            "top_p": 0.95,
        },
    )
    return llm


def validate_llm_config() -> bool:
    """Validate LLM configuration based on selected provider."""
    if LLM_PROVIDER == LLMProvider.AZURE_OPENAI:
        return all([AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_DEPLOYMENT, AZURE_OPENAI_API_VERSION])
    elif LLM_PROVIDER in (LLMProvider.LLAMA3, LLMProvider.OLLAMA):
        return bool(OLLAMA_BASE_URL and LLAMA3_MODEL)
    return False


def get_llm_display_name() -> str:
    """A friendly name for logs/UI."""
    if LLM_PROVIDER == LLMProvider.AZURE_OPENAI:
        return f"AzureOpenAI:{AZURE_OPENAI_DEPLOYMENT}"
    elif LLM_PROVIDER in (LLMProvider.LLAMA3, LLMProvider.OLLAMA):
        return f"Ollama:{LLAMA3_MODEL}"
    return str(LLM_PROVIDER)
