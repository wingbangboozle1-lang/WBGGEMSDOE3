#!/usr/bin/env python3
"""Refresh a non-authoritative public monitoring feed for GitHub Pages.

This never updates a submission verdict or treats a leaderboard row as a
submission receipt. Failure is explicit; old observations retain their date.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import tempfile
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[1]
LEADERBOARD = "https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/"


class Tables(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables: list[list[list[str]]] = []
        self.table: list[list[str]] | None = None
        self.row: list[str] | None = None
        self.cell: list[str] | None = None

    def handle_starttag(self, tag, attrs):
        if tag == "table" and self.table is None:
            self.table = []
        elif tag == "tr" and self.table is not None:
            self.row = []
        elif tag in ("td", "th") and self.row is not None:
            self.cell = []
        elif tag == "br" and self.cell is not None:
            self.cell.append(" ")

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.cell is not None and self.row is not None:
            self.row.append(" ".join("".join(self.cell).split()))
            self.cell = None
        elif tag == "tr" and self.row is not None and self.table is not None:
            if self.row:
                self.table.append(self.row)
            self.row = None
        elif tag == "table" and self.table is not None:
            self.tables.append(self.table)
            self.table = None


def parse_top_score(html: str) -> str:
    parser = Tables()
    parser.feed(html)
    for table in parser.tables:
        if not table:
            continue
        headers = [x.lower().replace("\u00a0", " ") for x in table[0]]
        if not any("rank" in x for x in headers):
            continue
        cols = [i for i, x in enumerate(headers) if "tversky" in x]
        if len(cols) != 1:
            continue
        col = cols[0]
        for row in table[1:]:
            if len(row) <= col or not re.fullmatch(r"\s*#?1\s*", row[0]):
                continue
            value = row[col].strip()
            if re.fullmatch(r"(?:0(?:\.\d+)?|1(?:\.0+)?)", value):
                return value
        raise ValueError("leaderboard table lacks an unambiguous rank-one score")
    raise ValueError("leaderboard table not found")


class SafeRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        parsed = urlparse(newurl)
        if parsed.scheme != "https" or parsed.hostname not in {"api.github.com", "www.drivendata.org"}:
            raise ValueError("untrusted redirect refused")
        # Never forward a GitHub token to DrivenData or another host.
        if parsed.hostname != urlparse(req.full_url).hostname:
            raise ValueError("cross-host redirect refused")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


OPENER = build_opener(SafeRedirect())


def retrieve(url: str, *, github: bool = False) -> str:
    host = urlparse(url)
    allowed = "api.github.com" if github else "www.drivendata.org"
    if host.scheme != "https" or host.netloc != allowed:
        raise ValueError("unexpected host")
    headers = {"User-Agent": "WBGGEMSDOE3-public-status/1.0", "Accept": "application/vnd.github+json" if github else "text/html"}
    if github:
        token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
        if token:
            headers["Authorization"] = "Bearer " + token
    with OPENER.open(Request(url, headers=headers), timeout=20) as response:
        data = response.read(8 * 1024 * 1024 + 1)
    if len(data) > 8 * 1024 * 1024:
        raise ValueError("response too large")
    return data.decode("utf-8")


def refresh(previous: dict | None = None) -> dict:
    now = dt.datetime.now(dt.timezone.utc).isoformat()
    old = (previous or {}).get("leaderboard", {})
    board = {"status": "unavailable", "source": LEADERBOARD, "checked_utc": now,
             "top_value": old.get("top_value"), "observed_utc": old.get("observed_utc"),
             "evidence_class": "PUBLIC LEADERBOARD; not a submission receipt"}
    try:
        board["top_value"] = parse_top_score(retrieve(LEADERBOARD))
        board["observed_utc"] = now
        board["status"] = "current"
    except Exception as exc:  # fail closed without exposing URLs, credentials, or response text
        board["status"] = "stale" if board["top_value"] is not None else "unavailable"
        board["error_type"] = type(exc).__name__
    priorities = json.loads((ROOT / "config/priority-rasters.json").read_text())
    repositories = []
    for item in priorities:
        if item["role"] != "historical_priority":
            continue
        entry = {"site": "GEMSDOE" + item["id"], "audited_ref": item["ref"],
                 "latest_ref": None, "status": "unavailable"}
        try:
            url = f"https://api.github.com/repos/{item['repo']}/commits/main"
            payload = json.loads(retrieve(url, github=True))
            commit = payload.get("sha", "")
            if not re.fullmatch(r"[0-9a-f]{40}", commit):
                raise ValueError("invalid commit")
            entry["latest_ref"] = commit
            entry["status"] = "unchanged" if commit == item["ref"] else "changed_since_audit"
        except Exception as exc:
            entry["error_type"] = type(exc).__name__
        repositories.append(entry)
    return {"schema": "public-monitor-v1", "checked_utc": now, "leaderboard": board,
            "repositories": repositories,
            "warning": "A changed or inaccessible repository is not automatically re-audited. This monitor cannot approve a submission."}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "docs/data/public-feed.json")
    args = parser.parse_args()
    try:
        previous = json.loads(args.output.read_text())
    except (OSError, ValueError):
        previous = {}
    result = refresh(previous)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    # Atomic publication: a truncated feed should never look current.
    fd, name = tempfile.mkstemp(prefix=".feed-", suffix=".json", dir=args.output.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump(result, stream, indent=2, allow_nan=False)
            stream.write("\n")
        os.replace(name, args.output)
    finally:
        Path(name).unlink(missing_ok=True)
    print(f"Leaderboard: {result['leaderboard']['status']}; source refs checked: {len(result['repositories'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
