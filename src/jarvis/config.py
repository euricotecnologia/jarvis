from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from jarvis.errors import ConfigurationError


@dataclass(frozen=True, slots=True)
class ProviderConfig:
    name: str
    kind: str
    enabled: bool
    model: str
    base_url: str
    api_key_env: str | None = None
    timeout_seconds: float = 120.0

    def api_key(self) -> str | None:
        return os.environ.get(self.api_key_env) if self.api_key_env else None


@dataclass(frozen=True, slots=True)
class VoiceConfig:
    enabled: bool
    language: str
    whisper_model: str
    device: str
    compute_type: str
    model_cache_path: Path
    sample_rate: int
    silence_seconds: float
    no_speech_timeout_seconds: float
    max_record_seconds: float
    speech_rms_threshold: float
    tts_rate: int
    tts_volume: float
    max_spoken_chars: int
    tts_engine: str = "windows"
    tts_model: str = "sapi5"
    tts_voice: str = "Microsoft Maria Desktop - Portuguese(Brazil)"
    tts_buffer_seconds: float = 0.4
    tts_stream: bool = True
    wake_word_enabled: bool = False
    wake_word: str = "jarvis"
    wake_word_required: bool = False
    wake_word_model: str = "base"
    kokoro_speed: float = 1.0
    transcription_engine: str = "local"  # "local" (faster-whisper) | "openai"
    transcription_cloud_model: str = "gpt-4o-transcribe"


def default_voice_config() -> VoiceConfig:
    return VoiceConfig(
        enabled=True,
        language="pt",
        whisper_model="small",
        device="cpu",
        compute_type="int8",
        model_cache_path=Path("data/models"),
        sample_rate=16000,
        silence_seconds=3.5,
        no_speech_timeout_seconds=12.0,
        max_record_seconds=45.0,
        speech_rms_threshold=0.003,
        tts_rate=185,
        tts_volume=1.0,
        max_spoken_chars=800,
        tts_engine="windows",
        tts_model="sapi5",
        tts_voice="Microsoft Maria Desktop - Portuguese(Brazil)",
        tts_buffer_seconds=0.4,
        tts_stream=True,
        wake_word_enabled=False,
        wake_word="jarvis",
        wake_word_required=False,
        wake_word_model="base",
        kokoro_speed=1.0,
        transcription_engine="local",
        transcription_cloud_model="gpt-4o-transcribe",
    )


@dataclass(frozen=True, slots=True)
class AgentConfig:
    """Permissões do agente para agir no computador do usuário."""

    enabled: bool = False
    filesystem_read: bool = True
    filesystem_write: bool = False
    shell: bool = False
    browser: bool = False
    ssh: bool = False
    allowed_roots: tuple[str, ...] = ()
    max_iterations: int = 12
    shell_timeout_seconds: float = 60.0
    max_output_chars: int = 12000


def default_agent_config() -> AgentConfig:
    return AgentConfig()


@dataclass(frozen=True, slots=True)
class VisionConfig:
    """A IA enxergar pela webcam. Desligado por padrão (privacidade)."""

    enabled: bool = False
    camera_index: int = 0
    jpeg_quality: int = 85
    timeout_seconds: float = 45.0


def default_vision_config() -> VisionConfig:
    return VisionConfig()


@dataclass(frozen=True, slots=True)
class AppConfig:
    database_path: Path
    default_provider: str
    fallback_order: tuple[str, ...]
    system_prompt: str
    providers: dict[str, ProviderConfig]
    voice: VoiceConfig = field(default_factory=default_voice_config)
    agent: AgentConfig = field(default_factory=default_agent_config)
    vision: VisionConfig = field(default_factory=default_vision_config)
    weather_city: str = "São Paulo"


DEFAULT_SYSTEM_PROMPT = (
    "Você e o Jarvis, o assistente pessoal do usuário. Fala português do Brasil "
    "com um jeito calmo, próximo e natural - como um amigo competente, não como "
    "um manual. Vai direto ao ponto, sem enrolar. Nunca faz uma ação sensivel "
    "(apagar, enviar, comprar, mudar configuração) sem confirmar antes."
)


