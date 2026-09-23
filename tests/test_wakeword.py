import threading
import time
import unittest
from unittest.mock import patch

import numpy as np

from jarvis.wakeword import WakeWordListener, matches_wake_word


class _FakeStream:
    """InputStream falso (modo callback): repete fala + silencio num loop."""

    _LOUD = np.full((1600,), 0.2, dtype=np.float32)
    _QUIET = np.zeros((1600,), dtype=np.float32)
    # 2 blocos de fala, 8 de silencio -> uma "palavra" a cada ~1 s
    _PATTERN = [_LOUD, _LOUD] + [_QUIET] * 8

    def __init__(self, **kw) -> None:
        self._cb = kw.get("callback")
        self._stop = threading.Event()
        self._t: threading.Thread | None = None

    def __enter__(self):
        self._t = threading.Thread(target=self._pump, daemon=True)
        self._t.start()
        return self

    def __exit__(self, *args):
        self._stop.set()
        return False

    def _pump(self) -> None:
        i = 0
        while not self._stop.is_set():
            block = self._PATTERN[i % len(self._PATTERN)]
            i += 1
            if self._cb is not None:
                self._cb(block.reshape(-1, 1), 1600, None, None)
            time.sleep(0.01)  # bem mais rapido que tempo real, so pra andar


class _FakeVoice:
    def __init__(self, transcript: str) -> None:
        self.transcript = transcript
        self.calls = 0

    def warm_up(self) -> None:
        pass

    def transcribe_probe(self, audio) -> str:  # noqa: ARG002
        self.calls += 1
        return self.transcript


class MatchesWakeWordTests(unittest.TestCase):
    def test_jarvis_direct_and_in_phrase(self) -> None:
        self.assertTrue(matches_wake_word("Jarvis", "jarvis"))
        self.assertTrue(matches_wake_word("ei Jarvis, tudo bem?", "jarvis"))
        self.assertTrue(matches_wake_word("  JARVIS!!  ", "jarvis"))

    def test_common_whisper_mistranscriptions_of_jarvis(self) -> None:
        for heard in ("jarves", "jarviz", "djarvis", "tchárvis"):
            self.assertTrue(matches_wake_word(heard, "jarvis"), heard)

    def test_fuzzy_one_edit(self) -> None:
        self.assertTrue(matches_wake_word("jarvís", "jarvis"))  # acento
        self.assertTrue(matches_wake_word("jarviss", "jarvis"))  # 1 insercao

    def test_unrelated_speech_does_not_trigger(self) -> None:
        for heard in (
            "o carro esta na garagem",
            "vamos comer pizza hoje a noite",
            "abre a janela por favor",
            "",
            "travis scott lancou musica",
        ):
            self.assertFalse(matches_wake_word(heard, "jarvis"), heard)

    def test_words_that_used_to_cause_false_triggers(self) -> None:
        # colisoes que ativavam a IA sem chamar pelo nome
        for heard in (
            "as chaves estao na mesa",
            "o jarbas ligou ontem",
            "ele deixou crescer a barba e as barbas",
            "as larvas na horta",
            "me passa as varas de pescar",
            "guarda as chaves de fenda",
        ):
            self.assertFalse(matches_wake_word(heard, "jarvis"), heard)

    def test_at_start_ignores_wake_word_mid_sentence(self) -> None:
        # escuta em segundo plano: nome no meio da conversa nao ativa
        self.assertFalse(
            matches_wake_word("ontem eu vi o jarvis no cinema", "jarvis", at_start=True)
        )
        self.assertFalse(
            matches_wake_word("acho que jarvis e um bom nome", "jarvis", at_start=True)
        )
        # nome na frente ativa
        self.assertTrue(
            matches_wake_word("jarvis abra o youtube", "jarvis", at_start=True)
        )
        self.assertTrue(
            matches_wake_word("ei jarvis, que horas sao", "jarvis", at_start=True)
        )
        # o Whisper as vezes poe um ruido/interjeicao antes do nome -> ainda ativa
        for heard in ("e o jarvis abre o site", "hmm jarvis liga a luz",
                      "ah jarvis", "opa jarvis tudo bem"):
            self.assertTrue(matches_wake_word(heard, "jarvis", at_start=True), heard)
        # mas duas palavras REAIS antes do nome nao ativam
        self.assertFalse(
            matches_wake_word("meu amigo jarvis chegou", "jarvis", at_start=True)
        )
        # digitado (at_start=False): aceita em qualquer lugar
        self.assertTrue(
            matches_wake_word("ontem eu vi o jarvis no cinema", "jarvis")
        )

    def test_custom_wake_word(self) -> None:
        self.assertTrue(matches_wake_word("ok computador, abra o navegador", "computador"))
        self.assertFalse(matches_wake_word("jarvis", "computador"))
        self.assertFalse(matches_wake_word("liga a luz da cozinha", "computador"))


