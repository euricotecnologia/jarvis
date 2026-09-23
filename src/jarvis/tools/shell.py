from __future__ import annotations

import asyncio
import re
import subprocess
import sys
from typing import Any

from jarvis.tools.base import Risk, Tool, ToolResult
from jarvis.tools.context import ToolContext

# Padroes que quase sempre destroem ou vazam algo: exigem confirmação mesmo
# com a política "confirmar so o irreversivel".
_DESTRUCTIVE = re.compile(
    r"\b(rm|del|erase|rmdir|rd|format|mkfs|diskpart|reg\s+delete|"
    r"remove-item|clear-content|set-content|out-file|"
    r"stop-computer|restart-computer|shutdown|takeown|icacls)\b"
    r"|>\s*\S"
    r"|\bcurl\b.*\|\s*(sh|bash|pwsh|powershell)"
    r"|Invoke-WebRequest.*\|\s*Invoke-Expression",
    re.IGNORECASE,
)

# Acesso remoto NAO passa pelo shell: existe a ferramenta 'executar_no_servidor'.
# Isso evita o agente tentar rodar ssh na mao ou baixar putty/plink.
_REMOTE_SSH = re.compile(
    r"^\s*(?:sudo\s+)?(ssh|scp|sftp|plink|pscp|putty)\b"
    r"|\b(?:winget|choco|scoop)\s+install\b.*\b(openssh|putty|plink)\b"
    r"|\bInstall-Module\b.*OpenSSH"
    r"|Add-WindowsCapability\b.*OpenSSH",
    re.IGNORECASE,
)


class ExecutarComando(Tool):
    name = "executar_comando"
    description = (
        "Executa um comando no PowerShell do Windows e devolve a saída. "
        "Use para tarefas de sistema, git, scripts e utilitarios."
    )
    risk = Risk.WRITE
    parameters = {
        "type": "object",
        "properties": {
            "comando": {"type": "string", "description": "Comando PowerShell."},
            "pasta_de_trabalho": {
                "type": "string",
                "description": "Pasta onde rodar (opcional, deve estar nas permitidas).",
            },
        },
        "required": ["comando"],
        "additionalProperties": False,
    }

    def is_destructive(self, args: dict[str, Any], ctx: ToolContext) -> bool:
        return bool(_DESTRUCTIVE.search(str(args.get("comando", ""))))

    def confirm_message(self, args: dict[str, Any]) -> str:
        return f"executar no shell: {args.get('comando')}"

    async def execute(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        command = str(args.get("comando", "")).strip()
        if not command:
            return ToolResult.failure("Comando vazio.")

        if _REMOTE_SSH.search(command):
            return ToolResult.failure(
                "Para acessar um servidor remoto use a ferramenta "
                "'executar_no_servidor' (o cliente SSH ja vem pronto - NAO "
                "instale putty, plink nem OpenSSH). Se ela nao aparecer, o "
                "usuario precisa ligar 'Acesso SSH' em Configurações > "
                "Permissões (ou usar o perfil Desenvolvimento) e cadastrar o "
                "servidor."
            )

        cwd = None
        raw_cwd = str(args.get("pasta_de_trabalho", "")).strip()
        if raw_cwd:
            path = ctx.resolve_writable(raw_cwd)
            if not path.is_dir():
                return ToolResult.failure(f"Pasta de trabalho invalida: {path}")
            cwd = str(path)

        if sys.platform == "win32":
            argv = [
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                command,
            ]
        else:  # facilita testes fora do Windows
            argv = ["/bin/sh", "-c", command]

        try:
            completed = await asyncio.to_thread(
                subprocess.run,
                argv,
                capture_output=True,
                text=True,
                cwd=cwd,
                timeout=ctx.config.shell_timeout_seconds,
            )
        except subprocess.TimeoutExpired:
            return ToolResult.failure(
                f"O comando passou de {ctx.config.shell_timeout_seconds:.0f}s e foi encerrado."
            )
        except OSError as exc:
            return ToolResult.failure(f"Não consegui executar: {exc}")

        limit = ctx.config.max_output_chars
        stdout = (completed.stdout or "").strip()
        stderr = (completed.stderr or "").strip()
        blocks = [f"exit_code={completed.returncode}"]
        if stdout:
            blocks.append(f"stdout:\n{stdout[:limit]}")
        if stderr:
            blocks.append(f"stderr:\n{stderr[:limit]}")
        return ToolResult(
            ok=completed.returncode == 0,
            content="\n\n".join(blocks),
            display=f"{command[:60]} (exit {completed.returncode})",
        )
