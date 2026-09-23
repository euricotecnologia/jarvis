import unittest
from unittest.mock import patch

from jarvis.config import AgentConfig
from jarvis.tools.calc import Calculadora
from jarvis.tools.context import ToolContext
from jarvis.tools.web import BuscarNaWeb, LerPaginaWeb, _TextExtractor


class CalculadoraTests(unittest.IsolatedAsyncioTestCase):
    async def _run(self, expr: str):
        return await Calculadora().run(
            {"expressao": expr}, ToolContext(config=AgentConfig(enabled=True))
        )

    async def test_arithmetic_and_functions(self) -> None:
        self.assertEqual((await self._run("2 + 3 * 4")).content, "2 + 3 * 4 = 14")
        self.assertTrue((await self._run("sqrt(16)")).content.endswith("= 4.0"))
        self.assertIn("3.14159", (await self._run("pi")).content)

    async def test_rejects_unsafe_input(self) -> None:
        for bad in ("__import__('os')", "open('x')", "1; import os", "x + 1"):
            result = await self._run(bad)
            self.assertFalse(result.ok, bad)


class TextExtractorTests(unittest.TestCase):
    def test_strips_html_and_scripts(self) -> None:
        parser = _TextExtractor()
        parser.feed(
            "<html><head><style>x{}</style></head><body>"
            "<script>var a=1</script><h1>Titulo</h1><p>Primeiro paragrafo.</p>"
            "<p>Segundo.</p></body></html>"
        )
        text = parser.text()
        self.assertIn("Titulo", text)
        self.assertIn("Primeiro paragrafo.", text)
        self.assertNotIn("var a", text)
        self.assertNotIn("x{}", text)


class WebToolTests(unittest.IsolatedAsyncioTestCase):
    def _ctx(self) -> ToolContext:
        return ToolContext(config=AgentConfig(enabled=True, browser=True))

    async def test_buscar_na_web_formats_results(self) -> None:
        from jarvis.websearch import SearchHit

        fake_hits = [
            SearchHit("Resultado 1", "https://a.com", "resumo um"),
            SearchHit("Resultado 2", "https://b.com", "resumo dois"),
        ]

        def fake_search(query, *, max_results=5, region="br-pt"):
            return fake_hits[:max_results]

        with patch("jarvis.websearch.search", fake_search):
            result = await BuscarNaWeb().run(
                {"consulta": "teste", "maximo": 2}, self._ctx()
            )
        self.assertTrue(result.ok)
        self.assertIn("Resultado 1", result.content)
        self.assertIn("https://b.com", result.content)

    async def test_buscar_na_web_reports_failure(self) -> None:
        from jarvis.websearch import SearchError

        def boom(*a, **k):
            raise SearchError("nenhum buscador respondeu")

        with patch("jarvis.websearch.search", boom):
            result = await BuscarNaWeb().run({"consulta": "x"}, self._ctx())
        self.assertFalse(result.ok)
        self.assertIn("falhou", result.content)

    async def test_ler_pagina_web_rejects_non_http(self) -> None:
        result = await LerPaginaWeb().run(
            {"url": "file:///c:/x.txt"}, self._ctx()
        )
        self.assertFalse(result.ok)


if __name__ == "__main__":
    unittest.main()
