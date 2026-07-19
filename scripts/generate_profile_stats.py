#!/usr/bin/env python3
"""Generate the repository-owned live GitHub statistics SVG.

The GitHub-hours figure is an activity-based estimate, not literal browser time. It
uses lifetime GitHub contribution totals with documented weights so the number is
transparent, repeatable and automatically refreshed.
"""

from __future__ import annotations

import datetime as dt
import html
import json
import math
import os
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageEnhance, ImageFont

USERNAME = os.environ.get("GITHUB_USERNAME", "berendsshalai").strip()
TOKEN = os.environ.get("GITHUB_TOKEN", "").strip()
ROOT = Path(__file__).resolve().parents[1]
SVG_PATH = ROOT / "assets" / "github-stats.svg"
GIF_PATH = ROOT / "assets" / "ascii-stats-gallery.gif"
JSON_PATH = ROOT / "data" / "github-stats.json"
README_PATH = ROOT / "README.md"
GLASS_BACKGROUND_PATH = ROOT / "assets" / "glass-environment.jpg"

API_ROOT = "https://api.github.com"
GRAPHQL_URL = "https://api.github.com/graphql"
MAX_FILE_BYTES = 2_000_000

SOURCE_EXTENSIONS = {
    ".asm", ".bash", ".bat", ".c", ".cc", ".clj", ".cljs", ".cmd", ".cpp", ".cs",
    ".css", ".dart", ".ex", ".exs", ".fs", ".fsx", ".go", ".graphql", ".h", ".hpp",
    ".html", ".java", ".js", ".jsx", ".json", ".kt", ".kts", ".lua", ".m", ".mm",
    ".php", ".pl", ".ps1", ".py", ".r", ".rb", ".rs", ".sass", ".scala", ".scss",
    ".sh", ".sql", ".svelte", ".swift", ".toml", ".ts", ".tsx", ".vb", ".vue",
    ".xml", ".yaml", ".yml",
}
EXCLUDED_PARTS = {
    ".git", ".idea", ".next", ".nuxt", ".output", ".pytest_cache", ".ruff_cache",
    ".venv", ".vscode", "__pycache__", "assets", "build", "coverage", "dist",
    "generated", "node_modules", "public", "site-packages", "target", "vendor",
}
EXCLUDED_SUFFIXES = {".lock", ".map", ".min.css", ".min.js", ".svg"}

# Conservative, documented effort weights for contribution types. These estimate
# effort associated with public GitHub activity; they do not measure logged-in time.
HOUR_WEIGHTS = {
    "commits": 1.5,
    "pull_requests": 2.0,
    "reviews": 0.75,
    "issues": 0.5,
}


class GitHubAPIError(RuntimeError):
    """Raised when GitHub returns an unusable response."""


