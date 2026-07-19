#!/usr/bin/env python3
"""Render the cinematic Emerald Observatory statistics sequence."""

from __future__ import annotations

import datetime as dt
import math
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from PIL import Image, ImageDraw, ImageFilter, ImageFont

WIDTH, HEIGHT = 1200, 675
ROOT = Path(__file__).resolve().parents[1]
FONTS = ROOT / "assets" / "fonts"
OBSERVATORY_MASTER = ROOT / "assets" / "cinematic" / "emerald-observatory-master.png"
FPS = 12
FRAMES_PER_METRIC = 35
METRIC_COUNT = 7
FRAME_DURATION_MS = round(1000 / FPS)
TRANSPARENT_KEY = (255, 0, 255)
GIF_ALPHA_THRESHOLD = 70


@dataclass(frozen=True)
class Theme:
    name: str
    edge: tuple[int, int, int]
    wall: tuple[int, int, int]
    wall_glyph: tuple[int, int, int]
    primary: tuple[int, int, int]
    secondary: tuple[int, int, int]
    muted: tuple[int, int, int]
    poster: tuple[int, int, int]
    poster_far: tuple[int, int, int]
    desk_hi: tuple[int, int, int]
    desk_mid: tuple[int, int, int]
    chair: tuple[int, int, int]


LIGHT = Theme(
    "light", (4, 8, 6), (18, 27, 21), (67, 96, 75),
    (246, 252, 248), (207, 222, 212), (149, 169, 155), (13, 22, 17),
    (9, 16, 12), (232, 242, 235), (101, 133, 111), (5, 9, 7),
)
DARK = Theme(
    "dark", (4, 8, 6), (18, 27, 21), (67, 96, 75),
    (246, 252, 248), (207, 222, 212), (149, 169, 155), (13, 22, 17),
    (9, 16, 12), (232, 242, 235), (101, 133, 111), (5, 9, 7),
)

ACCENTS = [
    (63, 185, 80), (86, 211, 100), (126, 231, 135), (46, 160, 67),
    (57, 211, 83), (35, 134, 54), (143, 239, 156),
]


def _font(size: int, bold: bool = False, role: str = "mono") -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    bundled = {
        "display": FONTS / "SpaceGrotesk-Variable.ttf",
        "body": FONTS / "Inter-Variable.ttf",
        "mono": FONTS / "IBMPlexMono-Medium.ttf",
    }[role]
    fallbacks = {
        "display": ["C:/Windows/Fonts/segoeuib.ttf", "DejaVuSans-Bold.ttf"],
        "body": ["C:/Windows/Fonts/segoeui.ttf", "DejaVuSans.ttf"],
        "mono": ["C:/Windows/Fonts/consolab.ttf" if bold else "C:/Windows/Fonts/consola.ttf", "DejaVuSansMono-Bold.ttf" if bold else "DejaVuSansMono.ttf"],
    }[role]
    candidates = [str(bundled), *fallbacks]
    for candidate in candidates:
        try:
            font = ImageFont.truetype(candidate, size)
            if bold and role in {"display", "body"} and hasattr(font, "set_variation_by_name"):
                try:
                    font.set_variation_by_name("SemiBold")
                except (OSError, ValueError):
                    pass
            return font
        except OSError:
            pass
    return ImageFont.load_default()


def _smooth(value: float) -> float:
    value = max(0.0, min(1.0, value))
    return value * value * (3.0 - 2.0 * value)


def _mix(a: tuple[int, int, int], b: tuple[int, int, int], amount: float) -> tuple[int, int, int]:
    return tuple(round(x + (y - x) * amount) for x, y in zip(a, b))


def _alpha(color: tuple[int, int, int], opacity: int) -> tuple[int, int, int, int]:
    return (*color, max(0, min(255, opacity)))


def _center_text(draw: ImageDraw.ImageDraw, xy: tuple[float, float], text: str, font: ImageFont.ImageFont, fill: tuple[int, ...]) -> None:
    box = draw.textbbox((0, 0), text, font=font)
    draw.text((xy[0] - (box[2] - box[0]) / 2, xy[1]), text, font=font, fill=fill)


