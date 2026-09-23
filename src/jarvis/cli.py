from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from jarvis.assistant import JarvisAssistant
from jarvis.config import AppConfig, load_config
from jarvis.database import Database
from jarvis.errors import JarvisError
from jarvis.providers.factory import create_provider


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="jarvis", description="Jarvis pessoal, local-first e modular."
    )
    parser.add_argument("--config", type=Path, help="Caminho do arquivo TOML.")
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("init-db", help="Cria ou atualiza o banco SQLite.")
    commands.add_parser("providers", help="Lista os provedores configurados.")
    commands.add_parser("doctor", help="Testa a conexão com os provedores.")
    commands.add_parser("gui", help="Abre a interface grafica futurista.")

    chat = commands.add_parser("chat", help="Inicia uma conversa.")
    chat.add_argument("prompt", nargs="?", help="Pergunta única; omita para modo interativo.")
    chat.add_argument("--provider", help="Forca um provedor especifico.")
    return parser


def _print_providers(config: AppConfig) -> None:
    print("PROVEDOR     ATIVO  TIPO              MODELO")
    for item in config.providers.values():
        print(
            f"{item.name:<12} {'sim' if item.enabled else 'nao':<6} "
            f"{item.kind:<17} {item.model}"
        )


async def _doctor(config: AppConfig) -> int:
    failures = 0
    for item in config.providers.values():
        if not item.enabled:
            print(f"[--] {item.name}: desativado")
            continue
        provider = create_provider(item)
        ok, detail = await provider.health_check()
        print(f"[{'OK' if ok else 'ERRO'}] {item.name}: {detail}")
        failures += int(not ok)
    return 1 if failures else 0


async def _chat(config: AppConfig, prompt: str | None, provider: str | None) -> int:
    assistant = JarvisAssistant(config)
    await assistant.initialize()
    conversation_id: int | None = None

    async def confirm(description: str) -> bool:
        answer = await asyncio.to_thread(
            input, f"\n[confirmar] {description}\nAprovar? (s/N) "
        )
        return answer.strip().lower() in {"s", "sim", "y", "yes"}

    def on_event(kind: str, message: str) -> None:
        marker = {"tool": "->", "notice": "  ", "error": "!!"}.get(kind, "  ")
        print(f"\n{marker} {message}", flush=True)

    async def send(text: str) -> None:
        nonlocal conversation_id
        print("\nJarvis:", end=" ", flush=True)
        received = False
        async for delta in assistant.ask_stream(
            text,
            conversation_id=conversation_id,
            provider_name=provider,
            confirm=confirm,
            on_event=on_event,
        ):
            received = True
            print(delta, end="", flush=True)
        conversation_id = assistant.active_conversation_id
        reply = assistant.last_stream
        if reply is not None:
            print(f"\n[{reply.response.provider}/{reply.response.model}]")
        elif not received:
            print("(o modelo não retornou texto)")
        else:
            print()

    if prompt:
        await send(prompt)
        return 0

    print("Jarvis iniciado. Digite 'sair' para encerrar.")
    while True:
        try:
            text = input("\nVoce: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if text.lower() in {"sair", "exit", "quit"}:
            break
        if text:
            await send(text)
    return 0


async def async_main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = load_config(args.config)
    if args.command == "init-db":
        database = Database(config.database_path)
        await asyncio.to_thread(database.initialize)
        await asyncio.to_thread(database.sync_providers, config.providers)
        print(f"Banco inicializado em {config.database_path}")
        return 0
    if args.command == "providers":
        _print_providers(config)
        return 0
    if args.command == "doctor":
        return await _doctor(config)
    if args.command == "gui":
        try:
            from jarvis.gui import run_gui
        except ImportError as exc:
            raise JarvisError(
                "A interface requer PySide6. Instale com: "
                ".\\.venv\\Scripts\\python.exe -m pip install -e '.[gui]'"
            ) from exc
        return run_gui(config)
    if args.command == "chat":
        return await _chat(config, args.prompt, args.provider)
    return 2


def main(argv: list[str] | None = None) -> None:
    try:
        raise SystemExit(asyncio.run(async_main(argv)))
    except JarvisError as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
