import json
import tempfile
import unittest
from pathlib import Path

from jarvis import toolbox
from jarvis.toolbox import ToolboxError, available_utilities, extract_text_from, run_utility


class RegistryTests(unittest.TestCase):
    def test_every_utility_has_an_impl(self) -> None:
        for spec in available_utilities():
            self.assertIn(spec["id"], toolbox._IMPL, spec["id"])
            self.assertIn(spec["category"], {"documentos", "imagens", "dados", "ia"})

    def test_unknown_utility(self) -> None:
        result = run_utility("nao_existe", {})
        self.assertFalse(result["ok"])

    def test_ai_without_runner(self) -> None:
        result = run_utility("ai_summarize", {"arquivo": "x"}, ai_runner=None)
        self.assertFalse(result["ok"])
        self.assertIn("IA", result["message"])


class DataUtilitiesTests(unittest.TestCase):
    def test_csv_to_json(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as directory:
            csv_path = Path(directory) / "t.csv"
            csv_path.write_text("nome,idade\nAna,30\nBia,25\n", encoding="utf-8")
            result = run_utility("csv_to_json", {"arquivo": str(csv_path)})
            self.assertTrue(result["ok"])
            data = json.loads(Path(result["outputPath"]).read_text(encoding="utf-8"))
            self.assertEqual(data[0]["nome"], "Ana")

    def test_json_format_minify(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as directory:
            path = Path(directory) / "t.json"
            path.write_text('{\n  "a": 1\n}', encoding="utf-8")
            result = run_utility("json_format", {"arquivo": str(path), "modo": "Minificar"})
            self.assertTrue(result["ok"])
            self.assertEqual(
                Path(result["outputPath"]).read_text(encoding="utf-8"), '{"a":1}'
            )

    def test_json_format_invalid(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as directory:
            path = Path(directory) / "bad.json"
            path.write_text("{nao e json}", encoding="utf-8")
            result = run_utility("json_format", {"arquivo": str(path), "modo": "Formatar"})
        self.assertFalse(result["ok"])
        self.assertIn("invalido", result["message"].lower())

    def test_file_hash_and_stats(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as directory:
            path = Path(directory) / "t.txt"
            path.write_text("uma frase\noutra linha\n", encoding="utf-8")
            hashed = run_utility("file_hash", {"arquivo": str(path)})
            stats = run_utility("text_stats", {"arquivo": str(path)})
        self.assertIn("SHA-256", hashed["text"])
        self.assertIn("Palavras:   4", stats["text"])
        self.assertIn("Linhas:     2", stats["text"])

    def test_password_gen_length_and_symbols(self) -> None:
        no_sym = run_utility("password_gen", {"tamanho": "24", "simbolos": "Nao"})
        self.assertEqual(len(no_sym["text"]), 24)
        self.assertTrue(no_sym["text"].isalnum())

    def test_missing_file(self) -> None:
        result = run_utility("file_hash", {"arquivo": "/nao/existe/zzz.bin"})
        self.assertFalse(result["ok"])


class ExtractTextTests(unittest.TestCase):
    def test_txt(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as directory:
            path = Path(directory) / "a.md"
            path.write_text("conteudo", encoding="utf-8")
            self.assertEqual(extract_text_from(path), "conteudo")

    def test_empty_raises(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as directory:
            path = Path(directory) / "a.txt"
            path.write_text("   \n  ", encoding="utf-8")
            with self.assertRaises(ToolboxError):
                extract_text_from(path)

    def test_truncation(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as directory:
            path = Path(directory) / "big.txt"
            path.write_text("x" * 5000, encoding="utf-8")
            out = extract_text_from(path, limit=100)
        self.assertLess(len(out), 200)
        self.assertIn("truncado", out)


class AiUtilitiesTests(unittest.TestCase):
    def test_ai_summarize_uses_runner_and_saves(self) -> None:
        calls: list[tuple[str, str]] = []

        def fake_ai(system: str, user: str) -> str:
            calls.append((system, user))
            return "RESUMO: ok"

        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as directory:
            path = Path(directory) / "doc.txt"
            path.write_text("um texto qualquer para resumir", encoding="utf-8")
            result = run_utility("ai_summarize", {"arquivo": str(path)}, ai_runner=fake_ai)
            self.assertTrue(result["ok"])
            self.assertEqual(result["text"], "RESUMO: ok")
            self.assertTrue(Path(result["outputPath"]).name.endswith("_resumo.md"))
            self.assertEqual(len(calls), 1)

    def test_ai_translate_target_language_in_prompt(self) -> None:
        seen: dict[str, str] = {}

        def fake_ai(system: str, user: str) -> str:
            seen["system"] = system
            return "translated"

        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as directory:
            path = Path(directory) / "d.txt"
            path.write_text("ola", encoding="utf-8")
            run_utility("ai_translate", {"arquivo": str(path), "idioma": "Espanhol"}, ai_runner=fake_ai)
        self.assertIn("Espanhol", seen["system"])


class PdfEditorTests(unittest.TestCase):
    def test_pdf_editor_utility_registration(self) -> None:
        utils = {u["id"]: u for u in available_utilities()}
        self.assertIn("pdf_editor", utils)
        self.assertEqual(utils["pdf_editor"]["category"], "documentos")

    def test_export_and_load_pdf(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as directory:
            out_file = Path(directory) / "test_doc.pdf"
            html_content = "<h1>Documento de Teste</h1><p>Paragrafo formatado com <b>negrito</b>.</p>"
            result = toolbox.export_text_to_pdf(html_content, output_path=str(out_file))
            self.assertTrue(result["ok"])
            self.assertTrue(out_file.exists())

            # Test loading it back
            loaded = toolbox.load_pdf_pages(str(out_file))
            self.assertTrue(loaded["ok"])
            self.assertGreaterEqual(loaded["pageCount"], 1)
            self.assertIn("Documento de Teste", loaded["fullText"])


if __name__ == "__main__":
    unittest.main()
