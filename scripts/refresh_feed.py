#!/usr/bin/env python3
"""Refresh the public leaderboard observation, keeping an honest stale snapshot on failure."""
from __future__ import annotations

from datetime import datetime, timezone
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "registry/leaderboard.json"
URL = "https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/"
# The public page loads its table via this official HTMX fragment. The top-level
# HTML is only a shell, so parsing that document alone cannot refresh the score.
PARTIAL_URL = "https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard_partial/?page=1"


class Rows(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_row = False
        self.in_cell = False
        self.current = []
        self.buffer = []
        self.rows = []

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self.in_row = True
            self.current = []
        elif tag in {"th", "td"} and self.in_row:
            self.in_cell = True
            self.buffer = []

    def handle_data(self, data):
        if self.in_cell:
            self.buffer.append(data)

    def handle_endtag(self, tag):
        if tag in {"th", "td"} and self.in_cell:
            self.current.append(" ".join("".join(self.buffer).split()))
            self.in_cell = False
        elif tag == "tr" and self.in_row:
            self.rows.append(self.current)
            self.in_row = False


def parse_first_place(html: str) -> str:
    p = Rows()
    p.feed(html)
    for cells in p.rows:
        if len(cells) < 3 or not re.fullmatch(r"#\s*1|1", cells[0].strip()):
            continue
        # A valid row has one explicit fractional DTI; avoid timestamps or ranks.
        scores = [m.group(0) for cell in cells[1:]
                  for m in re.finditer(r"(?<![\d.])(?:0\.\d{3,}|1\.0{3,})(?![\d.])", cell)]
        if len(scores) != 1 or not 0 <= float(scores[0]) <= 1:
            raise ValueError("ambiguous or missing first-place DTI cell")
        return scores[0]
    raise ValueError("first-place leaderboard row missing; page may require login or have changed")


def refresh(path: Path = PATH) -> dict:
    try:
        old = json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        old = {"source": URL, "best_public_dti": None, "last_success_utc": None}
    now = datetime.now(timezone.utc).isoformat()
    old["last_attempt_utc"] = now
    try:
        request = urllib.request.Request(PARTIAL_URL, headers={
            "User-Agent": "GEMS-evidence-monitor/1.0", "HX-Request": "true"})
        with urllib.request.urlopen(request, timeout=20) as r:
            if r.geturl() != PARTIAL_URL:
                raise ValueError("leaderboard fragment redirected; not accepting login or another page")
            html = r.read(8_000_001)
        if len(html) > 8_000_000:
            raise ValueError("leaderboard response too large")
        score = parse_first_place(html.decode("utf-8", errors="replace"))
        old.update(source=URL, best_public_dti=score, last_success_utc=now, last_attempt_error=None,
                   evidence_class="PUBLIC-LEADERBOARD OBSERVATION; not an upload receipt or candidate score",
                   scope="Public top-ranked team only; hidden private scores and any candidate receipt are unavailable.")
    except Exception as exc:
        # Avoid publishing a traceback or secrets. Preserve but mark the prior value stale.
        old["last_attempt_error"] = type(exc).__name__ + ": " + str(exc)[:160]
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(old, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)
    return old


if __name__ == "__main__":
    result = refresh()
    if result.get("last_attempt_error"):
        print("Refresh failed; displaying the last successful observation as stale:", result["last_attempt_error"])
    else:
        print("Public leaderboard updated at", result["last_success_utc"])
