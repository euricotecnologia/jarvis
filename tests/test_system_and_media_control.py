from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from jarvis.config import AgentConfig
from jarvis.database import Database
from jarvis.models import Message
from jarvis.tools.context import ToolContext
from jarvis.tools.media_control import (
    AjustarVolume,
    ControleReproducao,
    TocarMusicaOuVideo,
)
from jarvis.tools.memory_recall import (
    ConsultarHistoricoConversas,
    ConsultarMemoriaLongoPrazo,
)
from jarvis.tools.registry import build_tools
from jarvis.tools.system_control import (
    AbrirAplicativo,
    ControleConfiguracoesSistema,
    GerenciarJanelas,
)


class TestSystemAndMediaControl(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_jarvis.db"
        self.db = Database(self.db_path)
        self.db.initialize()
        self.context = ToolContext(
            config=AgentConfig(),
            confirm=AsyncMock(return_value=True),
            database=self.db,
        )

    async def asyncTearDown(self) -> None:
        self.temp_dir.cleanup()

    async def test_search_conversation_history(self) -> None:
        conv_id = self.db.create_conversation("Desenvolvimento Jarvis")
        self.db.add_message(conv_id, Message(role="user", content="Precisamos implementar o controle de mídia e janelas."))
        self.db.add_message(conv_id, Message(role="assistant", content="Perfeito, criaremos as ferramentas de sistema."))

        # 1. Test database search
        results = self.db.search_conversation_messages("mídia")
        self.assertEqual(len(results), 1)
        self.assertIn("controle de mídia", results[0]["content"])

        # 2. Test tool execution
        tool = ConsultarHistoricoConversas()
        output = await tool.run({"termo_busca": "janelas"}, self.context)
        self.assertIn("janelas", output)
        self.assertIn("USUÁRIO", output)

    async def test_memory_recall_tool(self) -> None:
        self.db.save_user_memory({
            "category": "regra",
            "key": "regra_codigo",
            "content": "Sempre escrever testes unitários para cada funcionalidade.",
            "confidence": 1.0,
        })
        tool = ConsultarMemoriaLongoPrazo()
        output = await tool.run({"categoria": "regra"}, self.context)
        self.assertIn("Sempre escrever testes", output)

    @patch("subprocess.Popen")
    @patch("os.startfile", create=True)
    async def test_open_application(self, mock_startfile: MagicMock, mock_popen: MagicMock) -> None:
        tool = AbrirAplicativo()
        res = await tool.run({"nome_aplicativo": "vscode"}, self.context)
        self.assertIn("sucesso", res)

    @patch("os.system")
    async def test_window_management(self, mock_os_system: MagicMock) -> None:
        tool = GerenciarJanelas()
        res = await tool.run({"acao": "minimizar_tudo"}, self.context)
        self.assertIn("minimizadas", res)

    @patch("os.system")
    async def test_system_settings_control(self, mock_os_system: MagicMock) -> None:
        tool = ControleConfiguracoesSistema()
        res = await tool.run({"comando": "abrir_configuracoes"}, self.context)
        self.assertIn("Configurações", res)

    @patch("jarvis.tools.media_control._send_media_key")
    async def test_media_playback_control(self, mock_send_key: MagicMock) -> None:
        tool = ControleReproducao()
        res = await tool.run({"acao": "play_pause"}, self.context)
        self.assertIn("acionado", res)
        mock_send_key.assert_called()

    @patch("jarvis.tools.media_control._send_media_key")
    async def test_volume_adjustment(self, mock_send_key: MagicMock) -> None:
        tool = AjustarVolume()
        res = await tool.run({"acao": "aumentar_volume"}, self.context)
        self.assertIn("aumentado", res)
        mock_send_key.assert_called()

    @patch("os.system")
    async def test_play_music_youtube(self, mock_os_system: MagicMock) -> None:
        tool = TocarMusicaOuVideo()
        res = await tool.run({"termo_busca": "Queen Bohemian Rhapsody", "plataforma": "youtube"}, self.context)
        self.assertIn("YouTube", res)

    async def test_str_returning_tool_through_agent(self) -> None:
        """Ferramentas que devolvem str (não ToolResult) não podem quebrar o agente."""
        from jarvis.agent import ToolAgent
        from jarvis.models import LLMResponse, ToolCall

        class FakeRouter:
            def __init__(self) -> None:
                self.calls = 0

            async def chat(self, request, provider_name=None):  # noqa: ANN001
                self.calls += 1
                if self.calls == 1:
                    return LLMResponse(
                        provider="fake", model="m", content="",
                        tool_calls=[ToolCall(
                            id="c1", name="abrir_aplicativo",
                            arguments={"nome_aplicativo": "calculadora"},
                        )],
                    )
                return LLMResponse(
                    provider="fake", model="m",
                    content="Pronto, abri a calculadora.", tool_calls=[],
                )

        agent = ToolAgent(FakeRouter(), AgentConfig(enabled=True))
        kinds = []
        with patch("os.startfile", create=True), patch("subprocess.Popen"):
            async for ev in agent.run_stream(
                [Message(role="user", content="abra a calculadora")],
                [AbrirAplicativo()],
                self.context,
            ):
                kinds.append((ev.kind, ev.text))
        # nenhum evento de erro; a nota deve reportar sucesso
        self.assertNotIn("error", [k for k, _ in kinds])
        self.assertTrue(any(k == "notice" and "ok" in t for k, t in kinds))

    def test_tools_registered_in_build_tools(self) -> None:
        tools = build_tools(AgentConfig())
        names = [t.name for t in tools]
        self.assertIn("consultar_historico_conversas", names)
        self.assertIn("consultar_memoria_longo_prazo", names)
        self.assertIn("abrir_aplicativo", names)
        self.assertIn("gerenciar_janelas", names)
        self.assertIn("controle_configuracoes_sistema", names)
        self.assertIn("controle_reproducao", names)
        self.assertIn("ajustar_volume", names)
        self.assertIn("tocar_musica_ou_video", names)


if __name__ == "__main__":
    unittest.main()
