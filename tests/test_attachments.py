import tempfile
import unittest
from pathlib import Path

from jarvis import attachments


def _tmp() -> Path:
    return Path(tempfile.mkdtemp())


class LoadAttachmentTests(unittest.TestCase):
    def test_text_document(self) -> None:
        path = _tmp() / "nota.txt"
        path.write_text("linha um\nlinha dois", encoding="utf-8")
        att = attachments.load_attachment(str(path))
        self.assertTrue(att.ok)
        self.assertEqual(att.kind, "document")
        self.assertIn("linha dois", att.text)
        self.assertEqual(att.as_dict()["name"], "nota.txt")

    def test_csv_document(self) -> None:
        path = _tmp() / "dados.csv"
        path.write_text("a,b\n1,2", encoding="utf-8")
        att = attachments.load_attachment(str(path))
        self.assertTrue(att.ok)
        self.assertIn("1,2", att.text)

    def test_xlsx_document(self) -> None:
        openpyxl = __import__("openpyxl")
        path = _tmp() / "plan.xlsx"
        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.title = "Vendas"
        sheet.append(["Produto", "Total"])
        sheet.append(["Cafe", 12])
        workbook.save(str(path))
        att = attachments.load_attachment(str(path))
        self.assertTrue(att.ok)
        self.assertIn("Vendas", att.text)
        self.assertIn("Cafe | 12", att.text)

    def test_image_is_normalized_to_jpeg(self) -> None:
        Image = __import__("PIL.Image", fromlist=["Image"])
        path = _tmp() / "foto.png"
        Image.new("RGB", (4000, 200), (5, 10, 15)).save(str(path))
        att = attachments.load_attachment(str(path))
        self.assertTrue(att.ok)
        self.assertEqual(att.kind, "image")
        self.assertTrue(att.jpeg.startswith(b"\xff\xd8"))
        self.assertLessEqual(max(att.width, att.height), attachments.IMAGE_MAX_EDGE)

    def test_missing_file_sets_error(self) -> None:
        att = attachments.load_attachment(str(_tmp() / "sumido.pdf"))
        self.assertFalse(att.ok)
        self.assertIn("não encontrado", att.error)

    def test_oversized_file_rejected(self) -> None:
        path = _tmp() / "grande.txt"
        path.write_bytes(b"x" * 16)
        original = attachments.MAX_BYTES
        attachments.MAX_BYTES = 8
        try:
            att = attachments.load_attachment(str(path))
        finally:
            attachments.MAX_BYTES = original
        self.assertFalse(att.ok)
        self.assertIn("grande", att.error)

    def test_legacy_office_asks_for_conversion(self) -> None:
        path = _tmp() / "velho.xls"
        path.write_bytes(b"\xd0\xcf\x11\xe0stub")
        att = attachments.load_attachment(str(path))
        self.assertFalse(att.ok)
        self.assertIn("xlsx", att.error)

    def test_text_is_truncated(self) -> None:
        path = _tmp() / "longo.txt"
        path.write_text("a" * (attachments.TEXT_LIMIT + 500), encoding="utf-8")
        att = attachments.load_attachment(str(path))
        self.assertTrue(att.ok)
        self.assertIn("cortado", att.text)
        self.assertLess(len(att.text), attachments.TEXT_LIMIT + 200)


class ComposePromptTests(unittest.TestCase):
    def _doc(self, name: str, text: str) -> attachments.Attachment:
        return attachments.Attachment(
            path=name, name=name, kind="document", size=len(text), text=text
        )

    def test_no_attachments_returns_text(self) -> None:
        self.assertEqual(attachments.compose_prompt("oi", []), "oi")

    def test_document_text_is_appended(self) -> None:
        out = attachments.compose_prompt(
            "resuma", [self._doc("a.txt", "conteudo do arquivo")]
        )
        self.assertIn("resuma", out)
        self.assertIn("[Documento anexado: a.txt]", out)
        self.assertIn("conteudo do arquivo", out)

    def test_image_uses_describe_callback(self) -> None:
        image = attachments.Attachment(
            path="x.png", name="x.png", kind="image", size=10, jpeg=b"\xff\xd8"
        )
        out = attachments.compose_prompt(
            "o que e isso?", [image], describe=lambda q, att: "um gato preto"
        )
        self.assertIn("[Imagem anexada: x.png]", out)
        self.assertIn("um gato preto", out)

    def test_describe_failure_is_contained(self) -> None:
        image = attachments.Attachment(
            path="x.png", name="x.png", kind="image", size=10, jpeg=b"\xff\xd8"
        )

        def boom(_q, _a):
            raise RuntimeError("sem visao")

        out = attachments.compose_prompt("ve", [image], describe=boom)
        self.assertIn("não consegui analisar", out)

    def test_errored_attachment_is_noted(self) -> None:
        bad = attachments.Attachment(
            path="b.pdf", name="b.pdf", kind="document", size=0,
            error="arquivo nao encontrado",
        )
        out = attachments.compose_prompt("leia", [bad])
        self.assertIn("não consegui ler", out)
        self.assertIn("b.pdf", out)


if __name__ == "__main__":
    unittest.main()