def _metric_rows(stats: dict[str, Any]) -> list[tuple[str, str, str]]:
    compact = lambda value: f"{value / 1000:.1f}K".replace(".0K", "K") if value >= 1000 else f"{value:,}"
    return [
        ("REPOSITORIES", f"{stats['repositories']:,}", "OWNED PUBLIC PROJECTS"),
        ("STARS", f"{stats['stars']:,}", "CURRENT RECOGNITION"),
        ("FOLLOWERS", f"{stats['followers']:,}", "CURRENT AUDIENCE"),
        ("CONTRIBUTIONS", f"{stats['contributions_365d']:,}", "TRAILING 365 DAYS"),
        ("COMMITS", f"{stats['commits_365d']:,}", "TRAILING 365 DAYS"),
        ("SOURCE LINES", compact(stats["estimated_source_lines"]), "TRACKED CODE ESTIMATE"),
        ("ACTIVITY HOURS", f"{stats['estimated_github_hours']:,}", "LIFETIME ACTIVITY ESTIMATE"),
    ]


def _room_base(theme: Theme) -> Image.Image:
    if not OBSERVATORY_MASTER.exists():
        raise FileNotFoundError(f"Missing cinematic background plate: {OBSERVATORY_MASTER}")
    with Image.open(OBSERVATORY_MASTER) as source:
        image = source.convert("RGBA").resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
    # A filmic vignette protects the overlaid telemetry without flattening the
    # generated glass, metal, stars, chair, desk or volumetric globe.
    vignette = Image.new("RGBA", image.size, (0, 0, 0, 0))
    vd = ImageDraw.Draw(vignette, "RGBA")
    for inset, alpha in ((0, 96), (34, 56), (72, 28)):
        vd.rounded_rectangle((inset, inset, WIDTH - inset, HEIGHT - inset), radius=44, outline=(0, 0, 0, alpha), width=38)
    vd.rectangle((0, 0, WIDTH, 118), fill=(0, 0, 0, 44))
    image.alpha_composite(vignette.filter(ImageFilter.GaussianBlur(18)))
    return image


def _globe_point(latitude: float, longitude: float, rotation: float, radius: float = 112) -> tuple[float, float, float]:
    longitude += rotation
    cos_lat = math.cos(latitude)
    return (
        600 + radius * cos_lat * math.sin(longitude),
        272 - radius * math.sin(latitude) * 0.92,
        cos_lat * math.cos(longitude),
    )


def _draw_observatory_globe(base: Image.Image, theme: Theme, rotation: float) -> None:
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    glow = Image.new("RGBA", base.size, (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow, "RGBA")
    glow_draw.ellipse((474, 146, 726, 398), outline=_alpha(ACCENTS[0], 72), width=10)
    layer.alpha_composite(glow.filter(ImageFilter.GaussianBlur(15)))
    draw = ImageDraw.Draw(layer, "RGBA")

    def path(points: Iterable[tuple[float, float, float]]) -> None:
        sequence = list(points)
        for start, end in zip(sequence, sequence[1:]):
            depth = (start[2] + end[2]) / 2
            color = ACCENTS[2] if depth >= 0 else ACCENTS[5]
            opacity = round(45 + max(0, depth) * 150) if depth >= 0 else 24
            draw.line((start[0], start[1], end[0], end[1]), fill=_alpha(color, opacity), width=1)

    for latitude in (-0.95, -0.48, 0.0, 0.48, 0.95):
        path(_globe_point(latitude, step * math.pi / 36 - math.pi, rotation) for step in range(73))
    for longitude in (step * math.pi / 6 for step in range(12)):
        path(_globe_point(-math.pi / 2 + step * math.pi / 36, longitude, rotation) for step in range(37))
    draw.ellipse((488, 160, 712, 384), outline=_alpha(ACCENTS[2], 150), width=1)
    for index in range(28):
        latitude = math.asin(-1 + 2 * (index + .5) / 28)
        longitude = index * math.pi * (3 - math.sqrt(5))
        x, y, depth = _globe_point(latitude, longitude, rotation)
        if depth > 0:
            radius = 1 + round(depth)
            draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=_alpha(ACCENTS[2], round(90 + depth * 145)))
    for bounds, opacity in (((468, 397, 732, 446), 110), ((510, 406, 690, 438), 86), ((548, 414, 652, 431), 62)):
        draw.ellipse(bounds, outline=_alpha(ACCENTS[0], opacity), width=1)
    base.alpha_composite(layer)


