from __future__ import annotations

import queue
import re
import threading
import time
import unicodedata
from collections import deque
from typing import TYPE_CHECKING, Callable

from jarvis.config import VoiceConfig

if TYPE_CHECKING:
    from jarvis.voice import VoiceService

# Grafias que o Whisper realmente produz ao ouvir "Jarvis" em pt-BR. Curado a
# dedo: NADA que colida com palavra/nome comum (fora "jarbas"/"chaves"/"larvas"
# etc., que geravam ativação falsa com a TV e conversa ao lado).
_JARVIS_VARIANTS = {
    "jarvis", "jarves", "jarvez", "jarviz", "jarvys",
    "jervis", "djarvis", "tcharvis",
}
# So faz fuzzy (1 edição) contra a palavra base, e so em tokens compridos.
_FUZZY_MIN_LEN = 5
# Ruidos/interjeicoes que o Whisper as vezes poe ANTES do nome ("é o Jarvis",
# "ei Jarvis", "hmm Jarvis"). So esses valem como enfeite na frente.
_LEADING_FILLER = {
    "e", "o", "a", "ei", "oi", "ai", "ah", "eh", "he", "ho", "uh", "um",
    "hm", "hmm", "opa", "ola", "ok", "entao", "ó", "é",
}


def _normalize(text: str) -> str:
    stripped = unicodedata.normalize("NFKD", text)
    stripped = stripped.encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"[^a-z ]+", " ", stripped).strip()


def _edit_distance_within(a: str, b: str, limit: int) -> bool:
    if abs(len(a) - len(b)) > limit:
        return False
    previous = list(range(len(b) + 1))
    for i, char_a in enumerate(a, 1):
        current = [i]
        best = i
        for j, char_b in enumerate(b, 1):
            cost = 0 if char_a == char_b else 1
            value = min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + cost)
            current.append(value)
            best = min(best, value)
        if best > limit:
            return False
        previous = current
    return previous[-1] <= limit


def _wake_targets(wake_word: str) -> set[str]:
    target = _normalize(wake_word)
    tokens = set(target.split())
    if "jarvis" in tokens:
        tokens |= _JARVIS_VARIANTS
    return {t for t in tokens if t}


def _fuzzy_bases(wake_word: str) -> set[str]:
    """Palavras contra as quais vale tentar 1 edição (so a base, não as variantes)."""
    return {t for t in _normalize(wake_word).split() if len(t) >= _FUZZY_MIN_LEN}


def _is_wake_token(token: str, targets: set[str], fuzzy: set[str]) -> bool:
    if token in targets:
        return True
    if len(token) < _FUZZY_MIN_LEN:
        return False
    return any(_edit_distance_within(token, base, 1) for base in fuzzy)


def matches_wake_word(text: str, wake_word: str, *, at_start: bool = False) -> bool:
    """True se `text` contem a palavra de ativação.

    `at_start=True` (escuta em segundo plano): so aceita se a palavra estiver
    entre as 3 primeiras — evita disparar com a palavra no meio de uma conversa
    ou da TV, mas tolera um "é", "ó", "ah" que o Whisper as vezes poe na frente.
    `at_start=False` (mensagem digitada): aceita em qualquer posição.
    """
    norm = _normalize(text)
    targets = _wake_targets(wake_word)
    fuzzy = _fuzzy_bases(wake_word)
    if not norm or not targets:
        return False
    tokens = norm.split()
    if any(t in norm for t in targets if " " in t):
        return True
    if not at_start:
        return any(_is_wake_token(t, targets, fuzzy) for t in tokens)
    # escuta em segundo plano: o nome tem que estar na frente. Aceita ate 2
    # tokens antes, mas SO se forem ruido/interjeicao ("é o Jarvis", "ei Jarvis").
    for index, token in enumerate(tokens[:3]):
        if _is_wake_token(token, targets, fuzzy):
            return all(t in _LEADING_FILLER for t in tokens[:index])
    return False


def command_after_wake_word(text: str, wake_word: str) -> str:
    """Devolve o que vem DEPOIS da palavra de ativação (o comando dito junto).

    Ex.: "Jarvis, que horas são?" -> "que horas são?". Vazio se so a palavra
    foi dita ou se nada uti vem depois.
    """
    targets = _wake_targets(wake_word)
    fuzzy = _fuzzy_bases(wake_word)
    raw_tokens = re.findall(r"\S+", text)
    for index, raw in enumerate(raw_tokens):
        if _is_wake_token(_normalize(raw), targets, fuzzy):
            rest = " ".join(raw_tokens[index + 1 :]).strip()
            return re.sub(r"^[\s,.:;!?\-–—]+", "", rest).strip()
    return ""


def strip_wake_prefix(text: str, wake_word: str) -> str | None:
    """Se a mensagem COMECA com a palavra de ativação, devolve o resto.

    Usado no modo "exigir o nome": "jarvis, abra o D:" -> "abra o D:".
    Devolve None se a palavra não está nas primeiras 3 palavras -> a mensagem
    deve ser ignorada.
    """
    targets = _wake_targets(wake_word)
    fuzzy = _fuzzy_bases(wake_word)
    raw_tokens = re.findall(r"\S+", text)
    for index, raw in enumerate(raw_tokens[:3]):
        if _is_wake_token(_normalize(raw), targets, fuzzy):
            rest = " ".join(raw_tokens[index + 1 :]).strip()
            return re.sub(r"^[\s,.:;!?\-–—]+", "", rest).strip()
    return None


