from __future__ import annotations

import datetime
import json
import re
from typing import TYPE_CHECKING, Any, Awaitable, Callable

from jarvis.database import Database

if TYPE_CHECKING:
    from jarvis.models import LLMRequest, LLMResponse, Message

# assinatura de router.chat(request, provider_name=None) -> LLMResponse
ChatFn = Callable[..., "Awaitable[LLMResponse]"]


class ContextualMemoryManager:
    """Gerenciador de Memória Contextual de Longo Prazo do Jarvis.
    
    Aprende fatos, regras, preferências e contextos de projeto a partir
    das interações do usuário e injeta essas memórias de forma inteligente no prompt.
    """

    def __init__(self, database: Database) -> None:
        self.db = database

    # até a primeira conjunção/pontuação — evita capturar a frase inteira
    _CLAUSE = r"([^,.;!?\n]+?)(?=\s+(?:e|mas|porque|pois|que|para|pra)\s|[,.;!?\n]|$)"

    def extract_and_learn(self, user_message: str, assistant_reply: str = "") -> list[dict[str, Any]]:
        """Extrai fatos/preferências/regras da fala do usuário (heurística por padrões).

        É deliberadamente conservador: só grava quando o texto casa um padrão
        claro. Muita coisa dita naturalmente não é capturada — para isso o
        agente tem `consultar_historico_conversas` e o usuário pode usar o
        botão "+ Adicionar Memória".
        """
        text = " ".join(user_message.strip().split())
        c = self._CLAUSE
        learned: list[dict[str, Any]] = []

        # (regex, categoria, base_key, template) — o template define o SENTIDO
        rules: list[tuple[str, str, str, str]] = [
            # preferências
            (rf"(?:eu\s+)?prefiro\s+{c}", "preferencia", "pref", "O usuário prefere {}"),
            (rf"(?:sempre\s+)?responda\s+(?:em|com|usando)\s+{c}", "preferencia", "estilo", "Nas respostas, usar {}"),
            (rf"gosto\s+de\s+{c}", "preferencia", "gosto", "O usuário gosta de {}"),
            (rf"(?:priorize|dê\s+prioridade\s+a)\s+{c}", "preferencia", "prioridade", "Priorizar {}"),
            # regras negativas — NÃO inverter o sentido
            (rf"(?:não\s+use|nunca\s+use|evite\s+usar|evite)\s+{c}", "regra", "evitar", "NUNCA usar {} (o usuário pediu para evitar)"),
            (rf"(?:não\s+quero|não\s+gosto\s+de|odeio)(?:\s+que\s+(?:você|vc))?(?:\s+us(?:e|ar))?\s+{c}", "regra", "aversao", "O usuário NÃO quer {}"),
            # identidade / fatos pessoais
            (r"(?:meu\s+nome\s+é|me\s+chamo|pode\s+me\s+chamar\s+de)\s+([A-Za-zÀ-ÿ]+(?:\s+(?!e\b|ou\b|mas\b|que\b|e,)[A-Za-zÀ-ÿ]+){0,2})", "fato", "nome_usuario", "O nome do usuário é {}"),
            (rf"(?:eu\s+)?(?:sou|trabalho\s+como)\s+(?!de\b|da\b|do\b)({c})", "fato", "profissao_usuario", "Profissão/cargo do usuário: {}"),
            (rf"(?:minha\s+empresa\s+é|trabalho\s+n[ao]|sou\s+dono\s+d[ao])\s+{c}", "empresa", "empresa_usuario", "Empresa/organização do usuário: {}"),
            (rf"(?:eu\s+)?moro\s+(?:em|no|na)\s+{c}", "fato", "local_usuario", "O usuário mora em {}"),
            # projetos
            (rf"(?:estou\s+desenvolvendo|estou\s+criando|estou\s+fazendo|meu\s+projeto\s+é|o\s+projeto\s+se\s+chama)\s+{c}", "projeto", "projeto_ativo", "Projeto em andamento: {}"),
            (rf"(?:nesse|neste|no)\s+projeto\s+(?:eu\s+|a\s+gente\s+|nós\s+)?(?:uso|usa|usamos|utilizo|utiliza|utilizamos)\s+{c}", "projeto", "stack_projeto", "Stack do projeto: {}"),
        ]

        for pattern, cat, base_key, template in rules:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                val = match.group(1).strip(" .,;:")
                if not (2 < len(val) <= 140):
                    continue
                # chave única e determinística: base + resumo do valor
                slug = re.sub(r"[^a-z0-9]+", "_", val.lower())[:32].strip("_")
                key = base_key if base_key == "nome_usuario" else f"{base_key}_{slug}"
                mem_id = self.db.save_user_memory({
                    "category": cat,
                    "key": key,
                    "content": template.format(val),
                    "confidence": 0.9 if cat in ("preferencia", "regra") else 0.95,
                    "source": "aprendizado_dialogo",
                })
                learned.append({"id": mem_id, "category": cat, "content": template.format(val)})

        return learned

    _STOP = frozenset(
        "a o e de da do das dos em no na para pra por com que se um uma os as "
        "eu meu minha voce você isso esse essa como qual quais onde quando".split()
    )
    _MAX_INJECT = 14

    def get_context_prompt(self, current_query: str = "") -> str:
        """Bloco de memórias para o System Prompt, priorizando as relevantes à pergunta atual."""
        memories = self.db.list_user_memories()
        if not memories:
            return ""

        # sempre incluir identidade/regras (baratas e quase sempre úteis)
        _core = ("fato", "regra", "empresa")
        always = [m for m in memories if m["category"] in _core]
        rest = [m for m in memories if m["category"] not in _core]

        q_words = {
            w for w in re.findall(r"[a-zà-ÿ0-9]{3,}", (current_query or "").lower())
            if w not in self._STOP
        }

        def relevance(m: dict[str, Any]) -> int:
            if not q_words:
                return 0
            text = m["content"].lower()
            return sum(1 for w in q_words if w in text)

        rest.sort(key=lambda m: (relevance(m), m["confidence"], m["access_count"]), reverse=True)
        chosen = (always + rest)[: self._MAX_INJECT]
        if not chosen:
            return ""

        lines = [
            "[MEMÓRIA CONTEXTUAL & APRENDIZADOS SOBRE O USUÁRIO]",
            "Conhecimentos de interações passadas — use para personalizar, mas confirme se algo parecer desatualizado:",
        ]
        for m in chosen:
            lines.append(f"- [{m['category'].upper()}] {m['content']}")
        return "\n".join(lines)