def _draw_metric_trace(layer: Image.Image, metric: int, box: tuple[int, int, int, int], accent: tuple[int, int, int], opacity: int = 220) -> None:
    draw = ImageDraw.Draw(layer, "RGBA")
    x0, y0, x1, y1 = box
    width, height = x1 - x0, y1 - y0
    draw.rounded_rectangle(box, radius=12, fill=(0, 0, 0, 26), outline=_alpha(accent, 72), width=1)
    baseline = y1 - 18
    points: list[tuple[float, float]] = []
    for index in range(13):
        phase = index * 0.72 + metric * 0.63
        energy = .38 + .32 * math.sin(phase) + .16 * math.sin(phase * 1.93)
        points.append((x0 + 14 + index * (width - 28) / 12, baseline - max(4, energy * (height - 28))))
    glow = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow, "RGBA")
    gd.line(points, fill=_alpha(accent, round(opacity * .58)), width=5, joint="curve")
    layer.alpha_composite(glow.filter(ImageFilter.GaussianBlur(6)))
    draw.line(points, fill=_alpha(accent, opacity), width=2, joint="curve")
    draw.line((x0 + 14, baseline, x1 - 14, baseline), fill=(204, 230, 212, 45), width=1)
    for x, y in points[::3]:
        draw.ellipse((x - 3, y - 3, x + 3, y + 3), fill=_alpha((126, 231, 135), opacity))


def _poster(theme: Theme, metric: int, title: str, value: str, note: str, updated: str, size: tuple[int, int], active: bool) -> Image.Image:
    width, height = size
    panel = Image.new("RGBA", size, (0, 0, 0, 0))
    shadow = Image.new("RGBA", size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow, "RGBA")
    accent = ACCENTS[metric]
    sd.rounded_rectangle((15, 16, width - 15, height - 8), radius=22, fill=_alpha(accent, 76 if active else 42))
    sd.rounded_rectangle((18, 22, width - 12, height - 4), radius=22, fill=(0, 0, 0, 180))
    shadow = shadow.filter(ImageFilter.GaussianBlur(16))
    panel.alpha_composite(shadow)
    draw = ImageDraw.Draw(panel, "RGBA")
    fill = theme.poster if active else theme.poster_far
    draw.rounded_rectangle((9, 7, width - 9, height - 17), radius=19, fill=_alpha(fill, 224), outline=_alpha((225, 244, 232), 105), width=1)
    draw.rounded_rectangle((11, 9, width - 11, height - 19), radius=18, outline=_alpha(accent, 190 if active else 96), width=1)
    draw.line((31, 9, width - 55, 9), fill=_alpha((232, 255, 238), 205 if active else 105), width=2)
    draw.line((width - 51, 9, width - 25, 9), fill=_alpha(accent, 250 if active else 135), width=2)
    draw.text((27, 25), f"{metric + 1:02d} / {title}", font=_font(15, True), fill=_alpha(accent if active else theme.secondary, 255))
    draw.text((27, 56), value, font=_font(43, True, "display"), fill=_alpha(theme.primary, 255))
    draw.text((27, 105), note, font=_font(11, False, "body"), fill=_alpha(theme.secondary, 245))
    _draw_metric_trace(panel, metric, (25, 143, width - 25, height - 76), accent, 255 if active else 170)
    draw.ellipse((29, height - 55, 42, height - 42), fill=_alpha(accent, 255))
    draw.text((53, height - 58), updated, font=_font(9), fill=_alpha(theme.muted, 245))
    return panel


def _paste_scaled(base: Image.Image, asset: Image.Image, center: tuple[float, float], scale: float, opacity: float, blur: float = 0.0) -> None:
    width = max(1, round(asset.width * scale))
    height = max(1, round(asset.height * scale))
    resized = asset.resize((width, height), Image.Resampling.LANCZOS)
    if blur > 0:
        resized = resized.filter(ImageFilter.GaussianBlur(blur))
    if opacity < 0.999:
        alpha_channel = resized.getchannel("A").point(lambda value: round(value * opacity))
        resized.putalpha(alpha_channel)
    base.alpha_composite(resized, (round(center[0] - width / 2), round(center[1] - height / 2)))


