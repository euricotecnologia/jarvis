from __future__ import annotations

import json
from typing import Any, AsyncIterator

from jarvis.errors import ProviderError, ProviderUnavailable
from jarvis.models import LLMRequest, LLMResponse, ToolCall
from jarvis.providers.base import LLMProvider
from jarvis.providers.common import parse_arguments


class AnthropicProvider(LLMProvider):
    def _headers(self) -> dict[str, str]:
        key = self.config.api_key()
        if not key:
            raise ProviderUnavailable(
                f"Defina a variavel {self.config.api_key_env} para usar {self.name}."
            )
        return {"x-api-key": key, "anthropic-version": "2023-06-01"}

    def _build_payload(self, request: LLMRequest) -> dict[str, Any]:
        system = "\n\n".join(
            message.content
            for message in request.messages
            if message.role in {"system", "developer"}
        )
        messages: list[dict[str, Any]] = []
        for message in request.messages:
            if message.role == "tool":
                messages.append(
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": message.tool_call_id or "",
                                "content": message.content,
                            }
                        ],
                    }
                )
            elif message.role == "assistant" and message.tool_calls:
                blocks: list[dict[str, Any]] = []
                if message.content:
                    blocks.append({"type": "text", "text": message.content})
                for call in message.tool_calls:
                    blocks.append(
                        {
                            "type": "tool_use",
                            "id": call.id,
                            "name": call.name,
                            "input": call.arguments,
                        }
                    )
                messages.append({"role": "assistant", "content": blocks})
            elif message.role in {"user", "assistant"}:
                messages.append(
                    {"role": message.role, "content": message.content}
                )
        payload: dict[str, Any] = {
            "model": self.config.model,
            "messages": messages,
            "max_tokens": request.max_output_tokens,
        }
        if system:
            payload["system"] = system
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        if request.tools:
            payload["tools"] = [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.parameters,
                }
                for tool in request.tools
            ]
            payload["tool_choice"] = {"type": "auto"}
        return payload

    async def stream_chat(self, request: LLMRequest) -> AsyncIterator[str]:
        payload = {**self._build_payload(request), "stream": True}
        async for data in self.http.stream_sse(
            "POST",
            f"{self.config.base_url}/messages",
            headers=self._headers(),
            payload=payload,
            timeout=self.config.timeout_seconds,
        ):
            try:
                event = json.loads(data)
            except json.JSONDecodeError:
                continue
            event_type = event.get("type")
            if event_type == "content_block_delta":
                delta = event.get("delta") or {}
                if delta.get("type") == "text_delta" and delta.get("text"):
                    yield delta["text"]
            elif event_type == "error":
                error = event.get("error") or {}
                raise ProviderError(
                    f"Anthropic: {error.get('message', 'erro no streaming')}"
                )

    async def chat(self, request: LLMRequest) -> LLMResponse:
        payload = self._build_payload(request)

        data = await self.http.request_json(
            "POST",
            f"{self.config.base_url}/messages",
            headers=self._headers(),
            payload=payload,
            timeout=self.config.timeout_seconds,
        )
        text_parts: list[str] = []
        calls: list[ToolCall] = []
        for block in data.get("content", []):
            if block.get("type") == "text":
                text_parts.append(str(block.get("text", "")))
            elif block.get("type") == "tool_use":
                calls.append(
                    ToolCall(
                        id=str(block.get("id", "")),
                        name=str(block.get("name", "")),
                        arguments=parse_arguments(block.get("input", {})),
                    )
                )
        usage_data = data.get("usage", {})
        usage = {
            key: int(value)
            for key, value in usage_data.items()
            if isinstance(value, (int, float))
        }
        return LLMResponse(
            provider=self.name,
            model=str(data.get("model", self.config.model)),
            content="\n".join(part for part in text_parts if part),
            tool_calls=tuple(calls),
            usage=usage,
            raw=data,
        )

    async def list_models(self) -> list[str]:
        data = await self.http.request_json(
            "GET",
            f"{self.config.base_url}/models",
            headers=self._headers(),
            timeout=min(self.config.timeout_seconds, 10),
        )
        return [str(item["id"]) for item in data.get("data", []) if "id" in item]

