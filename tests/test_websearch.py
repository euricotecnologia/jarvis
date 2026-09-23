import io
import unittest

from jarvis import websearch

_DDG_HTML = """
<html><body>
<div class="result results_links results_links_deep web-result">
  <h2 class="result__title">
    <a rel="nofollow" class="result__a"
       href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fexemplo.com%2Fartigo&amp;rut=abc">
       Primeiro Resultado &amp; Cia</a>
  </h2>
  <a class="result__url" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fexemplo.com">exemplo.com</a>
  <a class="result__snippet" href="//duckduckgo.com/l/?uddg=x">
     Um <b>resumo</b> com acento: informacao util.</a>
</div>
<div class="result">
  <h2><a class="result__a"
       href="//duckduckgo.com/l/?uddg=https%3A%2F%2Foutro.org%2Fp">Segundo</a></h2>
  <a class="result__snippet" href="#">Outro resumo aqui.</a>
</div>
</body></html>
"""

_BING_HTML = """
<html><body><ol id="b_results">
<li class="b_algo"><h2><a href="https://www.bing.com/ck/a?!&&p=1&u=a1aHR0cHM6Ly9iaW5nLXJlcy5jb20vcA&ntb=1">
  Titulo Bing</a></h2><div class="b_caption"><p>Resumo do bing.</p></div></li>
<li class="b_algo"><h2><a href="https://direto.com/x">Direto</a></h2>
  <p>Sem redirecionamento.</p></li>
</ol></body></html>
"""


class _Resp:
    def __init__(self, text: str) -> None:
        self._data = text.encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self, *a):
        return self._data

    @property
    def headers(self):
        class H:
            @staticmethod
            def get_content_charset():
                return "utf-8"

        return H()


def _opener_for(mapping: dict):
    def opener(request, timeout=0):
        for fragment, html in mapping.items():
            if fragment in request.full_url:
                if html is None:
                    raise OSError("boom")
                return _Resp(html)
        return _Resp("<html></html>")

    return opener


class DDGParseTests(unittest.TestCase):
    def test_parses_ddg_html_and_unwraps_links(self) -> None:
        hits = websearch.search(
            "teste", opener=_opener_for({"duckduckgo.com/html": _DDG_HTML})
        )
        self.assertEqual(len(hits), 2)
        self.assertEqual(hits[0].title, "Primeiro Resultado & Cia")
        self.assertEqual(hits[0].url, "https://exemplo.com/artigo")
        self.assertIn("informacao util", hits[0].snippet)
        self.assertEqual(hits[1].url, "https://outro.org/p")

    def test_falls_back_to_bing_when_ddg_empty(self) -> None:
        hits = websearch.search(
            "teste",
            opener=_opener_for(
                {"duckduckgo.com/html": "<html></html>", "bing.com": _BING_HTML}
            ),
        )
        self.assertEqual(hits[0].title, "Titulo Bing")
        self.assertEqual(hits[0].url, "https://bing-res.com/p")
        self.assertEqual(hits[1].url, "https://direto.com/x")

    def test_raises_search_error_when_all_fail(self) -> None:
        with self.assertRaises(websearch.SearchError):
            websearch.search(
                "teste",
                opener=_opener_for(
                    {"duckduckgo": None, "bing.com": None}
                ),
            )

    def test_empty_query_rejected(self) -> None:
        with self.assertRaises(websearch.SearchError):
            websearch.search("   ")

    def test_respects_max_results(self) -> None:
        hits = websearch.search(
            "teste", max_results=1,
            opener=_opener_for({"duckduckgo.com/html": _DDG_HTML}),
        )
        self.assertEqual(len(hits), 1)


if __name__ == "__main__":
    unittest.main()
