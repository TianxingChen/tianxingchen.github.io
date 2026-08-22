#!/usr/bin/env python3
"""Refresh GitHub stars + Google Scholar citations into assets/metrics.json."""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "metrics.json"

GITHUB_USER = "TianxingChen"
EXTRA_REPOS = ["RoboTwin-Platform/RoboTwin"]
SCHOLAR_ID = "pvS8MH8AAAAJ"


def github_stars() -> int:
    total = 0
    page = 1
    while page <= 10:
        url = f"https://api.github.com/users/{GITHUB_USER}/repos"
        r = requests.get(
            url,
            params={"per_page": 100, "page": page, "type": "owner"},
            headers={"Accept": "application/vnd.github+json"},
            timeout=30,
        )
        r.raise_for_status()
        repos = r.json()
        if not repos:
            break
        total += sum(int(repo.get("stargazers_count") or 0) for repo in repos)
        if len(repos) < 100:
            break
        page += 1

    for full_name in EXTRA_REPOS:
        r = requests.get(
            f"https://api.github.com/repos/{full_name}",
            headers={"Accept": "application/vnd.github+json"},
            timeout=30,
        )
        r.raise_for_status()
        total += int(r.json().get("stargazers_count") or 0)
    return total



def scholar_citations_scrape() -> int | None:
    """Fallback HTML scrape when scholarly is unavailable."""
    url = f"https://scholar.google.com/citations?user={SCHOLAR_ID}&hl=en"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    }
    try:
        r = requests.get(url, headers=headers, timeout=30)
        r.raise_for_status()
        html = r.text
        patterns = [
            r"Cited by\s*([0-9][0-9,]*)",
            r"Citations</a></td><td[^>]*>\s*([0-9][0-9,]*)",
            r">Citations</[^>]*>\s*<[^>]*>\s*([0-9][0-9,]*)",
        ]
        for pat in patterns:
            m = re.search(pat, html, flags=re.I)
            if m:
                return int(m.group(1).replace(",", ""))
    except Exception as exc:  # noqa: BLE001
        print(f"scholar scrape failed: {exc}", file=sys.stderr)
    return None


def scholar_citations() -> int | None:
    try:
        from scholarly import scholarly
    except ImportError:
        print("scholarly not installed; falling back to scrape", file=sys.stderr)
        return scholar_citations_scrape()

    try:
        author = scholarly.search_author_id(SCHOLAR_ID)
        author = scholarly.fill(author, sections=["basics", "indices"])
        cited = author.get("citedby")
        if cited is not None:
            return int(cited)
    except Exception as exc:  # noqa: BLE001 — keep workflow resilient
        print(f"scholar fetch failed: {exc}", file=sys.stderr)

    return scholar_citations_scrape()


def main() -> int:
    prev = {}
    if OUT.exists():
        try:
            prev = json.loads(OUT.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            prev = {}

    stars = github_stars()
    citations = scholar_citations()
    if citations is None:
        citations = int(prev.get("citations") or 1406)

    data = {
        "github_stars": stars,
        "citations": citations,
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(data, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
