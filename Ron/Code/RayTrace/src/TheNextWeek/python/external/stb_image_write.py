# Python stand-in for stb_image_write.h (Sean Barrett).
# The C header writes PNG/BMP/TGA/HDR; this module provides the same write API via Pillow.

from __future__ import annotations


def _mode_for_comp(comp: int) -> str:
    if comp == 1:
        return "L"
    if comp == 2:
        return "LA"
    if comp == 3:
        return "RGB"
    if comp == 4:
        return "RGBA"
    raise ValueError(f"unsupported component count: {comp}")


def _to_image(w, h, comp, data, stride_in_bytes=0):
    try:
        from PIL import Image
    except ImportError as exc:
        raise ImportError(
            "Pillow is required to write images (pip install pillow)"
        ) from exc

    mode = _mode_for_comp(comp)
    if isinstance(data, (bytes, bytearray, memoryview)):
        raw = bytes(data)
    else:
        raw = bytes(int(max(0, min(255, round(v)))) for v in data)

    if stride_in_bytes and stride_in_bytes != w * comp:
        rows = []
        for y in range(h):
            start = y * stride_in_bytes
            rows.append(raw[start : start + w * comp])
        raw = b"".join(rows)

    return Image.frombytes(mode, (w, h), raw)


def stbi_write_png(filename, w, h, comp, data, stride_in_bytes=0):
    try:
        img = _to_image(w, h, comp, data, stride_in_bytes)
        img.save(filename, format="PNG")
        return 1
    except Exception:
        return 0


def stbi_write_bmp(filename, w, h, comp, data):
    try:
        img = _to_image(w, h, comp, data)
        img.save(filename, format="BMP")
        return 1
    except Exception:
        return 0


def stbi_write_tga(filename, w, h, comp, data):
    try:
        img = _to_image(w, h, comp, data)
        img.save(filename, format="TGA")
        return 1
    except Exception:
        return 0


def stbi_write_jpg(filename, w, h, comp, data, quality=90):
    try:
        img = _to_image(w, h, comp, data)
        if img.mode in ("RGBA", "LA"):
            img = img.convert("RGB")
        img.save(filename, format="JPEG", quality=quality)
        return 1
    except Exception:
        return 0