def _draw_hero(base: Image.Image, theme: Theme, metric: int, row: tuple[str, str, str], updated: str, amount: float) -> None:
    title, value, note = row
    accent = ACCENTS[metric]
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer, "RGBA")
    hero_alpha = round(255 * _smooth(amount))
    glow = Image.new("RGBA", base.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow, "RGBA")
    gd.rounded_rectangle((54, 106, 430, 350), radius=26, outline=_alpha(accent, round(hero_alpha * .55)), width=10)
    layer.alpha_composite(glow.filter(ImageFilter.GaussianBlur(20)))
    draw = ImageDraw.Draw(layer, "RGBA")
    draw.rounded_rectangle((54, 106, 430, 350), radius=26, fill=(4, 10, 7, round(hero_alpha * .82)), outline=(218, 244, 225, round(hero_alpha * .40)), width=1)
    draw.rounded_rectangle((58, 110, 426, 346), radius=23, outline=_alpha(accent, round(hero_alpha * .65)), width=1)
    draw.text((82, 133), "LIVE GITHUB TELEMETRY", font=_font(11, True), fill=_alpha(accent, hero_alpha))
    draw.text((82, 165), title, font=_font(25, True, "display"), fill=_alpha(theme.primary, hero_alpha))
    value_size = 94 if len(value) <= 4 else 76
    draw.text((80, 196), value, font=_font(value_size, True, "display"), fill=_alpha((246, 252, 248), hero_alpha))
    draw.text((82, 296), note, font=_font(14, False, "body"), fill=_alpha(theme.secondary, hero_alpha))
    draw.text((82, 322), f"UPDATED {updated}", font=_font(9), fill=_alpha(theme.muted, hero_alpha))
    base.alpha_composite(layer)


def _compose(theme: Theme, rows: list[tuple[str, str, str]], posters: list[Image.Image], metric: int, local: float, updated: str, base: Image.Image) -> Image.Image:
    frame = base.copy().convert("RGBA")
    # Cinematic stages: recognition, dispersal/approach, hold, recession, restoration/navigation.
    approach = _smooth((local - 0.10) / 0.22) if local < 0.38 else 1.0
    recede = 1.0 - _smooth((local - 0.66) / 0.17) if local > 0.66 else 1.0
    hero = max(0.0, min(approach, recede))
    disperse = hero
    positions = [18, 300, 600, 900, 1182]
    for slot, relative in enumerate((-2, -1, 0, 1, 2)):
        index = (metric + relative) % METRIC_COUNT
        selected = relative == 0
        x = positions[slot]
        y = 234 if selected else 246
        scale = 1.0 if selected else (0.92 if abs(relative) == 1 else 0.84)
        opacity = 1.0 if selected else (0.82 if abs(relative) == 1 else 0.48)
        blur = 0.0
        if disperse > 0:
            if selected:
                opacity *= max(0.0, 1.0 - hero * 1.2)
                scale *= 1.0 + hero * 0.45
            else:
                direction = -1 if relative < 0 else 1
                x += direction * disperse * (138 + abs(relative) * 52)
                y -= disperse * 18
                scale *= 1.0 - disperse * 0.18
                opacity *= 1.0 - disperse * 0.78
                blur = disperse * 3.5
        _paste_scaled(frame, posters[index], (x, y), scale, opacity, blur)
    if hero > 0.03:
        _draw_hero(frame, theme, metric, rows[metric], updated, hero)
    # A moving telemetry mesh gives the photoreal globe motion without
    # replacing its cinematic materials with a flat vector sphere.
    _draw_observatory_globe(frame, theme, metric * 0.72 + local * 0.42)
    navigation = ImageDraw.Draw(frame, "RGBA")
    for dot in range(METRIC_COUNT):
        x = 531 + dot * 23
        color = ACCENTS[metric] if dot == metric else theme.muted
        navigation.ellipse((x, 628, x + 7, 635), fill=_alpha(color, 245 if dot == metric else 75))
    orbit_x = 510 + round(44 * local)
    navigation.ellipse((orbit_x, 623, orbit_x + 3, 626), fill=_alpha(ACCENTS[metric], 235))
    return frame


def _flatten_for_gif(frame: Image.Image, theme: Theme) -> Image.Image:
    return frame.convert("RGB")