def request_json(
    url: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
) -> tuple[Any, dict[str, str]]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": f"{USERNAME}-profile-statistics",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            body = response.read().decode("utf-8")
            response_headers = {key.lower(): value for key, value in response.headers.items()}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise GitHubAPIError(f"GitHub API returned HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise GitHubAPIError(f"GitHub API request failed: {exc.reason}") from exc
    try:
        return json.loads(body), response_headers
    except json.JSONDecodeError as exc:
        raise GitHubAPIError("GitHub API returned invalid JSON.") from exc


def fetch_user() -> dict[str, Any]:
    data, _ = request_json(f"{API_ROOT}/users/{urllib.parse.quote(USERNAME)}")
    if not isinstance(data, dict):
        raise GitHubAPIError("Unexpected user response shape.")
    return data


def fetch_owned_public_repositories() -> list[dict[str, Any]]:
    repositories: list[dict[str, Any]] = []
    page = 1
    while True:
        query = urllib.parse.urlencode(
            {"type": "owner", "sort": "full_name", "direction": "asc", "per_page": 100, "page": page}
        )
        data, _ = request_json(f"{API_ROOT}/users/{urllib.parse.quote(USERNAME)}/repos?{query}")
        if not isinstance(data, list):
            raise GitHubAPIError("Unexpected repository response shape.")
        repositories.extend(item for item in data if isinstance(item, dict))
        if len(data) < 100:
            return repositories
        page += 1


CONTRIBUTIONS_QUERY = """
query ProfileContributions($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      totalCommitContributions
      totalIssueContributions
      totalPullRequestContributions
      totalPullRequestReviewContributions
      restrictedContributionsCount
      contributionCalendar { totalContributions }
    }
  }
}
"""


def fetch_contribution_window(start: dt.datetime, end: dt.datetime) -> dict[str, int]:
    payload = {
        "query": CONTRIBUTIONS_QUERY,
        "variables": {
            "login": USERNAME,
            "from": start.isoformat().replace("+00:00", "Z"),
            "to": end.isoformat().replace("+00:00", "Z"),
        },
    }
    data, _ = request_json(GRAPHQL_URL, method="POST", payload=payload)
    if not isinstance(data, dict) or data.get("errors"):
        raise GitHubAPIError(f"Unexpected GraphQL response: {data}")
    user = data.get("data", {}).get("user")
    if not user:
        raise GitHubAPIError(f"GitHub user '{USERNAME}' was not found.")
    collection = user["contributionsCollection"]
    return {
        "contributions": int(collection["contributionCalendar"]["totalContributions"])
        + int(collection.get("restrictedContributionsCount", 0)),
        "commits": int(collection.get("totalCommitContributions", 0)),
        "issues": int(collection.get("totalIssueContributions", 0)),
        "pull_requests": int(collection.get("totalPullRequestContributions", 0)),
        "reviews": int(collection.get("totalPullRequestReviewContributions", 0)),
    }


def fetch_contribution_totals() -> dict[str, int]:
    end = dt.datetime.now(dt.timezone.utc)
    current = fetch_contribution_window(end - dt.timedelta(days=365), end)
    return {f"{key}_365d": value for key, value in current.items()}


def fetch_lifetime_contribution_totals(created_at: str) -> dict[str, int]:
    start = dt.datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    now = dt.datetime.now(dt.timezone.utc)
    totals = {"contributions": 0, "commits": 0, "issues": 0, "pull_requests": 0, "reviews": 0}
    cursor = start
    # GitHub limits a contributions collection to at most one year. Using 364-day
    # windows avoids leap-year boundary failures without overlap.
    while cursor < now:
        window_end = min(cursor + dt.timedelta(days=364, hours=23, minutes=59), now)
        window = fetch_contribution_window(cursor, window_end)
        for key in totals:
            totals[key] += window[key]
        cursor = window_end + dt.timedelta(seconds=1)
    return totals


def estimate_github_hours(lifetime: dict[str, int]) -> int:
    return round(sum(lifetime[key] * weight for key, weight in HOUR_WEIGHTS.items()))


def is_countable_source(path: Path) -> bool:
    lowered_parts = {part.lower() for part in path.parts}
    if lowered_parts & EXCLUDED_PARTS:
        return False
    lower_name = path.name.lower()
    return not any(lower_name.endswith(suffix) for suffix in EXCLUDED_SUFFIXES) and path.suffix.lower() in SOURCE_EXTENSIONS


def count_text_lines(path: Path) -> int:
    if not path.is_file() or path.stat().st_size > MAX_FILE_BYTES:
        return 0
    raw = path.read_bytes()
    if b"\x00" in raw[:8192]:
        return 0
    text = raw.decode("utf-8", errors="ignore")
    return text.count("\n") + (0 if not text or text.endswith("\n") else 1)


def estimate_tracked_source_lines(repositories: list[dict[str, Any]]) -> tuple[int, int, list[str]]:
    total_lines = 0
    counted_repositories = 0
    failed_repositories: list[str] = []
    candidates = [
        repo for repo in repositories
        if not repo.get("fork") and not repo.get("archived") and not repo.get("disabled") and repo.get("clone_url")
    ]
    with tempfile.TemporaryDirectory(prefix="profile-loc-") as temp_root:
        temp_root_path = Path(temp_root)
        for index, repo in enumerate(candidates):
            name = str(repo.get("name", f"repo-{index}"))
            destination = temp_root_path / f"{index:03d}-{name}"
            try:
                subprocess.run(
                    ["git", "clone", "--quiet", "--depth", "1", "--single-branch", str(repo["clone_url"]), str(destination)],
                    check=True, timeout=120, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True,
                )
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                failed_repositories.append(name)
                continue
            for path in destination.rglob("*"):
                relative = path.relative_to(destination)
                if is_countable_source(relative):
                    try:
                        total_lines += count_text_lines(path)
                    except (OSError, UnicodeError):
                        pass
            counted_repositories += 1
            shutil.rmtree(destination, ignore_errors=True)
    return total_lines, counted_repositories, failed_repositories


def compact_number(value: int) -> str:
    if value < 1_000:
        return f"{value:,}"
    if value < 1_000_000:
        return f"{value / 1_000:.1f}K".replace(".0K", "K")
    return f"{value / 1_000_000:.1f}M".replace(".0M", "M")


def metric_card(x: int, y: int, label: str, value: int, note: str = "") -> str:
    return f"""
      <g transform="translate({x} {y})">
        <rect width="292" height="78" rx="12" class="metric-bg"/>
        <text x="18" y="25" class="metric-label">{html.escape(label)}</text>
        <text x="18" y="56" class="metric-value">{html.escape(compact_number(value))}</text>
        <text x="274" y="56" text-anchor="end" class="metric-note">{html.escape(note)}</text>
      </g>"""


def render_svg(stats: dict[str, Any]) -> str:
    updated = html.escape(stats["updated_at_utc"].replace("T", " ").replace("+00:00", " UTC"))
    username = html.escape(stats["username"])
    cards = [
        metric_card(28, 83, "Repositories", stats["repositories"], "public"),
        metric_card(354, 83, "Stars", stats["stars"], "owned repos"),
        metric_card(680, 83, "Followers", stats["followers"], "current"),
        metric_card(28, 177, "Contributions", stats["contributions_365d"], "365 days"),
        metric_card(354, 177, "Commits", stats["commits_365d"], "365 days"),
        metric_card(680, 177, "Source lines", stats["estimated_source_lines"], "estimate"),
        metric_card(354, 271, "GitHub hours", stats["estimated_github_hours"], "lifetime est."),
    ]
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="384" viewBox="0 0 1000 384" role="img" aria-labelledby="title description">
  <title id="title">Live GitHub statistics for {username}</title>
  <desc id="description">Repositories, stars, followers, trailing 365-day contributions and commits, estimated source lines, and an activity-based lifetime GitHub-hours estimate.</desc>
  <style>
    .background {{ fill: #0d1117; stroke: #30363d; }}
    .metric-bg {{ fill: #161b22; stroke: #30363d; }}
    .heading {{ fill: #f0f6fc; font: 700 22px ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }}
    .subheading {{ fill: #8b949e; font: 400 12px ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }}
    .metric-label {{ fill: #8b949e; font: 600 12px ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; letter-spacing: .6px; }}
    .metric-value {{ fill: #58a6ff; font: 700 25px ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }}
    .metric-note {{ fill: #6e7681; font: 400 10px ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }}
  </style>
  <rect x="1" y="1" width="998" height="382" rx="16" class="background"/>
  <text x="28" y="38" class="heading">{username} / GitHub activity</text>
  <text x="28" y="62" class="subheading">Repository-owned statistics / refreshed {updated}</text>
  {''.join(cards)}
</svg>
"""


ASCII_LANDSCAPES = [
    [
        "              .       *          ",
        "       *             .            ",
        "             /\\                   ",
        "        /\\  /  \\      /\\          ",
        "   /\\  /  \\/    \\ /\\ /  \\         ",
        "__/  \\/            V  V    \\_______",
        "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~",
        "  .   .     .     .      .       ",
    ],
    [
        "      *        .          *       ",
        "   .      Y       Y               ",
        "         /|\\     /|\\      Y       ",
        "   Y    / | \\   / | \\    /|\\      ",
        "  /|\\     |       |     / | \\     ",
        "_/ | \\____|_______|_______|____",
        "   |      /   /   /   /          ",
        "      /   /   /   /   /          ",
    ],
    [
        "          .-~~~~~~~~-.            ",
        "      .-~~            ~~-.        ",
        "~~~~~~        ()          ~~~~~~~~",
        "    ~~~   ~~~    ~~~~   ~~~       ",
        " ~~    ~~~    ~~~    ~~~    ~~    ",
        "      _/|                 |\\_     ",
        "_____/  |_________________|  \\____",
        "         . . . . . . .           ",
    ],
    [
        "        .      +       .           ",
        "   +         .     .        +      ",
        "       |-|      _|_|_               ",
        "   _|_ | |  _|_|   |_|_   _|_      ",
        " _|   || |_|         | |_|   |_    ",
        "| []  || |  []  []   | | []   |   ",
        "|_____|__|___________|_|______|___",
        "  / / / / / / / / / / / / / /   ",
    ],
    [
        "        .         _.._             ",
        "   _..-~ ~-.._ .~    ~.   _.._    ",
        ".~            ~.      .~    ~.    ",
        "      _/\\_         _/\\_           ",
        "  _.-~    ~-._ _.-~    ~-._       ",
        "_/            V            \\______",
        "   .   .   .   .   .   .           ",
        " .   .   .   .   .   .   .         ",
    ],
    [
        "   *     .       *         .       ",
        "       .       .       *           ",
        " .        *        .        *      ",
        "          ___/\\___                 ",
        "     ____/        \\____            ",
        "____/                  \\_________",
        "     .----.      .----.             ",
        "____/______\\____/______\\__________",
    ],
    [
        "            \\ | /                  ",
        "          '-.;;;.-'                 ",
        "        -==  ;;;  ==-               ",
        "          .-';;;'-.                 ",
        "     _..-'  / | \\  '-.._          ",
        "__.-'______/__|__\\______'-.__     ",
        "   ////  ////  ////  ////           ",
        "__________________________________",
    ],
]


def load_mono_font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    names = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "C:/Windows/Fonts/consolab.ttf" if bold else "C:/Windows/Fonts/consola.ttf",
        "DejaVuSansMono-Bold.ttf" if bold else "DejaVuSansMono.ttf",
    ]
    for name in names:
        try:
            return ImageFont.truetype(name, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def ease_in_out(value: float) -> float:
    return value * value * (3 - 2 * value)


def cover_image(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    target_width, target_height = size
    scale = max(target_width / image.width, target_height / image.height)
    resized = image.resize((round(image.width * scale), round(image.height * scale)), Image.Resampling.LANCZOS)
    left = max(0, (resized.width - target_width) // 2)
    top = max(0, (resized.height - target_height) // 2)
    return resized.crop((left, top, left + target_width, top + target_height))


def draw_ascii_furniture(frame: Image.Image, frame_index: int) -> None:
    overlay = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    font = load_mono_font(13, bold=True)
    shadow = (2, 8, 18, 185)
    blue = (88, 166, 255, 210)
    white = (225, 240, 255, 205)
    table = """        __________________________________
       /_________________________________/|
      |                                 | |
      |_________________________________|/
          ||                       ||
          ||                       ||"""
    chair = """              .------------.
             /            /|
            /____________/ |
            |            | |
            |____________|/
                / || \\
               /  ||  \\"""
    drift = round(math.sin(frame_index * 0.34) * 3)
    draw.multiline_text((72 + drift, 350), table, font=font, fill=shadow, spacing=0)
    draw.multiline_text((70 + drift, 347), table, font=font, fill=blue, spacing=0)
    draw.multiline_text((690 - drift, 333), chair, font=font, fill=shadow, spacing=0)
    draw.multiline_text((687 - drift, 330), chair, font=font, fill=white, spacing=0)
    frame.alpha_composite(overlay)


def build_ascii_gallery_scene(stats: dict[str, Any]) -> tuple[Image.Image, list[int]]:
    scene_width, scene_height = 3060, 540
    if GLASS_BACKGROUND_PATH.exists():
        with Image.open(GLASS_BACKGROUND_PATH) as source:
            background = cover_image(source.convert("RGB"), (scene_width, scene_height))
    else:
        background = Image.new("RGB", (scene_width, scene_height), "#07101d")
    background = ImageEnhance.Brightness(background).enhance(0.62).convert("RGBA")
    veil = Image.new("RGBA", background.size, (3, 9, 22, 112))
    background.alpha_composite(veil)
    draw = ImageDraw.Draw(background, "RGBA")
    title_font = load_mono_font(14, bold=True)
    value_font = load_mono_font(31, bold=True)
    note_font = load_mono_font(11)
    art_font = load_mono_font(11, bold=True)
    centers = [270 + index * 420 for index in range(7)]
    metrics = [
        ("REPOSITORIES", f"{stats['repositories']} repositories", "OWNED PUBLIC PROJECTS"),
        ("STARS", f"{stats['stars']} stars", "CURRENT RECOGNITION"),
        ("FOLLOWERS", f"{stats['followers']} followers", "CURRENT AUDIENCE"),
        ("CONTRIBUTIONS", f"{stats['contributions_365d']} contributions", "TRAILING 365 DAYS"),
        ("COMMITS", f"{stats['commits_365d']} commits", "TRAILING 365 DAYS"),
        ("SOURCE LINES", f"{compact_number(stats['estimated_source_lines'])} source lines", "TRACKED CODE ESTIMATE"),
        ("GITHUB HOURS", f"{stats['estimated_github_hours']} GitHub hours", "ACTIVITY-BASED ESTIMATE"),
    ]
    draw.line((0, 390, scene_width, 390), fill=(120, 185, 255, 75), width=2)
    for index, (label, value, note) in enumerate(metrics):
        center = centers[index]
        left, top, right, bottom = center - 164, 52, center + 164, 356
        draw.rounded_rectangle((left + 7, top + 10, right + 7, bottom + 10), radius=22, fill=(0, 4, 14, 150))
        draw.rounded_rectangle((left, top, right, bottom), radius=22, fill=(12, 28, 52, 226), outline=(198, 227, 255, 178), width=2)
        draw.line((left + 24, top + 3, right - 24, top + 3), fill=(245, 250, 255, 150), width=2)
        draw.rounded_rectangle((left + 14, top + 56, right - 14, top + 216), radius=14, fill=(2, 10, 27, 158), outline=(88, 166, 255, 92), width=1)
        draw.text((left + 20, top + 20), f"{index + 1:02d} // {label}", font=title_font, fill=(158, 207, 255, 240))
        art = "\n".join(ASCII_LANDSCAPES[index])
        draw.multiline_text((left + 27, top + 72), art, font=art_font, fill=(88, 166, 255, 220), spacing=1)
        value_width = draw.textbbox((0, 0), value, font=value_font)[2]
        draw.text((center - value_width / 2, top + 232), value, font=value_font, fill=(242, 248, 255, 255))
        note_width = draw.textbbox((0, 0), note, font=note_font)[2]
        draw.text((center - note_width / 2, top + 277), note, font=note_font, fill=(141, 171, 205, 230))
        draw.line((left + 22, bottom - 13, right - 22, bottom - 13), fill=(88, 166, 255, 110), width=1)
    return background, centers


def render_ascii_stats_gallery(stats: dict[str, Any]) -> None:
    output_size = (1000, 460)
    scene, centers = build_ascii_gallery_scene(stats)
    frames: list[Image.Image] = []
    durations: list[int] = []
    previous_center = centers[0]
    frame_index = 0
    header_font = load_mono_font(12, bold=True)
    small_font = load_mono_font(10)
    updated = stats["updated_at_utc"].replace("T", " ").replace("+00:00", " UTC")
    for metric_index, target_center in enumerate(centers):
        for step in range(5):
            progress = ease_in_out((step + 1) / 5)
            camera_center = previous_center + (target_center - previous_center) * progress
            zoom = 1.04 + 0.46 * ease_in_out(min(1, (step + 1) / 4))
            crop_width = output_size[0] / zoom
            crop_height = output_size[1] / zoom
            center_y = 232
            left = max(0, min(scene.width - crop_width, camera_center - crop_width / 2))
            top = max(0, min(scene.height - crop_height, center_y - crop_height / 2))
            crop = scene.crop((round(left), round(top), round(left + crop_width), round(top + crop_height)))
            frame = crop.resize(output_size, Image.Resampling.LANCZOS).convert("RGBA")
            hud = Image.new("RGBA", output_size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(hud, "RGBA")
            draw.rounded_rectangle((13, 13, 986, 447), radius=26, fill=(220, 240, 255, 9), outline=(213, 235, 255, 125), width=2)
            draw.rounded_rectangle((28, 26, 420, 54), radius=12, fill=(235, 247, 255, 23), outline=(200, 230, 255, 62), width=1)
            draw.text((42, 34), "LIVE GITHUB STATISTICS // ASCII GALLERY", font=header_font, fill=(226, 241, 255, 245))
            draw.text((706, 35), f"REFRESHED {updated}", font=small_font, fill=(133, 170, 208, 235))
            for dot_index in range(7):
                x = 431 + dot_index * 21
                fill = (88, 166, 255, 245) if dot_index == metric_index else (139, 170, 202, 90)
                draw.ellipse((x, 424, x + 7, 431), fill=fill)
            sweep_x = (frame_index * 43) % output_size[0]
            draw.rectangle((sweep_x, 58, sweep_x + 2, 410), fill=(115, 190, 255, 18))
            for dust_index in range(18):
                x = (dust_index * 193 + frame_index * 17) % output_size[0]
                y = 68 + ((dust_index * 71 + frame_index * 9) % 330)
                draw.ellipse((x, y, x + 2, y + 2), fill=(195, 226, 255, 40))
            frame.alpha_composite(hud)
            draw_ascii_furniture(frame, frame_index)
            frames.append(frame.convert("P", palette=Image.Palette.ADAPTIVE, colors=72))
            durations.append(920 if step == 4 else 90)
            frame_index += 1
        previous_center = target_center
    GIF_PATH.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        GIF_PATH,
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,
        optimize=True,
        disposal=2,
    )


def update_readme_cache_key(cache_key: str) -> None:
    readme = README_PATH.read_text(encoding="utf-8")
    start = "<!-- LIVE_STATS_IMAGE_START -->"
    end = "<!-- LIVE_STATS_IMAGE_END -->"
    replacement = f"""{start}
<p align="center">
  <img src="./assets/ascii-stats-gallery.gif?version={cache_key}" width="100%" alt="Animated ASCII gallery of live GitHub statistics for Sha-Lai Berends: repositories, stars, followers, contributions, commits, estimated tracked source lines and estimated GitHub activity hours." />
</p>
{end}"""
    if start not in readme or end not in readme:
        raise RuntimeError("README live-stat markers were not found.")
    prefix, remainder = readme.split(start, 1)
    _, suffix = remainder.split(end, 1)
    README_PATH.write_text(prefix + replacement + suffix, encoding="utf-8")


def main() -> None:
    if not USERNAME or not TOKEN:
        raise RuntimeError("GITHUB_USERNAME and GITHUB_TOKEN are required.")
    user = fetch_user()
    repositories = fetch_owned_public_repositories()
    contributions = fetch_contribution_totals()
    lifetime = fetch_lifetime_contribution_totals(str(user["created_at"]))
    source_lines, counted_repos, failed_repos = estimate_tracked_source_lines(repositories)
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    stats: dict[str, Any] = {
        "username": USERNAME,
        "updated_at_utc": now.isoformat(),
        "repositories": len(repositories),
        "stars": sum(int(repo.get("stargazers_count", 0)) for repo in repositories),
        "followers": int(user.get("followers", 0)),
        "estimated_source_lines": source_lines,
        "estimated_github_hours": estimate_github_hours(lifetime),
        "lifetime_contribution_totals": lifetime,
        "source_line_repositories_counted": counted_repos,
        "source_line_repositories_failed": failed_repos,
        **contributions,
        "definitions": {
            "repositories": "Currently owned public repositories returned by the GitHub REST API.",
            "stars": "Current stargazer totals summed across owned public repositories.",
            "followers": "Current GitHub follower count.",
            "contributions_365d": "GitHub contribution-calendar total plus restricted contributions for the trailing 365 days.",
            "commits_365d": "Commit contributions reported by GitHub for the trailing 365 days.",
            "estimated_source_lines": "Current tracked source lines on default branches, excluding common vendor, generated, binary and documentation paths.",
            "estimated_github_hours": "Activity-based lifetime estimate: 1.5 hours per commit, 2 per pull request, 0.75 per review and 0.5 per issue. It is not literal logged-in or browser time.",
        },
    }
    SVG_PATH.parent.mkdir(parents=True, exist_ok=True)
    JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    SVG_PATH.write_text(render_svg(stats), encoding="utf-8")
    render_ascii_stats_gallery(stats)
    JSON_PATH.write_text(json.dumps(stats, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    update_readme_cache_key(now.strftime("%Y%m%d%H%M%S"))
    print(json.dumps(stats, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
