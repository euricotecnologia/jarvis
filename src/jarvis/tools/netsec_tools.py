from __future__ import annotations

from typing import Any

from jarvis.tools.base import Risk, Tool, ToolResult
from jarvis.tools.context import ToolContext

_STR = {"type": "string"}

_REMOTE = {
    "ping": "ping",
    "traceroute": "traceroute",
    "portas": "portas",
    "porta": "porta_especifica",
    "dns": "dns",
    "dns_reverso": "dns_reverso",
    "whois": "whois",
    "tls": "ssl",
    "http": "http_headers",
    "geoip": "geoip",
    "meu_ip": "meu_ip",
    "arp": "rede_local",
    "analise": "analise",
}
_LOCAL = {
    "portas_escuta": "portas_locais",
    "conexoes": "conexoes",
    "firewall": "firewall",
}


def _params_for(action_id: str, alvo: str, extra: str) -> dict[str, str]:
    if action_id in ("dns", "whois"):
        return {"dominio": alvo}
    if action_id in ("dns_reverso", "geoip"):
        return {"ip": alvo}
    if action_id == "http_headers":
        return {"url": alvo}
    if action_id == "porta_especifica":
        return {"alvo": alvo, "porta": extra}
    if action_id == "portas":
        return {"alvo": alvo, "portas": extra or "comuns"}
    return {"alvo": alvo}


class ReconRede(Tool):
    name = "recon_rede"
    description = (
        "Reconhecimento de rede em Python puro (SEM instalar nada). "
        "'acao': ping | traceroute | portas | porta | dns | dns_reverso | "
        "whois | tls | http | geoip | meu_ip | arp | analise. "
        "'alvo': IP, dominio ou URL (dispensavel em meu_ip/arp). "
        "'extra': lista/faixa de portas p/ 'portas', ou o numero p/ 'porta'. "
        "So use em ativos do proprio usuario / autorizados; nada intrusivo."
    )
    risk = Risk.SAFE
    parameters = {
        "type": "object",
        "properties": {
            "acao": {**_STR, "description": "O que investigar (ver descricao)."},
            "alvo": {**_STR, "description": "IP, dominio ou URL."},
            "extra": {**_STR, "description": "Portas (ex.: comuns, 1-1000, 22,80) ou numero."},
        },
        "required": ["acao"],
        "additionalProperties": False,
    }

    async def execute(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        import asyncio

        from jarvis import netsec

        acao = str(args.get("acao", "")).strip().lower()
        alvo = str(args.get("alvo", "")).strip()
        extra = str(args.get("extra", "")).strip()
        action_id = _REMOTE.get(acao)
        if action_id is None:
            return ToolResult.failure(
                f"acao invalida: {acao!r}. Use: {', '.join(_REMOTE)}."
            )
        if action_id not in ("meu_ip", "rede_local") and not alvo:
            return ToolResult.failure("Informe o 'alvo' (IP, dominio ou URL).")
        params = _params_for(action_id, alvo, extra)
        try:
            report = await asyncio.to_thread(netsec.run_action, action_id, params)
        except Exception as exc:  # noqa: BLE001
            return ToolResult.failure(f"recon falhou: {exc}")
        return ToolResult(
            ok=True,
            content=report[: ctx.config.max_output_chars],
            display=f"recon {acao} {alvo}".strip(),
        )


class InspecaoLocal(Tool):
    name = "inspecao_local"
    description = (
        "Inspeciona a rede DESTE computador (Python/psutil). "
        "'acao': portas_escuta (o que este PC expoe) | conexoes (conexoes "
        "ativas + processos) | firewall (estado do Firewall do Windows)."
    )
    risk = Risk.SAFE
    parameters = {
        "type": "object",
        "properties": {"acao": {**_STR}},
        "required": ["acao"],
        "additionalProperties": False,
    }

    async def execute(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        import asyncio

        from jarvis import netsec

        acao = str(args.get("acao", "")).strip().lower()
        action_id = _LOCAL.get(acao)
        if action_id is None:
            return ToolResult.failure(
                f"acao invalida: {acao!r}. Use: {', '.join(_LOCAL)}."
            )
        report = await asyncio.to_thread(netsec.run_action, action_id, {})
        return ToolResult(
            ok=True,
            content=report[: ctx.config.max_output_chars],
            display=f"inspecao {acao}",
        )
