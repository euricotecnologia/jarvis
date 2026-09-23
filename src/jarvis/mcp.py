"""Cliente MCP (Model Context Protocol) real, por stdio.

Fala JSON-RPC 2.0 delimitado por linha com um servidor MCP: `initialize` ->
`notifications/initialized` -> `tools/list` -> `tools/call`. Sem dependência
externa (só subprocess + json + threading). Cada servidor cadastrado vira um
conjunto de ferramentas dinâmicas para o agente.
"""

from __future__ import annotations

import json
import os
import queue
import shutil
import subprocess
import sys
import threading
import time
from typing import TYPE_CHECKING, Any

from jarvis.errors import JarvisError
from jarvis.tools.base import Risk, Tool, ToolResult

if TYPE_CHECKING:
    from jarvis.database import Database
    from jarvis.tools.context import ToolContext

_PROTOCOL = "2024-11-05"
_CLIENT_INFO = {"name": "jarvis", "version": "1.0"}


class MCPError(JarvisError):
    """Falha previsível ao falar com um servidor MCP."""


def _resolve_command(command: str) -> str:
    found = shutil.which(command)
    if found:
        return found
    # atalhos comuns no Windows
    for alt in (command + ".cmd", command + ".exe", command + ".bat"):
        found = shutil.which(alt)
        if found:
            return found
    if os.path.isfile(command):
        return command
    return command  # deixa o Popen tentar / falhar com erro claro


def _no_window() -> int:
    return getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0


class MCPClient:
    """Conexão viva com um servidor MCP por stdio."""

    def __init__(
        self,
        command: str,
        args: list[str] | None = None,
        env: dict[str, str] | None = None,
    ) -> None:
        self.command = command
        self.args = list(args or [])
        self.env = dict(env or {})
        self._proc: subprocess.Popen | None = None
        self._next_id = 1
        self._pending: dict[int, queue.Queue] = {}
        self._lock = threading.Lock()
        self._reader: threading.Thread | None = None
        self._alive = False
        self.server_info: dict[str, Any] = {}

    # -- ciclo de vida -------------------------------------------------
    def start(self, *, timeout: float = 20.0) -> None:
        argv = [_resolve_command(self.command), *self.args]
        full_env = {**os.environ, **self.env}
        try:
            self._proc = subprocess.Popen(
                argv,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                bufsize=1,
                env=full_env,
                creationflags=_no_window(),
            )
        except OSError as exc:
            raise MCPError(
                f"não consegui iniciar '{self.command}': {exc}. "
                "Confira o comando (ex.: 'npx', 'uvx', 'python')."
            ) from exc

        self._alive = True
        self._reader = threading.Thread(target=self._read_loop, daemon=True)
        self._reader.start()

        init = self._request(
            "initialize",
            {
                "protocolVersion": _PROTOCOL,
                "capabilities": {},
                "clientInfo": _CLIENT_INFO,
            },
            timeout=timeout,
        )
        self.server_info = init.get("serverInfo", {}) if isinstance(init, dict) else {}
        self._notify("notifications/initialized")

    def close(self) -> None:
        self._alive = False
        proc = self._proc
        if proc is None:
            return
        for stream in (proc.stdin, proc.stdout, proc.stderr):
            try:
                stream and stream.close()
            except OSError:
                pass
        try:
            proc.terminate()
            proc.wait(timeout=3)
        except Exception:  # noqa: BLE001
            try:
                proc.kill()
            except Exception:  # noqa: BLE001
                pass
        self._proc = None

    # -- API ---------------------------------------------------------
    def list_tools(self, *, timeout: float = 15.0) -> list[dict[str, Any]]:
        result = self._request("tools/list", {}, timeout=timeout)
        tools = result.get("tools", []) if isinstance(result, dict) else []
        return [t for t in tools if isinstance(t, dict) and t.get("name")]

    def call_tool(
        self, name: str, arguments: dict[str, Any], *, timeout: float = 90.0
    ) -> str:
        result = self._request(
            "tools/call", {"name": name, "arguments": arguments or {}}, timeout=timeout
        )
        if not isinstance(result, dict):
            return str(result)
        pieces: list[str] = []
        for block in result.get("content", []) or []:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    pieces.append(str(block.get("text", "")))
                elif block.get("type") == "resource":
                    res = block.get("resource", {})
                    pieces.append(str(res.get("text") or res.get("uri") or res))
                else:
                    pieces.append(json.dumps(block, ensure_ascii=False))
        text = "\n".join(p for p in pieces if p).strip() or json.dumps(
            result, ensure_ascii=False
        )
        if result.get("isError"):
            return f"[o servidor MCP reportou erro] {text}"
        return text

    # -- transporte -------------------------------------------------
    def _request(self, method: str, params: dict, *, timeout: float) -> Any:
        if not self._alive or self._proc is None or self._proc.stdin is None:
            raise MCPError("conexão MCP não está ativa")
        with self._lock:
            msg_id = self._next_id
            self._next_id += 1
            box: queue.Queue = queue.Queue(maxsize=1)
            self._pending[msg_id] = box
        payload = {"jsonrpc": "2.0", "id": msg_id, "method": method, "params": params}
        self._write(payload)
        try:
            kind, value = box.get(timeout=timeout)
        except queue.Empty:
            self._pending.pop(msg_id, None)
            raise MCPError(f"o servidor MCP não respondeu '{method}' em {timeout:.0f}s")
        if kind == "error":
            raise MCPError(f"MCP {method}: {value}")
        return value

    def _notify(self, method: str, params: dict | None = None) -> None:
        self._write({"jsonrpc": "2.0", "method": method, "params": params or {}})

    def _write(self, payload: dict) -> None:
        proc = self._proc
        if proc is None or proc.stdin is None:
            raise MCPError("stdin do servidor MCP fechado")
        try:
            proc.stdin.write(json.dumps(payload, ensure_ascii=False) + "\n")
            proc.stdin.flush()
        except OSError as exc:
            raise MCPError(f"não consegui enviar ao servidor MCP: {exc}") from exc

    def _read_loop(self) -> None:
        proc = self._proc
        if proc is None or proc.stdout is None:
            return
        try:
            for line in iter(proc.stdout.readline, ""):
                line = line.strip()
                if not line:
                    continue
                try:
                    msg = json.loads(line)
                except json.JSONDecodeError:
                    continue  # servidores às vezes logam texto no stdout
                if not isinstance(msg, dict) or "id" not in msg:
                    continue  # notificação do servidor -> ignora
                box = self._pending.pop(msg["id"], None)
                if box is None:
                    continue
                if "error" in msg:
                    err = msg["error"]
                    detail = err.get("message", err) if isinstance(err, dict) else err
                    box.put(("error", detail))
                else:
                    box.put(("ok", msg.get("result")))
        except (ValueError, OSError):
            pass  # stream fechado por close()
        finally:
            self._alive = False
            for box in list(self._pending.values()):  # acorda quem espera
                try:
                    box.put(("error", "o servidor MCP encerrou"))
                except Exception:  # noqa: BLE001
                    pass

    def stderr_tail(self, limit: int = 600) -> str:
        proc = self._proc
        if proc is None or proc.stderr is None:
            return ""
        try:
            return (proc.stderr.read() or "")[-limit:]
        except Exception:  # noqa: BLE001
            return ""


