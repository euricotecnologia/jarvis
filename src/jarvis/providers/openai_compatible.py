from __future__ import annotations

import json
from typing import Any, AsyncIterator

from jarvis.errors import ProviderError, ProviderUnavailable
from jarvis.models import LLMRequest, LLMResponse
from jarvis.providers.base import LLMProvider
from jarvis.providers.common import (
    openai_chat_messages,
    openai_chat_tools,
    parse_openai_chat_tool_calls,
)


class OpenAICompatibleProvider(LLMProvider):
    """Adaptador compartilhado por LM Studio e Ollama."""

    def _headers(self) -> dict[str, str]:
        key = self.config.api_key()
        if self.config.api_key_env and not key:
            raise ProviderUnavailable(
                f"Defina a variavel {self.config.api_key_env} para usar {self.name}."
            )
        return {"Authorization": f"Bearer {key or self.config.kind}"}

    async def chat(self, request: LLMRequest) -> LLMResponse:
        payload: dict[str, Any] = {
            "model": self.config.model,
            "messages": openai_chat_messages(request.messages),
            "max_tokens": request.max_output_tokens,
            "stream": False,
        }
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        if request.tools:
            payload["tools"] = openai_chat_tools(request.tools)
            payload["tool_choice"] = "auto"

        data = await self.http.request_json(
            "POST",
            f"{self.config.base_url}/chat/completions",
            headers=self._headers(),
            payload=payload,
            timeout=self.config.timeout_seconds,
        )
        try:
            message = data["choices"][0]["message"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError(f"Resposta inesperada de {self.name}") from exc

        usage_data = data.get("usage", {})
        usage = {
            key: int(value)
            for key, value in usage_data.items()
            if isinstance(value, (int, float))
        }
        return LLMResponse(
            provider=self.name,
            model=str(data.get("model", self.config.model)),
            content=str(message.get("content") or ""),
            tool_calls=parse_openai_chat_tool_calls(message.get("tool_calls")),
            usage=usage,
            raw=data,
        )

    async def stream_chat(self, request: LLMRequest) -> AsyncIterator[str]:
        payload: dict[str, Any] = {
            "model": self.config.model,
            "messages": openai_chat_messages(request.messages),
            "max_tokens": request.max_output_tokens,
            "stream": True,
        }
        if request.temperature is not None:
            payload["temperature"] = request.temperature

        async for data in self.http.stream_sse(
            "POST",
            f"{self.config.base_url}/chat/completions",
            headers=self._headers(),
            payload=payload,
            timeout=self.config.timeout_seconds,
        ):
            try:
                event = json.loads(data)
            except json.JSONDecodeError:
                continue
            error = event.get("error")
            if isinstance(error, dict):
                raise ProviderError(
                    f"{self.name}: {error.get('message', 'erro no streaming')}"
                )
            for choice in event.get("choices", []):
                delta = choice.get("delta") or {}
                text = delta.get("content")
                if text:
                    yield text

    async def list_models(self) -> list[str]:
        data = await self.http.request_json(
            "GET",
            f"{self.config.base_url}/models",
            headers=self._headers(),
            timeout=min(self.config.timeout_seconds, 10),
        )
        return [str(item["id"]) for item in data.get("data", []) if "id" in item]
