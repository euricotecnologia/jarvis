"""Caixa de ferramentas do menu Análises: converter, extrair, resumir, etc.

Cada utilitario roda 100% local (as de IA usam o provedor ja configurado). A
saída vai sempre para um ARQUIVO NOVO ao lado do original -- nunca sobrescreve.
Dependencias pesadas (pymupdf, pillow, python-docx, pdf2docx) ficam no extra
`.[tools]`; um utilitario sem sua lib avisa "instale X".
"""

from __future__ import annotations

import base64
import csv
import hashlib
import importlib.util
import json
import secrets
import string
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from typing import Any, Callable

from jarvis.errors import JarvisError


class ToolboxError(JarvisError):
    """Falha previsivel de um utilitario (vira mensagem amigavel na interface)."""


AiRunner = Callable[[str, str], str]  # (system_prompt, user_content) -> resposta

_TEXT_SUFFIXES = {".txt", ".md", ".markdown", ".rst", ".log", ".csv", ".json", ".xml", ".yaml", ".yml"}
_AI_CHAR_LIMIT = 16000


@dataclass(frozen=True, slots=True)
class Field:
    key: str
    label: str
    kind: str  # file | files | text | choice | int
    accept: str = ""
    choices: tuple[str, ...] = ()
    default: str = ""
    placeholder: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "label": self.label,
            "kind": self.kind,
            "accept": self.accept,
            "choices": list(self.choices),
            "default": self.default,
            "placeholder": self.placeholder,
        }


@dataclass(frozen=True, slots=True)
class Utility:
    id: str
    name: str
    description: str
    category: str  # documentos | imagens | dados | ia
    fields: tuple[Field, ...] = ()
    needs: tuple[str, ...] = ()
    ai: bool = False

    def available(self) -> bool:
        return all(importlib.util.find_spec(module) is not None for module in self.needs)

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "fields": [item.as_dict() for item in self.fields],
            "needs": list(self.needs),
            "ai": self.ai,
            "available": self.available(),
        }


_PDF = ("PDF (*.pdf)",)
_IMG = ("Imagens (*.png *.jpg *.jpeg *.webp *.bmp *.tiff)",)
_DOC = ("Documentos (*.pdf *.docx *.txt *.md)",)

