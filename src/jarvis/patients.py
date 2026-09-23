"""Setor Saúde — lógica de pacientes, prontuário e apoio à decisão clínica.

O construtor de contexto e a análise estruturada são adaptados do módulo
`ai-clinical` do sistema PROMEDIS (D:\\Projetos\\clinica): a IA recebe o
histórico completo do paciente + o registro em questão e devolve um JSON com
nível de risco, alertas, CID sugeridos, interações, diferenciais e condutas —
sempre como APOIO, nunca decisão final.
"""

from __future__ import annotations

import json
import re
from datetime import date
from typing import Any

from jarvis import medknow

RECORD_KINDS: tuple[tuple[str, str], ...] = (
    ("laudo", "Laudo"),
    ("exame", "Exame / resultado"),
    ("consulta", "Consulta"),
    ("evolucao", "Evolução"),
    ("prescricao", "Prescrição"),
    ("nota", "Nota"),
)
_KIND_LABEL = dict(RECORD_KINDS)

# campos de sinais vitais (chave -> rótulo, unidade)
VITALS: tuple[tuple[str, str, str], ...] = (
    ("pa", "Pressão arterial", "mmHg"),
    ("fc", "FC", "bpm"),
    ("fr", "FR", "irpm"),
    ("temp", "Temperatura", "°C"),
    ("spo2", "SpO₂", "%"),
    ("peso", "Peso", "kg"),
    ("altura", "Altura", "cm"),
    ("glicemia", "Glicemia", "mg/dL"),
    ("dor", "Dor (0-10)", ""),
)


def kind_label(kind: str) -> str:
    return _KIND_LABEL.get((kind or "").strip(), (kind or "nota").capitalize())


def age_from(birthdate: str, *, today: date | None = None) -> int | None:
    b = _parse_date(birthdate)
    if b is None:
        return None
    ref = today or date.today()
    years = ref.year - b.year - ((ref.month, ref.day) < (b.month, b.day))
    return years if 0 <= years < 140 else None


def _parse_date(text: str) -> date | None:
    text = (text or "").strip()
    for sep, order in (("-", "ymd"), ("/", "dmy")):
        if sep in text:
            parts = text.split(sep)
            if len(parts) != 3 or not all(p.isdigit() for p in parts):
                return None
            try:
                y, m, d = (
                    (int(parts[0]), int(parts[1]), int(parts[2])) if order == "ymd"
                    else (int(parts[2]), int(parts[1]), int(parts[0]))
                )
                return date(y, m, d)
            except ValueError:
                return None
    return None


def _med_list(patient: dict[str, Any]) -> list[str]:
    raw = (patient.get("medications") or "").strip()
    if not raw:
        return []
    return [p.strip() for p in re.split(r"[,\n;]+", raw) if p.strip()]


def format_vitals(vitals_json: str) -> str:
    try:
        v = json.loads(vitals_json) if vitals_json else {}
    except (json.JSONDecodeError, TypeError):
        return ""
    if not isinstance(v, dict):
        return ""
    parts = []
    for key, rotulo, unidade in VITALS:
        val = str(v.get(key, "") or "").strip()
        if val:
            parts.append(f"{rotulo} {val}{(' ' + unidade) if unidade else ''}")
    return ", ".join(parts)


