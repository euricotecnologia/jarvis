from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from jarvis.database import Database
from jarvis.gui import AI_AGENT_MODELS, AI_AGENT_PROVIDERS


class TestAiAgents(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db_path = Path(self.temp_dir.name) / "test_agents.db"
        self.db = Database(self.db_path)
        self.db.initialize()

    def tearDown(self) -> None:
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_database_agent_crud(self) -> None:
        # 1. Initial list empty
        agents = self.db.list_ai_agents()
        self.assertEqual(len(agents), 0)

        # 2. Insert new agent
        agent_id = self.db.save_ai_agent({
            "name": "Suporte Técnico",
            "provider": "Anthropic",
            "model": "claude-3-5-sonnet-latest",
            "api_key": "sk-ant-test",
            "base_url": "",
            "system_prompt": "Você é especialista em suporte.",
            "temperature": 0.5,
            "active": True,
        })
        self.assertGreater(agent_id, 0)

        # 3. Retrieve agent
        retrieved = self.db.get_ai_agent(agent_id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved["name"], "Suporte Técnico")
        self.assertEqual(retrieved["provider"], "Anthropic")
        self.assertEqual(retrieved["model"], "claude-3-5-sonnet-latest")
        self.assertEqual(retrieved["temperature"], 0.5)
        self.assertEqual(retrieved["active"], 1)

        # 4. Update agent
        self.db.save_ai_agent({
            "id": agent_id,
            "name": "Suporte Nível 2",
            "provider": "Anthropic",
            "model": "claude-3-7-sonnet-latest",
            "api_key": "sk-ant-test2",
            "base_url": "",
            "system_prompt": "Suporte avançado.",
            "temperature": 0.3,
            "active": False,
        })
        updated = self.db.get_ai_agent(agent_id)
        self.assertEqual(updated["name"], "Suporte Nível 2")
        self.assertEqual(updated["model"], "claude-3-7-sonnet-latest")
        self.assertEqual(updated["active"], 0)

        # 5. Delete agent
        self.db.delete_ai_agent(agent_id)
        self.assertEqual(len(self.db.list_ai_agents()), 0)

    def test_providers_and_models_catalogue(self) -> None:
        self.assertIn("OpenAI", AI_AGENT_PROVIDERS)
        self.assertIn("Anthropic", AI_AGENT_PROVIDERS)
        self.assertIn("Gemini", AI_AGENT_PROVIDERS)
        self.assertIn("Groq", AI_AGENT_PROVIDERS)
        self.assertIn("OpenRouter", AI_AGENT_PROVIDERS)
        self.assertIn("LM Studio", AI_AGENT_PROVIDERS)
        self.assertIn("Ollama", AI_AGENT_PROVIDERS)

        # OpenAI expanded catalogue
        openai_models = AI_AGENT_MODELS["OpenAI"]
        self.assertIn("gpt-3.5-turbo", openai_models)
        self.assertIn("gpt-3.5-turbo-0125", openai_models)
        self.assertIn("gpt-4", openai_models)
        self.assertIn("gpt-4-turbo", openai_models)
        self.assertIn("gpt-4o", openai_models)
        self.assertIn("gpt-4o-mini", openai_models)
        self.assertIn("chatgpt-4o-latest", openai_models)
        self.assertIn("o1", openai_models)
        self.assertIn("o1-mini", openai_models)
        self.assertIn("o3-mini", openai_models)
        self.assertIn("gpt-4.5-preview", openai_models)

        # Anthropic expanded catalogue
        anthropic_models = AI_AGENT_MODELS["Anthropic"]
        self.assertIn("claude-3-7-sonnet-latest", anthropic_models)
        self.assertIn("claude-3-5-sonnet-latest", anthropic_models)
        self.assertIn("claude-3-5-haiku-latest", anthropic_models)
        self.assertIn("claude-3-opus-latest", anthropic_models)
        self.assertIn("claude-3-opus-20240229", anthropic_models)
        self.assertIn("claude-2.1", anthropic_models)

        # Gemini expanded catalogue
        gemini_models = AI_AGENT_MODELS["Gemini"]
        self.assertIn("gemini-2.0-flash", gemini_models)
        self.assertIn("gemini-2.0-flash-lite", gemini_models)
        self.assertIn("gemini-2.0-pro-exp-02-05", gemini_models)
        self.assertIn("gemini-2.0-flash-thinking-exp-01-21", gemini_models)
        self.assertIn("gemini-1.5-pro", gemini_models)
        self.assertIn("gemini-1.5-flash", gemini_models)
        self.assertIn("gemini-1.5-flash-8b", gemini_models)
        self.assertIn("gemini-1.0-pro", gemini_models)

    def test_communication_agent_crud(self) -> None:
        # 1. Initial list empty
        comm_agents = self.db.list_communication_agents()
        self.assertEqual(len(comm_agents), 0)

        # 2. Insert new Communication Agent with all company fields
        agent_id = self.db.save_communication_agent({
            "name": "Ana Assistente",
            "age": "28",
            "gender": "Feminino",
            "role": "Consultora de Vendas",
            "model_id": 1,
            "model_name": "OpenAI // gpt-4o",
            "tone": "Acolhedor",
            "formality": "Equilibrado",
            "emoji_level": "Normal",
            "response_style": "Curto e objetivo",
            "language": "Português (Brasil)",
            "job_description": "Atender clientes interessados em produtos e serviços.",
            "responsibilities": '["Atender WhatsApp", "Gerar orçamentos"]',
            "company_name": "Empresa Fictícia Aurora",
            "company_segment": "Soluções criativas",
            "company_description": "Fale sobre a história, missão, visão, valores e diferenciais.",
            "company_products": "Design, Consultoria, Desenvolvimento Web",
            "company_target_audience": "Empresas, lojas, franquias e indústrias",
            "company_regions": "Cidade Alfa e regiões próximas",
            "company_business_hours": "Segunda a sexta, 08h às 18h",
            "company_payment_methods": "Pix, boleto, cartão e transferência",
            "company_policies": "Prazo de entrega em até 5 dias úteis. Garantia de 90 dias.",
            "company_info": "Empresa Fictícia Aurora",
            "active": True,
        })
        self.assertGreater(agent_id, 0)

        # 3. Retrieve
        retrieved = self.db.get_communication_agent(agent_id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved["name"], "Ana Assistente")
        self.assertEqual(retrieved["age"], "28")
        self.assertEqual(retrieved["gender"], "Feminino")
        self.assertEqual(retrieved["role"], "Consultora de Vendas")
        self.assertEqual(retrieved["tone"], "Acolhedor")
        self.assertEqual(retrieved["emoji_level"], "Normal")
        self.assertEqual(retrieved["company_name"], "Empresa Fictícia Aurora")
        self.assertEqual(retrieved["company_segment"], "Soluções criativas")
        self.assertEqual(retrieved["company_description"], "Fale sobre a história, missão, visão, valores e diferenciais.")
        self.assertEqual(retrieved["company_products"], "Design, Consultoria, Desenvolvimento Web")
        self.assertEqual(retrieved["company_target_audience"], "Empresas, lojas, franquias e indústrias")
        self.assertEqual(retrieved["company_regions"], "Cidade Alfa e regiões próximas")
        self.assertEqual(retrieved["company_business_hours"], "Segunda a sexta, 08h às 18h")
        self.assertEqual(retrieved["company_payment_methods"], "Pix, boleto, cartão e transferência")
        self.assertEqual(retrieved["company_policies"], "Prazo de entrega em até 5 dias úteis. Garantia de 90 dias.")
        self.assertEqual(retrieved["active"], 1)

        # 4. Update
        self.db.save_communication_agent({
            "id": agent_id,
            "name": "Ana Vendas Sênior",
            "age": "29",
            "gender": "Feminino",
            "role": "Líder de Vendas",
            "model_id": 1,
            "model_name": "OpenAI // gpt-4o",
            "tone": "Persuasivo",
            "formality": "Formal",
            "emoji_level": "Pouco",
            "response_style": "Consultivo",
            "language": "Português (Brasil)",
            "job_description": "Fechamento de contratos corporativos.",
            "responsibilities": '["Negociação avançada"]',
            "company_name": "Aurora Corp",
            "company_segment": "Tecnologia B2B",
            "company_description": "Soluções corporativas escaláveis.",
            "company_products": "Software Enterprise",
            "company_target_audience": "Grandes corporações",
            "company_regions": "Todo o Brasil",
            "company_business_hours": "24/7",
            "company_payment_methods": "Faturamento 30 dias",
            "company_policies": "SLA de 99.9%",
            "company_info": "Aurora Corp",
            "active": False,
        })
        updated = self.db.get_communication_agent(agent_id)
        self.assertEqual(updated["name"], "Ana Vendas Sênior")
        self.assertEqual(updated["role"], "Líder de Vendas")
        self.assertEqual(updated["company_name"], "Aurora Corp")
        self.assertEqual(updated["company_target_audience"], "Grandes corporações")
        self.assertEqual(updated["company_regions"], "Todo o Brasil")
        self.assertEqual(updated["active"], 0)

        # 5. Delete
        self.db.delete_communication_agent(agent_id)
        self.assertEqual(len(self.db.list_communication_agents()), 0)


if __name__ == "__main__":
    unittest.main()
