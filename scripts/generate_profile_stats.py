#!/usr/bin/env python3
"""Generate a repository-owned SVG containing live GitHub profile statistics.

Metrics:
- Public repositories currently owned by the configured user.
- Stars across currently owned public repositories.
- Followers.
- Contributions during the trailing 365 days.
- Commit contributions during the trailing 365 days.
- Estimated tracked source-code lines across public, non-fork, non-archived repositories.

The line count is intentionally labelled as an estimate. It counts current files on each
default branch, excludes likely generated/vendor paths, and does not represent historical
added/deleted lines.
"""

from __future__ import annotations

import datetime as dt
import html
import json
import os
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

USERNAME = os.environ.get("GITHUB_USERNAME", "berendsshalai").strip()
TOKEN = os.environ.get("GITHUB_TOKEN", "").strip()
ROOT = Path(__file__).resolve().parents[1]
SVG_PATH = ROOT / "assets" / "github-stats.svg"
JSON_PATH = ROOT / "data" / "github-stats.json"
README_PATH = ROOT / "README.md"

API_ROOT = "https://api.github.com"
GRAPHQL_URL = "https://api.github.com/graphql"

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

EXCLUDED_SUFFIXES = {
    ".lock", ".map", ".min.css", ".min.js", ".svg",
}

MAX_FILE_BYTES = 2_000_000


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
            {
                "type": "owner",
                "sort": "full_name",
                "direction": "asc",
                "per_page": 100,
                "page": page,
            }
        )
        data, _ = request_json(
            f"{API_ROOT}/users/{urllib.parse.quote(USERNAME)}/repos?{query}"
        )
        if not isinstance(data, list):
            raise GitHubAPIError("Unexpected repository response shape.")

        repositories.extend(item for item in data if isinstance(item, dict))

        if len(data) < 100:
            break
        page += 1

    return repositories


def fetch_contribution_totals() -> dict[str, int]:
    end = dt.datetime.now(dt.timezone.utc)
    start = end - dt.timedelta(days=365)

    query = """
    query ProfileContributions($login: String!, $from: DateTime!, $to: DateTime!) {
      user(login: $login) {
        contributionsCollection(from: $from, to: $to) {
          totalCommitContributions
          totalIssueContributions
          totalPullRequestContributions
          totalPullRequestReviewContributions
          restrictedContributionsCount
          contributionCalendar {
            totalContributions
          }
        }
      }
    }
    """

    payload = {
        "query": query,
        "variables": {
            "login": USERNAME,
            "from": start.isoformat().replace("+00:00", "Z"),
            "to": end.isoformat().replace("+00:00", "Z"),
        },
    }
    data, _ = request_json(GRAPHQL_URL, method="POST", payload=payload)

    if not isinstance(data, dict):
        raise GitHubAPIError("Unexpected GraphQL response shape.")
    if data.get("errors"):
        raise GitHubAPIError(f"GraphQL errors: {data['errors']}")

    user = data.get("data", {}).get("user")
    if not user:
        raise GitHubAPIError(f"GitHub user '{USERNAME}' was not found.")

    collection = user["contributionsCollection"]
    calendar_total = int(collection["contributionCalendar"]["totalContributions"])
    restricted_total = int(collection.get("restrictedContributionsCount", 0))

    return {
        "contributions_365d": calendar_total + restricted_total,
        "commits_365d": int(collection.get("totalCommitContributions", 0)),
        "issues_365d": int(collection.get("totalIssueContributions", 0)),
        "pull_requests_365d": int(collection.get("totalPullRequestContributions", 0)),
        "reviews_365d": int(collection.get("totalPullRequestReviewContributions", 0)),
    }


def is_countable_source(path: Path) -> bool:
    lowered_parts = {part.lower() for part in path.parts}
    if lowered_parts & EXCLUDED_PARTS:
        return False

    lower_name = path.name.lower()
    if any(lower_name.endswith(suffix) for suffix in EXCLUDED_SUFFIXES):
        return False

    return path.suffix.lower() in SOURCE_EXTENSIONS


def count_text_lines(path: Path) -> int:
    if not path.is_file() or path.stat().st_size > MAX_FILE_BYTES:
        return 0

    raw = path.read_bytes()
    if b"\x00" in raw[:8192]:
        return 0

    text = raw.decode("utf-8", errors="ignore")
    if not text:
        return 0
    return text.count("\n") + (0 if text.endswith("\n") else 1)


