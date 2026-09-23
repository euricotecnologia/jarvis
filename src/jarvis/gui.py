from __future__ import annotations

import asyncio
import os
import re
import shutil
import sys
import threading
import uuid
from dataclasses import replace
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import unquote, urlparse

from PySide6.QtCore import Property, Qt, QObject, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import (
    QAction,
    QColor,
    QDesktopServices,
    QFont,
    QFontDatabase,
    QGuiApplication,
    QIcon,
    QPainter,
    QPixmap,
)
from PySide6.QtQml import QQmlApplicationEngine

from jarvis.agenda import (
    REMINDER_CHOICES,
    birthday_label,
    combine_fields,
    describe_reminder,
    describe_when,
    parse_dt,
    reminder_due,
    reminder_text,
)
from jarvis import attachments as attachmentsmod
from jarvis import files as filebrowser
from jarvis import codeassist as codeassistmod
from jarvis import netsec as netsecmod
from jarvis import medknow as medknowmod
from jarvis import patients as patientsmod
from jarvis import profiles as profilesmod
from jarvis import saude as saudemod
from jarvis import sectors as sectorsmod
from jarvis import sysinfo
from jarvis import toolbox
from jarvis import vision as visionmod
from jarvis.assistant import JarvisAssistant
from jarvis.errors import DatabaseUnavailable
from jarvis.config import AppConfig
from jarvis.models import Appointment, Contact, LLMRequest, Message, Routine
from jarvis.routines import match_routine_command, seed_default_routines
from jarvis.scheduling import (
    build_schedule,
    describe_schedule,
    is_due,
    is_missed,
    next_occurrence,
)
from jarvis.telemetry import SystemMonitor
from jarvis.weather import WeatherService
from jarvis.whatsapp import WhatsAppManager
from jarvis.secret_store import (
    delete_secret,
    restore_secret_to_environment,
    save_secret,
    secret_configured,
)
from jarvis.voice import (
    KOKORO_VOICES,
    VoiceError,
    VoiceService,
    kokoro_available,
    missing_voice_dependencies,
)
from jarvis.wakeword import WakeWordListener, strip_wake_prefix


def window_url_to_path(raw: str) -> str:
    """Aceita caminho normal OU URL file:// (do FileDialog do QML)."""
    text = str(raw or "").strip()
    if text.startswith("file:"):
        parsed = urlparse(text)
        path = unquote(parsed.path)
        # Windows: file:///C:/x -> /C:/x  => tira a barra inicial
        if len(path) >= 3 and path[0] == "/" and path[2] == ":":
            path = path[1:]
        return path
    return text


AI_PROVIDER_LABELS = {
    "LM Studio": "lmstudio",
    "Ollama": "ollama",
    "OpenAI": "openai",
    "Claude": "claude",
    "Gemini": "gemini",
}
# opções da tela de Personalização (texto livre, mas com sugestões)
_PERSONALITY_LABELS = (
    "Prestativo e Amigável", "Direto ao ponto", "Formal e Profissional",
    "Bem-humorado", "Técnico e Detalhista", "Mentor paciente", "Neutro",
)
_TONE_LABELS = (
    "Natural", "Caloroso", "Sério", "Animado", "Calmo", "Enérgico",
)
_ACCENT_LABELS = (
    "Português (Brasil)", "Português (Portugal)", "Português neutro",
    "Inglês (EUA)", "Espanhol (LatAm)",
)
AI_PROVIDER_NAMES = {value: key for key, value in AI_PROVIDER_LABELS.items()}
AI_MODEL_SUGGESTIONS = {
    "lmstudio": ["google/gemma-4-e2b", "local-model"],
    "ollama": ["qwen3", "llama3.2", "gemma3", "mistral"],
    "openai": [
        "gpt-3.5-turbo",
        "gpt-4",
        "gpt-4-turbo",
        "gpt-4o-mini",
        "gpt-4o",
        "gpt-4.1-nano",
        "gpt-4.1-mini",
        "gpt-4.1",
        "gpt-5-nano",
        "gpt-5-mini",
        "gpt-5",
        "gpt-5.4-mini",
        "gpt-5.4",
        "gpt-5.5",
        "gpt-5.6-luna",
        "gpt-5.6-terra",
        "gpt-5.6-sol",
    ],
    "claude": ["claude-sonnet-5", "claude-opus-4.1", "claude-haiku-4.5"],
    "gemini": ["gemini-3.7-flash", "gemini-3.6-flash", "gemini-2.5-pro"],
}
API_KEY_ENV_NAMES = {
    "OpenAI": "OPENAI_API_KEY",
    "Claude": "ANTHROPIC_API_KEY",
    "Gemini": "GEMINI_API_KEY",
    "Gemini TTS": "GEMINI_API_KEY",
}
API_KEY_URLS = {
    "OpenAI": "https://platform.openai.com/api-keys",
    "Claude": "https://platform.claude.com/settings/keys",
    "Gemini": "https://aistudio.google.com/apikey",
    "Gemini TTS": "https://aistudio.google.com/apikey",
}
GEMINI_TTS_MODELS = [
    "gemini-3.1-flash-tts-preview",
    "gemini-2.5-flash-preview-tts",
    "gemini-2.5-pro-preview-tts",
]
GEMINI_VOICES = [
    "Kore", "Aoede", "Puck", "Charon", "Fenrir", "Zephyr", "Leda", "Orus",
    "Callirrhoe", "Autonoe", "Enceladus", "Iapetus", "Umbriel", "Algieba",
    "Despina", "Erinome", "Algenib", "Rasalgethi", "Laomedeia", "Achernar",
    "Alnilam", "Schedar", "Gacrux", "Pulcherrima", "Achird", "Zubenelgenubi",
    "Vindemiatrix", "Sadachbia", "Sadaltager", "Sulafat",
]

AI_AGENT_PROVIDERS = [
    "OpenAI",
    "Anthropic",
    "Gemini",
    "Groq",
    "OpenRouter",
    "LM Studio",
    "Ollama",
]

AI_AGENT_MODELS = {
    "OpenAI": [
        "gpt-4.5-preview",
        "gpt-4.5-preview-2025-02-27",
        "gpt-4o",
        "gpt-4o-2024-11-20",
        "gpt-4o-2024-08-06",
        "gpt-4o-2024-05-13",
        "gpt-4o-mini",
        "gpt-4o-mini-2024-07-18",
        "chatgpt-4o-latest",
        "o3-mini",
        "o3-mini-2025-01-31",
        "o1",
        "o1-2024-12-17",
        "o1-preview",
        "o1-preview-2024-09-12",
        "o1-mini",
        "o1-mini-2024-09-12",
        "gpt-4-turbo",
        "gpt-4-turbo-2024-04-09",
        "gpt-4-turbo-preview",
        "gpt-4-0125-preview",
        "gpt-4-1106-preview",
        "gpt-4-vision-preview",
        "gpt-4",
        "gpt-4-0613",
        "gpt-4-0314",
        "gpt-4-32k",
        "gpt-4-32k-0613",
        "gpt-3.5-turbo",
        "gpt-3.5-turbo-0125",
        "gpt-3.5-turbo-1106",
        "gpt-3.5-turbo-16k",
        "gpt-3.5-turbo-0613",
        "gpt-3.5-turbo-instruct",
    ],
    "Anthropic": [
        "claude-3-7-sonnet-latest",
        "claude-3-7-sonnet-20250219",
        "claude-3-5-sonnet-latest",
        "claude-3-5-sonnet-20241022",
        "claude-3-5-sonnet-20240620",
        "claude-3-5-haiku-latest",
        "claude-3-5-haiku-20241022",
        "claude-3-opus-latest",
        "claude-3-opus-20240229",
        "claude-3-sonnet-20240229",
        "claude-3-haiku-20240307",
        "claude-2.1",
        "claude-2.0",
        "claude-instant-1.2",
    ],
    "Gemini": [
        "gemini-2.0-flash",
        "gemini-2.0-flash-lite",
        "gemini-2.0-flash-lite-preview-02-05",
        "gemini-2.0-pro-exp-02-05",
        "gemini-2.0-flash-thinking-exp-01-21",
        "gemini-2.0-flash-exp",
        "gemini-exp-1206",
        "gemini-exp-1121",
        "gemini-exp-1114",
        "gemini-1.5-pro",
        "gemini-1.5-pro-latest",
        "gemini-1.5-pro-002",
        "gemini-1.5-pro-001",
        "gemini-1.5-flash",
        "gemini-1.5-flash-latest",
        "gemini-1.5-flash-002",
        "gemini-1.5-flash-001",
        "gemini-1.5-flash-8b",
        "gemini-1.5-flash-8b-latest",
        "gemini-1.5-flash-8b-001",
        "gemini-1.0-pro",
        "gemini-1.0-pro-vision",
        "gemini-pro",
        "gemini-pro-vision",
    ],
    "Groq": [
        "llama-3.3-70b-versatile",
        "llama-3.3-70b-specdec",
        "llama-3.2-1b-preview",
        "llama-3.2-3b-preview",
        "llama-3.2-11b-vision-preview",
        "llama-3.2-90b-vision-preview",
        "llama-3.1-405b-reasoning",
        "llama-3.1-70b-versatile",
        "llama-3.1-8b-instant",
        "llama3-70b-8192",
        "llama3-8b-8192",
        "mixtral-8x7b-32768",
        "gemma2-9b-it",
        "gemma-7b-it",
        "deepseek-r1-distill-llama-70b",
        "deepseek-r1-distill-llama-70b-specdec",
        "deepseek-r1-distill-qwen-32b",
        "qwen-2.5-32b",
        "qwen-2.5-coder-32b",
    ],
    "OpenRouter": [
        "openai/gpt-4o",
        "openai/gpt-4.5-preview",
        "anthropic/claude-3.7-sonnet",
        "anthropic/claude-3.5-sonnet",
        "deepseek/deepseek-r1",
        "deepseek/deepseek-chat",
        "meta-llama/llama-3.3-70b-instruct",
        "google/gemini-2.0-flash-exp",
    ],
    "LM Studio": [
        "local-model",
        "mistral-7b-instruct",
        "qwen2.5-coder-7b",
        "llama-3.2-3b",
        "custom",
    ],
    "Ollama": [
        "llama3.2",
        "llama3.1",
        "deepseek-r1",
        "qwen2.5-coder",
        "mistral",
        "gemma2",
        "phi4",
        "custom",
    ],
}



