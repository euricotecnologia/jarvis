import sqlite3
import tempfile
import unittest
from pathlib import Path

from jarvis.database import Database
from jarvis.errors import DatabaseUnavailable
from jarvis.models import Message, Server


class DatabaseTests(unittest.TestCase):
    def test_conversation_is_persisted(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as directory:
            database = Database(Path(directory) / "jarvis.db")
            database.initialize()
            conversation_id = database.create_conversation("Teste")
            database.add_message(
                conversation_id, Message(role="user", content="Ola, Jarvis")
            )
            database.add_message(
                conversation_id, Message(role="assistant", content="Ola!")
            )
            messages = database.get_messages(conversation_id)

        self.assertEqual([item.role for item in messages], ["user", "assistant"])
        self.assertEqual(messages[0].content, "Ola, Jarvis")

    def test_settings_round_trip(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as directory:
            database = Database(Path(directory) / "jarvis.db")
            database.initialize()
            database.set_setting("voice", {"language": "pt-BR"})
            value = database.get_setting("voice")
        self.assertEqual(value, {"language": "pt-BR"})

    def test_retry_recovers_from_transient_io_error(self) -> None:
        database = Database(Path(tempfile.gettempdir()) / "unused.db")
        attempts = {"n": 0}

        def flaky() -> str:
            attempts["n"] += 1
            if attempts["n"] < 3:
                raise sqlite3.OperationalError("disk I/O error")
            return "done"

        self.assertEqual(database._retry(flaky), "done")
        self.assertEqual(attempts["n"], 3)

    def test_retry_gives_friendly_error_when_persistent(self) -> None:
        database = Database(Path("D:/nope/jarvis.db"))

        def always_locked() -> None:
            raise sqlite3.OperationalError("disk I/O error")

        with self.assertRaises(DatabaseUnavailable):
            database._retry(always_locked)

    def test_retry_passes_through_real_errors(self) -> None:
        database = Database(Path("x"))

        def broken() -> None:
            raise sqlite3.OperationalError("no such table: foo")

        with self.assertRaises(sqlite3.OperationalError):
            database._retry(broken)

    def test_servers_crud(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as directory:
            database = Database(Path(directory) / "jarvis.db")
            database.initialize()
            new_id = database.save_server(
                Server(
                    alias="vps", host="1.2.3.4", user="root", port=2222,
                    auth="key", key_path="~/.ssh/id_ed25519",
                )
            )
            self.assertGreater(new_id, 0)
            self.assertEqual(database.find_server("VPS").host, "1.2.3.4")
            self.assertEqual(database.get_server(new_id).port, 2222)

            database.save_server(
                Server(id=new_id, alias="vps", host="9.9.9.9", user="ubuntu",
                       port=22, auth="password", password_enc="blob")
            )
            updated = database.get_server(new_id)
            self.assertEqual(updated.user, "ubuntu")
            self.assertEqual(updated.auth, "password")
            self.assertEqual(updated.password_enc, "blob")

            database.delete_server(new_id)
            self.assertIsNone(database.get_server(new_id))
            self.assertEqual(database.list_servers(), [])

    def test_conversation_history_list_and_transcript(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as directory:
            db = Database(Path(directory) / "jarvis.db")
            db.initialize()
            empty = db.create_conversation("So um titulo")
            chat = db.create_conversation("Como faco um bolo")
            db.add_message(chat, Message(role="user", content="me ensina um bolo"))
            db.add_message(
                chat, Message(role="assistant", content="Bata os ovos..."),
                provider="lmstudio", model="qwen3",
            )
            db.add_message(chat, Message(role="system", content="ignora isso"))

            listed = db.list_conversations()
            self.assertEqual([c["id"] for c in listed], [chat])  # 'empty' sem trocas
            self.assertEqual(listed[0]["turns"], 2)
            self.assertEqual(listed[0]["title"], "Como faco um bolo")
            self.assertNotIn(empty, [c["id"] for c in listed])

            transcript = db.conversation_transcript(chat)
            self.assertEqual([m["role"] for m in transcript], ["user", "assistant"])
            self.assertEqual(transcript[1]["label"], "LMSTUDIO / qwen3")

    def test_delete_and_rename_conversation(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as directory:
            db = Database(Path(directory) / "jarvis.db")
            db.initialize()
            cid = db.create_conversation("titulo velho")
            db.add_message(cid, Message(role="user", content="oi"))
            db.add_message(cid, Message(role="assistant", content="ola"))
            db.rename_conversation(cid, "titulo novo")
            self.assertEqual(db.list_conversations()[0]["title"], "titulo novo")
            db.delete_conversation(cid)
            self.assertEqual(db.list_conversations(), [])
            self.assertEqual(db.get_messages(cid), [])  # cascade

    def test_server_alias_is_unique(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as directory:
            database = Database(Path(directory) / "jarvis.db")
            database.initialize()
            database.save_server(Server(alias="a", host="h", user="u"))
            with self.assertRaises(sqlite3.IntegrityError):
                database.save_server(Server(alias="a", host="h2", user="u2"))

    def test_theme_setting_persistence(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as directory:
            database = Database(Path(directory) / "jarvis.db")
            database.initialize()
            database.set_setting("theme", {"mode": "claro"})
            self.assertEqual(database.get_setting("theme"), {"mode": "claro"})
            database.set_setting("theme", {"mode": "escuro"})
            self.assertEqual(database.get_setting("theme"), {"mode": "escuro"})

    def test_system_name_setting_persistence(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as directory:
            database = Database(Path(directory) / "jarvis.db")
            database.initialize()
            database.set_setting("runtime_preferences", {"system_name": "Sexta-Feira"})
            self.assertEqual(
                database.get_setting("runtime_preferences"),
                {"system_name": "Sexta-Feira"},
            )
            database.set_setting("runtime_preferences", {"system_name": "Jarvis"})
            self.assertEqual(
                database.get_setting("runtime_preferences"),
                {"system_name": "Jarvis"},
            )



