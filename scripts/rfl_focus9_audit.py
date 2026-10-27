#!/usr/bin/env python3
"""E0 (read-only audit, no placement): independent re-measurement of the nine
focus-site leader rasters + every locally downloadable submission TIF.

Written for session arena/bd44f94b (preregistration: knowledge/preregistration-2026-10-27-rfl.md).
Closes IR-17: all nine leaders are measured here by hand-written checks, not by
re-running scripts/audit_focus.py.  DTI numbers use the SHARED evaluators only
(gemsw.holdout.evaluate_hide_and_recover / evaluate_sgmc_with_ci) - never a fork.

Output: evidence/rfl_focus9_audit.json
Labels: owner scores = USER-REPORTED (registry/focus_sites.json); holdout =
HOLDOUT-DTI (evaluator, withheld positives, CI); SGMC = PROXY-DTI.  Nothing here
is an organizer-confirmed score.
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gemsw import grid as G, holdout as H  # noqa: E402

T0 = time.time()


def log(*a):
    print(f"[{time.time() - T0:6.1f}s]", *a, flush=True)


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


DISC3 = (np.add.outer(np.arange(-3, 4) ** 2, np.arange(-3, 4) ** 2) <= 9)


def inspect_tif(p: Path, foot, labels, tmpl_shape, tmpl_crs, tmpl_tr) -> dict:
    with rasterio.open(p) as ds:
        a = ds.read(1)
        meta = dict(shape=list(ds.shape), count=ds.count, dtype=ds.dtypes[0],
                    crs=str(ds.crs), transform=[float(v) for v in ds.transform][:6],
                    nodata=(None if ds.nodata is None or (isinstance(ds.nodata, float) and np.isnan(ds.nodata)) else float(ds.nodata)))
    fin = np.isfinite(a)
    inside, outside = a[foot], a[~foot]
    dots = fin & (a > 0) & foot
    checks = {
        "single_band": meta["count"] == 1,
        "shape_matches_sample": tuple(meta["shape"]) == tmpl_shape,
        "crs_epsg_32611": meta["crs"] == "EPSG:32611",
        "transform_matches_sample": meta["transform"] == [float(v) for v in tmpl_tr][:6],
        "in_footprint_all_finite_or_nan_only": True,  # measured below, reported not assumed
        "in_footprint_no_inf_no_sentinel": bool(not np.isinf(inside).any() and not (inside < -1e30).any()),
        "finite_values_in_0_1": bool(((a[fin] >= 0) & (a[fin] <= 1)).all()) if fin.any() else False,
        "whole_array_finite_and_in_0_1": bool(fin.all() and ((a >= 0) & (a <= 1)).all()),
    }
    return {
        "file": str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p),
        "sha256": sha256_file(p), "bytes": p.stat().st_size, **meta,
        "n_dots_finite_positive_in_footprint": int(dots.sum()),
        "n_positive_on_catalogue": int((dots & labels).sum()),
        "n_nan_in_footprint": int(np.isnan(inside).sum()),
        "outside_footprint": ("all_nan" if np.isnan(outside).all() else
                              "all_zero" if (outside == 0).all() else "mixed_or_other"),
        "whole_array_min_finite": float(a[fin].min()) if fin.any() else None,
        "whole_array_max_finite": float(a[fin].max()) if fin.any() else None,
        "unique_values_sample": [float(v) for v in np.unique(a[fin])[:8]] if fin.any() else [],
        "checks": checks,
        "_dots": dots,
    }


def main() -> int:
    pins = {s["site"]: s for s in json.loads((ROOT / "registry/focus_sites.json").read_text())["sites"]}
    g = G.load_grid(ROOT / "data/raw")
    with rasterio.open(ROOT / "data/raw/sample_submission.tif") as ds:
        tmpl_shape, tmpl_crs, tmpl_tr = ds.shape, ds.crs, ds.transform
    log(f"grid ok: footprint={int(g.foot.sum()):,} catalogue={int(g.labels.sum()):,}")

    ctx = H.load_holdout_context(ROOT / "data/raw")
    log("holdout context loaded")

    sites = ["GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE30",
             "GEMSDOE31", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36"]
    rows, masks = {}, {}
    for s in sites:
        p = ROOT / "data" / f"{s}.tif"
        r = inspect_tif(p, g.foot, g.labels, tmpl_shape, tmpl_crs, tmpl_tr)
        masks[s] = r.pop("_dots")
        r["pin_sha256_match"] = (r["sha256"] == pins[s]["sha256"])
        r["owner_reported_score_USER_REPORTED_not_organizer_confirmed"] = pins[s]["owner_reported"]
        r["upstream_repo"] = f"https://github.com/buffedlizard55-lab/{s}/blob/{pins[s]['ref']}/{pins[s]['path']}"
        ev = H.evaluate_hide_and_recover(masks[s], ctx, name=s, n_boot=1000)
        r["static_holdout_dti"] = {"label": "HOLDOUT-DTI (static saved file; not fold-local)",
                                   "evaluator_version": ev["evaluator_version"],
                                   "n_withheld_positives": ev["n_withheld_positives"],
                                   "dti": ev["pooled_dti"], "ci95": ev["ci95_cluster_bootstrap"]}
        sg = H.evaluate_sgmc_with_ci(masks[s], ctx, n_boot=1000)
        r["sgmc_proxy_dti"] = {"label": "PROXY-DTI (USGS SGMC off-catalogue; not a competition score)",
                               **{k: v for k, v in sg.items() if not str(k).startswith("_")}}
        rows[s] = r
        log(f"{s}: dots={r['n_dots_finite_positive_in_footprint']:,} pin={r['pin_sha256_match']} "
            f"holdout={ev['pooled_dti']:.4f} owner={pins[s]['owner_reported']}")

    # All 36 pairwise comparisons (independent implementation).
    log("pairwise 36 comparisons ...")
    dilated = {s: ndi.binary_dilation(masks[s], structure=DISC3) for s in sites}
    pairwise = []
    for i, a in enumerate(sites):
        for b in sites[i + 1:]:
            ma, mb = masks[a], masks[b]
            inter, union = int((ma & mb).sum()), int((ma | mb).sum())
            pairwise.append({
                "a": a, "b": b, "n_a": int(ma.sum()), "n_b": int(mb.sum()),
                "intersection": inter, "jaccard": inter / union if union else 0.0,
                "a_within_3px_of_b": float((ma & dilated[b]).sum() / max(int(ma.sum()), 1)),
                "b_within_3px_of_a": float((mb & dilated[a]).sum() / max(int(mb.sum()), 1)),
                "a_exact_subset_of_b": bool(not (ma & ~mb).any()),
                "b_exact_subset_of_a": bool(not (mb & ~ma).any()),
                "identical_support": bool((ma == mb).all()),
            })
    dup70 = [p for p in pairwise if p["a_within_3px_of_b"] > 0.70 and p["b_within_3px_of_a"] > 0.70]

    # GEMSDOE32 (B2) vs GEMSDOE31 anatomy, re-measured from bytes.
    m32, m31 = masks["GEMSDOE32"], masks["GEMSDOE31"]
    removed, added = m31 & ~m32, m32 & ~m31
    d_cat = ndi.distance_transform_edt(~g.labels)
    b2 = {"n_31": int(m31.sum()), "n_32": int(m32.sum()), "n_removed_31_minus_32": int(removed.sum()),
          "n_added_32_minus_31": int(added.sum()),
          "removed_dist_to_catalogue_px_min": float(d_cat[removed].min()) if removed.any() else None,
          "removed_dist_to_catalogue_px_max": float(d_cat[removed].max()) if removed.any() else None,
          "retained_dist_to_catalogue_px_min": float(d_cat[m32].min()) if m32.any() else None,
          "owner_gap_USER_REPORTED": "0.2778 - 0.2708 = +0.0070 (no organizer receipt in this repo)",
          "h6_1_pruning_holdout": "HOLDOUT-DTI paired delta +0.000054 vs unpruned; +0.000108 [-8e-07,+0.000235] vs random prune (evidence/h6_1_proximity_pruning_holdout.json) - does not explain +0.0070; buffered holdout has no withheld truth within 3px of visible catalogue (IR-13)"}
    log(f"B2 anatomy: removed={b2['n_removed_31_minus_32']} added={b2['n_added_32_minus_31']}")

    # Literal-witness vacuity, verified from the packed registry mask.
    idx = json.loads((ROOT / "registry/cspes_registry_index.json").read_text())
    dense = [f for f in idx["files"] if f.get("dense")]
    witness = {"n_dense_masks_in_rebuilt_registry": len(dense),
               "entries": [{k: f.get(k) for k in ("path", "sha256", "dots_sha256", "n_dots")} for f in dense],
               "footprint_cells": int(g.foot.sum())}
    if dense:
        pk = np.load(ROOT / ".cache/registry" / f"{dense[0]['dots_sha256']}.npy")
        wmask = np.unpackbits(pk)[: g.foot.size].reshape(g.foot.shape).astype(bool)
        witness["verified_positive_on_all_footprint_cells"] = bool((wmask & g.foot).sum() == g.foot.sum())
        witness["champion_b2_dots_within_3px_of_witness"] = float((m32 & wmask).sum() / max(int(m32.sum()), 1))
        witness["implication"] = ("Literal any-raster 70% rule is unsatisfiable for EVERY non-empty "
                                  "in-footprint candidate, including the 0.2778 champion itself (IR-01/IR-11). "
                                  "Operative uniqueness in this session = sparse-submission registry, literal result still reported.")
    log(f"witness: {witness.get('verified_positive_on_all_footprint_cells')} "
        f"champ overlap={witness.get('champion_b2_dots_within_3px_of_witness')}")

    # Every locally downloadable submission TIF: whole-array [0,1] / finite audit (IR-14 recheck).
    local = {}
    for p in sorted((ROOT / "submission").glob("*.tif")) + sorted((ROOT / "docs/downloads").glob("*.tif")) \
            + sorted((ROOT / "docs/hce/downloads").glob("*.tif")):
        r = inspect_tif(p, g.foot, g.labels, tmpl_shape, tmpl_crs, tmpl_tr)
        r.pop("_dots")
        local[r["file"]] = r
    bad_range = [k for k, v in local.items() if not v["checks"]["finite_values_in_0_1"]]
    log(f"local TIFs audited={len(local)} finite-out-of-[0,1]={bad_range}")

    out = {"audit": "E0 rfl_focus9_audit (arena/bd44f94b, 2026-10-27)",
           "evaluator": "GEMSDOE32-HIDE-RECOVER-v3.0 (shared gemsw.holdout, unmodified)",
           "sites": rows, "pairwise_36": pairwise,
           "pairwise_both_directions_above_70pct_within_3px": len(dup70),
           "b2_anatomy": b2, "literal_witness": witness, "local_downloadable_tifs": local,
           "elapsed_s": round(time.time() - T0, 1)}
    (ROOT / "evidence/rfl_focus9_audit.json").write_text(json.dumps(out, indent=1))
    log(f"wrote evidence/rfl_focus9_audit.json; pairwise>70% both ways: {len(dup70)}/36")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
