"""Shared, deterministic LBCAL lane banner for the root Pages renderer.

Same pattern as scripts/hce_banner.py and scripts/rfl_banner.py: one module, exact bytes
everywhere. The numbers come from the committed lane card evidence/lbcal_lane_decision.json,
so the banner is a pure function of evidence. It does not change the repository decision;
it surfaces an independent ESTIMATE for the selector. Details: docs/lbcal/index.html.
"""
from __future__ import annotations

import json
from pathlib import Path

_CARD = json.loads((Path(__file__).resolve().parents[1] / "evidence" / "lbcal_lane_decision.json").read_text())
_TDE = (_CARD.get("independent_estimate_of_main_cleared_file") or {}).get("lbcal_estimate")
_HOLD = _CARD["holdout_dti"]["pooled_dti"]
_RHO = _CARD["gate_concordance"]["spearman_holdout_vs_public"]

LBCAL_BANNER = (
    '<div style="background:#0d2a3d;color:#e6f4ff;border-bottom:2px solid #58a6ff;'
    'padding:10px 20px;font-size:14px">'
    '<div style="max-width:1080px;margin:0 auto;display:flex;flex-wrap:wrap;gap:10px;align-items:center">'
    '<strong style="color:#9fd0ff">INDEPENDENT ESTIMATE · 2026-10-27 (LBCAL lane)</strong>'
    '<span style="flex:1 1 300px">A leaderboard-calibrated density model (family-grouped CV &rho; 0.91 on 119 scored rasters) '
    f'estimates the cleared TDE-30k file at <b>{_TDE:.3f}</b>, against that lane&#39;s 0.207&ndash;0.269. These are ESTIMATES, '
    'not scores. Two inversions disagree on optimised designs, so treat expected scores as uncertain. The holdout gate tracks '
    f'the leaderboard at &rho; {_RHO:.2f}. The LBCAL file itself is negative (HOLDOUT-DTI {_HOLD:.4f}).</span>'
    '<a style="background:#58a6ff;color:#04121f;font-weight:700;padding:7px 12px;border-radius:6px;'
    'text-decoration:none" href="lbcal/index.html">LBCAL lane summary ↗</a>'
    '</div></div>'
)
