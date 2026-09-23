from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

Role = Literal["system", "developer", "user", "assistant", "tool"]


@dataclass(frozen=True, slots=True)
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True, slots=True)
class Message:
    role: Role
    content: str = ""
    # Preenchido em mensagens `assistant` que chamaram ferramentas.
    tool_calls: tuple["ToolCall", ...] = ()
    # Preenchidos em mensagens `tool` (resultado de uma ferramenta).
    tool_call_id: str | None = None
    name: str | None = None


@dataclass(frozen=True, slots=True)
class Routine:
    """Uma rotina de automação: nome + lista de passos em linguagem natural."""

    name: str
    steps: tuple[str, ...] = ()
    description: str = ""
    enabled: bool = True
    id: int | None = None


@dataclass(frozen=True, slots=True)
class Schedule:
    """Agendamento de uma rotina. Uma rotina tem no maximo um agendamento."""

    routine_id: int
    kind: str = "once"  # "once" | "daily" | "weekly"
    run_at: str | None = None  # ISO 'YYYY-MM-DDTHH:MM' quando kind == 'once'
    time_of_day: str | None = None  # 'HH:MM' quando kind in ('daily', 'weekly')
    weekday: int | None = None  # 0=segunda .. 6=domingo quando kind == 'weekly'
    enabled: bool = True
    last_run_at: str | None = None
    id: int | None = None


@dataclass(frozen=True, slots=True)
class Contact:
    """Um contato da agenda."""

    name: str
    phone: str = ""
    email: str = ""
    birthday: str | None = None  # 'MM-DD' ou 'YYYY-MM-DD'
    notes: str = ""
    tags: str = ""
    id: int | None = None


@dataclass(frozen=True, slots=True)
class Appointment:
    """Um compromisso na agenda."""

    title: str
    start_at: str  # ISO 'YYYY-MM-DDTHH:MM'
    end_at: str | None = None
    location: str = ""
    notes: str = ""
    contact_id: int | None = None
    reminder_minutes: int = 15  # -1 = sem lembrete
    reminded_at: str | None = None
    id: int | None = None


@dataclass(frozen=True, slots=True)
class Server:
    """Um servidor remoto acessivel por SSH (VPS, homelab...)."""

    alias: str
    host: str
    user: str
    port: int = 22
    auth: str = "key"  # "key" | "password" | "agent"
    key_path: str = ""
    password_enc: str = ""  # blob cifrado (secret_store); nunca em texto puro
    notes: str = ""
    id: int | None = None


@dataclass(frozen=True, slots=True)
class ToolDefinition:
    name: str
    description: str
    parameters: dict[str, Any]


@dataclass(frozen=True, slots=True)
class LLMRequest:
    messages: tuple[Message, ...]
    tools: tuple[ToolDefinition, ...] = ()
    max_output_tokens: int = 2048
    temperature: float | None = None


@dataclass(frozen=True, slots=True)
class LLMResponse:
    provider: str
    model: str
    content: str
    tool_calls: tuple[ToolCall, ...] = ()
    usage: dict[str, int] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict, repr=False)


@dataclass(frozen=True, slots=True)
class AssistantReply:
    conversation_id: int
    response: LLMResponse