def _global_palette(samples: Iterable[Image.Image], theme: Theme) -> Image.Image:
    sample_list = [_flatten_for_gif(sample, theme).resize((300, 225), Image.Resampling.LANCZOS) for sample in samples]
    atlas = Image.new("RGB", (300 * len(sample_list), 225))
    for index, sample in enumerate(sample_list):
        atlas.paste(sample, (index * 300, 0))
    # A shared cinematic palette keeps the photographic background stable while
    # GitHub only has to encode the moving glass/telemetry deltas.
    palette = atlas.quantize(colors=112, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    palette_data = palette.getpalette()
    pinned_colors = [
        TRANSPARENT_KEY,
        theme.edge,
        theme.primary,
        theme.secondary,
        theme.muted,
        theme.poster,
        theme.poster_far,
        *ACCENTS,
        (63, 185, 80),
        (86, 211, 100),
        (126, 231, 135),
    ]
    for index, color in enumerate(pinned_colors):
        palette_data[index * 3:index * 3 + 3] = list(color)
    palette.putpalette(palette_data)
    return palette


def render_theme(stats: dict[str, Any], theme: Theme, gif_path: Path, static_path: Path, contact_sheet_path: Path | None = None) -> dict[str, Any]:
    rows = _metric_rows(stats)
    updated_dt = dt.datetime.fromisoformat(stats["updated_at_utc"])
    updated = updated_dt.strftime("%Y-%m-%d %H:%M UTC")
    base = _room_base(theme)
    posters = [_poster(theme, index, *row, updated, (230, 286), index == 0) for index, row in enumerate(rows)]
    key_times = [0.05, 0.18, 0.29, 0.42, 0.55, 0.73, 0.90, 0.99]
    sample_frames = [_compose(theme, rows, posters, index % METRIC_COUNT, local, updated, base) for index, local in enumerate(key_times)]
    palette = _global_palette(sample_frames, theme)
    static_frame = _compose(theme, rows, posters, 0, 0.08, updated, base)
    static_path.parent.mkdir(parents=True, exist_ok=True)
    static_frame.save(static_path, optimize=True)
    if contact_sheet_path:
        sheet = Image.new("RGB", (800, 1200), theme.edge)
        for index, sample in enumerate(sample_frames):
            preview = Image.new("RGBA", sample.size, (*theme.edge, 255))
            preview.alpha_composite(sample)
            thumb = preview.convert("RGB").resize((400, 300), Image.Resampling.LANCZOS)
            sheet.paste(thumb, ((index % 2) * 400, (index // 2) * 300))
        contact_sheet_path.parent.mkdir(parents=True, exist_ok=True)
        sheet.save(contact_sheet_path, optimize=True)
    frames: list[Image.Image] = []
    for metric in range(METRIC_COUNT):
        for step in range(FRAMES_PER_METRIC):
            local = step / FRAMES_PER_METRIC
            frame = _compose(theme, rows, posters, metric, local, updated, base)
            if local > 0.88:
                navigation = _smooth((local - 0.88) / 0.12)
                incoming = _compose(theme, rows, posters, (metric + 1) % METRIC_COUNT, 0.0, updated, base)
                frame = Image.blend(frame, incoming, navigation)
            indexed = _flatten_for_gif(frame, theme).quantize(palette=palette, dither=Image.Dither.NONE)
            frames.append(indexed)
    gif_path.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        gif_path, save_all=True, append_images=frames[1:], duration=FRAME_DURATION_MS,
        loop=0, optimize=True, disposal=1,
    )
    return {
        "theme": theme.name, "dimensions": [WIDTH, HEIGHT], "fps": FPS,
        "frames": len(frames), "duration_seconds": len(frames) * FRAME_DURATION_MS / 1000,
        "gif_bytes": gif_path.stat().st_size, "static_bytes": static_path.stat().st_size,
    }


def render_ascii_statistics_room(stats: dict[str, Any], root: Path, *, contact_sheet: Path | None = None) -> list[dict[str, Any]]:
    assets = root / "assets"
    with tempfile.TemporaryDirectory(prefix="ascii-room-") as temp_dir:
        temporary = Path(temp_dir)
        targets = {
            "light_gif": temporary / "ascii-stats-gallery-color-transparent.gif",
            "light_static": temporary / "ascii-stats-gallery-color-transparent-static.png",
        }
        # The photographic plate owns its own dark cinematic environment, so a
        # single render remains legible in both GitHub themes and avoids storing
        # a redundant second 10+ MiB animation.
        results = [render_theme(stats, DARK, targets["light_gif"], targets["light_static"], contact_sheet)]
        assets.mkdir(parents=True, exist_ok=True)
        for source in targets.values():
            shutil.copy2(source, assets / source.name)
    return results
