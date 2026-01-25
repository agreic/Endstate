"""
Unit tests for LLM provider module.
Tests focus on Ollama (local) as requested.
"""
import os
from unittest.mock import patch, MagicMock
import pytest

from backend.llm.provider import (
    LLMProvider,
    get_llm,
    _get_ollama_llm,
    _get_gemini_llm,
)
from backend.config import LLMConfig, OllamaConfig, GeminiConfig


class TestLLMProvider:
    """Tests for LLMProvider enum."""

    def test_ollama_value(self):
        """Test Ollama enum value."""
        assert LLMProvider.OLLAMA.value == "ollama"

    def test_gemini_value(self):
        """Test Gemini enum value."""
        assert LLMProvider.GEMINI.value == "gemini"

    def test_enum_is_string(self):
        """Test that enum inherits from string."""
        assert isinstance(LLMProvider.OLLAMA, str)


class TestGetLLM:
    """Tests for get_llm function."""

    @patch("backend.llm.provider._get_ollama_llm")
    def test_get_ollama_by_string(self, mock_get_ollama):
        """Test getting Ollama LLM with string provider."""
        mock_llm = MagicMock()
        mock_get_ollama.return_value = mock_llm

        llm = get_llm(provider="ollama")

        mock_get_ollama.assert_called_once()
        assert llm == mock_llm

    @patch("backend.llm.provider._get_ollama_llm")
    def test_get_ollama_by_enum(self, mock_get_ollama):
        """Test getting Ollama LLM with enum provider."""
        mock_llm = MagicMock()
        mock_get_ollama.return_value = mock_llm

        llm = get_llm(provider=LLMProvider.OLLAMA)

        mock_get_ollama.assert_called_once()
        assert llm == mock_llm

    @patch("backend.llm.provider._get_gemini_llm")
    def test_get_gemini_by_string(self, mock_get_gemini):
        """Test getting Gemini LLM with string provider."""
        mock_llm = MagicMock()
        mock_get_gemini.return_value = mock_llm

        llm = get_llm(provider="gemini")

        mock_get_gemini.assert_called_once()
        assert llm == mock_llm

    @patch("backend.llm.provider._get_gemini_llm")
    def test_get_gemini_by_enum(self, mock_get_gemini):
        """Test getting Gemini LLM with enum provider."""
        mock_llm = MagicMock()
        mock_get_gemini.return_value = mock_llm

        llm = get_llm(provider=LLMProvider.GEMINI)

        mock_get_gemini.assert_called_once()
        assert llm == mock_llm

    @patch("backend.llm.provider._get_ollama_llm")
    def test_default_provider_from_config(self, mock_get_ollama):
        """Test using default provider from config."""
        mock_llm = MagicMock()
        mock_get_ollama.return_value = mock_llm

        llm_config = LLMConfig(provider="ollama")
        llm = get_llm(llm_config=llm_config)

        mock_get_ollama.assert_called_once()
        assert llm == mock_llm

    @patch("backend.llm.provider._get_ollama_llm")
    def test_provider_case_insensitive(self, mock_get_ollama):
        """Test that provider names are case insensitive."""
        mock_llm = MagicMock()
        mock_get_ollama.return_value = mock_llm

        llm = get_llm(provider="OLLAMA")
        assert llm == mock_llm

    def test_unsupported_provider(self):
        """Test error on unsupported provider."""
        with pytest.raises(ValueError):
            get_llm(provider="unsupported")


