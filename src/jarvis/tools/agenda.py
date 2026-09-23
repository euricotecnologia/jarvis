"""Ferramentas do agente para a Agenda: consultar e criar compromissos e contatos."""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from typing import Any

from jarvis.agenda import combine_fields, format_agenda, parse_birthday
from jarvis.errors import ToolError
from jarvis.models import Appointment, Contact
from jarvis.tools.base import Risk, Tool, ToolResult
from jarvis.tools.context import ToolContext


def _db(ctx: ToolContext):
    if ctx.database is None:
        raise ToolError("Banco de dados indisponível para a Agenda.")
    return ctx.database


def _resolve_date(text: str) -> date:
    text = (text or "").strip().lower()
    today = date.today()
    if text in {"", "hoje"}:
        return today
    if text in {"amanha", "amanhã"}:
        return today + timedelta(days=1)
    if text in {"depois de amanha", "depois de amanhã"}:
        return today + timedelta(days=2)
    match = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})$", text)
    if match:
        return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
    match = re.match(r"^(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?$", text)
    if match:
        day, month = int(match.group(1)), int(match.group(2))
        year = int(match.group(3)) if match.group(3) else today.year
        if year < 100:
            year += 2000
        return date(year, month, day)
    raise ValueError(f"Não entendi a data '{text}'. Use DD/MM/AAAA, 'hoje' ou 'amanha'.")


