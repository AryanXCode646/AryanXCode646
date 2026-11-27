"""GitHub profile telemetry updater. Standard library only."""

from __future__ import annotations

import html
import json
import os
import re
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

DEFAULT_USERNAME = "AryanXCode646"
DEFAULT_TIMEOUT = 30
MAX_DESCRIPTION_LEN = 82
ACTIVITY_LIMIT = 6

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
SVG = ROOT / "assets" / "profile-metrics.svg"
API = "https://api.github.com"

_NEXT_LINK_RE = re.compile(r'<([^>]+)>;\s*rel="next"')


def resolve_username() -> str:
    """Resolve the GitHub username according to precedence:
    1. PROFILE_USERNAME environment variable
    2. GITHUB_REPOSITORY_OWNER environment variable
    3. Verified default username 'AryanXCode646'
    """
    for env_var in ("PROFILE_USERNAME", "GITHUB_REPOSITORY_OWNER"):
        value = os.getenv(env_var, "").strip()
        if value:
            return value
    return DEFAULT_USERNAME


def utc_now_str() -> str:
    """Return current UTC timestamp formatted for profile telemetry."""
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")


def _build_headers(username: str) -> dict[str, str]:

def resolve_username() -> str:
    """Resolve the GitHub username using environment-variable precedence."""
    return (
        os.getenv("PROFILE_USERNAME")
        or os.getenv("GITHUB_REPOSITORY_OWNER")
        or "AryanSaxena20"
    )


def get_json(path: str):
    """Fetch JSON data from the GitHub API."""
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": f"{username}-profile-telemetry",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.getenv("GITHUB_TOKEN", "").strip()

    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def get_json_with_headers(
    path_or_url: str,
    *,
    timeout: int = DEFAULT_TIMEOUT,
) -> tuple[Any, dict[str, str]]:
    """Fetch JSON and response headers from the GitHub REST API."""
    url = path_or_url if path_or_url.startswith("https://") else f"{API}{path_or_url}"
    request = Request(url, headers=_build_headers(resolve_username()))
    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read()
            headers = {k.lower(): v for k, v in response.headers.items()} if response.headers else {}
            data = json.loads(raw.decode("utf-8"))
            return data, headers
    except HTTPError as exc:
        remaining = exc.headers.get("X-RateLimit-Remaining") if exc.headers else None
        reset = exc.headers.get("X-RateLimit-Reset") if exc.headers else None
        if exc.code in (403, 429) and remaining == "0":
            raise RuntimeError(
                f"GitHub API rate limit exceeded for {path_or_url} (reset={reset}): {exc}"
            ) from exc
        raise RuntimeError(f"GitHub API request failed for {path_or_url}: {exc}") from exc
    except (URLError, TimeoutError) as exc:
        raise RuntimeError(f"GitHub API network error for {path_or_url}: {exc}") from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"GitHub API returned invalid JSON for {path_or_url}: {exc}") from exc


def get_json(path_or_url: str, *, timeout: int = DEFAULT_TIMEOUT) -> Any:
    """Fetch parsed JSON from the GitHub REST API."""
    data, _ = get_json_with_headers(path_or_url, timeout=timeout)
    return data


def fetch_all_repos(username: str, *, timeout: int = DEFAULT_TIMEOUT) -> list[dict[str, Any]]:
    """Fetch all public owned repositories for a user, following pagination."""
    repos: list[dict[str, Any]] = []
    next_url: str | None = f"/users/{username}/repos?type=owner&sort=pushed&direction=desc&per_page=100"

    while next_url:
        page_data, headers = get_json_with_headers(next_url, timeout=timeout)
        if not isinstance(page_data, list):
            raise TypeError(f"Expected list of repositories from GitHub API, got {type(page_data).__name__}")
        repos.extend(page_data)
        link_header = headers.get("link", "")
        match = _NEXT_LINK_RE.search(link_header)
        next_url = match.group(1) if match else None

    return repos


def date_only(value: str | None) -> str:
    """Format an ISO-8601 timestamp as YYYY-MM-DD, or '—' when absent."""
    if not value:
        return "—"
    return datetime.fromisoformat(value).strftime("%Y-%m-%d")