UTILITIES: tuple[Utility, ...] = (
    # -------- documentos --------
    Utility(
        "pdf_to_word", "PDF para Word", "Converte um PDF em .docx mantendo o texto e o layout.",
        "documentos", (Field("arquivo", "Arquivo PDF", "file", "PDF (*.pdf)"),),
        needs=("pdf2docx",),
    ),
    Utility(
        "extract_text", "Extrair texto", "Tira todo o texto de um PDF ou Word e salva em .txt.",
        "documentos", (Field("arquivo", "Arquivo PDF ou Word", "file", "PDF ou Word (*.pdf *.docx)"),),
        needs=("fitz", "docx"),
    ),
    Utility(
        "pdf_merge", "Juntar PDFs", "Une varios PDFs em um so, na ordem escolhida.",
        "documentos", (Field("arquivos", "PDFs para juntar", "files", "PDF (*.pdf)"),),
        needs=("fitz",),
    ),
    Utility(
        "pdf_split", "Dividir PDF", "Gera um arquivo separado para cada página do PDF.",
        "documentos", (Field("arquivo", "Arquivo PDF", "file", "PDF (*.pdf)"),),
        needs=("fitz",),
    ),
    Utility(
        "pdf_extract_pages", "Extrair páginas", "Cria um novo PDF so com as páginas indicadas.",
        "documentos",
        (
            Field("arquivo", "Arquivo PDF", "file", "PDF (*.pdf)"),
            Field("paginas", "Páginas (ex.: 1-3,5,8)", "text", placeholder="1-3,5"),
        ),
        needs=("fitz",),
    ),
    Utility(
        "pdf_to_images", "PDF para imagens", "Salva cada página do PDF como uma imagem PNG.",
        "documentos",
        (
            Field("arquivo", "Arquivo PDF", "file", "PDF (*.pdf)"),
            Field("dpi", "Qualidade (DPI)", "int", default="150"),
        ),
        needs=("fitz",),
    ),
    Utility(
        "images_to_pdf", "Imagens para PDF", "Junta varias imagens em um único PDF.",
        "documentos", (Field("arquivos", "Imagens", "files", "Imagens (*.png *.jpg *.jpeg *.webp)"),),
        needs=("PIL",),
    ),
    Utility(
        "pdf_editor", "Editar PDF", "Editor rico para abrir, formatar, modificar texto e salvar PDFs.",
        "documentos", (Field("arquivo", "Arquivo PDF (opcional)", "file", "PDF (*.pdf)"),),
        needs=("fitz",),
    ),
    # -------- imagens --------
    Utility(
        "image_convert", "Converter imagem", "Troca o formato de uma imagem (PNG, JPG, WEBP...).",
        "imagens",
        (
            Field("arquivo", "Imagem", "file", "Imagens (*.png *.jpg *.jpeg *.webp *.bmp *.tiff)"),
            Field("formato", "Novo formato", "choice", choices=("PNG", "JPEG", "WEBP", "BMP")),
        ),
        needs=("PIL",),
    ),
    Utility(
        "image_resize", "Redimensionar imagem", "Altera largura / altura mantendo a proporção.",
        "imagens",
        (
            Field("arquivo", "Imagem", "file", "Imagens (*.png *.jpg *.jpeg *.webp *.bmp *.tiff)"),
            Field("largura", "Largura (px)", "int", default="1280"),
            Field("altura", "Altura (px, 0 = auto)", "int", default="0"),
        ),
        needs=("PIL",),
    ),
    Utility(
        "image_compress", "Comprimir imagem", "Diminui o tamanho do arquivo ajustando a qualidade.",
        "imagens",
        (
            Field("arquivo", "Imagem", "file", "Imagens (*.png *.jpg *.jpeg *.webp *.bmp *.tiff)"),
            Field("qualidade", "Qualidade (1-100)", "int", default="80"),
        ),
        needs=("PIL",),
    ),
    Utility(
        "image_strip_metadata", "Remover metadados", "Tira EXIF, GPS e dados de camera da imagem.",
        "imagens", (Field("arquivo", "Imagem", "file", "Imagens (*.png *.jpg *.jpeg *.webp *.bmp *.tiff)"),),
        needs=("PIL",),
    ),
    # -------- dados --------
    Utility(
        "csv_to_json", "CSV para JSON", "Converte uma planilha CSV em arquivo JSON estruturado.",
        "dados", (Field("arquivo", "Arquivo CSV", "file", "CSV (*.csv *.tsv)"),),
    ),
    Utility(
        "json_format", "Formatar JSON", "Deixa um JSON identado e legivel (ou minificado).",
        "dados",
        (
            Field("arquivo", "Arquivo JSON", "file", "JSON (*.json)"),
            Field("modo", "Modo", "choice", choices=("Formatar", "Minificar")),
        ),
    ),
    Utility(
        "file_hash", "Hash de arquivo", "Calcula SHA-256 e MD5 para conferir integridade.",
        "dados", (Field("arquivo", "Qualquer arquivo", "file"),),
    ),
    Utility(
        "text_stats", "Contar palavras", "Conta palavras, linhas e caracteres de um arquivo de texto.",
        "dados", (Field("arquivo", "Arquivo de texto", "file", "Texto (*.txt *.md *.csv *.log)"),),
    ),
    Utility(
        "password_gen", "Gerar senha", "Cria uma senha forte e aleatoria.",
        "dados",
        (
            Field("tamanho", "Tamanho", "int", default="20"),
            Field("simbolos", "Incluir simbolos", "choice", choices=("Sim", "Nao")),
        ),
    ),
    # -------- ia --------
    Utility(
        "ai_summarize", "Resumir documento", "Le um PDF/Word/TXT e escreve um resumo em topicos.",
        "ia", (Field("arquivo", "Documento", "file", "Documentos (*.pdf *.docx *.txt *.md)"),),
        ai=True,
    ),
    Utility(
        "ai_translate", "Traduzir documento", "Traduz o conteúdo de um documento para outro idioma.",
        "ia",
        (
            Field("arquivo", "Documento", "file", "Documentos (*.pdf *.docx *.txt *.md)"),
            Field("idioma", "Idioma de destino", "choice", choices=(
                "Inglês", "Espanhol", "Francês", "Alemão", "Italiano",
                "Português", "Japonês", "Chinês", "Russo", "Árabe", "Coreano", "Holandês"
            )),
        ),
        ai=True,
    ),
    Utility(
        "ai_action_items", "Extrair tarefas", "Lista os itens de ação / pendencias de uma ata ou texto.",
        "ia", (Field("arquivo", "Documento", "file", "Documentos (*.pdf *.docx *.txt *.md)"),),
        ai=True,
    ),
    Utility(
        "ai_explain_code", "Explicar código", "Explica em português o que um arquivo de código faz.",
        "ia", (Field("arquivo", "Arquivo de código", "file"),),
        ai=True,
    ),
)

_BY_ID = {item.id: item for item in UTILITIES}


def available_utilities() -> list[dict[str, Any]]:
    return [item.as_dict() for item in UTILITIES]