# ─────────────────────────────────────────────── contexto clínico completo
def clinical_context(
    patient: dict[str, Any],
    history_records: list[dict[str, Any]],
    focus_record: dict[str, Any] | None,
    attachment_texts: list[str] | None = None,
    *,
    today: date | None = None,
) -> str:
    lines: list[str] = ["## DADOS DO PACIENTE (confidencial, uso interno)"]
    age = age_from(patient.get("birthdate", ""), today=today)
    sex = {"M": "masculino", "F": "feminino"}.get(
        (patient.get("sex") or "").upper().strip(), ""
    )
    lines.append(f"- Nome: {patient.get('name') or '(sem nome)'}")
    if age is not None:
        lines.append(f"- Idade: {age} anos")
    if sex:
        lines.append(f"- Sexo: {sex}")
    for key, rot in (
        ("blood_type", "Tipo sanguíneo"),
        ("allergies", "ALERGIAS"),
        ("conditions", "Condições crônicas / comorbidades"),
        ("medications", "Medicamentos em uso"),
        ("background", "Antecedentes pessoais"),
        ("family_background", "Histórico familiar"),
        ("social_background", "Histórico social"),
        ("notes", "Observações"),
    ):
        val = (patient.get(key) or "").strip()
        if val:
            lines.append(f"- {rot}: {val}")

    # verificação local de interações entre os medicamentos do paciente
    inter = medknow.check_interactions(_med_list(patient))
    if inter:
        lines.append("\n## INTERAÇÕES DETECTADAS NA BASE LOCAL (confirmar em fonte atualizada)")
        for r in inter:
            lines.append(
                f"- [{r['gravidade'].upper()}] {r['medA']} × {r['medB']}: "
                f"{r['descricao']} ({r['mecanismo']})"
            )

    prev = [r for r in history_records if not focus_record or r.get("id") != focus_record.get("id")]
    if prev:
        lines.append(f"\n## HISTÓRICO NO PRONTUÁRIO (últimos {min(len(prev), 8)} registros)")
        for r in prev[:8]:
            when = (r.get("occurred_at") or "").strip() or "sem data"
            lines.append(f"\n### {kind_label(r.get('kind', ''))} — {r.get('title') or '(sem título)'} ({when})")
            body = (r.get("body") or "").strip()
            if body:
                lines.append(body[:800])
            vit = format_vitals(r.get("vitals", ""))
            if vit:
                lines.append(f"- Sinais vitais: {vit}")
            if (r.get("ai_summary") or "").strip():
                lines.append(f"- (análise anterior da IA: {r['ai_summary'][:300]})")

    if focus_record:
        lines.append("\n## REGISTRO EM ANÁLISE AGORA")
        when = (focus_record.get("occurred_at") or "").strip() or "sem data"
        lines.append(f"- Tipo: {kind_label(focus_record.get('kind', ''))} — "
                     f"{focus_record.get('title') or '(sem título)'} ({when})")
        vit = format_vitals(focus_record.get("vitals", ""))
        if vit:
            lines.append(f"- Sinais vitais: {vit}")
        body = (focus_record.get("body") or "").strip()
        if body:
            lines.append(f"- Texto digitado:\n{body}")
        anexos = "\n\n".join(t.strip() for t in (attachment_texts or []) if t and t.strip())
        if anexos:
            lines.append(f"- Conteúdo dos anexos (extraído automaticamente):\n{anexos[:10000]}")

    return "\n".join(lines)


_SYSTEM = (
    "Você é um assistente de APOIO à decisão clínica, experiente, no contexto "
    "do sistema de saúde brasileiro. Analise os dados e responda de forma "
    "estruturada, objetiva e em português.\n"
    "REGRAS OBRIGATÓRIAS:\n"
    "- Você é APOIO — não substitui o julgamento do médico nem fala com o paciente.\n"
    "- Destaque SEMPRE alergias e interações medicamentosas como alertas críticos.\n"
    "- Use códigos CID-10 oficiais (ex.: E11.9, J06.9, I10).\n"
    "- Para interações, seja específico sobre mecanismo e gravidade.\n"
    "- Não invente valores, doses ou referências. Se faltar dado, diga.\n"
    "- Responda SOMENTE com JSON válido no formato pedido, sem texto fora do JSON."
)

_JSON_SHAPE = """Responda com JSON exatamente neste formato:
{
  "nivel_risco": "baixo|moderado|alto|critico",
  "alertas": ["alerta crítico (alergia, interação, urgência)", "..."],
  "resumo": "resumo clínico do registro em 2-4 frases",
  "achados": ["achado/valor alterado com a magnitude", "o que está normal e tranquiliza"],
  "cid_sugeridos": [{"code": "X00.0", "description": "nome CID-10", "justificativa": "razão clínica", "confianca": "alta|media|baixa"}],
  "diagnosticos_diferenciais": ["hipótese + breve justificativa"],
  "interacoes_medicamentosas": [{"substancias": ["A", "B"], "gravidade": "leve|moderada|grave|contraindicado", "descricao": "mecanismo e risco"}],
  "conduta_sugerida": ["opção de conduta para o profissional CONSIDERAR"],
  "exames_recomendados": ["exame complementar + justificativa"],
  "perguntar_examinar": ["dado de anamnese/exame físico que ainda falta"],
  "observacoes": "pontos de atenção adicionais"
}
Use [] ou "" quando não houver itens. nivel_risco: "critico" = risco de vida imediato (sepse, IAM, AVC, anafilaxia); "alto" = grave, intervenção urgente; "moderado" = requer atenção; "baixo" = estável."""


