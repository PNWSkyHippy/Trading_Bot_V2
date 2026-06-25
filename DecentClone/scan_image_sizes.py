"""Print image dimensions for texture folders.

Usage:
    python scan_image_sizes.py
    python scan_image_sizes.py Textures/WallTextures
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image


IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def is_power_of_two(value: int) -> bool:
    return value > 0 and value & (value - 1) == 0


def status_for(width: int, height: int) -> str:
    notes: list[str] = []
    if width != height:
        notes.append("not-square")
    if not is_power_of_two(width) or not is_power_of_two(height):
        notes.append("not-power-of-two")
    if width == height == 1024:
        notes.append("ideal-1024")
    elif width == height == 2048:
        notes.append("large-2048")
    return ", ".join(notes) if notes else "ok"


def scan_images(folder: Path) -> int:
    if not folder.exists():
        print(f"Folder not found: {folder}")
        return 1
    if not folder.is_dir():
        print(f"Not a folder: {folder}")
        return 1

    files = sorted(
        path for path in folder.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_EXTS
    )
    if not files:
        print(f"No image files found in: {folder}")
        return 0

    name_width = max(len(path.name) for path in files)
    for path in files:
        try:
            with Image.open(path) as image:
                width, height = image.size
        except Exception as exc:
            print(f"{path.name:<{name_width}}  ERROR {exc}")
            continue

        print(
            f"{path.name:<{name_width}}  "
            f"Width {width:<5} Height {height:<5}  {status_for(width, height)}"
        )

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="List image dimensions and texture-size warnings."
    )
    parser.add_argument(
        "folder",
        nargs="?",
        default="Textures/WallTextures",
        help="folder to scan, default: Textures/WallTextures",
    )
    args = parser.parse_args()
    return scan_images(Path(args.folder))


if __name__ == "__main__":
    raise SystemExit(main())
