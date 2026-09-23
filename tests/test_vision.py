import io
import json
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from jarvis.config import ProviderConfig
from jarvis.vision import (
    Frame,
    VisionError,
    describe_scene,
    looks_like_vision_request,
)


class IntentTests(unittest.TestCase):
    def test_positive(self) -> None:
        for phrase in (
            "jarvis, o que voce esta vendo?",
            "consegue ver o que estou segurando?",
            "olhe pela webcam e me diga a cor",
            "usa a camera pra ver isso",
            "quantos dedos estou mostrando",
        ):
            self.assertTrue(looks_like_vision_request(phrase), phrase)

    def test_negative(self) -> None:
        for phrase in ("que horas sao", "abra o youtube", "resuma este pdf"):
            self.assertFalse(looks_like_vision_request(phrase), phrase)


def _fake_urlopen(payload: dict):
    captured: dict = {}

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return json.dumps(payload).encode("utf-8")

    def opener(request, timeout=0):
        captured["url"] = request.full_url
        captured["body"] = json.loads(request.data.decode("utf-8"))
        captured["headers"] = dict(request.headers)
        return Response()

    return opener, captured


class DescribeSceneTests(unittest.TestCase):
    FRAME = Frame(jpeg=b"\xff\xd8fakejpeg", width=640, height=480)

    def test_openai_compatible(self) -> None:
        provider = ProviderConfig(
            name="openai", kind="openai", enabled=True, model="gpt-4o",
            base_url="https://api.openai.com/v1", api_key_env="OPENAI_API_KEY",
        )
        payload = {"choices": [{"message": {"content": "Vejo uma xicara azul."}}]}
        opener, captured = _fake_urlopen(payload)
        with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-x"}), \
             patch("urllib.request.urlopen", opener):
            answer = describe_scene("o que ve?", self.FRAME, provider)
        self.assertEqual(answer, "Vejo uma xicara azul.")
        self.assertTrue(captured["url"].endswith("/chat/completions"))
        content = captured["body"]["messages"][0]["content"]
        self.assertEqual(content[0]["type"], "text")
        self.assertTrue(content[1]["image_url"]["url"].startswith("data:image/jpeg;base64,"))
        self.assertEqual(captured["headers"].get("Authorization"), "Bearer sk-x")

    def test_anthropic(self) -> None:
        provider = ProviderConfig(
            name="claude", kind="anthropic", enabled=True, model="claude-sonnet-5",
            base_url="https://api.anthropic.com/v1", api_key_env="ANTHROPIC_API_KEY",
        )
        payload = {"content": [{"type": "text", "text": "Uma sala com estante."}]}
        opener, captured = _fake_urlopen(payload)
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-ant"}), \
             patch("urllib.request.urlopen", opener):
            answer = describe_scene("", self.FRAME, provider)
        self.assertEqual(answer, "Uma sala com estante.")
        self.assertTrue(captured["url"].endswith("/messages"))
        block = captured["body"]["messages"][0]["content"][1]
        self.assertEqual(block["type"], "image")
        self.assertEqual(block["source"]["media_type"], "image/jpeg")
        self.assertEqual(captured["headers"].get("X-api-key"), "sk-ant")

    def test_http_error_is_vision_error(self) -> None:
        provider = ProviderConfig(
            name="lmstudio", kind="lmstudio", enabled=True, model="llava",
            base_url="http://localhost:1234/v1",
        )
        import urllib.error

        def opener(request, timeout=0):
            raise urllib.error.HTTPError(
                request.full_url, 400, "bad", {}, io.BytesIO(b'{"error":"no vision"}')
            )

        with patch("urllib.request.urlopen", opener):
            with self.assertRaises(VisionError):
                describe_scene("ve?", self.FRAME, provider)

    def test_bad_response_shape(self) -> None:
        provider = ProviderConfig(
            name="ollama", kind="ollama", enabled=True, model="qwen3",
            base_url="http://localhost:11434/v1",
        )
        opener, _ = _fake_urlopen({"weird": True})
        with patch("urllib.request.urlopen", opener):
            with self.assertRaises(VisionError):
                describe_scene("ve?", self.FRAME, provider)


class _Bright:
    """Frame falso com brilho controlavel e shape."""

    def __init__(self, value: float = 120.0) -> None:
        self.shape = (480, 640, 3)
        self._value = value

    def mean(self) -> float:
        return self._value


class CaptureFrameTests(unittest.TestCase):
    def test_capture_encodes_jpeg(self) -> None:
        class FakeCapture:
            def isOpened(self):
                return True

            def read(self):
                return True, _Bright(120.0)

            def release(self):
                pass

        fake_cv2 = SimpleNamespace(
            CAP_DSHOW=700,
            CAP_MSMF=1400,
            IMWRITE_JPEG_QUALITY=1,
            VideoCapture=lambda *a: FakeCapture(),
            imencode=lambda ext, frame, params: (True, SimpleNamespace(tobytes=lambda: b"JPEGDATA")),
        )
        with patch.dict(sys.modules, {"cv2": fake_cv2}), \
             patch("jarvis.vision.time.sleep"):
            from jarvis.vision import capture_frame

            frame = capture_frame(0, warmup_frames=4)
        self.assertEqual(frame.jpeg, b"JPEGDATA")
        self.assertEqual((frame.width, frame.height), (640, 480))

    def test_black_frame_raises(self) -> None:
        class DarkCapture:
            def isOpened(self):
                return True

            def read(self):
                return True, _Bright(0.5)

            def release(self):
                pass

        fake_cv2 = SimpleNamespace(
            CAP_DSHOW=700, CAP_MSMF=1400, IMWRITE_JPEG_QUALITY=1,
            VideoCapture=lambda *a: DarkCapture(), imencode=lambda *a: (True, None),
        )
        with patch.dict(sys.modules, {"cv2": fake_cv2}), \
             patch("jarvis.vision.time.sleep"):
            from jarvis.vision import capture_frame

            with self.assertRaisesRegex(VisionError, "preta"):
                capture_frame(0, warmup_frames=4)

    def test_camera_not_opening_raises(self) -> None:
        class Closed:
            def isOpened(self):
                return False

            def release(self):
                pass

        fake_cv2 = SimpleNamespace(
            CAP_DSHOW=700, CAP_MSMF=1400, IMWRITE_JPEG_QUALITY=1,
            VideoCapture=lambda *a: Closed(), imencode=lambda *a: (False, None),
        )
        with patch.dict(sys.modules, {"cv2": fake_cv2}):
            from jarvis.vision import capture_frame

            with self.assertRaises(VisionError):
                capture_frame(3, warmup_frames=1)


if __name__ == "__main__":
    unittest.main()