def estimate_tracked_source_lines(
    repositories: list[dict[str, Any]],
) -> tuple[int, int, list[str]]:
    total_lines = 0
    counted_repositories = 0
    failed_repositories: list[str] = []

    candidates = [
        repo
        for repo in repositories
        if not repo.get("fork")
        and not repo.get("archived")
        and not repo.get("disabled")
        and repo.get("clone_url")
    ]

    with tempfile.TemporaryDirectory(prefix="profile-loc-") as temp_root:
        temp_root_path = Path(temp_root)

        for index, repo in enumerate(candidates):
            name = str(repo.get("name", f"repo-{index}"))
            destination = temp_root_path / f"{index:03d}-{name}"

            command = [
                "git",
                "clone",
                "--quiet",
                "--depth",
                "1",
                "--single-branch",
                str(repo["clone_url"]),
                str(destination),
            ]

            try:
                subprocess.run(
                    command,
                    check=True,
                    timeout=120,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                    text=True,
                )
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                failed_repositories.append(name)
                continue

            repo_lines = 0
            for path in destination.rglob("*"):
                relative = path.relative_to(destination)
                if is_countable_source(relative):
                    try:
                        repo_lines += count_text_lines(path)
                    except (OSError, UnicodeError):
                        continue

            total_lines += repo_lines
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
    safe_label = html.escape(label)
    safe_value = html.escape(compact_number(value))
    safe_note = html.escape(note)

    return f"""
      <g transform="translate({x} {y})">
        <rect width="292" height="78" rx="12" class="metric-bg"/>
        <text x="18" y="25" class="metric-label">{safe_label}</text>
        <text x="18" y="56" class="metric-value">{safe_value}</text>
        <text x="274" y="56" text-anchor="end" class="metric-note">{safe_note}</text>
      </g>
    """


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
    ]

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="290" viewBox="0 0 1000 290" role="img" aria-labelledby="title description">
  <title id="title">Live GitHub statistics for {username}</title>
  <desc id="description">Current repositories, stars and followers; trailing 365 day contributions and commits; and estimated source lines.</desc>
  <style>
    .background {{ fill: #0d1117; stroke: #30363d; }}
    .metric-bg {{ fill: #161b22; stroke: #30363d; }}
    .heading {{ fill: #f0f6fc; font: 700 22px ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }}
    .subheading {{ fill: #8b949e; font: 400 12px ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }}
    .metric-label {{ fill: #8b949e; font: 600 12px ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; letter-spacing: .6px; text-transform: uppercase; }}
    .metric-value {{ fill: #58a6ff; font: 700 25px ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }}
    .metric-note {{ fill: #6e7681; font: 400 10px ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }}
  </style>

  <rect x="1" y="1" width="998" height="288" rx="16" class="background"/>
  <text x="28" y="38" class="heading">{username} / GitHub activity</text>
  <text x="28" y="62" class="subheading">Repository-owned statistics / refreshed {updated}</text>
  {''.join(cards)}
</svg>
"""


def update_readme_cache_key(cache_key: str) -> None:
    readme = README_PATH.read_text(encoding="utf-8")
    start = "<!-- LIVE_STATS_IMAGE_START -->"
    end = "<!-- LIVE_STATS_IMAGE_END -->"

    replacement = f"""{start}
<p align="center">
  <img src="./assets/github-stats.svg?version={cache_key}" width="100%" alt="Live GitHub statistics for Sha-Lai Berends: repositories, stars, followers, contributions, commits and estimated tracked source lines." />
</p>
{end}"""

    if start not in readme or end not in readme:
        raise RuntimeError("README live-stat markers were not found.")

    prefix, remainder = readme.split(start, 1)
    _, suffix = remainder.split(end, 1)
    README_PATH.write_text(prefix + replacement + suffix, encoding="utf-8")


def main() -> None:
    if not USERNAME:
        raise RuntimeError("GITHUB_USERNAME must not be empty.")
    if not TOKEN:
        raise RuntimeError("GITHUB_TOKEN is required for reliable API and GraphQL access.")

    user = fetch_user()
    repositories = fetch_owned_public_repositories()
    contributions = fetch_contribution_totals()
    source_lines, counted_repos, failed_repos = estimate_tracked_source_lines(repositories)

    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    stats: dict[str, Any] = {
        "username": USERNAME,
        "updated_at_utc": now.isoformat(),
        "repositories": len(repositories),
        "stars": sum(int(repo.get("stargazers_count", 0)) for repo in repositories),
        "followers": int(user.get("followers", 0)),
        "estimated_source_lines": source_lines,
        "source_line_repositories_counted": counted_repos,
        "source_line_repositories_failed": failed_repos,
        **contributions,
        "definitions": {
            "repositories": "Currently owned public repositories returned by the GitHub REST API.",
            "stars": "Current stargazer totals summed across owned public repositories.",
            "followers": "Current GitHub follower count.",
            "contributions_365d": "GitHub contribution-calendar total plus restricted contribution count for the trailing 365 days.",
            "commits_365d": "Commit contributions reported by GitHub for the trailing 365 days.",
            "estimated_source_lines": "Current tracked source-code lines on cloned default branches, excluding common vendor, generated, binary and documentation paths.",
        },
    }

    SVG_PATH.parent.mkdir(parents=True, exist_ok=True)
    JSON_PATH.parent.mkdir(parents=True, exist_ok=True)

    SVG_PATH.write_text(render_svg(stats), encoding="utf-8")
    JSON_PATH.write_text(json.dumps(stats, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    update_readme_cache_key(now.strftime("%Y%m%d%H%M%S"))

    print(json.dumps(stats, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
