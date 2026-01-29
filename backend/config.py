"""
Configuration module for Endstate backend.
Supports environment variables and config file overrides.
"""
import os
from dataclasses import dataclass, field
from typing import Literal
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass

import contextvars

# Context variables for request-scoped overrides
X_GEMINI_API_KEY = contextvars.ContextVar("x_gemini_api_key", default="")
X_OPENROUTER_API_KEY = contextvars.ContextVar("x_openrouter_api_key", default="")
X_OPENROUTER_MODEL = contextvars.ContextVar("x_openrouter_model", default="")
X_NEO4J_URI = contextvars.ContextVar("x_neo4j_uri", default="")
X_NEO4J_USERNAME = contextvars.ContextVar("x_neo4j_username", default="")
X_NEO4J_PASSWORD = contextvars.ContextVar("x_neo4j_password", default="")
X_LLM_PROVIDER = contextvars.ContextVar("x_llm_provider", default="")


@dataclass
class Neo4jConfig:
    """Neo4j database configuration."""
    _uri: str = field(default_factory=lambda: os.getenv("NEO4J_URI", "bolt://localhost:7687"))
    _username: str = field(default_factory=lambda: os.getenv("NEO4J_USERNAME", "neo4j"))
    _password: str = field(default_factory=lambda: os.getenv("NEO4J_PASSWORD", "password123"))
    database: str = field(default_factory=lambda: os.getenv("NEO4J_DATABASE", "neo4j"))

    @property
    def uri(self) -> str:
        override = X_NEO4J_URI.get()
        return override if override else self._uri

    @property
    def username(self) -> str:
        override = X_NEO4J_USERNAME.get()
        return override if override else self._username

    @property
    def password(self) -> str:
        override = X_NEO4J_PASSWORD.get()
        return override if override else self._password


@dataclass
class OllamaConfig:
    """Ollama (local LLM) configuration."""
    base_url: str = field(default_factory=lambda: os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))
    model: str = field(default_factory=lambda: os.getenv("OLLAMA_MODEL", "llama3.2"))
    temperature: float = 0.0
    timeout_seconds: float = field(default_factory=lambda: float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "600")))
    keep_alive: str = field(default_factory=lambda: os.getenv("OLLAMA_KEEP_ALIVE", "5m"))


@dataclass
class GeminiConfig:
    """Google Gemini API configuration."""
    _api_key: str = field(default_factory=lambda: os.getenv("GOOGLE_API_KEY", ""))
    model: str = field(default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite"))
    temperature: float = 0.0

    @property
    def api_key(self) -> str:
        override = X_GEMINI_API_KEY.get()
        return override if override else self._api_key


@dataclass
class OpenRouterConfig:
    """OpenRouter API configuration."""
    _api_key: str = field(default_factory=lambda: os.getenv("OPENROUTER_API_KEY", ""))
    model: str = field(default_factory=lambda: os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini"))
    base_url: str = "https://openrouter.ai/api/v1"
    temperature: float = 0.0

    @property
    def api_key(self) -> str:
        override = X_OPENROUTER_API_KEY.get()
        return override if override else self._api_key


@dataclass
class LLMConfig:
    """LLM provider configuration."""
    _provider: Literal["ollama", "gemini", "openrouter", "mock"] = field(
        default_factory=lambda: os.getenv("LLM_PROVIDER", "ollama")
    )
    ollama: OllamaConfig = field(default_factory=OllamaConfig)
    gemini: GeminiConfig = field(default_factory=GeminiConfig)
    openrouter: OpenRouterConfig = field(default_factory=OpenRouterConfig)
    timeout_seconds: float = field(default_factory=lambda: float(os.getenv("LLM_TIMEOUT_SECONDS", "600")))

    @property
    def provider(self) -> str:
        override = X_LLM_PROVIDER.get()
        return override if override else self._provider


@dataclass
class ChatConfig:
    """Chat service configuration."""
    history_max_messages: int = field(default_factory=lambda: int(os.getenv("CHAT_HISTORY_MAX_MESSAGES", "20")))


@dataclass
class Config:
    """Main configuration class."""
    neo4j: Neo4jConfig = field(default_factory=Neo4jConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    chat: ChatConfig = field(default_factory=ChatConfig)
    
    @classmethod
    def from_env(cls) -> "Config":
        """Create configuration from environment variables."""
        return cls()


# Global config instance
config = Config.from_env()
