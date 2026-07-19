#!/usr/bin/env python3
"""Render a theme-aware cinematic ASCII statistics room for the profile README."""

from __future__ import annotations

import datetime as dt
import math
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from PIL import Image, ImageDraw, ImageFilter, ImageFont

WIDTH, HEIGHT = 1200, 900
FPS = 15
FRAMES_PER_METRIC = 50
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
    "light", (255, 255, 255), (240, 242, 245), (221, 225, 230),
    (36, 41, 47), (87, 96, 106), (140, 149, 159), (250, 251, 252),
    (246, 248, 250), (255, 255, 255), (205, 214, 224), (22, 27, 34),
)
DARK = Theme(
    "dark", (13, 17, 23), (28, 33, 40), (48, 54, 61),
    (240, 246, 252), (201, 209, 217), (139, 148, 158), (22, 27, 34),
    (18, 23, 30), (240, 246, 252), (139, 148, 158), (2, 6, 12),
)

ACCENTS = [
    (47, 129, 247), (210, 153, 34), (57, 197, 207), (63, 185, 80),
    (163, 113, 247), (240, 136, 62), (255, 107, 107),
]


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "C:/Windows/Fonts/consolab.ttf" if bold else "C:/Windows/Fonts/consola.ttf",
        "DejaVuSansMono-Bold.ttf" if bold else "DejaVuSansMono.ttf",
    ]
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size)
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
    image = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    atmosphere = Image.new("RGBA", image.size, (0, 0, 0, 0))
    atmospheric_draw = ImageDraw.Draw(atmosphere, "RGBA")
    wall_alpha = 34 if theme.name == "dark" else 20
    atmospheric_draw.ellipse((105, 35, 1095, 790), fill=_alpha(theme.wall, wall_alpha))
    atmospheric_draw.ellipse((175, 35, 760, 660), fill=_alpha(ACCENTS[0], 25 if theme.name == "dark" else 16))
    atmospheric_draw.ellipse((520, 120, 1050, 720), fill=_alpha(ACCENTS[4], 18 if theme.name == "dark" else 11))
    image.alpha_composite(atmosphere.filter(ImageFilter.GaussianBlur(72)))
    draw = ImageDraw.Draw(image, "RGBA")
    mono = _font(11)
    glyphs = ".,:;"
    for row, y in enumerate(range(44, 670, 24)):
        for col, x in enumerate(range(26, WIDTH - 26, 31)):
            if (row * 19 + col * 31) % 7 in (0, 3):
                atmospheric_color = ACCENTS[(row + col) % len(ACCENTS)] if (row + col) % 5 == 0 else theme.wall_glyph
                draw.text((x, y), glyphs[(row + col) % len(glyphs)], font=mono, fill=_alpha(atmospheric_color, 54))
    draw.line((90, 688, 1110, 688), fill=_alpha(ACCENTS[0], 105), width=1)
    return image


def _draw_ascii_illustration(layer: Image.Image, metric: int, box: tuple[int, int, int, int], accent: tuple[int, int, int], opacity: int = 220) -> None:
    draw = ImageDraw.Draw(layer, "RGBA")
    x0, y0, x1, y1 = box
    font = _font(max(10, round((x1 - x0) / 24)), bold=True)
    art = [
        ["   |==|  |==|  |==|", "   |::|--|::|--|::|", "   |##|  |##|  |##|", "---+--+--+--+--+---", "      \\__|__/"],
        ["        .       ", "    .   *   .   ", "  *   \\|/   * ", "----- --*-- -----", "    .  /|\\  .  "],
        ["      (o)      ", "   (o)-+- (o)   ", "      |\\       ", "  (o)-+-(o)     ", "     / \\ (o)   "],
        [" .:  ::  :;  ;:", "::;;;::;;::;;;::", ";;##;;####;;##;;", "###&&####&&#####", "__::___;;;___::__"],
        ["o-----o       o ", "       \\     /  ", "        o---o   ", "       /     \\  ", "  o---o       o "],
        ["== import data ==", "-- validate rules --", ":: audit events ::", "++ export report ++", "================="],
        ["       .o.       ", "   .-'  |  '-.   ", "  /  .--+--.  \\  ", " |  /   |   \\  | ", "  '-.___|__.-'   "],
    ][metric]
    line_h = max(12, round((y1 - y0) / 6))
    for line_no, text in enumerate(art):
        _center_text(draw, ((x0 + x1) / 2 + 1, y0 + line_no * line_h + 1), text, font, _alpha(accent, round(opacity * 0.24)))
        _center_text(draw, ((x0 + x1) / 2, y0 + line_no * line_h), text, font, _alpha(accent, opacity))