class DynamicMCPTool(Tool):
    """Uma ferramenta remota de um servidor MCP, exposta ao agente."""

    def __init__(self, manager: "MCPManager", server: str, tool: dict[str, Any]) -> None:
        self._manager = manager
        self.server_name = server
        self.remote_name = str(tool.get("name"))
        self.name = _tool_id(server, self.remote_name)
        self.description = (
            f"[MCP:{server}] "
            + str(tool.get("description") or f"ferramenta {self.remote_name}")
        )[:900]
        schema = tool.get("inputSchema") or {"type": "object", "properties": {}}
        if not isinstance(schema, dict) or schema.get("type") != "object":
            schema = {"type": "object", "properties": {}}
        self.parameters = schema
        self.risk = Risk.WRITE

    def is_destructive(self, args: dict[str, Any], ctx: "ToolContext") -> bool:
        return True  # ferramenta externa: confirma antes de rodar

    def confirm_message(self, args: dict[str, Any]) -> str:
        return f"MCP {self.server_name} → {self.remote_name}({json.dumps(args, ensure_ascii=False)[:120]})"

    async def execute(self, args: dict[str, Any], ctx: "ToolContext") -> ToolResult:
        import asyncio

        try:
            text = await asyncio.to_thread(
                self._manager.call, self.server_name, self.remote_name, args
            )
        except MCPError as exc:
            return ToolResult.failure(str(exc))
        limit = getattr(ctx.config, "max_output_chars", 12000)
        return ToolResult(
            ok=True, content=text[:limit],
            display=f"{self.server_name}:{self.remote_name}",
        )


def _tool_id(server: str, tool: str) -> str:
    safe = "".join(c if c.isalnum() else "_" for c in f"{server}_{tool}").lower()
    return f"mcp_{safe}"[:60]


