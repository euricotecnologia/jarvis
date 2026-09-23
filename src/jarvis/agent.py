from __future__ import annotations

import getpass
import platform
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import AsyncIterator

from jarvis.config import AgentConfig
from jarvis.models import LLMRequest, Message
from jarvis.router import ModelRouter
from jarvis.tools.base import Tool, ToolResult
from jarvis.tools.context import ToolContext

_WEEKDAYS = (
    "segunda-feira", "terca-feira", "quarta-feira", "quinta-feira",
    "sexta-feira", "sabado", "domingo",
)

RESPONSE_STYLE = (
    "ESTILO DA RESPOSTA (suas respostas são LIDAS EM VOZ ALTA):\n"
    "- Fale como uma pessoa: natural, calorosa, direta. Nada de tom de manual.\n"
    "- Seja breve. Uma ou duas frases na maioria das vezes.\n"
    "- Depois de fazer uma ação (abrir algo, pesquisar, rodar um comando), so "
    "confirme o que fez em uma frase. Ex.: \"Pronto, abri a pesquisa da Sofia no "
    "YouTube.\"\n"
    "- NUNCA leia URLs, links, caminhos longos, código, JSON ou listas em voz "
    "alta - quem ouve não acompanha. Se precisar mostrar algo assim, diga que "
    "esta na tela.\n"
    "- Não repita o pedido do usuário nem explique o que vai fazer antes de "
    "fazer."
)


@dataclass(frozen=True, slots=True)
class AgentEvent:
    kind: str  # "delta" | "final" | "tool" | "notice" | "error"
    text: str = ""


def system_context() -> str:
    """Fatos do ambiente para o modelo não precisar de ferramenta para o obvio."""
    now = datetime.now().astimezone()
    try:
        user = getpass.getuser()
    except Exception:
        user = "desconhecido"
    return (
        "CONTEXTO ATUAL (confie nisto, não precisa de ferramenta):\n"
        f"- Data de hoje: {now:%d/%m/%Y} ({_WEEKDAYS[now.weekday()]}), {now:%H:%M}.\n"
        f"- Sistema: {platform.system()} {platform.release()}.\n"
        f"- Usuário: {user}. Pasta pessoal: {Path.home()}.\n"
        f"- Diretório de trabalho: {Path.cwd()}."
    )


def build_agent_system_prompt(base_prompt: str, tools: list[Tool]) -> str:
    lines = [base_prompt, "", RESPONSE_STYLE, "", system_context()]
    if tools:
        names = {tool.name for tool in tools}
        lines += [
            "",
            "COMO TRABALHAR COM FERRAMENTAS:",
            "- Pense passo a passo. Divida pedidos vagos em ações concretas e "
            "encadeie ferramentas ate concluir (ex.: listar_pasta -> ler_arquivo "
            "-> responder).",
            "- Se a primeira ferramenta falhar ou trouxer pouco, tente outro "
            "caminho antes de desistir (outro caminho, outra ferramenta, um "
            "comando no shell).",
            "- Interprete a intenção: 'abrir a pasta D:' = abrir no Explorador "
            "(abrir_pasta) OU listar o conteúdo (listar_pasta), conforme o "
            "contexto. Caminhos: 'D:' significa a raiz 'D:\\\\'.",
            "- Responda em texto so quando ja tiver o resultado. Uma ferramenta "
            "por vez. Nunca invente resultados.",
        ]
        if "abrir_pasta" in names:
            lines.append(
                "- Para 'abra/mostre a pasta X' prefira abrir_pasta; para 'o que "
                "tem em X' use listar_pasta."
            )
    return "\n".join(lines)


def _wordwise(text: str, group: int = 3) -> list[str]:
    parts = re.findall(r"\S+\s*", text)
    return ["".join(parts[i : i + group]) for i in range(0, len(parts), group)] or [text]