class JarvisBackend(QObject):
    messageAdded = Signal(str, str, str)
    streamStarted = Signal(str)
    streamDelta = Signal(str)
    streamEnded = Signal(str)
    busyChanged = Signal()
    statusChanged = Signal()
    providerChanged = Signal()
    voiceStateChanged = Signal()
    voiceLevelChanged = Signal()
    transcriptionReady = Signal(str, str)
    settingsChanged = Signal()
    confirmationRequested = Signal(str, str)  # token, descrição
    wakeWordDetected = Signal(str)  # comando dito junto com a palavra, ou ""
    systemStatsChanged = Signal()
    weatherChanged = Signal()
    viewChanged = Signal()
    routinesChanged = Signal()
    scheduleTriggered = Signal(int)  # routine_id
    agendaChanged = Signal()
    notificationRequested = Signal("QVariantMap")  # {title, whenText, ...}
    filesChanged = Signal()
    composeRequested = Signal(str)  # texto pre-preenchido no campo do chat
    toolboxChanged = Signal()
    chatMediaAdded = Signal("QVariantMap")  # {role, meta, caption, kind, uri}
    chatArtifactAdded = Signal("QVariantMap")  # {language, code, filename, previewable}
    chatBodyReplaced = Signal(str)  # troca o texto da última bolha do assistente
    systemPanelChanged = Signal()
    visionTested = Signal(str, str)  # dataUri, texto
    attachmentsChanged = Signal()  # anexos pendentes do chat
    serversChanged = Signal()  # lista de servidores SSH
    serverTested = Signal(str, str)  # alias, resultado do teste
    profileChanged = Signal()  # perfil de uso ativo
    sectorChanged = Signal()  # setor / ramo de atividade ativo
    patientsChanged = Signal()  # cadastro de pacientes (setor Saúde)
    patientRecordsChanged = Signal()  # registros do prontuário
    recordSaved = Signal(int)  # id do registro recém-salvo (para anexar depois)
    profileFolderNeeded = Signal(str)  # perfil que precisa de uma pasta (id)
    conversationsChanged = Signal()  # historico de conversas
    chatCleared = Signal()  # limpar a lista de mensagens no QML
    themeChanged = Signal()  # alternância entre tema claro e escuro
    systemNameChanged = Signal()  # alteração do nome do sistema / assistente
    whatsappStatusChanged = Signal()  # status da conexão WhatsApp (Baileys)
    whatsappLogsChanged = Signal()  # novos logs/mensagens de WhatsApp
    whatsappDraftReady = Signal(str)  # texto redigido com IA pronto para envio
    aiAgentsChanged = Signal()  # lista de modelos/agentes de IA
    aiAgentTestResult = Signal(bool, str)  # resultado do teste de modelo/chave (sucesso, mensagem)
    communicationAgentsChanged = Signal()  # lista de agentes de atendimento da aba Comunicação
    learnedMemoriesChanged = Signal()  # lista de memórias de longo prazo do usuário
    behaviorProfileChanged = Signal()  # perfil e preferências comportamentais aprendidas
    proactiveSuggestionsChanged = Signal()  # sugestões proativas dinâmicas
    personaChanged = Signal()  # personalização da identidade e voz do assistente
    mcpServersChanged = Signal()  # lista de servidores MCP registrados
    mcpTested = Signal("QVariantMap")  # resultado de "testar conexão" de um MCP

    def __init__(self, config: AppConfig) -> None:
        super().__init__()
        self._config = config
        self._base_system_prompt = config.system_prompt
        self._assistant = JarvisAssistant(config, on_media=self._emit_chat_media)
        self._assistant.database.initialize()
        self._assistant.database.sync_providers(config.providers)
        seed_default_routines(self._assistant.database)
        for secret_name in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY"):
            restore_secret_to_environment(self._assistant.database, secret_name)
        self._busy = False
        self._status = "SISTEMA PRONTO"
        self._active_provider = config.default_provider
        self._conversation_id: int | None = None
        self._voice = VoiceService(config.voice)
        self._voice_state = "idle"
        self._voice_level = 0.0
        self._voice_stop_event = threading.Event()
        self._speaking_stop = threading.Event()
        self._settings_revision = 0
        self._confirmations: dict[str, tuple[threading.Event, list[bool]]] = {}
        self._wake: WakeWordListener | None = None
        self._current_view = "hub"
        self._monitor = SystemMonitor()
        self._weather = WeatherService()
        self._stats: dict = {"available": False}
        self._weather_data: dict = {"ok": False, "city": config.weather_city}
        self._telemetry_stop = threading.Event()
        self._weather_wake = threading.Event()
        self._files_state: dict = {
            "ok": True, "error": "", "path": filebrowser.home_path(),
            "parent": "", "entries": [], "search": False,
        }
        self._files_busy = False
        self._toolbox_result: dict = {}
        self._toolbox_busy = False
        self._specs: dict = {"available": False, "hardware": [], "system": [], "gpu": []}
        self._processes: list = []
        self._disks: dict = {"volumes": [], "temp": {}, "recycle": {}}
        self._power: dict = {"hasBattery": False, "plans": []}
        self._sys_busy = False
        self._proc_busy = False
        self._disks_busy = False
        self._sys_message = ""
        self._pending_attachments: list = []
        self.transcriptionReady.connect(self._submit_transcription)
        self.wakeWordDetected.connect(self._on_wake_word)
        self.scheduleTriggered.connect(self._on_schedule_triggered)
        preferences = self._assistant.database.get_setting("runtime_preferences", {})
        if isinstance(preferences, dict) and preferences:
            self._apply_runtime_preferences(preferences)
        self._warm_voice()
        self._sync_wake_word()
        self._start_telemetry()
        project_root = Path(__file__).resolve().parent.parent.parent
        self._whatsapp_state: dict = {
            "status": "disconnected",
            "qrCode": "",
            "user": None,
            "connected": False,
            "logs": [],
        }
        self._whatsapp = WhatsAppManager(
            base_dir=project_root,
            on_status_changed=self._on_whatsapp_status_update,
        )
        self._whatsapp.start_bridge()

    def _on_whatsapp_status_update(self, status: dict) -> None:
        self._whatsapp_state = status
        self.whatsappStatusChanged.emit()
        self.whatsappLogsChanged.emit()

    def _sync_wake_word(self) -> None:
        """Liga/desliga a escuta da palavra de ativação conforme a config."""
        want = self._config.voice.wake_word_enabled
        if not want:
            if self._wake is not None:
                self._wake.stop()
                self._wake = None
            return
        if not self._voice.available:
            self.messageAdded.emit(
                "error",
                "Recurso de voz indisponível: a palavra de ativação precisa do "
                "pacote de voz (.[full]).",
                "PALAVRA DE ATIVACAO",
            )
            return
        if self._wake is not None:
            return

        self._wake = WakeWordListener(
            self._config.voice,
            self._voice,
            on_wake=lambda command: self.wakeWordDetected.emit(command),
            on_status=self._on_wake_status,
        )
        self._wake.start()
        self.messageAdded.emit(
            "system",
            f'Escutando em segundo plano. Diga "{self._config.voice.wake_word}" '
            "para eu responder.",
            "PALAVRA DE ATIVACAO",
        )

    def _on_wake_status(self, message: str) -> None:
        """So erros serios do listener vao pro chat; nunca o que o usuário falou."""
        lowered = message.lower()
        if "não consigo" in lowered or "indisponivel" in lowered or "ausentes" in lowered:
            self.messageAdded.emit("error", message, "PALAVRA DE ATIVACAO")

    @Slot()
    def shutdown(self) -> None:
        self._telemetry_stop.set()
        self._weather_wake.set()
        if self._wake is not None:
            self._wake.stop()
            self._wake = None
        self._voice.stop_speaking()

    @Slot(str)
    def _on_wake_word(self, command: str) -> None:
        if self._busy or self._voice_state not in {"idle", "error"}:
            if self._wake is not None:
                self._wake.resume()
            return
        if self._wake is not None:
            self._wake.pause()

        command = command.strip()
        if len(command) >= 3:
            # O comando foi falado junto com a palavra de ativação na mesma frase
            self._set_status("PALAVRA DETECTADA")
            self._set_voice_state("thinking")
            self.transcriptionReady.emit(command, "Automático")
        else:
            # Só a palavra de ativação foi dita -> abre a escuta para o comando
            self._set_status("PALAVRA DETECTADA // FALE")
            self._signal_listening_started()
            QTimer.singleShot(180, lambda: self.toggleListening("Automático"))

    def _warm_voice(self) -> None:
        if not self._voice.available:
            return
        threading.Thread(
            target=self._voice.warm_up,
            daemon=True,
            name="jarvis-voice-warmup",
        ).start()

    # -- telemetria (sistema + clima) -------------------------------------
    def _start_telemetry(self) -> None:
        threading.Thread(
            target=self._telemetry_worker, daemon=True, name="jarvis-telemetry"
        ).start()
        threading.Thread(
            target=self._weather_worker, daemon=True, name="jarvis-weather"
        ).start()
        threading.Thread(
            target=self._scheduler_worker, daemon=True, name="jarvis-scheduler"
        ).start()

    def _scheduler_worker(self) -> None:
        """A cada 20s: lembretes de compromissos + rotinas agendadas."""
        while not self._telemetry_stop.wait(20.0):
            try:
                self._check_appointment_reminders()
            except Exception:  # noqa: BLE001 - o agendador nunca derruba o app
                pass
            if self._busy or self._voice_state not in {"idle", "error"}:
                continue
            try:
                due = self._find_due_schedule()
            except Exception:  # noqa: BLE001 - o agendador nunca derruba o app
                continue
            if due is None:
                continue
            schedule, routine, missed = due
            now_iso = datetime.now().isoformat(timespec="seconds")
            if missed:
                self._assistant.database.mark_schedule_ran(
                    schedule.id, now_iso, disable=True
                )
                self.messageAdded.emit(
                    "system",
                    f'O agendamento da rotina "{routine.name}" foi perdido '
                    "(o app estava fechado no horário).",
                    "AUTOMACAO",
                )
                self.routinesChanged.emit()
                continue
            self._assistant.database.mark_schedule_ran(
                schedule.id, now_iso, disable=(schedule.kind == "once")
            )
            self.routinesChanged.emit()
            self.scheduleTriggered.emit(int(routine.id))

    def _find_due_schedule(self):
        now = datetime.now()
        for schedule in self._assistant.database.list_schedules():
            if not is_due(schedule, now):
                continue
            routine = self._assistant.database.get_routine(schedule.routine_id)
            if routine is None:
                self._assistant.database.clear_schedule(schedule.routine_id)
                continue
            return schedule, routine, is_missed(schedule, now)
        return None

    @Slot(int)
    def _on_schedule_triggered(self, routine_id: int) -> None:
        routine = self._assistant.database.get_routine(int(routine_id))
        if routine is None:
            return
        self.messageAdded.emit(
            "system",
            f'Agendamento: rodando a rotina "{routine.name}".',
            "AUTOMACAO",
        )
        self._launch_routine(routine, speak=True, echo=None)

    def _check_appointment_reminders(self) -> None:
        now = datetime.now()
        window = (now - timedelta(hours=3)).isoformat(timespec="minutes")
        names = {c.id: c.name for c in self._assistant.database.list_contacts()}
        for appointment in self._assistant.database.list_appointments(since=window):
            if not reminder_due(appointment, now):
                continue
            self._assistant.database.mark_appointment_reminded(
                appointment.id, now.isoformat(timespec="seconds")
            )
            message = reminder_text(appointment, now)
            start = parse_dt(appointment.start_at)
            self.notificationRequested.emit(
                {
                    "title": appointment.title,
                    "spoken": message,
                    "whenText": describe_when(appointment, now),
                    "timeText": f"{start:%H:%M}" if start else "",
                    "dateText": f"{start:%d/%m/%Y}" if start else "",
                    "location": appointment.location,
                    "contact": names.get(appointment.contact_id or -1, ""),
                    "notes": appointment.notes,
                }
            )
            self.messageAdded.emit("system", message, "AGENDA / LEMBRETE")
            self.agendaChanged.emit()
            if not self._busy and self._voice_state in {"idle", "error"}:
                self._speak_reply(message)
            return  # um lembrete por ciclo

    def _telemetry_worker(self) -> None:
        while not self._telemetry_stop.is_set():
            try:
                self._stats = self._monitor.sample().as_dict()
                self.systemStatsChanged.emit()
            except Exception:  # noqa: BLE001 - telemetria nunca derruba a UI
                pass
            self._telemetry_stop.wait(2.0)

    def _weather_worker(self) -> None:
        while not self._telemetry_stop.is_set():
            forced = self._weather_wake.is_set()
            self._weather_wake.clear()
            try:
                report = self._weather.get(self._config.weather_city, force=forced)
                self._weather_data = report.as_dict()
                self.weatherChanged.emit()
            except Exception:  # noqa: BLE001
                pass
            self._weather_wake.wait(900.0)

    @Property("QVariantMap", notify=systemStatsChanged)
    def systemStats(self) -> dict:
        return self._stats

    @Property("QVariantMap", notify=weatherChanged)
    def weather(self) -> dict:
        return self._weather_data

    @Property(str, notify=settingsChanged)
    def weatherCity(self) -> str:
        return self._config.weather_city

    @Property(str, notify=viewChanged)
    def currentView(self) -> str:
        return self._current_view

    @Property(str, constant=True)
    def userName(self) -> str:
        import getpass

        try:
            return getpass.getuser()
        except Exception:  # noqa: BLE001
            return "usuario"

    @Property(str, constant=True)
    def appVersion(self) -> str:
        return "v6.2.1"

    @Slot(str)
    def setView(self, view: str) -> None:
        view = (view or "hub").strip().lower()
        if view != self._current_view:
            self._current_view = view
            self.viewChanged.emit()

    @Slot()
    def refreshWeather(self) -> None:
        self._weather_wake.set()

    # -- rotinas de automação -------------------------------------------
    @Property("QVariantList", notify=routinesChanged)
    def routines(self) -> list[dict]:
        now = datetime.now()
        schedules = {
            item.routine_id: item
            for item in self._assistant.database.list_schedules()
        }
        result: list[dict] = []
        for item in self._assistant.database.list_routines():
            schedule = schedules.get(item.id)
            entry = {
                "id": item.id,
                "name": item.name,
                "description": item.description,
                "steps": "\n".join(item.steps),
                "stepCount": len(item.steps),
                "enabled": item.enabled,
                "scheduled": bool(schedule),
                "scheduleText": "",
                "scheduleKind": schedule.kind if schedule else "",
                "scheduleActive": bool(schedule and schedule.enabled),
            }
            if schedule is not None:
                entry["scheduleText"] = describe_schedule(schedule, now)
                nxt = next_occurrence(schedule, now) if schedule.enabled else None
                if nxt is not None:
                    entry["scheduleText"] += f"  (próxima: {nxt:%d/%m %H:%M})"
            result.append(entry)
        return result

    @Slot(int, str, str, str, int)
    def setSchedule(
        self,
        routine_id: int,
        kind: str,
        date_text: str,
        time_text: str,
        weekday: int,
    ) -> None:
        if self._assistant.database.get_routine(int(routine_id)) is None:
            self.messageAdded.emit("error", "Rotina inexistente.", "AUTOMACAO")
            return
        try:
            schedule = build_schedule(
                int(routine_id),
                kind,
                date_text=date_text,
                time_text=time_text,
                weekday=weekday if weekday >= 0 else None,
            )
        except ValueError as exc:
            self.messageAdded.emit("error", str(exc), "AUTOMAÇÃO / AGENDAMENTO")
            return
        self._assistant.database.set_schedule(schedule)
        self.routinesChanged.emit()
        self._set_status("AGENDAMENTO SALVO")
        self.messageAdded.emit(
            "system",
            f"Agendamento salvo: {describe_schedule(schedule)}.",
            "AUTOMACAO",
        )

    @Slot(int)
    def clearSchedule(self, routine_id: int) -> None:
        self._assistant.database.clear_schedule(int(routine_id))
        self.routinesChanged.emit()
        self.messageAdded.emit("system", "Agendamento removido.", "AUTOMACAO")

    # -- agenda (compromissos + contatos) -------------------------------
    @Property("QVariantList", constant=True)
    def reminderChoices(self) -> list[dict]:
        return [{"value": value, "label": label} for value, label in REMINDER_CHOICES]

    @Property("QVariantList", notify=agendaChanged)
    def appointments(self) -> list[dict]:
        now = datetime.now()
        names = {c.id: c.name for c in self._assistant.database.list_contacts()}
        window = (now - timedelta(days=1)).isoformat(timespec="minutes")
        result: list[dict] = []
        for item in self._assistant.database.list_appointments(since=window):
            start = parse_dt(item.start_at)
            result.append(
                {
                    "id": item.id,
                    "title": item.title,
                    "startISO": item.start_at,
                    "dateText": f"{start:%d/%m/%Y}" if start else "",
                    "timeText": f"{start:%H:%M}" if start else "",
                    "whenText": describe_when(item, now),
                    "location": item.location,
                    "notes": item.notes,
                    "contactId": item.contact_id or 0,
                    "contactName": names.get(item.contact_id or -1, ""),
                    "reminderMinutes": item.reminder_minutes,
                    "reminderText": describe_reminder(item.reminder_minutes),
                    "isPast": bool(start and start < now),
                }
            )
        return result

    @Property("QVariantList", notify=agendaChanged)
    def contacts(self) -> list[dict]:
        today = datetime.now().date()
        result: list[dict] = []
        for item in self._assistant.database.list_contacts():
            result.append(
                {
                    "id": item.id,
                    "name": item.name,
                    "phone": item.phone,
                    "email": item.email,
                    "birthday": item.birthday or "",
                    "notes": item.notes,
                    "tags": item.tags,
                    "birthdayLabel": birthday_label(item.birthday, today) or "",
                }
            )
        return result

    @Slot(int, str, str, str, str, str, int, int)
    def saveAppointment(
        self,
        appointment_id: int,
        title: str,
        date_text: str,
        time_text: str,
        location: str,
        notes: str,
        contact_id: int,
        reminder_minutes: int,
    ) -> None:
        title = (title or "").strip()
        if not title:
            self.messageAdded.emit("error", "Dê um título ao compromisso.", "AGENDA")
            return
        try:
            start_at = combine_fields(date_text.strip(), time_text.strip())
        except ValueError as exc:
            self.messageAdded.emit("error", str(exc), "AGENDA")
            return
        existing = (
            self._assistant.database.get_appointment(appointment_id)
            if appointment_id > 0
            else None
        )
        reminded = existing.reminded_at if existing else None
        if existing and existing.start_at != start_at:
            reminded = None  # mudou a hora -> pode avisar de novo
        self._assistant.database.save_appointment(
            Appointment(
                id=appointment_id if appointment_id > 0 else None,
                title=title,
                start_at=start_at,
                location=(location or "").strip(),
                notes=(notes or "").strip(),
                contact_id=contact_id if contact_id > 0 else None,
                reminder_minutes=int(reminder_minutes),
                reminded_at=reminded,
            )
        )
        self.agendaChanged.emit()
        self._set_status("COMPROMISSO SALVO")
        self.messageAdded.emit(
            "system", f'Compromisso "{title}" salvo.', "AGENDA"
        )

    @Slot(int)
    def deleteAppointment(self, appointment_id: int) -> None:
        self._assistant.database.delete_appointment(int(appointment_id))
        self.agendaChanged.emit()
        self.messageAdded.emit("system", "Compromisso removido.", "AGENDA")

    @Slot()
    def testNotification(self) -> None:
        """Dispara uma notificação de exemplo (botão 'testar' na Agenda)."""
        now = datetime.now()
        upcoming = [
            item
            for item in self._assistant.database.list_appointments(
                since=now.isoformat(timespec="minutes")
            )
        ]
        if upcoming:
            appointment = upcoming[0]
            start = parse_dt(appointment.start_at)
            names = {c.id: c.name for c in self._assistant.database.list_contacts()}
            payload = {
                "title": appointment.title,
                "spoken": reminder_text(appointment, now),
                "whenText": describe_when(appointment, now),
                "timeText": f"{start:%H:%M}" if start else "",
                "dateText": f"{start:%d/%m/%Y}" if start else "",
                "location": appointment.location,
                "contact": names.get(appointment.contact_id or -1, ""),
                "notes": appointment.notes,
            }
        else:
            soon = now + timedelta(minutes=15)
            payload = {
                "title": "Compromisso de exemplo",
                "spoken": "Lembrete: compromisso de exemplo em 15 minutos.",
                "whenText": f"Hoje {soon:%H:%M}  (em 15 min)",
                "timeText": f"{soon:%H:%M}",
                "dateText": f"{soon:%d/%m/%Y}",
                "location": "Sala de reuniao",
                "contact": "",
                "notes": "Isto e apenas uma demonstração da notificação.",
            }
        self.notificationRequested.emit(payload)

    @Slot(int, str, str, str, str, str)
    def saveContact(
        self,
        contact_id: int,
        name: str,
        phone: str,
        email: str,
        birthday: str,
        notes: str,
    ) -> None:
        name = (name or "").strip()
        if not name:
            self.messageAdded.emit("error", "Dê um nome ao contato.", "AGENDA")
            return
        stored_birthday = self._normalize_birthday(birthday)
        self._assistant.database.save_contact(
            Contact(
                id=contact_id if contact_id > 0 else None,
                name=name,
                phone=(phone or "").strip(),
                email=(email or "").strip(),
                birthday=stored_birthday,
                notes=(notes or "").strip(),
            )
        )
        self.agendaChanged.emit()
        self._set_status("CONTATO SALVO")
        self.messageAdded.emit("system", f'Contato "{name}" salvo.', "AGENDA")

    @staticmethod
    def _normalize_birthday(text: str) -> str | None:
        text = (text or "").strip()
        if not text:
            return None
        import re

        match = re.match(r"^(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?$", text)
        if not match:
            return None
        day, month = int(match.group(1)), int(match.group(2))
        if match.group(3):
            year = int(match.group(3))
            year += 2000 if year < 100 else 0
            return f"{year:04d}-{month:02d}-{day:02d}"
        return f"{month:02d}-{day:02d}"

    @Slot(int)
    def deleteContact(self, contact_id: int) -> None:
        self._assistant.database.delete_contact(int(contact_id))
        self.agendaChanged.emit()
        self.messageAdded.emit("system", "Contato removido.", "AGENDA")

    # ---------------------------------------------- servidores (SSH)
    @Property(bool, constant=True)
    def sshClientAvailable(self) -> bool:
        from jarvis import ssh as sshmod

        return sshmod.ssh_available()

    @Property("QVariantList", notify=serversChanged)
    def servers(self) -> list[dict]:
        out: list[dict] = []
        for item in self._assistant.database.list_servers():
            out.append(
                {
                    "id": item.id,
                    "alias": item.alias,
                    "host": item.host,
                    "user": item.user,
                    "port": item.port,
                    "auth": item.auth,
                    "keyPath": item.key_path,
                    "hasPassword": bool(item.password_enc),
                    "notes": item.notes,
                }
            )
        return out

    @Slot(int, str, str, str, int, str, str, str)
    def saveServer(
        self,
        server_id: int,
        alias: str,
        host: str,
        user: str,
        port: int,
        auth: str,
        key_path: str,
        password: str,
    ) -> None:
        from jarvis.models import Server
        from jarvis.secret_store import encrypt_value

        alias = (alias or "").strip()
        host = (host or "").strip()
        user = (user or "").strip()
        auth = (auth or "key").strip().lower()
        if auth not in {"key", "password", "agent"}:
            auth = "key"
        if not alias or not host or not user:
            self.messageAdded.emit(
                "error", "Preencha apelido, host e usuário.", "SERVIDORES"
            )
            return
        existing = (
            self._assistant.database.get_server(server_id)
            if server_id and server_id > 0
            else None
        )
        clash = self._assistant.database.find_server(alias)
        if clash is not None and clash.id != (existing.id if existing else None):
            self.messageAdded.emit(
                "error", f'Ja existe um servidor com o apelido "{alias}".', "SERVIDORES"
            )
            return

        password_enc = existing.password_enc if existing else ""
        if auth == "password":
            if (password or "").strip():
                password_enc = encrypt_value(password.strip())
            elif not password_enc:
                self.messageAdded.emit(
                    "error", "Informe a senha do servidor.", "SERVIDORES"
                )
                return
        else:
            password_enc = ""

        try:
            self._assistant.database.save_server(
                Server(
                    id=existing.id if existing else None,
                    alias=alias,
                    host=host,
                    user=user,
                    port=int(port) if port else 22,
                    auth=auth,
                    key_path=(key_path or "").strip(),
                    password_enc=password_enc,
                    notes=existing.notes if existing else "",
                )
            )
        except Exception as exc:  # noqa: BLE001
            self.messageAdded.emit("error", f"Não consegui salvar: {exc}", "SERVIDORES")
            return
        self.serversChanged.emit()
        self._set_status("SERVIDOR SALVO")
        self.messageAdded.emit("system", f'Servidor "{alias}" salvo.', "SERVIDORES")

    @Slot(int)
    def deleteServer(self, server_id: int) -> None:
        self._assistant.database.delete_server(int(server_id))
        self.serversChanged.emit()
        self.messageAdded.emit("system", "Servidor removido.", "SERVIDORES")

    @Slot(int)
    def testServer(self, server_id: int) -> None:
        server = self._assistant.database.get_server(int(server_id))
        if server is None:
            self.serverTested.emit("", "Servidor não encontrado.")
            return
        self._set_status("TESTANDO SERVIDOR")
        threading.Thread(
            target=self._server_test_worker,
            args=(server,),
            daemon=True,
            name="jarvis-ssh-test",
        ).start()

    def _server_test_worker(self, server) -> None:
        from jarvis import ssh as sshmod
        from jarvis.secret_store import decrypt_value

        password = None
        if server.auth == "password":
            password = decrypt_value(server.password_enc)
            if not password:
                self.serverTested.emit(
                    server.alias, "Senha não encontrada. Recadastre o servidor."
                )
                self._set_status("SISTEMA PRONTO")
                return
        try:
            result = sshmod.test_connection(server, password=password)
        except sshmod.SSHError as exc:
            self.serverTested.emit(server.alias, f"Falhou: {exc}")
            self._set_status("ATENÇÃO NECESSÁRIA")
            return
        if result.ok:
            self.serverTested.emit(
                server.alias, f"Conectou!\n{result.stdout or 'ok'}"
            )
            self._set_status("SISTEMA PRONTO")
        else:
            detail = result.stderr or result.stdout or "sem detalhes"
            self.serverTested.emit(
                server.alias, f"Conexão recusada (exit {result.exit_code}):\n{detail}"
            )
            self._set_status("ATENÇÃO NECESSÁRIA")

    @Slot(str, str)
    def openContactLink(self, kind: str, value: str) -> None:
        value = (value or "").strip()
        if not value:
            return
        import re

        digits = re.sub(r"\D", "", value)
        if kind == "whatsapp":
            if digits and not digits.startswith("55") and len(digits) <= 11:
                digits = "55" + digits
            QDesktopServices.openUrl(QUrl(f"https://wa.me/{digits}"))
        elif kind == "tel":
            QDesktopServices.openUrl(QUrl(f"tel:{digits}"))
        elif kind == "email":
            QDesktopServices.openUrl(QUrl(f"mailto:{value}"))

    @Slot(str)
    def copyText(self, text: str) -> None:
        clipboard = QGuiApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(text or "")
            self._set_status("COPIADO")

    # -- navegador de arquivos ------------------------------------------
    @Property(str, notify=filesChanged)
    def filesPath(self) -> str:
        return self._files_state.get("path", filebrowser.home_path())

    @Property(str, notify=filesChanged)
    def filesParent(self) -> str:
        return self._files_state.get("parent", "")

    @Property(str, notify=filesChanged)
    def filesError(self) -> str:
        return self._files_state.get("error", "")

    @Property("QVariantList", notify=filesChanged)
    def fileEntries(self) -> list[dict]:
        return self._files_state.get("entries", [])

    @Property(bool, notify=filesChanged)
    def filesSearchActive(self) -> bool:
        return bool(self._files_state.get("search"))

    @Property(bool, notify=filesChanged)
    def filesBusy(self) -> bool:
        return self._files_busy

    @Property("QVariantList", constant=True)
    def quickAccess(self) -> list[dict]:
        return filebrowser.quick_access()

    @Property("QVariantList", notify=settingsChanged)
    def fileFavorites(self) -> list[dict]:
        raw = self._runtime_preferences().get("file_favorites", [])
        favorites: list[dict] = []
        for item in raw if isinstance(raw, list) else []:
            path = Path(str(item))
            favorites.append({"label": path.name or str(path), "path": str(path)})
        return favorites

    @Slot(str)
    def openFolder(self, path: str) -> None:
        target = path or self._files_state.get("path") or filebrowser.home_path()
        state = filebrowser.list_directory(target)
        state["search"] = False
        self._files_state = state
        self.filesChanged.emit()

    @Slot()
    def filesGoUp(self) -> None:
        parent = self._files_state.get("parent")
        if parent:
            self.openFolder(parent)

    @Slot()
    def filesGoHome(self) -> None:
        self.openFolder(filebrowser.home_path())

    @Slot()
    def refreshFolder(self) -> None:
        self.openFolder(self._files_state.get("path", filebrowser.home_path()))

    @Slot(str)
    def openFile(self, path: str) -> None:
        target = Path(path)
        if not target.exists():
            self.messageAdded.emit("error", f"Não existe: {path}", "ARQUIVOS")
            return
        try:
            if sys.platform == "win32":
                os.startfile(str(target))  # type: ignore[attr-defined]
            else:
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(target)))
        except OSError as exc:
            self.messageAdded.emit("error", f"Não consegui abrir: {exc}", "ARQUIVOS")

    @Slot(str)
    def revealInExplorer(self, path: str) -> None:
        target = Path(path)
        if sys.platform == "win32" and target.exists():
            import subprocess

            try:
                subprocess.Popen(["explorer", f"/select,{target}"])
                return
            except OSError:
                pass
        folder = target if target.is_dir() else target.parent
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))

    @Slot(str, bool)
    def searchFiles(self, query: str, in_content: bool) -> None:
        query = (query or "").strip()
        base = self._files_state.get("path", filebrowser.home_path())
        if not query:
            self.openFolder(base)
            return
        if self._files_busy:
            return
        self._files_busy = True
        self.filesChanged.emit()
        threading.Thread(
            target=self._search_worker,
            args=(base, query, bool(in_content)),
            daemon=True,
            name="jarvis-file-search",
        ).start()

    def _search_worker(self, base: str, query: str, in_content: bool) -> None:
        try:
            if in_content:
                result = filebrowser.search_in_files(base, query)
                entries = [
                    {
                        "name": f"{item['name']}:{item['line']}",
                        "path": item["path"],
                        "isDir": False,
                        "kind": "text",
                        "size": 0,
                        "sizeText": f"linha {item['line']}",
                        "modified": item["text"],
                        "ext": "",
                    }
                    for item in result.get("matches", [])
                ]
            else:
                result = filebrowser.search_by_name(base, query)
                entries = result.get("entries", [])
            self._files_state = {
                "ok": result.get("ok", True),
                "error": result.get("error", "")
                or (
                    "Busca parcial (muitos resultados ou tempo esgotado)."
                    if result.get("truncated")
                    else ""
                ),
                "path": base,
                "parent": base,
                "entries": entries,
                "search": True,
                "searchQuery": query,
            }
        except Exception as exc:  # noqa: BLE001
            self._files_state = {
                "ok": False, "error": f"Falha na busca: {exc}",
                "path": base, "parent": base, "entries": [], "search": True,
            }
        finally:
            self._files_busy = False
            self.filesChanged.emit()

    @Slot(result="QVariantMap")
    def filesContext(self) -> dict:
        return self._files_state

    @Slot(str, result="QVariantMap")
    def previewFile(self, path: str) -> dict:
        return filebrowser.preview(path)

    @Slot(str)
    def askJarvisAboutFile(self, path: str) -> None:
        name = Path(path).name
        self.composeRequested.emit(f'Sobre o arquivo "{path}": ')
        self._set_status(f"PERGUNTE SOBRE {name}")

    @Slot(str)
    def toggleFileFavorite(self, path: str) -> None:
        path = str(Path(path))
        preferences = self._runtime_preferences()
        favorites = list(preferences.get("file_favorites", []))
        if path in favorites:
            favorites.remove(path)
        else:
            favorites.append(path)
        preferences["file_favorites"] = favorites
        self._assistant.database.set_setting("runtime_preferences", preferences)
        self._notify_settings_changed()

    # -- caixa de ferramentas (menu Análises) ---------------------------
    @Property("QVariantList", constant=True)
    def toolboxUtilities(self) -> list[dict]:
        return toolbox.available_utilities()

    @Property(bool, notify=toolboxChanged)
    def toolboxBusy(self) -> bool:
        return self._toolbox_busy

    @Property("QVariantMap", notify=toolboxChanged)
    def toolboxResult(self) -> dict:
        return self._toolbox_result

    @Slot()
    def clearToolboxResult(self) -> None:
        self._toolbox_result = {}
        self.toolboxChanged.emit()

    @Slot(str, "QVariantMap")
    def runUtility(self, utility_id: str, params: dict) -> None:
        if self._toolbox_busy:
            return
        self._toolbox_busy = True
        self._toolbox_result = {}
        self.toolboxChanged.emit()
        plain = {key: params[key] for key in params}
        threading.Thread(
            target=self._toolbox_worker,
            args=(str(utility_id), plain),
            daemon=True,
            name="jarvis-toolbox",
        ).start()

    def _toolbox_worker(self, utility_id: str, params: dict) -> None:
        def ai_runner(system_prompt: str, user_content: str) -> str:
            request = LLMRequest(
                messages=(
                    Message(role="system", content=system_prompt),
                    Message(role="user", content=user_content),
                )
            )
            response = asyncio.run(self._assistant.router.chat(request))
            return response.content.strip()

        try:
            result = toolbox.run_utility(utility_id, params, ai_runner=ai_runner)
        except Exception as exc:  # noqa: BLE001
            result = {"ok": False, "message": f"Falha inesperada: {exc}"}
        self._toolbox_result = result
        self._toolbox_busy = False
        self.toolboxChanged.emit()
        if result.get("ok"):
            self._set_status("FERRAMENTA CONCLUIDA")
        else:
            self._set_status("FERRAMENTA FALHOU")

    # -- editor visual de PDF -----------------------------------------
    @Slot(str, result="QVariantMap")
    def loadVisualPdf(self, path: str) -> dict:
        try:
            return toolbox.load_pdf_for_visual_edit(path)
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(str, "QVariantList", str, result="QVariantMap")
    def applyVisualPdfEdits(self, path: str, edits: list, output_path: str = "") -> dict:
        try:
            plain_edits = [dict(e) for e in edits]
            return toolbox.apply_visual_pdf_edits(path, plain_edits, output_path=output_path)
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(str, str, str, str, result="QVariantMap")
    def findAndReplacePdfText(self, path: str, find_text: str, replace_text: str, output_path: str = "") -> dict:
        try:
            return toolbox.find_and_replace_pdf_text(path, find_text, replace_text, output_path=output_path)
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(str, int, int, str, result="QVariantMap")
    def rotatePdfPage(self, path: str, page_index: int, angle: int = 90, output_path: str = "") -> dict:
        try:
            return toolbox.rotate_pdf_page(path, page_index, angle=angle, output_path=output_path)
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(str, int, str, result="QVariantMap")
    def deletePdfPage(self, path: str, page_index: int, output_path: str = "") -> dict:
        try:
            return toolbox.delete_pdf_page(path, page_index, output_path=output_path)
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(str, result="QVariantMap")
    def loadPdfPages(self, path: str) -> dict:
        try:
            return toolbox.load_pdf_pages(path)
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(str, str, str, result="QVariantMap")
    def exportPdfDocument(self, content: str, original_path: str = "", title: str = "") -> dict:
        try:
            return toolbox.export_text_to_pdf(content, original_path=original_path, title=title)
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(str, str, result=str)
    def askAiEdit(self, prompt_type: str, text: str) -> str:
        prompts = {
            "improve": (
                "Você é um editor de texto profissional. Melhore a clareza, coesão, gramática e "
                "profissionalismo do texto a seguir. Mantenha ou adicione tags HTML simples "
                "(<b>, <i>, <h2>, <h3>, <p>, <ul>, <li>) para enriquecer o visual. "
                "Responda apenas com o texto formatado."
            ),
            "summarize": (
                "Faça um resumo executivo bem estruturado do texto a seguir. "
                "Use títulos HTML (<h2>, <h3>), parágrafos (<p>) e tópicos (<ul>, <li>). "
                "Responda apenas com o texto formatado."
            ),
            "translate_en": (
                "Traduza o texto a seguir para Inglês profissional. Mantenha a formatação HTML. "
                "Responda apenas com o texto traduzido."
            ),
            "translate_es": (
                "Traduza o texto a seguir para Espanhol profissional. Mantenha a formatação HTML. "
                "Responda apenas com o texto traduzido."
            ),
            "formal": (
                "Reescreva o texto a seguir em tom formal, corporativo e elegante, "
                "adequado para documentos oficiais e relatórios executivos. "
                "Use parágrafos (<p>) e formatação HTML. Responda apenas com o texto."
            ),
        }
        system_prompt = prompts.get(prompt_type, "Melhore o texto mantendo a formatação HTML.")
        try:
            request = LLMRequest(
                messages=(
                    Message(role="system", content=system_prompt),
                    Message(role="user", content=text[:6000]),
                )
            )
            response = asyncio.run(self._assistant.router.chat(request))
            return response.content.strip()
        except Exception as e:
            return f"Erro ao processar com IA: {e}"

    # -- painel do Sistema --------------------------------------------
    @Property("QVariantMap", notify=systemPanelChanged)
    def systemSpecs(self) -> dict:
        return self._specs

    @Property("QVariantMap", notify=settingsChanged)
    def jarvisInfo(self) -> dict:
        database = self._assistant.database
        counts = database.stats()
        try:
            db_size = database.path.stat().st_size
        except OSError:
            db_size = 0
        provider = self._config.providers.get(self._config.default_provider)
        return {
            "version": self.appVersion,
            "provider": self._config.default_provider,
            "model": provider.model if provider else "",
            "dataDir": str(database.path.parent),
            "dbPath": str(database.path),
            "dbSize": sysinfo._fmt_bytes(db_size),
            "conversations": counts.get("conversations", 0),
            "messages": counts.get("messages", 0),
            "routines": counts.get("routines", 0),
            "appointments": counts.get("appointments", 0),
            "contacts": counts.get("contacts", 0),
        }

    @Property("QVariantList", notify=systemPanelChanged)
    def processList(self) -> list:
        return self._processes

    @Property("QVariantMap", notify=systemPanelChanged)
    def diskInfo(self) -> dict:
        return self._disks

    @Property("QVariantMap", notify=systemPanelChanged)
    def powerInfo(self) -> dict:
        return self._power

    @Property(bool, notify=systemPanelChanged)
    def systemBusy(self) -> bool:
        return self._sys_busy or self._disks_busy

    @Property(bool, notify=systemPanelChanged)
    def processBusy(self) -> bool:
        return self._proc_busy

    @Property(str, notify=systemPanelChanged)
    def systemMessage(self) -> str:
        return self._sys_message

    def _sys_thread(self, target, name: str) -> None:
        threading.Thread(target=target, daemon=True, name=name).start()

    @Slot()
    def refreshSpecs(self) -> None:
        if self._sys_busy:
            return
        self._sys_busy = True
        self.systemPanelChanged.emit()

        def work() -> None:
            try:
                self._specs = sysinfo.full_specs()
                self._power = sysinfo.power_status()
            except Exception:  # noqa: BLE001
                pass
            self._sys_busy = False
            self.systemPanelChanged.emit()

        self._sys_thread(work, "jarvis-specs")

    @Slot(str)
    def refreshProcesses(self, sort_by: str) -> None:
        if self._proc_busy:
            return
        self._proc_busy = True
        self.systemPanelChanged.emit()

        def work() -> None:
            try:
                self._processes = sysinfo.list_processes(sort_by or "cpu")
            except Exception:  # noqa: BLE001
                self._processes = []
            self._proc_busy = False
            self.systemPanelChanged.emit()

        self._sys_thread(work, "jarvis-procs")

    @Slot(int, str)
    def killProcess(self, pid: int, sort_by: str) -> None:
        def work() -> None:
            result = sysinfo.kill_process(int(pid))
            self._sys_message = result.get("message", "")
            self.systemPanelChanged.emit()
            self.messageAdded.emit(
                "system" if result.get("ok") else "error",
                self._sys_message,
                "SISTEMA / PROCESSOS",
            )
            self.refreshProcesses(sort_by or "cpu")

        self._sys_thread(work, "jarvis-kill")

    @Slot()
    def refreshDisks(self) -> None:
        if self._disks_busy:
            return
        self._disks_busy = True
        self.systemPanelChanged.emit()

        def work() -> None:
            try:
                self._disks = sysinfo.disks()
            except Exception:  # noqa: BLE001
                pass
            self._disks_busy = False
            self.systemPanelChanged.emit()

        self._sys_thread(work, "jarvis-disks")

    @Slot()
    def cleanTemp(self) -> None:
        def work() -> None:
            result = sysinfo.clean_temp()
            self._sys_message = result.get("message", "")
            self.messageAdded.emit(
                "system" if result.get("ok") else "error",
                self._sys_message, "SISTEMA / LIMPEZA",
            )
            self.refreshDisks()

        self._sys_thread(work, "jarvis-clean")

    @Slot()
    def emptyRecycleBin(self) -> None:
        def work() -> None:
            result = sysinfo.empty_recycle_bin()
            self._sys_message = result.get("message", "")
            self.messageAdded.emit(
                "system" if result.get("ok") else "error",
                self._sys_message, "SISTEMA / LIMPEZA",
            )
            self.refreshDisks()

        self._sys_thread(work, "jarvis-recycle")

    @Slot(str)
    def setPowerPlan(self, guid: str) -> None:
        def work() -> None:
            result = sysinfo.set_power_plan(guid)
            self._sys_message = result.get("message", "")
            self._power = sysinfo.power_status()
            self.systemPanelChanged.emit()
            self.messageAdded.emit(
                "system" if result.get("ok") else "error",
                self._sys_message, "SISTEMA / ENERGIA",
            )

        self._sys_thread(work, "jarvis-power")

    @Slot(str)
    def runQuickAction(self, action_id: str) -> None:
        def work() -> None:
            result = sysinfo.run_quick_action(action_id)
            self._sys_message = result.get("message", "")
            if self._sys_message:
                self.messageAdded.emit(
                    "system" if result.get("ok") else "error",
                    self._sys_message, "SISTEMA / AÇÕES",
                )
            self.systemPanelChanged.emit()

        self._sys_thread(work, "jarvis-quick")

    @Property(bool, notify=settingsChanged)
    def agentReadyForRoutines(self) -> bool:
        return self._config.agent.enabled

    @Slot(int, str, str, str)
    def saveRoutine(
        self, routine_id: int, name: str, description: str, steps_text: str
    ) -> None:
        name = (name or "").strip()
        if not name:
            self.messageAdded.emit(
                "error", "Dê um nome à rotina.", "AUTOMACAO"
            )
            return
        steps = tuple(
            line.strip()
            for line in (steps_text or "").splitlines()
            if line.strip()
        )
        if not steps:
            self.messageAdded.emit(
                "error", "A rotina precisa de pelo menos um passo.", "AUTOMACAO"
            )
            return
        try:
            self._assistant.database.save_routine(
                Routine(
                    id=routine_id if routine_id > 0 else None,
                    name=name,
                    description=(description or "").strip(),
                    steps=steps,
                    enabled=True,
                )
            )
        except Exception as exc:  # noqa: BLE001 - nome duplicado etc.
            self.messageAdded.emit(
                "error", f"Não consegui salvar a rotina: {exc}", "AUTOMACAO"
            )
            return
        self.routinesChanged.emit()
        self._set_status("ROTINA SALVA")
        self.messageAdded.emit(
            "system", f'Rotina "{name}" salva ({len(steps)} passo(s)).', "AUTOMACAO"
        )

    @Slot(int)
    def deleteRoutine(self, routine_id: int) -> None:
        routine = self._assistant.database.get_routine(int(routine_id))
        self._assistant.database.delete_routine(int(routine_id))
        self.routinesChanged.emit()
        if routine is not None:
            self.messageAdded.emit(
                "system", f'Rotina "{routine.name}" removida.', "AUTOMACAO"
            )

    @Slot(int)
    def runRoutine(self, routine_id: int) -> None:
        if self._busy or self._voice_state not in {"idle", "error"}:
            self.messageAdded.emit(
                "system", "Aguarde a ação atual terminar.", "AUTOMACAO"
            )
            return
        routine = self._assistant.database.get_routine(int(routine_id))
        self._launch_routine(routine, speak=False, echo=None)

    def _launch_routine(
        self, routine: Routine | None, *, speak: bool, echo: str | None
    ) -> None:
        if routine is None or not routine.steps:
            self.messageAdded.emit(
                "error", "Rotina inexistente ou sem passos.", "AUTOMACAO"
            )
            return
        if not self._config.agent.enabled:
            if echo:
                self.messageAdded.emit("user", echo, "VOCE")
            self.messageAdded.emit(
                "error",
                "As rotinas precisam do Agente ligado. Abra Configurações → "
                "Permissões e ative o agente.",
                "AUTOMACAO",
            )
            return
        if echo:
            self.messageAdded.emit("user", echo, "VOCE")
        self._set_busy(True)
        self._set_status("RODANDO ROTINA")
        threading.Thread(
            target=self._routine_worker,
            args=(routine, speak),
            daemon=True,
            name="jarvis-routine",
        ).start()

    def _routine_worker(self, routine: Routine, speak: bool) -> None:
        total = len(routine.steps)
        last_text = ""
        try:
            conversation_id = self._assistant.database.create_conversation(
                f"Rotina: {routine.name}"
            )
            confirm = self._make_confirm()
            self.messageAdded.emit(
                "system",
                f'Rotina "{routine.name}" — {total} passo(s).',
                "AUTOMACAO",
            )

            async def run_all() -> None:
                nonlocal last_text
                for index, step in enumerate(routine.steps, start=1):
                    self.messageAdded.emit(
                        "system", f"Passo {index}/{total}: {step}", "AUTOMACAO"
                    )
                    self._set_status(f"ROTINA {index}/{total}")
                    started = False
                    parts: list[str] = []
                    stream = self._assistant.ask_stream(
                        step,
                        conversation_id=conversation_id,
                        confirm=confirm,
                        on_event=self._agent_event,
                    )
                    async for delta in stream:
                        if not started:
                            started = True
                            self.streamStarted.emit(
                                f"ROTINA / {routine.name.upper()}"
                            )
                        parts.append(delta)
                        self.streamDelta.emit(delta)
                    reply = self._assistant.last_stream
                    step_text = (
                        reply.response.content if reply is not None else ""
                    ) or "".join(parts)
                    if started:
                        self.streamEnded.emit("")
                    if step_text.strip():
                        last_text = step_text.strip()

            asyncio.run(asyncio.wait_for(run_all(), timeout=120 * total + 60))

            self.messageAdded.emit(
                "system", f'Rotina "{routine.name}" concluída.', "AUTOMACAO"
            )
            self._set_status("SISTEMA PRONTO")
            if speak:
                self._speak_reply(f"Rotina {routine.name} concluída.")
            self._set_voice_state("idle")
        except TimeoutError:
            self.messageAdded.emit(
                "error",
                f'A rotina "{routine.name}" demorou demais e foi interrompida.',
                "AUTOMACAO",
            )
            self._set_status("ATENÇÃO NECESSÁRIA")
            self._set_voice_state("idle")
        except Exception as exc:  # noqa: BLE001
            self.messageAdded.emit(
                "error", f"Falha na rotina: {exc}", "AUTOMACAO"
            )
            self._set_status("ATENÇÃO NECESSÁRIA")
            self._set_voice_state("idle")
        finally:
            self._set_busy(False)

    @Slot(str)
    def saveWeatherCity(self, city: str) -> None:
        city = (city or "").strip()
        if not city or city == self._config.weather_city:
            return
        preferences = self._runtime_preferences()
        preferences["weather_city"] = city
        self._assistant.database.set_setting("runtime_preferences", preferences)
        self._config = replace(self._config, weather_city=city)
        self._notify_settings_changed()
        self._weather_wake.set()

    @Property(bool, notify=busyChanged)
    def busy(self) -> bool:
        return self._busy

    @Property(str, notify=statusChanged)
    def status(self) -> str:
        return self._status

    @Property(str, notify=providerChanged)
    def activeProvider(self) -> str:
        return self._active_provider

    @Property("QStringList", notify=settingsChanged)
    def providers(self) -> list[str]:
        return [
            "Automático",
            *[
                name
                for name, provider in self._config.providers.items()
                if provider.enabled
            ],
        ]

    @Property(str, notify=voiceStateChanged)
    def voiceState(self) -> str:
        return self._voice_state

    @Property(float, notify=voiceLevelChanged)
    def voiceLevel(self) -> float:
        return self._voice_level

    @Property(bool, notify=voiceStateChanged)
    def voiceAvailable(self) -> bool:
        return self._voice.available

    @Property(str, notify=voiceStateChanged)
    def voiceHint(self) -> str:
        hints = {
            "idle": "Clique para falar",
            "listening": "Ouvindo... clique para concluir",
            "transcribing": "Transcrevendo sua voz...",
            "thinking": "Preparando a resposta...",
            "speaking": "Jarvis esta falando...",
            "error": "Falha no recurso de voz",
        }
        if not self._config.voice.enabled:
            return "Voz desativada em config.toml"
        missing = missing_voice_dependencies()
        if missing:
            return "Instale o pacote de voz: .[full]"
        return hints.get(self._voice_state, "Clique para falar")

    @Property("QStringList", constant=True)
    def aiProviders(self) -> list[str]:
        return list(AI_PROVIDER_LABELS)

    @Property("QStringList", constant=True)
    def voiceEngines(self) -> list[str]:
        return ["Windows local", "Kokoro (local)", "Gemini TTS"]

    @Property("QStringList", constant=True)
    def transcriptionModels(self) -> list[str]:
        return ["tiny", "base", "small", "medium", "large-v3", "turbo"]

    @Property("QStringList", constant=True)
    def transcriptionEngines(self) -> list[str]:
        return ["Local (Whisper)", "OpenAI"]

    @Slot(str, result="QStringList")
    def transcriptionModelsFor(self, engine: str) -> list[str]:
        if engine == "OpenAI":
            return ["gpt-4o-transcribe", "gpt-4o-mini-transcribe", "whisper-1"]
        return ["tiny", "base", "small", "medium", "large-v3", "turbo"]

    @Property(str, notify=settingsChanged)
    def selectedTranscriptionEngine(self) -> str:
        return (
            "OpenAI"
            if self._config.voice.transcription_engine == "openai"
            else "Local (Whisper)"
        )

    @Property(str, notify=settingsChanged)
    def selectedTranscriptionModelCloud(self) -> str:
        return self._config.voice.transcription_cloud_model

    @Property(str, notify=settingsChanged)
    def selectedAiProvider(self) -> str:
        return AI_PROVIDER_NAMES.get(self._config.default_provider, "LM Studio")

    @Property(str, notify=settingsChanged)
    def selectedAiProviderKey(self) -> str:
        return self._config.default_provider

    @Property(str, notify=settingsChanged)
    def selectedAiModel(self) -> str:
        provider = self._config.providers.get(self._config.default_provider)
        return provider.model if provider else ""

    @Property(str, notify=settingsChanged)
    def selectedVoiceEngine(self) -> str:
        return {
            "gemini": "Gemini TTS",
            "kokoro": "Kokoro (local)",
        }.get(self._config.voice.tts_engine, "Windows local")

    @Property(str, notify=settingsChanged)
    def selectedVoiceModel(self) -> str:
        return self._config.voice.tts_model

    @Property(str, notify=settingsChanged)
    def selectedVoiceName(self) -> str:
        return self._config.voice.tts_voice

    @Property(str, notify=settingsChanged)
    def selectedTranscriptionModel(self) -> str:
        return self._config.voice.whisper_model

    @Property(bool, notify=settingsChanged)
    def wakeWordEnabled(self) -> bool:
        return self._config.voice.wake_word_enabled

    @Property(str, notify=settingsChanged)
    def wakeWord(self) -> str:
        return self._config.voice.wake_word

    @Property(bool, notify=settingsChanged)
    def wakeWordRequired(self) -> bool:
        return self._config.voice.wake_word_required

    # -- visão pela webcam -------------------------------------------
    @Property(bool, notify=settingsChanged)
    def webcamEnabled(self) -> bool:
        return self._config.vision.enabled

    @Property(int, notify=settingsChanged)
    def webcamIndex(self) -> int:
        return self._config.vision.camera_index

    @Property(bool, constant=True)
    def webcamSupported(self) -> bool:
        return visionmod.opencv_available()

    @Slot(bool, int)
    def saveWebcam(self, enabled: bool, camera_index: int) -> None:
        preferences = self._runtime_preferences()
        preferences["vision_enabled"] = bool(enabled)
        preferences["vision_camera_index"] = max(0, int(camera_index))
        self._assistant.database.set_setting("runtime_preferences", preferences)
        self._apply_runtime_preferences(preferences)
        self._notify_settings_changed()
        self._set_status("VISÃO ATUALIZADA")

    @Slot()
    def testWebcam(self) -> None:
        threading.Thread(
            target=self._webcam_test_worker, daemon=True, name="jarvis-webcam-test"
        ).start()

    def _webcam_test_worker(self) -> None:
        import base64 as _b64

        try:
            frame = visionmod.capture_frame(
                self._config.vision.camera_index,
                jpeg_quality=self._config.vision.jpeg_quality,
            )
        except visionmod.VisionError as exc:
            self.visionTested.emit("", str(exc))
            return
        data_uri = "data:image/jpeg;base64," + _b64.b64encode(frame.jpeg).decode("ascii")
        try:
            provider = self._config.providers.get(self._config.default_provider)
            answer = (
                visionmod.describe_scene(
                    "Descreva em uma ou duas frases o que você ve nesta imagem.",
                    frame,
                    provider,
                    timeout_seconds=self._config.vision.timeout_seconds,
                )
                if provider is not None
                else "(sem provedor de IA para descrever)"
            )
        except visionmod.VisionError as exc:
            answer = f"Imagem capturada, mas a IA não descreveu: {exc}"
        self.visionTested.emit(data_uri, answer)

    @Property(float, notify=settingsChanged)
    def voiceSilenceSeconds(self) -> float:
        prefs = self._runtime_preferences()
        return float(prefs.get("silence_seconds", self._config.voice.silence_seconds))

    @Property(str, notify=settingsChanged)
    def selectedVoiceSilenceLabel(self) -> str:
        sec = self.voiceSilenceSeconds
        if sec >= 900.0:
            return "Manual (só no clique)"
        if sec >= 4.5:
            return "Longo / Pensativo (5.0s)"
        if sec >= 3.2:
            return "Confortável (3.5s)"
        return "Normal (2.5s)"

    @Slot(bool, str, bool, str, str, str)
    def saveVoiceInput(
        self,
        wake_enabled: bool,
        wake_phrase: str,
        wake_required: bool,
        transcription_engine_label: str,
        transcription_model: str,
        silence_label: str = "Confortável (3.5s)",
    ) -> None:
        if self._busy or self._voice_state not in {"idle", "error"}:
            return
        engine = "openai" if transcription_engine_label == "OpenAI" else "local"
        if "Manual" in silence_label:
            silence_sec = 999.0
        elif "5.0s" in silence_label:
            silence_sec = 5.0
        elif "2.5s" in silence_label:
            silence_sec = 2.5
        else:
            silence_sec = 3.5

        preferences = self._runtime_preferences()
        preferences.update(
            {
                "wake_word_enabled": bool(wake_enabled),
                "wake_word": wake_phrase.strip() or "jarvis",
                "wake_word_required": bool(wake_required),
                "transcription_engine": engine,
                "silence_seconds": silence_sec,
                "speech_rms_threshold": 0.003,
            }
        )
        if engine == "openai":
            preferences["transcription_cloud_model"] = (
                transcription_model or "gpt-4o-transcribe"
            )
        else:
            preferences["whisper_model"] = transcription_model or "small"
        self._assistant.database.set_setting("runtime_preferences", preferences)
        self._apply_runtime_preferences(preferences)
        self._notify_settings_changed()

    @Property(bool, notify=settingsChanged)
    def geminiApiKeyConfigured(self) -> bool:
        return secret_configured(self._assistant.database, "GEMINI_API_KEY")

    @Property(int, notify=settingsChanged)
    def settingsRevision(self) -> int:
        return self._settings_revision

    # ---------------------------------------------- temas (claro / escuro)
    @Property(str, notify=themeChanged)
    def currentTheme(self) -> str:
        prefs = self._runtime_preferences()
        return str(prefs.get("theme", "dark")).lower()

    @Slot(str)
    def setTheme(self, theme_name: str) -> None:
        clean = (theme_name or "dark").strip().lower()
        if clean not in {"dark", "light"}:
            clean = "dark"
        prefs = self._runtime_preferences()
        if prefs.get("theme") == clean:
            return
        prefs["theme"] = clean
        self._assistant.database.set_setting("runtime_preferences", prefs)
        self.themeChanged.emit()
        self._notify_settings_changed()

    # ---------------------------------------------- nome do sistema / assistente
    @Property(str, notify=systemNameChanged)
    def systemName(self) -> str:
        prefs = self._runtime_preferences()
        name = str(prefs.get("system_name", "")).strip()
        return name if name else "Jarvis"

    @Slot(str)
    def setSystemName(self, name: str) -> None:
        clean = (name or "").strip()
        if not clean:
            clean = "Jarvis"
        prefs = self._runtime_preferences()
        if prefs.get("system_name") == clean:
            return
        prefs["system_name"] = clean
        self._assistant.database.set_setting("runtime_preferences", prefs)
        self.systemNameChanged.emit()
        self._notify_settings_changed()

    @Slot(str)
    def saveSystemName(self, name: str) -> None:
        self.setSystemName(name)

    # ---------------------------------------------- WhatsApp (Baileys v6.7.24)
    @Property(str, notify=whatsappStatusChanged)
    def whatsappStatus(self) -> str:
        return str(self._whatsapp_state.get("status", "disconnected"))

    @Property(str, notify=whatsappStatusChanged)
    def whatsappQrCode(self) -> str:
        return str(self._whatsapp_state.get("qrCode", ""))

    @Property(str, notify=whatsappStatusChanged)
    def whatsappUserPhone(self) -> str:
        user = self._whatsapp_state.get("user") or {}
        return str(user.get("phone", ""))

    @Property(str, notify=whatsappStatusChanged)
    def whatsappUserName(self) -> str:
        user = self._whatsapp_state.get("user") or {}
        return str(user.get("name", ""))

    @Property(bool, notify=whatsappStatusChanged)
    def whatsappConnected(self) -> bool:
        return bool(self._whatsapp_state.get("connected", False))

    @Property("QVariantList", notify=whatsappLogsChanged)
    def whatsappLogs(self) -> list:
        return list(self._whatsapp_state.get("logs", []))

    @Slot()
    def startWhatsApp(self) -> None:
        self._whatsapp.start_bridge()

    @Slot()
    def connectWhatsApp(self) -> None:
        self._whatsapp.connect()

    @Slot()
    def disconnectWhatsApp(self) -> None:
        self._whatsapp.disconnect()

    @Slot()
    def restartWhatsApp(self) -> None:
        self._whatsapp.stop_bridge()
        def _restart() -> None:
            import time
            time.sleep(1.0)
            self._whatsapp.start_bridge()
        threading.Thread(target=_restart, daemon=True).start()

    @Slot(str, str)
    def sendWhatsAppMessage(self, to: str, text: str) -> None:
        clean_to = (to or "").strip()
        clean_text = (text or "").strip()
        if not clean_to or not clean_text:
            self.messageAdded.emit("error", "Informe o destinatário e o texto da mensagem.", "WHATSAPP")
            return

        def _send() -> None:
            res = self._whatsapp.send_message(clean_to, clean_text)
            if res.get("success"):
                self.messageAdded.emit(
                    "system", f"Mensagem enviada com sucesso para {clean_to}!", "WHATSAPP"
                )
                self._whatsapp_state = self._whatsapp.get_status()
                self.whatsappLogsChanged.emit()
            else:
                err = res.get("error", "Erro desconhecido")
                self.messageAdded.emit("error", f"Falha ao enviar mensagem: {err}", "WHATSAPP")

        threading.Thread(target=_send, daemon=True).start()

    @Slot(str, str, str, str)
    def draftWhatsAppWithAI(
        self, contact_name: str, phone: str, instruction: str, tone: str
    ) -> None:
        clean_instr = (instruction or "").strip()
        if not clean_instr:
            self.messageAdded.emit("error", "Informe as instruções para a IA redigir a mensagem.", "WHATSAPP")
            return

        def _draft() -> None:
            self._set_status("REDIGINDO MENSAGEM COM IA...")
            prompt = (
                f"Você é o assistente {self.systemName}. Redija apenas o texto de uma mensagem de WhatsApp pronta para envio.\n"
                f"Destinatário: {contact_name or 'Contato'} (Telefone: {phone or 'N/A'})\n"
                f"Tom desejado: {tone or 'Amigável e profissional'}\n"
                f"Instrução do usuário: {clean_instr}\n\n"
                f"Regras: Retorne APENAS o texto da mensagem final, sem aspas adicionais, sem preâmbulo e sem saudações do tipo 'Aqui está sua mensagem'."
            )
            try:
                req = LLMRequest(
                    messages=[
                        Message(role="system", content=f"Você é {self.systemName}, um assistente inteligente."),
                        Message(role="user", content=prompt),
                    ],
                    temperature=0.7,
                )
                provider = self._assistant.current_provider()
                res = provider.chat(req)
                response_text = res.content.strip()
                if response_text:
                    self.whatsappDraftReady.emit(response_text)
                    self._set_status("MENSAGEM REDIGIDA")
                else:
                    self.messageAdded.emit("error", "A IA não retornou texto para a mensagem.", "WHATSAPP")
                    self._set_status("SISTEMA PRONTO")
            except Exception as exc:
                self.messageAdded.emit("error", f"Falha ao redigir mensagem com IA: {exc}", "WHATSAPP")
                self._set_status("SISTEMA PRONTO")

        threading.Thread(target=_draft, daemon=True).start()

    @Slot()
    def shutdown(self) -> None:
        if self._whatsapp:
            self._whatsapp.stop_bridge()
        if self._wake is not None:
            self._wake.stop()
            self._wake = None
        self._telemetry_stop.set()
        try:
            self._assistant.mcp.shutdown()
        except Exception:  # noqa: BLE001 - encerramento nunca derruba o app
            pass

    # ---------------------------------------------- Agentes de IA
    @Property("QVariantList", constant=True)
    def aiAgentProviders(self) -> list:
        return AI_AGENT_PROVIDERS

    @Slot(str, result="QVariantList")
    def aiAgentModels(self, provider: str) -> list:
        return AI_AGENT_MODELS.get(provider, ["default"])

    @Property("QVariantList", notify=aiAgentsChanged)
    def aiAgents(self) -> list:
        return self._assistant.database.list_ai_agents()

    @Slot(int, str, str, str, str, str, str, float, bool)
    def saveAiAgent(
        self,
        agent_id: int,
        name: str,
        provider: str,
        model: str,
        api_key: str,
        base_url: str,
        system_prompt: str,
        temperature: float,
        active: bool,
    ) -> None:
        agent_data = {
            "id": agent_id if agent_id > 0 else None,
            "name": (name or "Novo Agente").strip(),
            "provider": (provider or "OpenAI").strip(),
            "model": (model or "gpt-4o-mini").strip(),
            "api_key": (api_key or "").strip(),
            "base_url": (base_url or "").strip(),
            "system_prompt": (system_prompt or "").strip(),
            "temperature": float(temperature if temperature > 0 else 0.7),
            "active": bool(active),
        }
        self._assistant.database.save_ai_agent(agent_data)
        self.aiAgentsChanged.emit()
        self.messageAdded.emit(
            "system", f"Agente '{agent_data['name']}' salvo com sucesso.", "AGENTES DE IA"
        )

    @Slot(int)
    def deleteAiAgent(self, agent_id: int) -> None:
        self._assistant.database.delete_ai_agent(agent_id)
        self.aiAgentsChanged.emit()
        self.messageAdded.emit(
            "system", "Modelo de IA removido.", "AGENTES DE IA"
        )

    # ---------------------------------------------- Agentes de Atendimento (Comunicação)
    @Property("QVariantList", notify=communicationAgentsChanged)
    def communicationAgents(self) -> list:
        return self._assistant.database.list_communication_agents()

    @Slot(int, str, str, str, str, int, str, str, str, str, str, str, str, str, str, str, str, str, str, str, str, str, str, bool)
    def saveCommunicationAgent(
        self,
        agent_id: int,
        name: str,
        age: str,
        gender: str,
        role: str,
        model_id: int,
        model_name: str,
        tone: str,
        formality: str,
        emoji_level: str,
        response_style: str,
        language: str,
        job_description: str,
        responsibilities: str,
        company_name: str,
        company_segment: str,
        company_description: str,
        company_products: str,
        company_target_audience: str,
        company_regions: str,
        company_business_hours: str,
        company_payment_methods: str,
        company_policies: str,
        active: bool,
    ) -> None:
        agent_data = {
            "id": agent_id if agent_id > 0 else None,
            "name": (name or "Agente de IA").strip(),
            "age": (age or "").strip(),
            "gender": (gender or "").strip(),
            "role": (role or "").strip(),
            "model_id": int(model_id) if model_id and model_id > 0 else None,
            "model_name": (model_name or "").strip(),
            "tone": (tone or "").strip(),
            "formality": (formality or "").strip(),
            "emoji_level": (emoji_level or "Normal").strip(),
            "response_style": (response_style or "").strip(),
            "language": (language or "Português (Brasil)").strip(),
            "job_description": (job_description or "").strip(),
            "responsibilities": (responsibilities or "[]").strip(),
            "company_name": (company_name or "").strip(),
            "company_segment": (company_segment or "").strip(),
            "company_description": (company_description or "").strip(),
            "company_products": (company_products or "").strip(),
            "company_target_audience": (company_target_audience or "").strip(),
            "company_regions": (company_regions or "").strip(),
            "company_business_hours": (company_business_hours or "").strip(),
            "company_payment_methods": (company_payment_methods or "").strip(),
            "company_policies": (company_policies or "").strip(),
            "company_info": (company_description or "").strip(),
            "active": bool(active),
        }
        self._assistant.database.save_communication_agent(agent_data)
        self.communicationAgentsChanged.emit()
        self.messageAdded.emit(
            "system", f"Agente de IA '{agent_data['name']}' salvo com sucesso.", "COMUNICAÇÃO"
        )

    @Slot(int)
    def deleteCommunicationAgent(self, agent_id: int) -> None:
        self._assistant.database.delete_communication_agent(agent_id)
        self.communicationAgentsChanged.emit()
        self.messageAdded.emit(
            "system", "Agente de IA removido.", "COMUNICAÇÃO"
        )

    # ---------------------------------------------- Cognição, Memória & Sugestões Proativas Globais
    @Property("QVariantList", notify=learnedMemoriesChanged)
    def learnedMemories(self) -> list:
        return self._assistant.database.list_user_memories()

    @Property("QVariantMap", notify=behaviorProfileChanged)
    def behaviorProfile(self) -> dict:
        return self._assistant.database.get_behavior_profile()

    @Property("QVariantList", notify=proactiveSuggestionsChanged)
    def proactiveSuggestions(self) -> list:
        return self._assistant.cognition.proactive.generate_suggestions(
            self._current_view, sector=self.sector
        )

    @Property("QVariantMap", notify=personaChanged)
    def assistantPersona(self) -> dict:
        return self._assistant.database.get_assistant_persona()

    @Property("QVariantList", notify=mcpServersChanged)
    def mcpServers(self) -> list:
        return self._assistant.database.list_mcp_servers()

    @Slot(int, str, str, str)
    def saveLearnedMemory(self, memory_id: int, category: str, key: str, content: str) -> None:
        self._assistant.database.save_user_memory({
            "id": memory_id if memory_id > 0 else None,
            "category": (category or "fato").strip(),
            "key": (key or "").strip(),
            "content": (content or "").strip(),
            "confidence": 1.0,
            "source": "manual",
        })
        self.learnedMemoriesChanged.emit()
        self.messageAdded.emit(
            "system", "Memória salva no aprendizado contínuo do Jarvis.", "MEMÓRIA"
        )

    @Slot(int)
    def deleteLearnedMemory(self, memory_id: int) -> None:
        self._assistant.database.delete_user_memory(memory_id)
        self.learnedMemoriesChanged.emit()
        self.messageAdded.emit(
            "system", "Memória removida do aprendizado.", "MEMÓRIA"
        )

    @Slot()
    def clearLearnedMemories(self) -> None:
        self._assistant.database.clear_user_memories()
        self.learnedMemoriesChanged.emit()
        self.messageAdded.emit(
            "system", "Todas as memórias do Jarvis foram redefinidas.", "MEMÓRIA"
        )

    @Slot()
    def refreshCognition(self) -> None:
        self.learnedMemoriesChanged.emit()
        self.behaviorProfileChanged.emit()
        self.proactiveSuggestionsChanged.emit()

    # ---------------------------------------------- Personalização (persona)
    @Property("QVariantList", constant=True)
    def personalityOptions(self) -> list:
        return list(_PERSONALITY_LABELS)

    @Property("QVariantList", constant=True)
    def toneOptions(self) -> list:
        return list(_TONE_LABELS)

    @Property("QVariantList", constant=True)
    def accentOptions(self) -> list:
        return list(_ACCENT_LABELS)

    @Slot(str, str, str, str, str, int, float, str)
    def savePersona(
        self,
        name: str,
        personality: str,
        tone: str,
        accent: str,
        tts_voice: str,
        tts_rate: int,
        tts_volume: float,
        custom_instructions: str,
    ) -> None:
        if self._busy:
            self.messageAdded.emit(
                "error", "Aguarde a operação atual terminar.", "PERSONALIZAÇÃO"
            )
            return
        name = (name or "Jarvis").strip() or "Jarvis"
        try:
            self._assistant.database.save_assistant_persona(
                {
                    "name": name,
                    "personality": (personality or "").strip() or "Prestativo e Amigável",
                    "tone": (tone or "").strip() or "Natural",
                    "accent": (accent or "").strip() or "Português (Brasil)",
                    "tts_voice": (tts_voice or "").strip(),
                    "tts_rate": max(80, min(int(tts_rate or 180), 320)),
                    "tts_volume": max(0.1, min(float(tts_volume or 1.0), 1.0)),
                    "custom_instructions": (custom_instructions or "").strip(),
                }
            )
        except Exception as exc:  # noqa: BLE001
            self.messageAdded.emit("error", f"Não consegui salvar: {exc}", "PERSONALIZAÇÃO")
            return
        # aplica a voz da persona no serviço de voz
        prefs = self._runtime_preferences()
        if (tts_voice or "").strip():
            prefs["tts_voice"] = tts_voice.strip()
        prefs["tts_rate"] = max(80, min(int(tts_rate or 180), 320))
        prefs["tts_volume"] = max(0.1, min(float(tts_volume or 1.0), 1.0))
        self._assistant.database.set_setting("runtime_preferences", prefs)
        self._apply_runtime_preferences(prefs)
        self.personaChanged.emit()
        self._notify_settings_changed()
        self._set_status(f"PERSONALIZAÇÃO: {name.upper()}")
        self.messageAdded.emit(
            "system",
            f"Pode me chamar de {name}. Personalidade e voz atualizadas.",
            "PERSONALIZAÇÃO",
        )

    # ---------------------------------------------- MCP (Model Context Protocol)
    @Slot(int, str, str, str, str, bool)
    def saveMcpServer(
        self,
        server_id: int,
        name: str,
        command: str,
        args: str,
        env_json: str,
        enabled: bool,
    ) -> None:
        import json as _json

        name = (name or "").strip()
        command = (command or "").strip()
        if not name or not command:
            self.messageAdded.emit(
                "error", "Preencha o nome e o comando do servidor MCP.", "MCP"
            )
            return
        args = (args or "").strip()
        if args and not args.startswith("["):
            args = _json.dumps(args.split())  # "a b c" -> ["a","b","c"]
        env_json = (env_json or "").strip() or "{}"
        try:
            _json.loads(args or "[]")
            _json.loads(env_json)
        except ValueError:
            self.messageAdded.emit(
                "error", "Args ou variáveis de ambiente em formato inválido (JSON).", "MCP"
            )
            return
        try:
            self._assistant.database.save_mcp_server(
                {
                    "id": server_id if server_id and server_id > 0 else None,
                    "name": name,
                    "command": command,
                    "args": args or "[]",
                    "env_vars": env_json,
                    "enabled": bool(enabled),
                }
            )
        except Exception as exc:  # noqa: BLE001
            self.messageAdded.emit("error", f"Não consegui salvar: {exc}", "MCP")
            return
        self._assistant.mcp.invalidate()
        self.mcpServersChanged.emit()
        self._set_status("SERVIDOR MCP SALVO")

    @Slot(int)
    def deleteMcpServer(self, server_id: int) -> None:
        self._assistant.database.delete_mcp_server(int(server_id))
        self._assistant.mcp.invalidate()
        self.mcpServersChanged.emit()
        self.messageAdded.emit("system", "Servidor MCP removido.", "MCP")

    @Slot("QVariantMap")
    def testMcpServer(self, server) -> None:
        payload = {str(k): v for k, v in dict(server).items()}
        self._set_status("TESTANDO MCP")
        threading.Thread(
            target=self._mcp_test_worker,
            args=(payload,),
            daemon=True,
            name="jarvis-mcp-test",
        ).start()

    def _mcp_test_worker(self, server: dict) -> None:
        result = self._assistant.mcp.probe(server)
        self.mcpTested.emit(result)
        self._set_status(
            "MCP CONECTADO" if result.get("ok") else "MCP FALHOU"
        )

    @Slot(str)
    def executeProactiveSuggestion(self, action_text: str) -> None:
        if not action_text:
            return
        self.composeRequested.emit(action_text)
        if self._current_view != "hub":
            self.setView("hub")

    # ---------------------------------------------- Controle de Mídia Mãos-Livres
    @Slot()
    def mediaPlayPause(self) -> None:
        from jarvis.tools.media_control import VK_MEDIA_PLAY_PAUSE, _send_media_key
        _send_media_key(VK_MEDIA_PLAY_PAUSE)

    @Slot()
    def mediaNextTrack(self) -> None:
        from jarvis.tools.media_control import VK_MEDIA_NEXT_TRACK, _send_media_key
        _send_media_key(VK_MEDIA_NEXT_TRACK)

    @Slot()
    def mediaPrevTrack(self) -> None:
        from jarvis.tools.media_control import VK_MEDIA_PREV_TRACK, _send_media_key
        _send_media_key(VK_MEDIA_PREV_TRACK)

    @Slot()
    def mediaMute(self) -> None:
        from jarvis.tools.media_control import VK_VOLUME_MUTE, _send_media_key
        _send_media_key(VK_VOLUME_MUTE)

    @Slot()
    def volumeUp(self) -> None:
        from jarvis.tools.media_control import VK_VOLUME_UP, _send_media_key
        _send_media_key(VK_VOLUME_UP)
        _send_media_key(VK_VOLUME_UP)

    @Slot()
    def volumeDown(self) -> None:
        from jarvis.tools.media_control import VK_VOLUME_DOWN, _send_media_key
        _send_media_key(VK_VOLUME_DOWN)
        _send_media_key(VK_VOLUME_DOWN)

    @Slot(str, str, str, str)
    def testAiModelConnection(
        self, provider: str, model: str, api_key: str, base_url: str
    ) -> None:
        def _test() -> None:
            clean_prov = (provider or "OpenAI").strip()
            clean_mod = (model or "gpt-4o-mini").strip()
            clean_key = (api_key or "").strip()
            clean_url = (base_url or "").strip()

            import urllib.request
            import urllib.error
            import json

            try:
                if clean_prov == "OpenAI":
                    if not clean_key:
                        self.aiAgentTestResult.emit(False, "Chave de API da OpenAI não informada.")
                        return
                    req = urllib.request.Request(
                        "https://api.openai.com/v1/chat/completions",
                        data=json.dumps({
                            "model": clean_mod,
                            "messages": [{"role": "user", "content": "ping"}],
                            "max_tokens": 5
                        }).encode("utf-8"),
                        headers={
                            "Authorization": f"Bearer {clean_key}",
                            "Content-Type": "application/json"
                        },
                        method="POST"
                    )
                    with urllib.request.urlopen(req, timeout=10.0) as resp:
                        res = json.loads(resp.read().decode("utf-8"))
                        if "choices" in res:
                            self.aiAgentTestResult.emit(True, f"Conexão com OpenAI ({clean_mod}) bem sucedida!")
                        else:
                            self.aiAgentTestResult.emit(True, "Conexão estabelecida com sucesso.")

                elif clean_prov == "Anthropic":
                    if not clean_key:
                        self.aiAgentTestResult.emit(False, "Chave de API da Anthropic não informada.")
                        return
                    req = urllib.request.Request(
                        "https://api.anthropic.com/v1/messages",
                        data=json.dumps({
                            "model": clean_mod,
                            "messages": [{"role": "user", "content": "ping"}],
                            "max_tokens": 5
                        }).encode("utf-8"),
                        headers={
                            "x-api-key": clean_key,
                            "anthropic-version": "2023-06-01",
                            "Content-Type": "application/json"
                        },
                        method="POST"
                    )
                    with urllib.request.urlopen(req, timeout=10.0) as resp:
                        res = json.loads(resp.read().decode("utf-8"))
                        if "content" in res:
                            self.aiAgentTestResult.emit(True, f"Conexão com Anthropic ({clean_mod}) bem sucedida!")
                        else:
                            self.aiAgentTestResult.emit(True, "Conexão estabelecida com sucesso.")

                elif clean_prov == "Gemini":
                    if not clean_key:
                        self.aiAgentTestResult.emit(False, "Chave de API do Gemini não informada.")
                        return
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{clean_mod}:generateContent?key={clean_key}"
                    req = urllib.request.Request(
                        url,
                        data=json.dumps({
                            "contents": [{"parts": [{"text": "ping"}]}]
                        }).encode("utf-8"),
                        headers={"Content-Type": "application/json"},
                        method="POST"
                    )
                    with urllib.request.urlopen(req, timeout=10.0) as resp:
                        res = json.loads(resp.read().decode("utf-8"))
                        if "candidates" in res:
                            self.aiAgentTestResult.emit(True, f"Conexão com Gemini ({clean_mod}) bem sucedida!")
                        else:
                            self.aiAgentTestResult.emit(True, "Conexão estabelecida com sucesso.")

                elif clean_prov in {"Groq", "OpenRouter", "LM Studio", "Ollama"}:
                    target_url = clean_url
                    if not target_url:
                        if clean_prov == "Groq":
                            target_url = "https://api.groq.com/openai/v1/chat/completions"
                        elif clean_prov == "OpenRouter":
                            target_url = "https://openrouter.ai/api/v1/chat/completions"
                        elif clean_prov == "LM Studio":
                            target_url = "http://localhost:1234/v1/chat/completions"
                        elif clean_prov == "Ollama":
                            target_url = "http://localhost:11434/v1/chat/completions"

                    headers = {"Content-Type": "application/json"}
                    if clean_key:
                        headers["Authorization"] = f"Bearer {clean_key}"

                    req = urllib.request.Request(
                        target_url,
                        data=json.dumps({
                            "model": clean_mod,
                            "messages": [{"role": "user", "content": "ping"}],
                            "max_tokens": 5
                        }).encode("utf-8"),
                        headers=headers,
                        method="POST"
                    )
                    with urllib.request.urlopen(req, timeout=10.0) as resp:
                        res = json.loads(resp.read().decode("utf-8"))
                        if "choices" in res or "message" in res:
                            self.aiAgentTestResult.emit(True, f"Conexão com {clean_prov} ({clean_mod}) bem sucedida!")
                        else:
                            self.aiAgentTestResult.emit(True, f"Conexão com {clean_prov} respondendo.")

                else:
                    self.aiAgentTestResult.emit(True, f"Provedor {clean_prov} configurado.")

            except urllib.error.HTTPError as err:
                try:
                    err_msg = json.loads(err.read().decode("utf-8"))
                    msg = err_msg.get("error", {}).get("message") or err_msg.get("message") or str(err_msg)
                    self.aiAgentTestResult.emit(False, f"Erro HTTP {err.code}: {msg}")
                except Exception:
                    self.aiAgentTestResult.emit(False, f"Erro HTTP {err.code}: {err.reason}")
            except Exception as exc:
                self.aiAgentTestResult.emit(False, f"Falha de conexão: {exc}")

        threading.Thread(target=_test, daemon=True).start()

    # ---------------------------------------------- perfis de uso
    @Property("QVariantList", constant=True)
    def usageProfiles(self) -> list:
        return profilesmod.profile_choices()

    @Property(str, notify=profileChanged)
    def usageProfile(self) -> str:
        prefs = self._runtime_preferences()
        return str(prefs.get("usage_profile", profilesmod.DEFAULT_PROFILE))

    @Property("QVariantMap", notify=profileChanged)
    def usageProfileInfo(self) -> dict:
        prefs = self._runtime_preferences()
        profile = profilesmod.get_profile(
            str(prefs.get("usage_profile", profilesmod.DEFAULT_PROFILE))
        )
        info = dict(profile.as_dict())
        info["devFolder"] = str(prefs.get("dev_folder", "")).strip()
        return info

    @Property(str, notify=profileChanged)
    def devFolder(self) -> str:
        return str(self._runtime_preferences().get("dev_folder", "")).strip()

    @Slot(str)
    def setProfile(self, profile_id: str) -> None:
        self._apply_profile(profile_id, folder=None)

    @Slot(str, str)
    def setProfileFolder(self, profile_id: str, folder: str) -> None:
        self._apply_profile(profile_id, folder=(folder or "").strip())

    def _apply_profile(self, profile_id: str, *, folder: str | None) -> None:
        if self._busy or self._voice_state not in {"idle", "error"}:
            self.messageAdded.emit(
                "error", "Aguarde a operação atual terminar para trocar de perfil.",
                "PERFIL",
            )
            return
        profile = profilesmod.get_profile(profile_id)
        prefs = self._runtime_preferences()
        chosen_folder = folder if folder is not None else str(
            prefs.get("dev_folder", "")
        ).strip()

        if profile.needs_folder:
            valid = bool(chosen_folder) and Path(chosen_folder).expanduser().is_dir()
            if not valid:
                self.profileFolderNeeded.emit(profile.id)
                return
            prefs["dev_folder"] = str(Path(chosen_folder).expanduser())
            chosen_folder = prefs["dev_folder"]

        prefs["usage_profile"] = profile.id
        prefs.update(profile.permission_prefs(folder=chosen_folder))
        self._assistant.database.set_setting("runtime_preferences", prefs)
        self._apply_runtime_preferences(prefs)
        self.profileChanged.emit()
        self._notify_settings_changed()
        self._set_status(f"PERFIL: {profile.name.upper()}")

        caps = "\n".join(f"• {item}" for item in profile.capabilities)
        folder_line = (
            f"\nPasta de trabalho: {chosen_folder}" if profile.needs_folder else ""
        )
        self.messageAdded.emit(
            "system",
            f"{profile.icon} Perfil ativo: {profile.name}.\n{profile.description}"
            f"{folder_line}\n\n{caps}",
            "PERFIL DE USO",
        )

    # ---------------------------------------------- setor / ramo de atividade
    @Property("QVariantList", constant=True)
    def sectorChoices(self) -> list:
        return sectorsmod.sector_choices()

    @Property(str, notify=sectorChanged)
    def sector(self) -> str:
        return str(self._runtime_preferences().get("sector", sectorsmod.DEFAULT_SECTOR))

    @Property("QVariantMap", notify=sectorChanged)
    def sectorInfo(self) -> dict:
        return dict(sectorsmod.get_sector(self.sector).as_dict())

    @Property("QVariantList", notify=sectorChanged)
    def hiddenViews(self) -> list:
        return sectorsmod.hidden_views(self.sector)

    @Property("QVariantList", notify=sectorChanged)
    def hiddenProfiles(self) -> list:
        return sectorsmod.hidden_profiles(self.sector)

    @Property("QVariantList", notify=sectorChanged)
    def navItems(self) -> list:
        return sectorsmod.nav_items(self.sector)

    @Property("QVariantMap", notify=sectorChanged)
    def viewLabels(self) -> dict:
        return {k: v for k, v in sectorsmod.get_sector(self.sector).view_labels}

    @Slot(str)
    def setSector(self, sector_id: str) -> None:
        if self._busy or self._voice_state not in {"idle", "error"}:
            self.messageAdded.emit(
                "error", "Aguarde a operação atual terminar para trocar de setor.",
                "SETOR",
            )
            return
        sector = sectorsmod.get_sector(sector_id)
        prefs = self._runtime_preferences()
        prefs["sector"] = sector.id
        self._assistant.database.set_setting("runtime_preferences", prefs)
        self._apply_runtime_preferences(prefs)
        self.sectorChanged.emit()
        self.proactiveSuggestionsChanged.emit()
        self._notify_settings_changed()
        # se a tela atual sumiu do menu deste setor, volta pro HUB
        nav_keys = {n["key"] for n in sector.nav_items()}
        if self._current_view != "hub" and self._current_view not in nav_keys:
            self.setView("hub")
        if self._current_view in sector.hidden_views:
            self.setView("hub")
        self._set_status(f"SETOR: {sector.name.upper()}")
        caps = "\n".join(f"• {item}" for item in sector.capabilities)
        self.messageAdded.emit(
            "system",
            f"{sector.icon} Setor ativo: {sector.name}.\n{sector.description}"
            f"\n\n{caps}",
            "SETOR DE ATIVIDADE",
        )

    # ---------------------------------------------- painel de saúde
    @Property("QVariantList", constant=True)
    def healthActions(self) -> list:
        return saudemod.health_actions()

    @Slot(str, "QVariantMap")
    def runHealthAction(self, action_id: str, params) -> None:
        if self._busy or self._voice_state not in {"idle", "error"}:
            self.messageAdded.emit(
                "error", "Aguarde a operação atual terminar.", "SAÚDE"
            )
            return
        pdict = {str(k): str(v) for k, v in dict(params).items()}
        action = saudemod.get_action(action_id)
        if action is None:
            self.messageAdded.emit("error", "Ação desconhecida.", "SAÚDE")
            return
        try:
            prompt = saudemod.build_prompt(action_id, pdict)
        except (KeyError, ValueError) as exc:
            self.messageAdded.emit("error", str(exc), "SAÚDE")
            return
        self.messageAdded.emit("user", f"{action.icon} {action.label}", "VOCÊ")
        self._set_busy(True)
        self._set_status("APOIO CLÍNICO")
        threading.Thread(
            target=self._request_worker,
            args=(prompt, None, False),
            daemon=True,
            name="jarvis-saude",
        ).start()

    # ---------------------------------------------- pacientes (setor Saúde)
    @Property("QVariantList", notify=patientsChanged)
    def patients(self) -> list:
        return self._decorate_patients(self._assistant.database.list_patients())

    @Slot(str, result="QVariantList")
    def searchPatients(self, term: str) -> list:
        return self._decorate_patients(
            self._assistant.database.list_patients(term or "")
        )

    def _decorate_patients(self, rows: list) -> list:
        out = []
        for r in rows:
            age = patientsmod.age_from(r.get("birthdate", ""))
            out.append({
                **r,
                "age": age if age is not None else -1,
                "ageLabel": f"{age} anos" if age is not None else "",
            })
        return out

    @Slot("QVariantMap", result=int)
    def savePatient(self, data) -> int:
        d = {str(k): v for k, v in dict(data).items()}
        name = str(d.get("name", "")).strip()
        if not name:
            self.messageAdded.emit("error", "O paciente precisa de um nome.", "PACIENTES")
            return 0
        pid = self._assistant.database.save_patient(d)
        self.patientsChanged.emit()
        self._set_status("PACIENTE SALVO")
        self.messageAdded.emit("system", f'Paciente "{name}" salvo no cadastro.', "PACIENTES")
        return pid

    @Slot(int)
    def deletePatient(self, patient_id: int) -> None:
        self._assistant.database.delete_patient(int(patient_id))
        try:  # limpa os anexos daquele paciente do disco
            folder = (
                Path(self._assistant.database.path).resolve().parent
                / "patient_files" / str(int(patient_id))
            )
            if folder.is_dir():
                shutil.rmtree(folder, ignore_errors=True)
        except Exception:  # noqa: BLE001
            pass
        self.patientsChanged.emit()
        self.patientRecordsChanged.emit()
        self.messageAdded.emit("system", "Paciente e prontuário removidos.", "PACIENTES")

    @Slot(int, result="QVariantMap")
    def patientDetail(self, patient_id: int) -> dict:
        p = self._assistant.database.get_patient(int(patient_id))
        if not p:
            return {}
        age = patientsmod.age_from(p.get("birthdate", ""))
        return {**p, "age": age if age is not None else -1,
                "ageLabel": f"{age} anos" if age is not None else ""}

    # -------- registros do prontuário (timeline) --------
    @Slot(int, result="QVariantList")
    def patientRecords(self, patient_id: int) -> list:
        import json as _json
        out = []
        for r in self._assistant.database.list_patient_records(int(patient_id)):
            files = self._assistant.database.list_record_files(r["id"])
            risk = ""
            try:
                risk = str(_json.loads(r.get("ai_json") or "{}").get("nivel_risco", "")).lower()
            except (ValueError, AttributeError):
                pass
            out.append({
                **r,
                "kindLabel": patientsmod.kind_label(r.get("kind", "")),
                "vitalsLabel": patientsmod.format_vitals(r.get("vitals", "")),
                "fileCount": len(files),
                "analyzed": bool((r.get("ai_summary") or "").strip()),
                "risk": risk if risk in ("baixo", "moderado", "alto", "critico") else "",
            })
        return out

    @Slot(int, result="QVariantMap")
    def recordDetail(self, record_id: int) -> dict:
        r = self._assistant.database.get_patient_record(int(record_id))
        if not r:
            return {}
        import json as _json
        analysis = {}
        try:
            analysis = _json.loads(r.get("ai_json") or "{}")
        except ValueError:
            pass
        full = ""
        if analysis:
            full, _, _ = patientsmod.format_analysis(analysis)
        return {
            **r,
            "kindLabel": patientsmod.kind_label(r.get("kind", "")),
            "vitalsLabel": patientsmod.format_vitals(r.get("vitals", "")),
            "aiFull": full or (r.get("ai_summary") or ""),
            "risk": str(analysis.get("nivel_risco", "")).lower() if analysis else "",
        }

    @Property("QVariantList", constant=True)
    def recordKinds(self) -> list:
        return [{"id": k, "label": v} for k, v in patientsmod.RECORD_KINDS]

    @Property("QVariantList", constant=True)
    def vitalFields(self) -> list:
        return [{"key": k, "label": lbl, "unit": u} for k, lbl, u in patientsmod.VITALS]

    @Slot(int, result="QVariantList")
    def recordFiles(self, record_id: int) -> list:
        out = []
        for f in self._assistant.database.list_record_files(int(record_id)):
            out.append({
                "id": f["id"], "name": f["name"], "mime": f["mime"],
                "size": f["size"], "sizeLabel": attachmentsmod.human_size(f["size"]),
                "hasText": bool((f.get("extracted_text") or "").strip()),
                "path": f["path"],
            })
        return out

    @Slot("QVariantMap", result=int)
    def saveRecord(self, data) -> int:
        d = {str(k): v for k, v in dict(data).items()}
        try:
            patient_id = int(d.get("patient_id") or 0)
        except (TypeError, ValueError):
            patient_id = 0
        if not d.get("id") and patient_id <= 0:
            self.messageAdded.emit("error", "Escolha um paciente para o registro.", "PRONTUÁRIO")
            return 0
        rid = self._assistant.database.save_patient_record(d)
        self.patientRecordsChanged.emit()
        self.recordSaved.emit(rid)
        self._set_status("REGISTRO SALVO")
        return rid

    @Slot(int)
    def deleteRecord(self, record_id: int) -> None:
        for f in self._assistant.database.list_record_files(int(record_id)):
            self._remove_managed_file(f.get("path", ""))
        self._assistant.database.delete_patient_record(int(record_id))
        self.patientRecordsChanged.emit()
        self.messageAdded.emit("system", "Registro removido do prontuário.", "PRONTUÁRIO")

    @Slot(int, int, str)
    def attachToRecord(self, record_id: int, patient_id: int, file_path: str) -> None:
        raw = window_url_to_path(file_path)
        src = Path(raw).expanduser()
        if not src.is_file():
            self.messageAdded.emit("error", f"Arquivo não encontrado: {raw}", "PRONTUÁRIO")
            return
        att = attachmentsmod.load_attachment(str(src))
        if not att.ok:
            self.messageAdded.emit("error", f"Não consegui ler o anexo: {att.error}", "PRONTUÁRIO")
            return
        try:
            dest = self._managed_dir(patient_id) / f"{uuid.uuid4().hex[:8]}_{src.name}"
            shutil.copy2(src, dest)
        except Exception as exc:  # noqa: BLE001
            self.messageAdded.emit("error", f"Falha ao guardar o anexo: {exc}", "PRONTUÁRIO")
            return
        self._assistant.database.add_record_file({
            "record_id": int(record_id),
            "patient_id": int(patient_id),
            "name": src.name,
            "path": str(dest),
            "mime": att.kind,
            "size": att.size,
            "extracted_text": att.text or (
                f"[imagem anexada: {src.name}]" if att.kind == "image" else ""
            ),
        })
        self.patientRecordsChanged.emit()
        self._set_status("ANEXO ADICIONADO")

    @Slot(int)
    def deleteRecordFile(self, file_id: int) -> None:
        f = self._assistant.database.get_record_file(int(file_id))
        if f:
            self._remove_managed_file(f.get("path", ""))
        self._assistant.database.delete_record_file(int(file_id))
        self.patientRecordsChanged.emit()

    def _managed_dir(self, patient_id: int) -> Path:
        base = Path(self._assistant.database.path).resolve().parent / "patient_files"
        d = base / str(int(patient_id))
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _remove_managed_file(self, path: str) -> None:
        try:
            p = Path(path)
            if p.is_file() and "patient_files" in p.parts:
                p.unlink()
        except Exception:  # noqa: BLE001
            pass

    # -------- IA lê o laudo e faz o "segundo olhar" --------
    @Slot(int)
    def analyzeRecord(self, record_id: int) -> None:
        if self._busy or self._voice_state not in {"idle", "error"}:
            self.messageAdded.emit("error", "Aguarde a operação atual terminar.", "APOIO CLÍNICO")
            return
        record = self._assistant.database.get_patient_record(int(record_id))
        if not record:
            self.messageAdded.emit("error", "Registro não encontrado.", "APOIO CLÍNICO")
            return
        patient = self._assistant.database.get_patient(record["patient_id"]) or {}
        files = self._assistant.database.list_record_files(int(record_id))
        texts = [f.get("extracted_text", "") for f in files]
        if not (record.get("body") or "").strip() and not any(t.strip() for t in texts):
            self.messageAdded.emit(
                "error",
                "Este registro não tem texto nem anexo legível para a IA analisar.",
                "APOIO CLÍNICO",
            )
            return
        history = self._assistant.database.list_patient_records(record["patient_id"])
        self._set_busy(True)
        self._set_status("SEGUNDO OLHAR DA IA")
        self.messageAdded.emit(
            "user",
            f"🩺 Analisar {patientsmod.kind_label(record.get('kind',''))}: "
            f"{record.get('title') or '(sem título)'} — {patient.get('name','paciente')}",
            "VOCÊ",
        )
        threading.Thread(
            target=self._analyze_record_worker,
            args=(int(record_id), patient, history, record, texts),
            daemon=True,
            name="jarvis-analyze-record",
        ).start()

    def _analyze_record_worker(self, record_id, patient, history, record, texts) -> None:
        system, user = patientsmod.analyze_record_prompt(
            patient, history, record, texts
        )
        try:
            request = LLMRequest(
                messages=(
                    Message(role="system", content=system),
                    Message(role="user", content=user),
                ),
                max_output_tokens=2500,
                temperature=0.2,
            )
            response = asyncio.run(self._assistant.router.chat(request))
            content = (response.content or "").strip()
        except Exception as exc:  # noqa: BLE001
            self.messageAdded.emit("error", f"Falha na análise: {exc}", "APOIO CLÍNICO")
            self._set_busy(False)
            self._set_status("ATENÇÃO NECESSÁRIA")
            return
        if not content:
            self.messageAdded.emit("error", "A IA não retornou análise.", "APOIO CLÍNICO")
            self._set_busy(False)
            self._set_status("ATENÇÃO NECESSÁRIA")
            return
        analysis = patientsmod.parse_analysis(content)
        full, resumo, flags = patientsmod.format_analysis(analysis)
        import json as _json
        self._assistant.database.set_record_ai(
            record_id, resumo or full, flags, _json.dumps(analysis, ensure_ascii=False)
        )
        self.patientRecordsChanged.emit()
        self.messageAdded.emit(
            "system",
            f"{full}\n\n— Análise salva no prontuário.",
            "APOIO CLÍNICO / SEGUNDO OLHAR",
        )
        self._set_busy(False)
        self._set_status("SISTEMA PRONTO")

    # -------- consultas rápidas offline (base local PROMEDIS) --------
    @Slot(str, result="QVariantList")
    def checkDrugInteractions(self, meds_text: str) -> list:
        meds = [m.strip() for m in re.split(r"[,\n;]+", meds_text or "") if m.strip()]
        return medknowmod.check_interactions(meds)

    @Slot(str, result="QVariantList")
    def searchCid(self, query: str) -> list:
        return medknowmod.cid_search(query or "", limit=25)

    # ---------------------------------------------- painel de ciberseguranca
    @Property("QVariantList", constant=True)
    def securityActions(self) -> list:
        return netsecmod.security_actions()

    @Slot(str, "QVariantMap")
    def runSecurityAction(self, action_id: str, params) -> None:
        if self._busy or self._voice_state not in {"idle", "error"}:
            self.messageAdded.emit(
                "error", "Aguarde a operação atual terminar.", "SEGURANÇA"
            )
            return
        pdict = {str(k): str(v) for k, v in dict(params).items()}
        action = netsecmod.get_action(action_id)
        if action is None:
            self.messageAdded.emit("error", "Ação desconhecida.", "SEGURANÇA")
            return
        try:  # valida os campos obrigatórios
            netsecmod.build_prompt(action_id, pdict)
        except (KeyError, ValueError) as exc:
            self.messageAdded.emit("error", str(exc), "SEGURANÇA")
            return
        alvo = (pdict.get("alvo") or pdict.get("ip") or pdict.get("dominio")
                or pdict.get("url") or "")
        self.messageAdded.emit(
            "user",
            f"{action.icon} {action.label}" + (f": {alvo}" if alvo else ""),
            "VOCÊ",
        )
        self._set_busy(True)
        self._set_status("RECON DE SEGURANÇA")
        threading.Thread(
            target=self._netsec_worker,
            args=(action_id, pdict, action.label),
            daemon=True,
            name="jarvis-netsec",
        ).start()

    def _netsec_worker(self, action_id: str, params: dict, label: str) -> None:
        try:
            report = netsecmod.run_action(action_id, params)
        except Exception as exc:  # noqa: BLE001
            self.messageAdded.emit("error", f"Falha no recon: {exc}", "SEGURANÇA")
            self._set_busy(False)
            self._set_status("ATENÇÃO NECESSÁRIA")
            return
        shown = report if len(report) <= 1400 else (
            report[:1400] + "\n… (resultado completo enviado para a análise)"
        )
        self.messageAdded.emit("system", shown, f"RECON / {label.upper()}")
        prompt = (
            "[Recon de segurança autorizado, em ativo do próprio usuário] "
            f"Rodei '{label}' e o resultado bruto foi:\n\n{report}\n\n"
            "Explique o que isso revela, liste os riscos em ordem de prioridade "
            "(ALTO / MÉDIO / BAIXO) e diga como corrigir cada um. Seja objetivo; "
            "não repita a saída bruta."
        )
        self._request_worker(prompt, None, speak_reply=False)

    # ---------------------------------------------- painel assistente de codigo
    @Property("QVariantList", constant=True)
    def codeActions(self) -> list:
        return codeassistmod.code_actions()

    @Slot(str, "QVariantMap")
    def runCodeAction(self, action_id: str, params) -> None:
        if self._busy or self._voice_state not in {"idle", "error"}:
            self.messageAdded.emit(
                "error", "Aguarde a operação atual terminar.", "CÓDIGO"
            )
            return
        pdict = {str(k): str(v) for k, v in dict(params).items()}
        action = codeassistmod.get_action(action_id)
        if action is None:
            self.messageAdded.emit("error", "Ação desconhecida.", "CÓDIGO")
            return
        try:
            prompt = codeassistmod.build_prompt(action_id, pdict)
        except (KeyError, ValueError) as exc:
            self.messageAdded.emit("error", str(exc), "CÓDIGO")
            return
        self.messageAdded.emit("user", f"{action.icon} {action.label}", "VOCÊ")
        self._set_busy(True)
        self._set_status("ASSISTENTE DE CÓDIGO")
        threading.Thread(
            target=self._request_worker,
            args=(prompt, None, False),
            daemon=True,
            name="jarvis-codeassist",
        ).start()

    @Slot(str, result="QStringList")
    def aiModels(self, provider_label: str) -> list[str]:
        key = AI_PROVIDER_LABELS.get(provider_label, provider_label.lower())
        configured = self._config.providers.get(key)
        values = [configured.model] if configured else []
        return list(dict.fromkeys([*values, *AI_MODEL_SUGGESTIONS.get(key, [])]))

    @Slot(str, result="QStringList")
    def voiceModels(self, engine: str) -> list[str]:
        if engine == "Gemini TTS":
            return GEMINI_TTS_MODELS
        if engine == "Kokoro (local)":
            return ["kokoro-v1.0"]
        return ["sapi5"]

    @Slot(str, result="QStringList")
    def voiceNames(self, engine: str) -> list[str]:
        if engine == "Gemini TTS":
            return GEMINI_VOICES
        if engine == "Kokoro (local)":
            return list(KOKORO_VOICES)
        return VoiceService.windows_voice_names()

    @Slot(str, result=str)
    def credentialHint(self, provider_or_engine: str) -> str:
        env_name = API_KEY_ENV_NAMES.get(provider_or_engine)
        if not env_name:
            return "Execução local: nenhuma chave de API necessária"
        if secret_configured(self._assistant.database, env_name):
            return f"{env_name} salva no banco local"
        return f"Informe a chave {env_name} para usar este provedor"

    @Slot(str, result=str)
    def apiKeyEnvName(self, provider_or_engine: str) -> str:
        return API_KEY_ENV_NAMES.get(provider_or_engine, "")

    @Slot(str, result=bool)
    def apiKeyConfigured(self, provider_or_engine: str) -> bool:
        env_name = API_KEY_ENV_NAMES.get(provider_or_engine)
        return bool(
            env_name and secret_configured(self._assistant.database, env_name)
        )

    @Slot(str, str, str, str, str, str, str)
    def saveSettings(
        self,
        provider_label: str,
        ai_model: str,
        voice_engine_label: str,
        voice_model: str,
        voice_name: str,
        conversation_api_key: str,
        gemini_voice_api_key: str,
    ) -> None:
        if self._busy or self._voice_state not in {"idle", "error"}:
            self.messageAdded.emit(
                "error", "Aguarde a operação atual terminar antes de salvar.", "CONFIGURACOES"
            )
            return
        provider_key = AI_PROVIDER_LABELS.get(provider_label)
        if provider_key not in self._config.providers or not ai_model.strip():
            self.messageAdded.emit(
                "error", "Selecione um provedor e informe um modelo valido.", "CONFIGURACOES"
            )
            return
        conversation_secret_name = API_KEY_ENV_NAMES.get(provider_label)
        conversation_secret = conversation_api_key.strip()
        voice_secret = gemini_voice_api_key.strip()
        if (
            conversation_secret_name == "GEMINI_API_KEY"
            and conversation_secret
            and voice_secret
            and conversation_secret != voice_secret
        ):
            self.messageAdded.emit(
                "error",
                "A IA Gemini e a voz Gemini TTS usam a mesma chave. Informe a mesma chave nos dois campos.",
                "CONFIGURAÇÕES / SEGURANÇA",
            )
            return
        try:
            database = self._assistant.database
            if conversation_secret_name and conversation_secret:
                save_secret(database, conversation_secret_name, conversation_secret)
            if voice_engine_label == "Gemini TTS" and voice_secret:
                save_secret(database, "GEMINI_API_KEY", voice_secret)
        except Exception as exc:  # noqa: BLE001 - vira mensagem de erro na UI
            self.messageAdded.emit(
                "error",
                f"Não consegui gravar a chave no banco local: {exc}",
                "CONFIGURAÇÕES / SEGURANÇA",
            )
            return
        preferences = self._runtime_preferences()
        preferences.update(
            {
                "ai_provider": provider_key,
                "ai_model": ai_model.strip(),
                "tts_engine": {
                    "Gemini TTS": "gemini",
                    "Kokoro (local)": "kokoro",
                }.get(voice_engine_label, "windows"),
                "tts_model": voice_model,
                "tts_voice": voice_name,
            }
        )
        self._assistant.database.set_setting("runtime_preferences", preferences)
        self._apply_runtime_preferences(preferences)
        self._active_provider = provider_key
        self.providerChanged.emit()
        self._notify_settings_changed()
        self._set_status("CONFIGURAÇÕES SALVAS")
        self.messageAdded.emit(
            "system",
            f"IA: {provider_label} / {ai_model}. Voz: {voice_engine_label} / {voice_name}.",
            "CONFIGURAÇÕES SALVAS",
        )

    @Slot(str)
    def openApiKeyPage(self, provider_or_engine: str) -> None:
        url = API_KEY_URLS.get(provider_or_engine)
        if url:
            QDesktopServices.openUrl(QUrl(url))

    @Slot(str)
    def removeApiKey(self, provider_or_engine: str) -> None:
        env_name = API_KEY_ENV_NAMES.get(provider_or_engine)
        if not env_name:
            return
        delete_secret(self._assistant.database, env_name)
        self._notify_settings_changed()
        self._set_status(f"{env_name} REMOVIDA")
        self.messageAdded.emit(
            "system",
            f"A chave {env_name} foi removida do banco local.",
            "CONFIGURAÇÕES / SEGURANÇA",
        )

    def _runtime_preferences(self) -> dict:
        stored = self._assistant.database.get_setting("runtime_preferences", {})
        return dict(stored) if isinstance(stored, dict) else {}

    @Property(bool, notify=settingsChanged)
    def agentEnabled(self) -> bool:
        return self._config.agent.enabled

    @Property(bool, notify=settingsChanged)
    def agentFilesystemRead(self) -> bool:
        return self._config.agent.filesystem_read

    @Property(bool, notify=settingsChanged)
    def agentFilesystemWrite(self) -> bool:
        return self._config.agent.filesystem_write

    @Property(bool, notify=settingsChanged)
    def agentShell(self) -> bool:
        return self._config.agent.shell

    @Property(bool, notify=settingsChanged)
    def agentBrowser(self) -> bool:
        return self._config.agent.browser

    @Property(bool, notify=settingsChanged)
    def agentSsh(self) -> bool:
        return self._config.agent.ssh

    @Property(str, notify=settingsChanged)
    def agentAllowedRoots(self) -> str:
        return "\n".join(self._config.agent.allowed_roots)

    @Property(str, notify=settingsChanged)
    def agentSummary(self) -> str:
        agent = self._config.agent
        if not agent.enabled:
            return "Agente desligado: o Jarvis so conversa."
        active = [
            name
            for name, on in (
                ("ler arquivos", agent.filesystem_read),
                ("alterar arquivos", agent.filesystem_write),
                ("shell", agent.shell),
                ("navegador", agent.browser),
                ("SSH", agent.ssh),
            )
            if on
        ]
        roots = ", ".join(agent.allowed_roots) or "(pasta do usuário)"
        return f"Agente ligado — {', '.join(active) or 'nada'}. Escrita em: {roots}."

    @Slot(bool, bool, bool, bool, bool, str, bool)
    def savePermissions(
        self,
        enabled: bool,
        filesystem_read: bool,
        filesystem_write: bool,
        shell: bool,
        browser: bool,
        allowed_roots_text: str,
        ssh: bool = False,
    ) -> None:
        if self._busy or self._voice_state not in {"idle", "error"}:
            self.messageAdded.emit(
                "error", "Aguarde a operação atual terminar.", "PERMISSOES"
            )
            return
        roots = [
            line.strip()
            for line in allowed_roots_text.replace(";", "\n").splitlines()
            if line.strip()
        ]
        preferences = self._runtime_preferences()
        preferences.update(
            {
                "agent_enabled": bool(enabled),
                "agent_fs_read": bool(filesystem_read),
                "agent_fs_write": bool(filesystem_write),
                "agent_shell": bool(shell),
                "agent_browser": bool(browser),
                "agent_ssh": bool(ssh),
                "agent_allowed_roots": roots,
            }
        )
        self._assistant.database.set_setting("runtime_preferences", preferences)
        self._apply_runtime_preferences(preferences)
        self._notify_settings_changed()
        self._set_status("PERMISSÕES ATUALIZADAS")
        self.messageAdded.emit("system", self.agentSummary, "PERMISSOES")

    @Slot(str, bool)
    def resolveConfirmation(self, token: str, approved: bool) -> None:
        entry = self._confirmations.get(token)
        if entry is not None:
            entry[1].append(bool(approved))
            entry[0].set()

    def _make_confirm(self):
        import uuid

        async def confirm_async(description: str) -> bool:
            token = uuid.uuid4().hex
            event = threading.Event()
            box: list[bool] = []
            self._confirmations[token] = (event, box)
            self.confirmationRequested.emit(token, description)
            self._set_status("AGUARDANDO CONFIRMACAO")
            await asyncio.to_thread(event.wait)
            self._confirmations.pop(token, None)
            self._set_status("PROCESSANDO SOLICITAÇÃO")
            return bool(box) and box[0]

        return confirm_async

    def _agent_event(self, kind: str, text: str) -> None:
        if kind == "tool":
            self.messageAdded.emit("system", f"Vou usar: {text}", "AGENTE / AÇÃO")
        elif kind == "notice":
            self.messageAdded.emit("system", text, "AGENTE / RESULTADO")
        elif kind == "error":
            self.messageAdded.emit("error", text, "AGENTE / ERRO")

    def _emit_chat_media(self, data: bytes, kind: str, caption: str) -> None:
        """Mostra uma imagem/arquivo no chat (foto da webcam, print da tela...)."""
        import base64
        import tempfile
        import time as _time

        if not data:
            return
        uri = "data:image/jpeg;base64," + base64.b64encode(data).decode("ascii")
        folder = Path(tempfile.gettempdir()) / "jarvis-capturas"
        file_path = ""
        file_name = ""
        try:
            folder.mkdir(parents=True, exist_ok=True)
            # limpa capturas velhas (> ~40)
            olds = sorted(folder.glob("*.jpg"), key=lambda p: p.stat().st_mtime)
            for stale in olds[:-40]:
                stale.unlink(missing_ok=True)
            target = folder / f"{kind}-{int(_time.time() * 1000)}.jpg"
            target.write_bytes(data)
            file_path, file_name = str(target), target.name
        except OSError:
            pass
        self.chatMediaAdded.emit(
            {
                "role": "assistant",
                "meta": caption.upper(),
                "caption": caption,
                "kind": kind,
                "uri": uri,
                "filePath": file_path,
                "fileName": file_name,
            }
        )

    def _finalize_artifacts(self, final_text: str) -> None:
        """Depois da resposta: transforma blocos de código em cartoes no chat."""
        if "```" not in (final_text or ""):
            return
        try:
            from jarvis import artifacts

            clean, blocks = artifacts.extract_code_blocks(final_text)
        except Exception:  # noqa: BLE001
            return
        if not blocks:
            return
        self.chatBodyReplaced.emit(clean or "Aqui esta o que você pediu:")
        for block in blocks:
            self.chatArtifactAdded.emit(block.as_dict())

    def _downloads_dir(self) -> Path:
        for name in ("Downloads", "Download"):
            candidate = Path.home() / name
            if candidate.is_dir():
                return candidate
        return Path.home()

    @Slot(str, str)
    def downloadArtifact(self, content: str, filename: str) -> None:
        name = filename.strip() or "codigo.txt"
        target = self._downloads_dir() / name
        counter = 2
        while target.exists():
            target = target.with_name(f"{target.stem} ({counter}){target.suffix}")
            counter += 1
        try:
            target.write_text(content, encoding="utf-8")
        except OSError as exc:
            self.messageAdded.emit("error", f"Não consegui salvar: {exc}", "DOWNLOAD")
            return
        self._set_status("ARQUIVO BAIXADO")
        self.chatMediaAdded.emit(
            {
                "role": "system",
                "meta": "DOWNLOAD",
                "caption": f"Salvo em Downloads/{target.name}",
                "kind": "file",
                "uri": "",
                "filePath": str(target),
                "fileName": target.name,
            }
        )

    @Slot(str, str)
    def previewArtifact(self, content: str, filename: str) -> None:
        import tempfile

        name = filename.strip() or "pagina.html"
        folder = Path(tempfile.gettempdir()) / "jarvis-artefatos"
        try:
            folder.mkdir(parents=True, exist_ok=True)
            target = folder / name
            target.write_text(content, encoding="utf-8")
        except OSError as exc:
            self.messageAdded.emit("error", f"Não consegui abrir: {exc}", "VISUALIZAR")
            return
        self.openFile(str(target))

    # ------------------------------------------------------ anexos do chat
    @Property("QVariantList", notify=attachmentsChanged)
    def pendingAttachments(self) -> list:
        return [att.as_dict() for att in self._pending_attachments]

    @Slot("QVariantList")
    def addAttachments(self, paths) -> None:
        added = 0
        for raw in list(paths):
            text = str(raw).strip()
            if not text:
                continue
            if any(att.path == text for att in self._pending_attachments):
                continue
            if len(self._pending_attachments) >= 8:
                self.messageAdded.emit(
                    "system", "Limite de 8 anexos por mensagem.", "ANEXO"
                )
                break
            att = attachmentsmod.load_attachment(text)
            self._pending_attachments.append(att)
            added += 1
            if att.error:
                self.messageAdded.emit(
                    "error", f'Anexo "{att.name}": {att.error}', "ANEXO"
                )
        if added:
            self.attachmentsChanged.emit()

    @Slot(int)
    def removeAttachment(self, index: int) -> None:
        if 0 <= index < len(self._pending_attachments):
            self._pending_attachments.pop(index)
            self.attachmentsChanged.emit()

    @Slot()
    def clearAttachments(self) -> None:
        if self._pending_attachments:
            self._pending_attachments = []
            self.attachmentsChanged.emit()

    def _take_attachments(self) -> list:
        pending = self._pending_attachments
        if pending:
            self._pending_attachments = []
            self.attachmentsChanged.emit()
        return pending

    def _describe_attachment_image(self, question: str, att) -> str:
        provider = self._config.providers.get(self._config.default_provider)
        if provider is None:
            return "(nenhum provedor de IA configurado para analisar a imagem)"
        frame = visionmod.Frame(jpeg=att.jpeg, width=att.width, height=att.height)
        ask = (question or "").strip() or (
            "Descreva esta imagem em detalhes, em português do Brasil."
        )
        return visionmod.describe_scene(
            ask, frame, provider,
            timeout_seconds=self._config.vision.timeout_seconds,
        )

    def _announce_attachments(self, items: list) -> None:
        """Mostra cada anexo no chat (transparencia) antes da resposta."""
        for att in items:
            if att.kind == "image" and att.jpeg:
                self._emit_chat_media(att.jpeg, "image", f"Anexo: {att.name}")
            else:
                self.chatMediaAdded.emit(
                    {
                        "role": "user",
                        "meta": "ANEXO",
                        "caption": att.name
                        + ("" if att.ok else f"  ({att.error})"),
                        "kind": "file",
                        "uri": "",
                        "filePath": att.path,
                        "fileName": att.name,
                    }
                )

    def _notify_settings_changed(self) -> None:
        self._settings_revision += 1
        self.settingsChanged.emit()

    def _apply_runtime_preferences(self, preferences: dict[str, object]) -> None:
        provider_key = str(preferences.get("ai_provider", self._config.default_provider))
        if provider_key not in self._config.providers:
            provider_key = self._config.default_provider
        providers = dict(self._config.providers)
        selected = providers[provider_key]
        providers[provider_key] = replace(
            selected,
            enabled=True,
            model=str(preferences.get("ai_model", selected.model)),
        )
        old_voice = self._config.voice
        tts_engine = str(preferences.get("tts_engine", old_voice.tts_engine))
        tts_model = str(preferences.get("tts_model", old_voice.tts_model))
        tts_voice = str(preferences.get("tts_voice", old_voice.tts_voice))
        if tts_engine == "gemini":
            # Preferências antigas podem ter modelos/vozes que não existem mais.
            if tts_model not in GEMINI_TTS_MODELS:
                tts_model = GEMINI_TTS_MODELS[0]
            if tts_voice not in GEMINI_VOICES:
                tts_voice = GEMINI_VOICES[0]
        elif tts_engine == "kokoro":
            tts_model = "kokoro-v1.0"
            if tts_voice not in KOKORO_VOICES:
                tts_voice = KOKORO_VOICES[0]
        wake_phrase = str(
            preferences.get("wake_word", old_voice.wake_word)
        ).strip() or "jarvis"
        wake_required = bool(
            preferences.get("wake_word_required", old_voice.wake_word_required)
        )
        transcription_engine = str(
            preferences.get("transcription_engine", old_voice.transcription_engine)
        )
        cloud_model = str(
            preferences.get(
                "transcription_cloud_model", old_voice.transcription_cloud_model
            )
        )
        if transcription_engine == "openai" and cloud_model not in {
            "gpt-4o-transcribe",
            "gpt-4o-mini-transcribe",
            "whisper-1",
        }:
            cloud_model = "gpt-4o-transcribe"
        voice = replace(
            old_voice,
            whisper_model=str(
                preferences.get("whisper_model", old_voice.whisper_model)
            ),
            silence_seconds=float(
                preferences.get("silence_seconds", old_voice.silence_seconds)
            ),
            speech_rms_threshold=float(
                preferences.get("speech_rms_threshold", old_voice.speech_rms_threshold)
            ),
            tts_engine=tts_engine,
            tts_model=tts_model,
            tts_voice=tts_voice,
            tts_rate=int(preferences.get("tts_rate", old_voice.tts_rate)),
            tts_volume=float(preferences.get("tts_volume", old_voice.tts_volume)),
            wake_word_enabled=bool(
                preferences.get("wake_word_enabled", old_voice.wake_word_enabled)
            ),
            wake_word=wake_phrase,
            wake_word_required=wake_required,
            transcription_engine=transcription_engine,
            transcription_cloud_model=cloud_model,
        )
        old_agent = self._config.agent
        raw_roots = preferences.get("agent_allowed_roots", list(old_agent.allowed_roots))
        agent = replace(
            old_agent,
            enabled=bool(preferences.get("agent_enabled", old_agent.enabled)),
            filesystem_read=bool(
                preferences.get("agent_fs_read", old_agent.filesystem_read)
            ),
            filesystem_write=bool(
                preferences.get("agent_fs_write", old_agent.filesystem_write)
            ),
            shell=bool(preferences.get("agent_shell", old_agent.shell)),
            browser=bool(preferences.get("agent_browser", old_agent.browser)),
            ssh=bool(preferences.get("agent_ssh", old_agent.ssh)),
            allowed_roots=tuple(
                str(item).strip()
                for item in (raw_roots or [])
                if str(item).strip()
            ),
        )
        profile = profilesmod.get_profile(
            str(preferences.get("usage_profile", profilesmod.DEFAULT_PROFILE))
        )
        dev_folder = str(preferences.get("dev_folder", "")).strip()
        system_prompt = profilesmod.compose_system_prompt(
            self._base_system_prompt, profile, folder=dev_folder
        )
        system_prompt = sectorsmod.apply_sector(
            system_prompt, str(preferences.get("sector", sectorsmod.DEFAULT_SECTOR))
        )
        fallback = (provider_key, *(
            name for name in self._config.fallback_order if name != provider_key
        ))
        weather_city = str(
            preferences.get("weather_city", self._config.weather_city)
        ).strip() or self._config.weather_city
        vision = replace(
            self._config.vision,
            enabled=bool(preferences.get("vision_enabled", self._config.vision.enabled)),
            camera_index=max(0, int(
                preferences.get("vision_camera_index", self._config.vision.camera_index)
            )),
        )
        self._config = replace(
            self._config,
            default_provider=provider_key,
            fallback_order=fallback,
            providers=providers,
            voice=voice,
            agent=agent,
            vision=vision,
            weather_city=weather_city,
            system_prompt=system_prompt,
        )
        database = self._assistant.database
        database.sync_providers(providers)
        self._assistant = JarvisAssistant(
            self._config, database=database, on_media=self._emit_chat_media
        )
        voice_model_changed = old_voice.whisper_model != voice.whisper_model
        self._voice = VoiceService(voice)
        self._active_provider = provider_key
        if voice_model_changed:
            self._warm_voice()
        wake_changed = (
            old_voice.wake_word_enabled != voice.wake_word_enabled
            or old_voice.wake_word != voice.wake_word
        )
        if wake_changed and self._wake is not None:
            self._wake.stop()
            self._wake = None
        self._sync_wake_word()

    def _set_busy(self, value: bool) -> None:
        if self._busy != value:
            self._busy = value
            self.busyChanged.emit()
        if self._wake is not None:
            if value:
                self._wake.pause()
            elif self._voice_state in {"idle", "error"}:
                self._wake.resume()

    def _set_status(self, value: str) -> None:
        if self._status != value:
            self._status = value
            self.statusChanged.emit()

    def _set_voice_state(self, value: str) -> None:
        if self._voice_state != value:
            self._voice_state = value
            self.voiceStateChanged.emit()
        if self._wake is not None:
            if value in {"idle", "error"}:
                self._wake.resume()
            else:
                self._wake.pause()

    def _set_voice_level(self, value: float) -> None:
        value = max(0.0, min(1.0, value))
        if abs(self._voice_level - value) >= 0.03:
            self._voice_level = value
            self.voiceLevelChanged.emit()

    def _wake_gate(self, text: str) -> str | None:
        """No modo 'exigir o nome', so passa mensagens que comecam com a palavra.

        Devolve o texto sem o prefixo, ou None (a mensagem deve ser ignorada).
        Quando o modo está desligado, devolve o texto como veio.
        """
        voice = self._config.voice
        if not (voice.wake_word_enabled and voice.wake_word_required):
            return text
        stripped = strip_wake_prefix(text, voice.wake_word)
        if stripped is None:
            self.messageAdded.emit(
                "system",
                f'Ignorado. Comece com "{voice.wake_word}" '
                f'(ex.: "{voice.wake_word}, abra o YouTube").',
                "PALAVRA DE ATIVACAO",
            )
            return None
        return stripped or None

    @Slot(str, str)
    def sendMessage(self, text: str, provider: str) -> None:
        gated = self._wake_gate(text)
        if gated is None:
            return
        self._start_request(gated, provider, speak_reply=False)

    def _start_request(self, text: str, provider: str, speak_reply: bool) -> None:
        cleaned = text.strip()
        if self._busy:
            return
        attachments = self._take_attachments()
        if not cleaned and not attachments:
            return
        if not attachments:
            routine_name = match_routine_command(
                cleaned,
                [item.name for item in self._assistant.database.list_routines()],
            )
            if routine_name is not None:
                routine = self._assistant.database.get_routine(routine_name)
                self._launch_routine(routine, speak=speak_reply, echo=cleaned)
                return
            if (
                self._config.vision.enabled
                and not self._config.agent.enabled
                and visionmod.looks_like_vision_request(cleaned)
            ):
                self.messageAdded.emit("user", cleaned, "VOCE")
                self._set_busy(True)
                self._set_status("OLHANDO PELA WEBCAM")
                threading.Thread(
                    target=self._vision_worker,
                    args=(cleaned, speak_reply),
                    daemon=True,
                    name="jarvis-vision",
                ).start()
                return
        requested_provider = None if provider == "Automático" else provider
        self.messageAdded.emit("user", cleaned or "(anexo enviado)", "VOCE")
        self._announce_attachments(attachments)
        self._set_busy(True)
        self._set_status(
            "LENDO ANEXOS" if attachments else "PROCESSANDO SOLICITAÇÃO"
        )
        threading.Thread(
            target=self._request_worker,
            args=(cleaned, requested_provider, speak_reply, attachments),
            daemon=True,
            name="jarvis-model-request",
        ).start()

    def _vision_worker(self, question: str, speak: bool) -> None:
        try:
            provider = self._config.providers.get(self._config.default_provider)
            if provider is None:
                raise visionmod.VisionError("Nenhum provedor de IA configurado.")
            frame = visionmod.capture_frame(
                self._config.vision.camera_index,
                jpeg_quality=self._config.vision.jpeg_quality,
            )
            self._emit_chat_media(frame.jpeg, "image", "Foto da webcam")
            answer = visionmod.describe_scene(
                question, frame, provider,
                timeout_seconds=self._config.vision.timeout_seconds,
            )
            self.streamStarted.emit("JARVIS // VISÃO")
            self.streamDelta.emit(answer)
            self.streamEnded.emit(f"{provider.name.upper()} // VISÃO")
            if speak and answer.strip():
                self._speak_reply(answer)
            self._set_voice_state("idle")
            self._set_status("SISTEMA PRONTO")
        except visionmod.VisionError as exc:
            self.messageAdded.emit("error", str(exc), "VISAO")
            self._set_voice_state("idle")
            self._set_status("ATENÇÃO NECESSÁRIA")
        except Exception as exc:  # noqa: BLE001
            self.messageAdded.emit("error", f"Falha na visão: {exc}", "VISAO")
            self._set_voice_state("idle")
            self._set_status("ATENÇÃO NECESSÁRIA")
        finally:
            self._set_busy(False)

    def _request_worker(
        self,
        text: str,
        provider: str | None,
        speak_reply: bool = False,
        attachments: list | None = None,
    ) -> None:
        started = False
        parts: list[str] = []
        try:
            confirm = self._make_confirm()

            prompt = text
            if attachments:
                try:
                    prompt = attachmentsmod.compose_prompt(
                        text, attachments,
                        describe=self._describe_attachment_image,
                    )
                except Exception as exc:  # noqa: BLE001
                    self.messageAdded.emit(
                        "error", f"Falha ao preparar anexos: {exc}", "ANEXO"
                    )
                self._set_status("PROCESSANDO SOLICITAÇÃO")

            async def consume() -> None:
                nonlocal started
                stream = self._assistant.ask_stream(
                    prompt,
                    conversation_id=self._conversation_id,
                    provider_name=provider,
                    confirm=confirm,
                    on_event=self._agent_event,
                )
                async for delta in stream:
                    if not started:
                        started = True
                        self.streamStarted.emit("JARVIS")
                        self._set_status("RECEBENDO RESPOSTA")
                    parts.append(delta)
                    self.streamDelta.emit(delta)

            async def guarded() -> None:
                await asyncio.wait_for(consume(), timeout=240)

            asyncio.run(guarded())

            if self._assistant.active_conversation_id is not None:
                self._conversation_id = self._assistant.active_conversation_id
                self.conversationsChanged.emit()
            reply = self._assistant.last_stream
            streamed = "".join(parts).strip()
            if reply is not None and reply.response.content.strip():
                self._active_provider = reply.response.provider
                self.providerChanged.emit()
                label = (
                    f"{reply.response.provider.upper()} / {reply.response.model}"
                ).strip(" /")
                spoken_text = reply.response.content
            elif streamed:
                label = "JARVIS"
                spoken_text = streamed
            else:
                # Nunca terminar em silencio.
                label = "SEM RESPOSTA"
                spoken_text = ""
                if not started:
                    self.streamStarted.emit("JARVIS")
                self.streamDelta.emit(
                    "Não recebi resposta do provedor. Verifique a chave de API "
                    "e o modelo em Configurações, e tente de novo."
                )
            self.streamEnded.emit(label)
            self._finalize_artifacts(spoken_text)

            if speak_reply and spoken_text.strip():
                self._speak_reply(spoken_text)

            # o turno pode ter gerado aprendizado (cognition.process_user_turn)
            self.learnedMemoriesChanged.emit()
            self.behaviorProfileChanged.emit()

            self._set_voice_state("idle")
            self._set_status("SISTEMA PRONTO")
        except TimeoutError:
            if not started:
                self.streamStarted.emit("JARVIS")
            self.streamDelta.emit("A resposta demorou demais e foi cancelada.")
            self.streamEnded.emit("TEMPO ESGOTADO")
            self._set_voice_state("idle")
            self._set_status("ATENÇÃO NECESSÁRIA")
        except Exception as exc:
            if started:
                self.streamEnded.emit("FALHA")
            self.messageAdded.emit("error", str(exc), "FALHA DO NÚCLEO")
            self._set_voice_state("idle")
            self._set_status("ATENÇÃO NECESSÁRIA")
        finally:
            self._set_busy(False)

    def _speak_reply(self, spoken_text: str) -> None:
        """Narra a resposta com um watchdog: nada pode travar a interface."""
        engine = self._config.voice.tts_engine
        if engine == "gemini" and not secret_configured(
            self._assistant.database, "GEMINI_API_KEY"
        ):
            self.messageAdded.emit(
                "error",
                "Voz Gemini selecionada, mas sem GEMINI_API_KEY no banco. "
                "Usando a voz do Windows. Salve a chave em Configurações.",
                "VOZ / CONFIGURAÇÃO",
            )
        elif engine == "kokoro" and not kokoro_available():
            self.messageAdded.emit(
                "error",
                "Voz Kokoro selecionada, mas o pacote não está instalado. "
                "Rode: .\\.venv\\Scripts\\python.exe -m pip install kokoro-onnx",
                "VOZ / CONFIGURAÇÃO",
            )

        self._speaking_stop.clear()
        self._set_voice_state("speaking")
        self._set_status("RESPONDENDO POR VOZ")

        result: dict[str, object] = {}

        def run() -> None:
            try:
                result["warning"] = self._voice.speak(spoken_text)
            except VoiceError as exc:
                result["error"] = exc
            except Exception as exc:  # noqa: BLE001
                result["error"] = VoiceError(f"Falha inesperada na voz: {exc}")

        worker = threading.Thread(target=run, daemon=True, name="jarvis-tts")
        worker.start()
        worker.join(timeout=self._config.voice.max_spoken_chars / 12 + 20)
        if worker.is_alive():
            self._voice.stop_speaking()
            worker.join(timeout=3)
            self.messageAdded.emit(
                "error",
                "A sintese de voz demorou demais e foi interrompida.",
                "VOZ / SAÍDA",
            )
            return
        if self._speaking_stop.is_set():
            return
        if result.get("error") is not None:
            self.messageAdded.emit("error", str(result["error"]), "VOZ / SAÍDA")
        elif result.get("warning"):
            self.messageAdded.emit(
                "error", str(result["warning"]), "VOZ / FALLBACK AUTOMÁTICO"
            )

    @Slot()
    def stopSpeaking(self) -> None:
        """Interrompe a fala da IA imediatamente (botão, tecla Esc, novo comando)."""
        if self._voice_state != "speaking":
            return
        self._speaking_stop.set()
        self._voice.stop_speaking()
        self._set_status("FALA INTERROMPIDA")
        self._set_voice_state("idle")

    @Slot(str)
    def toggleListening(self, provider: str) -> None:
        if self._voice_state == "listening":
            self._voice_stop_event.set()
            self._set_status("FINALIZANDO CAPTURA")
            return
        if self._voice_state == "speaking":
            self._speaking_stop.set()
            self._voice.stop_speaking()
            self._set_status("FALA INTERROMPIDA")
            return
        if self._busy or self._voice_state not in {"idle", "error"}:
            return
        try:
            self._voice.assert_available()
        except VoiceError as exc:
            self.messageAdded.emit("error", str(exc), "VOZ / CONFIGURAÇÃO")
            self._set_voice_state("error")
            self._set_status("VOZ INDISPONÍVEL")
            return
        if self._config.voice.transcription_engine == "openai" and not secret_configured(
            self._assistant.database, "OPENAI_API_KEY"
        ):
            self.messageAdded.emit(
                "error",
                "Transcrição OpenAI selecionada, mas sem OPENAI_API_KEY. "
                "Usando o Whisper local.",
                "VOZ / CONFIGURAÇÃO",
            )
        self._voice_stop_event = threading.Event()
        self._set_voice_state("listening")
        self._set_voice_level(0.0)
        self._set_status("OUVINDO // FALE AGORA")
        threading.Thread(
            target=self._listen_worker,
            args=(provider,),
            daemon=True,
            name="jarvis-voice-input",
        ).start()

    def _listen_worker(self, provider: str) -> None:
        try:
            self._signal_listening_started()
            recording = self._voice.record_until_silence(
                self._voice_stop_event, self._set_voice_level
            )
            self._set_voice_level(0.0)
            self._set_voice_state("transcribing")
            self._set_status("TRANSCREVENDO // PRIMEIRO USO PODE DEMORAR")
            text = self._voice.transcribe(recording.audio)
            gated = self._wake_gate(text)
            if gated is None:
                self._set_voice_state("idle")
                self._set_status("SISTEMA PRONTO")
                return
            self.transcriptionReady.emit(gated, provider)
        except VoiceError as exc:
            self._set_voice_level(0.0)
            self._set_voice_state("error")
            self._set_status("ATENÇÃO NECESSÁRIA")
            self.messageAdded.emit("error", str(exc), "VOZ / ENTRADA")
        except Exception as exc:
            self._set_voice_level(0.0)
            self._set_voice_state("error")
            self._set_status("ATENÇÃO NECESSÁRIA")
            self.messageAdded.emit(
                "error", f"Falha inesperada no recurso de voz: {exc}", "VOZ / ENTRADA"
            )

    @Slot(str, str)
    def _submit_transcription(self, text: str, provider: str) -> None:
        self._set_voice_state("thinking")
        self._start_request(text, provider, speak_reply=True)

    @staticmethod
    def _signal_listening_started() -> None:
        if sys.platform != "win32":
            return
        try:
            import winsound

            winsound.MessageBeep(winsound.MB_OK)
        except Exception:
            pass

    @Slot()
    def newConversation(self) -> None:
        if self._busy or self._voice_state not in {"idle", "error"}:
            return
        self._conversation_id = None
        self.chatCleared.emit()
        self.messageAdded.emit(
            "system", "Nova conversa. Como posso ajudar?", "JARVIS CORE"
        )
        self._set_status("NOVA CONVERSA")

    # ---------------------------------------------- historico de conversas
    @Property("QVariantList", notify=conversationsChanged)
    def conversations(self) -> list:
        try:
            items = self._assistant.database.list_conversations()
        except Exception:  # noqa: BLE001
            return []
        out: list[dict] = []
        for item in items:
            out.append(
                {
                    "id": item["id"],
                    "title": item["title"],
                    "turns": item["turns"],
                    "when": self._relative_time(item["updatedAt"]),
                    "current": item["id"] == self._conversation_id,
                }
            )
        return out

    @staticmethod
    def _relative_time(iso: str | None) -> str:
        if not iso:
            return ""
        try:
            when = datetime.fromisoformat(str(iso).replace("Z", "").split(".")[0])
        except ValueError:
            return str(iso)[:16]
        delta = datetime.now() - when
        secs = delta.total_seconds()
        if secs < 60:
            return "agora"
        if secs < 3600:
            return f"ha {int(secs // 60)} min"
        if secs < 86400 and when.date() == datetime.now().date():
            return f"hoje {when:%H:%M}"
        if secs < 172800:
            return f"ontem {when:%H:%M}"
        return f"{when:%d/%m %H:%M}"

    @Slot(int)
    def openConversation(self, conversation_id: int) -> None:
        if self._busy or self._voice_state not in {"idle", "error"}:
            self.messageAdded.emit(
                "error", "Aguarde a operação atual terminar.", "HISTÓRICO"
            )
            return
        try:
            rows = self._assistant.database.conversation_transcript(
                int(conversation_id)
            )
        except Exception as exc:  # noqa: BLE001
            self.messageAdded.emit("error", f"Não consegui abrir: {exc}", "HISTÓRICO")
            return
        if not rows:
            return
        self._conversation_id = int(conversation_id)
        self.chatCleared.emit()
        for row in rows:
            role = row["role"]
            content = row["content"] or ""
            if role == "user":
                self.messageAdded.emit("user", content, "VOCÊ")
                continue
            label = row["label"] or "JARVIS"
            if "```" in content:
                try:
                    from jarvis import artifacts

                    clean, blocks = artifacts.extract_code_blocks(content)
                except Exception:  # noqa: BLE001
                    clean, blocks = content, []
                self.messageAdded.emit(
                    "assistant", clean or "Segue o que voce pediu:", label
                )
                for block in blocks:
                    self.chatArtifactAdded.emit(block.as_dict())
            else:
                self.messageAdded.emit("assistant", content, label)
        self.conversationsChanged.emit()
        self._set_status("HISTÓRICO CARREGADO")

    @Slot(int)
    def deleteConversation(self, conversation_id: int) -> None:
        if self._busy:
            return
        was_current = int(conversation_id) == self._conversation_id
        try:
            self._assistant.database.delete_conversation(int(conversation_id))
        except Exception as exc:  # noqa: BLE001
            self.messageAdded.emit("error", f"Não consegui apagar: {exc}", "HISTÓRICO")
            return
        if was_current:
            self._conversation_id = None
            self.chatCleared.emit()
        self.conversationsChanged.emit()
        self._set_status("CONVERSA APAGADA")

    @Slot(int, str)
    def renameConversation(self, conversation_id: int, title: str) -> None:
        title = (title or "").strip()
        if not title:
            return
        try:
            self._assistant.database.rename_conversation(int(conversation_id), title)
        except Exception:  # noqa: BLE001
            return
        self.conversationsChanged.emit()