class BehavioralLearner:
    """Rastreador e Adaptador de Comportamento do Usuário para o Jarvis."""

    def __init__(self, database: Database) -> None:
        self.db = database

    def record_interaction(self, user_text: str, tool_used: str | None = None) -> None:
        """Registra e processa métricas de comportamento a cada interação."""
        now = datetime.datetime.now()
        hour = now.hour

        # Registra log
        action_type = f"tool:{tool_used}" if tool_used else "chat_message"
        self.db.log_behavior_action(action_type, user_text[:100])

        # 1. Padrão de Horário de Uso
        if 6 <= hour < 12:
            period = "Manhã (06h-12h)"
        elif 12 <= hour < 18:
            period = "Tarde (12h-18h)"
        elif 18 <= hour < 23:
            period = "Noite (18h-23h)"
        else:
            period = "Madrugada (23h-06h)"
        self.db.set_behavior_feature("horario_mais_ativo", period, 0.8)

        # 2. Preferência Técnica / Linguagem de Programação
        tech_matches = re.findall(r"\b(python|javascript|typescript|qml|c\+\+|rust|sql|docker|git|bash|html|css)\b", user_text, re.IGNORECASE)
        if tech_matches:
            top_tech = tech_matches[0].lower()
            self.db.set_behavior_feature("linguagem_predileta", top_tech.capitalize(), 0.9)

        # 3. Nível de Detalhamento Solicitado
        if any(w in user_text.lower() for w in ["detalhe", "explique passo a passo", "completo", "como funciona"]):
            self.db.set_behavior_feature("estilo_resposta", "Detalhado e Didático", 0.85)
        elif any(w in user_text.lower() for w in ["rápido", "curto", "direto", "resuma", "só o comando", "apenas"]):
            self.db.set_behavior_feature("estilo_resposta", "Conciso e Direto", 0.9)

    def get_behavior_guidelines(self) -> str:
        """Retorna diretrizes comportamentais adaptativas para o prompt do Jarvis."""
        profile = self.db.get_behavior_profile()
        if not profile:
            return ""

        lines = ["[ADAPTAÇÃO COMPORTAMENTAL DO ASSISTENTE]"]
        if "estilo_resposta" in profile:
            lines.append(f"- Adaptação de estilo: O usuário prefere respostas em formato {profile['estilo_resposta']['value']}.")
        if "linguagem_predileta" in profile:
            lines.append(f"- Contexto técnico: O usuário frequentemente trabalha com {profile['linguagem_predileta']['value']}.")
        if "horario_mais_ativo" in profile:
            lines.append(f"- Padrão de rotina: Horário frequente de produtividade é no período da {profile['horario_mais_ativo']['value']}.")

        return "\n".join(lines)


