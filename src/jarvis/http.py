from __future__ import annotations

import asyncio
import json
import urllib.error
import urllib.request
from typing import Any, AsyncIterator, Iterator, Protocol

from jarvis.errors import ProviderError, ProviderUnavailable


class HttpClient(Protocol):
    async def request_json(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        payload: dict[str, Any] | None = None,
        timeout: float = 120,
    ) -> dict[str, Any]: ...

    def stream_sse(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        payload: dict[str, Any] | None = None,
        timeout: float = 300,
    ) -> AsyncIterator[str]: ...


class JsonHttpClient:
    async def request_json(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        payload: dict[str, Any] | None = None,
        timeout: float = 120,
    ) -> dict[str, Any]:
        return await asyncio.to_thread(
            self._request_json_sync, method, url, headers or {}, payload, timeout
        )

    @staticmethod
    def _request_json_sync(
        method: str,
        url: str,
        headers: dict[str, str],
        payload: dict[str, Any] | None,
        timeout: float,
    ) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        request_headers = {"Accept": "application/json", **headers}
        if body is not None:
            request_headers.setdefault("Content-Type", "application/json")
        request = urllib.request.Request(
            url=url, data=body, headers=request_headers, method=method.upper()
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw = response.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            try:
                parsed = json.loads(detail)
                detail = parsed.get("error", {}).get("message", detail)
            except (json.JSONDecodeError, AttributeError):
                pass
            error = ProviderError(f"HTTP {exc.code} em {url}: {detail}")
            error.status_code = exc.code  # type: ignore[attr-defined]
            raise error from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise ProviderUnavailable(f"Não foi possível acessar {url}: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise ProviderError(f"Resposta JSON invalida de {url}") from exc

    async def stream_sse(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        payload: dict[str, Any] | None = None,
        timeout: float = 300,
    ) -> AsyncIterator[str]:
        """Faz um POST e entrega o corpo de cada evento SSE (`data:`) do servidor.

        A leitura acontece numa thread para não travar o event loop; cada linha
        chega ao consumidor assíncrono por uma fila. `[DONE]` encerra o fluxo.
        """
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue[object] = asyncio.Queue(maxsize=256)
        done = object()

        def worker() -> None:
            try:
                for line in self._stream_sse_sync(
                    method, url, headers or {}, payload, timeout
                ):
                    loop.call_soon_threadsafe(queue.put_nowait, line)
            except BaseException as exc:  # propaga a exceção ao consumidor
                loop.call_soon_threadsafe(queue.put_nowait, exc)
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, done)

        future = loop.run_in_executor(None, worker)
        try:
            while True:
                item = await queue.get()
                if item is done:
                    break
                if isinstance(item, BaseException):
                    raise item
                yield item  # type: ignore[misc]
        finally:
            future.cancel()

    @staticmethod
    def _stream_sse_sync(
        method: str,
        url: str,
        headers: dict[str, str],
        payload: dict[str, Any] | None,
        timeout: float,
    ) -> Iterator[str]:
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
        request_headers = {"Accept": "text/event-stream", **headers}
        if body is not None:
            request_headers.setdefault("Content-Type", "application/json")
        request = urllib.request.Request(
            url=url, data=body, headers=request_headers, method=method.upper()
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                for raw in response:
                    line = raw.decode("utf-8", errors="replace").strip()
                    if not line or line.startswith(":"):
                        continue
                    if line.startswith("data:"):
                        data = line[5:].strip()
                        if data == "[DONE]":
                            return
                        yield data
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            try:
                detail = json.loads(detail).get("error", {}).get("message", detail)
            except (json.JSONDecodeError, AttributeError):
                pass
            raise ProviderError(f"HTTP {exc.code} em {url}: {detail}") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise ProviderUnavailable(f"Não foi possível acessar {url}: {exc}") from exc