def _default_data() -> dict[str, Any]:
    return {
        "app": {
            "database_path": "data/jarvis.db",
            "default_provider": "ollama",
            "fallback_order": ["ollama", "lmstudio", "openai", "claude", "gemini"],
            "system_prompt": DEFAULT_SYSTEM_PROMPT,
            "weather_city": "São Paulo",
        },
        "voice": {
            "enabled": True,
            "language": "pt",
            "whisper_model": "small",
            "device": "cpu",
            "compute_type": "int8",
            "model_cache_path": "data/models",
            "sample_rate": 16000,
            "silence_seconds": 3.5,
            "no_speech_timeout_seconds": 12.0,
            "max_record_seconds": 45.0,
            "speech_rms_threshold": 0.003,
            "tts_rate": 185,
            "tts_volume": 1.0,
            "max_spoken_chars": 800,
            "tts_engine": "windows",
            "tts_model": "sapi5",
            "tts_voice": "Microsoft Maria Desktop - Portuguese(Brazil)",
            "tts_buffer_seconds": 0.4,
            "tts_stream": True,
            "wake_word_enabled": False,
            "wake_word": "jarvis",
            "wake_word_required": False,
            "wake_word_model": "base",
            "kokoro_speed": 1.0,
            "transcription_engine": "local",
            "transcription_cloud_model": "gpt-4o-transcribe",
        },
        "providers": {
            "ollama": {
                "kind": "ollama",
                "enabled": True,
                "model": "qwen3",
                "base_url": "http://localhost:11434/v1",
            },
            "lmstudio": {
                "kind": "lmstudio",
                "enabled": True,
                "model": "local-model",
                "base_url": "http://localhost:1234/v1",
            },
            "openai": {
                "kind": "openai",
                "enabled": False,
                "model": "gpt-5.6-luna",
                "base_url": "https://api.openai.com/v1",
                "api_key_env": "OPENAI_API_KEY",
            },
            "claude": {
                "kind": "anthropic",
                "enabled": False,
                "model": "claude-sonnet-5",
                "base_url": "https://api.anthropic.com/v1",
                "api_key_env": "ANTHROPIC_API_KEY",
            },
            "gemini": {
                "kind": "gemini",
                "enabled": False,
                "model": "gemini-3.7-flash",
                "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
                "api_key_env": "GEMINI_API_KEY",
            },
        },
    }


