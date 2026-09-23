"""Regras de agendamento de rotinas.

O `JarvisBackend` roda um laco a cada ~20s (`_scheduler_worker`) que pergunta a
`is_due()` se algum agendamento venceu. Tudo em horário local; so dispara com o
app aberto.
"""

from __future__ import annotations

from datetime import datetime, time, timedelta

from jarvis.models import Schedule

WEEKDAY_NAMES = (
    "segunda-feira",
    "terça-feira",
    "quarta-feira",
    "quinta-feira",
    "sexta-feira",
    "sábado",
    "domingo",
)

# Janela de tolerancia para um agendamento "uma vez" atrasado (app estava fechado).
CATCHUP_WINDOW = timedelta(hours=12)


def parse_time_of_day(value: str | None) -> time | None:
    if not value:
        return None
    try:
        hour, minute = (int(part) for part in value.split(":", 1))
    except (ValueError, AttributeError):
        return None
    if 0 <= hour < 24 and 0 <= minute < 60:
        return time(hour=hour, minute=minute)
    return None


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def is_due(schedule: Schedule, now: datetime) -> bool:
    """True se `schedule` deveria ter rodado ate agora e ainda não rodou."""
    if not schedule.enabled:
        return False
    last_run = _parse_dt(schedule.last_run_at)

    if schedule.kind == "once":
        target = _parse_dt(schedule.run_at)
        if target is None:
            return False
        if last_run is not None:
            return False
        return now >= target

    moment = parse_time_of_day(schedule.time_of_day)
    if moment is None:
        return False
    if schedule.kind == "weekly":
        if schedule.weekday is None or now.weekday() != schedule.weekday:
            return False
    elif schedule.kind != "daily":
        return False

    target_today = now.replace(
        hour=moment.hour, minute=moment.minute, second=0, microsecond=0
    )
    if now < target_today:
        return False
    if last_run is not None and last_run >= target_today:
        return False
    return True


def is_missed(schedule: Schedule, now: datetime) -> bool:
    """Agendamento 'uma vez' que passou da janela de tolerancia."""
    if schedule.kind != "once":
        return False
    target = _parse_dt(schedule.run_at)
    return target is not None and now - target > CATCHUP_WINDOW


def next_occurrence(schedule: Schedule, now: datetime) -> datetime | None:
    """Próxima vez que o agendamento deve rodar (para exibir na interface)."""
    if schedule.kind == "once":
        return _parse_dt(schedule.run_at)

    moment = parse_time_of_day(schedule.time_of_day)
    if moment is None:
        return None
    candidate = now.replace(
        hour=moment.hour, minute=moment.minute, second=0, microsecond=0
    )
    if schedule.kind == "daily":
        if candidate <= now:
            candidate += timedelta(days=1)
        return candidate
    if schedule.kind == "weekly" and schedule.weekday is not None:
        days_ahead = (schedule.weekday - now.weekday()) % 7
        candidate += timedelta(days=days_ahead)
        if candidate <= now:
            candidate += timedelta(days=7)
        return candidate
    return None


def describe_schedule(schedule: Schedule, now: datetime | None = None) -> str:
    """Texto curto em pt-BR para o cartao da rotina."""
    now = now or datetime.now()
    if not schedule.enabled and schedule.kind == "once":
        target = _parse_dt(schedule.run_at)
        if target is not None and schedule.last_run_at:
            return f"Rodou em {target:%d/%m %H:%M}"
    if schedule.kind == "once":
        target = _parse_dt(schedule.run_at)
        if target is None:
            return "Agendamento invalido"
        return f"Uma vez em {target:%d/%m/%Y às %H:%M}"
    moment = parse_time_of_day(schedule.time_of_day)
    if moment is None:
        return "Agendamento invalido"
    if schedule.kind == "daily":
        return f"Todo dia às {moment:%H:%M}"
    if schedule.kind == "weekly" and schedule.weekday is not None:
        return f"Toda {WEEKDAY_NAMES[schedule.weekday]} às {moment:%H:%M}"
    return "Agendamento invalido"


def build_schedule(
    routine_id: int,
    kind: str,
    *,
    date_text: str = "",
    time_text: str = "",
    weekday: int | None = None,
) -> Schedule:
    """Monta um `Schedule` a partir dos campos da interface. Lanca ValueError."""
    kind = (kind or "").strip().lower()
    moment = parse_time_of_day(time_text)
    if moment is None:
        raise ValueError("Informe um horário valido (HH:MM).")
    time_str = f"{moment.hour:02d}:{moment.minute:02d}"

    if kind == "once":
        try:
            day, month, year = (int(part) for part in date_text.split("/"))
            target = datetime(year, month, day, moment.hour, moment.minute)
        except (ValueError, AttributeError) as exc:
            raise ValueError("Informe uma data valida (DD/MM/AAAA).") from exc
        if target < datetime.now() - timedelta(minutes=1):
            raise ValueError("Essa data e horário ja passaram.")
        return Schedule(
            routine_id=routine_id,
            kind="once",
            run_at=target.isoformat(timespec="minutes"),
        )
    if kind == "daily":
        return Schedule(routine_id=routine_id, kind="daily", time_of_day=time_str)
    if kind == "weekly":
        if weekday is None or not 0 <= weekday <= 6:
            raise ValueError("Escolha o dia da semana.")
        return Schedule(
            routine_id=routine_id,
            kind="weekly",
            time_of_day=time_str,
            weekday=weekday,
        )
    raise ValueError(f"Tipo de agendamento desconhecido: {kind}")
