from __future__ import annotations

import json
from typing import Any

from jarvis.models import Message, ToolCall, ToolDefinition


def parse_arguments(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {"value": parsed}
        except json.JSONDecodeError:
            return {"_raw": value}
    return {"value": value}


def openai_chat_messages(messages: tuple[Message, ...]) -> list[dict[str, Any]]:
    """Serializa mensagens para o formato /chat/completions, com ferramentas."""
    out: list[dict[str, Any]] = []
    for message in messages:
        if message.role == "tool":
            out.append(
                {
                    "role": "tool",
                    "tool_call_id": message.tool_call_id or "",
                    "content": message.content,
                }
            )
        elif message.role == "assistant" and message.tool_calls:
            out.append(
                {
                    "role": "assistant",
                    "content": message.content or None,
                    "tool_calls": [
                        {
                            "id": call.id,
                            "type": "function",
                            "function": {
                                "name": call.name,
                                "arguments": json.dumps(
                                    call.arguments, ensure_ascii=False
                                ),
                            },
                        }
                        for call in message.tool_calls
                    ],
                }
            )
        else:
            out.append({"role": message.role, "content": message.content})
    return out


def openai_chat_tools(tools: tuple[ToolDefinition, ...]) -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
            },
        }
        for tool in tools
    ]


def parse_openai_chat_tool_calls(items: list[dict[str, Any]] | None) -> tuple[ToolCall, ...]:
    calls: list[ToolCall] = []
    for index, item in enumerate(items or []):
        function = item.get("function", {})
        calls.append(
            ToolCall(
                id=str(item.get("id", f"call-{index}")),
                name=str(function.get("name", "")),
                arguments=parse_arguments(function.get("arguments", {})),
            )
        )
    return tuple(calls)