def filter_active_owned_repos(repos: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return non-fork, non-archived repositories sorted by pushed_at descending."""
    active = [
        r for r in repos
        if not r.get("fork", False) and not r.get("archived", False)
    ]
    return sorted(active, key=lambda r: r.get("pushed_at") or "", reverse=True)


def escape_markdown_table_cell(text: str) -> str:
    """Sanitize arbitrary text for safe rendering inside a Markdown table cell."""
    normalized = " ".join(text.replace("\r", " ").replace("\n", " ").split())
    escaped = html.escape(normalized, quote=True)
    return escaped.replace("|", "\\|")
    request = Request(f"{API}{path}", headers=headers)

    try:
        with urlopen(request, timeout=30) as response:
            return json.load(response)
    except (HTTPError, URLError) as exc:
        raise RuntimeError(
            f"GitHub API request failed for {path}: {exc}"
        ) from exc


def date_only(value: str | None) -> str:
    """Convert an ISO timestamp into a date."""
    if not value:
        return "—"

    return datetime.fromisoformat(
        value.replace("Z", "+00:00")
    ).strftime("%Y-%m-%d")

def update_marker(text: str, start: str, end: str, content: str) -> str:
    """Replace content between unique start/end HTML comment markers."""
    start_count = text.count(start)
    end_count = text.count(end)
    if start_count == 0 or end_count == 0:
        raise RuntimeError(f"Missing marker block: {start}")
    if start_count > 1 or end_count > 1:
        raise RuntimeError(f"Duplicate marker block detected: {start}")

def update_marker(
    text: str,
    start: str,
    end: str,
    content: str,
) -> str:
    """Replace content between README markers."""
    pattern = re.compile(
        rf"({re.escape(start)}).*?({re.escape(end)})",
        flags=re.DOTALL,
    )

    replacement = f"\\1\n{content}\n\\2"
    result, count = pattern.subn(
        lambda _: replacement.replace("\\1", start).replace("\\2", end),
        text,
        count=1,
    )

    if count != 1:
        raise RuntimeError(f"Missing marker block: {start}")

    return result

    start_idx = text.index(start)
    end_idx = text.index(end)
    if end_idx < start_idx:
        raise RuntimeError(f"Malformed marker order: {start} appears after {end}")

    before = text[: start_idx + len(start)]
    after = text[end_idx:]
    return f"{before}\n{content}\n{after}"


def build_profile(profile: dict[str, Any], repos: list[dict[str, Any]], now: str) -> str:
    """Build the Markdown telemetry summary table."""
    username = resolve_username()
    owned = filter_active_owned_repos(repos)
    stars = sum(int(r.get("stargazers_count") or 0) for r in owned)
def build_profile(
    profile: dict,
    repos: list[dict],
    now: str,
) -> str:
    """Generate the profile telemetry Markdown table."""
    owned = [
        repo
        for repo in repos
        if not repo.get("fork", False)
        and not repo.get("archived", False)
    ]

    stars = sum(
        int(repo.get("stargazers_count", 0))
        for repo in owned
    )

    languages: dict[str, int] = {}

    for repo in owned:
        language = repo.get("language")
        if language:
            languages[language] = languages.get(language, 0) + 1

    top_languages = sorted(
        languages.items(),
        key=lambda item: (-item[1], item[0]),
    )[:5]

    lang_text = " · ".join(
        f"`{name}` ({count})"
        for name, count in top_languages
    ) or "—"

    if owned:
        latest_name = str(owned[0].get("name") or "—")
        latest_url = owned[0].get("html_url") or f"https://github.com/{username}/{latest_name}"
        latest_link = f"[`{latest_name}`]({latest_url})" if latest_name != "—" else "—"
    else:
        latest_link = "—"
    latest_name = owned[0]["name"] if owned else "—"

    latest_link = (
        f"[`{latest_name}`]"
        f"(https://github.com/{resolve_username()}/{latest_name})"
        if latest_name != "—"
        else "—"
    )

    return "\n".join(
        [
            "| Metric | Current Value |",
            "| :--- | :---: |",
            f"| **Public Repositories** | `{int(profile.get('public_repos') or 0):,}` |",
            f"| **Active Owned Repositories** | `{len(owned):,}` |",
            f"| **Stars (Active Owned, excl. forks)** | `★ {stars:,}` |",
            f"| **Followers** | `{int(profile.get('followers') or 0):,}` |",
            f"| **Following** | `{int(profile.get('following') or 0):,}` |",
            f"| **Latest Active Repository** | {latest_link} |",
            f"| **Top Languages (Active Owned)** | {lang_text} |",
            f"| **Telemetry Updated** | `{now}` |",
        ]
    )


def build_activity(repos: list[dict[str, Any]], now: str) -> str:
    """Build the Markdown recent repository activity table."""
    owned = filter_active_owned_repos(repos)[:ACTIVITY_LIMIT]
def build_activity(repos: list[dict], now: str) -> str:
    """Generate the recent repository activity table."""
    owned = [
        repo
        for repo in repos
        if not repo.get("fork", False)
        and not repo.get("archived", False)
    ][:6]

    rows = [
        "| Repository | Description | Language | Stars | Last Pushed |",
        "| :--- | :--- | :---: | :---: | :---: |",
    ]

    if not owned:
        rows.append("| — | No active non-fork repositories found. | — | — | — |")
    else:
        for repo in owned:
            raw_desc = str(repo.get("description") or "—")
            collapsed = " ".join(raw_desc.replace("\r", " ").replace("\n", " ").split())
            if len(collapsed) > MAX_DESCRIPTION_LEN:
                collapsed = collapsed[: MAX_DESCRIPTION_LEN - 3] + "..."

            name = escape_markdown_table_cell(str(repo.get("name") or "—"))
            url = str(repo.get("html_url") or "#")
            lang = str(repo.get("language") or "—")
            stars = int(repo.get("stargazers_count") or 0)
            pushed = date_only(repo.get("pushed_at"))

            rows.append(
                f"| **[{name}]({url})** | "
                f"{escape_markdown_table_cell(collapsed)} | "
                f"`{lang}` | "
                f"★ {stars:,} | "
                f"`{pushed}` |"
            )

    rows.append("")
    rows.append(f"> Automatically synchronized from GitHub on `{now}`.")
    return "\n".join(rows)


def build_svg(profile: dict[str, Any], repos: list[dict[str, Any]], now: str) -> str:
    """Generate an accessible SVG summary card for profile metrics."""
    username = resolve_username()
    owned = filter_active_owned_repos(repos)
    stars = sum(int(r.get("stargazers_count") or 0) for r in owned)
    for repo in owned:
        description = (
            (repo.get("description") or "—")
            .replace("\n", " ")
            .strip()
        )

        if len(description) > 82:
            description = description[:79] + "..."

        rows.append(
            f"| **[{repo['name']}]({repo['html_url']})** | "
            f"{html.escape(description)} | "
            f"`{repo.get('language') or '—'}` | "
            f"★ {repo.get('stargazers_count', 0)} | "
            f"`{date_only(repo.get('pushed_at'))}` |"
        )

    rows.extend(
        [
            "",
            f"> ⚡ Automatically synchronized from GitHub on `{now}`.",
        ]
    )

    return "\n".join(rows)


def build_svg(
    profile: dict,
    repos: list[dict],
    now: str,
) -> str:
    """Generate the profile metrics SVG."""
    owned = [
        repo
        for repo in repos
        if not repo.get("fork", False)
        and not repo.get("archived", False)
    ]

    stars = sum(
        int(repo.get("stargazers_count", 0))
        for repo in owned
    )

    values = [
        ("PUBLIC REPOS", f"{int(profile.get('public_repos') or 0):,}"),
        ("OWNED STARS", f"★ {stars:,}"),
        ("FOLLOWERS", f"{int(profile.get('followers') or 0):,}"),
        ("FOLLOWING", f"{int(profile.get('following') or 0):,}"),
    ]

    parts: list[str] = []
    start_x = 14
    card_width = 190
    gap = 12

    for index, (label, value) in enumerate(values):
        x = start_x + index * (card_width + gap)

        parts.append(
            f"""  <g transform="translate({x},30)">
    <rect width="190" height="104" rx="12" fill="#111827" stroke="#334155"/>
    <text x="18" y="34" font-family="ui-monospace, SFMono-Regular, Menlo, monospace"
          font-size="12" fill="#94a3b8">{html.escape(label, quote=True)}</text>
    <text x="18" y="76" font-family="ui-monospace, SFMono-Regular, Menlo, monospace"
          font-size="26" font-weight="700" fill="#f8fafc">{html.escape(value, quote=True)}</text>
  </g>"""
            f"""<g transform="translate({x},26)">
  <rect width="190" height="108" rx="14"
        fill="#111827" stroke="#334155"/>
  <text x="18" y="34"
        font-family="ui-monospace, SFMono-Regular, Menlo, monospace"
        font-size="13" fill="#94a3b8">{html.escape(label)}</text>
  <text x="18" y="78"
        font-family="ui-monospace, SFMono-Regular, Menlo, monospace"
        font-size="28" font-weight="700"
        fill="#f8fafc">{html.escape(value)}</text>
</g>"""
        )

    header = html.escape(f"{username.upper()} / PROFILE TELEMETRY", quote=True)
    footer = html.escape(f"last synchronized: {now} (stars exclude forks and archived repos)", quote=True)
    cards = "\n".join(parts)

    return f"""<svg xmlns="http://www.w3.org/2000/svg"
  width="820" height="190" viewBox="0 0 820 190" role="img" aria-labelledby="telemetry-title telemetry-desc">
  <title id="telemetry-title">{html.escape(username, quote=True)} GitHub Profile Telemetry</title>
  <desc id="telemetry-desc">Public repositories, active owned stars, followers, and following counts.</desc>
  <rect width="100%" height="100%" rx="16" fill="#020617"/>
  <text x="20" y="20"
        font-family="ui-monospace, SFMono-Regular, Menlo, monospace"
        font-size="11" fill="#64748b">{header}</text>
{cards}
  <text x="20" y="166"
        font-family="ui-monospace, SFMono-Regular, Menlo, monospace"
        font-size="11" fill="#64748b">{footer}</text>
        font-size="11" fill="#64748b">
    ARYANXCODE646 / PROFILE TELEMETRY
  </text>
  {''.join(parts)}
  <text x="20" y="166"
        font-family="ui-monospace, SFMono-Regular, Menlo, monospace"
        font-size="11" fill="#64748b">
    last synchronized: {html.escape(now)}
  </text>
</svg>
"""


def atomic_write_text(path: Path, content: str, encoding: str = "utf-8") -> None:
    """Write text to path atomically via a temporary file in the same directory."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding=encoding,
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as tmp:
            tmp_path = Path(tmp.name)
            tmp.write(content)
            tmp.flush()
            os.fsync(tmp.fileno())
        os.replace(tmp_path, path)
    except Exception:
        if tmp_path is not None and tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
        raise


def main() -> None:
    username = resolve_username()
    now = utc_now_str()
    profile = get_json(f"/users/{username}")
    repos = fetch_all_repos(username)
    """Fetch GitHub data and update the profile README and SVG."""
    now = datetime.now(timezone.utc).strftime(
        "%Y-%m-%d %H:%M UTC"
    )

    # Resolve once and reuse for both API requests.
    username = resolve_username()

    profile = get_json(f"/users/{username}")

    repos = get_json(
        f"/users/{username}/repos"
        "?type=owner&sort=pushed&direction=desc&per_page=100"
    )

    readme = README.read_text(encoding="utf-8")

    readme = update_marker(
        readme,
        "<!-- PROFILE:START -->",
        "<!-- PROFILE:END -->",
        build_profile(profile, repos, now),
    )

    readme = update_marker(
        readme,
        "<!-- ACTIVITY:START -->",
        "<!-- ACTIVITY:END -->",
        build_activity(repos, now),
    )

    atomic_write_text(README, readme)
    atomic_write_text(SVG, build_svg(profile, repos, now))
    print(f"Profile synchronized for {username}: {now}")
    README.write_text(readme, encoding="utf-8")
    SVG.write_text(
        build_svg(profile, repos, now),
        encoding="utf-8",
    )

    print(f"Profile synchronized: {now}")


if __name__ == "__main__":
    main()
