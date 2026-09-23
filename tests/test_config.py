import tempfile
import unittest
from pathlib import Path

from jarvis.config import load_config


class ConfigTests(unittest.TestCase):
    def test_defaults_are_local_first(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config = load_config(Path(directory) / "missing.toml")
        self.assertEqual(config.default_provider, "ollama")
        self.assertTrue(config.providers["ollama"].enabled)
        self.assertFalse(config.providers["openai"].enabled)
        self.assertIn("gemini", config.providers)
        self.assertEqual(config.voice.tts_engine, "windows")
