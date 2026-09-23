"""Regras da Agenda: datas, aniversarios, lembretes e formatação pt-BR."""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta

from jarvis.models import Appointment

_WEEKDAYS = (
    "segunda",
    "terca",
    "quarta",
    "quinta",
    "sexta",
    "sabado",
    "domingo",
)
_WEEKDAYS_LONG = tuple(f"{name}-feira" if i < 5 else name for i, name in enumerate(_WEEKDAYS))

REMINDER_CHOICES = (
    (-1, "Sem lembrete"),
    (0, "Na hora"),
    (5, "5 min antes"),
    (10, "10 min antes"),
    (15, "15 min antes"),
    (30, "30 min antes"),
    (60, "1 hora antes"),
    (120, "2 horas antes"),
    (1440, "1 dia antes"),
)
# Janela de tolerancia: se o app estava fechado, ainda avisa se faltar pouco.
REMINDER_GRACE = timedelta(minutes=10)


def describe_reminder(minutes: int) -> str:
    for value, label in REMINDER_CHOICES:
        if value == minutes:
            return label
    if minutes % 1440 == 0:
        return f"{minutes // 1440} dia(s) antes"
    if minutes % 60 == 0:
        return f"{minutes // 60} hora(s) antes"
    return f"{minutes} min antes"


def parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def combine_fields(date_text: str, time_text: str) -> str:
    """'31/08/2026' + '15:30' -> '2026-08-31T15:30'. Lanca ValueError."""
    try:
        day, month, year = (int(part) for part in date_text.split("/"))
        hour, minute = (int(part) for part in time_text.split(":"))
        moment = datetime(year, month, day, hour, minute)
    except (ValueError, AttributeError) as exc:
        raise ValueError("Informe data (DD/MM/AAAA) e hora (HH:MM) validas.") from exc
    return moment.isoformat(timespec="minutes")


def day_label(day: date, today: date) -> str:
    delta = (day - today).days
    if delta == 0:
        return "Hoje"
    if delta == 1:
        return "Amanhã"
    if delta == -1:
        return "Ontem"
    if 1 < delta < 7:
        return _WEEKDAYS_LONG[day.weekday()].capitalize()
    return f"{_WEEKDAYS[day.weekday()].capitalize()} {day:%d/%m}"


def describe_when(appointment: Appointment, now: datetime) -> str:
    start = parse_dt(appointment.start_at)
    if start is None:
        return "data invalida"
    label = day_label(start.date(), now.date())
    text = f"{label} {start:%H:%M}"
    diff = start - now
    if timedelta(0) <= diff <= timedelta(hours=12):
        minutes = int(diff.total_seconds() // 60)
        if minutes < 60:
            text += f"  (em {max(minutes, 0)} min)"
        else:
            text += f"  (em {minutes // 60}h{minutes % 60:02d})"
    return text


def reminder_due(appointment: Appointment, now: datetime) -> bool:
    if appointment.reminder_minutes < 0 or appointment.reminded_at:
        return False
    start = parse_dt(appointment.start_at)
    if start is None:
        return False
    trigger = start - timedelta(minutes=appointment.reminder_minutes)
    return trigger <= now <= start + REMINDER_GRACE


def reminder_text(appointment: Appointment, now: datetime) -> str:
    start = parse_dt(appointment.start_at)
    if start is None:
        return f"Lembrete: {appointment.title}."
    diff = start - now
    minutes = int(diff.total_seconds() // 60)
    if minutes <= 0:
        when = "agora"
    elif minutes < 60:
        when = f"em {minutes} minutos"
    elif minutes < 1440:
        when = f"às {start:%H:%M}"
    else:
        when = f"amanhã às {start:%H:%M}"
    where = f", em {appointment.location}" if appointment.location else ""
    return f"Lembrete: {appointment.title} {when}{where}."


# -- aniversarios ---------------------------------------------------------
_BDAY_RE = re.compile(r"^(?:(\d{4})-)?(\d{1,2})-(\d{1,2})$")


def parse_birthday(value: str | None) -> tuple[int, int, int | None] | None:
    """Devolve (mes, dia, ano|None). Aceita 'MM-DD' ou 'YYYY-MM-DD'."""
    if not value:
        return None
    match = _BDAY_RE.match(value.strip())
    if not match:
        return None
    year = int(match.group(1)) if match.group(1) else None
    month, day = int(match.group(2)), int(match.group(3))
    if not (1 <= month <= 12 and 1 <= day <= 31):
        return None
    return month, day, year


def birthday_on(value: str | None, day: date) -> bool:
    parsed = parse_birthday(value)
    return parsed is not None and (parsed[0], parsed[1]) == (day.month, day.day)


def birthday_label(value: str | None, today: date) -> str | None:
    parsed = parse_birthday(value)
    if parsed is None:
        return None
    month, day, year = parsed
    try:
        this_year = date(today.year, month, day)
    except ValueError:
        return None
    upcoming = this_year if this_year >= today else date(today.year + 1, month, day)
    age = ""
    if year:
        age = f" (faz {upcoming.year - year})"
    delta = (upcoming - today).days
    if delta == 0:
        return f"Aniversário hoje{age}"
    if delta == 1:
        return f"Aniversário amanhã{age}"
    if delta <= 30:
        return f"Aniversário em {delta} dias{age}"
    return None


def format_agenda(
    appointments: list[Appointment],
    contacts_by_id: dict[int, str],
    now: datetime,
) -> str:
    """Texto para o modelo/voz responder 'o que tenho hoje?'."""
    if not appointments:
        return "Nenhum compromisso no periodo."
    lines: list[str] = []
    for item in appointments:
        start = parse_dt(item.start_at)
        when = describe_when(item, now) if start else item.start_at
        who = contacts_by_id.get(item.contact_id or -1, "")
        extra = " - ".join(part for part in (item.location, who) if part)
        lines.append(f"- {when}: {item.title}" + (f" ({extra})" if extra else ""))
    return "\n".join(lines)