# --------------------------------------------------------------------------
def _unique(path: Path) -> Path:
    if not path.exists():
        return path
    counter = 2
    while True:
        candidate = path.with_name(f"{path.stem} ({counter}){path.suffix}")
        if not candidate.exists():
            return candidate
        counter += 1


def _need_file(params: dict[str, Any], key: str = "arquivo") -> Path:
    raw = str(params.get(key, "")).strip()
    if not raw:
        raise ToolboxError("Escolha um arquivo.")
    path = Path(raw).expanduser()
    if not path.is_file():
        raise ToolboxError(f"Arquivo não encontrado: {path}")
    return path


def _need_files(params: dict[str, Any], key: str = "arquivos") -> list[Path]:
    raw = params.get(key) or []
    if isinstance(raw, str):
        raw = [piece for piece in raw.split("\n") if piece.strip()]
    paths = [Path(str(item)).expanduser() for item in raw]
    paths = [item for item in paths if item.is_file()]
    if not paths:
        raise ToolboxError("Escolha pelo menos um arquivo.")
    return paths


def _int(params: dict[str, Any], key: str, default: int) -> int:
    try:
        return int(str(params.get(key, default)).strip() or default)
    except ValueError:
        return default


def extract_text_from(path: Path, *, limit: int | None = None) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        fitz = import_module("fitz")
        with fitz.open(str(path)) as document:
            text = "\n\n".join(page.get_text() for page in document)
    elif suffix == ".docx":
        docx = import_module("docx")
        document = docx.Document(str(path))
        text = "\n".join(paragraph.text for paragraph in document.paragraphs)
    elif suffix in _TEXT_SUFFIXES or suffix == "":
        text = path.read_text(encoding="utf-8", errors="replace")
    else:
        raise ToolboxError(f"Não sei ler texto de arquivos {suffix or 'sem extensão'}.")
    text = text.strip()
    if not text:
        raise ToolboxError("Não encontrei texto neste arquivo.")
    if limit and len(text) > limit:
        text = text[:limit] + "\n\n[documento truncado para caber no limite]"
    return text


def _parse_ranges(spec: str, total: int) -> list[int]:
    pages: list[int] = []
    for chunk in spec.replace(" ", "").split(","):
        if not chunk:
            continue
        if "-" in chunk:
            start, _, end = chunk.partition("-")
            for number in range(int(start), int(end) + 1):
                if 1 <= number <= total and number not in pages:
                    pages.append(number)
        else:
            number = int(chunk)
            if 1 <= number <= total and number not in pages:
                pages.append(number)
    if not pages:
        raise ToolboxError("Nenhuma página valida no intervalo informado.")
    return pages


# ---- implementações ----
def _pdf_to_word(params, _ai):
    import logging

    logging.getLogger("pdf2docx").setLevel(logging.ERROR)
    source = _need_file(params)
    target = _unique(source.with_suffix(".docx"))
    Converter = import_module("pdf2docx").Converter
    converter = Converter(str(source))
    try:
        converter.convert(str(target))
    finally:
        converter.close()
    return {"ok": True, "message": f"Word gerado: {target.name}", "outputPath": str(target)}


def _extract_text(params, _ai):
    source = _need_file(params)
    text = extract_text_from(source)
    target = _unique(source.with_suffix(".txt"))
    target.write_text(text, encoding="utf-8")
    return {
        "ok": True,
        "message": f"Texto extraido ({len(text)} caracteres): {target.name}",
        "outputPath": str(target),
    }


def _pdf_merge(params, _ai):
    sources = _need_files(params)
    fitz = import_module("fitz")
    merged = fitz.open()
    try:
        for item in sources:
            with fitz.open(str(item)) as document:
                merged.insert_pdf(document)
        target = _unique(sources[0].with_name("unificado.pdf"))
        merged.save(str(target))
    finally:
        merged.close()
    return {
        "ok": True,
        "message": f"{len(sources)} PDFs unidos em {target.name}",
        "outputPath": str(target),
    }


def _pdf_split(params, _ai):
    source = _need_file(params)
    fitz = import_module("fitz")
    folder = _unique(source.with_name(f"{source.stem}_paginas"))
    folder.mkdir(parents=True)
    with fitz.open(str(source)) as document:
        total = document.page_count
        for index in range(total):
            single = fitz.open()
            single.insert_pdf(document, from_page=index, to_page=index)
            single.save(str(folder / f"pagina_{index + 1:03d}.pdf"))
            single.close()
    return {
        "ok": True,
        "message": f"{total} páginas salvas em {folder.name}/",
        "outputDir": str(folder),
    }


