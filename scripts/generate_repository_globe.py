#!/usr/bin/env python3
"""Generate the transparent rotating repository globe used by the profile README."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
FONTS = ASSETS / "fonts"
GIF_PATH = ASSETS / "repository-globe.gif"
STATIC_PATH = ASSETS / "repository-globe-static.png"

WIDTH = HEIGHT = 560
FRAME_COUNT = 96
FRAME_DURATION_MS = 58
TRANSPARENT_KEY = (255, 0, 255)

GREEN = (63, 185, 80)
BRIGHT = (126, 231, 135)
MINT = (86, 211, 100)
DEEP = (35, 134, 54)
QUIET = (46, 160, 67)

REPOSITORIES = [
    ("ATTENDANCE", -0.42, -1.02),
    ("SYSTEMS LAB", 0.54, -0.28),
    ("ONBOARDING", 0.18, 1.18),
    ("PORTFOLIO", -0.62, 0.46),
]


def _font(role: str, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = {
        "display": [FONTS / "SpaceGrotesk-Variable.ttf", Path("C:/Windows/Fonts/segoeuib.ttf")],
        "body": [FONTS / "Inter-Variable.ttf", Path("C:/Windows/Fonts/segoeui.ttf")],
        "mono": [FONTS / "IBMPlexMono-Medium.ttf", Path("C:/Windows/Fonts/consola.ttf")],
    }[role]
    for candidate in candidates:
        try:
            return ImageFont.truetype(str(candidate), size)
        except OSError:
            continue
    return ImageFont.load_default()


def _project(lat: float, lon: float, rotation: float, radius: float = 164) -> tuple[float, float, float]:
    longitude = lon + rotation
    cos_lat = math.cos(lat)
    x = 280 + radius * cos_lat * math.sin(longitude)
    y = 236 - radius * math.sin(lat) * 0.94
    z = cos_lat * math.cos(longitude)
    return x, y, z


def _line(layer: Image.Image, points: Iterable[tuple[float, float, float]], width: int = 1) -> None:
    draw = ImageDraw.Draw(layer, "RGBA")
    sequence = list(points)
    for start, end in zip(sequence, sequence[1:]):
        depth = (start[2] + end[2]) / 2
        color = BRIGHT if depth >= 0 else DEEP
        opacity = round(48 + max(-0.3, depth) * 145) if depth >= 0 else 24
        draw.line((start[0], start[1], end[0], end[1]), fill=(*color, max(12, opacity)), width=width)


def _draw_globe(rotation: float) -> Image.Image:
    frame = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))

    glow = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow, "RGBA")
    glow_draw.ellipse((102, 58, 458, 414), outline=(*GREEN, 112), width=14)
    glow_draw.ellipse((126, 82, 434, 390), fill=(*DEEP, 24))
    glow_draw.line((280, 64, 280, 445), fill=(*BRIGHT, 86), width=3)
    frame.alpha_composite(glow.filter(ImageFilter.GaussianBlur(18)))

    grid = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    for latitude in (-1.08, -0.72, -0.36, 0.0, 0.36, 0.72, 1.08):
        _line(grid, (_project(latitude, step * math.pi / 48 - math.pi, rotation) for step in range(97)))
    for longitude in (step * math.pi / 8 for step in range(16)):
        _line(grid, (_project(-math.pi / 2 + step * math.pi / 48, longitude, rotation) for step in range(49)))

    draw = ImageDraw.Draw(grid, "RGBA")
    nodes: list[tuple[float, float, float, str]] = []
    for index, (name, lat, lon) in enumerate(REPOSITORIES):
        x, y, z = _project(lat, lon, rotation)
        nodes.append((x, y, z, name))
        if z > -0.08:
            radius = 5 if z > 0.28 else 3
            draw.ellipse((x - radius * 2.4, y - radius * 2.4, x + radius * 2.4, y + radius * 2.4), fill=(*GREEN, 28))
            draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=(*BRIGHT, 245), outline=(*GREEN, 255), width=1)
            draw.text((x + 8, y - 8), f"R{index + 1:02d}", font=_font("mono", 9), fill=(*BRIGHT, 210))
    for index, start in enumerate(nodes):
        end = nodes[(index + 1) % len(nodes)]
        if start[2] > 0 and end[2] > 0:
            midpoint = ((start[0] + end[0]) / 2, min(start[1], end[1]) - 22)
            draw.line((start[0], start[1], midpoint[0], midpoint[1], end[0], end[1]), fill=(*MINT, 125), width=1)

    for index in range(72):
        latitude = math.asin(-1 + 2 * (index + 0.5) / 72)
        longitude = index * math.pi * (3 - math.sqrt(5))
        x, y, z = _project(latitude, longitude, rotation)
        if z > 0:
            radius = 1 + round(z * 1.5)
            draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=(*BRIGHT, round(75 + z * 145)))

    draw.ellipse((111, 67, 449, 405), outline=(*BRIGHT, 190), width=2)
    draw.arc((122, 79, 438, 395), 198, 327, fill=(*MINT, 225), width=3)
    frame.alpha_composite(grid)

    base = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    bd = ImageDraw.Draw(base, "RGBA")
    bd.line((280, 401, 280, 438), fill=(*BRIGHT, 180), width=2)
    for index, bounds in enumerate(((145, 408, 415, 470), (174, 420, 386, 460), (208, 430, 352, 451))):
        bd.ellipse(bounds, outline=(*GREEN, 165 - index * 30), width=2)
    for x in range(72, 489, 52):
        bd.line((280, 435, x, 492), fill=(*DEEP, 68), width=1)
    bd.line((75, 492, 485, 492), fill=(*GREEN, 94), width=1)
    bd.text((32, 28), "SYSTEMS OBSERVATORY", font=_font("mono", 12), fill=(*MINT, 235))
    bd.text((390, 28), "STATUS  ACTIVE", font=_font("mono", 10), fill=(*BRIGHT, 210))
    label = "REPOSITORY CONTOURS"
    box = bd.textbbox((0, 0), label, font=_font("display", 20))
    bd.text(((WIDTH - (box[2] - box[0])) / 2, 505), label, font=_font("display", 20), fill=(*BRIGHT, 245))
    detail = "04 FEATURED SYSTEMS  //  LIVE ROTATION"
    box = bd.textbbox((0, 0), detail, font=_font("mono", 9))
    bd.text(((WIDTH - (box[2] - box[0])) / 2, 536), detail, font=_font("mono", 9), fill=(*GREEN, 210))
    frame.alpha_composite(base)
    return frame


def _flatten(frame: Image.Image) -> Image.Image:
    # GIF supports binary rather than graded transparency. Preserve the source
    # green RGB values for retained pixels so the transparent key cannot bleed
    # magenta into soft holographic layers during palette conversion.
    rgb = frame.convert("RGB")
    mask = frame.getchannel("A").point(lambda value: 255 if value <= 16 else 0)
    rgb.paste(TRANSPARENT_KEY, mask=mask)
    return rgb


def generate() -> None:
    frames = [_draw_globe(index * math.tau / FRAME_COUNT) for index in range(FRAME_COUNT)]
    STATIC_PATH.parent.mkdir(parents=True, exist_ok=True)
    frames[10].save(STATIC_PATH, optimize=True)

    atlas = Image.new("RGB", (WIDTH * 8, HEIGHT), TRANSPARENT_KEY)
    for index, frame in enumerate(frames[::12]):
        atlas.paste(_flatten(frame), (index * WIDTH, 0))
    palette = atlas.quantize(colors=96, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    colors = palette.getpalette()
    for index, color in enumerate((TRANSPARENT_KEY, GREEN, BRIGHT, MINT, DEEP, QUIET)):
        colors[index * 3:index * 3 + 3] = list(color)
    palette.putpalette(colors)

    indexed: list[Image.Image] = []
    for frame in frames:
        item = _flatten(frame).quantize(palette=palette, dither=Image.Dither.NONE)
        item.paste(0, mask=frame.getchannel("A").point(lambda value: 255 if value <= 16 else 0))
        indexed.append(item)
    indexed[0].save(
        GIF_PATH,
        save_all=True,
        append_images=indexed[1:],
        duration=FRAME_DURATION_MS,
        loop=0,
        optimize=True,
        disposal=2,
        transparency=0,
    )
    print(f"Generated {GIF_PATH.name} ({GIF_PATH.stat().st_size:,} bytes) and {STATIC_PATH.name}.")


if __name__ == "__main__":
    generate()
