#!/usr/bin/env python3
"""Select (catalogue buffer x probability floor) by the estimator trained on real scores.

Session 2026-10-31.  The quadrant holdout cannot rank these variants: its truth
IS the public catalogue, so it rewards dots that sit on top of already-mapped
traces, which is exactly what the leaderboard cannot reward.  The only direct
evidence about designs at this scale is the 118-raster owner-reported ledger, so
the selection uses the site-grouped, leave-one-site-out-calibrated estimator
(E2) built in session_2026_10_31_estimate.py, restricted to variants inside the
measured successful envelope (35k-48k dots, mean_dots_within_3px <= 3.4).

Evidence class: ESTIMATE.  Selection on an estimator with leave-one-site-out MAE
0.052 / Spearman 0.754 is weaker than a holdout, and that weakness is stated
wherever the number is reported.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "data" / "work"
sys.path.insert(0, str(ROOT / "scripts"))
from session_2026_10_31_scan3 import capacity_support  # noqa: E402
from session_2026_10_31_estimate import (measure, standardize, ridge_fit, CONTROLS,  # noqa: E402
                                         spearman)


def main() -> int:
    footprint = np.load(WORK / "footprint_mask_2026_10_31.npy")
    with rasterio.open(ROOT / "data" / "raw" / "labels.tif") as src:
        catalogue = (src.read(1) > 0) & footprint
    d_cat = ndi.distance_transform_edt(~catalogue).astype(np.float32)
    prob = np.load(WORK / "candidate_prob_2026_10_31.npy")

    doc = json.loads((WORK / "ledger_covariates_2026_10_31.json").read_text())
    rows = doc["rows"]
    fp_mean = doc["target_footprint_mean_credit"]
    tnames = sorted(fp_mean)
    names = list(CONTROLS) + ["lift_" + t for t in tnames]
    X = np.array([[r[n] for n in names] for r in rows], float)
    y = np.array([r["score"] for r in rows], float)
    mu, sd = X.mean(0), X.std(0)
    sd = np.where(sd < 1e-12, 1.0, sd)
    lam = 0.0838
    b = ridge_fit((X - mu) / sd, y, lam)
    sites = np.array([r["site"] for r in rows])
    loo = np.zeros(len(y))
    for s in np.unique(sites):
        tr, te = sites != s, sites == s
        Xtr, m, d = standardize(X[tr])
        bb = ridge_fit(Xtr, y[tr], lam)
        loo[te] = np.hstack([np.ones((te.sum(), 1)), (X[te] - m) / d]) @ bb
    cal_a, cal_b = np.polyfit(loo, y, 1)
    resid = y - (cal_a * loo + cal_b)
    sd_res = float(resid.std(ddof=2))
    print(f"estimator: LOO MAE {np.abs(resid).mean():.4f} Spearman "
          f"{spearman(cal_a*loo+cal_b, y):+.3f} residual SD {sd_res:.4f}")

    z = np.load(WORK / "targets_2026_10_31.npz")
    fp_idx = np.flatnonzero(footprint.ravel())
    tmp = WORK / "_variant_probe.tif"
    out_rows = []
    for buf in (2.0, 4.0, 6.0, 8.0, 12.0):
        allowed = footprint & (d_cat > buf)
        for fl in (0.10, 0.15, 0.20, 0.25, 0.30, 0.40):
            dots = capacity_support(np.where(allowed, prob, -np.inf).astype(np.float32),
                                    allowed, 3, 1, fl)
            n = int(dots.sum())
            if n == 0:
                continue
            nb3 = ndi.uniform_filter(dots.astype(np.float32), size=7, mode="constant") * 49.0
            nb3 = float(nb3[dots].mean())
            vals = np.where(dots, np.float32(1.0), np.float32(0.0))
            prof = None
            with rasterio.open(ROOT / "data" / "raw" / "sample_submission.tif") as src:
                smeta = src.profile
            smeta.update(dtype="float32", count=1, compress="lzw")
            with rasterio.open(tmp, "w", **smeta) as dst:
                dst.write(vals, 1)
            rec = measure(tmp, z, footprint, catalogue, fp_idx, tnames, fp_mean)
            x = np.array([[rec[k] for k in names]], float)
            e1 = float(np.ravel(np.hstack([np.ones((1, 1)), (x - mu) / sd]) @ b)[0])
            est = cal_a * e1 + cal_b
            out_rows.append(dict(buffer=buf, floor=fl, dots=n, nb3=round(nb3, 3),
                                 mean_dcat=round(float(d_cat[dots].mean()), 2),
                                 e1=round(e1, 4), estimate=round(max(est, 0.0), 4),
                                 admissible=bool(35_000 <= n <= 48_000 and nb3 <= 3.4)))
            print(f"  buffer {buf:4.1f} floor {fl:.2f}: {n:>7,} dots nb3 {nb3:5.2f} "
                  f"dcat {d_cat[dots].mean():5.1f}  estimate {max(est,0):.4f}")
    tmp.unlink(missing_ok=True)
    adm = [r for r in out_rows if r["admissible"]]
    adm.sort(key=lambda r: -r["estimate"])
    print("\nTop admissible variants by estimate:")
    for r in adm[:6]:
        print(f"  buffer {r['buffer']:.0f} floor {r['floor']:.2f}: {r['dots']:,} dots, "
              f"estimate {r['estimate']:.4f} (+/- {1.96*sd_res:.3f})")
    (WORK / "variant_selection_2026_10_31.json").write_text(json.dumps(dict(
        session="2026-10-31", evidence_class="ESTIMATE (owner-reported ledger)",
        estimator_loo_mae=float(np.abs(resid).mean()),
        estimator_loo_spearman=spearman(cal_a * loo + cal_b, y),
        residual_sd=sd_res, variants=out_rows, admissible_ranked=adm), indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
