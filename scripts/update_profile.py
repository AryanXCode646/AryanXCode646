#!/usr/bin/env python3
"""GitHub profile telemetry updater. Standard library only."""

from __future__ import annotations

import html
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

USERNAME = "AryanXCode646"
ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
SVG = ROOT / "assets" / "profile-metrics.svg"
API = "https://api.github.com"


def get_json(path: str):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": f"{USERNAME}-profile-telemetry",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = Request(f"{API}{path}", headers=headers)
    try:
        with urlopen(request, timeout=30) as response:
            return __import__("json").load(response)
    except (HTTPError, URLError) as exc:
        raise RuntimeError(f"GitHub API request failed for {path}: {exc}") from exc


def date_only(value: str | None) -> str:
    if not value:
        return "—"
    return datetime.fromisoformat(value.replace("Z", "+00:00")).strftime("%Y-%m-%d")


def update_marker(text: str, start: str, end: str, content: str) -> str:
    pattern = re.compile(
        rf"({re.escape(start)}).*?({re.escape(end)})",
        flags=re.DOTALL,
    )
    result, count = pattern.subn(r"\1\n" + content + "\n" + r"\2", text, count=1)
    if count != 1:
        raise RuntimeError(f"Missing marker block: {start}")
    return result


def build_profile(profile: dict, repos: list[dict], now: str) -> str:
    owned = [
        r for r in repos
        if not r.get("fork", False) and not r.get("archived", False)
    ]

    stars = sum(int(r.get("stargazers_count", 0)) for r in owned)

    languages: dict[str, int] = {}
    for repo in owned:
        lang = repo.get("language")
        if lang:
            languages[lang] = languages.get(lang, 0) + 1

    top_languages = sorted(
        languages.items(),
        key=lambda item: (-item[1], item[0]),
    )[:5]

    lang_text = " · ".join(
        f"`{name}` ({count})" for name, count in top_languages
    ) or "—"

    latest_name = owned[0]["name"] if owned else "—"
    latest_link = (
        f"[`{latest_name}`](https://github.com/{USERNAME}/{latest_name})"
        if latest_name != "—"
        else "—"
    )

    return "\n".join(
        [
            "| Metric | Current Value |",
            "| :--- | :---: |",
            f"| **Public Repositories** | `{profile.get('public_repos', 0)}` |",
            f"| **Repository Stars** | `★ {stars:,}` |",
            f"| **Followers** | `{profile.get('followers', 0):,}` |",
            f"| **Following** | `{profile.get('following', 0):,}` |",
            f"| **Public Gists** | `{profile.get('public_gists', 0):,}` |",
            f"| **Latest Active Repository** | {latest_link} |",
            f"| **Top Repository Languages** | {lang_text} |",
            f"| **Telemetry Updated** | `{now}` |",
        ]
    )


def build_activity(repos: list[dict], now: str) -> str:
    owned = [
        r for r in repos
        if not r.get("fork", False) and not r.get("archived", False)
    ][:6]

    rows = [
        "| Repository | Description | Language | Stars | Last Pushed |",
        "| :--- | :--- | :---: | :---: | :---: |",
    ]

    for repo in owned:
        description = (repo.get("description") or "—").replace("\n", " ").strip()
        if len(description) > 82:
            description = description[:79] + "..."

        rows.append(
            f"| **[{repo['name']}]({repo['html_url']})** | "
            f"{html.escape(description)} | "
            f"`{repo.get('language') or '—'}` | "
            f"★ {repo.get('stargazers_count', 0)} | "
            f"`{date_only(repo.get('pushed_at'))}` |"
        )

    rows.append("")
    rows.append(
        f"> ⚡ Automatically synchronized from GitHub on `{now}`."
    )
    return "\n".join(rows)


def build_svg(profile: dict, repos: list[dict], now: str) -> str:
    owned = [
        r for r in repos
        if not r.get("fork", False) and not r.get("archived", False)
    ]
    stars = sum(int(r.get("stargazers_count", 0)) for r in owned)

    values = [
        ("REPOSITORIES", str(profile.get("public_repos", 0))),
        ("STARS", f"★ {stars}"),
        ("FOLLOWERS", str(profile.get("followers", 0))),
        ("FOLLOWING", str(profile.get("following", 0))),
    ]

    parts = []
    start_x = 14
    card_w = 190
    gap = 12

    for index, (label, value) in enumerate(values):
        x = start_x + index * (card_w + gap)
        parts.append(
            f"""<g transform="translate({x},26)">
  <rect width="190" height="108" rx="14" fill="#111827" stroke="#334155"/>
  <text x="18" y="34" font-family="ui-monospace, SFMono-Regular, Menlo, monospace"
        font-size="13" fill="#94a3b8">{html.escape(label)}</text>
  <text x="18" y="78" font-family="ui-monospace, SFMono-Regular, Menlo, monospace"
        font-size="28" font-weight="700" fill="#f8fafc">{html.escape(value)}</text>
</g>"""
        )

    return f"""<svg xmlns="http://www.w3.org/2000/svg"
  width="820" height="190" viewBox="0 0 820 190">
  <rect width="100%" height="100%" rx="18" fill="#020617"/>
  <text x="20" y="18"
        font-family="ui-monospace, SFMono-Regular, Menlo, monospace"
        font-size="11" fill="#64748b">ARYANXCODE646 / PROFILE TELEMETRY</text>
  {''.join(parts)}
  <text x="20" y="166"
        font-family="ui-monospace, SFMono-Regular, Menlo, monospace"
        font-size="11" fill="#64748b">last synchronized: {html.escape(now)}</text>
</svg>
"""


def main() -> None:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    profile = get_json(f"/users/{USERNAME}")
    repos = get_json(
        f"/users/{USERNAME}/repos?type=owner&sort=pushed&direction=desc&per_page=100"
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

    README.write_text(readme, encoding="utf-8")
    SVG.write_text(build_svg(profile, repos, now), encoding="utf-8")
    print(f"Profile synchronized: {now}")


if __name__ == "__main__":
    main()