def _tray_icon() -> QIcon:
    pixmap = QPixmap(64, 64)
    pixmap.fill(QColor(0, 0, 0, 0))
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QColor("#46EAF7"))
    painter.setBrush(QColor("#0A1428"))
    painter.drawEllipse(5, 5, 54, 54)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("#46EAF7"))
    painter.drawEllipse(23, 23, 18, 18)
    painter.end()
    return QIcon(pixmap)


def _install_tray(app, window, backend) -> object | None:
    """Icone na bandeja + balao de notificação ao lado do relogio do Windows."""
    try:
        from PySide6.QtWidgets import QMenu, QSystemTrayIcon
    except Exception:  # noqa: BLE001 - sem QtWidgets, segue sem bandeja
        return None
    if not QSystemTrayIcon.isSystemTrayAvailable():
        return None

    tray = QSystemTrayIcon(_tray_icon(), app)
    tray.setToolTip("Jarvis")

    def restore() -> None:
        window.show()
        try:
            window.showNormal()
        except Exception:  # noqa: BLE001
            pass
        window.raise_()
        window.requestActivate()

    menu = QMenu()
    open_action = QAction("Abrir o Jarvis", menu)
    open_action.triggered.connect(restore)
    quit_action = QAction("Sair", menu)
    quit_action.triggered.connect(app.quit)
    menu.addAction(open_action)
    menu.addSeparator()
    menu.addAction(quit_action)
    tray.setContextMenu(menu)

    def on_activated(reason) -> None:
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            restore()

    tray.activated.connect(on_activated)
    tray.messageClicked.connect(restore)

    def on_notification(info: dict) -> None:
        title = str(info.get("title", "Compromisso"))
        body = " · ".join(
            part
            for part in (
                str(info.get("whenText", "")),
                str(info.get("location", "")),
            )
            if part
        ) or "Você tem um compromisso agora."
        tray.showMessage(
            f"Jarvis — {title}",
            body,
            QSystemTrayIcon.MessageIcon.Information,
            30000,
        )

    backend.notificationRequested.connect(on_notification)
    tray.show()
    return tray


