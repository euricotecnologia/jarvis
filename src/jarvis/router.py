from __future__ import annotations

from dataclasses import replace
from typing import AsyncIterator

from jarvis.config import AppConfig
from jarvis.errors import NoProviderAvailable, ProviderUnavailable
from jarvis.models import LLMRequest, LLMResponse
from jarvis.providers.base import LLMProvider
from jarvis.providers.factory import create_provider


class ModelRouter:
    def __init__(
        self,
        config: AppConfig,
        providers: dict[str, LLMProvider] | None = None,
    ) -> None:
        self.config = config
        self.providers = providers or {
            name: create_provider(provider_config)
            for name, provider_config in config.providers.items()
            if provider_config.enabled
        }

    def _candidates(self, requested: str | None) -> list[str]:
        if requested:
            provider_config = self.config.providers.get(requested)
            if provider_config is None:
                raise ProviderUnavailable(f"Provedor desconhecido: {requested}")
            if not provider_config.enabled:
                raise ProviderUnavailable(f"Provedor desativado: {requested}")
            return [requested]

        ordered = [self.config.default_provider, *self.config.fallback_order]
        result: list[str] = []
        for name in ordered:
            if name not in result and name in self.providers:
                result.append(name)
        return result

    async def chat(
        self, request: LLMRequest, provider_name: str | None = None
    ) -> LLMResponse:
        failures: list[str] = []
        for name in self._candidates(provider_name):
            provider = self.providers.get(name)
            if provider is None:
                failures.append(f"{name}: não inicializado")
                continue
            try:
                return await provider.chat(request)
            except Exception as exc:
                # Modelo/endpoint que não aceita 'tools' devolve HTTP 400 —
                # tenta de novo sem ferramentas (padrão do OpenJarvis).
                if getattr(exc, "status_code", None) == 400 and request.tools:
                    try:
                        return await provider.chat(replace(request, tools=()))
                    except Exception as retry_exc:  # noqa: BLE001
                        exc = retry_exc
                failures.append(f"{name}: {exc}")
                if provider_name:
                    raise
        detail = "; ".join(failures) or "nenhum provedor habilitado"
        raise NoProviderAvailable(f"Nenhum provedor respondeu. {detail}")

    async def stream(
        self, request: LLMRequest, provider_name: str | None = None
    ) -> AsyncIterator[tuple[str, str, str]]:
        """Transmite `(delta, provedor, modelo)`.

        Streaming e so uma otimização: se falhar OU não produzir nada, cai para
        o `chat()` normal do mesmo provedor. Um turno nunca termina em silencio.
        Depois do primeiro token, um erro sobe direto (não da para recomecar).
        """
        failures: list[str] = []
        for name in self._candidates(provider_name):
            provider = self.providers.get(name)
            if provider is None:
                failures.append(f"{name}: não inicializado")
                continue

            emitted = False
            try:
                async for delta in provider.stream_chat(request):
                    if delta:
                        emitted = True
                        yield delta, name, provider.config.model
                if emitted:
                    return
                failures.append(f"{name}: streaming vazio")
            except Exception as stream_exc:  # noqa: BLE001
                if emitted:
                    raise
                failures.append(f"{name}: streaming falhou ({stream_exc})")

            # Streaming não entregou nada util -> tenta sem streaming.
            try:
                response = await provider.chat(request)
            except Exception as chat_exc:  # noqa: BLE001
                failures.append(f"{name}: {chat_exc}")
                if provider_name:
                    raise
                continue
            if response.content:
                yield response.content, name, response.model
            return

        detail = "; ".join(failures) or "nenhum provedor habilitado"
        raise NoProviderAvailable(f"Nenhum provedor respondeu. {detail}")

