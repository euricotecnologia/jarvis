from jarvis.config import ProviderConfig
from jarvis.errors import ConfigurationError
from jarvis.http import HttpClient
from jarvis.providers.anthropic import AnthropicProvider
from jarvis.providers.base import LLMProvider
from jarvis.providers.openai import OpenAIProvider
from jarvis.providers.openai_compatible import OpenAICompatibleProvider


def create_provider(
    config: ProviderConfig, http: HttpClient | None = None
) -> LLMProvider:
    if config.kind in {"ollama", "lmstudio", "openai-compatible", "gemini"}:
        return OpenAICompatibleProvider(config, http=http)
    if config.kind == "openai":
        return OpenAIProvider(config, http=http)
    if config.kind in {"anthropic", "claude"}:
        return AnthropicProvider(config, http=http)
    raise ConfigurationError(f"Tipo de provedor desconhecido: {config.kind}")
