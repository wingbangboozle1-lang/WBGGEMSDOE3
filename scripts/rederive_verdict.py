#!/usr/bin/env python3
"""Recompute this lane's verdict from the run card's own stored gate fields.

The promotion rule lives in exactly one place - `decide()` in `scripts/lane_ggo_release.py` - and
this script calls that same function on the numbers already recorded in
`evidence/ggo_run_card.json`. It exists so a verdict can be re-derived after the rule is tightened,
without re-running a 15-minute census and without anyone hand-typing a conclusion.

It changes only `performance_gate`, `verdict`, `verdict_reason`, `okay_to_submit` and the
provenance keys, and it refuses to run if any measured field it depends on is missing.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_gate():
    spec = importlib.util.spec_from_file_location("lane_ggo_release", ROOT / "scripts" / "lane_ggo_release.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["lane_ggo_release"] = mod
    spec.loader.exec_module(mod)          # module-level import only; main() is not invoked
    return mod


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--card", default=str(ROOT / "evidence" / "ggo_run_card.json"))
    ap.add_argument("--wait", type=int, default=0, help="seconds to wait for the card to appear")
    a = ap.parse_args()
    cp = Path(a.card)
    deadline = time.time() + a.wait
    while not cp.exists() and time.time() < deadline:
        time.sleep(10)
    if not cp.exists():
        print(f"refusing: {cp} does not exist", file=sys.stderr)
        return 2
    gate = load_gate()
    card = json.loads(cp.read_text())
    need = ("ledger_estimate", "focus_site_estimates", "uniqueness", "validator", "holdout_dti")
    missing = [k for k in need if k not in card]
    if missing:
        print(f"refusing: card is missing measured fields {missing}", file=sys.stderr)
        return 2
    est = card["ledger_estimate"]["value"]
    band = card["ledger_estimate"]["band"]
    best = max([f["owner_reported"] for f in card["focus_site_estimates"] if f.get("owner_reported")] or [0.0])
    perf, verdict, reason = gate.decide(
        card["uniqueness"]["unique"], bool(card["validator"]["all_checks_passed"]), est, band, best,
        card["holdout_dti"].get("value"), card["holdout_dti"].get("beats_incumbent"))
    card["performance_gate"] = perf
    card["verdict"] = verdict
    card["verdict_reason"] = reason
    card["okay_to_submit"] = verdict.startswith("promote")
    card["verdict_derived_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    card["verdict_derivation"] = ("recomputed from the card's own stored gate fields by "
                                 "scripts/rederive_verdict.py calling scripts/lane_ggo_release.py:decide()")
    cp.write_text(json.dumps(card, indent=1, allow_nan=False) + "\n")
    (ROOT / "docs" / "data" / "ggo_run_card.json").write_text(json.dumps(card, indent=1, allow_nan=False) + "\n")
    print(f"verdict -> {verdict}\n{reason}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
