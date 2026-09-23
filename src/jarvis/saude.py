"""Ações rápidas do painel "Saúde" (setor Saúde no chat).

Cada botão pede os dados e monta uma instrução para o agente. Nada roda aqui:
o agente responde como APOIO ao profissional — tudo é rascunho para revisão,
nunca diagnóstico/prescrição final nem fala direta com o paciente.
"""

from __future__ import annotations

from dataclasses import dataclass

_FRAME = (
    "[Apoio ao profissional de saúde — a resposta é rascunho para o "
    "profissional revisar e assumir; não é diagnóstico nem prescrição "
    "final] "
)


@dataclass(frozen=True, slots=True)
class HealthField:
    key: str
    label: str
    placeholder: str = ""
    optional: bool = False
    default: str = ""
    long: bool = False


@dataclass(frozen=True, slots=True)
class HealthAction:
    id: str
    label: str
    icon: str
    category: str
    description: str
    prompt: str
    fields: tuple[HealthField, ...] = ()

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
                    "long": f.long,
                }
                for f in self.fields
            ],
        }


ACTIONS: tuple[HealthAction, ...] = (
    HealthAction(
        "resumir_exame", "Resumir exame / laudo", "\U0001F9EA", "Exames",
        "Resume um resultado e sinaliza o que está fora da faixa.",
        _FRAME + "Resuma este exame/laudo, destaque em tópicos os achados "
        "relevantes e marque claramente os valores fora da faixa de "
        "referência e a magnitude do desvio. Ao final, liste o que o "
        "profissional deve correlacionar clinicamente. Não feche diagnóstico.\n\n"
        "RESULTADO:\n{conteudo}",
        (HealthField("conteudo", "Resultado do exame / laudo",
                     "cole o texto do exame", long=True),),
    ),
    HealthAction(
        "interacoes", "Interações medicamentosas", "\U0001F48A", "Medicação",
        "Checa interações e cuidados entre medicamentos.",
        _FRAME + "Para a lista de medicamentos abaixo, aponte interações "
        "relevantes (par a par), o mecanismo, a gravidade e a conduta "
        "sugerida (ajuste, espaçamento, monitorização). Considere também "
        "duplicidade terapêutica. Cite quando a informação depende de dose ou "
        "função renal/hepática. Mande confirmar em base de dados atualizada.\n\n"
        "MEDICAMENTOS: {medicamentos}\n"
        "CONTEXTO (opcional): {contexto}",
        (
            HealthField("medicamentos", "Medicamentos em uso",
                        "ex.: varfarina, amiodarona, omeprazol"),
            HealthField("contexto", "Contexto do paciente",
                        "idade, função renal, comorbidades", optional=True),
        ),
    ),
    HealthAction(
        "hipoteses", "Hipóteses diagnósticas", "\U0001F50D", "Raciocínio",
        "Levanta diferenciais para o profissional considerar.",
        _FRAME + "A partir do quadro clínico abaixo, liste hipóteses "
        "diagnósticas e diagnósticos diferenciais para o profissional "
        "CONSIDERAR, da mais para a menos provável, com o racional de cada uma "
        "e que dado (anamnese, exame físico, exame complementar) confirma ou "
        "afasta. Sinalize red flags e o que não pode passar batido. Termine "
        "lembrando que a decisão exige avaliação clínica presencial.\n\n"
        "QUADRO CLÍNICO:\n{quadro}",
        (HealthField("quadro", "Quadro clínico",
                     "queixa, tempo, sintomas, antecedentes, exame físico",
                     long=True),),
    ),
    HealthAction(
        "evolucao", "Rascunho de evolução (SOAP)", "\U0001F4DD", "Registro",
        "Organiza a consulta no formato SOAP para revisão.",
        _FRAME + "Organize as informações da consulta abaixo em uma evolução "
        "no formato SOAP (Subjetivo, Objetivo, Avaliação, Plano), em "
        "português claro e impessoal. Não acrescente dados que não foram "
        "informados. Deixe entre colchetes o que faltar preencher.\n\n"
        "DADOS DA CONSULTA:\n{dados}",
        (HealthField("dados", "Dados da consulta",
                     "queixa, achados, condutas, prescrição, retorno",
                     long=True),),
    ),
    HealthAction(
        "orientacao_paciente", "Orientações para o paciente", "\U0001F5E3", "Comunicação",
        "Escreve orientações em linguagem simples para revisão.",
        _FRAME + "Escreva orientações para o paciente em linguagem simples, "
        "acolhedora e sem jargão, sobre a condição e o plano abaixo. Inclua: o "
        "que é, o que fazer em casa, o que evitar, sinais de alerta para "
        "voltar ao serviço, e quando é o retorno. O texto será REVISADO e "
        "entregue pelo profissional — não fale como se fosse o médico.\n\n"
        "CONDIÇÃO E PLANO: {plano}",
        (HealthField("plano", "Condição e plano",
                     "diagnóstico/hipótese, medicação, cuidados, retorno",
                     long=True),),
    ),
    HealthAction(
        "traduzir_laudo", "Traduzir laudo", "\U0001F524", "Comunicação",
        "Converte jargão do laudo em linguagem acessível.",
        _FRAME + "Traduza o laudo abaixo para linguagem que um leigo entende, "
        "termo por termo quando útil, sem alarmismo e sem dar conduta. Ao "
        "final, diga em uma frase o que costuma significar, lembrando que só o "
        "profissional que acompanha o caso pode interpretar de fato.\n\n"
        "LAUDO:\n{conteudo}",
        (HealthField("conteudo", "Texto do laudo", "cole o laudo", long=True),),
    ),
    HealthAction(
        "calculo", "Calculadora clínica", "\U0001F9EE", "Cálculo",
        "IMC, clearance, superfície corporal, dose pediátrica.",
        _FRAME + "Calcule {qual} com os dados abaixo. Mostre a FÓRMULA usada, "
        "a substituição dos valores, o resultado com unidade e a "
        "interpretação/faixa. Se faltar algum dado, diga qual.\n\n"
        "DADOS: {dados}",
        (
            HealthField("qual", "O que calcular",
                        "IMC / clearance de creatinina / superfície corporal / dose pediátrica"),
            HealthField("dados", "Dados",
                        "ex.: 72 kg, 1,70 m, 54 anos, creatinina 1,1"),
        ),
    ),
    HealthAction(
        "cid", "Checar CID-10", "\U0001F5C2", "Registro",
        "Sugere códigos CID-10 prováveis para a condição.",
        _FRAME + "Para a condição/diagnóstico abaixo, sugira os códigos CID-10 "
        "mais prováveis com a descrição oficial de cada um, e aponte "
        "diferenças entre códigos próximos. Lembre de conferir na tabela "
        "oficial vigente.\n\n"
        "CONDIÇÃO: {condicao}",
        (HealthField("condicao", "Condição / diagnóstico",
                     "ex.: pneumonia adquirida na comunidade"),),
    ),
    HealthAction(
        "preparo_exame", "Preparo de exame", "\U0001F4CB", "Exames",
        "Orientações de preparo para um exame.",
        _FRAME + "Descreva o preparo padrão para o exame abaixo: jejum, "
        "suspensão ou manutenção de medicações, hidratação, documentos, "
        "duração e cuidados após. Diga que o preparo pode variar por "
        "serviço/equipamento e deve ser confirmado no local.\n\n"
        "EXAME: {exame}",
        (HealthField("exame", "Nome do exame",
                     "ex.: ressonância de crânio com contraste"),),
    ),
    HealthAction(
        "conduta", "Resumo de conduta / diretriz", "\U0001F4D6", "Raciocínio",
        "Resumo de manejo baseado em diretrizes (conferir a fonte).",
        _FRAME + "Resuma a conduta atual para a condição abaixo: abordagem "
        "inicial, exames, tratamento de primeira linha e alternativas, "
        "critérios de internação/encaminhamento e seguimento. Cite quais "
        "diretrizes/sociedades embasam e alerte que podem ter sido "
        "atualizadas — o profissional deve conferir a versão vigente.\n\n"
        "CONDIÇÃO: {condicao}\n"
        "POPULAÇÃO/CONTEXTO (opcional): {contexto}",
        (
            HealthField("condicao", "Condição",
                        "ex.: crise hipertensiva, ITU não complicada"),
            HealthField("contexto", "População / contexto",
                        "adulto, gestante, pediatria, atenção primária",
                        optional=True),
        ),
    ),
)

_BY_ID = {a.id: a for a in ACTIONS}


def health_actions() -> list[dict[str, object]]:
    return [a.as_dict() for a in ACTIONS]


def get_action(action_id: str) -> HealthAction | None:
    return _BY_ID.get((action_id or "").strip())


def build_prompt(action_id: str, params: dict[str, str] | None) -> str:
    action = get_action(action_id)
    if action is None:
        raise KeyError(f"acao de saude desconhecida: {action_id!r}")
    values = {k: str(v).strip() for k, v in (params or {}).items()}
    for f in action.fields:
        if not values.get(f.key):
            if f.optional:
                values[f.key] = f.default or "não informado"
            else:
                raise ValueError(f"Preencha o campo '{f.label}'.")
    try:
        return action.prompt.format(**values)
    except KeyError as exc:
        raise ValueError(f"Falta a informação {exc}.") from exc
