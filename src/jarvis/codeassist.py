"""Ações rápidas do painel "Assistente de Código" (perfil Desenvolvimento).

Cada botão monta uma instrução em linguagem natural e manda pro agente, que
já tem as ferramentas locais `analisar_repositorio`, `diagnosticar_bug`,
`editar_codigo_local`, `executar_testes_locais` e `interpretador_codigo`.
Nada roda aqui direto: o agente lê o repo, propõe e (com confirmação) edita.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CodeField:
    key: str
    label: str
    placeholder: str = ""
    optional: bool = False
    default: str = ""


@dataclass(frozen=True, slots=True)
class CodeAction:
    id: str
    label: str
    icon: str
    category: str
    description: str
    prompt: str
    fields: tuple[CodeField, ...] = ()

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "label": self.label,
            "icon": self.icon,
            "category": self.category,
            "description": self.description,
            "fields": [
                {
                    "key": f.key,
                    "label": f.label,
                    "placeholder": f.placeholder,
                    "optional": f.optional,
                    "default": f.default,
                }
                for f in self.fields
            ],
        }


_PATH = CodeField(
    "caminho", "Pasta do projeto",
    "deixe em branco para usar a pasta de trabalho", optional=True, default="",
)

ACTIONS: tuple[CodeAction, ...] = (
    CodeAction(
        "analisar", "Analisar repositório", "\U0001F50D", "Visão geral",
        "Mapeia linguagens, dependências e arquitetura do projeto.",
        "Use analisar_repositorio em {caminho} e me dê um panorama: linguagens, "
        "frameworks, como o projeto está organizado, pontos de entrada e o que "
        "chama atenção (dívidas técnicas, dependências desatualizadas).",
        (_PATH,),
    ),
    CodeAction(
        "diagnosticar", "Diagnosticar bug", "\U0001F41E", "Correção",
        "Investiga um erro e aponta a causa provável.",
        "Tenho este problema no projeto em {caminho}:\n\n{descricao}\n\n"
        "Use diagnosticar_bug e leitura de arquivos para achar a causa raiz. "
        "Explique o porquê e proponha a correção (sem editar ainda).",
        (
            _PATH,
            CodeField("descricao", "O que está acontecendo",
                      "mensagem de erro, comportamento errado, passos pra reproduzir"),
        ),
    ),
    CodeAction(
        "revisar", "Revisar mudanças", "\U0001F9EA", "Qualidade",
        "Revisa o código recente em busca de bugs e melhorias.",
        "Revise o código do projeto em {caminho}"
        "{foco}. Liste problemas de correção, segurança e clareza em ordem de "
        "prioridade (ALTO / MÉDIO / BAIXO) e sugira como resolver. Não edite ainda.",
        (
            _PATH,
            CodeField("foco", "Focar em algo? (opcional)",
                      "ex.: só a pasta src/auth, ou o último commit",
                      optional=True, default=""),
        ),
    ),
    CodeAction(
        "melhorar", "Sugerir melhorias", "\u2728", "Qualidade",
        "Aponta refatorações e boas práticas aplicáveis.",
        "Analise o projeto em {caminho} e sugira melhorias concretas: "
        "refatorações, simplificações, padrões que faltam, cobertura de testes. "
        "Priorize as de maior impacto e menor risco. Só liste — não edite.",
        (_PATH,),
    ),
    CodeAction(
        "implementar", "Implementar / editar", "\u270F\uFE0F", "Correção",
        "Pede uma mudança e deixa o agente editar os arquivos.",
        "No projeto em {caminho}, faça a seguinte mudança:\n\n{tarefa}\n\n"
        "Leia o que for necessário, use editar_codigo_local para aplicar e me "
        "mostre um resumo do que mudou em cada arquivo. Peça confirmação antes "
        "de cada escrita.",
        (
            _PATH,
            CodeField("tarefa", "O que fazer",
                      "descreva a alteração, feature ou correção desejada"),
        ),
    ),
    CodeAction(
        "testes", "Rodar os testes", "\u2705", "Qualidade",
        "Executa a suíte de testes e resume as falhas.",
        "Rode os testes do projeto em {caminho} com executar_testes_locais"
        "{alvo}. Resuma o resultado, e para cada falha explique a causa provável "
        "e como corrigir.",
        (
            _PATH,
            CodeField("alvo", "Teste específico? (opcional)",
                      "ex.: tests/test_auth.py", optional=True, default=""),
        ),
    ),
    CodeAction(
        "explicar", "Explicar um trecho", "\U0001F4D6", "Visão geral",
        "Explica o que um arquivo ou função faz.",
        "No projeto em {caminho}, leia {alvo} e me explique em português, "
        "passo a passo, o que faz, como se encaixa no resto e onde pode quebrar.",
        (
            _PATH,
            CodeField("alvo", "Arquivo ou função",
                      "ex.: src/jarvis/router.py, ou a função parse_config"),
        ),
    ),
    CodeAction(
        "dependencias", "Checar dependências", "\U0001F4E6", "Visão geral",
        "Lista pacotes desatualizados ou com risco.",
        "No projeto em {caminho}, examine os arquivos de dependência "
        "(requirements.txt, pyproject.toml, package.json...) e diga quais "
        "pacotes estão desatualizados, sem uso ou com alerta de segurança "
        "conhecido. Não instale nada.",
        (_PATH,),
    ),
    CodeAction(
        "snippet", "Rodar um código", "\U0001F5A5", "Visão geral",
        "Executa um trecho rápido com o interpretador local.",
        "Rode este código com interpretador_codigo e me mostre a saída:\n\n"
        "```{linguagem}\n{codigo}\n```",
        (
            CodeField("codigo", "Código", "cole o trecho a executar"),
            CodeField("linguagem", "Linguagem", "python / bash",
                      optional=True, default="python"),
        ),
    ),
)

_BY_ID = {a.id: a for a in ACTIONS}


def code_actions() -> list[dict[str, object]]:
    return [a.as_dict() for a in ACTIONS]


def get_action(action_id: str) -> CodeAction | None:
    return _BY_ID.get((action_id or "").strip())


def build_prompt(action_id: str, params: dict[str, str] | None) -> str:
    action = get_action(action_id)
    if action is None:
        raise KeyError(f"acao de codigo desconhecida: {action_id!r}")
    values = {key: str(value).strip() for key, value in (params or {}).items()}
    for f in action.fields:
        if not values.get(f.key):
            if f.optional:
                values[f.key] = f.default
            else:
                raise ValueError(f"Preencha o campo '{f.label}'.")

    caminho = values.get("caminho", "").strip()
    values["caminho"] = caminho or "a pasta de trabalho atual"

    # campos opcionais que viram frases quando preenchidos
    foco = values.get("foco", "").strip()
    values["foco"] = f", focando em: {foco}" if foco else ""
    alvo = values.get("alvo", "").strip()
    if "alvo" in {f.key for f in action.fields if f.optional}:
        values["alvo"] = f" ({alvo})" if alvo else ""

    try:
        return action.prompt.format(**values)
    except KeyError as exc:
        raise ValueError(f"Falta a informacao {exc}.") from exc
