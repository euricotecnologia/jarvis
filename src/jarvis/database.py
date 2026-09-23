from __future__ import annotations

import json
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Iterator

from jarvis.config import ProviderConfig
from jarvis.errors import DatabaseUnavailable
from jarvis.models import Appointment, Contact, Message, Routine, Schedule, Server

# Backoff quando o SO/antivirus bloqueia a escrita momentaneamente.
_RETRY_DELAYS = (0.15, 0.4, 0.9, 1.8)
_TRANSIENT = ("disk i/o error", "database is locked", "database is busy")


SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER NOT NULL
);

INSERT INTO schema_version(version)
SELECT 1
WHERE NOT EXISTS (SELECT 1 FROM schema_version);

CREATE TABLE IF NOT EXISTS providers (
    name TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    enabled INTEGER NOT NULL,
    model TEXT NOT NULL,
    base_url TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('system', 'developer', 'user', 'assistant', 'tool')),
    content TEXT NOT NULL,
    provider TEXT,
    model TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation
ON messages(conversation_id, id);

CREATE TABLE IF NOT EXISTS memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,
    content TEXT NOT NULL,
    importance REAL NOT NULL DEFAULT 0.5,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tool_executions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER REFERENCES conversations(id) ON DELETE SET NULL,
    tool_name TEXT NOT NULL,
    arguments_json TEXT NOT NULL,
    status TEXT NOT NULL,
    result_json TEXT,
    requires_confirmation INTEGER NOT NULL DEFAULT 0,
    confirmed_at TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    finished_at TEXT
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value_json TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS routines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL DEFAULT '',
    steps_json TEXT NOT NULL DEFAULT '[]',
    enabled INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS schedules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    routine_id INTEGER NOT NULL UNIQUE REFERENCES routines(id) ON DELETE CASCADE,
    kind TEXT NOT NULL DEFAULT 'once',
    run_at TEXT,
    time_of_day TEXT,
    weekday INTEGER,
    enabled INTEGER NOT NULL DEFAULT 1,
    last_run_at TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    phone TEXT NOT NULL DEFAULT '',
    email TEXT NOT NULL DEFAULT '',
    birthday TEXT,
    notes TEXT NOT NULL DEFAULT '',
    tags TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS appointments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    start_at TEXT NOT NULL,
    end_at TEXT,
    location TEXT NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT '',
    contact_id INTEGER REFERENCES contacts(id) ON DELETE SET NULL,
    reminder_minutes INTEGER NOT NULL DEFAULT 15,
    reminded_at TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_appointments_start ON appointments(start_at);

