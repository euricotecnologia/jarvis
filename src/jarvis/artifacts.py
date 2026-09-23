"""Detecta blocos de código nas respostas da IA para virarem cartoes com
Copiar / Baixar / Visualizar no chat.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_FENCE = re.compile(r"```([^\n`]*)\n(.*?)```", re.DOTALL)

_LANG_FILE = {
    "html": "pagina.html", "htm": "pagina.html",
    "css": "estilo.css", "scss": "estilo.scss",
    "javascript": "script.js", "js": "script.js",
    "typescript": "script.ts", "ts": "script.ts",
    "jsx": "componente.jsx", "tsx": "componente.tsx",
    "python": "script.py", "py": "script.py",
    "json": "dados.json", "sql": "consulta.sql",
    "bash": "script.sh", "sh": "script.sh", "shell": "script.sh",
    "powershell": "script.ps1", "ps1": "script.ps1",
    "xml": "documento.xml", "yaml": "config.yaml", "yml": "config.yaml",
    "toml": "config.toml", "ini": "config.ini",
    "markdown": "documento.md", "md": "documento.md",
    "java": "App.java", "kotlin": "App.kt",
    "c": "programa.c", "cpp": "programa.cpp", "c++": "programa.cpp",
    "csharp": "Programa.cs", "cs": "Programa.cs",
    "go": "main.go", "rust": "main.rs", "rs": "main.rs",
    "php": "index.php", "ruby": "script.rb", "rb": "script.rb",
    "dockerfile": "Dockerfile", "text": "texto.txt", "": "codigo.txt",
}

_PREVIEWABLE = {"html", "htm"}


@dataclass(frozen=True, slots=True)
class CodeBlock:
    language: str
    code: str
    filename: str
    previewable: bool

    def as_dict(self) -> dict[str, object]:
        return {
            "language": self.language or "texto",
            "code": self.code,
            "filename": self.filename,
            "previewable": self.previewable,
        }


def _clean_name(raw: str) -> str:
    raw = re.sub(r"[^A-Za-z0-9._-]+", "_", raw.strip()).strip("_")
    return raw or ""


def extract_code_blocks(text: str) -> tuple[str, list[CodeBlock]]:
    """Devolve (texto sem os blocos, lista de CodeBlock)."""
    blocks: list[CodeBlock] = []
    seen_langs: dict[str, int] = {}

    def _take(match: re.Match) -> str:
        info = match.group(1).strip()
        code = match.group(2).strip("\n")
        parts = info.split()
        language = (parts[0].lower() if parts else "").strip()
        hint = _clean_name(parts[1]) if len(parts) > 1 else ""

        if len(code) < 12 and "\n" not in code:
            return match.group(0)  # trecho curto inline, não e artefato

        base = _LANG_FILE.get(language, "codigo.txt")
        if hint and "." in hint:
            filename = hint
        else:
            count = seen_langs.get(base, 0)
            seen_langs[base] = count + 1
            if count:
                stem, _, ext = base.rpartition(".")
                filename = f"{stem}-{count + 1}.{ext}" if ext else f"{base}-{count + 1}"
            else:
                filename = base

        blocks.append(
            CodeBlock(
                language=language,
                code=code,
                filename=filename,
                previewable=language in _PREVIEWABLE,
            )
        )
        return f"‹código: {filename}›"

    clean = _FENCE.sub(_take, text)
    clean = re.sub(r"\n{3,}", "\n\n", clean).strip()
    return clean, blocks