class WakeWordListener:
    """Escuta o microfone em segundo plano e dispara `on_wake` ao ouvir a palavra.

    Reaproveita o modelo Whisper ja carregado pelo `VoiceService` (rápido, quente
    e preciso). O reconhecimento so roda quando ha som acima do limiar — o CPU
    fica ocioso no silencio.
    """

    def __init__(
        self,
        config: VoiceConfig,
        voice: "VoiceService",
        on_wake: Callable[[str], None],
        on_status: Callable[[str], None] | None = None,
        on_heard: Callable[[str], None] | None = None,
    ) -> None:
        self.config = config
        self._voice = voice
        self._on_wake = on_wake
        self._on_status = on_status or (lambda _message: None)
        self._on_heard = on_heard or (lambda _text: None)
        self._running = False
        self._paused = threading.Event()
        self._thread: threading.Thread | None = None
        self._stream = None
        self._sample_rate = 16000
        self._block = 1600  # 100 ms
        # Limiar de captura: um pouco ABAIXO do limiar de comando, senao a
        # palavra dita de longe / em voz normal nem chega a ser gravada. Os
        # falsos positivos sao barrados depois (transcrição + `at_start`).
        self._threshold = max(config.speech_rms_threshold * 0.85, 0.009)

    # -- ciclo de vida ----------------------------------------------------
    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._paused.clear()
        self._thread = threading.Thread(
            target=self._run, daemon=True, name="jarvis-wakeword"
        )
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        thread = self._thread
        if thread is not None:
            thread.join(timeout=3)
        self._thread = None

    def pause(self) -> None:
        self._paused.set()

    def resume(self) -> None:
        self._paused.clear()

    @property
    def active(self) -> bool:
        return self._running

    # -- implementação --------------------------------------------------
    def _run(self) -> None:
        try:
            import numpy as np
            import sounddevice as sd
        except Exception as exc:  # noqa: BLE001
            self._on_status(f"dependencias de audio ausentes: {exc}")
            self._running = False
            return

        # Garante o modelo carregado antes de comecar a ouvir.
        self._voice.warm_up()

        blocks: queue.Queue = queue.Queue(maxsize=120)  # ~12 s de folga

        def _callback(indata, frames, timing, status) -> None:  # noqa: ANN001
            del frames, timing, status
            if self._paused.is_set():
                return
            try:
                blocks.put_nowait(indata[:, 0].copy())
            except queue.Full:
                try:  # descarta o mais antigo, nunca trava o audio
                    blocks.get_nowait()
                    blocks.put_nowait(indata[:, 0].copy())
                except queue.Empty:
                    pass

        preroll: deque = deque(maxlen=6)  # ~0.6 s antes da fala
        captured: list | None = None
        silence = 0
        heard_anything = False
        min_len = int(0.3 * self._sample_rate)

        try:
            stream = sd.InputStream(
                samplerate=self._sample_rate,
                channels=1,
                dtype="float32",
                blocksize=self._block,
                callback=_callback,
            )
        except Exception as exc:  # noqa: BLE001
            self._on_status(f"não consegui abrir o microfone: {exc}")
            self._running = False
            return

        # O stream fica ABERTO o tempo todo. A transcrição roda enquanto o
        # callback continua enchendo a fila -> nada de "janela surda" depois
        # de cada palavra (era por isso que so pegava depois de repetir muito).
        with stream:
            while self._running:
                if self._paused.is_set():
                    captured = None
                    silence = 0
                    _drain(blocks)
                    time.sleep(0.08)
                    continue
                try:
                    block = blocks.get(timeout=0.4)
                except queue.Empty:
                    continue

                rms = float(np.sqrt(np.mean(np.square(block))))
                speaking = rms >= self._threshold

                if captured is None:
                    preroll.append(block)
                    if speaking:
                        captured = list(preroll) + [block]
                        silence = 0
                    continue

                captured.append(block)
                if speaking:
                    silence = 0
                else:
                    silence += 1

                # a palavra de ativação (com comando junto) cabe em ~4 s
                too_long = len(captured) * 0.1 > 4.5
                if silence < 6 and not too_long:
                    continue

                segment = list(captured)
                audio = np.concatenate(segment).astype(np.float32, copy=False)
                captured = None
                silence = 0
                preroll.clear()
                if len(audio) < min_len or not self._is_voice(segment, np):
                    continue

                text = ""
                try:
                    text = self._voice.transcribe_probe(audio)
                except Exception as exc:  # noqa: BLE001
                    self._on_status(f"escuta interrompida: {exc}")
                if text and not heard_anything:
                    heard_anything = True
                    self._on_status("microfone ok, estou ouvindo.")
                if text:
                    self._on_heard(text)
                if not matches_wake_word(
                    text, self.config.wake_word, at_start=True
                ):
                    continue

                # Palavra ouvida: pausa a escuta (a thread continua viva) e
                # entrega o comando dito na mesma frase, se houver.
                self._paused.set()
                _drain(blocks)
                command = command_after_wake_word(text, self.config.wake_word)
                if command and hasattr(self._voice, "transcribe"):
                    try:
                        better = self._voice.transcribe(audio)
                        command = (
                            command_after_wake_word(better, self.config.wake_word)
                            or command
                        )
                    except Exception:  # noqa: BLE001
                        pass
                self._on_wake(command)


    def _is_voice(self, segment: list, np) -> bool:  # noqa: ANN001
        """Rejeita ventilador/clique de teclado antes de gastar o Whisper:
        fala de verdade tem varios blocos acima do limiar e um pico claro.
        """
        rms = [float(np.sqrt(np.mean(np.square(b)))) for b in segment]
        if not rms:
            return False
        voiced = sum(1 for value in rms if value >= self._threshold)
        return voiced >= 3 and max(rms) >= self._threshold * 1.8


def _drain(q: "queue.Queue") -> None:
    try:
        while True:
            q.get_nowait()
    except queue.Empty:
        pass
