from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Awaitable, Callable

from jarvis.config import AgentConfig
from jarvis.errors import PermissionDenied

if TYPE_CHECKING:
    from jarvis.database import Database


def _normalize_raw_path(raw: str) -> str:
    """Aceita as formas que o usuário/modelo costuma escrever.

    - "D:" ou "d:" -> "D:\\" (senao o Windows resolve para o cwd do drive)
    - "disco D", "unidade D", "drive D:" -> "D:\\"
    - "~" e barras normais passam adiante.
    """
    text = raw.strip().strip('"').strip("'")
    match = re.fullmatch(
        r"(?:disco|unidade|drive|diretorio|pasta|raiz(?:\s+d[oa])?)?\s*"
        r"([a-zA-Z]):?[\\/]*",
        text,
        re.IGNORECASE,
    )
    if match:
        return f"{match.group(1).upper()}:\\"
    if re.fullmatch(r"[a-zA-Z]:", text):
        return text[0].upper() + ":\\"
    return text

ConfirmFn = Callable[[str], Awaitable[bool]]


async def _auto_deny(_message: str) -> bool:
    return False


@dataclass(slots=True)
class ToolContext:
    """Estado compartilhado pelas ferramentas durante um turno do agente."""

    config: AgentConfig
    confirm: ConfirmFn = _auto_deny
    home: Path = field(default_factory=Path.home)
    database: "Database | None" = None
    # (pergunta) -> (descrição, jpeg da webcam); None quando a visão esta off.
    vision: Callable[[str], "tuple[str, bytes]"] | None = None
    # (jpeg, pergunta) -> descrição de uma imagem qualquer (usa modelo com visão).
    describe_image: Callable[[bytes, str], str] | None = None
    # (bytes, kind, legenda) -> mostra a midia no chat.
    emit_media: Callable[[bytes, str, str], None] | None = None

    def write_roots(self) -> list[Path]:
        roots = [
            Path(item).expanduser()
            for item in self.config.allowed_roots
            if str(item).strip()
        ]
        if not roots:
            roots = [self.home]
        resolved: list[Path] = []
        for root in roots:
            try:
                resolved.append(root.resolve())
            except OSError:
                continue
        return resolved

    def resolve_readable(self, raw: str) -> Path:
        if not raw or not str(raw).strip():
            raise PermissionDenied("Caminho vazio.")
        cleaned = _normalize_raw_path(str(raw))
        try:
            return Path(cleaned).expanduser().resolve()
        except OSError as exc:
            raise PermissionDenied(f"Caminho invalido: {raw} ({exc})") from exc

    def resolve_writable(self, raw: str) -> Path:
        path = self.resolve_readable(raw)
        for root in self.write_roots():
            if path == root or root in path.parents:
                return path
        allowed = ", ".join(str(root) for root in self.write_roots())
        raise PermissionDenied(
            f"'{path}' está fora das pastas permitidas para escrita ({allowed}). "
            "Ajuste em Configurações > Permissões."
        )