class ProactiveSuggestionsEngine:
    """Motor de Sugestões Proativas e Ações Preditivas do Jarvis."""

    def __init__(self, database: Database) -> None:
        self.db = database

    _SECTOR_SUGGESTIONS: dict[str, list[dict[str, str]]] = {
        "saude": [
            {"title": "Pacientes de hoje", "text": "Consultas e retornos agendados",
             "icon": "🗓️", "action": "Quais pacientes tenho agendados para hoje e amanhã?",
             "tag": "AGENDA CLÍNICA"},
            {"title": "Laudos pendentes de análise", "text": "Registros sem o segundo olhar da IA",
             "icon": "🗂️", "action": "Liste os laudos e exames de pacientes que ainda não foram analisados.",
             "tag": "PRONTUÁRIO"},
            {"title": "Resumir último exame", "text": "Achados e alterações do registro mais recente",
             "icon": "🧪", "action": "Resuma o exame mais recente que registrei e destaque o que está fora da faixa.",
             "tag": "APOIO CLÍNICO"},
            {"title": "Checar interações", "text": "Medicações de um paciente",
             "icon": "💊", "action": "Verifique interações medicamentosas para a lista de remédios de um paciente meu.",
             "tag": "MEDICAÇÃO"},
            {"title": "Rascunho de evolução", "text": "Organizar a consulta em formato SOAP",
             "icon": "📝", "action": "Monte um rascunho de evolução no formato SOAP com os dados de uma consulta.",
             "tag": "REGISTRO"},
            {"title": "Orientações de alta", "text": "Texto em linguagem simples para o paciente",
             "icon": "🗣️", "action": "Escreva orientações pós-consulta em linguagem simples para eu revisar e entregar ao paciente.",
             "tag": "COMUNICAÇÃO"},
        ],
    }

    def generate_suggestions(
        self,
        current_view: str = "hub",
        last_interaction: str = "",
        sector: str = "geral",
    ) -> list[dict[str, str]]:
        """Gera chips e cartões de sugestões proativas com base no contexto temporal e histórico."""
        by_sector = self._SECTOR_SUGGESTIONS.get((sector or "geral").strip())
        if by_sector:
            return list(by_sector[:6])

        now = datetime.datetime.now()
        hour = now.hour
        suggestions: list[dict[str, str]] = []

        # 1. Sugestões Baseadas em Horário & Contexto Geral
        if 6 <= hour < 12:
            suggestions.append({
                "title": "Bom dia!",
                "text": "Verificar compromissos e tarefas de hoje",
                "icon": "🌅",
                "action": "Quais são meus compromissos e lembretes para hoje?",
                "tag": "ROTINA MATINAL"
            })
            suggestions.append({
                "title": "Status do Sistema",
                "text": "Monitorar uso de CPU, memória e servidores",
                "icon": "⚡",
                "action": "Qual o status de telemetria do sistema e uso de recursos?",
                "tag": "DIAGNÓSTICO"
            })
        elif 12 <= hour < 18:
            suggestions.append({
                "title": "Produtividade da Tarde",
                "text": "Revisar canais de comunicação e tarefas pendentes",
                "icon": "💬",
                "action": "Verifique o status do canal WhatsApp e mensagens pendentes.",
                "tag": "COMUNICAÇÃO"
            })
            suggestions.append({
                "title": "Gestão de Código & Git",
                "text": "Verificar status do repositório e commits",
                "icon": "🚀",
                "action": "Execute os testes do projeto e me informe o resultado.",
                "tag": "DESENVOLVIMENTO"
            })
        else:
            suggestions.append({
                "title": "Encerramento do Dia",
                "text": "Resumo de atividades e status dos servidores",
                "icon": "🌙",
                "action": "Faça um resumo das principais atividades de hoje.",
                "tag": "RESUMO"
            })
            suggestions.append({
                "title": "Backup & Segurança",
                "text": "Checagem de conexões SSH e integridade do banco",
                "icon": "🛡️",
                "action": "Verifique o status dos servidores SSH cadastrados.",
                "tag": "SEGURANÇA"
            })

        # 2. Sugestões Rápidas de Ação Frequente
        suggestions.append({
            "title": "Controle de Mídia",
            "text": "Play / Pausar música",
            "icon": "🎵",
            "action": "Pause ou reproduza a música atual.",
            "tag": "MÍDIA"
        })
        suggestions.append({
            "title": "Lembrança Perfeita",
            "text": "O que conversamos recentemente?",
            "icon": "🧠",
            "action": "Pesquise no histórico de conversas o que conversamos recentemente.",
            "tag": "MEMÓRIA"
        })
        suggestions.append({
            "title": "Agenda & Lembretes",
            "text": "Agendar novo compromisso",
            "icon": "📅",
            "action": "Criar um novo compromisso na agenda",
            "tag": "AGENDA"
        })
        suggestions.append({
            "title": "Comandos do Sistema",
            "text": "Abrir VS Code ou Terminal",
            "icon": "💻",
            "action": "Abra o VS Code para continuarmos o projeto.",
            "tag": "SISTEMA"
        })

        # 3. Sugestões Reativas após código ou tarefas
        if any(term in last_interaction.lower() for term in ["código", "função", "bug", "python", "erro", "teste"]):
            suggestions.insert(0, {
                "title": "Executar Testes",
                "text": "Rodar suíte automatizada de testes",
                "icon": "🧪",
                "action": "Execute os testes unitários do sistema e valide o código.",
                "tag": "AÇÃO REATIVA"
            })
        elif any(term in last_interaction.lower() for term in ["música", "video", "som", "tocar", "ouvir"]):
            suggestions.insert(0, {
                "title": "Tocar Música",
                "text": "Tocar no YouTube ou Spotify",
                "icon": "🎶",
                "action": "Toque músicas no YouTube.",
                "tag": "MÍDIA"
            })

        return suggestions[:6]


