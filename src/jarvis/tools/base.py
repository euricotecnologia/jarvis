from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any

from jarvis.errors import ToolError
from jarvis.models import ToolDefinition

if TYPE_CHECKING:
    from jarvis.tools.context import ToolContext


class Risk(str, Enum):
    """Quanto uma ferramenta pode machucar se sair errado."""

    SAFE = "safe"  # so le / inspeciona, sem efeito colateral
    WRITE = "write"  # cria ou altera dados de forma recuperavel
    IRREVERSIBLE = "irreversible"  # apaga, sobrescreve ou envia algo pra fora


@dataclass(frozen=True, slots=True)
class ToolResult:
    ok: bool
    content: str  # texto devolvido ao modelo
    display: str = ""  # resumo curto para a interface

    @classmethod
    def failure(cls, message: str) -> "ToolResult":
        return cls(ok=False, content=message, display=message)


_EMPTY_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {},
    "additionalProperties": False,
}


class Tool:
    name: str = ""
    description: str = ""
    risk: Risk = Risk.SAFE
    parameters: dict[str, Any] = _EMPTY_SCHEMA

    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name, description=self.description, parameters=self.parameters
        )

    async def run(self, args: dict[str, Any], ctx: "ToolContext") -> ToolResult:
        """Executa a ferramenta, transformando erros previsiveis em falha limpa."""
        try:
            return await self.execute(args, ctx)
        except ToolError as exc:
            return ToolResult.failure(str(exc))
        except OSError as exc:
            return ToolResult.failure(f"Erro de sistema: {exc}")

    async def execute(self, args: dict[str, Any], ctx: "ToolContext") -> ToolResult:
        raise NotImplementedError

    def is_destructive(self, args: dict[str, Any], ctx: "ToolContext") -> bool:
        """A política so confirma o irreversivel; ferramentas de escrita que
        podem sobrescrever algo existente respondem True aqui nesse caso."""
        return self.risk is Risk.IRREVERSIBLE

    def confirm_message(self, args: dict[str, Any]) -> str:
        pretty = ", ".join(f"{key}={value!r}" for key, value in args.items())
        return f"{self.name}({pretty})"
