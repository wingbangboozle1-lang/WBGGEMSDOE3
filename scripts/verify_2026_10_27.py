#!/usr/bin/env python3
"""Re-measure every raster fact cited in the 2026-10-27 executive summary.

Read-only. Uses the pinned fetch and SHA-256 checks in gems_project.audit and the
restored shared template; it creates no candidate, runs no experiment and uses no
competition slot. Official web observations are NOT re-fetched here (the sandbox
allowlist excludes drivendata.org); they are recorded with their source URLs in
knowledge/verification-2026-10-27.md and evidence/verification_2026-10-27.json.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import shutil
import sys

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems_project.audit import (LABEL_SHA, SAMPLE_SHA, WITNESS, get_reference,  # noqa: E402
                                source_url)
from gems_project.template import ensure_template  # noqa: E402

G32_SHA = "c55bafc470054e8271dcb89347a17e07fefe50de6af6e6ba6c4b169ef7ab6fa9"
G31 = {"repo": "buffedlizard55-lab/GEMSDOE31", "ref": "78f9bf3ae82e5c78ca348aa37c0660c339e72f0e",
       "path": "docs/downloads/gemsdoe31-h27-4-solo-d28-20261004-8acb75e1-nan.tif",
       "sha256": "07b6db440535404bb41ec8ddc797713e200d308e3da35937393efde5eb84bc40"}
G32 = {"repo": "buffedlizard55-lab/GEMSDOE32", "ref": "8953b986b2ce6eb5ee8b7eda23fe3ad529720986",
       "path": "docs/downloads/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif",
       "sha256": G32_SHA}
G36 = {"repo": "buffedlizard55-lab/GEMSDOE36", "ref": "b90418f852615aa0974cf9a53b92fa569ed133fc",
       "path": "docs/downloads/gemsdoe36-anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros.tif",
       "sha256": "e15891020b9c57056ac7fa874a5e506fbd6ed9314a4ea8e73af0753887a3708a"}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def within3(src: np.ndarray, tgt: np.ndarray) -> float:
    """Fraction of src dots whose nearest tgt dot lies within 3 px (Euclidean)."""
    if not tgt.any():
        return 0.0
    dist = distance_transform_edt(~tgt)
    return float((dist[src] <= 3.0).mean())


def main() -> int:
    cache = ROOT / ".cache" / "references"
    cache.mkdir(parents=True, exist_ok=True)
    template = ensure_template()
    sample = template / "data/official/sample_submission.tif"
    labels = template / "data/official/existing_faults.tif"
    checks = []

    def check(name, ok, value, source):
        checks.append({"check": name, "pass": bool(ok), "value": value, "source": source})

    check("sample SHA-256 matches pin", sha(sample) == SAMPLE_SHA, sha(sample), "restored shared template data/official")
    check("official catalogue SHA-256 matches pin", sha(labels) == LABEL_SHA, sha(labels), "restored shared template data/official")
    with rasterio.open(sample) as ds:
        foot = np.isfinite(ds.read(1))
        ref_grid = (ds.shape, ds.crs.to_string(), tuple(ds.transform)[:6])
    cat = labels_arr = None
    with rasterio.open(labels) as ds:
        labels_arr = ds.read(1)
    cat_pos = np.isfinite(labels_arr) & (labels_arr > 0)
    check("sample footprint = 5,167,373 finite cells", int(foot.sum()) == 5167373, int(foot.sum()), str(sample.relative_to(ROOT)) if sample.is_relative_to(ROOT) else "template sample")

    witness_path = get_reference(WITNESS, cache, "witness17.tif")
    with rasterio.open(witness_path) as ds:
        w = ds.read(1)
        w_grid = (ds.shape, ds.crs.to_string(), tuple(ds.transform)[:6])
    w_pos = np.isfinite(w) & (w > 0)
    check("witness SHA-256 matches pin", sha(witness_path) == WITNESS["sha256"], sha(witness_path), source_url(WITNESS))
    check("witness grid equals sample grid", w_grid == ref_grid, w_grid, source_url(WITNESS))
    check("witness positive on every footprint cell", int((w_pos & foot).sum()) == int(foot.sum()) and int((w_pos & ~foot).sum()) == 0,
          {"positive_inside": int((w_pos & foot).sum()), "footprint": int(foot.sum()), "positive_outside": int((w_pos & ~foot).sum())},
          source_url(WITNESS))

    paths = {}
    for name, entry in (("GEMSDOE32", G32), ("GEMSDOE31", G31), ("GEMSDOE36", G36)):
        paths[name] = get_reference(entry, cache, f"{name}.tif")
        check(f"{name} file SHA-256 matches pin", sha(paths[name]) == entry["sha256"], sha(paths[name]), source_url(entry))
    arr = {}
    for name, p in paths.items():
        with rasterio.open(p) as ds:
            arr[name] = ds.read(1)
            meta = {"dtype": ds.dtypes[0], "nodata": ds.nodata, "shape": list(ds.shape), "crs": ds.crs.to_string(),
                    "transform_ok": (ds.shape, ds.crs.to_string(), tuple(ds.transform)[:6]) == ref_grid}
        a = arr[name]
        finite = np.isfinite(a)
        meta.update({"nan_cells": int(np.isnan(a).sum()), "finite_cells": int(finite.sum()),
                     "min": float(np.nanmin(a)), "max": float(np.nanmax(a)),
                     "positive_dots": int((finite & (a > 0)).sum())})
        arr[name + "_meta"] = meta
    g32, g31, g36 = (arr[k] for k in ("GEMSDOE32", "GEMSDOE31", "GEMSDOE36"))
    d32, d31, d36 = ((np.isfinite(x) & (x > 0)) for x in (g32, g31, g36))
    m32 = arr["GEMSDOE32_meta"]
    check("GEMSDOE32 is float32 in [0,1] with no NaN", m32["dtype"] == "float32" and m32["min"] >= 0 and m32["max"] <= 1 and m32["nan_cells"] == 0,
          {k: m32[k] for k in ("dtype", "min", "max", "nan_cells")}, source_url(G32))
    check("GEMSDOE32 writes zeros (not NaN) outside footprint", m32["finite_cells"] == int(g32.size) and int(((g32 == 0) & ~foot).sum()) == int((~foot).sum()),
          {"finite_cells": m32["finite_cells"], "rectangle_cells": int(g32.size)}, source_url(G32))
    check("GEMSDOE32 has 37,654 positive dots", m32["positive_dots"] == 37654, m32["positive_dots"], source_url(G32))
    check("GEMSDOE32 dots are an exact subset of GEMSDOE31 dots", not (d32 & ~d31).any(), int((d31 & ~d32).sum()), source_url(G31))
    removed = d31 & ~d32
    dist_cat = distance_transform_edt(~cat_pos)
    check("all 2,545 removed GEMSDOE31 dots lie 1.41-2.00 px from the official catalogue",
          int(removed.sum()) == 2545 and float(dist_cat[removed].min()) > 1.4 and float(dist_cat[removed].max()) <= 2.0,
          {"removed": int(removed.sum()), "min_px": float(dist_cat[removed].min()), "max_px": float(dist_cat[removed].max())},
          "official catalogue existing_faults.tif (template) vs GEMSDOE31 H27-4 base")
    check("kept GEMSDOE32 dots are all >2 px from the catalogue", float(dist_cat[d32].min()) > 2.0,
          float(dist_cat[d32].min()), "official catalogue existing_faults.tif (template)")
    check("GEMSDOE32 retained dots carry identical values to GEMSDOE31", bool(np.array_equal(g31[d32], g32[d32])),
          {"retained": int(d32.sum()), "value_set": sorted({float(x) for x in np.unique(g32[d32])})}, source_url(G32))
    o32_31, o32_36 = within3(d32, d31), within3(d32, d36)
    check("GEMSDOE32 dots: 100% within 3 px of GEMSDOE31 dots", o32_31 >= 0.9999, o32_31, source_url(G31))
    check("GEMSDOE32 dots: 100% within 3 px of GEMSDOE36 dots", o32_36 >= 0.9999, o32_36, source_url(G36))

    # Upstream holdout record for the same mechanism (not a leaderboard score).
    src = template / "docs/data/h6_1_proximity_pruning_holdout.json"
    dest = ROOT / "evidence" / "h6_1_proximity_pruning_holdout.json"
    shutil.copyfile(src, dest)
    h6 = json.loads(dest.read_text())
    h6_summary = {
        "evidence_class": "HOLDOUT-DTI (upstream template experiment H6-1; not a leaderboard score)",
        "evaluator_version": h6["evaluator_version"],
        "withheld_positive_pixels": h6["scores"]["unpruned"]["withheld_positive_pixels"],
        "unpruned_dti_ci95": h6["scores"]["unpruned"]["ci95"],
        "proximity_prune_dti": h6["scores"]["proximity_prune"]["dti"],
        "paired_delta_vs_unpruned": h6["paired_differences"]["unpruned"]["delta"],
        "paired_delta_vs_unpruned_ci95": h6["paired_differences"]["unpruned"]["ci95"],
        "paired_delta_vs_random_prune": h6["paired_differences"]["random_prune"]["delta"],
        "paired_delta_vs_random_prune_ci95": h6["paired_differences"]["random_prune"]["ci95"],
        "tpw_unpruned_equals_proximity": h6["scores"]["unpruned"]["tpw"] == h6["scores"]["proximity_prune"]["tpw"],
        "verdict_in_source": h6.get("verdict"),
        "source_sha256": sha(dest),
        "source_path": "template docs/data/h6_1_proximity_pruning_holdout.json (pinned commit 822a0ce)",
    }
    check("H6-1 proximity pruning: paired delta vs random prune CI includes 0",
          h6_summary["paired_delta_vs_random_prune_ci95"][0] <= 0 <= h6_summary["paired_delta_vs_random_prune_ci95"][1],
          h6_summary["paired_delta_vs_random_prune_ci95"], str(dest.relative_to(ROOT)))

    # Survey every TIFF the repo ships, to test the user's "range [0, 1]" report.
    survey = []
    for tif in sorted(ROOT.glob("docs/**/*.tif")) + sorted(ROOT.glob("submission/*.tif")) + sorted(ROOT.glob("archive/**/*.tif")):
        with rasterio.open(tif) as ds:
            a = ds.read(1).astype("float64")
            fin = np.isfinite(a)
            grid_ok = (ds.shape, ds.crs.to_string() if ds.crs else None, tuple(ds.transform)[:6]) == ref_grid
            survey.append({
                "file": str(tif.relative_to(ROOT)), "sha256": sha(tif), "dtype": ds.dtypes[0],
                "nodata": None if ds.nodata is None else str(ds.nodata), "shape": list(ds.shape),
                "grid_matches_sample": grid_ok, "nan_cells": int(np.isnan(a).sum()),
                "out_of_range_finite_cells": int((fin & ((a < 0) | (a > 1))).sum()),
                "positive_dots": int((fin & (a > 0)).sum()),
            })
    check("no repo TIFF has finite values outside [0,1]", all(r["out_of_range_finite_cells"] == 0 for r in survey),
          {"files": len(survey), "out_of_range_total": sum(r["out_of_range_finite_cells"] for r in survey)},
          "local survey of docs/, submission/, archive/ TIFFs")

    failed = [c["check"] for c in checks if not c["pass"]]
    out = {
        "schema": "verification-2026-10-27-v1",
        "checked_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "evidence_class": "RASTER-MEASUREMENT (reproducible); official web observations recorded separately",
        "checks": checks,
        "all_passed": not failed,
        "failed_checks": failed,
        "holdout_h6_1": h6_summary,
        "uniqueness_rule_source": "PROJECT PROTOCOL (user brief), not an official DrivenData/NLR rule; see knowledge/verification-2026-10-27.md",
        "local_tiff_survey": survey,
        "candidate_created": False,
        "experiments_run_this_session": 0,
        "slots_used": 0,
    }
    (ROOT / "evidence" / "verification_2026-10-27.json").write_text(json.dumps(out, indent=2, allow_nan=False, default=str) + "\n")
    for c in checks:
        print(("PASS " if c["pass"] else "FAIL ") + c["check"])
    print("ALL PASSED" if not failed else f"FAILED: {failed}")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
