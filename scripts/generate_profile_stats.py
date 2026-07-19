#!/usr/bin/env python3
"""Generate repository-owned live GitHub statistics and profile visuals.

The GitHub-hours figure is an activity-based estimate, not literal browser time. It
uses lifetime GitHub contribution totals with documented weights so the number is
transparent, repeatable and automatically refreshed.
"""

from __future__ import annotations

import argparse
import datetime as dt
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

from ascii_stats_room import render_ascii_statistics_room

USERNAME = os.environ.get("GITHUB_USERNAME", "berendsshalai").strip()
TOKEN = os.environ.get("GITHUB_TOKEN", "").strip()
ROOT = Path(__file__).resolve().parents[1]
JSON_PATH = ROOT / "data" / "github-stats.json"
README_PATH = ROOT / "README.md"

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


def update_readme_cache_key(cache_key: str) -> None:
    readme = README_PATH.read_text(encoding="utf-8")
    start = "<!-- LIVE_STATS_IMAGE_START -->"
    end = "<!-- LIVE_STATS_IMAGE_END -->"
    replacement = f"""{start}
<p align="center">
  <picture>
    <source media="(prefers-reduced-motion: reduce)" srcset="./assets/ascii-stats-gallery-color-transparent-static.png?version={cache_key}">
    <img src="./assets/ascii-stats-gallery-color-transparent.gif?version={cache_key}" width="100%" alt="Cinematic Emerald Systems Observatory presenting live GitHub statistics through illuminated glass telemetry, a volumetric repository globe, a studio-quality desk and an observatory chair overlooking deep space." />
  </picture>
</p>
{end}"""
    if start not in readme or end not in readme:
        raise RuntimeError("README live-stat markers were not found.")
    prefix, remainder = readme.split(start, 1)
    _, suffix = remainder.split(end, 1)
    README_PATH.write_text(prefix + replacement + suffix, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--render-existing", action="store_true", help="Render using the last validated public statistics JSON without calling GitHub.")
    parser.add_argument("--contact-sheet", type=Path, help="Optional local-only contact sheet path for visual QA.")
    args = parser.parse_args()
    if args.render_existing:
        stats = json.loads(JSON_PATH.read_text(encoding="utf-8"))
        results = render_ascii_statistics_room(stats, ROOT, contact_sheet=args.contact_sheet)
        cache_key = dt.datetime.fromisoformat(stats["updated_at_utc"]).strftime("%Y%m%d%H%M%S")
        update_readme_cache_key(cache_key)
        print(json.dumps({"statistics": stats, "renders": results}, indent=2, sort_keys=True))
        return
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
    JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    render_ascii_statistics_room(stats, ROOT, contact_sheet=args.contact_sheet)
    JSON_PATH.write_text(json.dumps(stats, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    update_readme_cache_key(now.strftime("%Y%m%d%H%M%S"))
    print(json.dumps(stats, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