def _pdf_extract_pages(params, _ai):
    source = _need_file(params)
    fitz = import_module("fitz")
    with fitz.open(str(source)) as document:
        pages = _parse_ranges(str(params.get("paginas", "")), document.page_count)
        out = fitz.open()
        for number in pages:
            out.insert_pdf(document, from_page=number - 1, to_page=number - 1)
        target = _unique(source.with_name(f"{source.stem}_paginas_selecionadas.pdf"))
        out.save(str(target))
        out.close()
    return {
        "ok": True,
        "message": f"{len(pages)} página(s) em {target.name}",
        "outputPath": str(target),
    }


def _pdf_to_images(params, _ai):
    source = _need_file(params)
    dpi = max(60, min(600, _int(params, "dpi", 150)))
    fitz = import_module("fitz")
    folder = _unique(source.with_name(f"{source.stem}_imagens"))
    folder.mkdir(parents=True)
    with fitz.open(str(source)) as document:
        total = document.page_count
        for index, page in enumerate(document, 1):
            page.get_pixmap(dpi=dpi).save(str(folder / f"pagina_{index:03d}.png"))
    return {
        "ok": True,
        "message": f"{total} imagem(ns) em {folder.name}/",
        "outputDir": str(folder),
    }


def _images_to_pdf(params, _ai):
    sources = _need_files(params)
    Image = import_module("PIL.Image")
    frames = []
    for item in sources:
        picture = Image.open(item)
        frames.append(picture.convert("RGB"))
    target = _unique(sources[0].with_name("imagens.pdf"))
    frames[0].save(str(target), save_all=True, append_images=frames[1:])
    return {
        "ok": True,
        "message": f"{len(sources)} imagem(ns) em {target.name}",
        "outputPath": str(target),
    }


_PIL_FORMAT = {"PNG": ".png", "JPEG": ".jpg", "WEBP": ".webp", "BMP": ".bmp"}


def _image_convert(params, _ai):
    source = _need_file(params)
    fmt = str(params.get("formato", "PNG")).upper()
    if fmt not in _PIL_FORMAT:
        raise ToolboxError("Formato invalido.")
    Image = import_module("PIL.Image")
    picture = Image.open(source)
    if fmt in {"JPEG", "BMP"}:
        picture = picture.convert("RGB")
    target = _unique(source.with_suffix(_PIL_FORMAT[fmt]))
    picture.save(str(target), format=fmt)
    return {"ok": True, "message": f"Convertido: {target.name}", "outputPath": str(target)}


def _image_resize(params, _ai):
    source = _need_file(params)
    width = max(1, _int(params, "largura_max", 1280))
    height = max(1, _int(params, "altura_max", 1280))
    Image = import_module("PIL.Image")
    picture = Image.open(source)
    picture.thumbnail((width, height))
    target = _unique(source.with_name(f"{source.stem}_redim{source.suffix}"))
    picture.save(str(target))
    return {
        "ok": True,
        "message": f"Redimensionado para {picture.width}x{picture.height}: {target.name}",
        "outputPath": str(target),
    }


def _image_compress(params, _ai):
    source = _need_file(params)
    quality = max(1, min(100, _int(params, "qualidade", 80)))
    Image = import_module("PIL.Image")
    picture = Image.open(source).convert("RGB")
    suffix = source.suffix.lower() if source.suffix.lower() in {".jpg", ".jpeg", ".webp"} else ".jpg"
    target = _unique(source.with_name(f"{source.stem}_comprimido{suffix}"))
    picture.save(str(target), quality=quality, optimize=True)
    before = source.stat().st_size
    after = target.stat().st_size
    return {
        "ok": True,
        "message": f"De {before // 1024} KB para {after // 1024} KB: {target.name}",
        "outputPath": str(target),
    }


def _image_strip_metadata(params, _ai):
    source = _need_file(params)
    Image = import_module("PIL.Image")
    picture = Image.open(source)
    clean = Image.new(picture.mode, picture.size)
    clean.putdata(list(picture.getdata()))
    target = _unique(source.with_name(f"{source.stem}_sem_metadados{source.suffix}"))
    clean.save(str(target))
    return {"ok": True, "message": f"Sem metadados: {target.name}", "outputPath": str(target)}


def _csv_to_json(params, _ai):
    source = _need_file(params)
    with source.open("r", encoding="utf-8", errors="replace", newline="") as handle:
        rows = list(csv.DictReader(handle))
    target = _unique(source.with_suffix(".json"))
    target.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "ok": True,
        "message": f"{len(rows)} linha(s) em {target.name}",
        "outputPath": str(target),
    }


