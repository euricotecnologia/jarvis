import io
import json
import tempfile
import unittest
import urllib.error
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from jarvis.config import load_config
from jarvis.voice import (
    VoiceService,
    VoiceError,
    extract_gemini_audio,
    iter_gemini_audio_chunks,
    prepare_speech_text,
)


class VoiceTests(unittest.TestCase):
    def test_voice_defaults_are_local_and_pt_br(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config = load_config(Path(directory) / "missing.toml")
        self.assertTrue(config.voice.enabled)
        self.assertEqual(config.voice.language, "pt")
        self.assertEqual(config.voice.device, "cpu")
        self.assertEqual(config.voice.compute_type, "int8")

    def test_speech_text_removes_markdown_and_limits_length(self) -> None:
        result = prepare_speech_text("**Veja** [a pagina](https://example.com) `agora`", 30)
        self.assertEqual(result, "Veja a pagina agora")

    def test_speech_text_drops_urls_and_dangling_link_phrases(self) -> None:
        spoken = prepare_speech_text(
            'Pronto, abri a pesquisa da Sofia no YouTube. Aqui esta o link: '
            "[https://www.youtube.com/results?search_query=Sofia]"
            "(https://www.youtube.com/results?search_query=Sofia)",
            800,
        )
        self.assertEqual(spoken, "Pronto, abri a pesquisa da Sofia no YouTube.")
        self.assertNotIn("http", spoken)
        self.assertNotIn("link", spoken)

    def test_speech_text_keeps_normal_sentences_intact(self) -> None:
        self.assertEqual(prepare_speech_text("Bom dia.", 800), "Bom dia.")
        self.assertEqual(
            prepare_speech_text("Primeira frase. Segunda frase.", 800),
            "Primeira frase. Segunda frase.",
        )

    def test_gemini_tts_uses_interactions_api_model_and_voice(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config = load_config(Path(directory) / "missing.toml")
        voice = replace(
            config.voice,
            tts_engine="gemini",
            tts_model="gemini-3.1-flash-tts-preview",
            tts_voice="Kore",
        )
        service = VoiceService(voice)

        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        with (
            patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}),
            patch("urllib.request.urlopen", return_value=Response()) as urlopen,
            patch.object(service, "_play_gemini_stream") as play,
        ):
            service._speak_gemini("Ola")

        request = urlopen.call_args.args[0]
        self.assertEqual(
            request.full_url,
            "https://generativelanguage.googleapis.com/v1beta/interactions",
        )
        self.assertEqual(request.headers.get("Api-revision"), "2026-05-20")
        self.assertIn(b"gemini-3.1-flash-tts-preview", request.data)
        self.assertIn(b'"voice": "Kore"', request.data)
        self.assertIn(b'"stream": true', request.data)
        play.assert_called_once()

    def test_gemini_25_model_uses_non_streaming_and_output_audio(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config = load_config(Path(directory) / "missing.toml")
        voice = replace(
            config.voice,
            tts_engine="gemini",
            tts_model="gemini-2.5-flash-preview-tts",
            tts_voice="Kore",
        )
        service = VoiceService(voice)
        body = json.dumps(
            {"output_audio": {"data": "AAA=", "sample_rate": 24000}}
        ).encode("utf-8")

        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self):
                return body

        with (
            patch.dict("os.environ", {"GEMINI_API_KEY": "test-key"}),
            patch("urllib.request.urlopen", return_value=Response()) as urlopen,
            patch.object(service, "_play_pcm") as play,
        ):
            service._speak_gemini("Ola")

        self.assertNotIn(b'"stream"', urlopen.call_args.args[0].data)
        play.assert_called_once_with(b"\x00\x00", sample_rate=24000)

    def test_gemini_retries_before_falling_back_on_503(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config = load_config(Path(directory) / "missing.toml")
        service = VoiceService(
            replace(
                config.voice,
                tts_engine="gemini",
                tts_model="gemini-2.5-flash-preview-tts",
            )
        )
        attempts: list[int] = []
        good = json.dumps({"output_audio": {"data": "AAA=", "sample_rate": 24000}})

        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self):
                return good.encode("utf-8")

        def fake_urlopen(request, timeout=0):
            attempts.append(1)
            if len(attempts) == 1:
                raise urllib.error.HTTPError(
                    request.full_url, 503, "overloaded", {},
                    io.BytesIO(b'{"error":{"status":"UNAVAILABLE"}}'),
                )
            return Response()

        with (
            patch.dict("os.environ", {"GEMINI_API_KEY": "k"}),
            patch("urllib.request.urlopen", side_effect=fake_urlopen),
            patch("time.sleep"),
            patch.object(service, "_play_pcm") as play,
        ):
            service._speak_gemini("Ola")

        self.assertEqual(len(attempts), 2)
        play.assert_called_once()

    def test_gemini_audio_reads_output_audio_and_steps(self) -> None:
        pcm, rate = extract_gemini_audio(
            {"output_audio": {"data": "AAA=", "sample_rate": 22050}}
        )
        self.assertEqual((pcm, rate), (b"\x00\x00", 22050))

        pcm, rate = extract_gemini_audio(
            {"steps": [{"content": [{"type": "audio", "data": "AAA="}]}]}
        )
        self.assertEqual((pcm, rate), (b"\x00\x00", 24000))

    def test_gemini_sse_audio_chunks_are_decoded(self) -> None:
        # Formato real da Interactions API (verificado contra a API 2026-08):
        lines = [
            b'data: {"event_type":"interaction.created","interaction":{"status":"in_progress"}}\n',
            b"\n",
            b'data: {"index":0,"step":{"type":"model_output"},"event_type":"step.start"}\n',
            b"\n",
            b'data: {"index":0,"delta":{"mime_type":"audio/l16","data":"AAA="},'
            b'"event_type":"step.delta"}\n',
            b"\n",
            b'data: {"index":0,"delta":{"mime_type":"audio/l16","data":"//8="},'
            b'"event_type":"step.delta"}\n',
            b"\n",
            b'data: {"event_type":"interaction.completed","interaction":{"status":"completed"}}\n',
            b"\n",
            b"data: [DONE]\n",
            b"\n",
        ]
        self.assertEqual(
            list(iter_gemini_audio_chunks(lines)),
            [(b"\x00\x00", 24000, 1), (b"\xff\xff", 24000, 1)],
        )

    def test_gemini_quota_error_is_reported(self) -> None:
        lines = [
            b'data: {"event_type":"error","error":'
            b'{"code":"resource_exhausted","message":"limit"}}\n',
            b"\n",
        ]
        with self.assertRaisesRegex(VoiceError, "cota do Gemini TTS"):
            list(iter_gemini_audio_chunks(lines))

    def test_gemini_failed_interaction_status_raises(self) -> None:
        lines = [
            b'data: {"event_type":"interaction.completed",'
            b'"interaction":{"status":"failed"}}\n',
            b"\n",
        ]
        with self.assertRaises(VoiceError):
            list(iter_gemini_audio_chunks(lines))

    def test_gemini_speak_sends_full_text_in_one_call(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config = load_config(Path(directory) / "missing.toml")
        service = VoiceService(replace(config.voice, tts_engine="gemini"))
        calls: list[str] = []
        with (
            patch.object(service, "assert_available"),
            patch.object(service, "_speak_gemini", side_effect=calls.append),
        ):
            service.speak("Primeira frase. Segunda frase. Terceira frase.")
        self.assertEqual(calls, ["Primeira frase. Segunda frase. Terceira frase."])

    def test_gemini_failure_falls_back_to_windows_voice(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config = load_config(Path(directory) / "missing.toml")
        service = VoiceService(replace(config.voice, tts_engine="gemini"))
        with (
            patch.object(service, "_speak_gemini", side_effect=VoiceError("cota")),
            patch.object(service, "_speak_windows") as local_voice,
        ):
            warning = service.speak("Ola")
        local_voice.assert_called_once_with("Ola")
        self.assertIn("usei a voz local", warning)

    def test_kokoro_engine_routes_to_speak_kokoro(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config = load_config(Path(directory) / "missing.toml")
        service = VoiceService(
            replace(config.voice, tts_engine="kokoro", tts_voice="pf_dora")
        )
        with (
            patch.object(service, "assert_available"),
            patch.object(service, "_speak_kokoro") as kokoro,
        ):
            self.assertIsNone(service.speak("Bom dia."))
        kokoro.assert_called_once_with("Bom dia.")

    def test_openai_transcription_builds_multipart_request(self) -> None:
        import numpy as np

        with tempfile.TemporaryDirectory() as directory:
            config = load_config(Path(directory) / "missing.toml")
        service = VoiceService(
            replace(
                config.voice,
                transcription_engine="openai",
                transcription_cloud_model="gpt-4o-transcribe",
            )
        )

        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def read(self):
                return b"Bom dia, Jarvis."

        with (
            patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}),
            patch("urllib.request.urlopen", return_value=Response()) as urlopen,
        ):
            text = service._transcribe_openai(
                np.zeros(16000, dtype="float32")
            )

        self.assertEqual(text, "Bom dia, Jarvis.")
        request = urlopen.call_args.args[0]
        self.assertIn("audio/transcriptions", request.full_url)
        self.assertTrue(request.headers["Content-type"].startswith("multipart/form-data"))
        self.assertIn(b"gpt-4o-transcribe", request.data)
        self.assertIn(b"fala.wav", request.data)

    def test_transcribe_falls_back_to_local_when_openai_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config = load_config(Path(directory) / "missing.toml")
        service = VoiceService(
            replace(config.voice, transcription_engine="openai")
        )
        with (
            patch.object(service, "assert_available"),
            patch.object(
                service, "_transcribe_openai", side_effect=VoiceError("sem chave")
            ),
            patch.object(
                service, "_transcribe_local", return_value="texto local"
            ) as local,
        ):
            self.assertEqual(service.transcribe(object()), "texto local")
        local.assert_called_once()

    def test_kokoro_failure_falls_back_to_windows(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config = load_config(Path(directory) / "missing.toml")
        service = VoiceService(replace(config.voice, tts_engine="kokoro"))
        with (
            patch.object(service, "assert_available"),
            patch.object(
                service, "_speak_kokoro", side_effect=VoiceError("modelo ausente")
            ),
            patch.object(service, "_speak_windows") as local_voice,
        ):
            warning = service.speak("Ola")
        local_voice.assert_called_once_with("Ola")
        self.assertIn("Kokoro indisponível", warning)


if __name__ == "__main__":
    unittest.main()
