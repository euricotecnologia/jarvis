from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)

DEFAULT_BRIDGE_PORT = 25874
BRIDGE_HOST = "127.0.0.1"


class WhatsAppManager:
    """Gerenciador do serviço local Baileys WhatsApp Bridge."""

    def __init__(
        self,
        base_dir: Path,
        port: int = DEFAULT_BRIDGE_PORT,
        on_status_changed: Callable[[dict[str, Any]], None] | None = None,
        on_log_added: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        self.base_dir = Path(base_dir)
        self.port = port
        self.bridge_dir = self.base_dir / "services" / "whatsapp_bridge"
        self.server_js = self.bridge_dir / "server.js"
        self.on_status_changed = on_status_changed
        self.on_log_added = on_log_added

        self._process: subprocess.Popen[str] | None = None
        self._running = False
        self._monitor_thread: threading.Thread | None = None
        self._last_status: dict[str, Any] = {
            "status": "disconnected",
            "qrCode": "",
            "user": None,
            "connected": False,
            "logs": [],
        }

    @property
    def base_url(self) -> str:
        return f"http://{BRIDGE_HOST}:{self.port}"

    def is_bridge_installed(self) -> bool:
        return (self.bridge_dir / "node_modules").is_dir() and self.server_js.is_file()

    def start_bridge(self) -> bool:
        """Inicia o processo Node.js em background e inicia monitoramento."""
        if self._process and self._process.poll() is None:
            return True

        if not self.server_js.exists():
            logger.error("Script da bridge não encontrado em %s", self.server_js)
            return False

        # Localiza o executável node
        node_exec = shutil.which("node") or "node"

        try:
            env = os.environ.copy()
            env["PORT"] = str(self.port)
            env["SESSION_DIR"] = str(self.base_dir / "data" / "whatsapp_session")

            # No Windows, oculta a janela de console do subprocesso
            creation_flags = 0
            if sys.platform == "win32":
                creation_flags = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]

            self._process = subprocess.Popen(
                [node_exec, str(self.server_js)],
                cwd=str(self.base_dir),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=creation_flags,
            )
            self._running = True

            # Inicia thread de monitoramento/polling de status
            self._monitor_thread = threading.Thread(
                target=self._monitor_loop, daemon=True, name="WhatsAppBridgeMonitor"
            )
            self._monitor_thread.start()
            logger.info("WhatsApp Bridge iniciada na porta %d (PID: %d)", self.port, self._process.pid)
            return True
        except Exception as exc:
            logger.exception("Falha ao iniciar WhatsApp Bridge: %s", exc)
            return False

    def stop_bridge(self) -> None:
        """Para o processo Node.js."""
        self._running = False
        if self._process:
            try:
                self._process.terminate()
                self._process.wait(timeout=3)
            except Exception:
                try:
                    self._process.kill()
                except Exception:
                    pass
            self._process = None
        self._last_status = {
            "status": "disconnected",
            "qrCode": "",
            "user": None,
            "connected": False,
            "logs": [],
        }

    def _http_request(
        self, endpoint: str, method: str = "GET", data: dict[str, Any] | None = None, timeout: float = 4.0
    ) -> dict[str, Any]:
        url = f"{self.base_url}{endpoint}"
        body_bytes = json.dumps(data).encode("utf-8") if data is not None else None
        headers = {"Content-Type": "application/json"} if data is not None else {}

        req = urllib.request.Request(url, data=body_bytes, headers=headers, method=method)
        with urllib.request.urlopen(req, timeout=timeout) as response:
            res_data = response.read().decode("utf-8")
            return json.loads(res_data) if res_data else {}

    def get_status(self) -> dict[str, Any]:
        """Obtém status atual da bridge."""
        try:
            data = self._http_request("/status", method="GET")
            self._last_status = data
            return data
        except Exception:
            return self._last_status

    def connect(self) -> dict[str, Any]:
        """Solicita inicialização / conexão com o WhatsApp."""
        if not self._process or self._process.poll() is not None:
            self.start_bridge()
            time.sleep(0.5)
        try:
            return self._http_request("/connect", method="POST", data={})
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def disconnect(self) -> dict[str, Any]:
        """Desconecta a sessão atual e limpa credenciais."""
        try:
            return self._http_request("/disconnect", method="POST", data={})
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def send_message(self, to: str, text: str) -> dict[str, Any]:
        """Envia mensagem para número de WhatsApp."""
        try:
            return self._http_request("/send", method="POST", data={"to": to, "text": text}, timeout=10.0)
        except urllib.error.HTTPError as err:
            try:
                err_body = err.read().decode("utf-8")
                return json.loads(err_body)
            except Exception:
                return {"success": False, "error": f"HTTP {err.code}: {err.reason}"}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def _monitor_loop(self) -> None:
        """Loop de background para manter o estado sincronizado."""
        last_notified_state = ""
        while self._running:
            try:
                if self._process and self._process.poll() is not None:
                    # Processo morreu inesperadamente
                    logger.warning("WhatsApp bridge terminou com código %s", self._process.poll())
                    self._last_status = {
                        "status": "disconnected",
                        "qrCode": "",
                        "user": None,
                        "connected": False,
                        "logs": [],
                    }
                    if self.on_status_changed:
                        self.on_status_changed(self._last_status)
                    break

                status = self.get_status()
                state_signature = f"{status.get('status')}:{bool(status.get('qrCode'))}:{status.get('user')}"
                if state_signature != last_notified_state:
                    last_notified_state = state_signature
                    if self.on_status_changed:
                        self.on_status_changed(status)
            except Exception:
                pass
            time.sleep(1.5)
