"""Ferramentas do agente que "veem": webcam e captura de tela."""

from __future__ import annotations

from typing import Any

from jarvis.tools.base import Risk, Tool, ToolResult
from jarvis.tools.context import ToolContext


class VerPelaWebcam(Tool):
    name = "ver_pela_webcam"
    description = (
        "Tira uma foto pela webcam do usuário, mostra ela no chat e descreve o "
        "que aparece. Use quando pedirem para você 'ver', 'olhar', 'enxergar' "
        "algo pela câmera, dizer o que está na frente, que cor e, o que o usuário "
        "esta segurando, ler um papel/tela mostrado a câmera, etc."
    )
    risk = Risk.SAFE
    parameters = {
        "type": "object",
        "properties": {
            "pergunta": {
                "type": "string",
                "description": (
                    "O que observar na imagem. Ex.: 'o que estou segurando?', "
                    "'descreva o ambiente', 'leia o que está escrito'."
                ),
            }
        },
        "required": [],
        "additionalProperties": False,
    }

    async def execute(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        if ctx.vision is None:
            return ToolResult.failure(
                "A visão pela webcam está desligada. O usuário pode habilitar em "
                "Configurações > 05 WEBCAM (VISÃO)."
            )
        question = str(args.get("pergunta", "")).strip()
        try:
            description, jpeg = ctx.vision(question)
        except Exception as exc:  # noqa: BLE001 - vira contexto pro modelo
            return ToolResult.failure(f"Não consegui enxergar: {exc}")
        if ctx.emit_media is not None and jpeg:
            ctx.emit_media(jpeg, "image", "Foto da webcam")
        return ToolResult(
            ok=True,
            content=(
                "Tirei uma foto pela webcam e ja mostrei no chat. O que a imagem "
                f"mostra: {description}"
            ),
            display="olhou pela webcam",
        )


class TirarPrint(Tool):
    name = "tirar_print"
    description = (
        "Tira uma captura da tela do usuário (screenshot) e mostra no chat. Use "
        "quando pedirem 'tira um print', 'mostra a tela', 'captura o que está na "
        "tela'."
    )
    risk = Risk.SAFE
    parameters = {
        "type": "object",
        "properties": {
            "analisar": {
                "type": "string",
                "description": (
                    "Opcional: o que você deve observar/analisar na tela depois de "
                    "capturar (so funciona com um modelo que enxerga imagens)."
                ),
            }
        },
        "required": [],
        "additionalProperties": False,
    }

    async def execute(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        from jarvis import screenshot

        if not screenshot.available():
            return ToolResult.failure(
                'Para tirar prints instale: pip install -e ".[tools]"'
            )
        try:
            jpeg = screenshot.capture_screen()
        except Exception as exc:  # noqa: BLE001
            return ToolResult.failure(f"Não consegui tirar o print: {exc}")
        if ctx.emit_media is not None:
            ctx.emit_media(jpeg, "image", "Captura da tela")

        question = str(args.get("analisar", "")).strip()
        if question and ctx.describe_image is not None:
            try:
                description = ctx.describe_image(jpeg, question)
                return ToolResult(
                    ok=True,
                    content=f"Print tirado e mostrado no chat. Na tela: {description}",
                    display="tirou e analisou um print",
                )
            except Exception as exc:  # noqa: BLE001
                return ToolResult(
                    ok=True,
                    content=(
                        "Print tirado e mostrado no chat, mas não consegui "
                        f"analisar a imagem: {exc}"
                    ),
                    display="tirou um print",
                )
        return ToolResult(
            ok=True,
            content="Print da tela tirado e exibido no chat.",
            display="tirou um print",
        )