class TestGetOllamaLLM:
    """Tests for _get_ollama_llm function."""

    @patch("langchain_ollama.ChatOllama")
    def test_ollama_with_defaults(self, mock_chat_ollama):
        """Test Ollama LLM with default configuration."""
        mock_instance = MagicMock()
        mock_chat_ollama.return_value = mock_instance

        llm_config = LLMConfig(
            provider="ollama",
            ollama=OllamaConfig(
                base_url="http://localhost:11434",
                model="llama3.2",
                temperature=0.0,
            ),
        )

        _get_ollama_llm(llm_config)

        mock_chat_ollama.assert_called_once()
        call_kwargs = mock_chat_ollama.call_args[1]
        assert call_kwargs["model"] == "llama3.2"
        assert call_kwargs["base_url"] == "http://localhost:11434"
        assert call_kwargs["temperature"] == 0.0

    @patch("langchain_ollama.ChatOllama")
    def test_ollama_with_custom_model(self, mock_chat_ollama):
        """Test Ollama LLM with custom model override."""
        mock_instance = MagicMock()
        mock_chat_ollama.return_value = mock_instance

        llm_config = LLMConfig(
            provider="ollama",
            ollama=OllamaConfig(model="llama3.2"),
        )

        _get_ollama_llm(llm_config, model="mistral")

        call_kwargs = mock_chat_ollama.call_args[1]
        assert call_kwargs["model"] == "mistral"

    @patch("langchain_ollama.ChatOllama")
    def test_ollama_with_custom_base_url(self, mock_chat_ollama):
        """Test Ollama LLM with custom base URL."""
        mock_instance = MagicMock()
        mock_chat_ollama.return_value = mock_instance

        llm_config = LLMConfig(
            provider="ollama",
            ollama=OllamaConfig(base_url="http://custom:11434"),
        )

        _get_ollama_llm(llm_config, base_url="http://override:11434")

        call_kwargs = mock_chat_ollama.call_args[1]
        assert call_kwargs["base_url"] == "http://override:11434"

    @patch("langchain_ollama.ChatOllama")
    def test_ollama_passes_extra_kwargs(self, mock_chat_ollama):
        """Test that extra kwargs are passed to ChatOllama."""
        mock_instance = MagicMock()
        mock_chat_ollama.return_value = mock_instance

        llm_config = LLMConfig(
            provider="ollama",
            ollama=OllamaConfig(model="llama3.2"),
        )

        _get_ollama_llm(llm_config, num_predict=100, top_k=50)

        call_kwargs = mock_chat_ollama.call_args[1]
        assert call_kwargs["num_predict"] == 100
        assert call_kwargs["top_k"] == 50


class TestGetGeminiLLM:
    """Tests for _get_gemini_llm function."""

    @patch("langchain_google_genai.ChatGoogleGenerativeAI")
    @patch.dict(os.environ, {"GOOGLE_API_KEY": "test_key_123"}, clear=False)
    def test_gemini_with_api_key_from_env(self, mock_chat_genai):
        """Test Gemini LLM with API key from environment."""
        mock_instance = MagicMock()
        mock_chat_genai.return_value = mock_instance

        llm_config = LLMConfig(
            provider="gemini",
            gemini=GeminiConfig(model="gemini-pro"),
        )

        _get_gemini_llm(llm_config)

        mock_chat_genai.assert_called_once()
        call_kwargs = mock_chat_genai.call_args[1]
        assert call_kwargs["model"] == "gemini-pro"

    @patch("langchain_google_genai.ChatGoogleGenerativeAI")
    @patch.dict(os.environ, {}, clear=False)
    def test_gemini_with_api_key_parameter(self, mock_chat_genai):
        """Test Gemini LLM with API key passed as parameter."""
        mock_instance = MagicMock()
        mock_chat_genai.return_value = mock_instance

        llm_config = LLMConfig(
            provider="gemini",
            gemini=GeminiConfig(model="gemini-pro"),
        )

        _get_gemini_llm(llm_config, api_key="param_key")

        # Verify ChatGoogleGenerativeAI was called (api_key is set via env var in _get_gemini_llm)
        mock_chat_genai.assert_called_once()

    @patch("langchain_google_genai.ChatGoogleGenerativeAI")
    def test_gemini_without_api_key_raises_error(self, mock_chat_genai):
        """Test that Gemini raises error without API key."""
        llm_config = LLMConfig(
            provider="gemini",
            gemini=GeminiConfig(_api_key=""),
        )

        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="API key not found"):
                _get_gemini_llm(llm_config)

    @patch("langchain_google_genai.ChatGoogleGenerativeAI")
    @patch.dict(os.environ, {}, clear=True)
    def test_gemini_with_custom_model(self, mock_chat_genai):
        """Test Gemini LLM with custom model override."""
        mock_instance = MagicMock()
        mock_chat_genai.return_value = mock_instance

        llm_config = LLMConfig(
            provider="gemini",
            gemini=GeminiConfig(
                _api_key="test_key",
                model="gemini-1.5-flash",
            ),
        )

        _get_gemini_llm(llm_config, model="gemini-ultra")

        call_kwargs = mock_chat_genai.call_args[1]
        assert call_kwargs["model"] == "gemini-ultra"


class TestTestLLM:
    """Tests for test_llm function (renamed to avoid pytest collection)."""

    def test_connection_success(self):
        """Test successful LLM connection test."""
        from backend.llm.provider import test_llm as test_llm_func

        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "Hello"
        mock_llm.invoke.return_value = mock_response

        success, message = test_llm_func(mock_llm)

        assert success is True
        assert message == "Hello"
        mock_llm.invoke.assert_called_once_with("Say hello in one word")

    def test_connection_failure(self):
        """Test failed LLM connection test."""
        from backend.llm.provider import test_llm as test_llm_func

        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = Exception("Connection timeout")

        success, message = test_llm_func(mock_llm)

        assert success is False
        assert "Connection timeout" in message
