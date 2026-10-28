#!/usr/bin/env python3
"""KHD lane E2 — paired hide-and-recover holdout (HOLDOUT-DTI, quality gate only).

Evaluates on IDENTICAL folds: (a) the byte-exact GEMSDOE32 B2 support, (b) the KHD
candidate, (c) an equal-count strata-shuffled control.  Whole-segment buffered
withholding; visible faults masked pixel-exactly; b_visible_px=2.0 (B2 band) trim
against VISIBLE faults only.  Evaluator: gemsw.holdout (GEMSDOE32-HIDE-RECOVER
family, same instrument as the FCHD/THCS lanes for comparability).

KNOWN LIMITATION (documented, not fixed here): catalogue-holdout DTI is
anti-correlated with owner-reported scores for the dotted family (Spearman -0.146,
knowledge/protocol-revisions-2026-10-27.md R2).  This is a leak/quality gate; it
is NOT a leaderboard proxy and is never written as a score.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gemsw.holdout import load_holdout_context, evaluate_hide_and_recover  # noqa: E402

SESS = ROOT / ".cache" / "session"
RAW = ROOT / "data" / "raw"
SQRT5 = float(np.hypot(2, 1))


def main() -> int:
    t0 = time.time()
    ctx = load_holdout_context(RAW)

    khd = np.load(SESS / "khd-tomo_B37654_dots.npy")
    import rasterio
    with rasterio.open(ROOT / ".cache" / "focus" / "GEMSDOE32.tif") as ds:
        a = ds.read(1)
        b2 = np.isfinite(a) & (a > 0)

    # strata-shuffled control: same catalogue-distance band counts as KHD, random positions
    from scipy import ndimage as ndi
    stack = np.load(SESS / "fields.npy", mmap_mode="r")
    names = json.loads((SESS / "field_names.json").read_text())
    ix = {n: i for i, n in enumerate(names)}
    d_cat = np.asarray(stack[ix["d_cat"]], np.float32)
    rng = np.random.default_rng(99)
    ctrl = np.zeros_like(khd)
    edges = [2.24, 3.01, 5.01, 10.01, 20.01, 50.01, 1e9]
    lo = 2.24
    for hi in edges[1:]:
        stratum = ctx.foot & ~ctx.labels & (d_cat >= lo) & (d_cat < hi)
        k = int((khd & stratum).sum())
        if k:
            idxs = np.flatnonzero(stratum.ravel())
            sel = rng.choice(idxs, size=min(k, idxs.size), replace=False)
            ctrl.ravel()[sel] = True
        lo = hi

    out = {
        "label": "HOLDOUT-DTI (quality gate; NOT a leaderboard estimate — catalogue holdout is "
                 "anti-correlated with owner-reported dotted-family scores)",
        "evaluator": "gemsw.holdout.evaluate_hide_and_recover (GEMSDOE32-HIDE-RECOVER family)",
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "arms": {},
    }
    boots = {}
    for name, mask in (("B2_reference", b2), ("KHD_37654", khd), ("strata_control", ctrl)):
        hr = evaluate_hide_and_recover(mask & ctx.foot, ctx, b_visible_px=2.0, name=name)
        boots[name] = np.asarray(hr["_boots"])
        out["arms"][name] = {
            "n_dots": int(mask.sum()),
            "n_withheld_positives": hr["n_withheld_positives"],
            "pooled_dti": hr["pooled_dti"],
            "ci95_cluster_bootstrap": hr["ci95_cluster_bootstrap"],
            "evaluator_version": hr.get("evaluator_version"),
        }
        print(f"[holdout] {name:15s} HOLDOUT-DTI={hr['pooled_dti']:.5f} "
              f"CI={hr['ci95_cluster_bootstrap']} withheld={hr['n_withheld_positives']}", flush=True)

    # paired bootstrap on the difference KHD - B2 (shared folds; grid blocks)
    k = out["arms"]["KHD_37654"]["pooled_dti"]
    b = out["arms"]["B2_reference"]["pooled_dti"]
    delta = boots["KHD_37654"] - boots["B2_reference"]
    out["paired_delta_khd_minus_b2"] = {
        "value": k - b,
        "ci95": [float(np.percentile(delta, 2.5)), float(np.percentile(delta, 97.5))],
        "p_delta_le_0": float((delta <= 0).mean()),
    }
    (ROOT / "evidence" / "khd_holdout.json").write_text(json.dumps(out, indent=1, default=float))
    print(f"[holdout] paired delta (KHD-B2) = {out['paired_delta_khd_minus_b2']['value']:+.5f} "
          f"CI={out['paired_delta_khd_minus_b2']['ci95']}; wrote evidence/khd_holdout.json "
          f"in {time.time()-t0:.0f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
