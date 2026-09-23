"""Rotinas de automação: casar um comando falado/digitado com uma rotina salva.

Uma rotina e um nome + uma lista de passos em linguagem natural. O agente
executa os passos em sequencia (ver `JarvisBackend._routine_worker`).
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable

from jarvis.database import Database
from jarvis.models import Routine

# Verbos que iniciam um comando de rotina. Deliberadamente NÃO inclui "abrir"
# nem "ligar" para não colidir com "abra o YouTube".
_TRIGGER = re.compile(
    r"^\s*(?:jarvis[,:\s]+)?"
    r"(?:rod[ae]|rode|execut[ae]|execute|inici[ae]|inicie|ativ[ae]|ative|"
    r"come[cç][ae]|come[cç]e|start|dispara[r]?|roda[r]?)\s+"
    r"(?:a\s+)?(?:rotina\s+)?(.+?)\s*$",
    re.IGNORECASE,
)
_EXPLICIT = re.compile(
    r"^\s*(?:jarvis[,:\s]+)?rotina\s+(.+?)\s*$", re.IGNORECASE
)
_FILLERS = re.compile(
    r"\b(agora|por favor|pra mim|para mim|pfv|ai|entao|de novo)\b", re.IGNORECASE
)


def _normalize(text: str) -> str:
    stripped = unicodedata.normalize("NFKD", text)
    stripped = stripped.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", stripped).strip().lower()


def match_routine_command(text: str, names: Iterable[str]) -> str | None:
    """Devolve o nome da rotina se `text` for um comando para roda-la, senao None."""
    match = _TRIGGER.match(text) or _EXPLICIT.match(text)
    if not match:
        return None
    candidate = _FILLERS.sub("", match.group(1)).strip()
    candidate_norm = _normalize(candidate)
    if not candidate_norm:
        return None

    names = list(names)
    partial: str | None = None
    for name in names:
        name_norm = _normalize(name)
        if name_norm == candidate_norm:
            return name
        if name_norm and (name_norm in candidate_norm or candidate_norm in name_norm):
            partial = partial or name
    if partial:
        return partial

    # última tentativa: sobreposição de palavras (>= metade das palavras do nome)
    candidate_words = set(candidate_norm.split())
    best: tuple[int, str] | None = None
    for name in names:
        name_words = set(_normalize(name).split())
        if not name_words:
            continue
        overlap = len(candidate_words & name_words)
        if overlap and overlap >= (len(name_words) + 1) // 2:
            if best is None or overlap > best[0]:
                best = (overlap, name)
    return best[1] if best else None


_SEED_ROUTINES = (
    Routine(
        name="Bom dia",
        description="Clima do dia e um cumprimento rápido.",
        steps=(
            "Me diga o clima de agora em uma frase curta.",
            "Me deseje um bom dia de forma breve e calorosa.",
        ),
    ),
    Routine(
        name="Modo trabalho",
        description="Musica para concentrar e a pasta de downloads.",
        steps=(
            "Abra o YouTube e pesquise por 'lofi hip hop radio'.",
            "Abra a pasta de Downloads.",
        ),
    ),
)


def seed_default_routines(database: Database) -> None:
    """Cria rotinas de exemplo uma única vez (marca em settings)."""
    if database.get_setting("routines_seeded"):
        return
    if not database.list_routines():
        for routine in _SEED_ROUTINES:
            database.save_routine(routine)
    database.set_setting("routines_seeded", True)