def analyze_record_prompt(
    patient: dict[str, Any],
    history_records: list[dict[str, Any]],
    focus_record: dict[str, Any],
    attachment_texts: list[str],
    doctor_question: str = "",
    *,
    today: date | None = None,
) -> tuple[str, str]:
    """Retorna (system_prompt, user_message) para a análise estruturada."""
    ctx = clinical_context(patient, history_records, focus_record, attachment_texts, today=today)
    q = f"\n\n## PERGUNTA DO PROFISSIONAL\n{doctor_question.strip()}" if doctor_question.strip() else ""
    return _SYSTEM, f"{ctx}{q}\n\n{_JSON_SHAPE}"


_RISK = {
    "critico": ("⛔ CRÍTICO", "risco de vida imediato"),
    "alto": ("🔴 ALTO", "grave, intervenção urgente"),
    "moderado": ("🟠 MODERADO", "requer atenção"),
    "baixo": ("🟢 BAIXO", "quadro estável"),
}


def parse_analysis(raw: str) -> dict[str, Any]:
    raw = (raw or "").strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-zA-Z]*\n?|```$", "", raw).strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if not m:
            return {"observacoes": raw}
        try:
            data = json.loads(m.group(0))
        except json.JSONDecodeError:
            return {"observacoes": raw}
    return data if isinstance(data, dict) else {"observacoes": raw}


def format_analysis(a: dict[str, Any]) -> tuple[str, str, str]:
    """(texto completo p/ chat, resumo curto, alertas) a partir do JSON."""
    if not isinstance(a, dict) or (set(a) <= {"observacoes"} and not a.get("nivel_risco")):
        txt = str(a.get("observacoes", "")).strip() if isinstance(a, dict) else str(a)
        return txt, txt[:400], ""

    L: list[str] = []
    risk = str(a.get("nivel_risco", "")).lower().strip()
    if risk in _RISK:
        lbl, desc = _RISK[risk]
        L.append(f"**NÍVEL DE RISCO: {lbl}** ({desc})")

    alertas = [x for x in (a.get("alertas") or []) if str(x).strip()]
    if alertas:
        L.append("\n**⚠️ ALERTAS**")
        L.extend(f"- {x}" for x in alertas)

    if (a.get("resumo") or "").strip():
        L.append(f"\n**Resumo**\n{a['resumo'].strip()}")

    def bullets(title: str, items: list) -> None:
        clean = [x for x in (items or []) if str(x).strip()]
        if clean:
            L.append(f"\n**{title}**")
            L.extend(f"- {x}" for x in clean)

    bullets("Achados", a.get("achados"))

    cids = a.get("cid_sugeridos") or []
    if cids:
        L.append("\n**CID-10 sugeridos (para considerar)**")
        for c in cids:
            if isinstance(c, dict):
                L.append(
                    f"- {c.get('code', '?')} — {c.get('description', '')} "
                    f"({c.get('confianca', '?')}): {c.get('justificativa', '')}"
                )

    bullets("Diagnósticos diferenciais", a.get("diagnosticos_diferenciais"))

    inter = a.get("interacoes_medicamentosas") or []
    if inter:
        L.append("\n**Interações medicamentosas**")
        for it in inter:
            if isinstance(it, dict):
                subs = ", ".join(it.get("substancias", []) or [])
                L.append(f"- [{it.get('gravidade', '?').upper()}] {subs}: {it.get('descricao', '')}")

    bullets("Conduta sugerida (opções para o profissional)", a.get("conduta_sugerida"))
    bullets("Exames recomendados", a.get("exames_recomendados"))
    bullets("Ainda falta perguntar / examinar", a.get("perguntar_examinar"))

    if (a.get("observacoes") or "").strip():
        L.append(f"\n**Observações**\n{a['observacoes'].strip()}")

    L.append("\n_Rascunho de apoio — confirme com avaliação clínica e diretriz atualizada antes de qualquer conduta._")

    full = "\n".join(L)
    resumo = (a.get("resumo") or "").strip() or (alertas[0] if alertas else full[:300])
    flags = " · ".join(alertas)
    return full, resumo, flags


# --- compat: usada por versões anteriores / testes antigos --------------
def patient_context(patient: dict[str, Any], *, today: date | None = None) -> str:
    return clinical_context(patient, [], None, None, today=today)


def split_ai_output(text: str) -> tuple[str, str]:
    a = parse_analysis(text)
    full, resumo, flags = format_analysis(a)
    return resumo or full, flags
