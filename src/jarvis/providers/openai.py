from __future__ import annotations

import json
from typing import Any, AsyncIterator

from jarvis.errors import ProviderError, ProviderUnavailable
from jarvis.models import LLMRequest, LLMResponse, ToolCall
from jarvis.providers.base import LLMProvider
from jarvis.providers.common import parse_arguments


class OpenAIProvider(LLMProvider):
    def _headers(self) -> dict[str, str]:
        key = self.config.api_key()
        if not key:
            raise ProviderUnavailable(
                f"Defina a variavel {self.config.api_key_env} para usar {self.name}."
            )
        return {"Authorization": f"Bearer {key}"}

    def _build_payload(self, request: LLMRequest) -> dict[str, Any]:
        instructions = "\n\n".join(
            message.content
            for message in request.messages
            if message.role in {"system", "developer"}
        )
        input_messages: list[dict[str, Any]] = []
        for message in request.messages:
            if message.role in {"system", "developer"}:
                continue
            if message.role == "tool":
                input_messages.append(
                    {
                        "type": "function_call_output",
                        "call_id": message.tool_call_id or "",
                        "output": message.content,
                    }
                )
                continue
            if message.role == "assistant" and message.tool_calls:
                if message.content:
                    input_messages.append(
                        {"role": "assistant", "content": message.content}
                    )
                for call in message.tool_calls:
                    input_messages.append(
                        {
                            "type": "function_call",
                            "call_id": call.id,
                            "name": call.name,
                            "arguments": json.dumps(
                                call.arguments, ensure_ascii=False
                            ),
                        }
                    )
                continue
            input_messages.append(
                {"role": message.role, "content": message.content}
            )
        payload: dict[str, Any] = {
            "model": self.config.model,
            "input": input_messages,
            "max_output_tokens": request.max_output_tokens,
            "store": False,
        }
        if instructions:
            payload["instructions"] = instructions
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        if request.tools:
            payload["tools"] = [
                {
                    "type": "function",
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                    "strict": False,
                }
                for tool in request.tools
            ]
            payload["tool_choice"] = "auto"
        return payload

    async def stream_chat(self, request: LLMRequest) -> AsyncIterator[str]:
        payload = {**self._build_payload(request), "stream": True}
        async for data in self.http.stream_sse(
            "POST",
            f"{self.config.base_url}/responses",
            headers=self._headers(),
            payload=payload,
            timeout=self.config.timeout_seconds,
        ):
            try:
                event = json.loads(data)
            except json.JSONDecodeError:
                continue
            event_type = event.get("type")
            if event_type == "response.output_text.delta":
                delta = event.get("delta")
                if delta:
                    yield delta
            elif event_type in {
                "response.failed",
                "response.incomplete",
                "response.error",
                "error",
            }:
                response = event.get("response") or {}
                detail = (
                    event.get("message")
                    or (response.get("error") or {}).get("message")
                    or (response.get("incomplete_details") or {}).get("reason")
                    or event.get("code")
                    or json.dumps(event)[:200]
                )
                raise ProviderError(f"A OpenAI não concluiu a resposta: {detail}")

    async def chat(self, request: LLMRequest) -> LLMResponse:
        payload = self._build_payload(request)

        data = await self.http.request_json(
            "POST",
            f"{self.config.base_url}/responses",
            headers=self._headers(),
            payload=payload,
            timeout=self.config.timeout_seconds,
        )
        text_parts: list[str] = []
        calls: list[ToolCall] = []
        for item in data.get("output", []):
            if item.get("type") == "message":
                for content in item.get("content", []):
                    if content.get("type") in {"output_text", "text"}:
                        text_parts.append(str(content.get("text", "")))
            elif item.get("type") == "function_call":
                calls.append(
                    ToolCall(
                        id=str(item.get("call_id") or item.get("id", "")),
                        name=str(item.get("name", "")),
                        arguments=parse_arguments(item.get("arguments", {})),
                    )
                )
        if not text_parts and not calls and data.get("status") == "failed":
            raise ProviderError(f"A OpenAI não concluiu a resposta: {data.get('error')}")
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

