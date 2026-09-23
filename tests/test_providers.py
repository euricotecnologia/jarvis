import os
import unittest
from typing import Any
from unittest.mock import patch

from jarvis.config import ProviderConfig
from jarvis.models import LLMRequest, Message, ToolDefinition
from jarvis.providers.anthropic import AnthropicProvider
from jarvis.providers.openai import OpenAIProvider
from jarvis.providers.openai_compatible import OpenAICompatibleProvider


class FakeHttp:
    def __init__(self, response: dict[str, Any]) -> None:
        self.response = response
        self.calls: list[dict[str, Any]] = []

    async def request_json(self, method, url, **kwargs):
        self.calls.append({"method": method, "url": url, **kwargs})
        return self.response


TOOL = ToolDefinition(
    name="get_time",
    description="Consulta a hora",
    parameters={"type": "object", "properties": {}, "additionalProperties": False},
)
REQUEST = LLMRequest(
    messages=(
        Message(role="system", content="Responda em portugues."),
        Message(role="user", content="Que horas sao?"),
    ),
    tools=(TOOL,),
)


class ProviderTests(unittest.IsolatedAsyncioTestCase):
    async def test_openai_responses_is_normalized(self) -> None:
        http = FakeHttp(
            {
                "model": "gpt-test",
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": "Agora."}],
                    },
                    {
                        "type": "function_call",
                        "call_id": "call-1",
                        "name": "get_time",
                        "arguments": "{}",
                    },
                ],
                "usage": {"input_tokens": 10, "output_tokens": 2},
            }
        )
        config = ProviderConfig(
            name="openai",
            kind="openai",
            enabled=True,
            model="gpt-test",
            base_url="https://api.openai.com/v1",
            api_key_env="TEST_OPENAI_KEY",
        )
        with patch.dict(os.environ, {"TEST_OPENAI_KEY": "secret"}):
            response = await OpenAIProvider(config, http=http).chat(REQUEST)

        self.assertEqual(response.content, "Agora.")
        self.assertEqual(response.tool_calls[0].name, "get_time")
        payload = http.calls[0]["payload"]
        self.assertEqual(payload["instructions"], "Responda em portugues.")
        self.assertEqual(payload["tools"][0]["name"], "get_time")
        self.assertFalse(payload["store"])

    async def test_openai_gpt35_uses_supported_responses_endpoint(self) -> None:
        http = FakeHttp(
            {
                "model": "gpt-3.5-turbo",
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": "Ola."}],
                    }
                ],
            }
        )
        config = ProviderConfig(
            name="openai",
            kind="openai",
            enabled=True,
            model="gpt-3.5-turbo",
            base_url="https://api.openai.com/v1",
            api_key_env="TEST_OPENAI_KEY",
        )
        with patch.dict(os.environ, {"TEST_OPENAI_KEY": "secret"}):
            response = await OpenAIProvider(config, http=http).chat(REQUEST)

        self.assertEqual(response.content, "Ola.")
        self.assertEqual(http.calls[0]["url"], "https://api.openai.com/v1/responses")

    async def test_openai_compatible_payload_and_tool_call(self) -> None:
        http = FakeHttp(
            {
                "model": "qwen3",
                "choices": [
                    {
                        "message": {
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": "call-2",
                                    "function": {
                                        "name": "get_time",
                                        "arguments": "{}",
                                    },
                                }
                            ],
                        }
                    }
                ],
            }
        )
        config = ProviderConfig(
            name="ollama",
            kind="ollama",
            enabled=True,
            model="qwen3",
            base_url="http://localhost:11434/v1",
        )
        response = await OpenAICompatibleProvider(config, http=http).chat(REQUEST)
        self.assertEqual(response.tool_calls[0].id, "call-2")
        self.assertEqual(
            http.calls[0]["payload"]["tools"][0]["function"]["name"], "get_time"
        )

    async def test_tool_result_messages_are_serialized_per_provider(self) -> None:
        from jarvis.models import ToolCall
        from jarvis.providers.anthropic import AnthropicProvider

        convo = LLMRequest(
            messages=(
                Message(role="user", content="que horas sao?"),
                Message(
                    role="assistant",
                    content="",
                    tool_calls=(ToolCall(id="t1", name="get_time", arguments={}),),
                ),
                Message(role="tool", tool_call_id="t1", name="get_time", content="15:04"),
            )
        )

        oc = FakeHttp({"model": "m", "choices": [{"message": {"content": "Sao 15:04."}}]})
        await OpenAICompatibleProvider(
            ProviderConfig(
                name="ollama", kind="ollama", enabled=True, model="m",
                base_url="http://x/v1",
            ),
            http=oc,
        ).chat(convo)
        msgs = oc.calls[0]["payload"]["messages"]
        self.assertEqual(msgs[1]["tool_calls"][0]["id"], "t1")
        self.assertEqual(msgs[2]["role"], "tool")
        self.assertEqual(msgs[2]["tool_call_id"], "t1")

        oa = FakeHttp({"model": "m", "output": []})
        with patch.dict(os.environ, {"TEST_OPENAI_KEY": "k"}):
            await OpenAIProvider(
                ProviderConfig(
                    name="openai", kind="openai", enabled=True, model="m",
                    base_url="https://api.openai.com/v1", api_key_env="TEST_OPENAI_KEY",
                ),
                http=oa,
            ).chat(convo)
        items = oa.calls[0]["payload"]["input"]
        self.assertTrue(any(i.get("type") == "function_call" for i in items))
        self.assertTrue(any(i.get("type") == "function_call_output" for i in items))

        an = FakeHttp({"model": "m", "content": [{"type": "text", "text": "ok"}]})
        with patch.dict(os.environ, {"TEST_ANTHROPIC_KEY": "k"}):
            await AnthropicProvider(
                ProviderConfig(
                    name="claude", kind="anthropic", enabled=True, model="m",
                    base_url="https://api.anthropic.com/v1",
                    api_key_env="TEST_ANTHROPIC_KEY",
                ),
                http=an,
            ).chat(convo)
        amsgs = an.calls[0]["payload"]["messages"]
        self.assertEqual(amsgs[1]["content"][0]["type"], "tool_use")
        self.assertEqual(amsgs[2]["content"][0]["type"], "tool_result")

    async def test_anthropic_messages_is_normalized(self) -> None:
        http = FakeHttp(
            {
                "model": "claude-test",
                "content": [
                    {"type": "text", "text": "Vou verificar."},
                    {"type": "tool_use", "id": "tool-1", "name": "get_time", "input": {}},
                ],
                "usage": {"input_tokens": 8, "output_tokens": 3},
            }
        )
        config = ProviderConfig(
            name="claude",
            kind="anthropic",
            enabled=True,
            model="claude-test",
            base_url="https://api.anthropic.com/v1",
            api_key_env="TEST_ANTHROPIC_KEY",
        )
        with patch.dict(os.environ, {"TEST_ANTHROPIC_KEY": "secret"}):
            response = await AnthropicProvider(config, http=http).chat(REQUEST)

        self.assertEqual(response.content, "Vou verificar.")
        self.assertEqual(response.tool_calls[0].id, "tool-1")
        payload = http.calls[0]["payload"]
        self.assertEqual(payload["system"], "Responda em portugues.")
        self.assertEqual(payload["tools"][0]["input_schema"]["type"], "object")
