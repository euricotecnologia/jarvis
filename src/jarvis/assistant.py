from __future__ import annotations

import asyncio
import threading
from typing import AsyncIterator, Awaitable, Callable

from jarvis.agent import (
    RESPONSE_STYLE,
    ToolAgent,
    build_agent_system_prompt,
    system_context,
)
from jarvis.cognition import CognitiveEngine
from jarvis.config import AppConfig
from jarvis.database import Database
from jarvis.models import AssistantReply, LLMRequest, LLMResponse, Message
from jarvis.router import ModelRouter
from jarvis.tools.context import ToolContext
from jarvis.tools.registry import build_tools

ConfirmFn = Callable[[str], Awaitable[bool]]
EventFn = Callable[[str, str], None]

# consolidação de memória por LLM: roda 1x a cada N turnos do usuário
_CONSOLIDATE_EVERY_TURNS = 3


async def _auto_deny(_message: str) -> bool:
    return False


MediaSink = Callable[[bytes, str, str], None]


class JarvisAssistant:
    def __init__(
        self,
        config: AppConfig,
        database: Database | None = None,
        router: ModelRouter | None = None,
        on_media: MediaSink | None = None,
    ) -> None:
        self.config = config
        self.database = database or Database(config.database_path)
        self.router = router or ModelRouter(config)
        self.cognition = CognitiveEngine(self.database)
        from jarvis.mcp import MCPManager

        self.mcp = MCPManager(self.database)
        self.active_conversation_id: int | None = None
        self.last_stream: AssistantReply | None = None
        self.on_media = on_media

    async def initialize(self) -> None:
        await asyncio.to_thread(self.database.initialize)
        await asyncio.to_thread(self.database.sync_providers, self.config.providers)

    def _make_vision(self):
        from jarvis import vision as vision_module

        provider = self.config.providers.get(self.config.default_provider)

        def look(question: str) -> tuple[str, bytes]:
            if provider is None:
                raise vision_module.VisionError("Nenhum provedor de IA configurado.")
            answer, frame = vision_module.describe_with_config(
                question, provider, self.config.vision
            )
            return answer, frame.jpeg

        return look

    def _make_describe_image(self):
        from jarvis import vision as vision_module

        provider = self.config.providers.get(self.config.default_provider)

        def describe(jpeg: bytes, question: str) -> str:
            if provider is None:
                raise vision_module.VisionError("Nenhum provedor de IA configurado.")
            frame = vision_module.Frame(jpeg=jpeg, width=0, height=0)
            return vision_module.describe_scene(
                question, frame, provider,
                timeout_seconds=self.config.vision.timeout_seconds,
            )

        return describe

    async def ask(
        self,
        text: str,
        *,
        conversation_id: int | None = None,
        provider_name: str | None = None,
    ) -> AssistantReply:
        if conversation_id is None:
            conversation_id = await asyncio.to_thread(
                self.database.create_conversation, text[:80]
            )
        await asyncio.to_thread(
            self.database.add_message,
            conversation_id,
            Message(role="user", content=text),
        )
        history = await asyncio.to_thread(self.database.get_messages, conversation_id)
        cog_ctx = self.cognition.build_cognitive_context(text)
        sys_prompt = f"{self.config.system_prompt}\n\n{cog_ctx}" if cog_ctx else self.config.system_prompt

        request = LLMRequest(
            messages=(Message(role="system", content=sys_prompt), *history)
        )
        response = await self.router.chat(request, provider_name=provider_name)
        await asyncio.to_thread(
            self.database.add_message,
            conversation_id,
            Message(role="assistant", content=response.content),
            provider=response.provider,
            model=response.model,
            metadata={"usage": response.usage},
        )
        # Aprendizado e extração cognitiva
        await asyncio.to_thread(self.cognition.process_user_turn, text, response.content)
        return AssistantReply(conversation_id=conversation_id, response=response)

    async def ask_stream(
        self,
        text: str,
        *,
        conversation_id: int | None = None,
        provider_name: str | None = None,
        confirm: ConfirmFn | None = None,
        on_event: EventFn | None = None,
    ) -> AsyncIterator[str]:
        """Versão em streaming de `ask`: emite o texto da resposta em pedacos.

        Se as permissões do agente estiverem ligadas, roda o loop de
        ferramentas (`ToolAgent`); `confirm` decide ações destrutivas e
        `on_event(kind, texto)` recebe avisos de ferramenta para a interface.
        Ao terminar, `last_stream` guarda a resposta completa e a mensagem e
        persistida no banco.
        """
        if conversation_id is None:
            conversation_id = await asyncio.to_thread(
                self.database.create_conversation, text[:80]
            )
        self.active_conversation_id = conversation_id
        self.last_stream = None
        await asyncio.to_thread(
            self.database.add_message,
            conversation_id,
            Message(role="user", content=text),
        )
        history = await asyncio.to_thread(self.database.get_messages, conversation_id)

        cog_ctx = self.cognition.build_cognitive_context(text)
        base_sys_prompt = f"{self.config.system_prompt}\n\n{cog_ctx}" if cog_ctx else self.config.system_prompt

        agent_config = self.config.agent
        vision_on = self.config.vision.enabled
        tools = (
            build_tools(agent_config, vision_enabled=vision_on)
            if agent_config.enabled
            else []
        )
        if agent_config.enabled:
            try:
                tools += await asyncio.to_thread(self.mcp.load_active_mcp_tools)
            except Exception:  # noqa: BLE001 - MCP nunca derruba o chat
                pass

        parts: list[str] = []
        final_text = ""
        provider_used = self.config.default_provider
        model_used = ""

        try:
            if agent_config.enabled and tools:
                system_prompt = build_agent_system_prompt(
                    base_sys_prompt, tools
                )
                messages = [
                    Message(role="system", content=system_prompt),
                    *history,
                ]
                context = ToolContext(
                    config=agent_config,
                    confirm=confirm or _auto_deny,
                    database=self.database,
                    vision=self._make_vision() if vision_on else None,
                    describe_image=self._make_describe_image() if vision_on else None,
                    emit_media=self.on_media,
                )
                agent = ToolAgent(self.router, agent_config)
                async for event in agent.run_stream(
                    messages, tools, context, provider_name=provider_name
                ):
                    if event.kind == "delta":
                        parts.append(event.text)
                        yield event.text
                    elif event.kind == "final":
                        final_text = event.text
                    elif on_event is not None:
                        on_event(event.kind, event.text)
                provider_used = agent.last_provider or (
                    provider_name or self.config.default_provider
                )
                model_used = agent.last_model or model_used
            else:
                request = LLMRequest(
                    messages=(
                        Message(
                            role="system",
                            content=(
                                f"{base_sys_prompt}\n\n{RESPONSE_STYLE}"
                                f"\n\n{system_context()}"
                            ),
                        ),
                        *history,
                    )
                )
                async for delta, provider_name_used, model in self.router.stream(
                    request, provider_name=provider_name
                ):
                    provider_used, model_used = provider_name_used, model
                    parts.append(delta)
                    yield delta
        finally:
            content = final_text.strip() or "".join(parts).strip()
            if content:
                self.last_stream = AssistantReply(
                    conversation_id=conversation_id,
                    response=LLMResponse(
                        provider=provider_used, model=model_used, content=content
                    ),
                )
                await asyncio.to_thread(
                    self.database.add_message,
                    conversation_id,
                    Message(role="assistant", content=content),
                    provider=provider_used,
                    model=model_used,
                    metadata={"agent": bool(agent_config.enabled and tools)},
                )
                # Aprendizado cognitivo contínuo do Jarvis (camada rápida)
                await asyncio.to_thread(self.cognition.process_user_turn, text, content)
                # camada profunda: consolidação por LLM a cada N turnos, em
                # segundo plano (não segura a resposta nem o loop deste turno)
                user_turns = sum(1 for m in history if m.role == "user")
                if user_turns % _CONSOLIDATE_EVERY_TURNS == 0:
                    snapshot = list(history) + [
                        Message(role="assistant", content=content)
                    ]
                    self._spawn_consolidation(snapshot, provider_name)

    def _spawn_consolidation(
        self, messages: list[Message], provider_name: str | None
    ) -> None:
        def _work() -> None:
            try:
                asyncio.run(
                    self.cognition.consolidator.consolidate(
                        messages, self.router.chat, provider_name=provider_name
                    )
                )
            except Exception:  # noqa: BLE001 - consolidação nunca derruba nada
                pass

        threading.Thread(
            target=_work, daemon=True, name="jarvis-memory-consolidate"
        ).start()

