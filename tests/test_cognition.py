from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path

from jarvis.cognition import (
    BehavioralLearner,
    CognitiveEngine,
    ContextualMemoryManager,
    MemoryConsolidator,
    ProactiveSuggestionsEngine,
)
from jarvis.database import Database
from jarvis.models import LLMResponse, Message


class TestCognition(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db_path = Path(self.temp_dir.name) / "test_jarvis.db"
        self.db = Database(self.db_path)
        self.db.initialize()
        self.cognition = CognitiveEngine(self.db)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_memory_crud(self) -> None:
        # 1. Salvar memória
        mem_id = self.db.save_user_memory({
            "category": "preferencia",
            "key": "pref_lang",
            "content": "O usuário prefere código em Python 3.12 com type hints.",
            "confidence": 1.0,
            "source": "teste",
        })
        self.assertGreater(mem_id, 0)

        # 2. Obter memória
        mem = self.db.get_user_memory(mem_id)
        self.assertIsNotNone(mem)
        self.assertEqual(mem["key"], "pref_lang")
        self.assertEqual(mem["category"], "preferencia")

        # 3. Listar memórias
        memories = self.db.list_user_memories()
        self.assertEqual(len(memories), 1)

        # 4. Buscar memórias
        results = self.db.search_user_memories("Python")
        self.assertEqual(len(results), 1)

        # 5. Excluir memória
        self.db.delete_user_memory(mem_id)
        self.assertEqual(len(self.db.list_user_memories()), 0)

    def test_automatic_memory_learning(self) -> None:
        manager = ContextualMemoryManager(self.db)

        # Simula usuário expressando preferências e fatos
        manager.extract_and_learn("Eu prefiro respostas curtas e diretas.")
        manager.extract_and_learn("Meu nome é Carlos Silva.")
        manager.extract_and_learn("Estou desenvolvendo o projeto Jarvis IA.")

        memories = self.db.list_user_memories()
        self.assertGreaterEqual(len(memories), 3)

        prompt_block = manager.get_context_prompt()
        self.assertIn("[MEMÓRIA CONTEXTUAL & APRENDIZADOS SOBRE O USUÁRIO]", prompt_block)
        self.assertIn("Carlos Silva", prompt_block)
        self.assertIn("Jarvis IA", prompt_block)

    def test_negative_rule_keeps_meaning(self) -> None:
        manager = ContextualMemoryManager(self.db)
        manager.extract_and_learn("Nunca use emojis nas respostas.")
        contents = [m["content"].lower() for m in self.db.list_user_memories()]
        self.assertTrue(any("nunca usar emojis" in c for c in contents))
        self.assertFalse(any("prefere emojis" in c or "prefere: emojis" in c for c in contents))

    def test_name_capture_stops_at_conjunction(self) -> None:
        manager = ContextualMemoryManager(self.db)
        manager.extract_and_learn("Meu nome é Ana e sou desenvolvedora.")
        names = [m["content"] for m in self.db.list_user_memories() if m["key"] == "nome_usuario"]
        self.assertEqual(names, ["O nome do usuário é Ana"])

    def test_llm_consolidation_saves_durable_facts(self) -> None:
        convo = [
            Message(role="user", content="a gente usa Postgres e Redis nesse projeto"),
            Message(role="assistant", content="Ok."),
            Message(role="user", content="meu sócio se chama Bruno, cuida do front"),
            Message(role="assistant", content="Anotado."),
        ]

        async def fake_chat(request, provider_name=None):
            self.assertEqual(request.messages[0].role, "system")
            payload = (
                '```json\n['
                '{"category":"projeto","key":"db","content":"O projeto usa Postgres e Redis","confidence":0.9},'
                '{"category":"fato","key":"socio","content":"O sócio do usuário se chama Bruno","confidence":0.9},'
                '{"category":"lixo","key":"x","content":"categoria invalida ignorada","confidence":0.9}'
                ']\n```'
            )
            return LLMResponse(provider="fake", model="m", content=payload)

        con = MemoryConsolidator(self.db)
        saved = asyncio.run(con.consolidate(convo, fake_chat))
        contents = {m["content"] for m in self.db.list_user_memories()}
        self.assertIn("O projeto usa Postgres e Redis", contents)
        self.assertIn("O sócio do usuário se chama Bruno", contents)
        self.assertNotIn("categoria invalida ignorada", contents)  # categoria fora da lista
        # roda de novo: dedup, nada novo
        again = asyncio.run(con.consolidate(convo, fake_chat))
        self.assertEqual(again, [])
        self.assertEqual(len(saved), 2)

    def test_llm_consolidation_survives_bad_output(self) -> None:
        async def junk(request, provider_name=None):
            return LLMResponse(provider="f", model="m", content="desculpe, não entendi")

        async def boom(request, provider_name=None):
            raise RuntimeError("provedor caiu")

        con = MemoryConsolidator(self.db)
        msgs = [Message(role="user", content="uma frase qualquer com conteudo suficiente aqui")]
        self.assertEqual(asyncio.run(con.consolidate(msgs, junk)), [])
        self.assertEqual(asyncio.run(con.consolidate(msgs, boom)), [])

    def test_query_relevance_prioritises(self) -> None:
        manager = ContextualMemoryManager(self.db)
        for i in range(20):
            self.db.save_user_memory({
                "category": "projeto", "key": f"p{i}",
                "content": f"nota irrelevante numero {i}", "confidence": 0.9,
            })
        self.db.save_user_memory({
            "category": "projeto", "key": "kubernetes",
            "content": "O deploy do projeto usa Kubernetes na AWS", "confidence": 0.9,
        })
        block = manager.get_context_prompt("como faço o deploy no kubernetes?")
        self.assertIn("Kubernetes", block)

    def test_behavioral_learning(self) -> None:
        learner = BehavioralLearner(self.db)

        learner.record_interaction("Por favor, detalhe como funciona essa função em Python.")
        profile = self.db.get_behavior_profile()

        self.assertIn("linguagem_predileta", profile)
        self.assertEqual(profile["linguagem_predileta"]["value"], "Python")
        self.assertIn("estilo_resposta", profile)
        self.assertEqual(profile["estilo_resposta"]["value"], "Detalhado e Didático")

        guidelines = learner.get_behavior_guidelines()
        self.assertIn("[ADAPTAÇÃO COMPORTAMENTAL DO ASSISTENTE]", guidelines)
        self.assertIn("Python", guidelines)

    def test_proactive_suggestions(self) -> None:
        engine = ProactiveSuggestionsEngine(self.db)
        suggestions = engine.generate_suggestions("hub", last_interaction="Como resolver esse bug no python?")

        self.assertGreater(len(suggestions), 0)
        # Deve conter ação reativa para testes de código
        titles = [s["title"] for s in suggestions]
        self.assertIn("Executar Testes", titles)

    def test_cognitive_engine_unification(self) -> None:
        self.cognition.process_user_turn(
            "Meu nome é Mariana e eu prefiro explicações em C++.",
            "Olá Mariana! Perfeito, usarei exemplos em C++."
        )

        full_context = self.cognition.build_cognitive_context()
        self.assertIn("Mariana", full_context)
        self.assertIn("C++", full_context)


if __name__ == "__main__":
    unittest.main()
