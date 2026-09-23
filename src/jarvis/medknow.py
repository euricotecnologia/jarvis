"""Base de conhecimento clínica local do setor Saúde.

Portado do sistema PROMEDIS (D:\\Projetos\\clinica):
- interações medicamentosas curadas (verificação por par, offline);
- CID-10 completo (DATASUS V2007, ~10.2k códigos) para busca offline;
- calculadoras clínicas (IMC, clearance de creatinina, superfície corporal,
  dose pediátrica).

Nada aqui dá conduta: são ferramentas de consulta para o profissional.
"""

from __future__ import annotations

import functools
import gzip
import math
import re
import unicodedata
from pathlib import Path

_DATA = Path(__file__).resolve().parent / "data"

# ─────────────────────────────────────────────── interações medicamentosas
# (substância A, substância B, gravidade, risco, mecanismo)
_SEV_ORDER = {"contraindicado": 0, "grave": 1, "moderada": 2, "leve": 3}

DRUG_INTERACTIONS: tuple[tuple[str, str, str, str, str], ...] = (
    ("Warfarina", "AAS", "grave", "Risco aumentado de sangramento grave.", "Inibição plaquetária + anticoagulação sinérgica."),
    ("Warfarina", "Ibuprofeno", "grave", "Risco aumentado de sangramento grave.", "AINEs inibem COX-1 e deslocam a varfarina de proteínas plasmáticas."),
    ("Warfarina", "Naproxeno", "grave", "Risco aumentado de sangramento grave.", "AINEs inibem COX-1 e deslocam a varfarina de proteínas plasmáticas."),
    ("Warfarina", "Diclofenaco", "grave", "Risco aumentado de sangramento grave.", "AINEs inibem COX-1 e deslocam a varfarina de proteínas plasmáticas."),
    ("Warfarina", "Fluconazol", "grave", "Aumento significativo do efeito anticoagulante; risco de sangramento.", "Fluconazol inibe CYP2C9, reduzindo o metabolismo da varfarina."),
    ("Warfarina", "Amiodarona", "grave", "Potencialização do efeito anticoagulante; risco de sangramento grave.", "Amiodarona inibe CYP2C9 e CYP3A4."),
    ("Warfarina", "Rifampicina", "grave", "Redução drástica do efeito anticoagulante; risco de trombose.", "Rifampicina é potente indutor de CYP2C9 e CYP3A4."),
    ("Warfarina", "Fenitoína", "moderada", "Interação complexa: pode aumentar ou reduzir o efeito anticoagulante.", "Fenitoína inicialmente inibe e depois induz a CYP2C9."),
    ("Fluoxetina", "Tramadol", "grave", "Risco de síndrome serotoninérgica: agitação, hipertermia, convulsão.", "Somatória de efeito serotoninérgico central."),
    ("Sertralina", "Tramadol", "grave", "Risco de síndrome serotoninérgica: agitação, hipertermia, convulsão.", "Somatória de efeito serotoninérgico central."),
    ("Paroxetina", "Tramadol", "grave", "Risco de síndrome serotoninérgica e redução da analgesia do tramadol.", "Paroxetina inibe CYP2D6, bloqueando a ativação do tramadol."),
    ("Fluoxetina", "IMAO", "contraindicado", "Síndrome serotoninérgica grave com risco de morte. USO CONTRAINDICADO.", "Inibição da MAO + ISRS causa acúmulo massivo de serotonina."),
    ("Sertralina", "IMAO", "contraindicado", "Síndrome serotoninérgica grave com risco de morte. USO CONTRAINDICADO.", "Inibição da MAO + ISRS causa acúmulo massivo de serotonina."),
    ("Venlafaxina", "IMAO", "contraindicado", "Síndrome serotoninérgica grave com risco de morte. USO CONTRAINDICADO.", "Inibição da MAO + IRSN causa acúmulo massivo de serotonina."),
    ("Tramadol", "IMAO", "contraindicado", "Risco de síndrome serotoninérgica e crise hipertensiva graves. CONTRAINDICADO.", "Tramadol inibe a recaptação de serotonina; IMAO inibe sua degradação."),
    ("Digoxina", "Amiodarona", "grave", "Aumento dos níveis de digoxina; risco de toxicidade digitálica.", "Amiodarona inibe a glicoproteína-P e reduz o clearance renal da digoxina."),
    ("Digoxina", "Claritromicina", "grave", "Toxicidade digitálica: arritmias, náuseas, distúrbios visuais.", "Claritromicina inibe CYP3A4 e glicoproteína-P."),
    ("Digoxina", "Eritromicina", "moderada", "Aumento dos níveis de digoxina; monitorar toxicidade.", "Inibição da flora intestinal que metaboliza a digoxina."),
    ("Sinvastatina", "Claritromicina", "grave", "Risco de miopatia e rabdomiólise.", "Claritromicina inibe CYP3A4, elevando a concentração de sinvastatina."),
    ("Sinvastatina", "Amiodarona", "grave", "Risco de miopatia e rabdomiólise; limitar a dose de sinvastatina.", "Amiodarona inibe CYP3A4."),
    ("Sinvastatina", "Cetoconazol", "grave", "Risco de rabdomiólise; uso concomitante contraindicado.", "Cetoconazol é potente inibidor de CYP3A4."),
    ("Atorvastatina", "Claritromicina", "moderada", "Aumento dos níveis de atorvastatina; risco de miopatia.", "Claritromicina inibe CYP3A4."),
    ("Captopril", "Espironolactona", "moderada", "Risco de hipercalemia, sobretudo na insuficiência renal.", "Ambos reduzem a excreção de potássio."),
    ("Enalapril", "Espironolactona", "moderada", "Risco de hipercalemia, sobretudo na insuficiência renal.", "IECA reduz aldosterona; espironolactona é antagonista da aldosterona."),
    ("Losartana", "Espironolactona", "moderada", "Risco de hipercalemia, sobretudo na insuficiência renal.", "BRA + antialdosterônico: dupla redução da excreção de potássio."),
    ("Morfina", "Benzodiazepínico", "grave", "Depressão respiratória grave com risco de apneia e morte.", "Sinergismo de depressão do SNC e do drive respiratório."),
    ("Tramadol", "Benzodiazepínico", "grave", "Depressão respiratória grave com risco de apneia.", "Sinergismo de depressão do SNC."),
    ("Codeína", "Benzodiazepínico", "grave", "Depressão respiratória com risco de apneia.", "Sinergismo de depressão do SNC."),
    ("Álcool", "Benzodiazepínico", "grave", "Depressão intensa do SNC; risco de coma e depressão respiratória.", "Potencialização GABAérgica sinérgica."),
    ("Metronidazol", "Álcool", "grave", "Reação tipo dissulfiram: rubor, taquicardia, náuseas intensas, hipotensão.", "Metronidazol inibe a acetaldeído desidrogenase."),
    ("Tinidazol", "Álcool", "grave", "Reação tipo dissulfiram: rubor, taquicardia, náuseas intensas.", "Inibição da acetaldeído desidrogenase."),
    ("Metformina", "Álcool", "moderada", "Risco aumentado de acidose lática, sobretudo em uso excessivo.", "Álcool potencia o efeito da metformina sobre o metabolismo do lactato."),
    ("Glibenclamida", "Fluconazol", "moderada", "Hipoglicemia grave.", "Fluconazol inibe CYP2C9, reduzindo o metabolismo da sulfonilureia."),
    ("Lítio", "Ibuprofeno", "grave", "Aumento da toxicidade do lítio: tremores, confusão, convulsões.", "AINEs reduzem a excreção renal de lítio."),
    ("Lítio", "Diclofenaco", "grave", "Aumento da toxicidade do lítio: tremores, confusão, convulsões.", "AINEs reduzem a excreção renal de lítio."),
    ("Lítio", "Captopril", "moderada", "Risco de toxicidade do lítio por redução da excreção renal.", "IECA reduz o fluxo renal e pode aumentar a reabsorção de lítio."),
    ("Sildenafila", "Nitrato", "contraindicado", "Hipotensão grave e refratária com risco de morte. USO CONTRAINDICADO.", "Vasodilatação sinérgica extrema via GMPc."),
    ("Tadalafila", "Nitrato", "contraindicado", "Hipotensão grave e refratária com risco de morte. USO CONTRAINDICADO.", "Vasodilatação sinérgica extrema via GMPc."),
    ("Vardenafila", "Nitrato", "contraindicado", "Hipotensão grave e refratária com risco de morte. USO CONTRAINDICADO.", "Vasodilatação sinérgica extrema via GMPc."),
    ("Azatioprina", "Alopurinol", "grave", "Toxicidade grave da azatioprina: mielossupressão intensa.", "Alopurinol inibe a xantina oxidase, que metaboliza a azatioprina."),
    ("Metotrexato", "Ibuprofeno", "grave", "Toxicidade do metotrexato: leucopenia, mucosite, toxicidade renal.", "AINEs reduzem a excreção renal do metotrexato."),
    ("Metotrexato", "AAS", "grave", "Toxicidade do metotrexato: leucopenia, mucosite, toxicidade renal.", "AAS compete com o metotrexato pela secreção tubular renal."),
    ("Rifampicina", "Anticoncepcional oral", "grave", "Falha contraceptiva; usar método adicional durante e por 1 mês após.", "Rifampicina induz CYP3A4 e reduz a biodisponibilidade dos hormônios."),
    ("Ciprofloxacino", "Antiácido", "leve", "Redução de até 90% na absorção do ciprofloxacino; espaçar 2h.", "Quelação de cátions metálicos do antiácido com o antibiótico."),
    ("AAS", "Ibuprofeno", "moderada", "Ibuprofeno pode antagonizar o efeito cardioprotetor do AAS.", "Competição pelo sítio de acetilação da COX-1 plaquetária."),
    ("Claritromicina", "Amiodarona", "grave", "Prolongamento do QT e risco de torsades de pointes.", "Efeito aditivo no bloqueio de canais de potássio cardíacos."),
    ("Ondansetrona", "Amiodarona", "grave", "Prolongamento do QT e risco de arritmia.", "Efeito aditivo no intervalo QT."),
    ("Espironolactona", "Cloreto de potássio", "grave", "Hipercalemia grave.", "Soma de retenção de potássio."),
    ("Enalapril", "Cloreto de potássio", "grave", "Hipercalemia grave.", "IECA reduz a excreção de potássio."),
)

