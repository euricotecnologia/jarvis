import asyncio
import tempfile
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path

from jarvis.agenda import (
    birthday_label,
    birthday_on,
    combine_fields,
    day_label,
    describe_reminder,
    describe_when,
    format_agenda,
    parse_birthday,
    reminder_due,
)
from jarvis.config import AgentConfig
from jarvis.database import Database
from jarvis.models import Appointment, Contact
from jarvis.tools.agenda import (
    ConsultarAgenda,
    SalvarCompromisso,
    SalvarContato,
)
from jarvis.tools.context import ToolContext


class HelperTests(unittest.TestCase):
    def test_combine_fields(self) -> None:
        self.assertEqual(combine_fields("31/08/2026", "15:30"), "2026-08-31T15:30")
        with self.assertRaises(ValueError):
            combine_fields("bla", "15:30")

    def test_day_label(self) -> None:
        today = date(2026, 8, 31)
        self.assertEqual(day_label(today, today), "Hoje")
        self.assertEqual(day_label(today + timedelta(days=1), today), "Amanhã")

    def test_describe_reminder(self) -> None:
        self.assertEqual(describe_reminder(-1), "Sem lembrete")
        self.assertEqual(describe_reminder(60), "1 hora antes")
        self.assertEqual(describe_reminder(1440), "1 dia antes")

    def test_describe_when_includes_countdown(self) -> None:
        now = datetime(2026, 8, 31, 14, 30)
        appt = Appointment(title="x", start_at="2026-08-31T15:00")
        self.assertIn("em 30 min", describe_when(appt, now))

    def test_reminder_due(self) -> None:
        appt = Appointment(
            title="x", start_at="2026-08-31T15:00", reminder_minutes=15
        )
        self.assertFalse(reminder_due(appt, datetime(2026, 8, 31, 14, 30)))
        self.assertTrue(reminder_due(appt, datetime(2026, 8, 31, 14, 46)))
        done = Appointment(
            title="x",
            start_at="2026-08-31T15:00",
            reminder_minutes=15,
            reminded_at="2026-08-31T14:46:00",
        )
        self.assertFalse(reminder_due(done, datetime(2026, 8, 31, 14, 50)))
        never = Appointment(
            title="x", start_at="2026-08-31T15:00", reminder_minutes=-1
        )
        self.assertFalse(reminder_due(never, datetime(2026, 8, 31, 14, 59)))

    def test_birthday(self) -> None:
        self.assertEqual(parse_birthday("03-14"), (3, 14, None))
        self.assertEqual(parse_birthday("1990-03-14"), (3, 14, 1990))
        self.assertIsNone(parse_birthday("nope"))
        self.assertTrue(birthday_on("03-14", date(2027, 3, 14)))
        self.assertEqual(
            birthday_label("08-31", date(2026, 8, 31)), "Aniversário hoje"
        )
        self.assertIn(
            "faz 36", birthday_label("1990-09-02", date(2026, 8, 31)) or ""
        )

    def test_format_agenda_empty(self) -> None:
        self.assertIn("Nenhum", format_agenda([], {}, datetime.now()))


class AgendaToolTests(unittest.TestCase):
    def _ctx(self, db: Database) -> ToolContext:
        return ToolContext(config=AgentConfig(enabled=True), database=db)

    def test_save_and_query(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as directory:
            db = Database(Path(directory) / "jarvis.db")
            db.initialize()
            ctx = self._ctx(db)

            tomorrow = (datetime.now() + timedelta(days=1)).strftime("%d/%m/%Y")
            result = asyncio.run(
                SalvarCompromisso().execute(
                    {"titulo": "Dentista", "data": tomorrow, "hora": "09:00"}, ctx
                )
            )
            self.assertTrue(result.ok)
            self.assertEqual(len(db.list_appointments()), 1)

            query = asyncio.run(
                ConsultarAgenda().execute({"periodo": "semana"}, ctx)
            )
            self.assertIn("Dentista", query.content)

    def test_save_contact(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as directory:
            db = Database(Path(directory) / "jarvis.db")
            db.initialize()
            ctx = self._ctx(db)
            result = asyncio.run(
                SalvarContato().execute(
                    {"nome": "Maria", "telefone": "11999998888", "aniversario": "14/03"},
                    ctx,
                )
            )
            self.assertTrue(result.ok)
            saved = db.list_contacts()[0]
            self.assertEqual(saved.name, "Maria")
            self.assertEqual(saved.birthday, "03-14")

    def test_tool_requires_database(self) -> None:
        ctx = ToolContext(config=AgentConfig(enabled=True), database=None)
        result = asyncio.run(ConsultarAgenda().run({"periodo": "hoje"}, ctx))
        self.assertFalse(result.ok)


class ContactStoreTests(unittest.TestCase):
    def test_crud_and_cascade(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as directory:
            db = Database(Path(directory) / "jarvis.db")
            db.initialize()
            cid = db.save_contact(Contact(name="Ana", phone="123"))
            aid = db.save_appointment(
                Appointment(title="call", start_at="2026-08-31T10:00", contact_id=cid)
            )
            self.assertEqual(db.get_appointment(aid).contact_id, cid)
            db.delete_contact(cid)
            # ON DELETE SET NULL
            self.assertIsNone(db.get_appointment(aid).contact_id)
            self.assertEqual(db.find_contacts("Ana"), [])


if __name__ == "__main__":
    unittest.main()
