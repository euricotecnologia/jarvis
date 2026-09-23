from __future__ import annotations

import fnmatch
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from jarvis.tools.base import Risk, Tool, ToolResult
from jarvis.tools.context import ToolContext

_STR = {"type": "string"}


def _clip(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n... [truncado, {len(text) - limit} caracteres a mais]"


class ListarPasta(Tool):
    name = "listar_pasta"
    description = "Lista arquivos e subpastas de um diretório."
    risk = Risk.SAFE
    parameters = {
        "type": "object",
        "properties": {"caminho": {**_STR, "description": "Pasta a listar."}},
        "required": ["caminho"],
        "additionalProperties": False,
    }

    async def execute(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        path = ctx.resolve_readable(str(args.get("caminho", "")))
        if not path.is_dir():
            return ToolResult.failure(f"Não e uma pasta: {path}")
        entries = []
        for item in sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name.lower())):
            marker = "/" if item.is_dir() else ""
            try:
                size = item.stat().st_size if item.is_file() else 0
            except OSError:
                size = 0
            entries.append(f"{item.name}{marker}\t{size} B" if size else f"{item.name}{marker}")
        body = "\n".join(entries) or "(pasta vazia)"
        return ToolResult(
            ok=True,
            content=f"{path}\n{_clip(body, ctx.config.max_output_chars)}",
            display=f"listou {len(entries)} itens em {path.name or path}",
        )


class AbrirPasta(Tool):
    name = "abrir_pasta"
    description = (
        "Abre uma pasta (ou arquivo) na janela do Explorador de Arquivos do "
        "Windows. Ex.: 'D:', 'D:/Projetos', a pasta de Downloads."
    )
    risk = Risk.WRITE
    parameters = {
        "type": "object",
        "properties": {
            "caminho": {**_STR, "description": "Pasta ou arquivo a abrir. Aceita 'D:'."}
        },
        "required": ["caminho"],
        "additionalProperties": False,
    }

    async def execute(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        path = ctx.resolve_readable(str(args.get("caminho", "")))
        if not path.exists():
            return ToolResult.failure(f"Não existe: {path}")
        try:
            if sys.platform == "win32":
                os.startfile(str(path))  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(path)])
            else:
                subprocess.Popen(["xdg-open", str(path)])
        except OSError as exc:
            return ToolResult.failure(f"Não consegui abrir {path}: {exc}")
        return ToolResult(ok=True, content=f"Abri {path} no Explorador.", display=f"abriu {path}")


