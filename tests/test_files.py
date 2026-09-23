import tempfile
import unittest
from pathlib import Path

from jarvis.files import (
    format_size,
    list_directory,
    preview,
    quick_access,
    search_by_name,
    search_in_files,
)


class FormatSizeTests(unittest.TestCase):
    def test_units(self) -> None:
        self.assertEqual(format_size(512), "512 B")
        self.assertEqual(format_size(2048), "2 KB")
        self.assertEqual(format_size(5 * 1024 * 1024), "5.0 MB")


class ListDirectoryTests(unittest.TestCase):
    def _tree(self, root: Path) -> None:
        (root / "sub").mkdir()
        (root / "sub" / "deep.txt").write_text("ola mundo", encoding="utf-8")
        (root / "a.txt").write_text("conteudo A", encoding="utf-8")
        (root / "b.py").write_text("print('oi')\n", encoding="utf-8")

    def test_lists_dirs_first_and_sorted(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as directory:
            root = Path(directory)
            self._tree(root)
            result = list_directory(str(root))
        self.assertTrue(result["ok"])
        names = [e["name"] for e in result["entries"]]
        self.assertEqual(names, ["sub", "a.txt", "b.py"])
        self.assertTrue(result["entries"][0]["isDir"])
        self.assertEqual(result["entries"][2]["kind"], "code")
        self.assertTrue(result["parent"])

    def test_missing_folder(self) -> None:
        result = list_directory(str(Path(tempfile.gettempdir()) / "nao_existe_zzz"))
        self.assertFalse(result["ok"])
        self.assertIn("não encontrada", result["error"].lower())

    def test_file_is_not_a_folder(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as directory:
            f = Path(directory) / "x.txt"
            f.write_text("x", encoding="utf-8")
            result = list_directory(str(f))
        self.assertFalse(result["ok"])


class SearchTests(unittest.TestCase):
    def test_search_by_name_recurses(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as directory:
            root = Path(directory)
            (root / "sub").mkdir()
            (root / "sub" / "relatorio_final.txt").write_text("x", encoding="utf-8")
            (root / "outro.txt").write_text("x", encoding="utf-8")
            result = search_by_name(str(root), "relatorio")
        self.assertTrue(result["ok"])
        self.assertEqual(len(result["entries"]), 1)
        self.assertEqual(result["entries"][0]["name"], "relatorio_final.txt")

    def test_search_in_files_finds_line(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as directory:
            root = Path(directory)
            (root / "notas.md").write_text(
                "linha um\nsegredo aqui\nlinha tres\n", encoding="utf-8"
            )
            result = search_in_files(str(root), "segredo")
        self.assertTrue(result["ok"])
        self.assertEqual(result["matches"][0]["line"], 2)
        self.assertIn("segredo", result["matches"][0]["text"])

    def test_search_empty_query(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as directory:
            self.assertFalse(search_by_name(directory, "  ")["ok"])


class PreviewTests(unittest.TestCase):
    def test_text_preview(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as directory:
            f = Path(directory) / "a.txt"
            f.write_text("linha 1\nlinha 2", encoding="utf-8")
            result = preview(str(f))
        self.assertEqual(result["kind"], "text")
        self.assertIn("linha 1", result["text"])

    def test_missing_file(self) -> None:
        result = preview(str(Path(tempfile.gettempdir()) / "nada_zzz.txt"))
        self.assertEqual(result["kind"], "none")

    def test_binary_detection(self) -> None:
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as directory:
            f = Path(directory) / "bin.dat"
            f.write_bytes(b"\x00\x01\x02binary\x00stuff")
            # sem extensao conhecida -> "other"; com \x00 no txt seria "other" tb
            g = Path(directory) / "weird.txt"
            g.write_bytes(b"texto\x00nulo")
            self.assertEqual(preview(str(g))["kind"], "other")


class QuickAccessTests(unittest.TestCase):
    def test_has_home(self) -> None:
        items = quick_access()
        self.assertTrue(any(i["label"] == "Inicio" for i in items))
        self.assertTrue(all("path" in i for i in items))


if __name__ == "__main__":
    unittest.main()
