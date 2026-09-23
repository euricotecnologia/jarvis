import tempfile
import unittest
from pathlib import Path

from jarvis.cognition import CognitiveEngine
from jarvis.database import Database


class PersonaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.db = Database(Path(tempfile.mkdtemp()) / "t.db")
        self.db.initialize()

    def test_default_persona(self) -> None:
        p = self.db.get_assistant_persona()
        self.assertEqual(p["name"], "Jarvis")
        self.assertIn("tts_rate", p)

    def test_save_and_prompt(self) -> None:
        self.db.save_assistant_persona({
            "name": "Sexta-feira",
            "personality": "Bem-humorado",
            "tone": "Animado",
            "accent": "Português (Brasil)",
            "tts_voice": "Maria",
            "tts_rate": 200,
            "tts_volume": 0.8,
            "custom_instructions": "Me chame de chefe.",
        })
        p = self.db.get_assistant_persona()
        self.assertEqual(p["name"], "Sexta-feira")
        self.assertEqual(p["tts_rate"], 200)
        self.assertEqual(p["tts_voice"], "Maria")

        prompt = CognitiveEngine(self.db).get_persona_prompt()
        self.assertIn("Sexta-feira", prompt)
        self.assertIn("Bem-humorado", prompt)
        self.assertIn("Me chame de chefe", prompt)

    def test_name_never_empty(self) -> None:
        self.db.save_assistant_persona({"name": "   "})
        self.assertEqual(self.db.get_assistant_persona()["name"], "Jarvis")


if __name__ == "__main__":
    unittest.main()
