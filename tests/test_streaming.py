import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from jarvis.assistant import JarvisAssistant
from jarvis.config import ProviderConfig, load_config
from jarvis.database import Database
from jarvis.models import LLMRequest, LLMResponse, Message
from jarvis.providers.openai_compatible import OpenAICompatibleProvider
from jarvis.router import ModelRouter


class FakeStreamHttp:
    def __init__(self, lines: list[str]) -> None:
        self.lines = lines
        self.calls: list[dict[str, Any]] = []

    async def request_json(self, *args, **kwargs):  # pragma: no cover - guard
        raise AssertionError("stream_chat nao deveria usar request_json")

    async def stream_sse(self, method, url, *, headers=None, payload=None, timeout=300):
        self.calls.append({"method": method, "url": url, "payload": payload})
        for line in self.lines:
            yield line


class FakeProvider:
    def __init__(self, name, deltas=None, error=None, model="modelo") -> None:
        self.name = name
        self._deltas = deltas or []
        self._error = error
        self.config = SimpleNamespace(model=model, name=name)

    async def stream_chat(self, request: LLMRequest):
        if self._error is not None and not self._deltas:
            raise self._error
        for delta in self._deltas:
            yield delta

    async def chat(self, request: LLMRequest):
        raise RuntimeError(f"{self.name}: sem caminho nao-streaming")


REQUEST = LLMRequest(messages=(Message(role="user", content="oi"),))


class StreamingTests(unittest.IsolatedAsyncioTestCase):
    async def test_openai_compatible_stream_parses_sse_deltas(self) -> None:
        http = FakeStreamHttp(
            [
                '{"choices":[{"delta":{"role":"assistant"}}]}',
                '{"choices":[{"delta":{"content":"Ola"}}]}',
                '{"choices":[{"delta":{"content":", mundo"}}]}',
                '{"choices":[{"delta":{},"finish_reason":"stop"}]}',
            ]
        )
        config = ProviderConfig(
            name="ollama",
            kind="ollama",
            enabled=True,
            model="qwen3",
            base_url="http://localhost:11434/v1",
        )
        provider = OpenAICompatibleProvider(config, http=http)
        deltas = [chunk async for chunk in provider.stream_chat(REQUEST)]
        self.assertEqual(deltas, ["Ola", ", mundo"])
        self.assertTrue(http.calls[0]["payload"]["stream"])
        self.assertEqual(
            http.calls[0]["url"], "http://localhost:11434/v1/chat/completions"
        )

    async def test_router_stream_falls_back_before_first_token(self) -> None:
        config = SimpleNamespace(
            default_provider="a",
            fallback_order=("a", "b"),
            providers={},
        )
        router = ModelRouter(
            config,  # type: ignore[arg-type]
            providers={
                "a": FakeProvider("a", error=RuntimeError("offline")),
                "b": FakeProvider("b", deltas=["oi ", "mundo"], model="b-1"),
            },
        )
        collected = [item async for item in router.stream(REQUEST)]
        self.assertEqual([text for text, _, _ in collected], ["oi ", "mundo"])
        self.assertEqual({name for _, name, _ in collected}, {"b"})

    async def test_router_stream_falls_back_to_non_streaming_same_provider(self) -> None:
        config = SimpleNamespace(
            default_provider="a", fallback_order=("a",), providers={}
        )

        class StreamBroken(FakeProvider):
            async def stream_chat(self, request):
                raise RuntimeError("SSE caiu")
                yield  # torna isto um gerador assincrono

            async def chat(self, request):
                return LLMResponse(
                    provider=self.name, model=self.config.model, content="via rest"
                )

        router = ModelRouter(
            config,  # type: ignore[arg-type]
            providers={"a": StreamBroken("a", model="a-1")},
        )
        collected = [item async for item in router.stream(REQUEST)]
        self.assertEqual(collected, [("via rest", "a", "a-1")])

    async def test_router_stream_does_not_fall_back_mid_stream(self) -> None:
        config = SimpleNamespace(
            default_provider="a", fallback_order=("a", "b"), providers={}
        )

        class Breaks(FakeProvider):
            async def stream_chat(self, request):
                yield "come"
                raise RuntimeError("conexao caiu")

        router = ModelRouter(
            config,  # type: ignore[arg-type]
            providers={
                "a": Breaks("a"),
                "b": FakeProvider("b", deltas=["nao usar"]),
            },
        )
        with self.assertRaises(RuntimeError):
            _ = [item async for item in router.stream(REQUEST)]

    async def test_assistant_ask_stream_persists_full_reply(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as directory:
            config = load_config(Path(directory) / "missing.toml")
            database = Database(Path(directory) / "jarvis.db")
            database.initialize()

            class FakeRouter:
                async def stream(self, request, provider_name=None):
                    for delta in ["Oi", ", ", "mundo"]:
                        yield delta, "fake", "modelo-x"

            assistant = JarvisAssistant(
                config, database=database, router=FakeRouter()
            )
            chunks = [
                chunk async for chunk in assistant.ask_stream("bom dia")
            ]
            stored = database.get_messages(assistant.active_conversation_id)

        self.assertEqual(chunks, ["Oi", ", ", "mundo"])
        self.assertIsNotNone(assistant.last_stream)
        self.assertEqual(assistant.last_stream.response.content, "Oi, mundo")
        self.assertEqual(assistant.last_stream.response.provider, "fake")
        self.assertEqual(stored[-1].role, "assistant")
        self.assertEqual(stored[-1].content, "Oi, mundo")

    async def test_memory_consolidation_triggers_every_third_turn(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as directory:
            config = load_config(Path(directory) / "missing.toml")
            database = Database(Path(directory) / "jarvis.db")
            database.initialize()

            class FakeRouter:
                async def stream(self, request, provider_name=None):
                    yield "ok", "fake", "m"

            assistant = JarvisAssistant(config, database=database, router=FakeRouter())
            spawned: list[int] = []
            assistant._spawn_consolidation = lambda msgs, prov: spawned.append(len(msgs))

            conv = None
            for i in range(6):
                async for _ in assistant.ask_stream(f"mensagem {i}", conversation_id=conv):
                    pass
                conv = assistant.active_conversation_id

        # turnos do usuário: 1..6 -> dispara em 3 e 6
        self.assertEqual(len(spawned), 2)


if __name__ == "__main__":
    unittest.main()
