#!/usr/bin/env python3
"""Rewrite the README feed block and the docs feeds from the current evidence.

The block between <!-- FEED:BEGIN --> and <!-- FEED:END --> in README.md is regenerated
from `evidence/*.json`, so the repository's first screen is always the measured state of
the last run, never a hand-typed claim. Numbers are copied by key, not by hand.
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BEGIN, END = "<!-- FEED:BEGIN -->", "<!-- FEED:END -->"
PATTERN = re.compile(re.escape(BEGIN) + r".*?" + re.escape(END), re.S)


def j(p):
    f = ROOT / p
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}


def main() -> int:
    card = j("evidence/ggo_run_card.json")
    exp = j("evidence/ggo_experiment.json")
    est = j("evidence/score_estimator.json")
    lb = j("evidence/leaderboard_observation_2026-10-31.json")
    v, u, r = card.get("validator", {}), card.get("uniqueness", {}), card.get("raster", {})
    e, h = card.get("ledger_estimate", {}), card.get("holdout_dti", {})
    top1 = next((x["best_public_dti"] for x in lb.get("rows", []) if x["rank"] == 1), None)
    cleared = bool(card.get("verdict", "").startswith("promote")) and v.get("all_checks_passed")
    can_max = max((c or {}).get("max_auc", 0) for c in (exp.get("leakage_canary") or {"x": {"max_auc": 0}}).values())

    hold_rank = ", ".join(f"`{k.split('|')[0]}` {val['holdout_dti']:.4f}" for k, val in
                          sorted((exp.get("holdout") or {}).items(),
                                 key=lambda kv: -kv[1]["holdout_dti"])[:4]) or "no holdout rows"
    block = f"""{BEGIN}
## Current desk state — regenerated {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())} by `scripts/build_readme_feed.py`

**Decision: {'CLEARED FOR DOWNLOAD AND PORTAL UPLOAD' if cleared else 'NOT CLEARED — do not upload'}.**
Do not read any number below as an organizer-confirmed score: no submission was uploaded from this
environment, so no receipt exists.

| | |
|---|---|
| File | [`docs/downloads/{r.get('file', '—')}`](docs/downloads/{r.get('file', '')}) · sha256 `{(r.get('sha256') or '—')[:24]}…` |
| Format gates | {sum(1 for x in v.values() if x is True)}/{len(v)} true · all-pass {v.get('all_checks_passed')} |
| Estimate | **{e.get('value', '—')}** {e.get('label', '')} ({e.get('n_dots', '—')} dots), CV MAE {est.get('site_grouped_cv', {}).get('mae', '—')}, estimator Spearman {est.get('site_grouped_cv', {}).get('spearman', '—')} on {est.get('n_probes', '—')} public probes — an estimate, never a score |
| HOLDOUT-DTI | {h.get('value', '—')} ({h.get('withheld_positives', '—')} withheld positives, CI {h.get('ci95_mean_of_folds', '—')}); arm {h.get('arm', '—')} beats incumbent on the holdout: {h.get('beats_incumbent', '—')} |
| Uniqueness | {u.get('registry_comparators', '—')} sibling rasters censused, {len(u.get('blocked_by') or [])} blockers, worst informative 3-px overlap {(u.get('worst_informative_overlap') or {}).get('value', '—')}, worst |ρ| {(u.get('worst_abs_rho') or {}).get('value', '—')} |
| Leakage canary | max single-feature AUC {can_max} (bar 0.90) |
| Live public leaderboard | rank 1 = **{top1}** ({lb.get('observed_utc', '—')}); the brief's 0.4413 / 0.3195 are stale (IR-31-01) |

Holdout arms (pooled, best first): {hold_rank}.

Read next: [docs/index.html](docs/index.html) (one-click download desk),
[docs/executive-summary.html](docs/executive-summary.html) (nine-site table with estimates and
uniqueness), [docs/how-to-submit.html](docs/how-to-submit.html) (exact portal steps and the root
cause of `Predicted values must be in range [0, 1]`),
[docs/research.html](docs/research.html) (instruments, sources, census),
`evidence/ggo_run_card.json` (machine-readable run card).
{END}"""

    readme = ROOT / "README.md"
    txt = readme.read_text(encoding="utf-8")
    txt = PATTERN.sub(lambda _: block, txt, count=1) if PATTERN.search(txt) else (
        txt.split("\n", 1)[0] + "\n\n" + block + "\n\n" + txt.split("\n", 1)[1])
    readme.write_text(txt, encoding="utf-8")
    (ROOT / "docs" / "data" / "desk_feed.json").write_text(json.dumps(dict(
        built_utc=block.split("regenerated ")[1].split(" by")[0], cleared=cleared, raster=r,
        validator=v, uniqueness={k: u.get(k) for k in
                                 ("registry_comparators", "unique", "worst_informative_overlap", "worst_abs_rho")},
        estimate=e, holdout=h, leaderboard_top1=top1), indent=1) + "\n", encoding="utf-8")
    print("README feed block and docs/data/desk_feed.json rewritten")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
