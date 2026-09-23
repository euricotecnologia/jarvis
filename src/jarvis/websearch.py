"""Busca na web usando so a biblioteca padrão (urllib + html.parser).

Sem dependencia compilada -- o `ddgs`/`primp` foi removido porque a política
de Controle de Aplicativo do Windows bloqueia a DLL nativa dele. Tenta o
DuckDuckGo (HTML e Lite) e cai para o Bing se preciso.
"""

from __future__ import annotations

import base64
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from html.parser import HTMLParser

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
_REGION_TO_DDG = {
    "br-pt": "br-pt", "pt-br": "br-pt", "pt": "br-pt",
    "us-en": "us-en", "en": "us-en", "": "wt-wt",
}


class SearchError(RuntimeError):
    """Falha previsivel da busca (vira contexto para o modelo)."""


@dataclass(frozen=True, slots=True)
class SearchHit:
    title: str
    url: str
    snippet: str


def _fetch(url: str, opener, *, data: bytes | None = None, timeout: int = 15) -> str:
    request = urllib.request.Request(
        url,
        data=data,
        headers={
            "User-Agent": _USER_AGENT,
            "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.6",
        },
    )
    with opener(request, timeout=timeout) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read(3_000_000).decode(charset, errors="replace")


def _unwrap_ddg(href: str) -> str:
    """Link do DDG vem embrulhado: //duckduckgo.com/l/?uddg=<url>&rut=..."""
    if "uddg=" in href:
        query = urllib.parse.urlparse(href).query or href.split("?", 1)[-1]
        params = urllib.parse.parse_qs(query)
        if params.get("uddg"):
            return params["uddg"][0]
    if href.startswith("//"):
        return "https:" + href
    return href


def _unwrap_bing(href: str) -> str:
    """Bing embrulha o link organico em /ck/a?...&u=a1<base64url>."""
    if "bing.com/ck/" not in href and not href.startswith("/ck/"):
        return href
    params = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
    raw = (params.get("u") or [""])[0]
    if raw.startswith("a1"):
        payload = raw[2:]
        payload += "=" * (-len(payload) % 4)
        try:
            return base64.urlsafe_b64decode(payload).decode("utf-8", "replace")
        except Exception:  # noqa: BLE001
            return href
    return href


class _DDGHtmlParser(HTMLParser):
    """Le os resultados de html.duckduckgo.com / lite.duckduckgo.com."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.hits: list[SearchHit] = []
        self._mode: str | None = None          # "title" | "snippet"
        self._href = ""
        self._title_parts: list[str] = []
        self._snippet_parts: list[str] = []
        self._pending_title = ""
        self._pending_href = ""

    def handle_starttag(self, tag, attrs):
        if tag != "a":
            return
        cls = dict(attrs).get("class", "") or ""
        href = dict(attrs).get("href", "") or ""
        if "result__a" in cls or "result-link" in cls:
            self._mode = "title"
            self._href = href
            self._title_parts = []
        elif "result__snippet" in cls or "result-snippet" in cls:
            self._mode = "snippet"
            self._snippet_parts = []

    def handle_data(self, data):
        if self._mode == "title":
            self._title_parts.append(data)
        elif self._mode == "snippet":
            self._snippet_parts.append(data)

    def handle_endtag(self, tag):
        if tag != "a" or self._mode is None:
            return
        if self._mode == "title":
            self._pending_title = "".join(self._title_parts).strip()
            self._pending_href = self._href
        elif self._mode == "snippet":
            snippet = " ".join("".join(self._snippet_parts).split())
            url = _unwrap_ddg(self._pending_href)
            if self._pending_title and url.startswith("http"):
                self.hits.append(
                    SearchHit(self._pending_title, url, snippet)
                )
            self._pending_title = ""
            self._pending_href = ""
        self._mode = None


class _BingParser(HTMLParser):
    """Fallback: resultados organicos do Bing (li.b_algo)."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.hits: list[SearchHit] = []
        self._depth_algo = 0
        self._in_h2 = False
        self._in_link = False
        self._in_p = False
        self._href = ""
        self._title: list[str] = []
        self._para: list[str] = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        cls = a.get("class", "") or ""
        if tag == "li" and "b_algo" in cls:
            self._depth_algo = 1
            self._href = ""
            self._title = []
            self._para = []
        elif self._depth_algo and tag == "li":
            self._depth_algo += 1
        elif self._depth_algo and tag == "h2":
            self._in_h2 = True
        elif self._depth_algo and tag == "a" and self._in_h2:
            self._in_link = True
            self._href = a.get("href", "") or self._href
        elif self._depth_algo and tag == "p":
            self._in_p = True

    def handle_data(self, data):
        if self._in_link:
            self._title.append(data)
        elif self._in_p:
            self._para.append(data)

    def handle_endtag(self, tag):
        if not self._depth_algo:
            return
        if tag == "a" and self._in_link:
            self._in_link = False
        elif tag == "h2":
            self._in_h2 = False
        elif tag == "p":
            self._in_p = False
        elif tag == "li":
            self._depth_algo -= 1
            if self._depth_algo == 0:
                title = " ".join("".join(self._title).split())
                para = " ".join("".join(self._para).split())
                url = _unwrap_bing(self._href)
                if title and url.startswith("http"):
                    self.hits.append(SearchHit(title, url, para))


def _dedup(hits: list[SearchHit], limit: int) -> list[SearchHit]:
    seen: set[str] = set()
    out: list[SearchHit] = []
    for hit in hits:
        key = hit.url.rstrip("/")
        if key in seen:
            continue
        seen.add(key)
        out.append(hit)
        if len(out) >= limit:
            break
    return out


def search(
    query: str,
    *,
    max_results: int = 5,
    region: str = "br-pt",
    opener=None,
    timeout: int = 15,
) -> list[SearchHit]:
    query = query.strip()
    if not query:
        raise SearchError("Consulta vazia.")
    opener = opener or urllib.request.urlopen
    max_results = max(1, min(int(max_results), 10))
    kl = _REGION_TO_DDG.get(region.lower(), "wt-wt")
    q = urllib.parse.quote_plus(query)

    attempts = (
        ("ddg-html", f"https://html.duckduckgo.com/html/?q={q}&kl={kl}", _DDGHtmlParser),
        ("bing", f"https://www.bing.com/search?q={q}&setlang=pt-br", _BingParser),
        ("ddg-lite", f"https://lite.duckduckgo.com/lite/?q={q}&kl={kl}", _DDGHtmlParser),
    )

    last_error: Exception | None = None
    for _name, url, parser_cls in attempts:
        try:
            html = _fetch(url, opener, timeout=timeout)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
            last_error = exc
            continue
        parser = parser_cls()
        try:
            parser.feed(html)
        except Exception as exc:  # noqa: BLE001 - HTML pode vir quebrado
            last_error = exc
            continue
        hits = _dedup(parser.hits, max_results)
        if hits:
            return hits

    if last_error is not None:
        raise SearchError(f"nenhum buscador respondeu ({last_error})")
    return []