_ALIASES = {
    "aspirina": "aas", "acido acetilsalicilico": "aas", "ácido acetilsalicílico": "aas",
    "varfarina": "warfarina", "coumadin": "warfarina", "marevan": "warfarina",
    "clonazepam": "benzodiazepínico", "diazepam": "benzodiazepínico",
    "alprazolam": "benzodiazepínico", "lorazepam": "benzodiazepínico",
    "bromazepam": "benzodiazepínico", "midazolam": "benzodiazepínico",
    "isossorbida": "nitrato", "mononitrato de isossorbida": "nitrato",
    "propatilnitrato": "nitrato", "nitroglicerina": "nitrato",
    "viagra": "sildenafila", "cialis": "tadalafila",
    "selegilina": "imao", "tranilcipromina": "imao", "moclobemida": "imao",
}


def _norm(text: str) -> str:
    t = unicodedata.normalize("NFKD", (text or "").lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", t).strip()


def _canon(name: str) -> str:
    n = _norm(name)
    return _norm(_ALIASES.get(n, n))


def check_interactions(medications: list[str]) -> list[dict[str, str]]:
    """Pares de medicamentos da lista que batem com a base local."""
    names = [m for m in (medications or []) if m and m.strip()]
    if len(names) < 2:
        return []
    out: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = _canon(names[i]), _canon(names[j])
            if not a or not b:
                continue
            for sa, sb, sev, desc, mech in DRUG_INTERACTIONS:
                na, nb = _norm(sa), _norm(sb)
                hit = (
                    (na in a or a in na) and (nb in b or b in nb)
                ) or (
                    (na in b or b in na) and (nb in a or a in nb)
                )
                if hit:
                    key = tuple(sorted((names[i], names[j])) + [sev])
                    if key in seen:
                        continue
                    seen.add(key)
                    out.append({
                        "medA": names[i], "medB": names[j],
                        "gravidade": sev, "descricao": desc, "mecanismo": mech,
                    })
                    break
    out.sort(key=lambda r: _SEV_ORDER.get(r["gravidade"], 9))
    return out


def format_interactions(rows: list[dict[str, str]]) -> str:
    if not rows:
        return "Nenhuma interação encontrada na base local (não exclui outras — confira em base atualizada)."
    icon = {"contraindicado": "⛔", "grave": "🔴", "moderada": "🟠", "leve": "🟡"}
    lines = []
    for r in rows:
        lines.append(
            f"{icon.get(r['gravidade'], '•')} {r['medA']} × {r['medB']} "
            f"[{r['gravidade'].upper()}]\n    {r['descricao']}\n    Mecanismo: {r['mecanismo']}"
        )
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────── CID-10
@functools.lru_cache(maxsize=1)
def _cid10() -> list[tuple[str, str]]:
    path = _DATA / "cid10.tsv.gz"
    if not path.is_file():
        return []
    with gzip.open(path, "rt", encoding="utf-8") as f:
        rows = []
        for line in f:
            code, _, desc = line.partition("\t")
            if code and desc:
                rows.append((code.strip(), desc.strip()))
        return rows


def cid_search(query: str, limit: int = 20) -> list[dict[str, str]]:
    q = _norm(query)
    if len(q) < 2:
        return []
    data = _cid10()
    # match direto por código (com ou sem ponto)
    qcode = q.replace(".", "").upper()
    exact = [
        {"code": _fmt_cid(c), "description": d}
        for c, d in data if c.upper() == qcode or c.upper().startswith(qcode)
    ]
    if exact and q[0].isalpha() and any(ch.isdigit() for ch in q):
        return exact[:limit]
    terms = [t for t in q.split() if len(t) > 2]
    scored: list[tuple[int, str, str]] = []
    for c, d in data:
        nd = _norm(d)
        if all(t in nd for t in terms) if terms else False:
            score = -len(d) + (100 if nd.startswith(terms[0]) else 0)
            scored.append((score, _fmt_cid(c), d))
    scored.sort(reverse=True)
    res = [{"code": c, "description": d} for _, c, d in scored[:limit]]
    return res or exact[:limit]


def _fmt_cid(code: str) -> str:
    code = code.strip().upper()
    if len(code) >= 4 and code[3].isdigit():
        return f"{code[:3]}.{code[3:]}"
    return code


# ────────────────────────────────────────────────── calculadoras clínicas
def bmi(weight_kg: float, height_m: float) -> dict[str, object]:
    if weight_kg <= 0 or height_m <= 0:
        raise ValueError("peso e altura devem ser positivos")
    h = height_m if height_m < 3 else height_m / 100
    val = weight_kg / (h * h)
    if val < 18.5:
        cat = "baixo peso"
    elif val < 25:
        cat = "eutrófico"
    elif val < 30:
        cat = "sobrepeso"
    elif val < 35:
        cat = "obesidade grau I"
    elif val < 40:
        cat = "obesidade grau II"
    else:
        cat = "obesidade grau III"
    return {"valor": round(val, 1), "unidade": "kg/m²", "categoria": cat,
            "formula": "peso ÷ altura²"}


def cockcroft_gault(age: int, weight_kg: float, creatinine: float, female: bool) -> dict[str, object]:
    if min(age, weight_kg, creatinine) <= 0:
        raise ValueError("idade, peso e creatinina devem ser positivos")
    val = ((140 - age) * weight_kg) / (72 * creatinine)
    if female:
        val *= 0.85
    if val >= 90:
        stage = "≥90 (normal ou G1)"
    elif val >= 60:
        stage = "60–89 (G2)"
    elif val >= 45:
        stage = "45–59 (G3a)"
    elif val >= 30:
        stage = "30–44 (G3b)"
    elif val >= 15:
        stage = "15–29 (G4)"
    else:
        stage = "<15 (G5)"
    return {"valor": round(val, 1), "unidade": "mL/min", "categoria": stage,
            "formula": "[(140−idade) × peso ÷ (72 × creatinina)] × (0,85 se mulher)"}


def bsa(weight_kg: float, height_cm: float) -> dict[str, object]:
    if weight_kg <= 0 or height_cm <= 0:
        raise ValueError("peso e altura devem ser positivos")
    val = math.sqrt((weight_kg * height_cm) / 3600)
    return {"valor": round(val, 2), "unidade": "m²", "categoria": "",
            "formula": "raiz(peso × altura ÷ 3600) — Mosteller"}


def pediatric_dose(dose_per_kg: float, weight_kg: float, max_dose: float | None = None) -> dict[str, object]:
    if dose_per_kg <= 0 or weight_kg <= 0:
        raise ValueError("dose/kg e peso devem ser positivos")
    val = dose_per_kg * weight_kg
    capped = max_dose is not None and val > max_dose
    if capped:
        val = float(max_dose)
    return {"valor": round(val, 2), "unidade": "por administração",
            "categoria": "limitada à dose máxima do adulto" if capped else "",
            "formula": "dose/kg × peso" + ("  (com teto)" if max_dose else "")}
