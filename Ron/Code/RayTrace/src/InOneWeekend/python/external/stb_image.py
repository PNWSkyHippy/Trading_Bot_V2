# Python stand-in for stb_image.h (Sean Barrett).
# The C header is a large decoder; this module provides the same load API via Pillow.

from __future__ import annotations

import os


STBI_FREE = lambda _data: None


def _open_rgb(filename: str):
    try:
        from PIL import Image
    except ImportError as exc:
        raise ImportError(
            "Pillow is required to load textures (pip install pillow)"
        ) from exc
    img = Image.open(filename)
    return img.convert("RGB")


def stbi_load(filename, req_comp=3):
    """Load an image as 8-bit RGB bytes.

    Returns (bytearray, width, height, components) or None on failure.
    Mirrors stbi_load() from stb_image.h.
    """
    try:
        img = _open_rgb(filename)
    except Exception:
        return None
    width, height = img.size
    data = bytearray(img.tobytes())
    return data, width, height, 3


def stbi_loadf(filename, req_comp=3):
    """Load an image as linear-ish float RGB in [0, 1].

    Returns (list[float], width, height, components) or None on failure.
    Mirrors stbi_loadf() from stb_image.h.
    """
    loaded = stbi_load(filename, req_comp)
    if loaded is None:
        return None
    data, width, height, n = loaded
    floats = [b / 255.0 for b in data]
    return floats, width, height, n