class LerArquivo(Tool):
    name = "ler_arquivo"
    description = "Le o conteúdo de texto de um arquivo."
    risk = Risk.SAFE
    parameters = {
        "type": "object",
        "properties": {"caminho": {**_STR, "description": "Arquivo a ler."}},
        "required": ["caminho"],
        "additionalProperties": False,
    }

    async def execute(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        path = ctx.resolve_readable(str(args.get("caminho", "")))
        if not path.is_file():
            return ToolResult.failure(f"Arquivo não encontrado: {path}")
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            return ToolResult.failure(f"Não consegui ler {path}: {exc}")
        return ToolResult(
            ok=True,
            content=_clip(text, ctx.config.max_output_chars),
            display=f"leu {path.name} ({len(text)} caracteres)",
        )


class BuscarArquivos(Tool):
    name = "buscar_arquivos"
    description = "Procura arquivos por padrão de nome (glob) dentro de uma pasta."
    risk = Risk.SAFE
    parameters = {
        "type": "object",
        "properties": {
            "pasta": {**_STR, "description": "Pasta base da busca."},
            "padrao": {**_STR, "description": "Padrão glob, ex.: *.py ou nota*.txt"},
        },
        "required": ["pasta", "padrao"],
        "additionalProperties": False,
    }

    async def execute(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        base = ctx.resolve_readable(str(args.get("pasta", "")))
        pattern = str(args.get("padrao", "*"))
        if not base.is_dir():
            return ToolResult.failure(f"Não e uma pasta: {base}")
        hits: list[str] = []
        for item in base.rglob("*"):
            if item.is_file() and fnmatch.fnmatch(item.name, pattern):
                hits.append(str(item))
                if len(hits) >= 200:
                    break
        body = "\n".join(hits) or "(nenhum arquivo encontrado)"
        return ToolResult(
            ok=True,
            content=_clip(body, ctx.config.max_output_chars),
            display=f"{len(hits)} arquivo(s) para '{pattern}'",
        )


class ProcurarTexto(Tool):
    name = "procurar_texto"
    description = "Procura um trecho de texto dentro dos arquivos de uma pasta."
    risk = Risk.SAFE
    parameters = {
        "type": "object",
        "properties": {
            "pasta": {**_STR, "description": "Pasta base da busca."},
            "texto": {**_STR, "description": "Texto a procurar (sem diferenciar maiuscula)."},
        },
        "required": ["pasta", "texto"],
        "additionalProperties": False,
    }

    async def execute(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        base = ctx.resolve_readable(str(args.get("pasta", "")))
        needle = str(args.get("texto", "")).lower()
        if not base.is_dir():
            return ToolResult.failure(f"Não e uma pasta: {base}")
        if not needle:
            return ToolResult.failure("Informe o texto a procurar.")
        matches: list[str] = []
        scanned = 0
        for item in base.rglob("*"):
            if not item.is_file():
                continue
            scanned += 1
            if scanned > 4000:
                break
            try:
                for number, line in enumerate(
                    item.read_text(encoding="utf-8", errors="ignore").splitlines(), 1
                ):
                    if needle in line.lower():
                        matches.append(f"{item}:{number}: {line.strip()[:200]}")
                        if len(matches) >= 100:
                            break
            except OSError:
                continue
            if len(matches) >= 100:
                break
        body = "\n".join(matches) or "(nenhuma ocorrencia)"
        return ToolResult(
            ok=True,
            content=_clip(body, ctx.config.max_output_chars),
            display=f"{len(matches)} ocorrencia(s)",
        )


class EscreverArquivo(Tool):
    name = "escrever_arquivo"
    description = (
        "Cria ou substitui um arquivo de texto com o conteúdo informado."
    )
    risk = Risk.WRITE
    parameters = {
        "type": "object",
        "properties": {
            "caminho": {**_STR, "description": "Arquivo a escrever."},
            "conteudo": {**_STR, "description": "Conteúdo completo do arquivo."},
        },
        "required": ["caminho", "conteudo"],
        "additionalProperties": False,
    }

    async def execute(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        path = ctx.resolve_writable(str(args.get("caminho", "")))
        content = str(args.get("conteudo", ""))
        existed = path.exists()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        except OSError as exc:
            return ToolResult.failure(f"Não consegui escrever {path}: {exc}")
        verb = "substituiu" if existed else "criou"
        return ToolResult(
            ok=True,
            content=f"{verb} {path} ({len(content)} caracteres)",
            display=f"{verb} {path.name}",
        )

    def is_destructive(self, args: dict[str, Any], ctx: ToolContext) -> bool:
        try:
            return ctx.resolve_writable(str(args.get("caminho", ""))).exists()
        except Exception:
            return True

    def confirm_message(self, args: dict[str, Any]) -> str:
        return f"sobrescrever arquivo: {args.get('caminho')}"


class AnexarArquivo(Tool):
    name = "anexar_arquivo"
    description = "Adiciona texto ao final de um arquivo (cria se não existir)."
    risk = Risk.WRITE
    parameters = {
        "type": "object",
        "properties": {
            "caminho": {**_STR, "description": "Arquivo alvo."},
            "conteudo": {**_STR, "description": "Texto a acrescentar."},
        },
        "required": ["caminho", "conteudo"],
        "additionalProperties": False,
    }

    async def execute(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        path = ctx.resolve_writable(str(args.get("caminho", "")))
        content = str(args.get("conteudo", ""))
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as handle:
                handle.write(content)
        except OSError as exc:
            return ToolResult.failure(f"Não consegui anexar em {path}: {exc}")
        return ToolResult(
            ok=True, content=f"anexou {len(content)} caracteres em {path}",
            display=f"anexou em {path.name}",
        )


class CriarPasta(Tool):
    name = "criar_pasta"
    description = "Cria uma pasta (e as intermediarias necessarias)."
    risk = Risk.WRITE
    parameters = {
        "type": "object",
        "properties": {"caminho": {**_STR, "description": "Pasta a criar."}},
        "required": ["caminho"],
        "additionalProperties": False,
    }

    async def execute(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        path = ctx.resolve_writable(str(args.get("caminho", "")))
        try:
            path.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            return ToolResult.failure(f"Não consegui criar {path}: {exc}")
        return ToolResult(ok=True, content=f"pasta pronta: {path}", display=f"criou {path.name}/")


class Mover(Tool):
    name = "mover"
    description = "Move ou renomeia um arquivo/pasta. Sobrescreve o destino se existir."
    risk = Risk.IRREVERSIBLE
    parameters = {
        "type": "object",
        "properties": {
            "origem": {**_STR, "description": "Caminho atual."},
            "destino": {**_STR, "description": "Novo caminho."},
        },
        "required": ["origem", "destino"],
        "additionalProperties": False,
    }

    async def execute(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        source = ctx.resolve_writable(str(args.get("origem", "")))
        target = ctx.resolve_writable(str(args.get("destino", "")))
        if not source.exists():
            return ToolResult.failure(f"Origem não existe: {source}")
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source), str(target))
        except (OSError, shutil.Error) as exc:
            return ToolResult.failure(f"Não consegui mover: {exc}")
        return ToolResult(ok=True, content=f"movido para {target}", display=f"moveu para {target.name}")

    def confirm_message(self, args: dict[str, Any]) -> str:
        return f"mover {args.get('origem')} -> {args.get('destino')}"


class Apagar(Tool):
    name = "apagar"
    description = "Apaga um arquivo ou pasta de forma permanente."
    risk = Risk.IRREVERSIBLE
    parameters = {
        "type": "object",
        "properties": {"caminho": {**_STR, "description": "Caminho a apagar."}},
        "required": ["caminho"],
        "additionalProperties": False,
    }

    async def execute(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        path = ctx.resolve_writable(str(args.get("caminho", "")))
        if not path.exists():
            return ToolResult.failure(f"Não existe: {path}")
        try:
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
        except OSError as exc:
            return ToolResult.failure(f"Não consegui apagar {path}: {exc}")
        return ToolResult(ok=True, content=f"apagado: {path}", display=f"apagou {path.name}")

    def confirm_message(self, args: dict[str, Any]) -> str:
        return f"APAGAR permanentemente: {args.get('caminho')}"
