import unittest

from jarvis.artifacts import extract_code_blocks


class ExtractCodeBlocksTests(unittest.TestCase):
    def test_no_fence_returns_text_unchanged(self) -> None:
        text = "Ola, aqui esta a resposta sem codigo."
        clean, blocks = extract_code_blocks(text)
        self.assertEqual(clean, text)
        self.assertEqual(blocks, [])

    def test_html_block_becomes_previewable_artifact(self) -> None:
        text = (
            "Segue a pagina:\n\n"
            "```html\n<!doctype html>\n<h1>Oi</h1>\n```\n\n"
            "Abra no navegador."
        )
        clean, blocks = extract_code_blocks(text)
        self.assertEqual(len(blocks), 1)
        block = blocks[0]
        self.assertEqual(block.language, "html")
        self.assertTrue(block.previewable)
        self.assertEqual(block.filename, "pagina.html")
        self.assertIn("<h1>Oi</h1>", block.code)
        self.assertIn("‹código: pagina.html›", clean)
        self.assertNotIn("```", clean)

    def test_filename_hint_from_info_line(self) -> None:
        text = "```python meu_script.py\nprint('oi')\nprint('tchau')\n```"
        _, blocks = extract_code_blocks(text)
        self.assertEqual(blocks[0].filename, "meu_script.py")
        self.assertEqual(blocks[0].language, "python")

    def test_multiple_same_language_get_unique_names(self) -> None:
        text = (
            "```python\nfor i in range(10):\n    print(i)\n```\n"
            "```python\nx = 1 + 2 + 3\nprint(x)\n```"
        )
        _, blocks = extract_code_blocks(text)
        self.assertEqual(blocks[0].filename, "script.py")
        self.assertEqual(blocks[1].filename, "script-2.py")

    def test_short_inline_snippet_is_not_an_artifact(self) -> None:
        text = "Use o comando `ls` ou ```pip install``` para instalar."
        clean, blocks = extract_code_blocks(text)
        self.assertEqual(blocks, [])
        self.assertIn("pip install", clean)

    def test_unknown_language_falls_back_to_generic_name(self) -> None:
        text = "```\nlinha um do arquivo\nlinha dois do arquivo\n```"
        _, blocks = extract_code_blocks(text)
        self.assertEqual(blocks[0].filename, "codigo.txt")
        self.assertFalse(blocks[0].previewable)

    def test_as_dict_shape(self) -> None:
        text = "```json\n{\n  \"a\": 1\n}\n```"
        _, blocks = extract_code_blocks(text)
        data = blocks[0].as_dict()
        self.assertEqual(
            set(data), {"language", "code", "filename", "previewable"}
        )
        self.assertEqual(data["filename"], "dados.json")


if __name__ == "__main__":
    unittest.main()
