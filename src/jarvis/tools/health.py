from __future__ import annotations

from typing import TYPE_CHECKING, Any

from jarvis import medknow
from jarvis.tools.base import Tool, ToolResult

if TYPE_CHECKING:
    from jarvis.tools.context import ToolContext


class InteracoesMedicamentosas(Tool):
    """Verifica interações entre medicamentos numa base clínica local (offline)."""

    name = "interacoes_medicamentosas"
    description = (
        "Verifica, numa base local curada (~50 pares clínicos relevantes), "
        "interações medicamentosas entre uma lista de fármacos. Use no setor "
        "Saúde. Retorna gravidade, risco e mecanismo. Não substitui base "
        "farmacológica atualizada."
    )
    parameters = {
        "type": "object",
        "properties": {
            "medicamentos": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Nomes dos medicamentos / princípios ativos.",
            }
        },
        "required": ["medicamentos"],
    }

    async def execute(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        meds = [str(m).strip() for m in (args.get("medicamentos") or []) if str(m).strip()]
        if len(meds) < 2:
            return ToolResult.failure("Informe pelo menos 2 medicamentos.")
        rows = medknow.check_interactions(meds)
        return ToolResult(
            ok=True,
            content=medknow.format_interactions(rows),
            display=f"{len(rows)} interação(ões)",
        )


class BuscarCID(Tool):
    """Busca códigos CID-10 (DATASUS) numa tabela local offline."""

    name = "buscar_cid"
    description = (
        "Consulta a CID-10 oficial (DATASUS, ~10 mil códigos) offline: por "
        "código (ex.: 'E11', 'J45.0') ou por texto ('pneumonia', 'diabetes "
        "tipo 2'). Retorna código + descrição oficial."
    )
    parameters = {
        "type": "object",
        "properties": {
            "consulta": {"type": "string", "description": "Código ou termo a buscar."}
        },
        "required": ["consulta"],
    }

    async def execute(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        q = str(args.get("consulta", "")).strip()
        res = medknow.cid_search(q, limit=20)
        if not res:
            return ToolResult(ok=True, content=f"Nada encontrado para '{q}' na CID-10.", display="0")
        body = "\n".join(f"{r['code']}  {r['description']}" for r in res)
        return ToolResult(ok=True, content=body, display=f"{len(res)} códigos")


class CalculadoraClinica(Tool):
    """Escores e doses clínicas: IMC, clearance de creatinina, superfície corporal, dose pediátrica."""

    name = "calculadora_clinica"
    description = (
        "Calcula, mostrando a fórmula: IMC (peso, altura), clearance de "
        "creatinina Cockcroft-Gault (idade, peso, creatinina, sexo), "
        "superfície corporal (peso, altura), dose pediátrica (dose/kg, peso, "
        "dose máxima opcional)."
    )
    parameters = {
        "type": "object",
        "properties": {
            "calculo": {
                "type": "string",
                "enum": ["imc", "clearance", "superficie_corporal", "dose_pediatrica"],
            },
            "peso_kg": {"type": "number"},
            "altura_cm": {"type": "number"},
            "idade": {"type": "integer"},
            "creatinina": {"type": "number"},
            "sexo_feminino": {"type": "boolean"},
            "dose_por_kg": {"type": "number"},
            "dose_maxima": {"type": "number"},
        },
        "required": ["calculo"],
    }

    async def execute(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        calc = str(args.get("calculo", "")).strip().lower()
        try:
            if calc == "imc":
                r = medknow.bmi(float(args["peso_kg"]), float(args["altura_cm"]))
            elif calc == "clearance":
                r = medknow.cockcroft_gault(
                    int(args["idade"]), float(args["peso_kg"]),
                    float(args["creatinina"]), bool(args.get("sexo_feminino")),
                )
            elif calc == "superficie_corporal":
                r = medknow.bsa(float(args["peso_kg"]), float(args["altura_cm"]))
            elif calc == "dose_pediatrica":
                r = medknow.pediatric_dose(
                    float(args["dose_por_kg"]), float(args["peso_kg"]),
                    float(args["dose_maxima"]) if args.get("dose_maxima") else None,
                )
            else:
                return ToolResult.failure(f"Cálculo '{calc}' não reconhecido.")
        except (KeyError, TypeError, ValueError) as exc:
            return ToolResult.failure(f"Faltam dados ou valor inválido: {exc}")
        cat = f"  ({r['categoria']})" if r.get("categoria") else ""
        return ToolResult(
            ok=True,
            content=f"{r['valor']} {r['unidade']}{cat}\nFórmula: {r['formula']}",
            display=f"{r['valor']} {r['unidade']}",
        )
