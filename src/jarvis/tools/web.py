from __future__ import annotations

import asyncio
import re
import urllib.error
import urllib.request
from html.parser import HTMLParser
from typing import Any

from jarvis.tools.base import Risk, Tool, ToolResult
from jarvis.tools.context import ToolContext

_STR = {"type": "string"}
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


class _TextExtractor(HTMLParser):
    """Extrai o texto visivel de uma página, ignorando script/style/nav."""

    _SKIP = {"script", "style", "noscript", "head", "svg"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._chunks: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: Any) -> None:
        if tag in self._SKIP:
            self._skip_depth += 1
        elif tag in {"p", "br", "div", "li", "h1", "h2", "h3", "tr"}:
            self._chunks.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in self._SKIP and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0:
            text = data.strip()
            if text:
                self._chunks.append(text + " ")

    def text(self) -> str:
        joined = "".join(self._chunks)
        joined = re.sub(r"[ \t]+", " ", joined)
        joined = re.sub(r"\n\s*\n+", "\n\n", joined)
        return joined.strip()


class BuscarNaWeb(Tool):
    name = "buscar_na_web"
    description = (
        "Pesquisa na internet (DuckDuckGo) e devolve título, link e resumo dos "
        "resultados como texto para você ler. Use quando precisar de informação "
        "atual. Para abrir o site no navegador do usuário use 'pesquisar_web'."
    )
    risk = Risk.SAFE
    parameters = {
        "type": "object",
        "properties": {
            "consulta": {**_STR, "description": "O que pesquisar."},
            "maximo": {
                "type": "integer",
                "description": "Quantos resultados (1 a 10, padrão 5).",
            },
        },
        "required": ["consulta"],
        "additionalProperties": False,
    }

    async def execute(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        query = str(args.get("consulta", "")).strip()
        if not query:
            return ToolResult.failure("Diga o que devo pesquisar.")
        try:
            maximo = int(args.get("maximo", 5))
        except (TypeError, ValueError):
            maximo = 5
        maximo = max(1, min(maximo, 10))

        from jarvis import websearch

        try:
            hits = await asyncio.to_thread(
                websearch.search, query, max_results=maximo, region="br-pt"
            )
        except websearch.SearchError as exc:
            return ToolResult.failure(f"A busca falhou: {exc}")
        except Exception as exc:  # noqa: BLE001 - vira contexto pro modelo
            return ToolResult.failure(f"A busca falhou: {exc}")

        if not hits:
            return ToolResult(
                ok=True,
                content=f"Nenhum resultado para '{query}'.",
                display="0 resultados",
            )

        lines: list[str] = []
        for index, hit in enumerate(hits, 1):
            lines.append(
                f"{index}. {hit.title}\n   {hit.url}\n   {hit.snippet[:400]}"
            )
        return ToolResult(
            ok=True,
            content="\n\n".join(lines)[: ctx.config.max_output_chars],
            display=f"{len(hits)} resultado(s) para '{query}'",
        )


class LerPaginaWeb(Tool):
    name = "ler_pagina_web"
    description = (
        "Baixa uma página da web e devolve o texto principal (sem HTML). "
        "Use depois de 'buscar_na_web' para ler um resultado."
    )
    risk = Risk.SAFE
    parameters = {
        "type": "object",
        "properties": {"url": {**_STR, "description": "Endereco https:// da página."}},
        "required": ["url"],
        "additionalProperties": False,
    }

    async def execute(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        url = str(args.get("url", "")).strip()
        if not url.lower().startswith(("http://", "https://")):
            return ToolResult.failure("Informe uma URL http(s):// completa.")
        request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                charset = response.headers.get_content_charset() or "utf-8"
                raw = response.read(2_000_000)
        except urllib.error.HTTPError as exc:
            return ToolResult.failure(f"O site respondeu HTTP {exc.code}.")
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            return ToolResult.failure(f"Não consegui acessar {url}: {exc}")

        html = raw.decode(charset, errors="replace")
        parser = _TextExtractor()
        try:
            parser.feed(html)
        except Exception:  # noqa: BLE001 - HTML malformado
            pass
        text = parser.text() or "(a página não tem texto legivel)"
        return ToolResult(
            ok=True,
            content=text[: ctx.config.max_output_chars],
            display=f"leu {url} ({len(text)} caracteres)",
        )
