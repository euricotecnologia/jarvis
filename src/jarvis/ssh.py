"""Executa comandos numa VPS/servidor remoto por SSH.

Usa um cliente OpenSSH ja pronto -- NUNCA baixa nem instala nada. Ordem de
busca: `tools/ssh/ssh.exe` (copia embutida no projeto) -> o OpenSSH do
Windows -> o do Git -> o do PATH. Sem biblioteca de cripto compilada (que a
política de Controle de Aplicativo costuma bloquear). Autenticação por
chave, ssh-agent ou senha (via SSH_ASKPASS, sem gravar a senha em arquivo).
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from jarvis.errors import JarvisError
from jarvis.models import Server

# copia embutida: <raiz-do-projeto>/tools/ssh/ssh.exe
_VENDORED_SSH = Path(__file__).resolve().parents[2] / "tools" / "ssh" / (
    "ssh.exe" if sys.platform == "win32" else "ssh"
)
_SYSTEM_CANDIDATES = (
    r"C:\Windows\System32\OpenSSH\ssh.exe",
    r"C:\Program Files\Git\usr\bin\ssh.exe",
    r"C:\Program Files\OpenSSH\ssh.exe",
)
_cached_ssh: str | None = None


class SSHError(JarvisError):
    """Falha previsivel ao falar com o servidor remoto."""


@dataclass(frozen=True, slots=True)
class RemoteResult:
    exit_code: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.exit_code == 0


def ssh_available() -> bool:
    try:
        return bool(_ssh_executable())
    except SSHError:
        return False


def _ssh_executable() -> str:
    global _cached_ssh
    if _cached_ssh and Path(_cached_ssh).exists():
        return _cached_ssh
    if _VENDORED_SSH.exists():
        _cached_ssh = str(_VENDORED_SSH)
        return _cached_ssh
    for candidate in _SYSTEM_CANDIDATES:
        if Path(candidate).exists():
            _cached_ssh = candidate
            return candidate
    found = shutil.which("ssh")
    if found:
        _cached_ssh = found
        return found
    raise SSHError(
        "cliente OpenSSH não encontrado. Copie um ssh.exe para "
        "tools/ssh/ ou adicione o 'Cliente OpenSSH' em Configurações > "
        "Aplicativos > Recursos opcionais do Windows."
    )


def _no_window() -> int:
    return getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0


def _base_argv(server: Server, *, connect_timeout: int = 12) -> list[str]:
    argv = [
        _ssh_executable(),
        "-p", str(server.port or 22),
        "-o", f"ConnectTimeout={connect_timeout}",
        "-o", "StrictHostKeyChecking=accept-new",
        "-o", "NumberOfPasswordPrompts=1",
        "-o", "PreferredAuthentications="
        + ("password,keyboard-interactive" if server.auth == "password"
           else "publickey"),
    ]
    if server.auth != "password":
        argv += ["-o", "BatchMode=yes"]
    if server.auth == "key" and server.key_path.strip():
        argv += ["-i", os.path.expanduser(server.key_path.strip())]
    host = server.host.strip()
    user = server.user.strip()
    argv.append(f"{user}@{host}" if user else host)
    return argv


def _write_askpass(python_exe: str) -> str:
    """Cria um .cmd temporario que imprime a senha vinda de JARVIS_SSH_PW.

    A senha NUNCA entra no arquivo -- so no ambiente do processo filho.
    """
    handle = tempfile.NamedTemporaryFile(
        "w", suffix=".cmd", delete=False, encoding="ascii"
    )
    handle.write("@echo off\r\n")
    handle.write(
        f'"{python_exe}" -c '
        '"import os,sys;sys.stdout.write(os.environ.get(\'JARVIS_SSH_PW\',\'\'))"\r\n'
    )
    handle.close()
    return handle.name


def run_remote(
    server: Server,
    command: str,
    *,
    timeout: float = 60.0,
    password: str | None = None,
) -> RemoteResult:
    command = (command or "").strip()
    if not command:
        raise SSHError("comando vazio")
    if not server.host.strip() or not server.user.strip():
        raise SSHError("servidor sem host ou usuário configurado")

    argv = _base_argv(server)
    argv.append(command)

    env = dict(os.environ)
    helper: str | None = None
    try:
        if server.auth == "password":
            if not password:
                raise SSHError("senha do servidor não informada")
            helper = _write_askpass(sys.executable or "python")
            env["SSH_ASKPASS"] = helper
            env["SSH_ASKPASS_REQUIRE"] = "force"
            env["JARVIS_SSH_PW"] = password
            env.setdefault("DISPLAY", "localhost:0")

        try:
            completed = subprocess.run(
                argv,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env,
                creationflags=_no_window(),
                stdin=subprocess.DEVNULL,
            )
        except subprocess.TimeoutExpired as exc:
            raise SSHError(
                f"o comando remoto passou de {timeout:.0f}s e foi encerrado"
            ) from exc
        except OSError as exc:
            raise SSHError(f"não consegui executar o ssh: {exc}") from exc
    finally:
        if helper:
            try:
                os.unlink(helper)
            except OSError:
                pass

    return RemoteResult(
        exit_code=completed.returncode,
        stdout=(completed.stdout or "").strip(),
        stderr=(completed.stderr or "").strip(),
    )


def test_connection(server: Server, *, password: str | None = None) -> RemoteResult:
    """Comando inofensivo so para validar host/usuário/chave/senha."""
    return run_remote(
        server,
        "echo jarvis-ssh-ok; hostname; (uname -sr || ver) 2>/dev/null",
        timeout=20.0,
        password=password,
    )
