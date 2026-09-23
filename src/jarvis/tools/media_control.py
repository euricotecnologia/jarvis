from __future__ import annotations

import ctypes
import os
import sys
import urllib.parse
from typing import TYPE_CHECKING, Any

from jarvis.tools.base import Tool

if TYPE_CHECKING:
    from jarvis.tools.context import ToolContext

# Windows Virtual Key Codes para Controle Multimídia
VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP = 0xAF
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_MEDIA_STOP = 0xB2
VK_MEDIA_PLAY_PAUSE = 0xB3


def _send_media_key(vk_code: int) -> None:
    """Dispara um evento de tecla multimídia no Windows."""
    if sys.platform == "win32":
        user32 = ctypes.windll.user32
        user32.keybd_event(vk_code, 0, 0, 0)
        user32.keybd_event(vk_code, 0, 2, 0)


class ControleReproducao(Tool):
    """Controla a reprodução de mídia mãos-livres (Play, Pause, Próxima, Anterior, Parar)."""

    name = "controle_reproducao"
    description = (
        "Controla a reprodução de músicas e vídeos no sistema operacional mãos-livres: "
        "play/pause, próxima faixa, faixa anterior ou parar."
    )
    parameters = {
        "type": "object",
        "properties": {
            "acao": {
                "type": "string",
                "enum": ["play_pause", "proxima_faixa", "faixa_anterior", "parar"],
                "description": "Comando de reprodução de mídia.",
            },
        },
        "required": ["acao"],
    }

    async def run(self, args: dict[str, Any], context: ToolContext) -> str:
        acao = str(args.get("acao", "play_pause")).strip().lower()

        if sys.platform != "win32":
            return "Controle de reprodução disponível apenas no Windows."

        if acao in ("play_pause", "play", "pause"):
            _send_media_key(VK_MEDIA_PLAY_PAUSE)
            return "Reproduzir / Pausar acionado."
        elif acao in ("proxima_faixa", "proxima", "next"):
            _send_media_key(VK_MEDIA_NEXT_TRACK)
            return "Avançado para a próxima faixa."
        elif acao in ("faixa_anterior", "anterior", "prev", "previous"):
            _send_media_key(VK_MEDIA_PREV_TRACK)
            return "Retornado para a faixa anterior."
        elif acao in ("parar", "stop"):
            _send_media_key(VK_MEDIA_STOP)
            return "Reprodução de mídia parada."

        return f"Ação de mídia '{acao}' não reconhecida."


class AjustarVolume(Tool):
    """Ajusta o volume do sistema operacional (definir nível, aumentar, diminuir, mutar)."""

    name = "ajustar_volume"
    description = (
        "Controla o volume de áudio do computador: "
        "definir volume específico (0 a 100%), aumentar volume, diminuir volume, mutar ou desmutar."
    )
    parameters = {
        "type": "object",
        "properties": {
            "acao": {
                "type": "string",
                "enum": ["definir_volume", "aumentar_volume", "diminuir_volume", "mutar_desmutar"],
                "description": "Ação de volume desejada.",
            },
            "nivel": {
                "type": "integer",
                "description": "Nível de volume de 0 a 100 (necessário quando acao='definir_volume').",
            },
        },
        "required": ["acao"],
    }

    async def run(self, args: dict[str, Any], context: ToolContext) -> str:
        acao = str(args.get("acao", "")).strip().lower()
        nivel = args.get("nivel")

        if sys.platform != "win32":
            return "Ajuste de volume disponível apenas no Windows."

        if acao == "mutar_desmutar" or acao == "mutar":
            _send_media_key(VK_VOLUME_MUTE)
            return "Mudo de áudio alternado com sucesso."

        elif acao == "aumentar_volume":
            # Pressiona volume up 3 vezes (~6%)
            for _ in range(3):
                _send_media_key(VK_VOLUME_UP)
            return "Volume do sistema aumentado."

        elif acao == "diminuir_volume":
            # Pressiona volume down 3 vezes (~6%)
            for _ in range(3):
                _send_media_key(VK_VOLUME_DOWN)
            return "Volume do sistema reduzido."

        elif acao == "definir_volume" and nivel is not None:
            clamped = max(0, min(100, int(nivel)))
            # Ajuste de volume master via PowerShell CoreAudio
            ps_script = f"""
            $obj = New-Object -ComObject WScript.Shell
            1..50 | ForEach-Object {{ $obj.SendKeys([char]174) }}
            1..{int(clamped / 2)} | ForEach-Object {{ $obj.SendKeys([char]175) }}
            """
            os.system(f'powershell -command "{ps_script.strip()}"')
            return f"Volume do sistema ajustado para aproximadamente {clamped}%."

        return f"Comando de volume '{acao}' não reconhecido."


class TocarMusicaOuVideo(Tool):
    """Busca e reproduz músicas ou vídeos no YouTube, Spotify ou navegador."""

    name = "tocar_musica_ou_video"
    description = (
        "Pesquisa e reproduz músicas ou vídeos no YouTube ou Spotify mãos-livres. "
        "Ex: 'tocar Bohemian Rhapsody no YouTube', 'tocar rock no Spotify'."
    )
    parameters = {
        "type": "object",
        "properties": {
            "termo_busca": {
                "type": "string",
                "description": "Nome da música, artista, vídeo ou gênero a reproduzir.",
            },
            "plataforma": {
                "type": "string",
                "enum": ["youtube", "spotify", "padrao"],
                "description": "Plataforma onde reproduzir (padrão: 'youtube').",
            },
        },
        "required": ["termo_busca"],
    }

    async def run(self, args: dict[str, Any], context: ToolContext) -> str:
        termo = str(args.get("termo_busca", "")).strip()
        plataforma = str(args.get("plataforma", "youtube")).strip().lower()

        if not termo:
            return "Informe o nome da música ou vídeo a reproduzir."

        encoded = urllib.parse.quote_plus(termo)

        if plataforma == "spotify":
            spotify_uri = f"spotify:search:{encoded}"
            try:
                os.system(f"start {spotify_uri}")
                return f"Abrindo Spotify com a pesquisa: '{termo}'."
            except Exception:
                pass

        # Fallback YouTube
        youtube_url = f"https://www.youtube.com/results?search_query={encoded}"
        os.system(f"start {youtube_url}")
        return f"Abrindo reprodução no YouTube para: '{termo}'."
