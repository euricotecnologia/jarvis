from __future__ import annotations

import asyncio
from typing import Any

from jarvis.tools.base import Risk, Tool, ToolResult
from jarvis.tools.context import ToolContext

_STR = {"type": "string"}


def _db(ctx: ToolContext):
    if ctx.database is None:
        raise RuntimeError("banco de dados indisponível para as ferramentas de servidor")
    return ctx.database


class ListarServidores(Tool):
    name = "listar_servidores"
    description = (
        "Lista os servidores (VPS) que o usuário cadastrou e que você pode "
        "acessar por SSH. Use antes de 'executar_no_servidor' se não souber o apelido."
    )
    risk = Risk.SAFE

    async def execute(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        servers = _db(ctx).list_servers()
        if not servers:
            return ToolResult(
                ok=True,
                content="Nenhum servidor cadastrado. O usuário adiciona em "
                "Configurações > Servidores.",
                display="0 servidores",
            )
        lines = []
        for server in servers:
            line = f"- {server.alias}: {server.user}@{server.host}:{server.port} ({server.auth})"
            if server.notes:
                line += f" -- {server.notes}"
            lines.append(line)
        return ToolResult(
            ok=True,
            content="\n".join(lines),
            display=f"{len(servers)} servidor(es)",
        )


class ExecutarNoServidor(Tool):
    name = "executar_no_servidor"
    description = (
        "Roda um comando shell (Linux) num servidor remoto por SSH e devolve a "
        "saída. 'servidor' e o apelido cadastrado (veja 'listar_servidores'). "
        "TODO comando remoto pede confirmação do usuário."
    )
    risk = Risk.WRITE
    parameters = {
        "type": "object",
        "properties": {
            "servidor": {**_STR, "description": "Apelido do servidor cadastrado."},
            "comando": {**_STR, "description": "Comando shell a executar no servidor."},
        },
        "required": ["servidor", "comando"],
        "additionalProperties": False,
    }

    def is_destructive(self, args: dict[str, Any], ctx: ToolContext) -> bool:
        return True  # servidor externo: sempre confirma

    def confirm_message(self, args: dict[str, Any]) -> str:
        return f"SSH em '{args.get('servidor')}': {args.get('comando')}"

    async def execute(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        alias = str(args.get("servidor", "")).strip()
        command = str(args.get("comando", "")).strip()
        if not command:
            return ToolResult.failure("Diga o comando a rodar no servidor.")
        database = _db(ctx)
        server = database.find_server(alias) if alias else None
        if server is None:
            known = ", ".join(s.alias for s in database.list_servers()) or "nenhum"
            return ToolResult.failure(
                f"Servidor '{alias}' não encontrado. Cadastrados: {known}."
            )

        password = None
        if server.auth == "password":
            from jarvis.secret_store import decrypt_value

            password = decrypt_value(server.password_enc)
            if not password:
                return ToolResult.failure(
                    f"A senha de '{alias}' não está salva. Recadastre em "
                    "Configurações > Servidores."
                )

        from jarvis import ssh as sshmod

        try:
            result = await asyncio.to_thread(
                sshmod.run_remote,
                server,
                command,
                timeout=ctx.config.shell_timeout_seconds,
                password=password,
            )
        except sshmod.SSHError as exc:
            return ToolResult.failure(f"SSH falhou: {exc}")

        limit = ctx.config.max_output_chars
        blocks = [f"exit_code={result.exit_code}"]
        if result.stdout:
            blocks.append(f"stdout:\n{result.stdout[:limit]}")
        if result.stderr:
            blocks.append(f"stderr:\n{result.stderr[:limit]}")
        return ToolResult(
            ok=result.ok,
            content="\n\n".join(blocks),
            display=f"{alias}: {command[:50]} (exit {result.exit_code})",
        )
