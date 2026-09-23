from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from jarvis.config import AgentConfig
from jarvis.database import Database
from jarvis.tools.browser import GerenciarGuiasNavegador
from jarvis.tools.context import ToolContext
from jarvis.tools.filesystem_manager import (
    CompactarDescompactar,
    OrganizarPasta,
    PesquisarArquivosInteligente,
    RenomearArquivosLote,
)
from jarvis.tools.registry import build_tools
from jarvis.tools.screen_reader import LerEAnalisarTela


class TestFileBrowserScreenTools(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root_path = Path(self.temp_dir.name)
        self.db_path = self.root_path / "test_jarvis.db"
        self.db = Database(self.db_path)
        self.db.initialize()
        self.context = ToolContext(
            config=AgentConfig(),
            confirm=AsyncMock(return_value=True),
            database=self.db,
            describe_image=MagicMock(return_value="A tela mostra o VS Code aberto com o projeto Jarvis."),
        )

    async def asyncTearDown(self) -> None:
        self.temp_dir.cleanup()

    async def test_organize_folder(self) -> None:
        test_folder = self.root_path / "Downloads"
        test_folder.mkdir()
        (test_folder / "foto.png").write_text("dummy")
        (test_folder / "relatorio.pdf").write_text("dummy")
        (test_folder / "script.py").write_text("print('hello')")

        tool = OrganizarPasta()
        res = await tool.run({"caminho_pasta": str(test_folder), "modo": "categoria"}, self.context)
        self.assertIn("organizado", res)
        self.assertTrue((test_folder / "Imagens" / "foto.png").exists())
        self.assertTrue((test_folder / "Documentos" / "relatorio.pdf").exists())
        self.assertTrue((test_folder / "Codigos" / "script.py").exists())

    async def test_smart_file_search(self) -> None:
        search_folder = self.root_path / "Docs"
        search_folder.mkdir()
        (search_folder / "contrato_2026.pdf").write_text("Conteúdo confidencial do contrato.")
        (search_folder / "anotacoes.txt").write_text("Notas rápidas de reuniões.")

        tool = PesquisarArquivosInteligente()
        res = await tool.run({
            "caminho_pasta": str(search_folder),
            "termo_nome": "contrato",
            "extensoes": [".pdf"],
        }, self.context)
        self.assertIn("contrato_2026.pdf", res)

    async def test_zip_and_unzip(self) -> None:
        data_folder = self.root_path / "data"
        data_folder.mkdir()
        (data_folder / "arquivo1.txt").write_text("teste 1")
        (data_folder / "arquivo2.txt").write_text("teste 2")

        # 1. Compactar
        zip_tool = CompactarDescompactar()
        zip_dest = self.root_path / "pacote.zip"
        res_zip = await zip_tool.run({
            "acao": "compactar",
            "origem": str(data_folder),
            "destino": str(zip_dest),
        }, self.context)
        self.assertIn("sucesso", res_zip)
        self.assertTrue(zip_dest.exists())

        # 2. Descompactar
        extract_folder = self.root_path / "extraido"
        res_unzip = await zip_tool.run({
            "acao": "descompactar",
            "origem": str(zip_dest),
            "destino": str(extract_folder),
        }, self.context)
        self.assertIn("extraído", res_unzip)
        self.assertTrue((extract_folder / "arquivo1.txt").exists())

    async def test_batch_rename(self) -> None:
        rename_folder = self.root_path / "Fotos"
        rename_folder.mkdir()
        (rename_folder / "img_a.png").write_text("1")
        (rename_folder / "img_b.png").write_text("2")

        tool = RenomearArquivosLote()
        res = await tool.run({
            "caminho_pasta": str(rename_folder),
            "prefixo": "Viagem_",
            "numerar_sequencial": True,
        }, self.context)
        self.assertIn("renomeado", res)
        self.assertTrue((rename_folder / "Viagem_img_a_01.png").exists())

    @patch("ctypes.windll.user32.keybd_event", create=True)
    async def test_browser_tab_management(self, mock_keybd: MagicMock) -> None:
        tool = GerenciarGuiasNavegador()
        res = await tool.execute({"acao": "nova_guia"}, self.context)
        self.assertTrue(res.ok)
        self.assertIn("Nova guia", res.content)

    @patch("jarvis.screenshot.capture_screen", return_value=b"fake_jpeg")
    @patch("jarvis.screenshot.available", return_value=True)
    async def test_screen_reader_tool(self, mock_avail: MagicMock, mock_capture: MagicMock) -> None:
        tool = LerEAnalisarTela()
        res = await tool.execute({"pergunta_ou_foco": "O que está aberto?"}, self.context)
        self.assertTrue(res.ok)
        self.assertIn("analisada com sucesso", res.content)
        self.assertIn("VS Code", res.content)

    def test_registry_contains_all_new_tools(self) -> None:
        tools = build_tools(AgentConfig(browser=True))
        names = [t.name for t in tools]
        self.assertIn("organizar_pasta", names)
        self.assertIn("pesquisar_arquivos_inteligente", names)
        self.assertIn("compactar_descompactar", names)
        self.assertIn("renomear_arquivos_lote", names)
        self.assertIn("gerenciar_guias_navegador", names)
        self.assertIn("ler_e_analisar_tela", names)


if __name__ == "__main__":
    unittest.main()