class StripWakePrefixTests(unittest.TestCase):
    def test_only_accepts_name_at_the_front(self) -> None:
        from jarvis.wakeword import strip_wake_prefix

        self.assertEqual(strip_wake_prefix("jarvis, abra o D:", "jarvis"), "abra o D:")
        self.assertEqual(
            strip_wake_prefix("Jarvis abra o youtube", "jarvis"), "abra o youtube"
        )
        self.assertEqual(strip_wake_prefix("ok jarvis", "jarvis"), "")
        self.assertIsNone(strip_wake_prefix("abra o D:", "jarvis"))
        self.assertIsNone(strip_wake_prefix("abre a janela, jarvis", "jarvis"))


class CommandAfterWakeWordTests(unittest.TestCase):
    def test_extracts_trailing_command(self) -> None:
        from jarvis.wakeword import command_after_wake_word

        self.assertEqual(
            command_after_wake_word("Jarvis, que horas sao?", "jarvis"),
            "que horas sao?",
        )
        self.assertEqual(
            command_after_wake_word("ei jarvis pesquise lofi no youtube", "jarvis"),
            "pesquise lofi no youtube",
        )
        self.assertEqual(command_after_wake_word("Jarvis", "jarvis"), "")
        self.assertEqual(command_after_wake_word("jarvis.", "jarvis"), "")
        self.assertEqual(
            command_after_wake_word("ok computador liga a luz", "computador"),
            "liga a luz",
        )


class WakeWordListenerLoopTests(unittest.TestCase):
    def _config(self):
        from jarvis.config import default_voice_config

        return default_voice_config()

    def test_fires_on_match_and_stays_alive_for_next_time(self) -> None:
        voice = _FakeVoice("Jarvis, que horas sao")
        wakes: list[str] = []
        listener = WakeWordListener(self._config(), voice, on_wake=wakes.append)

        fake_sd = type("sd", (), {"InputStream": _FakeStream})

        with patch.dict("sys.modules", {"sounddevice": fake_sd}):
            listener.start()
            deadline = time.time() + 4
            while not wakes and time.time() < deadline:
                time.sleep(0.02)
            fired_once = bool(wakes)
            thread_alive = listener._thread is not None and listener._thread.is_alive()
            listener.resume()  # simula o GUI liberando a escuta
            deadline = time.time() + 4
            while len(wakes) < 2 and time.time() < deadline:
                time.sleep(0.02)
            listener.stop()

        self.assertTrue(fired_once, "deveria disparar on_wake ao ouvir 'Jarvis'")
        self.assertTrue(thread_alive, "a thread deve continuar viva apos disparar")
        self.assertGreaterEqual(len(wakes), 2, "deve poder disparar de novo apos resume()")
        self.assertEqual(wakes[0], "que horas sao", "passa o comando dito junto")

    def test_stream_stays_open_across_utterances(self) -> None:
        """O microfone nao pode fechar entre uma palavra e outra."""
        voice = _FakeVoice("nada aqui")  # nunca casa -> segue ouvindo
        opens: list[int] = []

        class _Counting(_FakeStream):
            def __enter__(self):
                opens.append(1)
                return super().__enter__()

        with patch.dict("sys.modules", {"sounddevice": type("sd", (), {"InputStream": _Counting})}):
            listener = WakeWordListener(self._config(), voice, on_wake=lambda _c: None)
            listener.start()
            time.sleep(1.0)
            listener.stop()

        self.assertGreaterEqual(voice.calls, 2, "deveria transcrever varias falas")
        self.assertEqual(opens, [1], "o InputStream abre UMA vez e fica aberto")


if __name__ == "__main__":
    unittest.main()
