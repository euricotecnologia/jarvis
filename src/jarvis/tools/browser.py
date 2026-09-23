from __future__ import annotations

import urllib.parse
import webbrowser
from typing import Any

from jarvis.tools.base import Risk, Tool, ToolResult
from jarvis.tools.context import ToolContext

_STR = {"type": "string"}

# Sites com busca por URL: {consulta} e substituido pelo termo ja escapado.
SEARCH_SITES: dict[str, str] = {
    "google": "https://www.google.com/search?q={consulta}",
    "youtube": "https://www.youtube.com/results?search_query={consulta}",
    "maps": "https://www.google.com/maps/search/{consulta}",
    "wikipedia": "https://pt.wikipedia.org/w/index.php?search={consulta}",
    "github": "https://github.com/search?q={consulta}",
    "amazon": "https://www.amazon.com.br/s?k={consulta}",
    "mercadolivre": "https://lista.mercadolivre.com.br/{consulta}",
    "gmail": "https://mail.google.com/mail/u/0/#search/{consulta}",
    "spotify": "https://open.spotify.com/search/{consulta}",
    "duckduckgo": "https://duckduckgo.com/?q={consulta}",
}

# Atalhos para abrir a home de um serviço.
SITE_HOMES: dict[str, str] = {
    "youtube": "https://www.youtube.com",
    "google": "https://www.google.com",
    "gmail": "https://mail.google.com",
    "maps": "https://www.google.com/maps",
    "drive": "https://drive.google.com",
    "agenda": "https://calendar.google.com",
    "calendar": "https://calendar.google.com",
    "github": "https://github.com",
    "chatgpt": "https://chat.openai.com",
    "whatsapp": "https://web.whatsapp.com",
    "spotify": "https://open.spotify.com",
    "netflix": "https://www.netflix.com",
    "instagram": "https://www.instagram.com",
    "linkedin": "https://www.linkedin.com",
}


def _normalize_url(raw: str) -> str | None:
    raw = raw.strip()
    if not raw:
        return None
    lowered = raw.lower()
    if lowered in SITE_HOMES:
        return SITE_HOMES[lowered]
    if "://" in raw:
        parsed = urllib.parse.urlparse(raw)
        if parsed.scheme in {"http", "https"} and parsed.netloc:
            return raw
        return None
    # "youtube.com/foo" ou "youtube.com" -> https://
    if "." in raw.split("/")[0]:
        return "https://" + raw
    return None


