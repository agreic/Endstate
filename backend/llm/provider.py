"""
LLM provider module for Endstate.
Supports Ollama (local) and Gemini (API) providers.
"""
from typing import Optional, Union
from enum import Enum

from langchain_core.language_models import BaseChatModel

from ..config import LLMConfig, config


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    OLLAMA = "ollama"
    GEMINI = "gemini"
    MOCK = "mock"


def get_llm(
    provider: Optional[Union[str, LLMProvider]] = None,
    llm_config: Optional[LLMConfig] = None,
    **kwargs,
) -> BaseChatModel:
    """
    Get an LLM instance based on provider.
    
    Args:
        provider: LLM provider ("ollama", "gemini", or "mock"). Uses config default if not specified.
        llm_config: Optional config override. Uses global config if not provided.
        **kwargs: Additional arguments passed to the LLM constructor.
        
    Returns:
        LangChain chat model instance.
        
    Raises:
        ValueError: If provider is not supported or API key is missing.
    """
    llm_config = llm_config or config.llm
    provider = provider or llm_config.provider
    
    if isinstance(provider, str):
        provider = LLMProvider(provider.lower())
    
    if provider == LLMProvider.OLLAMA:
        return _get_ollama_llm(llm_config, **kwargs)
    elif provider == LLMProvider.GEMINI:
        return _get_gemini_llm(llm_config, **kwargs)
    elif provider == LLMProvider.MOCK:
        from backend.llm.mock_provider import MockLLM
        return MockLLM()
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")


def _get_ollama_llm(llm_config: LLMConfig, **kwargs) -> BaseChatModel:
    """Get Ollama LLM instance."""
    from langchain_ollama import ChatOllama
    
    ollama_config = llm_config.ollama
    timeout = kwargs.get("timeout_seconds", llm_config.timeout_seconds)
    keep_alive = kwargs.get("keep_alive", ollama_config.keep_alive)
    
    return ChatOllama(
        model=kwargs.get("model", ollama_config.model),
        base_url=kwargs.get("base_url", ollama_config.base_url),
        temperature=kwargs.get("temperature", ollama_config.temperature),
        keep_alive=keep_alive,
        sync_client_kwargs={"timeout": timeout},
        async_client_kwargs={"timeout": timeout},
        **{k: v for k, v in kwargs.items() if k not in ["model", "base_url", "temperature", "timeout", "timeout_seconds", "keep_alive"]},
    )


def _get_gemini_llm(llm_config: LLMConfig, **kwargs) -> BaseChatModel:
    """Get Gemini LLM instance."""
    from langchain_google_genai import ChatGoogleGenerativeAI
    from ..config import X_GEMINI_API_KEY
    
    gemini_config = llm_config.gemini
    
    # Check for API key
    # Priority: explicit kwargs > request context (X-Gemini-API-Key) > environment config
    context_api_key = X_GEMINI_API_KEY.get()
    api_key = kwargs.get("api_key") or context_api_key or gemini_config.api_key
    if not api_key:
        raise ValueError(
            "Gemini API key not found. Set GOOGLE_API_KEY environment variable, "
            "provide it in the request headers, or pass api_key parameter."
        )
    
    return ChatGoogleGenerativeAI(
        model=kwargs.get("model", gemini_config.model),
        temperature=kwargs.get("temperature", gemini_config.temperature),
        google_api_key=api_key,
        **{k: v for k, v in kwargs.items() if k not in ["model", "temperature", "api_key", "timeout", "google_api_key"]},
    )


def test_llm(llm: BaseChatModel) -> tuple[bool, str]:
    """
    Test an LLM connection.
    
    Args:
        llm: LLM instance to test.
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        response = llm.invoke("Say hello in one word")
        return True, response.content
    except Exception as e:
        return False, str(e)
