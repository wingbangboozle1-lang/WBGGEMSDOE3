#!/usr/bin/env python3
"""Post-hoc diagnostics for the LBCAL candidate (added AFTER the verdict; cannot change it).

1. Overlap saturation: for every registry raster, the share of the allowed domain
   inside its 3 px halo (what a random candidate would score on the forward-overlap
   test) next to the candidate's measured forward overlap -> vacuous vs informative
   duplicate firings.
2. Nearest-neighbour residual check: the model's family-CV residuals on the scored
   rasters whose dots the candidate overlaps beyond chance.  A systematic
   over-prediction there means the candidate's ESTIMATE is optimistic.

Writes evidence/lbcal/postcheck.json and appends a summary to evidence/lbcal_run_card.json.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import binary_dilation

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from lbcal import data as D  # noqa: E402

DISK = (lambda r: (np.add.outer(np.arange(-r, r + 1) ** 2, np.arange(-r, r + 1) ** 2) <= r * r))(3)


def main() -> int:
    grid = D.load_grid()
    allowed = grid.foot & ~grid.cat
    card_p = ROOT / "evidence" / "lbcal_run_card.json"
    card = json.loads(card_p.read_text())
    scan = json.loads((ROOT / "evidence" / "lbcal" / "registry_scan_final.json").read_text())
    cv = json.loads((ROOT / "evidence" / "lbcal_cv.json").read_text())
    var = json.loads((ROOT / "evidence" / "lbcal_variants.json").read_text())
    bounded = var["variants"][var["selected"]]["cv_pred"]
    cvp = {r["submission"]: (r["owner_reported"], bounded[j]) for j, r in enumerate(cv["observations"])}
    rows = []
    for r in scan["rows"]:
        if "error" in r:
            continue
        with rasterio.open(r["file"]) as ds:
            a = ds.read(1)
        t = np.isfinite(a) & (a > 0) & grid.foot
        cov = float(binary_dilation(t, structure=DISK)[allowed].mean()) if t.any() else 0.0
        fo = float(r["my_dots_within_3px_of_theirs"])
        row = dict(submission=r["submission"], their_dots=int(t.sum()), forward_overlap=round(fo, 4),
                   halo_share_of_allowed=round(cov, 4), excess_over_random=round(fo - cov, 4),
                   firing=bool(fo > 0.70), vacuous_firing=bool(fo > 0.70 and cov > 0.70))
        if r["submission"] in cvp:
            s, p = cvp[r["submission"]]
            row.update(owner_reported=s, bounded_family_cv=round(p, 4), residual=round(s - p, 4))
        rows.append(row)
    near = [r for r in rows if r["excess_over_random"] > 0.25 and "owner_reported" in r]
    near = [r for r in near if r["bounded_family_cv"] > 0]
    ratio = [r["owner_reported"] / r["bounded_family_cv"] for r in near]
    under = [r["submission"][:24] for r, q in zip(near, ratio) if q > 1.1]
    over = [r["submission"][:24] for r, q in zip(near, ratio) if q < 0.9]
    est = card["estimate"]["cross_fit_mean"]
    firing = [r for r in rows if r["firing"]]
    summary = dict(
        label="POST-HOC DIAGNOSTIC (computed after the verdict; cannot change it)",
        firings=len(firing), vacuous_firings=sum(r["vacuous_firing"] for r in firing),
        informative_firings=[dict(submission=r["submission"], forward_overlap=r["forward_overlap"],
                                  halo_share=r["halo_share_of_allowed"]) for r in firing if not r["vacuous_firing"]],
        nearest_neighbours=[dict(submission=r["submission"], excess=r["excess_over_random"],
                                 owner_reported=r["owner_reported"], cv=r["bounded_family_cv"]) for r in near],
        nn_mean_residual=round(float(np.mean([r["residual"] for r in near])), 4) if near else None,
        nn_mean_ratio_owner_over_cv=round(float(np.mean(ratio)), 3) if ratio else None,
        nn_min_ratio=round(float(np.min(ratio)), 3) if ratio else None,
        nn_max_ratio=round(float(np.max(ratio)), 3) if ratio else None,
        ratio_adjusted_estimate=round(est * float(np.mean(ratio)), 3) if ratio else None,
        worst_case_ratio_adjusted_estimate=round(est * float(np.min(ratio)), 3) if ratio else None,
        interpretation=(
            f"{len(near)} scored rasters share the candidate's dot locations beyond chance (excess > 0.25). "
            f"The model under-predicts {len(under)} of them by >10% (owner/CV up to {max(ratio):.2f}; mostly the "
            f"d2.8 dotted-ridge lineage) and over-predicts {len(over)} by >10% (down to {min(ratio):.2f}: "
            f"{', '.join(over)}). So the candidate's ESTIMATE has a plausible range rather than a point: "
            f"ratio-adjusted {est * min(ratio):.3f}-{est * max(ratio):.3f}. These are heuristics, not scores.")
        if ratio else "no beyond-chance neighbours",
    )
    (ROOT / "evidence" / "lbcal" / "postcheck.json").write_text(json.dumps(dict(summary=summary, rows=rows), indent=1) + "\n")
    card["post_hoc_diagnostics"] = summary
    card_p.write_text(json.dumps(card, indent=1, default=float) + "\n")
    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
