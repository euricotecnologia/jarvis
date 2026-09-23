import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jarvis.database import Database
from jarvis.secret_store import (
    delete_secret,
    restore_secret_to_environment,
    save_secret,
    secret_configured,
)


class SecretStoreTests(unittest.TestCase):
    def _fresh_db(self, directory: str) -> Database:
        database = Database(Path(directory) / "jarvis.db")
        database.initialize()
        return database

    @patch("jarvis.secret_store._read_legacy_keyring", return_value=None)
    def test_secret_round_trips_through_sqlite_only(self, _legacy) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as directory:
            database = self._fresh_db(directory)
            os.environ.pop("GEMINI_API_KEY", None)

            save_secret(database, "GEMINI_API_KEY", "  segredo-abc  ")
            self.assertEqual(os.environ["GEMINI_API_KEY"], "segredo-abc")

            stored = database.get_setting("secret::GEMINI_API_KEY")
            self.assertIsInstance(stored, str)
            self.assertNotIn("segredo-abc", stored)  # cifrado, nao em texto puro
            self.assertTrue(secret_configured(database, "GEMINI_API_KEY"))

            os.environ.pop("GEMINI_API_KEY", None)
            self.assertTrue(
                restore_secret_to_environment(database, "GEMINI_API_KEY")
            )
            self.assertEqual(os.environ["GEMINI_API_KEY"], "segredo-abc")

            delete_secret(database, "GEMINI_API_KEY")
            self.assertIsNone(database.get_setting("secret::GEMINI_API_KEY"))
            self.assertNotIn("GEMINI_API_KEY", os.environ)

    @patch("jarvis.secret_store._read_legacy_keyring", return_value=None)
    def test_missing_secret_is_not_configured(self, _legacy) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as directory:
            database = self._fresh_db(directory)
            os.environ.pop("ANTHROPIC_API_KEY", None)
            self.assertFalse(secret_configured(database, "ANTHROPIC_API_KEY"))
            self.assertFalse(
                restore_secret_to_environment(database, "ANTHROPIC_API_KEY")
            )

    @patch(
        "jarvis.secret_store._read_legacy_keyring",
        return_value="chave-antiga-do-windows",
    )
    def test_legacy_keyring_secret_is_migrated_into_sqlite(self, _legacy) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as directory:
            database = self._fresh_db(directory)
            os.environ.pop("OPENAI_API_KEY", None)
            self.assertTrue(
                restore_secret_to_environment(database, "OPENAI_API_KEY")
            )
            self.assertEqual(os.environ["OPENAI_API_KEY"], "chave-antiga-do-windows")
            self.assertTrue(secret_configured(database, "OPENAI_API_KEY"))
            delete_secret(database, "OPENAI_API_KEY")


if __name__ == "__main__":
    unittest.main()
