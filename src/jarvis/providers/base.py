from __future__ import annotations

from abc import ABC, abstractmethod
from typing import AsyncIterator

from jarvis.config import ProviderConfig
from jarvis.http import HttpClient, JsonHttpClient
from jarvis.models import LLMRequest, LLMResponse


class LLMProvider(ABC):
    def __init__(self, config: ProviderConfig, http: HttpClient | None = None) -> None:
        self.config = config
        self.http = http or JsonHttpClient()

    @property
    def name(self) -> str:
        return self.config.name

    @abstractmethod
    async def chat(self, request: LLMRequest) -> LLMResponse:
        raise NotImplementedError

    async def stream_chat(self, request: LLMRequest) -> AsyncIterator[str]:
        """Entrega a resposta em pedacos de texto.

        A implementação padrão apenas reaproveita `chat()` e emite o texto
        inteiro de uma vez; provedores que suportam SSE sobrescrevem isto.
        """
        response = await self.chat(request)
        if response.content:
            yield response.content

    @abstractmethod
    async def list_models(self) -> list[str]:
        raise NotImplementedError

    async def health_check(self) -> tuple[bool, str]:
        try:
            models = await self.list_models()
        except Exception as exc:  # a mensagem e parte do diagnostico da CLI
            return False, str(exc)
        if self.config.model in models:
            return True, f"online; modelo {self.config.model} disponível"
        sample = ", ".join(models[:5]) or "nenhum modelo listado"
        return False, f"online, mas o modelo {self.config.model} não foi encontrado ({sample})"

