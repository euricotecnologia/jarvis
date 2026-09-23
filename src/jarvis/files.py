"""Navegador de arquivos: listar, buscar (nome e conteúdo) e pre-visualizar.

Tudo aqui e SO LEITURA. Escrever/mover/apagar continua no agente, restrito as
pastas liberadas em Permissões. Nenhuma função lanca exceção para a interface:
falhas viram `{"ok": False, "error": ...}`.
"""

from __future__ import annotations

import string
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

_TEXT_EXT = {
    ".txt", ".md", ".markdown", ".rst", ".log", ".csv", ".tsv", ".ini", ".cfg",
    ".conf", ".toml", ".yaml", ".yml", ".json", ".xml", ".env", ".gitignore",
}
_CODE_EXT = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".c", ".h", ".cpp", ".hpp", ".cc",
    ".cs", ".java", ".go", ".rs", ".rb", ".php", ".sh", ".ps1", ".bat", ".sql",
    ".qml", ".html", ".css", ".scss", ".sass", ".vue", ".lua", ".r", ".kt",
    ".swift", ".dart", ".pl", ".m", ".mm",
}
_IMAGE_EXT = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".ico", ".tiff", ".svg"}
_PDF_EXT = {".pdf"}
_ARCHIVE_EXT = {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz", ".iso"}
_AUDIO_EXT = {".mp3", ".wav", ".flac", ".ogg", ".m4a", ".aac", ".wma"}
_VIDEO_EXT = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".wmv", ".flv"}

_SCAN_DIR_LIMIT = 6000
_SEARCH_SKIP_DIRS = {
    "node_modules", ".git", "__pycache__", ".venv", "venv", "$RECYCLE.BIN",
    "System Volume Information", ".cache", "AppData",
}


def _kind(path: Path, is_dir: bool) -> str:
    if is_dir:
        return "folder"
    ext = path.suffix.lower()
    if ext in _IMAGE_EXT:
        return "image"
    if ext in _CODE_EXT:
        return "code"
    if ext in _TEXT_EXT:
        return "text"
    if ext in _PDF_EXT:
        return "pdf"
    if ext in _ARCHIVE_EXT:
        return "archive"
    if ext in _AUDIO_EXT:
        return "audio"
    if ext in _VIDEO_EXT:
        return "video"
    return "other"


def format_size(num: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if num < 1024.0:
            return f"{num:.0f} {unit}" if unit in ("B", "KB") else f"{num:.1f} {unit}"
        num /= 1024.0
    return f"{num:.1f} PB"


@dataclass(frozen=True, slots=True)
class FileEntry:
    name: str
    path: str
    is_dir: bool
    kind: str
    size: int
    size_text: str
    modified: str
    ext: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "path": self.path,
            "isDir": self.is_dir,
            "kind": self.kind,
            "size": self.size,
            "sizeText": self.size_text,
            "modified": self.modified,
            "ext": self.ext,
        }


def _entry(path: Path) -> FileEntry | None:
    try:
        stat = path.stat()
        is_dir = path.is_dir()
    except OSError:
        return None
    size = 0 if is_dir else int(stat.st_size)
    try:
        modified = datetime.fromtimestamp(stat.st_mtime).strftime("%d/%m/%Y %H:%M")
    except (OSError, OverflowError, ValueError):
        modified = ""
    return FileEntry(
        name=path.name or str(path),
        path=str(path),
        is_dir=is_dir,
        kind=_kind(path, is_dir),
        size=size,
        size_text="" if is_dir else format_size(size),
        modified=modified,
        ext=path.suffix.lower(),
    )


def _resolve(raw: str) -> Path:
    path = Path(raw).expanduser()
    try:
        return path.resolve()
    except OSError:
        return path


def list_directory(raw: str) -> dict[str, Any]:
    path = _resolve(raw)
    if not path.exists():
        return {"ok": False, "error": "Pasta não encontrada.", "path": str(path),
                "parent": "", "entries": []}
    if not path.is_dir():
        return {"ok": False, "error": "Não e uma pasta.", "path": str(path.parent),
                "parent": "", "entries": []}
    try:
        children = list(path.iterdir())
    except OSError as exc:
        return {"ok": False, "error": f"Sem acesso a esta pasta ({exc}).",
                "path": str(path), "parent": str(path.parent), "entries": []}

    entries: list[FileEntry] = []
    for child in children:
        entry = _entry(child)
        if entry is not None:
            entries.append(entry)
        if len(entries) >= _SCAN_DIR_LIMIT:
            break
    entries.sort(key=lambda item: (not item.is_dir, item.name.lower()))
    parent = str(path.parent) if path.parent != path else ""
    return {
        "ok": True,
        "error": "",
        "path": str(path),
        "parent": parent,
        "entries": [item.as_dict() for item in entries],
        "truncated": len(children) > _SCAN_DIR_LIMIT,
    }