class ConsultarAgenda(Tool):
    name = "consultar_agenda"
    description = (
        "Lista os compromissos do usuário num periodo. Use para responder "
        "'o que tenho hoje?', 'minha agenda de amanha', 'compromissos da semana'."
    )
    risk = Risk.SAFE
    parameters = {
        "type": "object",
        "properties": {
            "periodo": {
                "type": "string",
                "description": (
                    "'hoje', 'amanha', 'semana', 'mes' ou uma data DD/MM/AAAA."
                ),
            }
        },
        "required": [],
        "additionalProperties": False,
    }

    async def execute(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        database = _db(ctx)
        periodo = str(args.get("periodo", "hoje")).strip().lower()
        now = datetime.now()
        if periodo in {"semana", "essa semana", "esta semana"}:
            since = now.replace(hour=0, minute=0, second=0, microsecond=0)
            until = since + timedelta(days=7)
        elif periodo in {"mes", "mês", "esse mes", "este mes"}:
            since = now.replace(hour=0, minute=0, second=0, microsecond=0)
            until = since + timedelta(days=31)
        else:
            day = _resolve_date(periodo) if periodo not in {"", "hoje"} else now.date()
            since = datetime(day.year, day.month, day.day)
            until = since + timedelta(days=1)
        items = database.list_appointments(
            since=since.isoformat(timespec="minutes"),
            until=until.isoformat(timespec="minutes"),
        )
        names = {c.id: c.name for c in database.list_contacts()}
        return ToolResult(
            ok=True,
            content=format_agenda(items, names, now),
            display=f"{len(items)} compromisso(s)",
        )


class SalvarCompromisso(Tool):
    name = "salvar_compromisso"
    description = (
        "Cria um compromisso na agenda do usuário. Confirme título, data e hora "
        "antes de chamar se estiverem ambiguos."
    )
    risk = Risk.WRITE
    parameters = {
        "type": "object",
        "properties": {
            "titulo": {"type": "string"},
            "data": {"type": "string", "description": "DD/MM/AAAA, 'hoje' ou 'amanha'."},
            "hora": {"type": "string", "description": "HH:MM em 24h."},
            "duracao_min": {"type": "integer", "description": "Duração em minutos (opcional)."},
            "local": {"type": "string"},
            "lembrete_min": {
                "type": "integer",
                "description": "Minutos antes para avisar. -1 = sem lembrete. Padrão 15.",
            },
            "contato": {"type": "string", "description": "Nome de um contato existente (opcional)."},
        },
        "required": ["titulo", "data", "hora"],
        "additionalProperties": False,
    }

    async def execute(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        database = _db(ctx)
        title = str(args.get("titulo", "")).strip()
        if not title:
            return ToolResult.failure("O compromisso precisa de um título.")
        try:
            day = _resolve_date(str(args.get("data", "")))
            hour, minute = (int(part) for part in str(args["hora"]).split(":"))
            start_at = combine_fields(
                f"{day.day:02d}/{day.month:02d}/{day.year}", f"{hour:02d}:{minute:02d}"
            )
        except (ValueError, KeyError, AttributeError) as exc:
            return ToolResult.failure(f"Data ou hora invalida: {exc}")

        end_at = None
        duration = args.get("duracao_min")
        if isinstance(duration, (int, float)) and duration > 0:
            end = datetime.fromisoformat(start_at) + timedelta(minutes=int(duration))
            end_at = end.isoformat(timespec="minutes")

        contact_id = None
        contact_name = str(args.get("contato", "")).strip()
        if contact_name:
            matches = database.find_contacts(contact_name)
            if matches:
                contact_id = matches[0].id

        reminder = args.get("lembrete_min", 15)
        reminder = int(reminder) if isinstance(reminder, (int, float)) else 15

        appointment_id = database.save_appointment(
            Appointment(
                title=title,
                start_at=start_at,
                end_at=end_at,
                location=str(args.get("local", "")).strip(),
                contact_id=contact_id,
                reminder_minutes=reminder,
            )
        )
        pretty = datetime.fromisoformat(start_at)
        return ToolResult(
            ok=True,
            content=f"Compromisso #{appointment_id} criado: {title} em {pretty:%d/%m às %H:%M}.",
            display=f"compromisso salvo: {title}",
        )


class BuscarContato(Tool):
    name = "buscar_contato"
    description = "Procura um contato por nome, telefone, email ou tag."
    risk = Risk.SAFE
    parameters = {
        "type": "object",
        "properties": {"termo": {"type": "string"}},
        "required": ["termo"],
        "additionalProperties": False,
    }

    async def execute(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        database = _db(ctx)
        term = str(args.get("termo", "")).strip()
        if not term:
            return ToolResult.failure("Informe o que procurar.")
        found = database.find_contacts(term)
        if not found:
            return ToolResult(ok=True, content=f"Nenhum contato para '{term}'.", display="0 contatos")
        lines = [
            "- " + ", ".join(
                part
                for part in (c.name, c.phone, c.email)
                if part
            )
            for c in found
        ]
        return ToolResult(
            ok=True, content="\n".join(lines), display=f"{len(found)} contato(s)"
        )


class SalvarContato(Tool):
    name = "salvar_contato"
    description = "Cria um contato na agenda do usuário."
    risk = Risk.WRITE
    parameters = {
        "type": "object",
        "properties": {
            "nome": {"type": "string"},
            "telefone": {"type": "string"},
            "email": {"type": "string"},
            "aniversario": {"type": "string", "description": "DD/MM ou DD/MM/AAAA (opcional)."},
            "notas": {"type": "string"},
        },
        "required": ["nome"],
        "additionalProperties": False,
    }

    async def execute(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        database = _db(ctx)
        name = str(args.get("nome", "")).strip()
        if not name:
            return ToolResult.failure("O contato precisa de um nome.")
        birthday = None
        raw_bday = str(args.get("aniversario", "")).strip()
        if raw_bday:
            match = re.match(r"^(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?$", raw_bday)
            if match:
                day, month = int(match.group(1)), int(match.group(2))
                if match.group(3):
                    year = int(match.group(3))
                    year += 2000 if year < 100 else 0
                    birthday = f"{year:04d}-{month:02d}-{day:02d}"
                else:
                    birthday = f"{month:02d}-{day:02d}"
            elif parse_birthday(raw_bday):
                birthday = raw_bday
        contact_id = database.save_contact(
            Contact(
                name=name,
                phone=str(args.get("telefone", "")).strip(),
                email=str(args.get("email", "")).strip(),
                birthday=birthday,
                notes=str(args.get("notas", "")).strip(),
            )
        )
        return ToolResult(
            ok=True,
            content=f"Contato #{contact_id} criado: {name}.",
            display=f"contato salvo: {name}",
        )