def _poster(theme: Theme, metric: int, title: str, value: str, note: str, updated: str, size: tuple[int, int], active: bool) -> Image.Image:
    width, height = size
    panel = Image.new("RGBA", size, (0, 0, 0, 0))
    shadow = Image.new("RGBA", size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow, "RGBA")
    accent = ACCENTS[metric]
    sd.rounded_rectangle((18, 20, width - 18, height - 10), radius=22, fill=_alpha(accent, 60 if active else 35))
    sd.rounded_rectangle((22, 25, width - 14, height - 6), radius=22, fill=(0, 0, 0, 62 if theme.name == "light" else 118))
    shadow = shadow.filter(ImageFilter.GaussianBlur(13))
    panel.alpha_composite(shadow)
    draw = ImageDraw.Draw(panel, "RGBA")
    fill = theme.poster if active else theme.poster_far
    draw.rounded_rectangle((9, 7, width - 9, height - 17), radius=19, fill=_alpha(fill, 235), outline=_alpha(accent, 205 if active else 125), width=1)
    draw.line((29, 8, width - 29, 8), fill=_alpha(accent, 245 if active else 145), width=2)
    # ASCII material shell: aligned, stable characters instead of raster noise.
    shell_font = _font(10)
    shell_chars = ".:;+=x"
    for row, y in enumerate(range(22, height - 28, 16)):
        for col, x in enumerate(range(22, width - 22, 18)):
            if (row * 11 + col * 7 + metric) % 9 == 0:
                draw.text((x, y), shell_chars[(row + col + metric) % len(shell_chars)], font=shell_font, fill=_alpha(theme.wall_glyph, 32))
    draw.text((28, 25), f"{metric + 1:02d} / {title}", font=_font(19, True), fill=_alpha(accent if active else theme.secondary, 255))
    draw.text((28, 60), value, font=_font(45, True), fill=_alpha(theme.primary, 255))
    draw.text((28, 112), note, font=_font(13, True), fill=_alpha(theme.secondary, 235))
    _draw_ascii_illustration(panel, metric, (25, 155, width - 25, height - 82), accent, 255 if active else 205)
    draw.ellipse((29, height - 55, 42, height - 42), fill=_alpha(accent, 255))
    draw.text((53, height - 59), updated, font=_font(11), fill=_alpha(theme.muted, 220))
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
    veil_phase = max(0.0, min(1.0, (amount - 0.10) / 0.38))
    if veil_phase > 0:
        veil_size = round(62 + 350 * _smooth(veil_phase))
        veil_alpha = round(78 * (1.0 - _smooth(veil_phase))) + 12
        _center_text(draw, (600, 185 - veil_size * 0.22), title, _font(veil_size, True), _alpha(accent, veil_alpha))
    hero_alpha = round(255 * _smooth(amount))
    _center_text(draw, (600, 116), title, _font(60, True), _alpha(accent, hero_alpha))
    value_size = 170 if len(value) <= 4 else 138
    _center_text(draw, (600, 204), value, _font(value_size, True), _alpha(theme.primary, hero_alpha))
    _center_text(draw, (600, 405), note, _font(25, True), _alpha(theme.secondary, hero_alpha))
    _draw_ascii_illustration(layer, metric, (330, 468, 870, 650), accent, round(248 * amount))
    _center_text(draw, (600, 640), f"UPDATED {updated}", _font(13), _alpha(theme.muted, hero_alpha))
    base.alpha_composite(layer)