class ToolAgent:
    """Loop ReAct com function-calling NATIVO do provedor (sem protocolo de texto)."""

    def __init__(self, router: ModelRouter, config: AgentConfig) -> None:
        self.router = router
        self.config = config
        self.last_provider = ""
        self.last_model = ""

    async def run_stream(
        self,
        messages: list[Message],
        tools: list[Tool],
        ctx: ToolContext,
        *,
        provider_name: str | None = None,
    ) -> AsyncIterator[AgentEvent]:
        by_name = {tool.name: tool for tool in tools}
        tool_defs = tuple(tool.definition() for tool in tools)
        working = list(messages)
        limit = self.config.max_output_chars

        for _step in range(self.config.max_iterations):
            request = LLMRequest(messages=tuple(working), tools=tool_defs)
            try:
                response = await self.router.chat(
                    request, provider_name=provider_name
                )
            except Exception as exc:  # noqa: BLE001 - não deixa o turno explodir
                message = (
                    f"Não consegui falar com o provedor de IA agora ({exc}). "
                    "Tente de novo em instantes."
                )
                yield AgentEvent("error", str(exc))
                for chunk in _wordwise(message):
                    yield AgentEvent("delta", chunk)
                yield AgentEvent("final", message)
                return

            self.last_provider = response.provider or self.last_provider
            self.last_model = response.model or self.last_model

            if not response.tool_calls:
                text = (response.content or "").strip() or (
                    "Não consegui gerar uma resposta agora."
                )
                for chunk in _wordwise(text):
                    yield AgentEvent("delta", chunk)
                yield AgentEvent("final", text)
                return

            working.append(
                Message(
                    role="assistant",
                    content=response.content or "",
                    tool_calls=response.tool_calls,
                )
            )

            for call in response.tool_calls:
                tool = by_name.get(call.name)
                yield AgentEvent(
                    "tool",
                    tool.confirm_message(call.arguments)
                    if tool is not None
                    else f"{call.name}(...)",
                )

                if tool is None:
                    working.append(
                        Message(
                            role="tool",
                            tool_call_id=call.id,
                            name=call.name,
                            content=(
                                f"Ferramenta '{call.name}' não existe. "
                                f"Disponiveis: {', '.join(by_name) or 'nenhuma'}."
                            ),
                        )
                    )
                    yield AgentEvent("error", f"ferramenta desconhecida: {call.name}")
                    continue

                if tool.is_destructive(call.arguments, ctx):
                    approved = await ctx.confirm(tool.confirm_message(call.arguments))
                    if not approved:
                        working.append(
                            Message(
                                role="tool",
                                tool_call_id=call.id,
                                name=call.name,
                                content="O usuário RECUSOU esta ação. Não repita; "
                                "explique ou tome outro caminho.",
                            )
                        )
                        yield AgentEvent("notice", "Ação recusada pelo usuário.")
                        continue

                try:
                    result = await tool.run(call.arguments, ctx)
                    if isinstance(result, str):
                        # algumas ferramentas devolvem texto puro em vez de ToolResult
                        result = ToolResult(ok=True, content=result)
                    content = result.content
                    display = result.display or (
                        "ok" if result.ok else "falhou"
                    )
                except Exception as exc:  # noqa: BLE001 - vira contexto pro modelo
                    content = f"ERRO ao executar: {exc}"
                    display = f"{call.name}: erro"
                    yield AgentEvent("error", f"{call.name}: {exc}")
                else:
                    yield AgentEvent("notice", f"{call.name}: {display}")

                working.append(
                    Message(
                        role="tool",
                        tool_call_id=call.id,
                        name=call.name,
                        content=content[:limit],
                    )
                )

        limit_message = (
            "Cheguei ao limite de passos sem concluir. Me diga se quer que eu siga."
        )
        for chunk in _wordwise(limit_message):
            yield AgentEvent("delta", chunk)
        yield AgentEvent("final", limit_message)