class MCPManager:
    """Mantém as conexões MCP e o catálogo de ferramentas (cache curto)."""

    _CACHE_TTL = 30.0

    def __init__(self, database: "Database") -> None:
        self.database = database
        self._clients: dict[str, MCPClient] = {}
        self._tool_cache: list[Tool] = []
        self._cache_at = 0.0
        self._status: dict[str, str] = {}
        self._lock = threading.RLock()

    # -- ferramentas para o agente ---------------------------------
    def load_active_mcp_tools(self, *, force: bool = False) -> list[Tool]:
        now = time.monotonic()
        if not force and self._tool_cache and now - self._cache_at < self._CACHE_TTL:
            return list(self._tool_cache)
        with self._lock:
            tools: list[Tool] = []
            self._status = {}
            for server in self.database.list_mcp_servers():
                if not server.get("enabled"):
                    continue
                name = str(server.get("name") or "server")
                try:
                    client = self._client_for(server)
                    for meta in client.list_tools():
                        tools.append(DynamicMCPTool(self, name, meta))
                    self._status[name] = f"ok ({sum(1 for t in tools if isinstance(t, DynamicMCPTool) and t.server_name == name)} ferramentas)"
                except MCPError as exc:
                    self._status[name] = f"falhou: {exc}"
                except Exception as exc:  # noqa: BLE001
                    self._status[name] = f"erro: {exc}"
            self._tool_cache = tools
            self._cache_at = now
            return list(tools)

    def call(self, server: str, tool: str, args: dict[str, Any]) -> str:
        row = next(
            (s for s in self.database.list_mcp_servers() if s.get("name") == server),
            None,
        )
        if row is None:
            raise MCPError(f"servidor MCP '{server}' não está cadastrado")
        if not row.get("enabled"):
            raise MCPError(f"servidor MCP '{server}' está desativado")
        with self._lock:
            client = self._client_for(row)
        return client.call_tool(tool, args)

    # -- teste de conexão (UI) -----------------------------------
    def probe(self, server: dict[str, Any]) -> dict[str, Any]:
        name = str(server.get("name") or "server")
        try:
            client = MCPClient(
                str(server.get("command", "")),
                _parse_args(server.get("args")),
                _parse_env(server.get("env_vars")),
            )
            client.start(timeout=25)
            tools = client.list_tools()
            info = client.server_info
            client.close()
            return {
                "ok": True,
                "server": name,
                "serverInfo": info,
                "tools": [
                    {"name": t.get("name"), "description": t.get("description", "")}
                    for t in tools
                ],
            }
        except MCPError as exc:
            return {"ok": False, "server": name, "error": str(exc)}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "server": name, "error": f"{exc}"}

    def status(self) -> dict[str, str]:
        return dict(self._status)

    def invalidate(self) -> None:
        """Descarta catálogo e conexões — a config dos servidores mudou.

        Fecha os subprocessos vivos para que a próxima carga suba clientes
        novos com o comando/args atuais (senão uma edição só valeria após
        reiniciar o app) e para não deixar processo órfão ao remover/desligar.
        """
        with self._lock:
            self._tool_cache = []
            self._cache_at = 0.0
            for client in list(self._clients.values()):
                try:
                    client.close()
                except Exception:  # noqa: BLE001
                    pass
            self._clients.clear()

    def shutdown(self) -> None:
        with self._lock:
            for client in list(self._clients.values()):
                try:
                    client.close()
                except Exception:  # noqa: BLE001
                    pass
            self._clients.clear()
            self._tool_cache = []
            self._cache_at = 0.0

    # -- interno ---------------------------------------------------
    def _client_for(self, server: dict[str, Any]) -> MCPClient:
        name = str(server.get("name") or "server")
        client = self._clients.get(name)
        if client is not None and client._alive:
            return client
        if client is not None:
            client.close()
        client = MCPClient(
            str(server.get("command", "")),
            _parse_args(server.get("args")),
            _parse_env(server.get("env_vars")),
        )
        client.start()
        self._clients[name] = client
        return client


def _parse_args(raw: Any) -> list[str]:
    if isinstance(raw, list):
        return [str(x) for x in raw]
    try:
        value = json.loads(raw) if raw else []
        return [str(x) for x in value] if isinstance(value, list) else []
    except (json.JSONDecodeError, TypeError):
        return str(raw).split() if raw else []


def _parse_env(raw: Any) -> dict[str, str]:
    if isinstance(raw, dict):
        return {str(k): str(v) for k, v in raw.items()}
    try:
        value = json.loads(raw) if raw else {}
        return {str(k): str(v) for k, v in value.items()} if isinstance(value, dict) else {}
    except (json.JSONDecodeError, TypeError):
        return {}


# compat: código antigo chamava MCPServerManager(db).load_active_mcp_tools()
MCPServerManager = MCPManager