def _draw_furniture(base: Image.Image, theme: Theme) -> None:
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer, "RGBA")
    mono = _font(12, True)
    # Contact shadows retain the glyph rhythm and remain deliberately soft.
    shadow = Image.new("RGBA", base.size, (0, 0, 0, 0))
    sh = ImageDraw.Draw(shadow, "RGBA")
    sh.ellipse((345, 700, 855, 755), fill=(0, 0, 0, 48 if theme.name == "light" else 100))
    sh.ellipse((490, 855, 710, 900), fill=(0, 0, 0, 75 if theme.name == "light" else 135))
    layer.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(18)))
    desk_top = "=" * 66
    draw.text((337, 688), desk_top, font=mono, fill=_alpha(theme.desk_mid, 255))
    draw.text((337, 676), "_" * 66, font=mono, fill=_alpha(theme.desk_hi, 255))
    for row, y in enumerate(range(704, 884, 12)):
        inset = row // 5
        draw.text((369 + inset, y), "/", font=mono, fill=_alpha(theme.desk_mid, 245))
        draw.text((819 - inset, y), "\\", font=mono, fill=_alpha(theme.desk_mid, 245))
    # Sculptural ASCII shell chair.
    chair_font = _font(13, True)
    ramp = "@&B8#MW%Xx+:"
    for row in range(15):
        ny = row / 14
        half = round(84 * math.sin(math.pi * (0.10 + ny * 0.82)) ** 0.72)
        y = 692 + row * 11
        for col, x in enumerate(range(600 - half, 600 + half, 8)):
            distance = abs(x - 600) / max(1, half)
            index = min(len(ramp) - 1, round(distance * 7 + ny * 3))
            chair_tone = _mix(theme.chair, ACCENTS[0], 0.44) if distance > 0.74 else _mix(theme.chair, theme.muted, distance * 0.18)
            draw.text((x, y), ramp[index], font=chair_font, fill=_alpha(chair_tone, 255))
    draw.text((525, 847), "/", font=_font(17, True), fill=_alpha(theme.chair, 255))
    draw.text((667, 847), "\\", font=_font(17, True), fill=_alpha(theme.chair, 255))
    draw.text((506, 872), "/", font=_font(17, True), fill=_alpha(theme.chair, 255))
    draw.text((686, 872), "\\", font=_font(17, True), fill=_alpha(theme.chair, 255))
    # Delicate directional ASCII plant.
    leaf = (43, 218, 232)
    leaf_dark = (4, 145, 166)
    plant_font = _font(16, True)
    stems = [(710, 672, 684, 608, "/"), (710, 672, 733, 600, "\\"), (710, 672, 708, 587, "|"), (710, 672, 753, 625, "\\")]
    for x0, y0, x1, y1, glyph in stems:
        steps = 7
        for step in range(steps):
            x = x0 + (x1 - x0) * step / steps
            y = y0 + (y1 - y0) * step / steps
            draw.text((x, y), glyph, font=plant_font, fill=_alpha(leaf_dark, 255))
    for x, y, glyph in [(676, 599, "<"), (700, 580, "{"), (728, 592, "}"), (748, 615, ">"), (691, 620, "<"), (725, 622, ">")]:
        draw.text((x, y), glyph * 2, font=_font(19, True), fill=_alpha(leaf, 255))
    pot_lines = ["/::::\\", "|####|", "\\____/"]
    for line, y in zip(pot_lines, (659, 675, 691)):
        _center_text(draw, (712, y), line, _font(14, True), _alpha((255, 139, 79), 255))
    base.alpha_composite(layer)


def _compose(theme: Theme, rows: list[tuple[str, str, str]], posters: list[Image.Image], metric: int, local: float, updated: str, base: Image.Image, furniture: Image.Image) -> Image.Image:
    frame = base.copy().convert("RGBA")
    # Cinematic stages: recognition, dispersal/approach, hold, recession, restoration/navigation.
    approach = _smooth((local - 0.10) / 0.22) if local < 0.38 else 1.0
    recede = 1.0 - _smooth((local - 0.66) / 0.17) if local > 0.66 else 1.0
    hero = max(0.0, min(approach, recede))
    disperse = hero
    positions = [40, 300, 600, 900, 1160]
    for slot, relative in enumerate((-2, -1, 0, 1, 2)):
        index = (metric + relative) % METRIC_COUNT
        selected = relative == 0
        x = positions[slot]
        y = 310 if selected else 325
        scale = 1.0 if selected else (0.92 if abs(relative) == 1 else 0.84)
        opacity = 1.0 if selected else (0.82 if abs(relative) == 1 else 0.48)
        blur = 0.0
        if disperse > 0:
            if selected:
                opacity *= max(0.0, 1.0 - hero * 1.2)
                scale *= 1.0 + hero * 0.45
            else:
                direction = -1 if relative < 0 else 1
                x += direction * disperse * (150 + abs(relative) * 55)
                y -= disperse * 28
                scale *= 1.0 - disperse * 0.18
                opacity *= 1.0 - disperse * 0.78
                blur = disperse * 3.5
        _paste_scaled(frame, posters[index], (x, y), scale, opacity, blur)
    if hero > 0.03:
        _draw_hero(frame, theme, metric, rows[metric], updated, hero)
    navigation = ImageDraw.Draw(frame, "RGBA")
    for dot in range(METRIC_COUNT):
        x = 531 + dot * 23
        color = ACCENTS[metric] if dot == metric else theme.muted
        navigation.ellipse((x, 660, x + 7, 667), fill=_alpha(color, 245 if dot == metric else 75))
    orbit_x = 510 + round(44 * local)
    navigation.ellipse((orbit_x, 655, orbit_x + 3, 658), fill=_alpha(ACCENTS[metric], 235))
    frame.alpha_composite(furniture)
    return frame


