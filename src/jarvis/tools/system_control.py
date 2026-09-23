from __future__ import annotations

import ctypes
import os
import shutil
import subprocess
import sys
from typing import TYPE_CHECKING, Any

from jarvis.tools.base import Tool

if TYPE_CHECKING:
    from jarvis.tools.context import ToolContext

# Mapeamento rápido de aplicativos conhecidos no Windows
APP_MAP = {
    "vscode": "code",
    "vs code": "code",
    "visual studio code": "code",
    "code": "code",
    "bloco de notas": "notepad",
    "notepad": "notepad",
    "calculadora": "calc",
    "calc": "calc",
    "navegador": "chrome",
    "chrome": "chrome",
    "google chrome": "chrome",
    "edge": "msedge",
    "microsoft edge": "msedge",
    "brave": "brave",
    "firefox": "firefox",
    "explorer": "explorer",
    "explorador de arquivos": "explorer",
    "pastas": "explorer",
    "spotify": "spotify",
    "terminal": "wt",
    "windows terminal": "wt",
    "powershell": "powershell",
    "cmd": "cmd",
    "prompt de comando": "cmd",
    "gerenciador de tarefas": "taskmgr",
    "taskmgr": "taskmgr",
    "configuracoes": "ms-settings:",
    "configurações": "ms-settings:",
    "settings": "ms-settings:",
    "painel de controle": "control",
    "control panel": "control",
    "discord": "discord",
    "telegram": "telegram",
    "slack": "slack",
    "word": "winword",
    "excel": "excel",
    "powerpoint": "powerpnt",
    "paint": "mspaint",
}


class AbrirAplicativo(Tool):
    """Abre aplicativos e programas no Windows com facilidade."""

    name = "abrir_aplicativo"
    description = (
        "Abre um aplicativo ou programa instalado no computador "
        "(ex: VS Code, Chrome, Bloco de Notas, Calculadora, Spotify, Explorador de Arquivos, Terminal, etc.)."
    )
    parameters = {
        "type": "object",
        "properties": {
            "nome_aplicativo": {
                "type": "string",
                "description": "Nome do aplicativo a abrir (ex: 'vscode', 'chrome', 'calculadora', 'spotify', 'bloco de notas').",
            },
            "argumentos": {
                "type": "string",
                "description": "Argumentos ou arquivo a abrir opcionalmente.",
            },
        },
        "required": ["nome_aplicativo"],
    }

    async def run(self, args: dict[str, Any], context: ToolContext) -> str:
        app_name = str(args.get("nome_aplicativo", "")).strip().lower()
        extra_args = str(args.get("argumentos", "")).strip()

        target_cmd = APP_MAP.get(app_name, app_name)

        try:
            if target_cmd.startswith("ms-settings:"):
                os.system(f"start {target_cmd}")
                return "Configurações do Windows abertas com sucesso."

            # Verifica se está no PATH ou executa diretamente
            if extra_args:
                cmd_line = f"{target_cmd} {extra_args}"
                subprocess.Popen(cmd_line, shell=True)
            else:
                try:
                    os.startfile(target_cmd)
                except Exception:
                    subprocess.Popen(target_cmd, shell=True)

            return f"Aplicativo '{app_name}' aberto com sucesso."
        except Exception as exc:
            return f"Falha ao abrir o aplicativo '{app_name}': {exc}"