def _iter_tree(base: Path, deadline: float):
    stack = [base]
    while stack:
        if time.monotonic() > deadline:
            return
        current = stack.pop()
        try:
            children = list(current.iterdir())
        except OSError:
            continue
        for child in children:
            yield child
            try:
                if child.is_dir() and child.name not in _SEARCH_SKIP_DIRS:
                    stack.append(child)
            except OSError:
                continue


def search_by_name(root: str, query: str, *, limit: int = 300,
                   budget_seconds: float = 6.0) -> dict[str, Any]:
    base = _resolve(root)
    needle = query.strip().lower()
    if not needle:
        return {"ok": False, "error": "Digite o que procurar.", "entries": []}
    if not base.is_dir():
        return {"ok": False, "error": "Pasta invalida.", "entries": []}
    hits: list[FileEntry] = []
    deadline = time.monotonic() + budget_seconds
    for child in _iter_tree(base, deadline):
        if needle in child.name.lower():
            entry = _entry(child)
            if entry is not None:
                hits.append(entry)
                if len(hits) >= limit:
                    break
    hits.sort(key=lambda item: (not item.is_dir, item.name.lower()))
    return {
        "ok": True,
        "error": "",
        "entries": [item.as_dict() for item in hits],
        "truncated": len(hits) >= limit or time.monotonic() > deadline,
    }


def search_in_files(root: str, query: str, *, limit: int = 200,
                    max_file_bytes: int = 1_200_000,
                    budget_seconds: float = 8.0) -> dict[str, Any]:
    base = _resolve(root)
    needle = query.strip().lower()
    if not needle:
        return {"ok": False, "error": "Digite o texto a procurar.", "matches": []}
    if not base.is_dir():
        return {"ok": False, "error": "Pasta invalida.", "matches": []}
    matches: list[dict[str, Any]] = []
    deadline = time.monotonic() + budget_seconds
    for child in _iter_tree(base, deadline):
        if len(matches) >= limit:
            break
        try:
            if not child.is_file() or _kind(child, False) not in {"text", "code"}:
                continue
            if child.stat().st_size > max_file_bytes:
                continue
            with child.open("r", encoding="utf-8", errors="ignore") as handle:
                for number, line in enumerate(handle, 1):
                    if needle in line.lower():
                        matches.append({
                            "path": str(child),
                            "name": child.name,
                            "line": number,
                            "text": line.strip()[:240],
                        })
                        if len(matches) >= limit:
                            break
        except OSError:
            continue
    return {
        "ok": True,
        "error": "",
        "matches": matches,
        "truncated": len(matches) >= limit or time.monotonic() > deadline,
    }


def preview(raw: str, *, max_bytes: int = 60_000) -> dict[str, Any]:
    path = _resolve(raw)
    if not path.is_file():
        return {"kind": "none", "error": "Arquivo não encontrado."}
    kind = _kind(path, False)
    if kind == "image":
        try:
            return {"kind": "image", "url": path.as_uri()}
        except ValueError:
            return {"kind": "none", "error": "Não consegui abrir a imagem."}
    if kind in {"text", "code"} or path.suffix == "":
        try:
            with path.open("rb") as handle:
                blob = handle.read(max_bytes + 1)
        except OSError as exc:
            return {"kind": "none", "error": f"Sem acesso: {exc}"}
        if b"\x00" in blob[:1024]:
            return {"kind": "other", "error": "Arquivo binario."}
        return {
            "kind": "text",
            "text": blob[:max_bytes].decode("utf-8", errors="replace"),
            "truncated": len(blob) > max_bytes,
            "lang": kind,
        }
    return {"kind": kind}


def quick_access() -> list[dict[str, str]]:
    home = Path.home()
    candidates = [
        ("Inicio", home),
        ("Area de trabalho", home / "Desktop"),
        ("Downloads", home / "Downloads"),
        ("Documentos", home / "Documents"),
        ("Imagens", home / "Pictures"),
    ]
    result: list[dict[str, str]] = []
    for label, path in candidates:
        try:
            if path.exists():
                result.append({"label": label, "path": str(path)})
        except OSError:
            continue
    if sys.platform == "win32":
        for letter in string.ascii_uppercase:
            drive = Path(f"{letter}:\\")
            try:
                if drive.exists():
                    result.append({"label": f"Disco {letter}:", "path": str(drive)})
            except OSError:
                continue
    else:
        result.append({"label": "Raiz /", "path": "/"})
    return result


def home_path() -> str:
    return str(Path.home())