CREATE TABLE IF NOT EXISTS servers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alias TEXT NOT NULL UNIQUE,
    host TEXT NOT NULL,
    user TEXT NOT NULL,
    port INTEGER NOT NULL DEFAULT 22,
    auth TEXT NOT NULL DEFAULT 'key',
    key_path TEXT NOT NULL DEFAULT '',
    password_enc TEXT NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ai_agents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    api_key TEXT NOT NULL DEFAULT '',
    base_url TEXT NOT NULL DEFAULT '',
    system_prompt TEXT NOT NULL DEFAULT '',
    temperature REAL NOT NULL DEFAULT 0.7,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS communication_agents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    age TEXT NOT NULL DEFAULT '',
    gender TEXT NOT NULL DEFAULT '',
    role TEXT NOT NULL DEFAULT '',
    model_id INTEGER,
    model_name TEXT NOT NULL DEFAULT '',
    tone TEXT NOT NULL DEFAULT '',
    formality TEXT NOT NULL DEFAULT '',
    emoji_level TEXT NOT NULL DEFAULT 'Normal',
    response_style TEXT NOT NULL DEFAULT '',
    language TEXT NOT NULL DEFAULT 'Português (Brasil)',
    job_description TEXT NOT NULL DEFAULT '',
    responsibilities TEXT NOT NULL DEFAULT '[]',
    company_name TEXT NOT NULL DEFAULT '',
    company_segment TEXT NOT NULL DEFAULT '',
    company_description TEXT NOT NULL DEFAULT '',
    company_products TEXT NOT NULL DEFAULT '',
    company_target_audience TEXT NOT NULL DEFAULT '',
    company_regions TEXT NOT NULL DEFAULT '',
    company_business_hours TEXT NOT NULL DEFAULT '',
    company_payment_methods TEXT NOT NULL DEFAULT '',
    company_policies TEXT NOT NULL DEFAULT '',
    company_info TEXT NOT NULL DEFAULT '',
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,
    key TEXT NOT NULL,
    content TEXT NOT NULL,
    confidence REAL NOT NULL DEFAULT 1.0,
    access_count INTEGER NOT NULL DEFAULT 0,
    source TEXT NOT NULL DEFAULT 'chat',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_behavior_profile (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    feature TEXT NOT NULL UNIQUE,
    value TEXT NOT NULL,
    score REAL NOT NULL DEFAULT 1.0,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_behavior_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action_type TEXT NOT NULL,
    action_payload TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS assistant_persona (
    id INTEGER PRIMARY KEY DEFAULT 1,
    name TEXT NOT NULL DEFAULT 'Jarvis',
    personality TEXT NOT NULL DEFAULT 'Prestativo e Amigável',
    tone TEXT NOT NULL DEFAULT 'Natural',
    accent TEXT NOT NULL DEFAULT 'Português (Brasil)',
    tts_voice TEXT NOT NULL DEFAULT '',
    tts_rate INTEGER NOT NULL DEFAULT 180,
    tts_volume REAL NOT NULL DEFAULT 1.0,
    custom_instructions TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS mcp_servers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    command TEXT NOT NULL,
    args TEXT NOT NULL DEFAULT '[]',
    env_vars TEXT NOT NULL DEFAULT '{}',
    enabled INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Setor Saúde: cadastro de pacientes e prontuário
CREATE TABLE IF NOT EXISTS patients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    birthdate TEXT NOT NULL DEFAULT '',
    sex TEXT NOT NULL DEFAULT '',
    phone TEXT NOT NULL DEFAULT '',
    email TEXT NOT NULL DEFAULT '',
    document TEXT NOT NULL DEFAULT '',
    cns TEXT NOT NULL DEFAULT '',
    blood_type TEXT NOT NULL DEFAULT '',
    allergies TEXT NOT NULL DEFAULT '',
    conditions TEXT NOT NULL DEFAULT '',
    medications TEXT NOT NULL DEFAULT '',
    background TEXT NOT NULL DEFAULT '',
    family_background TEXT NOT NULL DEFAULT '',
    social_background TEXT NOT NULL DEFAULT '',
    insurance TEXT NOT NULL DEFAULT '',
    emergency_contact TEXT NOT NULL DEFAULT '',
    city TEXT NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS patient_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id INTEGER NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    kind TEXT NOT NULL DEFAULT 'nota',
    title TEXT NOT NULL DEFAULT '',
    body TEXT NOT NULL DEFAULT '',
    occurred_at TEXT NOT NULL DEFAULT '',
    vitals TEXT NOT NULL DEFAULT '',
    ai_summary TEXT NOT NULL DEFAULT '',
    ai_flags TEXT NOT NULL DEFAULT '',
    ai_json TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_precords_patient ON patient_records(patient_id);

CREATE TABLE IF NOT EXISTS patient_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    record_id INTEGER NOT NULL REFERENCES patient_records(id) ON DELETE CASCADE,
    patient_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    path TEXT NOT NULL,
    mime TEXT NOT NULL DEFAULT '',
    size INTEGER NOT NULL DEFAULT 0,
    extracted_text TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_pfiles_record ON patient_files(record_id);
"""


class Database:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path, timeout=15.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 15000")
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            connection.execute("PRAGMA journal_mode = WAL")
        except sqlite3.OperationalError:
            pass  # sem WAL o banco ainda funciona (modo rollback)
        return connection

    def _friendly(self, exc: sqlite3.Error) -> Exception:
        message = str(exc).lower()
        if any(marker in message for marker in _TRANSIENT) or "unable to open" in message:
            return DatabaseUnavailable(
                f"O banco local ({self.path}) não pode ser gravado agora. "
                "Quase sempre e o antivirus bloqueando o app nesta pasta. "
                "Tente: reiniciar o PC; adicionar a pasta do projeto as exceções "
                "do antivirus; ou apontar 'database_path' no config.toml para uma "
                f"pasta no C:. Detalhe tecnico: {exc}"
            )
        return exc

    def _retry(self, action: Callable[[], Any]) -> Any:
        for delay in (*_RETRY_DELAYS, None):
            try:
                return action()
            except sqlite3.OperationalError as exc:
                if delay is None or not any(
                    marker in str(exc).lower() for marker in _TRANSIENT
                ):
                    raise self._friendly(exc) from exc
                time.sleep(delay)
        raise RuntimeError("unreachable")

    @contextmanager
    def session(self) -> Iterator[sqlite3.Connection]:
        """Abre uma transação com retry e sempre libera o arquivo (Windows)."""
        connection = self._retry(self.connect)
        try:
            yield connection
            self._retry(connection.commit)
        except BaseException:
            try:
                connection.rollback()
            except sqlite3.Error:
                pass
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        def _do() -> None:
            with self.session() as connection:
                connection.executescript(SCHEMA)

                # Migração automática de colunas para communication_agents se já existia
                cols_info = connection.execute("PRAGMA table_info(communication_agents)").fetchall()
                existing_cols = {col[1] for col in cols_info}
                new_cols = [
                    ("company_description", "TEXT NOT NULL DEFAULT ''"),
                    ("company_products", "TEXT NOT NULL DEFAULT ''"),
                    ("company_target_audience", "TEXT NOT NULL DEFAULT ''"),
                    ("company_regions", "TEXT NOT NULL DEFAULT ''"),
                    ("company_business_hours", "TEXT NOT NULL DEFAULT ''"),
                    ("company_payment_methods", "TEXT NOT NULL DEFAULT ''"),
                    ("company_policies", "TEXT NOT NULL DEFAULT ''"),
                ]
                for col_name, col_type in new_cols:
                    if col_name not in existing_cols:
                        try:
                            connection.execute(f"ALTER TABLE communication_agents ADD COLUMN {col_name} {col_type}")
                        except Exception:
                            pass

                # Migração de colunas do setor Saúde (bancos anteriores)
                _extra = {
                    "patients": [
                        "cns", "background", "family_background",
                        "social_background", "insurance", "emergency_contact",
                        "city",
                    ],
                    "patient_records": ["vitals", "ai_json"],
                }
                for table, cols in _extra.items():
                    try:
                        have = {c[1] for c in connection.execute(
                            f"PRAGMA table_info({table})"
                        ).fetchall()}
                    except Exception:
                        continue
                    for col in cols:
                        if col not in have:
                            try:
                                connection.execute(
                                    f"ALTER TABLE {table} ADD COLUMN {col} TEXT NOT NULL DEFAULT ''"
                                )
                            except Exception:
                                pass

        self._retry(_do)

    def sync_providers(self, providers: dict[str, ProviderConfig]) -> None:
        def _do() -> None:
            self._sync_providers_once(providers)

        self._retry(_do)

    def _sync_providers_once(self, providers: dict[str, ProviderConfig]) -> None:
        with self.session() as connection:
            connection.executemany(
                """
                INSERT INTO providers(name, kind, enabled, model, base_url)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    kind = excluded.kind,
                    enabled = excluded.enabled,
                    model = excluded.model,
                    base_url = excluded.base_url,
                    updated_at = CURRENT_TIMESTAMP
                """,
                [
                    (
                        item.name,
                        item.kind,
                        int(item.enabled),
                        item.model,
                        item.base_url,
                    )
                    for item in providers.values()
                ],
            )

    def create_conversation(self, title: str | None = None) -> int:
        with self.session() as connection:
            cursor = connection.execute(
                "INSERT INTO conversations(title) VALUES (?)", (title,)
            )
            return int(cursor.lastrowid)

    def add_message(
        self,
        conversation_id: int,
        message: Message,
        *,
        provider: str | None = None,
        model: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> int:
        with self.session() as connection:
            cursor = connection.execute(
                """
                INSERT INTO messages(
                    conversation_id, role, content, provider, model, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    conversation_id,
                    message.role,
                    message.content,
                    provider,
                    model,
                    json.dumps(metadata or {}, ensure_ascii=False),
                ),
            )
            connection.execute(
                "UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (conversation_id,),
            )
            return int(cursor.lastrowid)

    def get_messages(self, conversation_id: int) -> list[Message]:
        with self.session() as connection:
            rows = connection.execute(
                """
                SELECT role, content
                FROM messages
                WHERE conversation_id = ?
                ORDER BY id
                """,
                (conversation_id,),
            ).fetchall()
        return [Message(role=row["role"], content=row["content"]) for row in rows]

    # -- historico de conversas (menu "Historico" do chat) --------------
    def list_conversations(self, limit: int = 80) -> list[dict[str, Any]]:
        """Conversas com pelo menos uma troca, mais recentes primeiro."""
        with self.session() as connection:
            rows = connection.execute(
                """
                SELECT c.id, c.title, c.updated_at,
                    (SELECT COUNT(*) FROM messages m
                     WHERE m.conversation_id = c.id
                       AND m.role IN ('user', 'assistant')) AS turns
                FROM conversations c
                ORDER BY c.updated_at DESC, c.id DESC
                LIMIT ?
                """,
                (int(limit),),
            ).fetchall()
        return [
            {
                "id": int(row["id"]),
                "title": (row["title"] or "").strip() or "Conversa sem titulo",
                "updatedAt": row["updated_at"],
                "turns": int(row["turns"]),
            }
            for row in rows
            if row["turns"] > 0
        ]

    def conversation_transcript(self, conversation_id: int) -> list[dict[str, Any]]:
        """user/assistant de uma conversa, para recarregar no chat."""
        with self.session() as connection:
            rows = connection.execute(
                """
                SELECT role, content, provider, model
                FROM messages
                WHERE conversation_id = ? AND role IN ('user', 'assistant')
                ORDER BY id
                """,
                (conversation_id,),
            ).fetchall()
        out: list[dict[str, Any]] = []
        for row in rows:
            label = ""
            if row["role"] == "assistant":
                label = (
                    f"{(row['provider'] or '').upper()} / {row['model'] or ''}"
                ).strip(" /") or "JARVIS"
            out.append(
                {"role": row["role"], "content": row["content"], "label": label}
            )
        return out

    def rename_conversation(self, conversation_id: int, title: str) -> None:
        with self.session() as connection:
            connection.execute(
                "UPDATE conversations SET title = ? WHERE id = ?",
                (title.strip()[:120], conversation_id),
            )

    def delete_conversation(self, conversation_id: int) -> None:
        with self.session() as connection:
            connection.execute(
                "DELETE FROM conversations WHERE id = ?", (conversation_id,)
            )

    def set_setting(self, key: str, value: Any) -> None:
        with self.session() as connection:
            connection.execute(
                """
                INSERT INTO settings(key, value_json) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value_json = excluded.value_json,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (key, json.dumps(value, ensure_ascii=False)),
            )

    def get_setting(self, key: str, default: Any = None) -> Any:
        with self.session() as connection:
            row = connection.execute(
                "SELECT value_json FROM settings WHERE key = ?", (key,)
            ).fetchone()
        return json.loads(row["value_json"]) if row else default

    def delete_setting(self, key: str) -> None:
        with self.session() as connection:
            connection.execute("DELETE FROM settings WHERE key = ?", (key,))

    def stats(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        with self.session() as connection:
            for table in (
                "conversations", "messages", "routines", "appointments", "contacts"
            ):
                try:
                    row = connection.execute(
                        f"SELECT COUNT(*) AS n FROM {table}"
                    ).fetchone()
                    counts[table] = int(row["n"])
                except sqlite3.Error:
                    counts[table] = 0
        return counts

    # -- rotinas de automação ---------------------------------------------
    @staticmethod
    def _row_to_routine(row: sqlite3.Row) -> Routine:
        try:
            steps = tuple(str(item) for item in json.loads(row["steps_json"]))
        except (ValueError, TypeError):
            steps = ()
        return Routine(
            id=int(row["id"]),
            name=row["name"],
            description=row["description"] or "",
            steps=steps,
            enabled=bool(row["enabled"]),
        )

    def list_routines(self) -> list[Routine]:
        with self.session() as connection:
            rows = connection.execute(
                "SELECT id, name, description, steps_json, enabled "
                "FROM routines ORDER BY name COLLATE NOCASE"
            ).fetchall()
        return [self._row_to_routine(row) for row in rows]

    def get_routine(self, identifier: int | str) -> Routine | None:
        column = "id" if isinstance(identifier, int) else "name"
        with self.session() as connection:
            row = connection.execute(
                f"SELECT id, name, description, steps_json, enabled "
                f"FROM routines WHERE {column} = ? COLLATE NOCASE",
                (identifier,),
            ).fetchone()
        return self._row_to_routine(row) if row else None

    def save_routine(self, routine: Routine) -> int:
        steps_json = json.dumps(list(routine.steps), ensure_ascii=False)
        with self.session() as connection:
            if routine.id:
                connection.execute(
                    "UPDATE routines SET name = ?, description = ?, steps_json = ?, "
                    "enabled = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (
                        routine.name,
                        routine.description,
                        steps_json,
                        int(routine.enabled),
                        routine.id,
                    ),
                )
                return int(routine.id)
            cursor = connection.execute(
                "INSERT INTO routines(name, description, steps_json, enabled) "
                "VALUES (?, ?, ?, ?) "
                "ON CONFLICT(name) DO UPDATE SET "
                "description = excluded.description, steps_json = excluded.steps_json, "
                "enabled = excluded.enabled, updated_at = CURRENT_TIMESTAMP",
                (routine.name, routine.description, steps_json, int(routine.enabled)),
            )
            if cursor.lastrowid:
                return int(cursor.lastrowid)
            row = connection.execute(
                "SELECT id FROM routines WHERE name = ?", (routine.name,)
            ).fetchone()
            return int(row["id"])

    def delete_routine(self, routine_id: int) -> None:
        with self.session() as connection:
            connection.execute("DELETE FROM routines WHERE id = ?", (routine_id,))

    # -- agendamentos ----------------------------------------------------
    @staticmethod
    def _row_to_schedule(row: sqlite3.Row) -> Schedule:
        return Schedule(
            id=int(row["id"]),
            routine_id=int(row["routine_id"]),
            kind=row["kind"],
            run_at=row["run_at"],
            time_of_day=row["time_of_day"],
            weekday=row["weekday"] if row["weekday"] is None else int(row["weekday"]),
            enabled=bool(row["enabled"]),
            last_run_at=row["last_run_at"],
        )

    def list_schedules(self) -> list[Schedule]:
        with self.session() as connection:
            rows = connection.execute(
                "SELECT id, routine_id, kind, run_at, time_of_day, weekday, "
                "enabled, last_run_at FROM schedules"
            ).fetchall()
        return [self._row_to_schedule(row) for row in rows]

    def get_schedule(self, routine_id: int) -> Schedule | None:
        with self.session() as connection:
            row = connection.execute(
                "SELECT id, routine_id, kind, run_at, time_of_day, weekday, "
                "enabled, last_run_at FROM schedules WHERE routine_id = ?",
                (routine_id,),
            ).fetchone()
        return self._row_to_schedule(row) if row else None

    def set_schedule(self, schedule: Schedule) -> None:
        with self.session() as connection:
            connection.execute(
                "INSERT INTO schedules("
                "routine_id, kind, run_at, time_of_day, weekday, enabled, last_run_at"
                ") VALUES (?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(routine_id) DO UPDATE SET "
                "kind = excluded.kind, run_at = excluded.run_at, "
                "time_of_day = excluded.time_of_day, weekday = excluded.weekday, "
                "enabled = excluded.enabled, last_run_at = excluded.last_run_at",
                (
                    schedule.routine_id,
                    schedule.kind,
                    schedule.run_at,
                    schedule.time_of_day,
                    schedule.weekday,
                    int(schedule.enabled),
                    schedule.last_run_at,
                ),
            )

    def clear_schedule(self, routine_id: int) -> None:
        with self.session() as connection:
            connection.execute(
                "DELETE FROM schedules WHERE routine_id = ?", (routine_id,)
            )

    def mark_schedule_ran(
        self, schedule_id: int, when: str, *, disable: bool
    ) -> None:
        with self.session() as connection:
            connection.execute(
                "UPDATE schedules SET last_run_at = ?, enabled = ? WHERE id = ?",
                (when, 0 if disable else 1, schedule_id),
            )

    # -- contatos ------------------------------------------------------
    @staticmethod
    def _row_to_contact(row: sqlite3.Row) -> Contact:
        return Contact(
            id=int(row["id"]),
            name=row["name"],
            phone=row["phone"] or "",
            email=row["email"] or "",
            birthday=row["birthday"],
            notes=row["notes"] or "",
            tags=row["tags"] or "",
        )

    def list_contacts(self) -> list[Contact]:
        with self.session() as connection:
            rows = connection.execute(
                "SELECT id, name, phone, email, birthday, notes, tags "
                "FROM contacts ORDER BY name COLLATE NOCASE"
            ).fetchall()
        return [self._row_to_contact(row) for row in rows]

    def get_contact(self, contact_id: int) -> Contact | None:
        with self.session() as connection:
            row = connection.execute(
                "SELECT id, name, phone, email, birthday, notes, tags "
                "FROM contacts WHERE id = ?",
                (contact_id,),
            ).fetchone()
        return self._row_to_contact(row) if row else None

    def find_contacts(self, term: str) -> list[Contact]:
        like = f"%{term.strip()}%"
        with self.session() as connection:
            rows = connection.execute(
                "SELECT id, name, phone, email, birthday, notes, tags FROM contacts "
                "WHERE name LIKE ? OR phone LIKE ? OR email LIKE ? OR tags LIKE ? "
                "ORDER BY name COLLATE NOCASE",
                (like, like, like, like),
            ).fetchall()
        return [self._row_to_contact(row) for row in rows]

    def save_contact(self, contact: Contact) -> int:
        with self.session() as connection:
            if contact.id:
                connection.execute(
                    "UPDATE contacts SET name = ?, phone = ?, email = ?, "
                    "birthday = ?, notes = ?, tags = ?, updated_at = CURRENT_TIMESTAMP "
                    "WHERE id = ?",
                    (
                        contact.name,
                        contact.phone,
                        contact.email,
                        contact.birthday,
                        contact.notes,
                        contact.tags,
                        contact.id,
                    ),
                )
                return int(contact.id)
            cursor = connection.execute(
                "INSERT INTO contacts(name, phone, email, birthday, notes, tags) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    contact.name,
                    contact.phone,
                    contact.email,
                    contact.birthday,
                    contact.notes,
                    contact.tags,
                ),
            )
            return int(cursor.lastrowid)

    def delete_contact(self, contact_id: int) -> None:
        with self.session() as connection:
            connection.execute("DELETE FROM contacts WHERE id = ?", (contact_id,))

    # -- compromissos ------------------------------------------------
    @staticmethod
    def _row_to_appointment(row: sqlite3.Row) -> Appointment:
        return Appointment(
            id=int(row["id"]),
            title=row["title"],
            start_at=row["start_at"],
            end_at=row["end_at"],
            location=row["location"] or "",
            notes=row["notes"] or "",
            contact_id=row["contact_id"] if row["contact_id"] is None
            else int(row["contact_id"]),
            reminder_minutes=int(row["reminder_minutes"]),
            reminded_at=row["reminded_at"],
        )

    def list_appointments(
        self, *, since: str | None = None, until: str | None = None
    ) -> list[Appointment]:
        query = (
            "SELECT id, title, start_at, end_at, location, notes, contact_id, "
            "reminder_minutes, reminded_at FROM appointments"
        )
        clauses: list[str] = []
        params: list[str] = []
        if since is not None:
            clauses.append("start_at >= ?")
            params.append(since)
        if until is not None:
            clauses.append("start_at <= ?")
            params.append(until)
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY start_at"
        with self.session() as connection:
            rows = connection.execute(query, params).fetchall()
        return [self._row_to_appointment(row) for row in rows]

    def get_appointment(self, appointment_id: int) -> Appointment | None:
        with self.session() as connection:
            row = connection.execute(
                "SELECT id, title, start_at, end_at, location, notes, contact_id, "
                "reminder_minutes, reminded_at FROM appointments WHERE id = ?",
                (appointment_id,),
            ).fetchone()
        return self._row_to_appointment(row) if row else None

    def save_appointment(self, appointment: Appointment) -> int:
        with self.session() as connection:
            if appointment.id:
                connection.execute(
                    "UPDATE appointments SET title = ?, start_at = ?, end_at = ?, "
                    "location = ?, notes = ?, contact_id = ?, reminder_minutes = ?, "
                    "reminded_at = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (
                        appointment.title,
                        appointment.start_at,
                        appointment.end_at,
                        appointment.location,
                        appointment.notes,
                        appointment.contact_id,
                        appointment.reminder_minutes,
                        appointment.reminded_at,
                        appointment.id,
                    ),
                )
                return int(appointment.id)
            cursor = connection.execute(
                "INSERT INTO appointments(title, start_at, end_at, location, notes, "
                "contact_id, reminder_minutes, reminded_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    appointment.title,
                    appointment.start_at,
                    appointment.end_at,
                    appointment.location,
                    appointment.notes,
                    appointment.contact_id,
                    appointment.reminder_minutes,
                    appointment.reminded_at,
                ),
            )
            return int(cursor.lastrowid)

    def delete_appointment(self, appointment_id: int) -> None:
        with self.session() as connection:
            connection.execute(
                "DELETE FROM appointments WHERE id = ?", (appointment_id,)
            )

    def mark_appointment_reminded(self, appointment_id: int, when: str) -> None:
        with self.session() as connection:
            connection.execute(
                "UPDATE appointments SET reminded_at = ? WHERE id = ?",
                (when, appointment_id),
            )

    # -- servidores (SSH) ----------------------------------------------
    _SERVER_COLS = (
        "id, alias, host, user, port, auth, key_path, password_enc, notes"
    )

    @staticmethod
    def _row_to_server(row: sqlite3.Row) -> Server:
        return Server(
            id=int(row["id"]),
            alias=row["alias"],
            host=row["host"],
            user=row["user"],
            port=int(row["port"]),
            auth=row["auth"] or "key",
            key_path=row["key_path"] or "",
            password_enc=row["password_enc"] or "",
            notes=row["notes"] or "",
        )

    def list_servers(self) -> list[Server]:
        with self.session() as connection:
            rows = connection.execute(
                f"SELECT {self._SERVER_COLS} FROM servers "
                "ORDER BY alias COLLATE NOCASE"
            ).fetchall()
        return [self._row_to_server(row) for row in rows]

    def get_server(self, server_id: int) -> Server | None:
        with self.session() as connection:
            row = connection.execute(
                f"SELECT {self._SERVER_COLS} FROM servers WHERE id = ?",
                (server_id,),
            ).fetchone()
        return self._row_to_server(row) if row else None

    def find_server(self, alias: str) -> Server | None:
        with self.session() as connection:
            row = connection.execute(
                f"SELECT {self._SERVER_COLS} FROM servers "
                "WHERE alias = ? COLLATE NOCASE",
                (alias.strip(),),
            ).fetchone()
        return self._row_to_server(row) if row else None

    def save_server(self, server: Server) -> int:
        with self.session() as connection:
            if server.id:
                connection.execute(
                    "UPDATE servers SET alias = ?, host = ?, user = ?, port = ?, "
                    "auth = ?, key_path = ?, password_enc = ?, notes = ?, "
                    "updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (
                        server.alias, server.host, server.user, server.port,
                        server.auth, server.key_path, server.password_enc,
                        server.notes, server.id,
                    ),
                )
                return int(server.id)
            cursor = connection.execute(
                "INSERT INTO servers(alias, host, user, port, auth, key_path, "
                "password_enc, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    server.alias, server.host, server.user, server.port,
                    server.auth, server.key_path, server.password_enc, server.notes,
                ),
            )
            return int(cursor.lastrowid)

    def delete_server(self, server_id: int) -> None:
        with self.session() as connection:
            connection.execute("DELETE FROM servers WHERE id = ?", (server_id,))

    def list_ai_agents(self) -> list[dict[str, Any]]:
        with self.session() as connection:
            rows = connection.execute(
                "SELECT id, name, provider, model, api_key, base_url, "
                "system_prompt, temperature, active, created_at, updated_at "
                "FROM ai_agents ORDER BY id DESC"
            ).fetchall()
        return [dict(row) for row in rows]

    def get_ai_agent(self, agent_id: int) -> dict[str, Any] | None:
        with self.session() as connection:
            row = connection.execute(
                "SELECT id, name, provider, model, api_key, base_url, "
                "system_prompt, temperature, active, created_at, updated_at "
                "FROM ai_agents WHERE id = ?",
                (agent_id,),
            ).fetchone()
        return dict(row) if row else None

    def save_ai_agent(self, agent: dict[str, Any]) -> int:
        with self.session() as connection:
            agent_id = agent.get("id")
            name = str(agent.get("name", "Agente")).strip()
            provider = str(agent.get("provider", "OpenAI")).strip()
            model = str(agent.get("model", "gpt-4o-mini")).strip()
            api_key = str(agent.get("api_key", "")).strip()
            base_url = str(agent.get("base_url", "")).strip()
            system_prompt = str(agent.get("system_prompt", "")).strip()
            temperature = float(agent.get("temperature", 0.7))
            active = 1 if agent.get("active", True) else 0

            if agent_id:
                connection.execute(
                    "UPDATE ai_agents SET name = ?, provider = ?, model = ?, "
                    "api_key = ?, base_url = ?, system_prompt = ?, temperature = ?, "
                    "active = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (
                        name, provider, model, api_key, base_url,
                        system_prompt, temperature, active, int(agent_id),
                    ),
                )
                return int(agent_id)

            cursor = connection.execute(
                "INSERT INTO ai_agents(name, provider, model, api_key, base_url, "
                "system_prompt, temperature, active) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (name, provider, model, api_key, base_url, system_prompt, temperature, active),
            )
            return int(cursor.lastrowid)

    def delete_ai_agent(self, agent_id: int) -> None:
        with self.session() as connection:
            connection.execute("DELETE FROM ai_agents WHERE id = ?", (int(agent_id),))

    # ---------------------------------------------- Communication Agents CRUD
    def list_communication_agents(self) -> list[dict[str, Any]]:
        with self.session() as connection:
            rows = connection.execute(
                "SELECT id, name, age, gender, role, model_id, model_name, "
                "tone, formality, emoji_level, response_style, language, "
                "job_description, responsibilities, company_name, company_segment, "
                "company_description, company_products, company_target_audience, "
                "company_regions, company_business_hours, company_payment_methods, "
                "company_policies, company_info, active, created_at, updated_at "
                "FROM communication_agents ORDER BY id DESC"
            ).fetchall()
        return [dict(row) for row in rows]

    def get_communication_agent(self, agent_id: int) -> dict[str, Any] | None:
        with self.session() as connection:
            row = connection.execute(
                "SELECT id, name, age, gender, role, model_id, model_name, "
                "tone, formality, emoji_level, response_style, language, "
                "job_description, responsibilities, company_name, company_segment, "
                "company_description, company_products, company_target_audience, "
                "company_regions, company_business_hours, company_payment_methods, "
                "company_policies, company_info, active, created_at, updated_at "
                "FROM communication_agents WHERE id = ?",
                (agent_id,),
            ).fetchone()
        return dict(row) if row else None

    def save_communication_agent(self, agent: dict[str, Any]) -> int:
        with self.session() as connection:
            agent_id = agent.get("id")
            name = str(agent.get("name", "Agente de IA")).strip()
            age = str(agent.get("age", "")).strip()
            gender = str(agent.get("gender", "")).strip()
            role = str(agent.get("role", "")).strip()
            model_id = agent.get("model_id")
            model_name = str(agent.get("model_name", "")).strip()
            tone = str(agent.get("tone", "")).strip()
            formality = str(agent.get("formality", "")).strip()
            emoji_level = str(agent.get("emoji_level", "Normal")).strip()
            response_style = str(agent.get("response_style", "")).strip()
            language = str(agent.get("language", "Português (Brasil)")).strip()
            job_description = str(agent.get("job_description", "")).strip()
            responsibilities = str(agent.get("responsibilities", "[]")).strip()
            company_name = str(agent.get("company_name", "")).strip()
            company_segment = str(agent.get("company_segment", "")).strip()
            company_description = str(agent.get("company_description", "")).strip()
            company_products = str(agent.get("company_products", "")).strip()
            company_target_audience = str(agent.get("company_target_audience", "")).strip()
            company_regions = str(agent.get("company_regions", "")).strip()
            company_business_hours = str(agent.get("company_business_hours", "")).strip()
            company_payment_methods = str(agent.get("company_payment_methods", "")).strip()
            company_policies = str(agent.get("company_policies", "")).strip()
            company_info = str(agent.get("company_info", "")).strip()
            active = 1 if agent.get("active", True) else 0

            if agent_id:
                connection.execute(
                    "UPDATE communication_agents SET name = ?, age = ?, gender = ?, "
                    "role = ?, model_id = ?, model_name = ?, tone = ?, formality = ?, "
                    "emoji_level = ?, response_style = ?, language = ?, job_description = ?, "
                    "responsibilities = ?, company_name = ?, company_segment = ?, "
                    "company_description = ?, company_products = ?, company_target_audience = ?, "
                    "company_regions = ?, company_business_hours = ?, company_payment_methods = ?, "
                    "company_policies = ?, company_info = ?, "
                    "active = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (
                        name, age, gender, role, model_id, model_name,
                        tone, formality, emoji_level, response_style, language,
                        job_description, responsibilities, company_name, company_segment,
                        company_description, company_products, company_target_audience,
                        company_regions, company_business_hours, company_payment_methods,
                        company_policies, company_info,
                        active, int(agent_id),
                    ),
                )
                return int(agent_id)

            cursor = connection.execute(
                "INSERT INTO communication_agents(name, age, gender, role, model_id, "
                "model_name, tone, formality, emoji_level, response_style, language, "
                "job_description, responsibilities, company_name, company_segment, "
                "company_description, company_products, company_target_audience, "
                "company_regions, company_business_hours, company_payment_methods, "
                "company_policies, company_info, active) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    name, age, gender, role, model_id, model_name,
                    tone, formality, emoji_level, response_style, language,
                    job_description, responsibilities, company_name, company_segment,
                    company_description, company_products, company_target_audience,
                    company_regions, company_business_hours, company_payment_methods,
                    company_policies, company_info, active,
                ),
            )
            return int(cursor.lastrowid)

    def delete_communication_agent(self, agent_id: int) -> None:
        with self.session() as connection:
            connection.execute("DELETE FROM communication_agents WHERE id = ?", (int(agent_id),))

    # ---------------------------------------------- Memória & Cognição Global do Sistema Jarvis
    def list_user_memories(self, category: str | None = None) -> list[dict[str, Any]]:
        with self.session() as connection:
            if category:
                rows = connection.execute(
                    "SELECT id, category, key, content, confidence, access_count, "
                    "source, created_at, updated_at FROM user_memories "
                    "WHERE category = ? ORDER BY access_count DESC, id DESC",
                    (category,),
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT id, category, key, content, confidence, access_count, "
                    "source, created_at, updated_at FROM user_memories "
                    "ORDER BY access_count DESC, id DESC"
                ).fetchall()
        return [dict(row) for row in rows]

    def get_user_memory(self, memory_id: int) -> dict[str, Any] | None:
        with self.session() as connection:
            row = connection.execute(
                "SELECT id, category, key, content, confidence, access_count, "
                "source, created_at, updated_at FROM user_memories WHERE id = ?",
                (memory_id,),
            ).fetchone()
        return dict(row) if row else None

    def save_user_memory(self, memory: dict[str, Any]) -> int:
        with self.session() as connection:
            memory_id = memory.get("id")
            category = str(memory.get("category", "fato")).strip()
            key = str(memory.get("key", "")).strip()
            content = str(memory.get("content", "")).strip()
            confidence = float(memory.get("confidence", 1.0))
            source = str(memory.get("source", "chat")).strip()

            if memory_id:
                connection.execute(
                    "UPDATE user_memories SET category = ?, key = ?, content = ?, "
                    "confidence = ?, source = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (category, key, content, confidence, source, int(memory_id)),
                )
                return int(memory_id)

            # Check if matching key exists
            existing = None
            if key:
                existing = connection.execute(
                    "SELECT id FROM user_memories WHERE key = ?", (key,)
                ).fetchone()

            if existing:
                connection.execute(
                    "UPDATE user_memories SET category = ?, content = ?, confidence = ?, "
                    "access_count = access_count + 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (category, content, confidence, existing["id"]),
                )
                return int(existing["id"])

            cursor = connection.execute(
                "INSERT INTO user_memories(category, key, content, confidence, source) "
                "VALUES (?, ?, ?, ?, ?)",
                (category, key, content, confidence, source),
            )
            return int(cursor.lastrowid)

    def delete_user_memory(self, memory_id: int) -> None:
        with self.session() as connection:
            connection.execute("DELETE FROM user_memories WHERE id = ?", (int(memory_id),))

    def clear_user_memories(self) -> None:
        with self.session() as connection:
            connection.execute("DELETE FROM user_memories")

    def increment_memory_access(self, memory_ids: list[int]) -> None:
        if not memory_ids:
            return
        with self.session() as connection:
            placeholders = ",".join("?" for _ in memory_ids)
            connection.execute(
                f"UPDATE user_memories SET access_count = access_count + 1, updated_at = CURRENT_TIMESTAMP "
                f"WHERE id IN ({placeholders})",
                tuple(memory_ids),
            )

    def search_user_memories(self, query: str, limit: int = 15) -> list[dict[str, Any]]:
        clean_q = f"%{query.strip()}%"
        with self.session() as connection:
            rows = connection.execute(
                "SELECT id, category, key, content, confidence, access_count, source, created_at, updated_at "
                "FROM user_memories WHERE key LIKE ? OR content LIKE ? "
                "ORDER BY access_count DESC, id DESC LIMIT ?",
                (clean_q, clean_q, limit),
            ).fetchall()
        return [dict(row) for row in rows]

    # ---------------------------------------------- Aprendizagem Comportamental
    def get_behavior_profile(self) -> dict[str, Any]:
        with self.session() as connection:
            rows = connection.execute(
                "SELECT feature, value, score, updated_at FROM user_behavior_profile"
            ).fetchall()
        return {row["feature"]: {"value": row["value"], "score": row["score"], "updated_at": row["updated_at"]} for row in rows}

    def set_behavior_feature(self, feature: str, value: str, score: float = 1.0) -> None:
        with self.session() as connection:
            connection.execute(
                "INSERT INTO user_behavior_profile(feature, value, score, updated_at) "
                "VALUES (?, ?, ?, CURRENT_TIMESTAMP) "
                "ON CONFLICT(feature) DO UPDATE SET value = excluded.value, "
                "score = excluded.score, updated_at = CURRENT_TIMESTAMP",
                (feature, value, float(score)),
            )

    def log_behavior_action(self, action_type: str, action_payload: str = "") -> None:
        with self.session() as connection:
            connection.execute(
                "INSERT INTO user_behavior_logs(action_type, action_payload) VALUES (?, ?)",
                (action_type, action_payload),
            )

    def get_recent_behavior_logs(self, limit: int = 100) -> list[dict[str, Any]]:
        with self.session() as connection:
            rows = connection.execute(
                "SELECT id, action_type, action_payload, created_at "
                "FROM user_behavior_logs ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    # ---------------------------------------------- Lembrança Perfeita & Recall de Histórico
    def search_conversation_messages(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        """Busca em todas as mensagens de todas as conversas salvas no banco."""
        clean_q = f"%{query.strip()}%"
        with self.session() as connection:
            rows = connection.execute(
                "SELECT m.id, m.conversation_id, m.role, m.content, m.created_at, c.title AS conversation_title "
                "FROM messages m "
                "LEFT JOIN conversations c ON c.id = m.conversation_id "
                "WHERE m.content LIKE ? "
                "ORDER BY m.id DESC LIMIT ?",
                (clean_q, limit),
            ).fetchall()
        return [dict(row) for row in rows]

    # ---------------------------------------------- Personalização Total do Assistente
    def get_assistant_persona(self) -> dict[str, Any]:
        with self.session() as connection:
            row = connection.execute(
                "SELECT name, personality, tone, accent, tts_voice, tts_rate, tts_volume, "
                "custom_instructions, updated_at FROM assistant_persona WHERE id = 1"
            ).fetchone()
        if row:
            return dict(row)
        return {
            "name": "Jarvis",
            "personality": "Prestativo e Amigável",
            "tone": "Natural",
            "accent": "Português (Brasil)",
            "tts_voice": "",
            "tts_rate": 180,
            "tts_volume": 1.0,
            "custom_instructions": "",
        }

    def save_assistant_persona(self, persona: dict[str, Any]) -> None:
        with self.session() as connection:
            connection.execute(
                "INSERT INTO assistant_persona(id, name, personality, tone, accent, "
                "tts_voice, tts_rate, tts_volume, custom_instructions, updated_at) "
                "VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP) "
                "ON CONFLICT(id) DO UPDATE SET "
                "name = excluded.name, personality = excluded.personality, "
                "tone = excluded.tone, accent = excluded.accent, "
                "tts_voice = excluded.tts_voice, tts_rate = excluded.tts_rate, "
                "tts_volume = excluded.tts_volume, "
                "custom_instructions = excluded.custom_instructions, "
                "updated_at = CURRENT_TIMESTAMP",
                (
                    str(persona.get("name", "Jarvis")).strip() or "Jarvis",
                    str(persona.get("personality", "Prestativo e Amigável")).strip(),
                    str(persona.get("tone", "Natural")).strip(),
                    str(persona.get("accent", "Português (Brasil)")).strip(),
                    str(persona.get("tts_voice", "")).strip(),
                    int(persona.get("tts_rate", 180)),
                    float(persona.get("tts_volume", 1.0)),
                    str(persona.get("custom_instructions", "")).strip(),
                ),
            )

    # ---------------------------------------------- Integração MCP (Model Context Protocol)
    def list_mcp_servers(self) -> list[dict[str, Any]]:
        with self.session() as connection:
            rows = connection.execute(
                "SELECT id, name, command, args, env_vars, enabled, created_at, updated_at "
                "FROM mcp_servers ORDER BY name ASC"
            ).fetchall()
        return [dict(row) for row in rows]

    def save_mcp_server(self, server: dict[str, Any]) -> int:
        server_id = server.get("id")
        name = str(server.get("name", "")).strip()
        command = str(server.get("command", "")).strip()
        args = str(server.get("args", "[]")).strip()
        env_vars = str(server.get("env_vars", "{}")).strip()
        enabled = 1 if server.get("enabled", True) else 0

        with self.session() as connection:
            if server_id:
                connection.execute(
                    "UPDATE mcp_servers SET name = ?, command = ?, args = ?, env_vars = ?, "
                    "enabled = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (name, command, args, env_vars, enabled, int(server_id)),
                )
                return int(server_id)

            cursor = connection.execute(
                "INSERT INTO mcp_servers(name, command, args, env_vars, enabled) "
                "VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT(name) DO UPDATE SET "
                "command = excluded.command, args = excluded.args, "
                "env_vars = excluded.env_vars, enabled = excluded.enabled, "
                "updated_at = CURRENT_TIMESTAMP",
                (name, command, args, env_vars, enabled),
            )
            return int(cursor.lastrowid or 0)

    def delete_mcp_server(self, server_id: int) -> None:
        with self.session() as connection:
            connection.execute("DELETE FROM mcp_servers WHERE id = ?", (int(server_id),))

    # ---------------------------------------------- Setor Saúde: pacientes
    _PATIENT_FIELDS = (
        "name", "birthdate", "sex", "phone", "email", "document", "cns",
        "blood_type", "allergies", "conditions", "medications", "background",
        "family_background", "social_background", "insurance",
        "emergency_contact", "city", "notes",
    )
    _PATIENT_COLS = "id, " + ", ".join(_PATIENT_FIELDS) + ", created_at, updated_at"

    def list_patients(self, search: str = "") -> list[dict[str, Any]]:
        with self.session() as connection:
            if search.strip():
                like = f"%{search.strip()}%"
                rows = connection.execute(
                    f"SELECT {self._PATIENT_COLS} FROM patients "
                    "WHERE name LIKE ? OR document LIKE ? OR phone LIKE ? "
                    "ORDER BY name COLLATE NOCASE",
                    (like, like, like),
                ).fetchall()
            else:
                rows = connection.execute(
                    f"SELECT {self._PATIENT_COLS} FROM patients "
                    "ORDER BY name COLLATE NOCASE"
                ).fetchall()
        return [dict(r) for r in rows]

    def get_patient(self, patient_id: int) -> dict[str, Any] | None:
        with self.session() as connection:
            row = connection.execute(
                f"SELECT {self._PATIENT_COLS} FROM patients WHERE id = ?",
                (int(patient_id),),
            ).fetchone()
        return dict(row) if row else None

    def save_patient(self, patient: dict[str, Any]) -> int:
        pid = patient.get("id")
        vals = tuple(str(patient.get(k, "") or "").strip() for k in self._PATIENT_FIELDS)
        with self.session() as connection:
            if pid:
                sets = ", ".join(f"{k}=?" for k in self._PATIENT_FIELDS)
                connection.execute(
                    f"UPDATE patients SET {sets}, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                    (*vals, int(pid)),
                )
                return int(pid)
            cols = ", ".join(self._PATIENT_FIELDS)
            qs = ", ".join("?" for _ in self._PATIENT_FIELDS)
            cursor = connection.execute(
                f"INSERT INTO patients({cols}) VALUES ({qs})", vals
            )
            return int(cursor.lastrowid or 0)

    def delete_patient(self, patient_id: int) -> None:
        with self.session() as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("DELETE FROM patients WHERE id = ?", (int(patient_id),))

    _RECORD_COLS = (
        "id, patient_id, kind, title, body, occurred_at, vitals, ai_summary, "
        "ai_flags, ai_json, created_at, updated_at"
    )

    def list_patient_records(self, patient_id: int) -> list[dict[str, Any]]:
        with self.session() as connection:
            rows = connection.execute(
                f"SELECT {self._RECORD_COLS} FROM patient_records WHERE patient_id = ? "
                "ORDER BY (occurred_at = '') ASC, occurred_at DESC, id DESC",
                (int(patient_id),),
            ).fetchall()
        return [dict(r) for r in rows]

    def get_patient_record(self, record_id: int) -> dict[str, Any] | None:
        with self.session() as connection:
            row = connection.execute(
                f"SELECT {self._RECORD_COLS} FROM patient_records WHERE id = ?",
                (int(record_id),),
            ).fetchone()
        return dict(row) if row else None

    def save_patient_record(self, record: dict[str, Any]) -> int:
        rid = record.get("id")
        vals = (
            str(record.get("kind", "nota")).strip() or "nota",
            str(record.get("title", "")).strip(),
            str(record.get("body", "")).strip(),
            str(record.get("occurred_at", "")).strip(),
            str(record.get("vitals", "")).strip(),
        )
        with self.session() as connection:
            if rid:
                connection.execute(
                    "UPDATE patient_records SET kind=?, title=?, body=?, "
                    "occurred_at=?, vitals=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                    (*vals, int(rid)),
                )
                return int(rid)
            cursor = connection.execute(
                "INSERT INTO patient_records(patient_id, kind, title, body, "
                "occurred_at, vitals) VALUES (?, ?, ?, ?, ?, ?)",
                (int(record["patient_id"]), *vals),
            )
            return int(cursor.lastrowid or 0)

    def set_record_ai(self, record_id: int, summary: str, flags: str, ai_json: str = "") -> None:
        with self.session() as connection:
            connection.execute(
                "UPDATE patient_records SET ai_summary=?, ai_flags=?, ai_json=?, "
                "updated_at=CURRENT_TIMESTAMP WHERE id=?",
                (summary, flags, ai_json, int(record_id)),
            )

    def delete_patient_record(self, record_id: int) -> None:
        with self.session() as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute(
                "DELETE FROM patient_records WHERE id = ?", (int(record_id),)
            )

    def list_record_files(self, record_id: int) -> list[dict[str, Any]]:
        with self.session() as connection:
            rows = connection.execute(
                "SELECT id, record_id, patient_id, name, path, mime, size, "
                "extracted_text, created_at FROM patient_files WHERE record_id = ? "
                "ORDER BY id",
                (int(record_id),),
            ).fetchall()
        return [dict(r) for r in rows]

    def add_record_file(self, file: dict[str, Any]) -> int:
        with self.session() as connection:
            cursor = connection.execute(
                "INSERT INTO patient_files(record_id, patient_id, name, path, mime, "
                "size, extracted_text) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    int(file["record_id"]), int(file["patient_id"]),
                    str(file.get("name", "")), str(file.get("path", "")),
                    str(file.get("mime", "")), int(file.get("size", 0)),
                    str(file.get("extracted_text", "")),
                ),
            )
            return int(cursor.lastrowid or 0)

    def get_record_file(self, file_id: int) -> dict[str, Any] | None:
        with self.session() as connection:
            row = connection.execute(
                "SELECT id, record_id, patient_id, name, path, mime, size, "
                "extracted_text, created_at FROM patient_files WHERE id = ?",
                (int(file_id),),
            ).fetchone()
        return dict(row) if row else None

    def delete_record_file(self, file_id: int) -> None:
        with self.session() as connection:
            connection.execute(
                "DELETE FROM patient_files WHERE id = ?", (int(file_id),)
            )

