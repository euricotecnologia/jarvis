from __future__ import annotations

from typing import TYPE_CHECKING, Any

from jarvis.tools.base import Risk, Tool, ToolResult

if TYPE_CHECKING:
    from jarvis.tools.context import ToolContext


class LerEAnalisarTela(Tool):
    """Lê e analisa o conteúdo visual e textual exibido na tela do computador."""

    name = "ler_e_analisar_tela"
    description = (
        "Captura a tela do computador e faz uma leitura e análise multimodal completa do que está "
        "sendo exibido. Use para responder dúvidas sobre erros no código, formulários, páginas web abertas, "
        "documentos, gráficos, planilhas ou quando o usuário pedir 'Jarvis, o que está na minha tela?', "
        "'leia o que está escrito', 'explique o erro na tela', 'resuma este documento na tela'."
    )
    risk = Risk.SAFE
    parameters = {
        "type": "object",
        "properties": {
            "pergunta_ou_foco": {
                "type": "string",
                "description": (
                    "O que você deve analisar ou responder sobre a tela. "
                    "Ex: 'qual o erro mostrado no terminal?', 'resuma este texto', "
                    "'leia os dados deste formulário', 'o que está acontecendo na tela?'"
                ),
            },
        },
        "required": [],
        "additionalProperties": False,
    }

    async def execute(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        from jarvis import screenshot

        if not screenshot.available():
            return ToolResult.failure(
                "Módulo de captura de tela não disponível. Instale dependências com: pip install Pillow"
            )

        try:
            jpeg = screenshot.capture_screen()
        except Exception as exc:
            return ToolResult.failure(f"Não foi possível capturar a tela: {exc}")

        if ctx.emit_media is not None:
            ctx.emit_media(jpeg, "image", "Leitura e Análise da Tela")

        foco = str(args.get("pergunta_ou_foco", "")).strip()
        prompt_visao = foco or (
            "Descreva detalhadamente o conteúdo desta tela: quais aplicativos estão abertos, "
            "quais textos e títulos principais aparecem, e se há alguma mensagem de erro, aviso "
            "ou código importante em exibição."
        )

        if ctx.describe_image is not None:
            try:
                analise = ctx.describe_image(jpeg, prompt_visao)
                return ToolResult(
                    ok=True,
                    content=f"Tela capturada e analisada com sucesso:\n\n{analise}",
                    display="leu e analisou a tela",
                )
            except Exception as exc:
                return ToolResult(
                    ok=True,
                    content=(
                        "Capturei o print da tela e exibi no chat, mas ocorreu uma instabilidade "
                        f"no motor de visão multimodal: {exc}"
                    ),
                    display="capturou a tela",
                )

        return ToolResult(
            ok=True,
            content="Capturei a imagem da tela e já mostrei no chat para você.",
            display="capturou a tela",
        )
