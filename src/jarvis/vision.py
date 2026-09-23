"""A IA enxergar pela webcam.

Captura um frame com OpenCV, codifica em JPEG e manda para um modelo com visão
(OpenAI/Claude/Gemini ou um modelo multimodal local). Nada e gravado em disco;
a imagem so vai para o provedor de IA que você escolheu.
"""

from __future__ import annotations

import base64
import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass

from jarvis.config import ProviderConfig, VisionConfig
from jarvis.errors import JarvisError

DEFAULT_PROMPT = (
    "você está enxergando pela webcam do usuário. Descreva de forma natural e "
    "util o que aparece na imagem, em português do Brasil. Se o usuário fez uma "
    "pergunta especifica, responda a ela olhando a imagem."
)

_VISION_VERBS = (
    "enxerg", "consegue ver", "esta vendo", "esta enxergando", "ta vendo",
    "olha pra", "olhe pra", "olha pela", "olhe pela", "pela webcam",
    "pela camera", "pela câmera", "na webcam", "na camera", "na câmera",
    "a camera pra", "a câmera pra", "camera pra ver", "câmera pra ver",
    "usar a webcam", "usa a webcam", "usar a camera", "usa a camera",
    "ligar a webcam", "ligue a webcam", "abrir a webcam",
    "o que voce ve", "o que voce esta vendo", "o que ha na minha frente",
    "o que tem na minha frente", "descreve o que", "descreva o que",
    "que cor e", "que cor é", "quantos dedos", "leia isto", "leia isso",
    "sua visao", "sua visão", "olhe isso", "olha isso", "veja isso",
    "veja isto", "consegue enxergar",
)


class VisionError(JarvisError):
    pass


@dataclass(frozen=True, slots=True)
class Frame:
    jpeg: bytes
    width: int
    height: int


def opencv_available() -> bool:
    try:
        import cv2  # noqa: F401
    except Exception:  # noqa: BLE001
        return False
    return True


def looks_like_vision_request(text: str) -> bool:
    lowered = (text or "").lower()
    return any(marker in lowered for marker in _VISION_VERBS)


def _mean_brightness(frame) -> float:
    try:
        return float(frame.mean())
    except Exception:  # noqa: BLE001
        return 0.0


def _open_capture(cv2, camera_index: int):
    """Tenta DSHOW e depois MSMF/padrão. Devolve um VideoCapture aberto ou None."""
    backends = []
    for name in ("CAP_DSHOW", "CAP_MSMF"):
        value = getattr(cv2, name, None)
        if value is not None:
            backends.append(value)
    backends.append(0)  # padrão
    for backend in backends:
        capture = cv2.VideoCapture(camera_index, backend)
        if capture.isOpened():
            return capture
        capture.release()
    return None


def capture_frame(camera_index: int = 0, *, jpeg_quality: int = 85,
                  warmup_frames: int = 10) -> Frame:
    """Abre a webcam, pega um frame não-preto e fecha. Lanca VisionError em falha."""
    try:
        import cv2
    except Exception as exc:  # noqa: BLE001
        raise VisionError(
            "Recurso de visão indisponível: instale o pacote com "
            '.\\.venv\\Scripts\\python.exe -m pip install -e ".[vision]"'
        ) from exc

    capture = _open_capture(cv2, camera_index)
    if capture is None:
        raise VisionError(
            f"Não consegui abrir a webcam (indice {camera_index}). "
            "Feche outros apps que usam a câmera (Meet, Zoom, Teams...) e "
            "verifique a tampa/chave de privacidade da webcam."
        )
    try:
        frame = None
        best_brightness = -1.0
        # Sensor precisa de tempo para expor: descarta os primeiros frames e
        # fica com o mais claro dentro do orcamento.
        for index in range(max(3, warmup_frames)):
            ok, candidate = capture.read()
            if not ok or candidate is None:
                time.sleep(0.05)
                continue
            brightness = _mean_brightness(candidate)
            if brightness > best_brightness:
                best_brightness = brightness
                frame = candidate
            if brightness >= 12 and index >= 3:
                break  # ja tem imagem util
            time.sleep(0.06)

        if frame is None:
            raise VisionError("A webcam abriu mas não entregou nenhum frame.")
        if best_brightness < 4.0:
            raise VisionError(
                "A webcam devolveu uma imagem preta. A tampa de privacidade pode "
                "estar fechada, ou outro programa esta usando a câmera."
            )
        ok, buffer = cv2.imencode(
            ".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), int(jpeg_quality)]
        )
        if not ok:
            raise VisionError("Não consegui codificar a imagem da webcam.")
        height, width = frame.shape[:2]
        return Frame(jpeg=buffer.tobytes(), width=int(width), height=int(height))
    finally:
        capture.release()


def _http_json(url: str, headers: dict[str, str], payload: dict, timeout: float) -> dict:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:300]
        hint = ""
        if exc.code in (400, 415, 422, 500):
            hint = (
                " (o modelo atual talvez não enxergue imagens - use gpt-4o, "
                "gpt-4.1, claude-* ou gemini-*)"
            )
        raise VisionError(
            f"O provedor recusou a imagem ({exc.code}){hint}: {detail}"
        ) from exc
    except (urllib.error.URLError, OSError, TimeoutError) as exc:
        raise VisionError(f"Falha de rede ao enviar a imagem: {exc}") from exc


def describe_scene(
    question: str,
    frame: Frame,
    provider: ProviderConfig,
    *,
    timeout_seconds: float = 45.0,
) -> str:
    """Manda o frame + a pergunta para o provedor e devolve a resposta em texto."""
    prompt = (question or "").strip() or DEFAULT_PROMPT
    b64 = base64.b64encode(frame.jpeg).decode("ascii")
    api_key = provider.api_key()

    if provider.kind == "anthropic":
        url = f"{provider.base_url}/messages"
        headers = {"anthropic-version": "2023-06-01"}
        if api_key:
            headers["x-api-key"] = api_key
        payload = {
            "model": provider.model,
            "max_tokens": 600,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": b64,
                            },
                        },
                    ],
                }
            ],
        }
        data = _http_json(url, headers, payload, timeout_seconds)
        blocks = data.get("content") or []
        for block in blocks:
            if isinstance(block, dict) and block.get("type") == "text":
                return block.get("text", "").strip()
        raise VisionError("O modelo respondeu sem texto.")

    # OpenAI / Gemini(openai) / LM Studio / Ollama - formato chat/completions
    url = f"{provider.base_url}/chat/completions"
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    payload = {
        "model": provider.model,
        "max_tokens": 600,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
                    },
                ],
            }
        ],
    }
    data = _http_json(url, headers, payload, timeout_seconds)
    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise VisionError(
            "O modelo atual não respondeu com texto. Ele enxerga imagens? "
            "Use um modelo com visão (gpt-4o, claude, gemini, llava...)."
        ) from exc


def describe_with_config(
    question: str,
    provider: ProviderConfig,
    vision: VisionConfig,
) -> tuple[str, Frame]:
    frame = capture_frame(vision.camera_index, jpeg_quality=vision.jpeg_quality)
    answer = describe_scene(
        question, frame, provider, timeout_seconds=vision.timeout_seconds
    )
    return answer, frame