def _json_format(params, _ai):
    source = _need_file(params)
    try:
        data = json.loads(source.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ToolboxError(f"JSON invalido: {exc}") from exc
    minify = str(params.get("modo", "Formatar")).lower().startswith("min")
    dumped = (
        json.dumps(data, ensure_ascii=False, separators=(",", ":"))
        if minify
        else json.dumps(data, ensure_ascii=False, indent=2)
    )
    target = _unique(source.with_name(f"{source.stem}_{'min' if minify else 'formatado'}.json"))
    target.write_text(dumped, encoding="utf-8")
    return {"ok": True, "message": f"Gerado: {target.name}", "outputPath": str(target)}


def _file_hash(params, _ai):
    source = _need_file(params)
    sha = hashlib.sha256()
    md5 = hashlib.md5()
    with source.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            sha.update(block)
            md5.update(block)
    text = f"Arquivo: {source.name}\nTamanho: {source.stat().st_size} bytes\n\nSHA-256:\n{sha.hexdigest()}\n\nMD5:\n{md5.hexdigest()}"
    return {"ok": True, "message": "Hash calculado.", "text": text}


def _text_stats(params, _ai):
    source = _need_file(params)
    content = source.read_text(encoding="utf-8", errors="replace")
    words = len(content.split())
    lines = len(content.splitlines())
    text = (
        f"Arquivo: {source.name}\n\n"
        f"Palavras:   {words}\n"
        f"Linhas:     {lines}\n"
        f"Caracteres: {len(content)}\n"
        f"Sem espacos:{len(content.replace(chr(32), '').replace(chr(10), ''))}"
    )
    return {"ok": True, "message": "Contagem pronta.", "text": text}


def _password_gen(params, _ai):
    size = max(6, min(128, _int(params, "tamanho", 20)))
    alphabet = string.ascii_letters + string.digits
    if not str(params.get("simbolos", "Sim")).lower().startswith("n"):
        alphabet += "!@#$%^&*-_=+?"
    password = "".join(secrets.choice(alphabet) for _ in range(size))
    return {"ok": True, "message": "Senha gerada (copie e guarde).", "text": password}


def _ai_summarize(params, ai: AiRunner):
    text = extract_text_from(_need_file(params), limit=_AI_CHAR_LIMIT)
    result = ai(
        "Você resume documentos em português do Brasil. Seja claro e objetivo: "
        "um paragrafo de visão geral e depois topicos com os pontos principais.",
        f"Resuma o documento a seguir:\n\n{text}",
    )
    source = _need_file(params)
    target = _unique(source.with_name(f"{source.stem}_resumo.md"))
    target.write_text(result, encoding="utf-8")
    return {"ok": True, "message": f"Resumo salvo em {target.name}", "text": result,
            "outputPath": str(target)}


def _pdf_editor(params, _ai):
    raw = str(params.get("arquivo", "")).strip()
    if raw:
        source = Path(raw).expanduser()
        if source.is_file() and source.suffix.lower() == ".pdf":
            data = load_pdf_pages(str(source))
            return {
                "ok": True,
                "message": f"PDF {source.name} carregado ({data.get('pageCount', 0)} páginas).",
                "text": data.get("fullText", ""),
                "outputPath": str(source),
            }
    return {
        "ok": True,
        "message": "Editor de PDF pronto.",
    }


def _hex_to_rgb(hex_str: str) -> tuple[float, float, float]:
    clean = hex_str.lstrip("#")
    if len(clean) == 6:
        try:
            return (
                int(clean[0:2], 16) / 255.0,
                int(clean[2:4], 16) / 255.0,
                int(clean[4:6], 16) / 255.0,
            )
        except ValueError:
            pass
    return (0.0, 0.0, 0.0)


def load_pdf_for_visual_edit(path: str) -> dict[str, Any]:
    fitz = import_module("fitz")
    file_path = Path(path).expanduser()
    if not file_path.is_file():
        raise ToolboxError(f"Arquivo não encontrado: {file_path}")
    doc = fitz.open(str(file_path))
    pages = []
    try:
        for idx, page in enumerate(doc):
            pix = page.get_pixmap(dpi=140)
            img_b64 = "data:image/png;base64," + base64.b64encode(pix.tobytes("png")).decode("ascii")
            blocks = []
            for b in page.get_text("blocks"):
                text = b[4].strip() if len(b) > 4 else ""
                if text:
                    blocks.append({
                        "x": float(b[0]),
                        "y": float(b[1]),
                        "width": float(b[2] - b[0]),
                        "height": float(b[3] - b[1]),
                        "text": text,
                    })
            pages.append({
                "page": idx + 1,
                "width": float(page.rect.width),
                "height": float(page.rect.height),
                "image": img_b64,
                "blocks": blocks,
            })
    finally:
        doc.close()
    return {
        "ok": True,
        "path": str(file_path),
        "name": file_path.name,
        "pageCount": len(pages),
        "pages": pages,
    }


def find_and_replace_pdf_text(source_path: str, find_text: str, replace_text: str, output_path: str = "") -> dict[str, Any]:
    if not find_text:
        raise ToolboxError("Informe o texto a ser localizado.")
    fitz = import_module("fitz")
    source = Path(source_path).expanduser()
    if not source.is_file():
        raise ToolboxError(f"Arquivo não encontrado: {source}")

    if output_path:
        target = Path(output_path).expanduser()
    else:
        target = _unique(source.with_name(f"{source.stem}_editado.pdf"))

    doc = fitz.open(str(source))
    total_replaced = 0
    try:
        for page in doc:
            hits = page.search_for(find_text)
            for rect in hits:
                page.add_redact_annot(rect, fill=(1, 1, 1))
                page.apply_redactions()
                fsize = max(8.0, min(36.0, rect.height * 0.75))
                page.insert_textbox(rect, replace_text, fontsize=fsize, color=(0, 0, 0))
                total_replaced += 1
        target.parent.mkdir(parents=True, exist_ok=True)
        doc.save(str(target))
    finally:
        doc.close()

    updated_data = load_pdf_for_visual_edit(str(target))
    return {
        "ok": True,
        "message": f"{total_replaced} substituição(ões) realizada(s) em {target.name}.",
        "outputPath": str(target),
        "outputDir": str(target.parent),
        "pages": updated_data.get("pages", []),
        "replacedCount": total_replaced,
    }


def apply_visual_pdf_edits(source_path: str, edits: list[dict[str, Any]], output_path: str = "") -> dict[str, Any]:
    fitz = import_module("fitz")
    source = Path(source_path).expanduser()
    if not source.is_file():
        raise ToolboxError(f"Arquivo não encontrado: {source}")

    if output_path:
        target = Path(output_path).expanduser()
    else:
        target = _unique(source.with_name(f"{source.stem}_editado.pdf"))

    doc = fitz.open(str(source))
    try:
        for edit in edits:
            p_idx = int(edit.get("page", 1)) - 1
            if p_idx < 0 or p_idx >= len(doc):
                continue
            page = doc[p_idx]
            action = edit.get("action", "")

            if action == "replace_text":
                x = float(edit.get("x", 0))
                y = float(edit.get("y", 0))
                w = float(edit.get("width", 100))
                h = float(edit.get("height", 20))
                rect = fitz.Rect(x, y, x + w, y + h)
                new_text = str(edit.get("new_text", ""))
                font_size = float(edit.get("font_size", max(9.0, h * 0.75)))
                color_hex = str(edit.get("color", "#000000"))
                rgb = _hex_to_rgb(color_hex)

                page.add_redact_annot(rect, fill=(1, 1, 1))
                page.apply_redactions()
                page.insert_textbox(rect, new_text, fontsize=font_size, color=rgb)

            elif action == "insert_text":
                x = float(edit.get("x", 50))
                y = float(edit.get("y", 50))
                w = float(edit.get("width", 200))
                h = float(edit.get("height", 30))
                rect = fitz.Rect(x, y, x + w, y + h)
                text = str(edit.get("text", ""))
                font_size = float(edit.get("font_size", 12))
                fill_white = bool(edit.get("fill_white", False))
                color_hex = str(edit.get("color", "#000000"))
                rgb = _hex_to_rgb(color_hex)

                if fill_white:
                    page.draw_rect(rect, color=None, fill=(1, 1, 1))
                page.insert_textbox(rect, text, fontsize=font_size, color=rgb)

            elif action == "insert_image":
                img_path = Path(str(edit.get("image_path", ""))).expanduser()
                if img_path.is_file():
                    x = float(edit.get("x", 50))
                    y = float(edit.get("y", 50))
                    w = float(edit.get("width", 150))
                    h = float(edit.get("height", 100))
                    rect = fitz.Rect(x, y, x + w, y + h)
                    page.insert_image(rect, filename=str(img_path))

            elif action == "redact":
                x = float(edit.get("x", 0))
                y = float(edit.get("y", 0))
                w = float(edit.get("width", 100))
                h = float(edit.get("height", 20))
                rect = fitz.Rect(x, y, x + w, y + h)
                color = (0, 0, 0) if edit.get("color") == "black" else (1, 1, 1)
                page.add_redact_annot(rect, fill=color)
                page.apply_redactions()

            elif action == "rotate":
                degrees = int(edit.get("degrees", 90))
                page.set_rotation((page.rotation + degrees) % 360)

        target.parent.mkdir(parents=True, exist_ok=True)
        doc.save(str(target))
    finally:
        doc.close()

    updated = load_pdf_for_visual_edit(str(target))
    return {
        "ok": True,
        "message": f"Alterações salvas com sucesso em {target.name}",
        "outputPath": str(target),
        "outputDir": str(target.parent),
        "pages": updated.get("pages", []),
    }


def rotate_pdf_page(source_path: str, page_index: int, angle: int = 90, output_path: str = "") -> dict[str, Any]:
    fitz = import_module("fitz")
    source = Path(source_path).expanduser()
    if not source.is_file():
        raise ToolboxError(f"Arquivo não encontrado: {source}")

    if output_path:
        target = Path(output_path).expanduser()
    else:
        target = _unique(source.with_name(f"{source.stem}_rotacionado.pdf"))

    doc = fitz.open(str(source))
    try:
        p_idx = page_index - 1
        if 0 <= p_idx < len(doc):
            p = doc[p_idx]
            p.set_rotation((p.rotation + angle) % 360)
        target.parent.mkdir(parents=True, exist_ok=True)
        doc.save(str(target))
    finally:
        doc.close()

    updated = load_pdf_for_visual_edit(str(target))
    return {
        "ok": True,
        "message": f"Página {page_index} rotacionada com sucesso.",
        "outputPath": str(target),
        "outputDir": str(target.parent),
        "pages": updated.get("pages", []),
    }


def delete_pdf_page(source_path: str, page_index: int, output_path: str = "") -> dict[str, Any]:
    fitz = import_module("fitz")
    source = Path(source_path).expanduser()
    if not source.is_file():
        raise ToolboxError(f"Arquivo não encontrado: {source}")

    if output_path:
        target = Path(output_path).expanduser()
    else:
        target = _unique(source.with_name(f"{source.stem}_editado.pdf"))

    doc = fitz.open(str(source))
    try:
        if len(doc) <= 1:
            raise ToolboxError("O PDF tem apenas 1 página e não pode ficar vazio.")
        p_idx = page_index - 1
        if 0 <= p_idx < len(doc):
            doc.delete_page(p_idx)
        target.parent.mkdir(parents=True, exist_ok=True)
        doc.save(str(target))
    finally:
        doc.close()

    updated = load_pdf_for_visual_edit(str(target))
    return {
        "ok": True,
        "message": f"Página {page_index} excluída com sucesso.",
        "outputPath": str(target),
        "outputDir": str(target.parent),
        "pages": updated.get("pages", []),
    }


def load_pdf_pages(path: str) -> dict[str, Any]:
    fitz = import_module("fitz")
    file_path = Path(path).expanduser()
    if not file_path.is_file():
        raise ToolboxError(f"Arquivo não encontrado: {file_path}")
    doc = fitz.open(str(file_path))
    pages = []
    try:
        for idx in range(len(doc)):
            page = doc[idx]
            text = page.get_text("text")
            pages.append({
                "page": idx + 1,
                "text": text,
            })
    finally:
        doc.close()
    return {
        "ok": True,
        "path": str(file_path),
        "name": file_path.name,
        "pageCount": len(pages),
        "pages": pages,
        "fullText": "\n\n".join(p["text"] for p in pages),
    }


def export_text_to_pdf(content: str, output_path: str = "", original_path: str = "", title: str = "Documento") -> dict[str, Any]:
    fitz = import_module("fitz")
    if output_path:
        target = Path(output_path).expanduser()
    elif original_path:
        orig = Path(original_path).expanduser()
        target = _unique(orig.with_name(f"{orig.stem}_editado.pdf"))
    else:
        docs_dir = Path.home() / "Documents"
        if not docs_dir.exists():
            docs_dir = Path.cwd() / "data"
        docs_dir.mkdir(parents=True, exist_ok=True)
        target = _unique(docs_dir / "documento_editado.pdf")

    doc = fitz.open()

    styled_html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
body {{
    font-family: Helvetica, Arial, sans-serif;
    font-size: 11pt;
    line-height: 1.5;
    color: #111111;
    margin: 0;
    padding: 0;
}}
h1 {{ font-size: 18pt; color: #0b2545; margin-bottom: 12px; border-bottom: 1px solid #134074; padding-bottom: 4px; }}
h2 {{ font-size: 14pt; color: #134074; margin-top: 12px; margin-bottom: 6px; }}
h3 {{ font-size: 12pt; color: #1d2d44; margin-top: 10px; margin-bottom: 4px; }}
p {{ margin-bottom: 8px; }}
ul, ol {{ margin-top: 4px; margin-bottom: 8px; padding-left: 20px; }}
li {{ margin-bottom: 3px; }}
code {{ font-family: monospace; background: #f0f4f8; padding: 2px 4px; border-radius: 3px; font-size: 10pt; }}
</style>
</head>
<body>
{content}
</body>
</html>"""

    page = doc.new_page(width=595, height=842) # A4
    rect = fitz.Rect(45, 50, 550, 792)
    try:
        page.insert_htmlbox(rect, styled_html)
    except Exception:
        page.insert_textbox(rect, content, fontsize=11, fontname="helv", color=(0.1, 0.1, 0.1))

    target.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(target))
    doc.close()

    return {
        "ok": True,
        "message": f"PDF salvo com sucesso: {target.name}",
        "outputPath": str(target),
        "outputDir": str(target.parent),
    }


def _ai_translate(params, ai: AiRunner):
    idioma = str(params.get("idioma", "Inglês")).strip() or "Inglês"
    text = extract_text_from(_need_file(params), limit=_AI_CHAR_LIMIT)
    result = ai(
        f"Você é um tradutor profissional. Traduza para {idioma} mantendo o "
        "sentido, o tom e a formatação. Responda apenas com a tradução.",
        text,
    )
    source = _need_file(params)
    clean_lang = idioma.lower().replace(" ", "_")
    target = _unique(source.with_name(f"{source.stem}_{clean_lang}.md"))
    target.write_text(result, encoding="utf-8")
    return {"ok": True, "message": f"Tradução salva em {target.name}", "text": result,
            "outputPath": str(target)}


def _ai_action_items(params, ai: AiRunner):
    text = extract_text_from(_need_file(params), limit=_AI_CHAR_LIMIT)
    result = ai(
        "Você extrai itens de ação de atas e anotações. Liste cada tarefa em uma "
        "linha comecando com '- [ ] ', com responsável e prazo quando houver. Se "
        "não houver tarefas, diga isso.",
        text,
    )
    return {"ok": True, "message": "Itens de ação extraidos.", "text": result}


def _ai_explain_code(params, ai: AiRunner):
    source = _need_file(params)
    text = source.read_text(encoding="utf-8", errors="replace")[:_AI_CHAR_LIMIT]
    result = ai(
        "Você explica código para outra pessoa dev em português do Brasil. Diga o "
        "proposito do arquivo, as partes principais e pontos de atenção. Seja conciso.",
        f"Arquivo: {source.name}\n\n{text}",
    )
    return {"ok": True, "message": f"Explicação de {source.name}.", "text": result}


_IMPL: dict[str, Callable[[dict[str, Any], AiRunner | None], dict[str, Any]]] = {
    "pdf_to_word": _pdf_to_word,
    "extract_text": _extract_text,
    "pdf_merge": _pdf_merge,
    "pdf_split": _pdf_split,
    "pdf_extract_pages": _pdf_extract_pages,
    "pdf_to_images": _pdf_to_images,
    "images_to_pdf": _images_to_pdf,
    "pdf_editor": _pdf_editor,
    "image_convert": _image_convert,
    "image_resize": _image_resize,
    "image_compress": _image_compress,
    "image_strip_metadata": _image_strip_metadata,
    "csv_to_json": _csv_to_json,
    "json_format": _json_format,
    "file_hash": _file_hash,
    "text_stats": _text_stats,
    "password_gen": _password_gen,
    "ai_summarize": _ai_summarize,
    "ai_translate": _ai_translate,
    "ai_action_items": _ai_action_items,
    "ai_explain_code": _ai_explain_code,
}


def run_utility(
    utility_id: str,
    params: dict[str, Any],
    *,
    ai_runner: AiRunner | None = None,
) -> dict[str, Any]:
    """Executa um utilitario. Devolve {ok, message, outputPath?, outputDir?, text?}."""
    utility = _BY_ID.get(utility_id)
    if utility is None:
        return {"ok": False, "message": f"Ferramenta desconhecida: {utility_id}"}
    missing = [module for module in utility.needs if importlib.util.find_spec(module) is None]
    if missing:
        return {
            "ok": False,
            "message": (
                "Esta ferramenta precisa de uma biblioteca extra. Rode:\n"
                '.\\.venv\\Scripts\\python.exe -m pip install -e ".[tools]"'
            ),
        }
    if utility.ai and ai_runner is None:
        return {"ok": False, "message": "Nenhum provedor de IA disponível."}
    try:
        result = _IMPL[utility_id](params, ai_runner)
    except ToolboxError as exc:
        return {"ok": False, "message": str(exc)}
    except Exception as exc:  # noqa: BLE001 - vira mensagem amigavel
        return {"ok": False, "message": f"Falhou: {exc}"}
    result.setdefault("ok", True)
    result.setdefault("message", "Concluido.")
    return result