class MemoryConsolidator:
    """Extrai memórias duráveis de uma conversa usando o próprio LLM.

    Complementa a heurística por regex de `ContextualMemoryManager`: em vez de
    depender de frases exatas, pede ao modelo para listar em JSON os fatos que
    valem para conversas futuras. Roda de vez em quando (não a cada turno).
    """

    _CATEGORIES = ("fato", "preferencia", "regra", "projeto", "empresa", "ferramenta")
    _MAX_ITEMS = 6
    _MAX_TRANSCRIPT_CHARS = 6000

    _SYSTEM = (
        "Você é o módulo de memória de longo prazo de um assistente pessoal. "
        "Sua tarefa: ler um trecho de conversa e extrair APENAS fatos DURÁVEIS "
        "sobre o usuário e os projetos dele — coisas que valem para conversas "
        "FUTURAS.\n\n"
        "Responda SOMENTE com um array JSON. Cada item:\n"
        '  {"category": "<categoria>", "key": "<slug_curto>", '
        '"content": "<frase curta em 3a pessoa>", "confidence": <0.0-1.0>}\n\n'
        f"Categorias válidas: {', '.join(_CATEGORIES)}.\n"
        "INCLUA: nome, papel/profissão, empresa, cidade; stack e decisões de "
        "arquitetura de um projeto; preferências de estilo de resposta; regras "
        "explícitas ('nunca faça X'); ferramentas/serviços que a pessoa usa.\n"
        "NÃO inclua: perguntas pontuais, estado temporário ('estou com um bug "
        "agora'), trechos de código, opiniões passageiras, nem nada que já "
        "esteja na lista 'JÁ SEI'.\n"
        "Cada 'content' começa com 'O usuário ' ou 'O projeto '. Frase curta.\n"
        f"No máximo {_MAX_ITEMS} itens. Se não houver nada novo e durável, "
        "responda exatamente: []"
    )

    def __init__(self, database: Database) -> None:
        self.db = database

    def _transcript(self, messages: list["Message"]) -> str:
        parts: list[str] = []
        for m in messages:
            role = getattr(m, "role", "")
            if role not in ("user", "assistant"):
                continue
            text = (getattr(m, "content", "") or "").strip()
            if not text:
                continue
            who = "USUÁRIO" if role == "user" else "ASSISTENTE"
            parts.append(f"{who}: {text}")
        blob = "\n".join(parts)
        return blob[-self._MAX_TRANSCRIPT_CHARS :]

    def _known(self) -> str:
        rows = self.db.list_user_memories()
        if not rows:
            return "(nada ainda)"
        return "\n".join(f"- [{r['category']}] {r['content']}" for r in rows[:40])

    @staticmethod
    def _parse(raw: str) -> list[dict[str, Any]]:
        raw = (raw or "").strip()
        if raw.startswith("```"):
            raw = re.sub(r"^```[a-zA-Z]*\n?|```$", "", raw).strip()
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            match = re.search(r"\[.*\]", raw, re.DOTALL)
            if not match:
                return []
            try:
                data = json.loads(match.group(0))
            except json.JSONDecodeError:
                return []
        return data if isinstance(data, list) else []

    async def consolidate(
        self,
        messages: list["Message"],
        chat_fn: ChatFn,
        *,
        provider_name: str | None = None,
    ) -> list[dict[str, Any]]:
        """Chama o LLM, grava o que for novo e durável, devolve os itens salvos."""
        from jarvis.models import LLMRequest, Message

        transcript = self._transcript(messages)
        if len(transcript) < 40:  # nada de substancial
            return []

        request = LLMRequest(
            messages=(
                Message(role="system", content=self._SYSTEM),
                Message(
                    role="user",
                    content=f"JÁ SEI:\n{self._known()}\n\nCONVERSA:\n{transcript}",
                ),
            ),
            max_output_tokens=600,
            temperature=0.0,
        )
        try:
            response = await chat_fn(request, provider_name=provider_name)
        except Exception:  # noqa: BLE001 - consolidação nunca derruba nada
            return []

        saved: list[dict[str, Any]] = []
        existing = {
            self._norm(r["content"]) for r in self.db.list_user_memories()
        }
        for item in self._parse(getattr(response, "content", "")):
            if not isinstance(item, dict):
                continue
            content = str(item.get("content", "")).strip()
            category = str(item.get("category", "fato")).strip().lower()
            if not (5 < len(content) <= 200) or category not in self._CATEGORIES:
                continue
            if self._norm(content) in existing:
                continue
            try:
                confidence = float(item.get("confidence", 0.75))
            except (TypeError, ValueError):
                confidence = 0.75
            raw_key = str(item.get("key", "")).strip() or content
            key = re.sub(r"[^a-z0-9]+", "_", raw_key.lower())[:40].strip("_") or "mem"
            mem_id = self.db.save_user_memory({
                "category": category,
                "key": f"llm_{key}",
                "content": content,
                "confidence": max(0.3, min(confidence, 0.98)),
                "source": "consolidacao_llm",
            })
            existing.add(self._norm(content))
            saved.append({"id": mem_id, "category": category, "content": content})
            if len(saved) >= self._MAX_ITEMS:
                break
        return saved

    @staticmethod
    def _norm(text: str) -> str:
        return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


