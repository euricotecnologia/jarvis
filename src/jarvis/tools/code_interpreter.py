from __future__ import annotations

import io
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any

from jarvis.tools.base import Risk, Tool, ToolResult

if TYPE_CHECKING:
    from jarvis.tools.context import ToolContext


class InterpretadorCodigo(Tool):
    """Executa scripts Python e comandos em ambiente local isolado para processamento de dados e cálculos."""

    name = "interpretador_codigo"
    description = (
        "Executa código Python no computador de forma isolada para realizar cálculos complexos, "
        "processamento de texto/dados, manipulação de tabelas, simulações ou gerar gráficos. "
        "Se o código gerar gráficos com matplotlib (plt.show() ou plt.savefig()), eles serão exibidos no chat."
    )
    risk = Risk.WRITE
    parameters = {
        "type": "object",
        "properties": {
            "codigo_python": {
                "type": "string",
                "description": "Código Python completo a ser executado.",
            },
            "timeout_segundos": {
                "type": "integer",
                "description": "Tempo máximo de execução em segundos (padrão: 30).",
            },
        },
        "required": ["codigo_python"],
    }

    async def execute(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        code = str(args.get("codigo_python", "")).strip()
        timeout = int(args.get("timeout_segundos", 30))

        if not code:
            return ToolResult.failure("Nenhum código Python foi fornecido para execução.")

        with tempfile.TemporaryDirectory() as tmpdir:
            script_path = Path(tmpdir) / "script.py"
            plot_path = Path(tmpdir) / "plot.png"

            # Injeta interceptação opcional de plt.show() para salvar o gráfico
            wrapped_code = f"""
import sys
import os

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    _orig_show = plt.show
    def _custom_show(*args, **kwargs):
        plt.savefig(r'{plot_path}', bbox_inches='tight', dpi=150)
    plt.show = _custom_show
except ImportError:
    pass

{code}
"""
            script_path.write_text(wrapped_code, encoding="utf-8")

            python_exe = sys.executable or "python"
            try:
                proc = subprocess.run(
                    [python_exe, str(script_path)],
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    cwd=tmpdir,
                )
            except subprocess.TimeoutExpired:
                return ToolResult.failure(f"Tempo limite de execução excedido ({timeout} segundos).")
            except Exception as exc:
                return ToolResult.failure(f"Falha ao executar processo Python: {exc}")

            stdout = proc.stdout.strip()
            stderr = proc.stderr.strip()

            # Se gerou imagem/gráfico, emite para o chat
            if plot_path.exists() and ctx.emit_media is not None:
                try:
                    img_bytes = plot_path.read_bytes()
                    ctx.emit_media(img_bytes, "image", "Gráfico gerado pelo interpretador de código")
                except Exception:
                    pass

            output_lines = []
            if stdout:
                output_lines.append(f"Saída (stdout):\n{stdout}")
            if stderr:
                output_lines.append(f"Erros/Avisos (stderr):\n{stderr}")
            if not stdout and not stderr:
                output_lines.append("Código executado com sucesso (sem saída no terminal).")

            if plot_path.exists():
                output_lines.append("\n[Gráfico gerado e exibido no chat]")

            success = (proc.returncode == 0)
            return ToolResult(
                ok=success,
                content="\n\n".join(output_lines),
                display="executou código Python",
            )