def run_gui(config: AppConfig) -> int:
    try:
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance() or QApplication(sys.argv)
    except Exception:  # noqa: BLE001 - fallback sem QtWidgets
        app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    app.setApplicationName("Jarvis Personal")
    app.setOrganizationName("Jarvis")
    if hasattr(app, "setQuitOnLastWindowClosed"):
        app.setQuitOnLastWindowClosed(True)

    font_path = (
        Path(__file__).resolve().parent
        / "assets"
        / "fonts"
        / "SpaceGrotesk-Variable.ttf"
    )
    font_id = QFontDatabase.addApplicationFont(str(font_path))
    families = QFontDatabase.applicationFontFamilies(font_id)
    if families:
        app.setFont(QFont(families[0], 10))

    engine = QQmlApplicationEngine()
    try:
        backend = JarvisBackend(config)
    except DatabaseUnavailable as exc:
        try:
            from PySide6.QtWidgets import QMessageBox

            QMessageBox.critical(None, "Jarvis - banco de dados", str(exc))
        except Exception:  # noqa: BLE001
            print(f"Erro: {exc}", file=sys.stderr)
        return 1
    app.aboutToQuit.connect(backend.shutdown)
    engine.rootContext().setContextProperty("jarvisBackend", backend)
    engine.rootContext().setContextProperty(
        "jarvisSettingsPreview", bool(os.environ.get("JARVIS_GUI_SHOW_SETTINGS"))
    )
    engine.rootContext().setContextProperty(
        "jarvisCloudSettingsPreview",
        bool(os.environ.get("JARVIS_GUI_PREVIEW_CLOUD_SETTINGS")),
    )
    engine.rootContext().setContextProperty(
        "jarvisPermissionsPreview",
        bool(os.environ.get("JARVIS_GUI_PREVIEW_PERMISSIONS")),
    )
    qml_path = Path(__file__).resolve().parent / "ui" / "Main.qml"
    engine.load(QUrl.fromLocalFile(str(qml_path)))
    if not engine.rootObjects():
        return 1

    _tray = _install_tray(app, engine.rootObjects()[0], backend)

    screenshot_path = os.environ.get("JARVIS_GUI_SCREENSHOT")
    if screenshot_path:
        window = engine.rootObjects()[0]

        def capture() -> None:
            Path(screenshot_path).parent.mkdir(parents=True, exist_ok=True)
            screen = window.screen() or app.primaryScreen()
            screen.grabWindow(window.winId()).save(screenshot_path)
            app.quit()

        QTimer.singleShot(1500, capture)

    return app.exec()
