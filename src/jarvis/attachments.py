"""Anexos do chat: imagens e documentos (PDF, Word, Excel, txt, csv...).

O usuário anexa um arquivo pelo botão de clipe; a IA recebe o conteúdo junto
com a mensagem. Documentos viram texto (extraido localmente); imagens são
normalizadas para JPEG e descritas pelo provedor de visão configurado.
Nada e enviado para fora além do provedor de IA ja escolhido.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from importlib import import_module
from pathlib import Path

from jarvis.errors import JarvisError

MAX_BYTES = 25 * 1024 * 1024          # 25 MB por arquivo
TEXT_LIMIT = 20_000                   # caracteres de texto por documento
IMAGE_MAX_EDGE = 1600                 # px -- reduz imagens grandes antes de enviar

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tif", ".tiff"}
DOC_SUFFIXES = {
    ".pdf", ".docx", ".txt", ".md", ".markdown", ".rst", ".log",
    ".csv", ".tsv", ".json", ".xml", ".yaml", ".yml", ".ini",
    ".xlsx", ".xlsm",
}
_PLAIN_SUFFIXES = {
    ".txt", ".md", ".markdown", ".rst", ".log", ".csv", ".tsv",
    ".json", ".xml", ".yaml", ".yml", ".ini", "",
}


class AttachmentError(JarvisError):
    """Falha previsivel ao ler um anexo (vira aviso amigavel no chat)."""


@dataclass(frozen=True, slots=True)
class Attachment:
    path: str
    name: str
    kind: str                 # "image" | "document"
    size: int
    text: str = ""            # texto extraido (documentos)
    jpeg: bytes = field(default=b"", repr=False)  # imagem normalizada
    width: int = 0
    height: int = 0
    error: str = ""

    @property
    def ok(self) -> bool:
        return not self.error

    def as_dict(self) -> dict[str, object]:
        return {
            "path": self.path,
            "name": self.name,
            "kind": self.kind,
            "size": self.size,
            "sizeLabel": human_size(self.size),
            "hasText": bool(self.text),
            "error": self.error,
        }


def human_size(num: int) -> str:
    step = float(num)
    for unit in ("B", "KB", "MB", "GB"):
        if step < 1024 or unit == "GB":
            return f"{step:.0f} {unit}" if unit == "B" else f"{step:.1f} {unit}"
        step /= 1024
    return f"{num} B"


def classify(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in IMAGE_SUFFIXES:
        return "image"
    return "document"


def load_attachment(raw: str) -> Attachment:
    """Le um arquivo e devolve um Attachment pronto para ir para a IA.

    Nunca levanta exceção: erros previsiveis vao no campo `error`.
    """
    path = Path(str(raw)).expanduser()
    name = path.name or str(path)
    kind = classify(path)
    try:
        if not path.is_file():
            raise AttachmentError("arquivo não encontrado")
        size = path.stat().st_size
        if size > MAX_BYTES:
            raise AttachmentError(
                f"muito grande ({human_size(size)}); limite {human_size(MAX_BYTES)}"
            )
        if kind == "image":
            jpeg, width, height = _normalize_image(path)
            return Attachment(
                path=str(path), name=name, kind="image", size=size,
                jpeg=jpeg, width=width, height=height,
            )
        text = _read_document(path)
        return Attachment(
            path=str(path), name=name, kind="document", size=size, text=text,
        )
    except AttachmentError as exc:
        return Attachment(
            path=str(path), name=name, kind=kind,
            size=_safe_size(path), error=str(exc),
        )
    except Exception as exc:  # noqa: BLE001
        return Attachment(
            path=str(path), name=name, kind=kind,
            size=_safe_size(path), error=f"não consegui ler: {exc}",
        )


def _safe_size(path: Path) -> int:
    try:
        return path.stat().st_size
    except OSError:
        return 0


def _normalize_image(path: Path) -> tuple[bytes, int, int]:
    try:
        Image = import_module("PIL.Image")
    except Exception as exc:  # noqa: BLE001
        raise AttachmentError(
            "suporte a imagens indisponível (instale o extra .[tools])"
        ) from exc
    import io

    with Image.open(str(path)) as img:
        img = img.convert("RGB")
        longest = max(img.size)
        if longest > IMAGE_MAX_EDGE:
            scale = IMAGE_MAX_EDGE / longest
            new_size = (round(img.width * scale), round(img.height * scale))
            resample = getattr(Image, "Resampling", Image).LANCZOS
            img = img.resize(new_size, resample)
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=85)
        return buffer.getvalue(), img.width, img.height


def _read_document(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".xlsx", ".xlsm"}:
        text = _read_xlsx(path)
    elif suffix == ".xls":
        raise AttachmentError("converta o .xls para .xlsx e anexe de novo")
    elif suffix == ".doc":
        raise AttachmentError("converta o .doc para .docx e anexe de novo")
    elif suffix in {".pdf", ".docx"}:
        text = _read_via_toolbox(path)
    elif suffix in _PLAIN_SUFFIXES:
        text = path.read_text(encoding="utf-8", errors="replace")
    else:
        raise AttachmentError(f"não sei ler arquivos {suffix or 'sem extensão'}")
    text = (text or "").strip()
    if not text:
        raise AttachmentError("nenhum texto encontrado no arquivo")
    if len(text) > TEXT_LIMIT:
        text = text[:TEXT_LIMIT] + "\n\n[documento cortado para caber no limite]"
    return text


def _read_via_toolbox(path: Path) -> str:
    from jarvis.toolbox import ToolboxError, extract_text_from

    try:
        return extract_text_from(path)
    except ToolboxError as exc:
        raise AttachmentError(str(exc)) from exc
    except ModuleNotFoundError as exc:
        raise AttachmentError(
            "falta uma biblioteca para este formato (instale o extra .[tools])"
        ) from exc


def _read_xlsx(path: Path) -> str:
    try:
        openpyxl = import_module("openpyxl")
    except Exception as exc:  # noqa: BLE001
        raise AttachmentError(
            "leitura de Excel indisponível (instale o extra .[tools])"
        ) from exc

    workbook = openpyxl.load_workbook(str(path), read_only=True, data_only=True)
    lines: list[str] = []
    try:
        for sheet in workbook.worksheets:
            lines.append(f"## Planilha: {sheet.title}")
            rows = 0
            for row in sheet.iter_rows(values_only=True):
                cells = ["" if value is None else str(value) for value in row]
                if any(cell.strip() for cell in cells):
                    lines.append(" | ".join(cells).rstrip(" |"))
                    rows += 1
                if rows >= 400:
                    lines.append("[... planilha longa, linhas restantes omitidas]")
                    break
            lines.append("")
    finally:
        workbook.close()
    return "\n".join(lines)


def compose_prompt(text: str, attachments: list[Attachment], *, describe=None) -> str:
    """Junta a mensagem do usuário com o conteúdo dos anexos.

    `describe(question, attachment) -> str` (opcional) analisa imagens; se não
    vier ou falhar, a imagem entra so com o nome.
    """
    if not attachments:
        return text
    blocks: list[str] = []
    for att in attachments:
        if att.error:
            blocks.append(f"[Anexo \"{att.name}\": não consegui ler -- {att.error}]")
        elif att.kind == "document":
            blocks.append(f"[Documento anexado: {att.name}]\n{att.text}")
        else:  # image
            description = ""
            if describe is not None:
                try:
                    description = (describe(text, att) or "").strip()
                except Exception as exc:  # noqa: BLE001
                    description = f"(não consegui analisar a imagem: {exc})"
            blocks.append(
                f"[Imagem anexada: {att.name}]"
                + (f"\n{description}" if description else "")
            )
    joined = "\n\n".join(blocks)
    if text.strip():
        return f"{text.strip()}\n\n---\n{joined}"
    return joined
