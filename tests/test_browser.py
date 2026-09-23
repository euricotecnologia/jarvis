import unittest
from unittest.mock import patch

from jarvis.config import AgentConfig
from jarvis.tools.browser import AbrirSite, PesquisarWeb, _normalize_url
from jarvis.tools.context import ToolContext
from jarvis.tools.registry import build_tools


class NormalizeUrlTests(unittest.TestCase):
    def test_alias_full_url_and_bare_domain(self) -> None:
        self.assertEqual(_normalize_url("youtube"), "https://www.youtube.com")
        self.assertEqual(
            _normalize_url("https://example.com/x"), "https://example.com/x"
        )
        self.assertEqual(
            _normalize_url("youtube.com/feed"), "https://youtube.com/feed"
        )

    def test_rejects_non_web_schemes_and_garbage(self) -> None:
        self.assertIsNone(_normalize_url("file:///etc/passwd"))
        self.assertIsNone(_normalize_url("javascript:alert(1)"))
        self.assertIsNone(_normalize_url("nao e url"))
        self.assertIsNone(_normalize_url(""))


class BrowserToolTests(unittest.IsolatedAsyncioTestCase):
    def _ctx(self) -> ToolContext:
        return ToolContext(config=AgentConfig(enabled=True, browser=True))

    async def test_abrir_site_opens_default_browser(self) -> None:
        with patch("jarvis.tools.browser.webbrowser.open", return_value=True) as opened:
            result = await AbrirSite().run({"endereco": "youtube"}, self._ctx())
        self.assertTrue(result.ok)
        opened.assert_called_once_with("https://www.youtube.com", new=2)

    async def test_abrir_site_rejects_bad_address(self) -> None:
        with patch("jarvis.tools.browser.webbrowser.open") as opened:
            result = await AbrirSite().run({"endereco": "file:///c:/x"}, self._ctx())
        self.assertFalse(result.ok)
        opened.assert_not_called()

    async def test_pesquisar_web_youtube_builds_search_url(self) -> None:
        with patch("jarvis.tools.browser.webbrowser.open", return_value=True) as opened:
            result = await PesquisarWeb().run(
                {"consulta": "receita de pão", "site": "youtube"}, self._ctx()
            )
        self.assertTrue(result.ok)
        opened.assert_called_once_with(
            "https://www.youtube.com/results?search_query=receita+de+p%C3%A3o", new=2
        )

    async def test_pesquisar_web_defaults_to_google(self) -> None:
        with patch("jarvis.tools.browser.webbrowser.open", return_value=True) as opened:
            await PesquisarWeb().run({"consulta": "clima hoje"}, self._ctx())
        url = opened.call_args.args[0]
        self.assertTrue(url.startswith("https://www.google.com/search?q="))

    async def test_pesquisar_web_unknown_site_errors(self) -> None:
        with patch("jarvis.tools.browser.webbrowser.open") as opened:
            result = await PesquisarWeb().run(
                {"consulta": "x", "site": "orkut"}, self._ctx()
            )
        self.assertFalse(result.ok)
        opened.assert_not_called()


class RegistryTests(unittest.TestCase):
    def test_browser_tools_gated_by_permission(self) -> None:
        without = {t.name for t in build_tools(AgentConfig(enabled=True))}
        self.assertNotIn("abrir_site", without)

        with_browser = {
            t.name for t in build_tools(AgentConfig(enabled=True, browser=True))
        }
        self.assertIn("abrir_site", with_browser)
        self.assertIn("pesquisar_web", with_browser)


if __name__ == "__main__":
    unittest.main()
