from __future__ import annotations

from typing import TYPE_CHECKING, Any

from jarvis.tools.base import Tool

if TYPE_CHECKING:
    from jarvis.tools.context import ToolContext


class ConsultarHistoricoConversas(Tool):
    """Busca no histórico de conversas passadas do usuário com o Jarvis.
    Permite lembrar de qualquer coisa discutida anteriormente, decisões, códigos ou assuntos."""

    name = "consultar_historico_conversas"
    description = (
        "Pesquisa no histórico completo de conversas anteriores com o usuário. "
        "Use sempre que o usuário perguntar o que foi conversado antes, sobre tópicos "
        "passados, instruções anteriores, ideias ou decisões tomadas em conversas passadas."
    )
    parameters = {
        "type": "object",
        "properties": {
            "termo_busca": {
                "type": "string",
                "description": "Palavra-chave, tópico, nome ou assunto a buscar no histórico.",
            },
            "limite": {
                "type": "integer",
                "description": "Quantidade máxima de mensagens a retornar (padrão: 10).",
            },
        },
        "required": ["termo_busca"],
    }

    async def run(self, args: dict[str, Any], context: ToolContext) -> str:
        term = str(args.get("termo_busca", "")).strip()
        if not term:
            return "Informe um termo ou palavra-chave para buscar no histórico."
        limit = int(args.get("limite", 10))

        results = context.database.search_conversation_messages(term, limit=limit)
        if not results:
            return f"Nenhuma mensagem anterior encontrada contendo '{term}'."

        lines = [f"Encontradas {len(results)} mensagem(ns) no histórico sobre '{term}':\n"]
        for r in results:
            date_str = r.get("created_at", "")
            title = r.get("conversation_title") or f"Conversa #{r.get('conversation_id')}"
            role = "USUÁRIO" if r.get("role") == "user" else "JARVIS"
            content = (r.get("content") or "").strip()
            if len(content) > 300:
                content = content[:300] + "..."
            lines.append(f"[{date_str}] ({title}) {role}: {content}\n")

        return "\n".join(lines)


class ConsultarMemoriaLongoPrazo(Tool):
    """Consulta memórias, preferências e fatos consolidados sobre o usuário."""

    name = "consultar_memoria_longo_prazo"
    description = (
        "Consulta as memórias de longo prazo consolidadas pelo Jarvis sobre o usuário "
        "(preferências, regras, fatos pessoais, projetos, empresa)."
    )
    parameters = {
        "type": "object",
        "properties": {
            "categoria": {
                "type": "string",
                "description": "Categoria da memória (preferencia, fato, projeto, regra, empresa, ou 'todas').",
            },
            "termo_busca": {
                "type": "string",
                "description": "Filtro opcional por palavra-chave.",
            },
        },
    }

    async def run(self, args: dict[str, Any], context: ToolContext) -> str:
        cat = args.get("categoria")
        if cat in ("todas", "todos", "all", ""):
            cat = None
        term = str(args.get("termo_busca", "")).strip()

        if term:
            memories = context.database.search_user_memories(term, limit=15)
        else:
            memories = context.database.list_user_memories(category=cat)

        if not memories:
            return "Nenhuma memória consolidada encontrada para os critérios informados."

        lines = [f"Memórias consolidadas ({len(memories)} itens):"]
        for m in memories:
            lines.append(f"- [{m.get('category', '').upper()}] {m.get('content', '')}")

        return "\n".join(lines)
