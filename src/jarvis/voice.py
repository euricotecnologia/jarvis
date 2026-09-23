from __future__ import annotations

import base64
import importlib.util
import json
import os
import queue
import re
import sys
import threading
import time
import types
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Callable, Iterator

from jarvis.config import VoiceConfig


class VoiceError(RuntimeError):
    """Falha recuperavel no subsistema de voz."""


def missing_voice_dependencies() -> list[str]:
    modules = ("numpy", "sounddevice", "faster_whisper", "pyttsx3")
    return [name for name in modules if importlib.util.find_spec(name) is None]


def kokoro_available() -> bool:
    """A voz neural local (Kokoro) precisa de kokoro-onnx + espeakng-loader."""
    return (
        importlib.util.find_spec("kokoro_onnx") is not None
        and importlib.util.find_spec("espeakng_loader") is not None
        and importlib.util.find_spec("phonemizer") is not None
    )


KOKORO_VOICES = ("pf_dora", "pm_alex", "pm_santa")


_URL_RE = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
_EMOJI_RE = re.compile(
    r"[\U00010000-\U0010ffff\u2600-\u26ff\u2700-\u27bf\ufe00-\ufe0f\u200d\u20e3\u2300-\u23ff\u2b50\u2b55\u2934\u2935\u25aa-\u25fe]",
    flags=re.UNICODE,
)