def load_config(path: str | Path | None = None) -> AppConfig:
    config_path = Path(path or os.environ.get("JARVIS_CONFIG", "config.toml"))
    if config_path.exists():
        try:
            with config_path.open("rb") as handle:
                data = tomllib.load(handle)
        except (OSError, tomllib.TOMLDecodeError) as exc:
            raise ConfigurationError(f"Não foi possível ler {config_path}: {exc}") from exc
        base_dir = config_path.resolve().parent
    else:
        data = _default_data()
        base_dir = Path.cwd()

    app_data = data.get("app", {})
    voice_data = data.get("voice", {})
    providers_data = data.get("providers", {})
    if not isinstance(providers_data, dict) or not providers_data:
        raise ConfigurationError("A configuração precisa conter pelo menos um provedor.")

    providers: dict[str, ProviderConfig] = {}
    for name, item in providers_data.items():
        if not isinstance(item, dict):
            raise ConfigurationError(f"Configuração invalida do provedor {name}.")
        try:
            providers[name] = ProviderConfig(
                name=name,
                kind=str(item.get("kind", name)),
                enabled=bool(item.get("enabled", True)),
                model=str(item["model"]),
                base_url=str(item["base_url"]).rstrip("/"),
                api_key_env=item.get("api_key_env"),
                timeout_seconds=float(item.get("timeout_seconds", 120)),
            )
        except KeyError as exc:
            raise ConfigurationError(
                f"Campo obrigatório ausente em providers.{name}: {exc.args[0]}"
            ) from exc

    database_path = Path(app_data.get("database_path", "data/jarvis.db"))
    if not database_path.is_absolute():
        database_path = base_dir / database_path

    model_cache_path = Path(voice_data.get("model_cache_path", "data/models"))
    if not model_cache_path.is_absolute():
        model_cache_path = base_dir / model_cache_path

    voice = VoiceConfig(
        enabled=bool(voice_data.get("enabled", True)),
        language=str(voice_data.get("language", "pt")),
        whisper_model=str(voice_data.get("whisper_model", "small")),
        device=str(voice_data.get("device", "cpu")),
        compute_type=str(voice_data.get("compute_type", "int8")),
        model_cache_path=model_cache_path,
        sample_rate=int(voice_data.get("sample_rate", 16000)),
        silence_seconds=float(voice_data.get("silence_seconds", 3.5)),
        no_speech_timeout_seconds=float(
            voice_data.get("no_speech_timeout_seconds", 12.0)
        ),
        max_record_seconds=float(voice_data.get("max_record_seconds", 45.0)),
        speech_rms_threshold=float(voice_data.get("speech_rms_threshold", 0.003)),
        tts_rate=int(voice_data.get("tts_rate", 185)),
        tts_volume=float(voice_data.get("tts_volume", 1.0)),
        max_spoken_chars=int(voice_data.get("max_spoken_chars", 800)),
        tts_engine=str(voice_data.get("tts_engine", "windows")),
        tts_model=str(voice_data.get("tts_model", "sapi5")),
        tts_voice=str(
            voice_data.get(
                "tts_voice", "Microsoft Maria Desktop - Portuguese(Brazil)"
            )
        ),
        tts_buffer_seconds=float(voice_data.get("tts_buffer_seconds", 0.4)),
        tts_stream=bool(voice_data.get("tts_stream", True)),
        wake_word_enabled=bool(voice_data.get("wake_word_enabled", False)),
        wake_word=str(voice_data.get("wake_word", "jarvis")),
        wake_word_required=bool(voice_data.get("wake_word_required", False)),
        wake_word_model=str(voice_data.get("wake_word_model", "base")),
        kokoro_speed=float(voice_data.get("kokoro_speed", 1.0)),
        transcription_engine=str(voice_data.get("transcription_engine", "local")),
        transcription_cloud_model=str(
            voice_data.get("transcription_cloud_model", "gpt-4o-transcribe")
        ),
    )

    default_provider = str(app_data.get("default_provider", "ollama"))
    if default_provider not in providers:
        raise ConfigurationError(f"Provedor padrão desconhecido: {default_provider}")

    fallback_order = tuple(app_data.get("fallback_order", providers.keys()))
    unknown = [name for name in fallback_order if name not in providers]
    if unknown:
        raise ConfigurationError(f"Provedores desconhecidos no fallback: {', '.join(unknown)}")

    agent_data = data.get("agent", {})
    roots = agent_data.get("allowed_roots", [])
    agent = AgentConfig(
        enabled=bool(agent_data.get("enabled", False)),
        filesystem_read=bool(agent_data.get("filesystem_read", True)),
        filesystem_write=bool(agent_data.get("filesystem_write", False)),
        shell=bool(agent_data.get("shell", False)),
        browser=bool(agent_data.get("browser", False)),
        ssh=bool(agent_data.get("ssh", False)),
        allowed_roots=tuple(str(item) for item in roots if str(item).strip()),
        max_iterations=int(agent_data.get("max_iterations", 12)),
        shell_timeout_seconds=float(agent_data.get("shell_timeout_seconds", 60.0)),
        max_output_chars=int(agent_data.get("max_output_chars", 12000)),
    )

    vision_data = data.get("vision", {})
    vision = VisionConfig(
        enabled=bool(vision_data.get("enabled", False)),
        camera_index=int(vision_data.get("camera_index", 0)),
        jpeg_quality=int(vision_data.get("jpeg_quality", 85)),
        timeout_seconds=float(vision_data.get("timeout_seconds", 45.0)),
    )

    return AppConfig(
        database_path=database_path,
        default_provider=default_provider,
        fallback_order=fallback_order,
        system_prompt=str(app_data.get("system_prompt", DEFAULT_SYSTEM_PROMPT)),
        providers=providers,
        voice=voice,
        agent=agent,
        vision=vision,
        weather_city=str(app_data.get("weather_city", "São Paulo")).strip() or "São Paulo",
    )