class GerenciarJanelas(Tool):
    """Gerencia janelas no Windows (minimizar, maximizar, restaurar, fechar, minimizar tudo)."""

    name = "gerenciar_janelas"
    description = (
        "Gerencia as janelas do sistema operacional Windows: "
        "minimizar tudo (mostrar área de trabalho), restaurar tudo, "
        "minimizar janela ativa, maximizar janela ativa, fechar janela ativa."
    )
    parameters = {
        "type": "object",
        "properties": {
            "acao": {
                "type": "string",
                "enum": ["minimizar_tudo", "restaurar_tudo", "minimizar_ativa", "maximizar_ativa", "restaurar_ativa", "fechar_ativa"],
                "description": "Ação a executar nas janelas do sistema.",
            },
        },
        "required": ["acao"],
    }

    async def run(self, args: dict[str, Any], context: ToolContext) -> str:
        action = str(args.get("acao", "")).strip().lower()

        if sys.platform != "win32":
            return "Gerenciamento de janelas disponível apenas no ambiente Windows."

        user32 = ctypes.windll.user32

        if action == "minimizar_tudo":
            # Mostra área de trabalho (Win + D / MinimizeAll)
            os.system('powershell -command "(New-Object -ComObject Shell.Application).MinimizeAll()"')
            return "Todas as janelas foram minimizadas (Área de Trabalho)."

        elif action == "restaurar_tudo":
            os.system('powershell -command "(New-Object -ComObject Shell.Application).UndoMinimizeAll()"')
            return "Todas as janelas minimizadas foram restauradas."

        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return "Nenhuma janela ativa detectada no momento."

        if action == "minimizar_ativa":
            user32.ShowWindow(hwnd, 6)  # SW_MINIMIZE
            return "Janela ativa minimizada com sucesso."
        elif action == "maximizar_ativa":
            user32.ShowWindow(hwnd, 3)  # SW_MAXIMIZE
            return "Janela ativa maximizada com sucesso."
        elif action == "restaurar_ativa":
            user32.ShowWindow(hwnd, 9)  # SW_RESTORE
            return "Janela ativa restaurada com sucesso."
        elif action == "fechar_ativa":
            user32.PostMessageW(hwnd, 0x0010, 0, 0)  # WM_CLOSE
            return "Janela ativa fechada."

        return f"Ação de janela '{action}' não reconhecida."


class ControleConfiguracoesSistema(Tool):
    """Controla configurações do Windows e status de energia/bloqueio."""

    name = "controle_configuracoes_sistema"
    description = (
        "Controla configurações do sistema por voz ou comando: "
        "bloquear tela, abrir configurações do Windows, verificar status da bateria, "
        "abrir gerenciador de tarefas ou desligar tela."
    )
    parameters = {
        "type": "object",
        "properties": {
            "comando": {
                "type": "string",
                "enum": ["bloquear_tela", "abrir_configuracoes", "status_bateria", "desligar_tela", "gerenciador_tarefas"],
                "description": "Comando de configuração do sistema a executar.",
            },
        },
        "required": ["comando"],
    }

    async def run(self, args: dict[str, Any], context: ToolContext) -> str:
        cmd = str(args.get("comando", "")).strip().lower()

        if cmd == "bloquear_tela":
            if sys.platform == "win32":
                ctypes.windll.user32.LockWorkStation()
                return "Computador bloqueado com sucesso."
            return "Bloqueio de tela disponível apenas no Windows."

        elif cmd == "abrir_configuracoes":
            os.system("start ms-settings:")
            return "Configurações do Windows abertas."

        elif cmd == "gerenciador_tarefas":
            os.system("start taskmgr")
            return "Gerenciador de Tarefas aberto."

        elif cmd == "desligar_tela":
            if sys.platform == "win32":
                # SC_MONITORPOWER: 2 (off)
                ctypes.windll.user32.SendMessageW(0xFFFF, 0x0112, 0xF170, 2)
                return "Monitor desligado (modo econômico)."
            return "Comando suportado apenas no Windows."

        elif cmd == "status_bateria":
            try:
                import psutil
                battery = psutil.sensors_battery()
                if battery is None:
                    return "Este computador não possui bateria (computador desktop conectado à tomada)."
                plugged = "conectado à tomada" if battery.power_plugged else "na bateria"
                return f"Bateria em {battery.percent:.0f}% ({plugged})."
            except Exception as exc:
                return f"Não foi possível consultar o status da bateria: {exc}"

        return f"Comando '{cmd}' não reconhecido."
