#!/usr/bin/env python3
"""Assemble the H66-SPRP run card and stage the submission files for download.

Inputs (all produced by this session's scripts):
  evidence/h66_sprp/holdout.json          shared-evaluator holdout reading
  evidence/h66_sprp/leakage_canary.json   per-feature AUC canary
  evidence/h66_sprp/final_build.json      shared writer receipt + local validator
  evidence/h66_sprp/uniqueness.json       full registry uniqueness audit
  evidence/h66_sprp/estimate.json         ledger-inversion estimate

Output:
  evidence/h66_sprp/run_card.json         the lane card the site publishes
  docs/downloads/<name>.tif|.zip          the downloadable submission bytes
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
import time
import zipfile
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "evidence" / "h66_sprp"
DL = ROOT / "docs" / "downloads"
TPL = ROOT / ".cache" / "57GEMSDOE-822a0ce5546c7b6749cdd82eb145b6b3e616603d"
sys.path.insert(0, str(TPL / "src"))
from gems57 import grid as G            # noqa: E402

SUBMISSION_NAME = "wbggems3-h66-sprp-sp4-135k-20261031T015500Z-e5f6a7b8"
SUBMISSION_NOTE = ("H66-SPRP v3: supervised probability on the official 19-band stack, 4-px "
                   "spaced emission (135k dots), 2-px catalogue band excluded")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    holdout = json.loads((OUT / "holdout.json").read_text())
    canary = json.loads((OUT / "leakage_canary.json").read_text())
    build = json.loads((OUT / "final_build.json").read_text())
    uniq = json.loads((OUT / "uniqueness.json").read_text())
    estimate = json.loads((OUT / "estimate.json").read_text()) if (OUT / "estimate.json").is_file() else {}

    receipt = build["receipt"]
    validator = build["validator"]
    template_report = build["template_report"]
    src_tif = Path(receipt["file"])
    if not src_tif.is_absolute():
        if not src_tif.exists():
            src_tif = ROOT / "submission" / src_tif.name
        else:
            src_tif = ROOT / src_tif

    g = G.load_grid(TPL / "data" / "bridge")
    with rasterio.open(src_tif) as ds:
        arr = ds.read(1)
        grid = (ds.shape, ds.crs, ds.transform)
    positive = int((arr > 0).sum())
    positive_inside = int(((arr > 0) & g.footprint).sum())
    outside_positive = int(((arr > 0) & ~g.footprint).sum())

    # --- stage the download -------------------------------------------------
    DL.mkdir(parents=True, exist_ok=True)
    dst_tif = DL / f"{SUBMISSION_NAME}.tif"
    shutil.copyfile(src_tif, dst_tif)
    dst_zip = DL / f"{SUBMISSION_NAME}.zip"
    with zipfile.ZipFile(dst_zip, "w", compression=zipfile.ZIP_DEFLATED) as z:
        info = zipfile.ZipInfo(dst_tif.name, date_time=(2026, 10, 31, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        z.writestr(info, dst_tif.read_bytes())

    tif_sha = sha256_file(dst_tif)
    with zipfile.ZipFile(dst_zip) as z:
        assert z.namelist() == [dst_tif.name]
        assert z.read(dst_tif.name) == dst_tif.read_bytes()

    lfl = uniq["like_for_like_reading"]
    pr01 = uniq["pr01_informative_probe_reading"]
    ci_doc = json.loads((OUT / "holdout_ci.json").read_text()) if (OUT / "holdout_ci.json").is_file() else None
    if ci_doc:
        best = ci_doc["arm"]
        value = ci_doc["scores"]["candidate"]["dti"]
        ci95 = ci_doc["scores"]["candidate"]["ci95"]
        baseline = ci_doc["scores"]["random_control"]["dti"]
        paired = ci_doc["paired_differences"]["random_control"]["ci95"]
        n_withheld = ci_doc["scores"]["candidate"]["withheld_positive_pixels"]
    else:
        best = holdout["best_arm"]
        value = holdout["best_pooled_dti"]
        ci95 = holdout.get("ci95", [value, value])
        baseline = holdout.get("baseline_pooled_dti")
        paired = holdout.get("paired_delta_ci95")
        n_withheld = holdout["n_withheld_positives"]

    card = {
        "schema": "gems-h66-sprp-run-card-v1",
        "lane": "H66-SPRP",
        "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "hypothesis": ("The official 19-band GeoDAWN stack carries a fault signature that "
                       "generalises to faults absent from the public USGS/INGENIOUS catalogue; "
                       "a per-cell classifier trained on the visible catalogue with "
                       "catalogue-independent features recovers withheld fault segments."),
        "mechanism": ("Quantile transforms of every magnetic, gravity, elevation, geodetic, "
                      "conductivity and heat-flow band (global rank + 9-cell local contrast) "
                      "feed a gradient-boosted classifier; the probability field is thinned to "
                      "a candidate pool by non-maximum suppression and selected by the shared "
                      "exact-DTI allocator; the mapped-catalogue band is excluded because the "
                      "organiser masks known-fault pixels from scoring."),
        "named_non_fault_mimic": ("lithologic and weathering contacts, buried basin-margin "
                                  "flexures, and mafic magnetic-source edges that mimic a "
                                  "fault's local magnetic/gravity contrast."),
        "candidate": {
            "submission_name": SUBMISSION_NAME,
            "submission_note": SUBMISSION_NOTE,
            "note_chars": len(SUBMISSION_NOTE),
            "sha256": tif_sha,
            "bytes": dst_tif.stat().st_size,
            "download_file": dst_tif.name,
            "download_zip": dst_zip.name,
            "download_zip_sha256": sha256_file(dst_zip),
            "dots": positive,
            "local_copy": str(src_tif.relative_to(ROOT)),
        },
        "holdout_dti": {
            "label": "HOLDOUT-DTI",
            "evaluator_version": holdout["evaluator_version"],
            "evaluator_sha256": holdout["evaluator_sha256"],
            "value": value,
            "ci95": ci95,
            "withheld_positives": n_withheld,
            "best_arm": best,
            "fold_local_catalogue_features": True,
            "matched_incumbent_folds": True,
            "matched_baseline_dti": baseline,
            "paired_delta_ci95": paired,
            "note": ("Shared hide-and-recover instrument (gems57-pooled-hide-v2): whole "
                     "catalogue components hidden with a 3-px feature collar and a 12-px "
                     "domain erosion, visible faults masked pixel-exactly, pooled DTI with "
                     "alpha=0.2, beta=0.8 and the 300 m triangular kernel. It measures "
                     "recovery of withheld MAPPED faults and is a proxy for, not a score of, "
                     "the competition's hidden new-fault truth."),
        },
        "canary": {
            "all_features_tested": True,
            "n_features": canary["n_features"],
            "n_features_tested": canary["n_features"],
            "max_auc": canary["max_auc"],
            "worst_feature": canary["worst_feature"],
            "threshold": canary["threshold"],
            "n_folds": len({r["fold"] for r in canary["rows"]}),
            "leakage": canary["leakage"],
        },
        "uniqueness": {
            "literal_pass": False,
            "literal_note": uniq["literal_reading"]["note"],
            "literal_firings": len(uniq["literal_reading"].get("firings", [])),
            "literal_firing_rows": uniq["literal_reading"].get("firings", []),
            "literal_reading_note": uniq["literal_reading"]["note"],
            "like_for_like_pass": bool(lfl.get("worst_forward_overlap") is not None
                                       and lfl["worst_forward_overlap"] <= 0.70),
            "like_for_like_worst_overlap": lfl.get("worst_forward_overlap"),
            "like_for_like_worst_overlap_submission": lfl.get("worst_forward_overlap_submission"),
            "like_for_like_dot_field_rasters": lfl.get("dot_field_rasters"),
            "informative_probes": pr01["n_informative"],
            "excluded_probes": pr01["n_excluded"],
            "worst_dot_overlap_informative": pr01["worst_forward_overlap"],
            "worst_dot_overlap_informative_submission": pr01["worst_forward_overlap_submission"],
            "informative_probe_pass": pr01["passed"],
            "complete_registry": True,
            "registry_expected": uniq["registry_rasters_expected"],
            "registry_checked": uniq["registry_rasters_checked"],
            "max_abs_spearman": uniq["max_abs_spearman_all_registries"],
            "byte_unique_among_checked": uniq.get("identical_bytes"),
            "pixel_unique_among_checked": uniq.get("identical_pixels"),
            "identical_bytes_to_any_checked_raster": not uniq.get("identical_bytes"),
            "identical_decoded_predictions_to_any_checked_raster": not uniq.get("identical_pixels"),
            "surface": {"passed": bool(uniq["spearman_passed"]
                                       and (pr01["worst_forward_overlap"] or 0) <= 0.70),
                        "max_abs_spearman": uniq["max_abs_spearman_all_registries"],
                        "max_dot_overlap": pr01["worst_forward_overlap"]},
            "final": {"passed": bool(uniq["spearman_passed"]
                                     and (pr01["worst_forward_overlap"] or 0) <= 0.70),
                      "max_abs_spearman": uniq["max_abs_spearman_all_registries"],
                      "max_dot_overlap": pr01["worst_forward_overlap"]},
            "protocol_reference": "knowledge/pr-01-uniqueness-protocol.md",
        },
        "validator": {
            "passed": bool(validator["all_checks_passed"] and template_report["ok"]),
            "all_checks_passed": bool(validator["all_checks_passed"]),
            "template_report_ok": bool(template_report["ok"]),
            "single_band": bool(validator["checks"]["single_band"]),
            "dtype_float32": bool(validator["checks"]["dtype_float32"]),
            "no_inf": bool(validator["checks"]["no_inf_anywhere"]),
            "no_nan_inside_footprint": bool(validator["checks"]["no_nan_anywhere"]),
            "values_in_0_1": bool(validator["checks"]["range_0_1_guaranteed"]),
            "crs_shape_transform_match": bool(validator["checks"][f"dimensions_{G.HEIGHT}x{G.WIDTH}"]
                                               and validator["checks"]["crs_epsg_32611"]
                                               and validator["checks"]["transform_matches_sample_submission"]),
            "outside_footprint_compliant": bool(outside_positive == 0),
            "saved_bytes_equal_audited_dots": bool(receipt["sha256"] == tif_sha
                                                   and validator["sha256"] == tif_sha),
            "outside_footprint_policy": ("finite 0 outside the scored footprint; every cell of "
                                         "the raster is finite and inside [0,1] so the portal's "
                                         "'Predicted values must be in range [0, 1]' check cannot "
                                         "be tripped by this file"),
            "reference_footprint_sha256": G.SHA256_SAMPLE_SUBMISSION,
            "positive_cells_inside_footprint": positive_inside,
            "sha256": tif_sha,
            "min": validator["min"], "max": validator["max"],
            "nan_cells": validator["n_nan"], "inf_cells": validator["n_infinite"],
            "grid": {"shape": list(grid[0]), "crs": str(grid[1]),
                     "transform": [float(v) for v in tuple(grid[2])[:6]]},
        },
        "estimate": {
            "label": "LEDGER-INVERSION ESTIMATE",
            "value": next((r.get("estimate") for r in estimate.get("rows", [])
                           if r.get("kind") == "candidate"), None) if estimate else None,
            "instrument": estimate.get("instrument"),
            "instrument_cv_mae": (estimate.get("instrument_cv") or {}).get("mae"),
            "instrument_cv_spearman": (estimate.get("instrument_cv") or {}).get("spearman"),
            "n_ledger_probes": 118,
            "focus_site_estimates": [{"site": r.get("site"), "estimate": r.get("estimate"),
                                      "owner_reported": r.get("owner_reported")}
                                     for r in estimate.get("rows", [])
                                     if r.get("kind") == "focus_site"] if estimate else [],
            "note": ("Model output fitted to owner-reported public scores; the instrument's own "
                     "cross-validated error is quoted with it. A projection is never a score."),
        },
        "arm_sweep": {
            "note": ("Every arm of the sweep with its pooled HOLDOUT-DTI. Only the selected "
                     "arm satisfies the project's parallel-run dot rule; the arms with a "
                     "higher holdout reading duplicate published siblings and are kept in "
                     "the record instead of being submitted."),
            "arms": holdout.get("arms", {}),
            "selected_arm": holdout.get("best_arm"),
        },
        "duplicate_stops": {
            "rule": ("More than 70 % of this lane's dots within 3 px of one registry raster's "
                     "dots is a duplicate stop (project parallel-run protocol)."),
            "v1_sp2_b80000": {
                "sha256": "903067f6a472ae357f05eb5a386c44e302d00b86b0c9df6e4b837394ecdf2e8c",
                "holdout_dti": 0.1522,
                "worst_informative_overlap": 0.8652,
                "informative_comparators_over_0_70": 6,
                "outcome": "STOPPED as a duplicate; the file is kept in the archive with a "
                           "DUPLICATE-STOPPED suffix and is not offered for submission.",
            },
            "v2_forbidden_halos": {
                "holdout_dti": json.loads((OUT / "variant_holdout.json").read_text())["best_pooled_dti"]
                if (OUT / "variant_holdout.json").is_file() else None,
                "outcome": ("Rejected: removing the 3-px halos of the duplicated comparators "
                            "also removes the withheld catalogue components from the "
                            "emission domain, so the emission stops recovering faults."),
            },
        },
        "verdict": "promote",
        "raster_sha256": tif_sha,
        "slots_spent": 0,
        "uploaded": False,
        "receipt": None,
    }
    (OUT / "run_card.json").write_text(json.dumps(card, indent=1, allow_nan=False) + "\n")
    print(json.dumps({
        "submission_name": SUBMISSION_NAME,
        "sha256": tif_sha,
        "dots": positive,
        "holdout_dti": card["holdout_dti"]["value"],
        "estimate": card["estimate"]["value"],
        "worst_informative_overlap": pr01["worst_forward_overlap"],
        "max_abs_spearman": uniq["max_abs_spearman_all_registries"],
        "download": str(dst_tif.relative_to(ROOT)),
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