def prepare_speech_text(text: str, max_chars: int) -> str:
    """Limpa o texto para ser LIDO em voz alta: sem markdown, sem URLs, sem código, sem emojis."""
    cleaned = re.sub(r"```.*?```", " (ha um bloco de código na tela) ", text, flags=re.S)
    cleaned = re.sub(r"`([^`]+)`", r"\1", cleaned)
    # Links markdown: fica so o texto; se o texto também for uma URL, some.
    cleaned = re.sub(
        r"!?\[([^\]]*)\]\([^)]+\)",
        lambda m: "" if _URL_RE.fullmatch(m.group(1).strip()) else m.group(1),
        cleaned,
    )
    cleaned = _URL_RE.sub("o link", cleaned)
    cleaned = re.sub(r"^\s*[#>]+\s*", "", cleaned, flags=re.M)
    cleaned = re.sub(r"^\s*[*+\-]\s+", "", cleaned, flags=re.M)  # marcador de lista
    cleaned = re.sub(r"[*_~`|]", "", cleaned)
    cleaned = _EMOJI_RE.sub("", cleaned)  # remove emojis para a voz não descrevê-los
    cleaned = re.sub(r"\bo link\b(?:[\s,:]+o link\b)+", "o link", cleaned)
    cleaned = re.sub(r"[ \t]*\n[ \t]*", ". ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    # Frases de introdução de link que ficaram penduradas sem o link.
    cleaned = re.sub(
        r"[\.\s]*\b(aqui (?:est[aá]|vai) o link|segue o link|o link (?:[eé]|abaixo)|"
        r"confira (?:em|no link)|acesse (?:aqui|o link)|link[:：])\s*[:：]?\s*$",
        ".",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"\s*\.\s*\.+", ".", cleaned).strip()
    if not cleaned:
        return ""
    if len(cleaned) <= max_chars:
        return cleaned
    shortened = cleaned[:max_chars].rsplit(" ", 1)[0].rstrip(".,;: ")
    return f"{shortened}. O resto esta escrito na tela."


@dataclass(slots=True)
class RecordingResult:
    audio: object
    duration_seconds: float


class VoiceService:
    def __init__(self, config: VoiceConfig) -> None:
        self.config = config
        self._model = None
        self._model_lock = threading.Lock()
        self._speaker_lock = threading.Lock()
        self._speaker = None
        self._stop_speaking = threading.Event()
        self._kokoro = None
        self._kokoro_lock = threading.Lock()
        self._probe_model = None
        self._probe_lock = threading.Lock()

    @property
    def available(self) -> bool:
        return self.config.enabled and not missing_voice_dependencies()

    def assert_available(self) -> None:
        if not self.config.enabled:
            raise VoiceError("O recurso de voz está desativado em config.toml.")
        missing = missing_voice_dependencies()
        if missing:
            names = ", ".join(missing)
            raise VoiceError(
                f"Dependencias de voz ausentes ({names}). Instale com: "
                '.\\.venv\\Scripts\\python.exe -m pip install -e ".[full]"'
            )

    def record_until_silence(
        self,
        stop_event: threading.Event,
        level_callback: Callable[[float], None] | None = None,
    ) -> RecordingResult:
        self.assert_available()
        import numpy as np
        import sounddevice as sd

        cfg = self.config
        blocks: queue.Queue[object] = queue.Queue()
        recorded: list[object] = []
        heard_speech = False
        last_speech_at = 0.0
        started_at = time.monotonic()

        def callback(indata, frames, timing, status) -> None:  # noqa: ANN001
            del frames, timing
            if status:
                blocks.put(VoiceError(f"Falha no microfone: {status}"))
                return
            blocks.put(indata[:, 0].copy())

        try:
            with sd.InputStream(
                samplerate=cfg.sample_rate,
                channels=1,
                dtype="float32",
                blocksize=max(800, cfg.sample_rate // 10),
                callback=callback,
            ):
                while not stop_event.is_set():
                    now = time.monotonic()
                    elapsed = now - started_at
                    if elapsed >= cfg.max_record_seconds:
                        break
                    if not heard_speech and elapsed >= cfg.no_speech_timeout_seconds:
                        raise VoiceError("Não detectei fala. Tente novamente mais perto do microfone.")
                    try:
                        block = blocks.get(timeout=0.25)
                    except queue.Empty:
                        continue
                    if isinstance(block, Exception):
                        raise block
                    recorded.append(block)
                    rms = float(np.sqrt(np.mean(np.square(block), dtype=np.float64)))
                    if level_callback:
                        level_callback(min(1.0, rms / max(cfg.speech_rms_threshold * 5, 0.001)))
                    if rms >= cfg.speech_rms_threshold:
                        heard_speech = True
                        last_speech_at = now
                    elif heard_speech and now - last_speech_at >= max(cfg.silence_seconds, 2.5):
                        break
        except VoiceError:
            raise
        except Exception as exc:
            raise VoiceError(
                "Não consegui acessar o microfone. Verifique o dispositivo padrão e "
                "a permissão de Microfone nas Configurações do Windows."
            ) from exc

        # Drena blocos restantes na fila para não perder o final da fala
        while True:
            try:
                block = blocks.get_nowait()
                if not isinstance(block, Exception):
                    recorded.append(block)
            except queue.Empty:
                break

        if not heard_speech or not recorded:
            raise VoiceError("Nenhuma fala foi detectada.")
        audio = np.concatenate(recorded).astype(np.float32, copy=False)
        return RecordingResult(audio=audio, duration_seconds=len(audio) / cfg.sample_rate)

    def _get_model(self):  # noqa: ANN202
        if self._model is not None:
            return self._model
        with self._model_lock:
            if self._model is None:
                WhisperModel = _load_whisper_model_class()

                self.config.model_cache_path.mkdir(parents=True, exist_ok=True)
                self._model = WhisperModel(
                    self.config.whisper_model,
                    device=self.config.device,
                    compute_type=self.config.compute_type,
                    download_root=str(self.config.model_cache_path),
                )
        return self._model

    def _get_probe_model(self):  # noqa: ANN202
        """Modelo leve so para a palavra de ativação (escuta continua).

        Se `wake_word_model` for igual ao modelo principal, reaproveita.
        """
        probe_name = (self.config.wake_word_model or "").strip()
        if not probe_name or probe_name == self.config.whisper_model:
            return self._get_model()
        if self._probe_model is not None:
            return self._probe_model
        with self._probe_lock:
            if self._probe_model is None:
                WhisperModel = _load_whisper_model_class()
                self.config.model_cache_path.mkdir(parents=True, exist_ok=True)
                self._probe_model = WhisperModel(
                    probe_name,
                    device=self.config.device,
                    compute_type=self.config.compute_type,
                    download_root=str(self.config.model_cache_path),
                )
        return self._probe_model

    def transcribe(self, audio: object) -> str:
        self.assert_available()
        if self.config.transcription_engine == "openai":
            try:
                return self._transcribe_openai(audio)
            except VoiceError as cloud_error:
                # Cai para o modelo local se a nuvem falhar (sem chave, offline...).
                try:
                    text = self._transcribe_local(audio)
                except VoiceError:
                    raise cloud_error
                return text
        return self._transcribe_local(audio)

    def _transcribe_local(self, audio: object, *, probe: bool = False) -> str:
        try:
            if probe:
                # Escuta continua da palavra de ativação: modelo leve, mas com
                # busca em feixe e um prompt que enviesa para a grafia "Jarvis"
                # (o tiny/base erra muito o nome sem essa dica).
                model = self._get_probe_model()
                name = self.config.wake_word.capitalize()
                segments, _ = model.transcribe(
                    audio,
                    language=self.config.language,
                    task="transcribe",
                    beam_size=3,
                    vad_filter=False,
                    condition_on_previous_text=False,
                    initial_prompt=(
                        f"O usuario chama o assistente pelo nome {name}. "
                        f"Exemplos: \"{name}\". \"{name}, que horas sao?\". "
                        f"\"Ei {name}, abre o YouTube.\""
                    ),
                )
            else:
                model = self._get_model()
                segments, _ = model.transcribe(
                    audio,
                    language=self.config.language,
                    task="transcribe",
                    beam_size=3,
                    best_of=3,
                    vad_filter=True,
                    vad_parameters={"min_silence_duration_ms": 1200, "speech_pad_ms": 500},
                    condition_on_previous_text=False,
                    initial_prompt=(
                        "Conversa em português do Brasil com pontuação, números, perguntas e vocabulário natural. "
                        "Exemplos: 'eu tinha 5 laranjas', 'quantos sobraram?', 'bom dia Jarvis'."
                    ),
                )
            text = " ".join(segment.text.strip() for segment in segments).strip()
        except VoiceError:
            raise
        except Exception as exc:
            raise VoiceError(
                "Não consegui carregar ou executar o modelo local de transcrição."
            ) from exc
        if not text:
            raise VoiceError("Ouvi o audio, mas não consegui entender as palavras.")
        return text

    def _transcribe_openai(self, audio: object) -> str:
        """Transcrição pela API da OpenAI (/v1/audio/transcriptions)."""
        import io
        import wave

        import numpy as np

        key = os.environ.get("OPENAI_API_KEY")
        if not key:
            raise VoiceError(
                "Defina a OPENAI_API_KEY para usar a transcrição da OpenAI."
            )

        arr = np.asarray(audio, dtype=np.float32)
        pcm = (np.clip(arr, -1.0, 1.0) * 32767.0).astype("<i2").tobytes()
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(int(self.config.sample_rate))
            wav.writeframes(pcm)

        boundary = "jarvis" + os.urandom(12).hex()

        def field(name: str, value: str) -> bytes:
            return (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
                f"{value}\r\n"
            ).encode("utf-8")

        body = b"".join(
            (
                field("model", self.config.transcription_cloud_model),
                field("language", self.config.language),
                field("response_format", "text"),
                (
                    f"--{boundary}\r\n"
                    'Content-Disposition: form-data; name="file"; '
                    'filename="fala.wav"\r\n'
                    "Content-Type: audio/wav\r\n\r\n"
                ).encode("utf-8"),
                wav_buffer.getvalue(),
                f"\r\n--{boundary}--\r\n".encode("utf-8"),
            )
        )

        request = urllib.request.Request(
            "https://api.openai.com/v1/audio/transcriptions",
            data=body,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": f"multipart/form-data; boundary={boundary}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                text = response.read().decode("utf-8", errors="replace").strip()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise VoiceError(
                f"Transcrição OpenAI recusada (HTTP {exc.code}): {detail[:200]}"
            ) from exc
        except (OSError, urllib.error.URLError) as exc:
            raise VoiceError(
                f"Não consegui acessar a transcrição da OpenAI: {exc}"
            ) from exc
        if not text:
            raise VoiceError("A OpenAI ouviu o audio mas não devolveu texto.")
        return text

    def transcribe_probe(self, audio: object) -> str:
        """Transcrição de um trecho curto para a palavra de ativação.

        SEMPRE local: a escuta e continua, mandar cada som para a nuvem seria
        caro e lento. Devolve "" em vez de levantar exceção.
        """
        try:
            return self._transcribe_local(audio, probe=True)
        except Exception:
            return ""

    def warm_up(self) -> None:
        """Carrega o modelo local de transcrição fora do caminho critico.

        A primeira transcrição carrega o faster-whisper do disco, o que pode
        levar varios segundos. Chamar isto na inicialização faz esse custo
        acontecer enquanto o usuário ainda nem falou.
        """
        if not self.available:
            return
        try:
            self._get_probe_model()  # leve: deixa a palavra de ativação pronta
        except Exception:
            pass
        try:
            self._get_model()
        except Exception:
            pass

    def speak(self, text: str) -> str | None:
        self.assert_available()
        self._stop_speaking.clear()
        spoken = prepare_speech_text(text, self.config.max_spoken_chars)
        if not spoken:
            return None
        return self._render_speech(spoken)

    def speak_segment(self, text: str) -> str | None:
        """Fala um trecho ja limpo (uma frase) sem truncar pelo limite global."""
        self.assert_available()
        self._stop_speaking.clear()
        spoken = prepare_speech_text(text, len(text) + 1)
        if not spoken:
            return None
        return self._render_speech(spoken)

    def _render_speech(self, spoken: str) -> str | None:
        engine = self.config.tts_engine
        if engine == "gemini":
            return self._render_with_fallback(self._speak_gemini, "Gemini", spoken)
        if engine == "kokoro":
            return self._render_with_fallback(self._speak_kokoro, "Kokoro", spoken)
        self._speak_windows(spoken)
        return None

    def _render_with_fallback(self, primary, label: str, spoken: str) -> str | None:
        try:
            primary(spoken)
            return None
        except VoiceError as primary_error:
            if self._stop_speaking.is_set():
                return None
            try:
                self._speak_windows(spoken)
            except VoiceError as windows_error:
                raise VoiceError(
                    f"{label} falhou ({primary_error}) e a voz local também "
                    f"falhou ({windows_error})."
                ) from windows_error
            return f"{label} indisponível; usei a voz local. Motivo: {primary_error}"

    def _speak_windows(self, spoken: str) -> None:
        try:
            import pyttsx3

            with self._speaker_lock:
                engine = pyttsx3.init("sapi5")
                self._speaker = engine
                engine.setProperty("rate", self.config.tts_rate)
                engine.setProperty("volume", self.config.tts_volume)
                self._select_windows_voice(engine)
                engine.say(spoken)
                engine.runAndWait()
                engine.stop()
                self._speaker = None
        except Exception as exc:
            self._speaker = None
            raise VoiceError("Não consegui reproduzir a resposta pela voz do Windows.") from exc

    def _select_windows_voice(self, engine) -> bool:  # noqa: ANN001
        preferred = self.config.tts_voice.lower().strip()
        if preferred:
            for voice in engine.getProperty("voices"):
                description = " ".join(
                    (str(getattr(voice, "id", "")), str(getattr(voice, "name", "")))
                ).lower()
                if preferred in description or description in preferred:
                    engine.setProperty("voice", voice.id)
                    return True
        terms = ("portuguese", "portugues", "brazil", "brasil", "pt-br", "pt_br")
        for voice in engine.getProperty("voices"):
            languages = " ".join(str(item) for item in getattr(voice, "languages", ()))
            description = " ".join(
                (str(getattr(voice, "id", "")), str(getattr(voice, "name", "")), languages)
            ).lower()
            if any(term in description for term in terms):
                engine.setProperty("voice", voice.id)
                return True
        return False

    @staticmethod
    def windows_voice_names() -> list[str]:
        try:
            import pyttsx3

            engine = pyttsx3.init("sapi5")
            names = [
                str(getattr(voice, "name", "") or getattr(voice, "id", ""))
                for voice in engine.getProperty("voices")
            ]
            engine.stop()
            return [name for name in names if name]
        except Exception:
            return [
                "Microsoft Maria Desktop - Portuguese(Brazil)",
                "Microsoft Zira Desktop - English (United States)",
            ]

    def _kokoro_paths(self) -> tuple[Path, Path]:
        base = self.config.model_cache_path / "kokoro"
        return base / "kokoro-v1.0.onnx", base / "voices-v1.0.bin"

    def _get_kokoro(self):  # noqa: ANN202
        if self._kokoro is not None:
            return self._kokoro
        with self._kokoro_lock:
            if self._kokoro is not None:
                return self._kokoro
            try:
                import espeakng_loader
                from kokoro_onnx import Kokoro
                from phonemizer.backend.espeak.wrapper import EspeakWrapper
            except ImportError as exc:
                raise VoiceError(
                    "Voz Kokoro ausente. Instale com: "
                    '.\\.venv\\Scripts\\python.exe -m pip install kokoro-onnx'
                ) from exc

            model_path, voices_path = self._kokoro_paths()
            if not model_path.exists() or not voices_path.exists():
                raise VoiceError(
                    f"Modelos do Kokoro não encontrados em {model_path.parent}. "
                    "Baixe kokoro-v1.0.onnx e voices-v1.0.bin."
                )
            EspeakWrapper.set_library(espeakng_loader.get_library_path())
            EspeakWrapper.set_data_path(espeakng_loader.get_data_path())
            self._kokoro = Kokoro(str(model_path), str(voices_path))
        return self._kokoro

    def _speak_kokoro(self, spoken: str) -> None:
        """Voz neural local (Kokoro ONNX). pt-BR, sem chave, sem cota."""
        if self._stop_speaking.is_set():
            return
        voice = self.config.tts_voice
        if voice not in KOKORO_VOICES:
            voice = KOKORO_VOICES[0]
        try:
            model = self._get_kokoro()
            samples, sample_rate = model.create(
                spoken, voice=voice, speed=self.config.kokoro_speed, lang="pt-br"
            )
        except VoiceError:
            raise
        except Exception as exc:
            raise VoiceError(f"Falha ao sintetizar com o Kokoro: {exc}") from exc

        if self._stop_speaking.is_set():
            return
        try:
            import numpy as np
            import sounddevice as sd

            audio = np.asarray(samples, dtype=np.float32)
            sd.play(audio, samplerate=int(sample_rate), blocking=True)
        except Exception as exc:
            raise VoiceError(
                "O Kokoro gerou o audio, mas o Windows não conseguiu reproduzi-lo. "
                "Verifique o dispositivo de saída padrão."
            ) from exc

    def _speak_gemini(self, spoken: str) -> None:
        """Sintetiza `spoken` pela Interactions API do Gemini (/v1beta/interactions).

        Contrato conforme a doc oficial (Api-Revision 2026-05-20): `input`,
        `response_format`, `generation_config.speech_config`, e para streaming
        `stream: true` com eventos SSE `step.delta`. Tenta de novo em 429/500/503,
        que a doc descreve como picos temporarios de demanda.
        """
        key = os.environ.get("GEMINI_API_KEY")
        if not key:
            raise VoiceError(
                "Defina a variavel GEMINI_API_KEY para usar a voz Gemini TTS."
            )
        model = self.config.tts_model
        payload: dict[str, object] = {
            "model": model,
            "input": f"[calmly, warm] {spoken}",
            "response_format": {"type": "audio"},
            "generation_config": {
                "speech_config": [{"voice": self.config.tts_voice}]
            },
        }
        streaming = self.config.tts_stream and not model.startswith("gemini-2.5")
        if streaming:
            payload["stream"] = True
        headers = {
            "Content-Type": "application/json",
            "Accept": "text/event-stream" if streaming else "application/json",
            "x-goog-api-key": key,
            "Api-Revision": "2026-05-20",
        }
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")

        data: dict[str, object] | None = None
        for attempt in range(3):
            if self._stop_speaking.is_set():
                return
            request = urllib.request.Request(
                "https://generativelanguage.googleapis.com/v1beta/interactions",
                data=body,
                headers=headers,
                method="POST",
            )
            try:
                with urllib.request.urlopen(request, timeout=45) as response:
                    if streaming:
                        self._play_gemini_stream(response)
                        return
                    data = json.loads(response.read().decode("utf-8"))
                break
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace")
                if exc.code in (429, 500, 503) and attempt < 2:
                    time.sleep(1.5 * (attempt + 1))
                    continue
                raise VoiceError(
                    f"Gemini TTS recusou a solicitação (HTTP {exc.code}): {detail[:300]}"
                ) from exc
            except VoiceError:
                raise
            except (ValueError, OSError, urllib.error.URLError) as exc:
                if attempt < 2:
                    time.sleep(1.0 * (attempt + 1))
                    continue
                raise VoiceError(f"Não consegui acessar o Gemini TTS: {exc}") from exc

        if data is None:
            raise VoiceError("O Gemini TTS não devolveu resposta.")

        try:
            pcm, sample_rate = extract_gemini_audio(data)
        except (KeyError, ValueError) as exc:
            status = str(data.get("status", "desconhecido"))
            raise VoiceError(
                f"O Gemini respondeu com status {status}, mas sem audio reproduzivel."
            ) from exc

        try:
            self._play_pcm(pcm, sample_rate=sample_rate)
        except Exception as exc:
            raise VoiceError(
                "O Gemini gerou o audio, mas o Windows não conseguiu reproduzi-lo. "
                "Verifique o dispositivo de saída padrão."
            ) from exc

    @staticmethod
    def _play_pcm(pcm: bytes, sample_rate: int) -> None:
        import numpy as np
        import sounddevice as sd

        audio = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0
        sd.play(audio, samplerate=sample_rate, blocking=True)

    def _play_gemini_stream(self, response: object) -> None:
        import sounddevice as sd

        output = None
        chunks = 0
        expected_rate = 0
        expected_channels = 0
        buffered: list[bytes] = []
        buffered_bytes = 0

        def start_output() -> None:
            nonlocal output, buffered, buffered_bytes
            if output is not None or not buffered:
                return
            output = sd.RawOutputStream(
                samplerate=expected_rate,
                channels=expected_channels,
                dtype="int16",
                latency="high",
            )
            output.start()
            output.write(b"".join(buffered))
            buffered = []
            buffered_bytes = 0

        try:
            for pcm, sample_rate, channels in iter_gemini_audio_chunks(response):
                if self._stop_speaking.is_set():
                    break
                if output is None:
                    if not expected_rate:
                        expected_rate = sample_rate
                        expected_channels = channels
                    elif sample_rate != expected_rate or channels != expected_channels:
                        raise VoiceError(
                            "O formato do audio Gemini mudou durante o streaming."
                        )
                    buffered.append(pcm)
                    buffered_bytes += len(pcm)
                    target_bytes = int(
                        expected_rate
                        * expected_channels
                        * 2
                        * self.config.tts_buffer_seconds
                    )
                    if buffered_bytes >= target_bytes:
                        start_output()
                elif sample_rate != expected_rate or channels != expected_channels:
                    raise VoiceError("O formato do audio Gemini mudou durante o streaming.")
                else:
                    output.write(pcm)
                chunks += 1
            if self._stop_speaking.is_set():
                return
            if chunks == 0:
                raise VoiceError("O Gemini concluiu a resposta sem enviar audio.")
            start_output()
        except VoiceError:
            raise
        except Exception as exc:
            raise VoiceError(
                "O Gemini iniciou o audio, mas o Windows não conseguiu reproduzir "
                "o streaming. Verifique o dispositivo de saída padrão."
            ) from exc
        finally:
            if output is not None:
                try:
                    output.stop()
                finally:
                    output.close()

    def stop_speaking(self) -> None:
        self._stop_speaking.set()
        speaker = self._speaker
        if speaker is not None:
            try:
                speaker.stop()
            except Exception:
                pass
        try:
            import sounddevice as sd

            sd.stop()
        except Exception:
            pass


def _load_whisper_model_class():  # noqa: ANN202
    """Carrega faster-whisper sem PyAV quando o Windows bloquear suas DLLs.

    O Jarvis entrega um array NumPy de 16 kHz diretamente ao transcritor. Nesse
    caminho o PyAV, usado apenas para decodificar arquivos, nunca e chamado. O
    stub evita que uma DLL de FFmpeg bloqueada pelo Smart App Control impeça o
    uso do caminho de audio em memória.
    """
    try:
        __import__("av")
    except ImportError:
        for name in tuple(sys.modules):
            if name == "av" or name.startswith("av."):
                sys.modules.pop(name, None)
        av_stub = types.ModuleType("av")
        invalid_data_error = type("InvalidDataError", (Exception,), {})
        av_stub.error = types.SimpleNamespace(InvalidDataError=invalid_data_error)
        sys.modules["av"] = av_stub

    from faster_whisper import WhisperModel

    return WhisperModel


_GEMINI_DEFAULT_RATE = 24000


def _decode_gemini_audio_blob(blob: dict[str, object]) -> tuple[bytes, int] | None:
    """Um `{mime_type, data}` (ou legado `{type, data, sample_rate}`) -> PCM."""
    encoded = blob.get("data")
    if not isinstance(encoded, str) or not encoded:
        return None
    mime = str(blob.get("mime_type") or blob.get("mimeType") or blob.get("type") or "")
    if mime and "audio" not in mime and mime != "audio":
        return None
    try:
        pcm = base64.b64decode(encoded, validate=True)
    except (ValueError, TypeError) as exc:
        raise ValueError("Audio base64 invalido na resposta Gemini.") from exc
    if not pcm:
        return None
    match = re.search(r"rate=(\d+)", mime)
    rate = (
        int(match.group(1))
        if match
        else int(blob.get("sample_rate") or _GEMINI_DEFAULT_RATE)
    )
    return pcm, rate


def _raise_gemini_error(event: dict[str, object]) -> None:
    error = event.get("error")
    if not isinstance(error, dict):
        interaction = event.get("interaction")
        status = (
            interaction.get("status")
            if isinstance(interaction, dict)
            else event.get("status")
        )
        raise VoiceError(f"O Gemini TTS terminou com status '{status}'.")
    code = str(error.get("code") or error.get("status") or "erro").lower()
    message = str(error.get("message", "Falha no Gemini TTS."))
    if code in {"quota_exceeded", "resource_exhausted", "429"}:
        raise VoiceError(
            "A cota do Gemini TTS foi excedida. Aguarde a renovação da cota "
            "ou use a voz Windows local."
        )
    raise VoiceError(f"Gemini TTS ({code}): {message[:240]}")


def extract_gemini_audio(data: dict[str, object]) -> tuple[bytes, int]:
    """Extrai audio de uma resposta NÃO-streaming da Interactions API."""
    if isinstance(data.get("error"), dict) or (
        isinstance(data.get("interaction"), dict)
        and data["interaction"].get("status") not in (None, "completed")  # type: ignore[union-attr]
    ):
        _raise_gemini_error(data)

    candidates: list[object] = [data.get("output_audio")]
    for container_key in ("steps", "output"):
        container = data.get(container_key)
        if isinstance(container, list):
            for item in reversed(container):
                if isinstance(item, dict):
                    content = item.get("content") or item.get("delta")
                    if isinstance(content, list):
                        candidates.extend(reversed(content))
                    elif isinstance(content, dict):
                        candidates.append(content)

    for candidate in candidates:
        if isinstance(candidate, dict):
            decoded = _decode_gemini_audio_blob(candidate)
            if decoded is not None:
                return decoded
    raise KeyError("Nenhum bloco de audio encontrado na resposta Gemini.")


def iter_gemini_audio_chunks(lines: object) -> Iterator[tuple[bytes, int, int]]:
    """Converte eventos SSE da Interactions API em fragmentos PCM (pcm, rate, canais).

    Formato real (verificado 2026-08): cada linha `data:` e um evento com
    `event_type`. O audio chega em `step.delta` como
    `{"delta": {"mime_type": "audio/l16", "data": "<base64>"}}`. Erros vem em
    `event_type == "error"` ou num `interaction` com status != completed.
    """
    for raw_line in lines:  # type: ignore[union-attr]
        line = (
            raw_line.decode("utf-8", errors="replace")
            if isinstance(raw_line, bytes)
            else str(raw_line)
        ).strip()
        if not line.startswith("data:"):
            continue
        value = line[5:].strip()
        if value == "[DONE]":
            break
        try:
            event = json.loads(value)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue

        event_type = event.get("event_type")
        if event_type == "error" or isinstance(event.get("error"), dict):
            _raise_gemini_error(event)
        if event_type == "interaction.completed":
            interaction = event.get("interaction")
            if (
                isinstance(interaction, dict)
                and interaction.get("status") not in (None, "completed")
            ):
                _raise_gemini_error(event)
            continue
        if event_type not in (None, "step.delta"):
            continue

        delta = event.get("delta")
        if not isinstance(delta, dict):
            continue
        decoded = _decode_gemini_audio_blob(delta)
        if decoded is not None:
            pcm, rate = decoded
            yield pcm, rate, int(delta.get("channels") or 1)
