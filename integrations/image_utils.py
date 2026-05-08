from __future__ import annotations

import base64
import io
from pathlib import Path

from django.conf import settings
from PIL import Image


def to_base64_jpeg(image_path: Path) -> dict[str, str]:
    img = Image.open(image_path)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    img.thumbnail(settings.IMAGE_MAX_SIZE)

    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=settings.JPEG_QUALITY, optimize=True)
    return {
        "title": f"{image_path.stem}.jpg",
        "image_base64": base64.b64encode(buffer.getvalue()).decode("utf-8"),
    }


def is_allowed_image(filename: str) -> bool:
    return Path(filename).suffix.lower() in settings.IMAGE_ALLOWED_EXTENSIONS

