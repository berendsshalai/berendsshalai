#!/usr/bin/env python3
"""Validate the generated cinematic ASCII statistics room assets."""

from __future__ import annotations

import re
from pathlib import Path

from PIL import Image, ImageChops, ImageStat

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
README = ROOT / "README.md"
GIF_NAMES = ("ascii-stats-gallery.gif", "ascii-stats-gallery-dark.gif")
PNG_NAMES = ("ascii-stats-gallery-static.png", "ascii-stats-gallery-dark-static.png")
EXPECTED_SIZE = (1200, 900)
MAX_GIF_BYTES = 12 * 1024 * 1024
MAX_PNG_BYTES = 2 * 1024 * 1024


def fail(message: str) -> None:
    raise SystemExit(f"FAIL: {message}")


def edge_matches(image: Image.Image, expected: tuple[int, int, int]) -> bool:
    rgb = image.convert("RGB")
    points = ((0, 0), (rgb.width - 1, 0), (0, rgb.height - 1), (rgb.width - 1, rgb.height - 1))
    return all(rgb.getpixel(point) == expected for point in points)


def validate_gif(name: str, edge: tuple[int, int, int]) -> dict[str, float | int | str]:
    path = ASSETS / name
    if not path.exists():
        fail(f"missing {name}")
    if path.stat().st_size > MAX_GIF_BYTES:
        fail(f"{name} exceeds 12 MiB")
    with Image.open(path) as image:
        if image.size != EXPECTED_SIZE:
            fail(f"{name} dimensions are {image.size}")
        if image.info.get("loop") != 0:
            fail(f"{name} does not loop infinitely")
        frames = getattr(image, "n_frames", 1)
        if frames < 300:
            fail(f"{name} has only {frames} frames")
        duration = 0
        first = None
        last = None
        palette = None
        for index in range(frames):
            image.seek(index)
            duration += int(image.info.get("duration", 0))
            frame = image.convert("RGB")
            if not frame.getbbox():
                fail(f"{name} contains blank frame {index}")
            if index == 0:
                first = frame.copy()
                palette = image.getpalette()
                if not edge_matches(frame, edge):
                    fail(f"{name} edge color does not match its GitHub theme")
            if image.getpalette() not in (None, palette):
                fail(f"{name} palette changes at frame {index}")
            last = frame.copy()
        if not 21_000 <= duration <= 25_000:
            fail(f"{name} duration is {duration / 1000:.2f}s")
        assert first is not None and last is not None
        seam_rms = sum(ImageStat.Stat(ImageChops.difference(first, last)).rms) / 3
        if seam_rms > 18:
            fail(f"{name} loop seam RMS is {seam_rms:.2f}")
    return {"name": name, "bytes": path.stat().st_size, "frames": frames, "duration_seconds": duration / 1000, "seam_rms": round(seam_rms, 2)}


def validate_png(name: str, edge: tuple[int, int, int]) -> dict[str, int | str]:
    path = ASSETS / name
    if not path.exists():
        fail(f"missing {name}")
    if path.stat().st_size > MAX_PNG_BYTES:
        fail(f"{name} exceeds 2 MiB")
    with Image.open(path) as image:
        image.load()
        if image.size != EXPECTED_SIZE:
            fail(f"{name} dimensions are {image.size}")
        if not edge_matches(image, edge):
            fail(f"{name} edge color does not match its GitHub theme")
    return {"name": name, "bytes": path.stat().st_size}


def main() -> None:
    readme = README.read_text(encoding="utf-8")
    for name in (*GIF_NAMES, *PNG_NAMES):
        if f"./assets/{name}?version=" not in readme:
            fail(f"README does not reference {name}")
    block = re.search(r"<!-- LIVE_STATS_IMAGE_START -->(.*?)<!-- LIVE_STATS_IMAGE_END -->", readme, re.S)
    if not block or "<picture>" not in block.group(1):
        fail("theme-aware live statistics picture block is missing")
    tracked_frames = list(ROOT.glob("**/frame-*.png")) + list(ROOT.glob("**/frames/*.png"))
    if tracked_frames:
        fail("generated frame files exist in the repository tree")
    results = [
        validate_gif(GIF_NAMES[0], (255, 255, 255)),
        validate_gif(GIF_NAMES[1], (13, 17, 23)),
        validate_png(PNG_NAMES[0], (255, 255, 255)),
        validate_png(PNG_NAMES[1], (13, 17, 23)),
    ]
    print("PASS: cinematic ASCII statistics room assets validated.")
    for result in results:
        print(result)


if __name__ == "__main__":
    main()
