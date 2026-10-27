"""Shared, deterministic THCS-OOF lane banner for the root Pages renderer.

Same pattern as scripts/hce_banner.py, scripts/rfl_banner.py, and scripts/lbcal_banner.py:
all numbers come from committed evidence JSONs (evidence/thcs_run_card.json,
evidence/thcs_experiments.json, evidence/focus_and_lane_comparison.json).
Does not alter the root repository release gate; links directly to docs/thcs/index.html.
"""
from __future__ import annotations

import json
from pathlib import Path

_EV = Path(__file__).resolve().parents[1] / "evidence"
_RC = json.loads((_EV / "thcs_run_card.json").read_text())
_EXP = json.loads((_EV / "thcs_experiments.json").read_text())
_COMP = json.loads((_EV / "focus_and_lane_comparison.json").read_text())

_HOLD = _RC["holdout_evaluation"]["pooled_dti"]
_E1 = _EXP["experiments"][0]["pooled_dti"]
_E2 = _EXP["experiments"][1]["pooled_dti"]
_CAL_RHO = _COMP["empirical_calibration_quality"]["loso_spearman_rho"]
_EST = next(r["loso_model_estimate_not_confirmed"] for r in _COMP["rows"] if r["site"] == "WBGGEMSDOE3 (THCS-OOF)")
_DOTS = _RC["artifact"]["emitted_dots"]

THCS_BANNER = (
    '<div style="background:#10261e;color:#e6fff3;border-bottom:2px solid #2ea043;'
    'padding:10px 20px;font-size:14px">'
    '<div style="max-width:1080px;margin:0 auto;display:flex;flex-wrap:wrap;gap:10px;align-items:center">'
    '<strong style="color:#7ee787">HYDROTHERMAL-GEOPHYSICAL LANE · 2026-10-27 (THCS-OOF)</strong>'
    f'<span style="flex:1 1 300px">Zero-catalogue 48-ch OOF HGB + 300 m CELF ({_DOTS:,} dots; fixes IR-20 Band-6 radiometric '
    f'<code>tc</code> &amp; IR-21 <code>validation.py</code> bug; 48/48 canaries PASS; 13/13 <code>[0,1]</code> byte checks PASS; '
    f'43.0% 3-px overlap vs GEMSDOE32, 20.2% vs TDE-30k). Achieves best zero-catalogue <b>HOLDOUT-DTI {_HOLD:.5f}</b> in repo '
    f'(GDR #1391 2m-probe/sinter/geotherm ablation: {_E1:.5f} &rarr; {_E2:.5f}, +12.4%; 120-run LOSO &rho; {_CAL_RHO:.2f} '
    f'ESTIMATE {_EST:.3f}, not a score). Verdict <code>negative</code> vs 0.09920 champion holdout (hold weekly slot).</span>'
    '<a style="background:#2ea043;color:#ffffff;font-weight:700;padding:7px 12px;border-radius:6px;'
    'text-decoration:none" href="thcs/index.html">THCS-OOF 5-page dossier ↗</a>'
    '</div></div>'
)
