#!/usr/bin/env python3
"""Refresh selected public leaderboard rows, retaining a marked stale snapshot on failure.

This reads only the public DrivenData leaderboard fragment. It cannot identify a
submitted raster, access private scores, view a user's quota, or establish a receipt.
"""
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
TRACKED_RANKS = (1, 2, 25, 26, 48)


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


def parse_public_scores(html: str) -> dict[int, str]:
    """Parse unambiguous public rank/DTI cells from a leaderboard table fragment."""
    parser = Rows()
    parser.feed(html)
    scores: dict[int, str] = {}
    for cells in parser.rows:
        if not cells:
            continue
        rank_match = re.fullmatch(r"\s*#?\s*(\d+)\s*", cells[0])
        if not rank_match:
            continue
        rank = int(rank_match.group(1))
        # Rows can include a participant name and relative submission age. A DTI
        # is the single explicit three-or-more-decimal fraction in the row.
        values = [m.group(0) for cell in cells[1:]
                  for m in re.finditer(r"(?<![\d.])(?:0\.\d{3,}|1\.0{3,})(?![\d.])", cell)]
        if len(values) != 1 or not 0 <= float(values[0]) <= 1:
            raise ValueError(f"ambiguous or missing public DTI for rank {rank}")
        if rank in scores:
            raise ValueError(f"duplicate public rank {rank}")
        scores[rank] = values[0]
    if 1 not in scores:
        raise ValueError("first-place leaderboard row missing; page may require login or have changed")
    return scores


def parse_first_place(html: str) -> str:
    """Compatibility helper retained for callers that need only the leader."""
    return parse_public_scores(html)[1]


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
        with urllib.request.urlopen(request, timeout=20) as response:
            if response.geturl() != PARTIAL_URL:
                raise ValueError("leaderboard fragment redirected; not accepting login or another page")
            html = response.read(8_000_001)
        if len(html) > 8_000_000:
            raise ValueError("leaderboard response too large")
        scores = parse_public_scores(html.decode("utf-8", errors="replace"))
        old.update(source=URL, best_public_dti=scores[1], last_success_utc=now, last_attempt_error=None,
                   evidence_class="PUBLIC-LEADERBOARD OBSERVATION; not an upload receipt or candidate score",
                   scope="Captured public leaderboard rows only; private scores, project file identities, user quota, and receipts are unavailable.",
                   observation_time_precision="UTC timestamp recorded at refresh request start; the source does not expose a server observation time",
                   observation_method="Official public leaderboard HTMX fragment parsed automatically; the feed records requested ranks only.")
        for rank in TRACKED_RANKS:
            key = f"rank_{rank}_public_dti"
            if rank in scores:
                old[key] = scores[rank]
            else:
                # Do not carry forward a stale rank as though it were observed in
                # this refresh; the dated static snapshot remains separate.
                old.pop(key, None)
        old["captured_ranks"] = {str(rank): scores[rank] for rank in TRACKED_RANKS if rank in scores}
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
