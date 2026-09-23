"""Captura da tela (screenshot) para mostrar no chat."""

from __future__ import annotations

import importlib.util
import io

from jarvis.errors import JarvisError


class ScreenshotError(JarvisError):
    pass


def available() -> bool:
    return importlib.util.find_spec("PIL") is not None


def capture_screen(*, jpeg_quality: int = 80, max_width: int = 1920) -> bytes:
    """Tira um print de todos os monitores e devolve JPEG. Lanca ScreenshotError."""
    try:
        from PIL import ImageGrab
    except Exception as exc:  # noqa: BLE001
        raise ScreenshotError(
            "Para tirar prints instale o Pillow: "
            '.\\.venv\\Scripts\\python.exe -m pip install -e ".[tools]"'
        ) from exc

    try:
        image = ImageGrab.grab(all_screens=True)
    except Exception as exc:  # noqa: BLE001
        raise ScreenshotError(f"Não consegui capturar a tela: {exc}") from exc

    if image.mode != "RGB":
        image = image.convert("RGB")
    if image.width > max_width:
        ratio = max_width / image.width
        image = image.resize((max_width, max(1, int(image.height * ratio))))

    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=int(jpeg_quality), optimize=True)
    return buffer.getvalue()
