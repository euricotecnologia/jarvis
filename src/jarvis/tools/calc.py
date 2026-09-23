from __future__ import annotations

import ast
import math
import operator
from typing import Any

from jarvis.tools.base import Risk, Tool, ToolResult
from jarvis.tools.context import ToolContext

_BINOPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARYOPS = {ast.UAdd: operator.pos, ast.USub: operator.neg}
_NAMES: dict[str, float] = {"pi": math.pi, "e": math.e, "tau": math.tau}
_FUNCS = {
    "abs": abs, "round": round, "min": min, "max": max,
    "sqrt": math.sqrt, "log": math.log, "ln": math.log, "log10": math.log10,
    "log2": math.log2, "exp": math.exp, "sin": math.sin, "cos": math.cos,
    "tan": math.tan, "asin": math.asin, "acos": math.acos, "atan": math.atan,
    "ceil": math.ceil, "floor": math.floor, "factorial": math.factorial,
}


def _eval(node: ast.AST) -> Any:
    if isinstance(node, ast.Expression):
        return _eval(node.body)
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError("So números são permitidos.")
    if isinstance(node, ast.BinOp) and type(node.op) in _BINOPS:
        return _BINOPS[type(node.op)](_eval(node.left), _eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARYOPS:
        return _UNARYOPS[type(node.op)](_eval(node.operand))
    if isinstance(node, ast.Name) and node.id in _NAMES:
        return _NAMES[node.id]
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        func = _FUNCS.get(node.func.id)
        if func is None:
            raise ValueError(f"Função não permitida: {node.func.id}")
        return func(*[_eval(arg) for arg in node.args])
    raise ValueError("Expressão não suportada.")


class Calculadora(Tool):
    name = "calculadora"
    description = (
        "Avalia uma expressão matematica com precisão (aritmetica, potencias, "
        "sqrt, log, sin/cos/tan, pi, e...). Ex.: '(1234*89)/7 + sqrt(2)'."
    )
    risk = Risk.SAFE
    parameters = {
        "type": "object",
        "properties": {"expressao": {"type": "string", "description": "A conta."}},
        "required": ["expressao"],
        "additionalProperties": False,
    }

    async def execute(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        expression = str(args.get("expressao", "")).strip()
        if not expression:
            return ToolResult.failure("Informe a expressão.")
        try:
            tree = ast.parse(expression, mode="eval")
            value = _eval(tree)
        except (ValueError, SyntaxError, TypeError, OverflowError, ZeroDivisionError) as exc:
            return ToolResult.failure(f"Não consegui calcular: {exc}")
        return ToolResult(
            ok=True, content=f"{expression} = {value}", display=f"= {value}"
        )