class CognitiveEngine:
    """Motor Cognitivo Unificado do Sistema Jarvis."""

    def __init__(self, database: Database) -> None:
        self.database = database
        self.memory = ContextualMemoryManager(database)
        self.behavior = BehavioralLearner(database)
        self.proactive = ProactiveSuggestionsEngine(database)
        self.consolidator = MemoryConsolidator(database)

    def process_user_turn(self, user_message: str, assistant_reply: str = "", tool_used: str | None = None) -> None:
        """Processa a fala do usuário para aprendizado contínuo (camada rápida por regex)."""
        self.memory.extract_and_learn(user_message, assistant_reply)
        self.behavior.record_interaction(user_message, tool_used)

    def get_persona_prompt(self) -> str:
        """Gera as diretrizes de personalidade, tom e identidade personalizadas."""
        persona = self.database.get_assistant_persona()
        lines = ["[PERSONALIDADE & IDENTIDADE DO ASSISTENTE]"]
        name = persona.get("name", "Jarvis")
        personality = persona.get("personality", "Prestativo e Amigável")
        tone = persona.get("tone", "Natural")
        accent = persona.get("accent", "Português (Brasil)")
        custom = persona.get("custom_instructions", "")

        lines.append(f"- Seu nome é: {name}. Identifique-se e responda sempre sob esta identidade.")
        lines.append(f"- Estilo e Personalidade: Adote uma postura {personality}.")
        lines.append(f"- Tonalidade da comunicação: {tone}.")
        lines.append(f"- Idioma e Variação: {accent}.")
        lines.append("- Nunca descreva ou soletre nomes de emojis em texto (ex.: nunca fale 'rosto sorridente' ou 'emoji de coração'); mantenha a fala natural e fluida.")
        if custom:
            lines.append(f"- Instruções Especiais do Usuário: {custom}")

        return "\n".join(lines)

    def build_cognitive_context(self, current_query: str = "") -> str:
        """Gera o contexto cognitivo completo (persona + memórias + perfil) para o System Prompt."""
        blocks = []
        persona_ctx = self.get_persona_prompt()
        if persona_ctx:
            blocks.append(persona_ctx)

        mem_ctx = self.memory.get_context_prompt(current_query)
        if mem_ctx:
            blocks.append(mem_ctx)

        beh_ctx = self.behavior.get_behavior_guidelines()
        if beh_ctx:
            blocks.append(beh_ctx)

        return "\n\n".join(blocks)
