from __future__ import annotations

import base64
import os
import sys

from jarvis.database import Database

# Segredos ficam na tabela `settings` do SQLite, sob este prefixo, cifrados.
_KEY_PREFIX = "secret::"
_LEGACY_SERVICE_NAME = "Jarvis Personal"


def _encrypt(value: str) -> str:
    raw = value.encode("utf-8")
    if sys.platform == "win32":
        try:  # DPAPI: so o próprio usuário do Windows consegue decifrar
            import win32crypt

            blob = win32crypt.CryptProtectData(raw, "jarvis", None, None, None, 0)
            return "dpapi:" + base64.b64encode(blob).decode("ascii")
        except Exception:
            pass
    return "b64:" + base64.b64encode(raw).decode("ascii")


def _decrypt(stored: str) -> str | None:
    scheme, _, payload = stored.partition(":")
    try:
        blob = base64.b64decode(payload.encode("ascii"))
        if scheme == "dpapi":
            import win32crypt

            _description, data = win32crypt.CryptUnprotectData(
                blob, None, None, None, 0
            )
            return data.decode("utf-8")
        if scheme == "b64":
            return blob.decode("utf-8")
    except Exception:
        return None
    return None


def encrypt_value(value: str) -> str:
    """Cifra um segredo avulso (ex.: senha de SSH) para guardar no banco."""
    return _encrypt(value)


def decrypt_value(stored: str) -> str | None:
    """Decifra o que `encrypt_value` gerou. None se não der."""
    if not stored:
        return None
    return _decrypt(stored)


def _read_legacy_keyring(name: str) -> str | None:
    try:
        import keyring

        return keyring.get_password(_LEGACY_SERVICE_NAME, name)
    except Exception:
        return None


def restore_secret_to_environment(database: Database, name: str) -> bool:
    """Carrega o segredo do banco para `os.environ`, se ainda não estiver la."""
    if os.environ.get(name):
        return True
    stored = database.get_setting(_KEY_PREFIX + name)
    if isinstance(stored, str) and stored:
        value = _decrypt(stored)
        if value:
            os.environ[name] = value
            return True
    # Migração única: chave que ficou no Gerenciador de Credenciais do Windows.
    legacy = _read_legacy_keyring(name)
    if legacy:
        save_secret(database, name, legacy)
        return True
    return False


def save_secret(database: Database, name: str, value: str) -> None:
    cleaned = value.strip()
    if not cleaned:
        return
    database.set_setting(_KEY_PREFIX + name, _encrypt(cleaned))
    os.environ[name] = cleaned


def delete_secret(database: Database, name: str) -> None:
    database.delete_setting(_KEY_PREFIX + name)
    os.environ.pop(name, None)
    try:  # limpa também qualquer residuo da versão antiga
        import keyring

        keyring.delete_password(_LEGACY_SERVICE_NAME, name)
    except Exception:
        pass


def secret_configured(database: Database, name: str) -> bool:
    if os.environ.get(name):
        return True
    stored = database.get_setting(_KEY_PREFIX + name)
    return isinstance(stored, str) and bool(stored)
