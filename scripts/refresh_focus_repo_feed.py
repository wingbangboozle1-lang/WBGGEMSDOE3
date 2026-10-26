#!/usr/bin/env python3
"""Refresh a read-only feed of public GitHub commit metadata for the nine focus sites.

This deliberately does not scrape owner-reported scores, contact DrivenData, fetch TIFs,
or infer competition results. It uses GitHub's public REST API without credentials.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

OWNER = "buffedlizard55-lab"
FOCUS_REPOS = (
    "GEMSDOE24",
    "GEMSDOE25",
    "GEMSDOE27",
    "GEMSDOE28",
    "GEMSDOE30",
    "GEMSDOE31",
    "GEMSDOE32",
    "GEMSDOE33",
    "GEMSDOE36",
)
DEFAULT_OUTPUT = Path(__file__).resolve().parents[1] / "docs" / "data" / "focus-repo-feed.json"


def _get_json(url: str, timeout: float = 15.0) -> dict[str, Any]:
    request = Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "WBGGEMSDOE3-focus-repo-feed/1.0",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        method="GET",
    )
    with urlopen(request, timeout=timeout) as response:
        if response.status != 200:
            raise RuntimeError(f"GitHub API returned HTTP {response.status}")
        return json.loads(response.read().decode("utf-8"))


def fetch_commit(repo: str) -> dict[str, Any]:
    url = f"https://api.github.com/repos/{OWNER}/{repo}/commits/main"
    checked = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    try:
        data = _get_json(url)
        commit = data.get("commit", {})
        details = commit.get("committer") or commit.get("author") or {}
        return {
            "repository": repo,
            "status": "ok",
            "branch": "main",
            "commit_sha": data.get("sha"),
            "committed_at_utc": details.get("date"),
            "message": (commit.get("message") or "").splitlines()[0],
            "url": data.get("html_url"),
            "checked_at_utc": checked,
        }
    except (HTTPError, URLError, TimeoutError, RuntimeError, ValueError, KeyError) as exc:
        return {
            "repository": repo,
            "status": "error",
            "branch": "main",
            "commit_sha": None,
            "committed_at_utc": None,
            "message": None,
            "url": f"https://github.com/{OWNER}/{repo}",
            "checked_at_utc": checked,
            "error": f"{type(exc).__name__}: {exc}",
        }


def build_feed() -> dict[str, Any]:
    checked_at = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    repositories = [fetch_commit(repo) for repo in FOCUS_REPOS]
    successes = sum(row["status"] == "ok" for row in repositories)
    return {
        "schema_version": 1,
        "feed_type": "public GitHub repository activity only; not an official competition score feed",
        "owner": OWNER,
        "checked_at_utc": checked_at,
        "repositories_checked": len(repositories),
        "repositories_updated": successes,
        "score_values_added": False,
        "official_leaderboard": {
            "status": "not checked",
            "reason": "DrivenData is outside this repository's automated public-GitHub feed; no authenticated competition session is available.",
        },
        "items": repositories,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT, help="JSON output path")
    args = parser.parse_args()
    feed = build_feed()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(feed, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(args.out),
        "checked_at_utc": feed["checked_at_utc"],
        "repositories_updated": feed["repositories_updated"],
        "repositories_checked": feed["repositories_checked"],
        "official_leaderboard": feed["official_leaderboard"]["status"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