def _flatten_for_gif(frame: Image.Image, theme: Theme) -> Image.Image:
    rgba = frame.convert("RGBA")
    flattened = Image.new("RGBA", rgba.size, (*theme.edge, 255))
    flattened.alpha_composite(rgba)
    rgb = flattened.convert("RGB")
    transparent_mask = rgba.getchannel("A").point(lambda value: 255 if value <= GIF_ALPHA_THRESHOLD else 0)
    rgb.paste(TRANSPARENT_KEY, mask=transparent_mask)
    return rgb


def _global_palette(samples: Iterable[Image.Image], theme: Theme) -> Image.Image:
    sample_list = [_flatten_for_gif(sample, theme).resize((300, 225), Image.Resampling.LANCZOS) for sample in samples]
    atlas = Image.new("RGB", (300 * len(sample_list), 225))
    for index, sample in enumerate(sample_list):
        atlas.paste(sample, (index * 300, 0))
    palette = atlas.quantize(colors=96, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    palette_data = palette.getpalette()
    pinned_colors = [
        TRANSPARENT_KEY,
        theme.edge,
        *ACCENTS,
        (43, 218, 232),
        (4, 145, 166),
        (255, 139, 79),
        (88, 166, 255),
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
    furniture = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    _draw_furniture(furniture, theme)
    posters = [_poster(theme, index, *row, updated, (250, 330), index == 0) for index, row in enumerate(rows)]
    key_times = [0.05, 0.18, 0.29, 0.42, 0.55, 0.73, 0.90, 0.99]
    sample_frames = [_compose(theme, rows, posters, index % METRIC_COUNT, local, updated, base, furniture) for index, local in enumerate(key_times)]
    palette = _global_palette(sample_frames, theme)
    static_frame = _compose(theme, rows, posters, 0, 0.08, updated, base, furniture)
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
            frame = _compose(theme, rows, posters, metric, local, updated, base, furniture)
            if local > 0.88:
                navigation = _smooth((local - 0.88) / 0.12)
                incoming = _compose(theme, rows, posters, (metric + 1) % METRIC_COUNT, 0.0, updated, base, furniture)
                frame = Image.blend(frame, incoming, navigation)
            indexed = _flatten_for_gif(frame, theme).quantize(palette=palette, dither=Image.Dither.NONE)
            transparent_mask = frame.getchannel("A").point(lambda value: 255 if value <= GIF_ALPHA_THRESHOLD else 0)
            indexed.paste(0, mask=transparent_mask)
            frames.append(indexed)
    gif_path.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        gif_path, save_all=True, append_images=frames[1:], duration=FRAME_DURATION_MS,
        loop=0, optimize=True, disposal=2, transparency=0,
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
            "dark_gif": temporary / "ascii-stats-gallery-color-dark-transparent.gif",
            "light_static": temporary / "ascii-stats-gallery-color-transparent-static.png",
            "dark_static": temporary / "ascii-stats-gallery-color-dark-transparent-static.png",
        }
        results = [
            render_theme(stats, LIGHT, targets["light_gif"], targets["light_static"], contact_sheet),
            render_theme(stats, DARK, targets["dark_gif"], targets["dark_static"]),
        ]
        assets.mkdir(parents=True, exist_ok=True)
        for source in targets.values():
            shutil.copy2(source, assets / source.name)
    return results