class AbrirSite(Tool):
    name = "abrir_site"
    description = (
        "Abre um site no navegador padrão do usuário. Aceita URL completa, "
        "'youtube.com', ou um apelido conhecido (youtube, gmail, agenda, drive...)."
    )
    risk = Risk.WRITE
    parameters = {
        "type": "object",
        "properties": {
            "endereco": {**_STR, "description": "URL ou nome do site a abrir."}
        },
        "required": ["endereco"],
        "additionalProperties": False,
    }

    async def execute(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        url = _normalize_url(str(args.get("endereco", "")))
        if url is None:
            return ToolResult.failure(
                "Não reconheci o endereco. Passe uma URL (https://...) ou um "
                f"apelido: {', '.join(sorted(SITE_HOMES))}."
            )
        if not webbrowser.open(url, new=2):
            return ToolResult.failure(
                "Não consegui acionar o navegador padrão do sistema."
            )
        return ToolResult(
            ok=True,
            content="Site aberto no navegador do usuário.",
            display=f"abriu {url}",
        )


class PesquisarWeb(Tool):
    name = "pesquisar_web"
    description = (
        "Faz uma pesquisa e abre os resultados no navegador. Informe 'site' para "
        f"escolher onde buscar: {', '.join(sorted(SEARCH_SITES))} "
        "(padrão: google)."
    )
    risk = Risk.WRITE
    parameters = {
        "type": "object",
        "properties": {
            "consulta": {**_STR, "description": "O que pesquisar."},
            "site": {
                **_STR,
                "description": "Onde pesquisar (youtube, google, maps...). Opcional.",
            },
        },
        "required": ["consulta"],
        "additionalProperties": False,
    }

    async def execute(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        query = str(args.get("consulta", "")).strip()
        if not query:
            return ToolResult.failure("Diga o que devo pesquisar.")
        site = str(args.get("site", "google")).strip().lower() or "google"
        template = SEARCH_SITES.get(site)
        if template is None:
            return ToolResult.failure(
                f"Não sei pesquisar em '{site}'. Opções: {', '.join(sorted(SEARCH_SITES))}."
            )
        encoded = urllib.parse.quote_plus(query)
        url = template.replace("{consulta}", encoded)
        if not webbrowser.open(url, new=2):
            return ToolResult.failure(
                "Não consegui acionar o navegador padrão do sistema."
            )
        return ToolResult(
            ok=True,
            content=f"Pesquisa por '{query}' aberta no {site}.",
            display=f"pesquisou '{query}' em {site}",
        )


class GerenciarGuiasNavegador(Tool):
    """Gerencia guias e navegação no navegador ativo por comandos de voz."""

    name = "gerenciar_guias_navegador"
    description = (
        "Controla as guias e páginas do navegador da web: "
        "abrir nova guia, fechar guia atual, reabrir última guia fechada, "
        "próxima guia, guia anterior, recarregar página, voltar página, avançar página."
    )
    risk = Risk.WRITE
    parameters = {
        "type": "object",
        "properties": {
            "acao": {
                "type": "string",
                "enum": [
                    "nova_guia", "fechar_guia", "reabrir_guia_fechada",
                    "proxima_guia", "guia_anterior", "recarregar_pagina",
                    "voltar_pagina", "avancar_pagina", "zoom_in", "zoom_out", "zoom_reset"
                ],
                "description": "Ação a executar nas guias ou página do navegador.",
            },
        },
        "required": ["acao"],
        "additionalProperties": False,
    }

    async def execute(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        import ctypes
        import sys

        acao = str(args.get("acao", "")).strip().lower()

        if sys.platform != "win32":
            return ToolResult.failure("Controle de guias via atalhos disponível apenas no Windows.")

        user32 = ctypes.windll.user32

        def press(*keys: int) -> None:
            for k in keys:
                user32.keybd_event(k, 0, 0, 0)
            for k in reversed(keys):
                user32.keybd_event(k, 0, 2, 0)

        VK_CONTROL = 0x11
        VK_SHIFT = 0x10
        VK_MENU = 0x12  # Alt
        VK_TAB = 0x09
        VK_F5 = 0x74
        VK_LEFT = 0x25
        VK_RIGHT = 0x27

        if acao == "nova_guia":
            press(VK_CONTROL, 0x54)  # Ctrl + T
            return ToolResult(ok=True, content="Nova guia aberta no navegador.", display="abriu nova guia")
        elif acao == "fechar_guia":
            press(VK_CONTROL, 0x57)  # Ctrl + W
            return ToolResult(ok=True, content="Guia atual do navegador fechada.", display="fechou guia")
        elif acao == "reabrir_guia_fechada":
            press(VK_CONTROL, VK_SHIFT, 0x54)  # Ctrl + Shift + T
            return ToolResult(ok=True, content="Última guia fechada foi reaberta.", display="reabriu guia fechada")
        elif acao == "proxima_guia":
            press(VK_CONTROL, VK_TAB)  # Ctrl + Tab
            return ToolResult(ok=True, content="Alternado para a próxima guia.", display="próxima guia")
        elif acao == "guia_anterior":
            press(VK_CONTROL, VK_SHIFT, VK_TAB)  # Ctrl + Shift + Tab
            return ToolResult(ok=True, content="Alternado para a guia anterior.", display="guia anterior")
        elif acao == "recarregar_pagina":
            press(VK_F5)
            return ToolResult(ok=True, content="Página recarregada.", display="recarregou página")
        elif acao == "voltar_pagina":
            press(VK_MENU, VK_LEFT)  # Alt + Left
            return ToolResult(ok=True, content="Voltou para a página anterior no histórico.", display="voltou página")
        elif acao == "avancar_pagina":
            press(VK_MENU, VK_RIGHT)  # Alt + Right
            return ToolResult(ok=True, content="Avançou para a próxima página no histórico.", display="avançou página")
        elif acao == "zoom_in":
            press(VK_CONTROL, 0xBB)  # Ctrl + Plus
            return ToolResult(ok=True, content="Zoom aumentado.", display="zoom in")
        elif acao == "zoom_out":
            press(VK_CONTROL, 0xBD)  # Ctrl + Minus
            return ToolResult(ok=True, content="Zoom diminuído.", display="zoom out")
        elif acao == "zoom_reset":
            press(VK_CONTROL, 0x30)  # Ctrl + 0
            return ToolResult(ok=True, content="Zoom redefinido para 100%.", display="zoom reset")

        return ToolResult.failure(f"Ação de guia '{acao}' não reconhecida.")
