import tempfile
import unittest
from pathlib import Path

from jarvis.config import AppConfig, ProviderConfig
from jarvis.errors import ProviderUnavailable
from jarvis.models import LLMRequest, LLMResponse, Message
from jarvis.providers.base import LLMProvider
from jarvis.router import ModelRouter


class StubProvider(LLMProvider):
    def __init__(self, config, response=None, error=None):
        super().__init__(config)
        self.response = response
        self.error = error

    async def chat(self, request):
        if self.error:
            raise self.error
        return self.response

    async def list_models(self):
        return [self.config.model]


class RouterTests(unittest.IsolatedAsyncioTestCase):
    async def test_falls_back_to_next_provider(self) -> None:
        configs = {
            name: ProviderConfig(
                name=name,
                kind="ollama",
                enabled=True,
                model="test",
                base_url="http://localhost",
            )
            for name in ("first", "second")
        }
        with tempfile.TemporaryDirectory() as directory:
            config = AppConfig(
                database_path=Path(directory) / "db.sqlite",
                default_provider="first",
                fallback_order=("first", "second"),
                system_prompt="teste",
                providers=configs,
            )
            providers = {
                "first": StubProvider(configs["first"], error=ProviderUnavailable("offline")),
                "second": StubProvider(
                    configs["second"],
                    response=LLMResponse(
                        provider="second", model="test", content="funcionou"
                    ),
                ),
            }
            router = ModelRouter(config, providers=providers)
            response = await router.chat(
                LLMRequest(messages=(Message(role="user", content="oi"),))
            )

        self.assertEqual(response.provider, "second")

    async def test_explicit_provider_does_not_fallback(self) -> None:
        provider_config = ProviderConfig(
            name="first",
            kind="ollama",
            enabled=True,
            model="test",
            base_url="http://localhost",
        )
        config = AppConfig(
            database_path=Path("unused.db"),
            default_provider="first",
            fallback_order=("first",),
            system_prompt="teste",
            providers={"first": provider_config},
        )
        router = ModelRouter(
            config,
            providers={
                "first": StubProvider(
                    provider_config, error=ProviderUnavailable("offline")
                )
            },
        )
        with self.assertRaises(ProviderUnavailable):
            await router.chat(
                LLMRequest(messages=(Message(role="user", content="oi"),)),
                provider_name="first",
            )

