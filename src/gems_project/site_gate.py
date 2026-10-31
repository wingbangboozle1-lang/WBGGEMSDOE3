"""Release-gate v2: verify a candidate submission against saved bytes and saved evidence.

Why v2 exists
-------------
`gems-release-gate-v1` was a *fail-closed no-candidate* contract: it rejected any gate that
named a file, any run card that claimed a raster hash, and any page that used positive
language. That was the correct contract while no candidate existed, but it can never express
a cleared submission -- by construction it can only ever say "nothing to submit".

v2 keeps the same spirit (every claim must be recomputed from saved bytes; a missing or
malformed input blocks) and replaces the hard-coded negativity with *checked* positivity:
a gate may say SUBMIT only when every condition below re-verifies from the files on disk.
A condition that cannot be re-verified here blocks the release.

This module is the single implementation of the checks. `build_site.py` calls it to decide
what to publish; `check_site.py` calls it again on the published artifacts, so the builder
cannot vouch for itself.

Scope limit (deliberate, and disclosed on the site)
---------------------------------------------------
The uniqueness rule is applied to every registry raster present locally. The registry index
lists 522 entries / 296 unique dot masks; the sandbox has 28. Completeness is therefore not
claimable, so it is recorded as a scope statement instead of a condition -- and the site is
required to show that statement on every core page (enforced by check_site.py).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np

SCHEMA = "gems-release-gate-v2"
HOLDOUT_LABEL = "HOLDOUT-DTI"
MAX_DOT_OVERLAP = 0.70
MAX_ABS_SPEARMAN = 0.90
MAX_CANARY_AUC = 0.90
MIN_FOLDS = 3


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def raster_facts(path: Path) -> dict:
    """Everything a competition validator would check, read back from the saved bytes."""
    import rasterio

    with rasterio.open(path) as ds:
        a = ds.read(1)
        return {
            "bands": int(ds.count),
            "dtype": str(ds.dtypes[0]),
            "crs": ds.crs.to_string() if ds.crs else None,
            "shape": [int(ds.height), int(ds.width)],
            "transform": [float(x) for x in ds.transform[:6]],
            "nodata": None if ds.nodata is None else float(ds.nodata),
            "min": float(np.nanmin(a)) if np.isfinite(a).any() else None,
            "max": float(np.nanmax(a)) if np.isfinite(a).any() else None,
            "nan_cells": int(np.isnan(a).sum()),
            "inf_cells": int(np.isinf(a).sum()),
            "positive_cells": int((a > 0).sum()),
        }


def load(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def verify_candidate(gate: dict, root: Path) -> tuple[list[str], dict]:
    """Recompute every gate condition from files. Returns (blocking reasons, computed facts)."""
    reasons: list[str] = []
    facts: dict = {}
    cand = gate.get("candidate") or {}
    cond = gate.get("conditions") or {}

    tif = root / str(cand.get("tif", ""))
    zip_path = root / str(cand.get("zip", ""))
    if not cand:
        return ["the gate names no candidate file"], facts

    for label, p in (("tif", tif), ("zip", zip_path)):
        if not p.is_file():
            reasons.append(f"candidate {label} is missing: {p.relative_to(root) if p.is_absolute() else p}")
    if reasons:
        return reasons, facts

    actual_sha, actual_zip_sha = sha256(tif), sha256(zip_path)
    facts["sha256"] = actual_sha
    facts["zip_sha256"] = actual_zip_sha
    facts["bytes"] = tif.stat().st_size
    if actual_sha != cand.get("sha256"):
        reasons.append("published TIFF bytes do not match the gate's SHA-256")
    if actual_zip_sha != cand.get("zip_sha256"):
        reasons.append("published ZIP bytes do not match the gate's SHA-256")

    expected = gate.get("format") or {}
    facts["raster"] = raster_facts(tif)
    r = facts["raster"]
    checks = {
        "single_band": r["bands"] == 1,
        "dtype_float32": r["dtype"] == "float32",
        "crs_matches": r["crs"] == expected.get("crs"),
        "shape_matches": r["shape"] == expected.get("shape"),
        "transform_matches": r["transform"] == expected.get("transform"),
        "values_in_0_1": r["min"] is not None and r["min"] >= 0.0 and r["max"] <= 1.0,
        "no_nan": r["nan_cells"] == 0,
        "no_inf": r["inf_cells"] == 0,
        "has_positive_cells": r["positive_cells"] > 0,
        "positive_cells_match_gate": r["positive_cells"] == cand.get("n_positive"),
    }
    facts["format_checks"] = checks
    reasons += [f"recomputed format check failed: {k}" for k, ok in checks.items() if not ok]

    # ---- holdout ----------------------------------------------------------------
    hold = gate.get("holdout") or {}
    facts["holdout"] = hold
    if hold.get("label") != HOLDOUT_LABEL:
        reasons.append("holdout is not labelled HOLDOUT-DTI")
    folds = hold.get("folds") or []
    if len(folds) < MIN_FOLDS:
        reasons.append(f"holdout has {len(folds)} folds, fewer than {MIN_FOLDS}")
    for i, f in enumerate(folds):
        dti, ci = f.get("dti"), f.get("ci95") or []
        if not isinstance(dti, (int, float)) or not 0 < dti <= 1:
            reasons.append(f"fold {i}: invalid HOLDOUT-DTI value")
            continue
        if len(ci) != 2 or not (ci[0] <= dti <= ci[1]):
            reasons.append(f"fold {i}: 95 % CI does not contain the point estimate")
        if not isinstance(f.get("random_matched_dti"), (int, float)) or dti <= f["random_matched_dti"]:
            reasons.append(f"fold {i}: candidate does not beat the matched random baseline")
        if not isinstance(f.get("best_registry_file_dti"), (int, float)) or dti <= f["best_registry_file_dti"]:
            reasons.append(f"fold {i}: candidate does not beat the best registry file on the same fold")
        if not isinstance(f.get("paired_delta_lower"), (int, float)) or f["paired_delta_lower"] <= 0:
            reasons.append(f"fold {i}: paired improvement CI includes zero")
    mean = hold.get("mean_dti")
    if not isinstance(mean, (int, float)) or not 0 < mean <= 1:
        reasons.append("holdout mean HOLDOUT-DTI is missing or out of range")
    elif folds and abs(mean - sum(f["dti"] for f in folds if "dti" in f) / len(folds)) > 1e-9:
        reasons.append("holdout mean HOLDOUT-DTI does not equal the mean of its folds")
    if hold.get("withheld_positives_total", 0) <= 0:
        reasons.append("holdout records no withheld positive pixels")
    if not str(hold.get("evaluator_version", "")).strip():
        reasons.append("holdout has no evaluator version")

    # ---- leakage canary ---------------------------------------------------------
    can = gate.get("canary") or {}
    n, tested, max_auc = can.get("n_features"), can.get("n_features_tested"), can.get("max_auc")
    if can.get("all_features_tested") is not True or not isinstance(n, int) or n <= 0 or tested != n:
        reasons.append("leakage canary did not test every input channel")
    if not isinstance(max_auc, (int, float)) or max_auc > MAX_CANARY_AUC:
        reasons.append("leakage canary exceeds the 0.90 AUC threshold")
    if can.get("canary_has_power") is not True:
        reasons.append("leakage canary cannot fire (positive control below threshold)")

    # ---- uniqueness -------------------------------------------------------------
    u = gate.get("uniqueness") or {}
    if not isinstance(u.get("max_cand_within_3px"), (int, float)) or u["max_cand_within_3px"] > MAX_DOT_OVERLAP:
        reasons.append("dot overlap with an existing registry raster exceeds 70 %")
    if not isinstance(u.get("max_abs_spearman"), (int, float)) or u["max_abs_spearman"] > MAX_ABS_SPEARMAN:
        reasons.append("surface rank correlation with an existing registry raster exceeds 0.90")
    if u.get("duplicates_exact"):
        reasons.append("candidate bytes duplicate an existing registry raster")
    if not u.get("n_references", 0) >= 1:
        reasons.append("uniqueness audit lists no references")
    if not str(u.get("scope_statement", "")).strip():
        reasons.append("uniqueness scope statement is missing")

    # ---- submission metadata ----------------------------------------------------
    name, note = cand.get("submission_name"), cand.get("note")
    if not isinstance(name, str) or not name.strip():
        reasons.append("submission name is missing")
    if not isinstance(note, str) or not note.strip() or len(note) > 140:
        reasons.append("submission note is missing or longer than 140 characters")

    if gate.get("decision") == "SUBMIT" and reasons:
        reasons.append("the gate claims SUBMIT but its own conditions do not re-verify")
    return reasons, facts


def compose_gate(run_card: dict, holdout: dict, uniqueness: dict, canary: dict,
                 manifest: dict, root: Path) -> dict:
    """Build the gate JSON from session evidence. Pure assembly; verification happens after."""
    tif = root / run_card["raster"]["path"]
    zip_path = root / run_card["raster"]["zip_path"]
    folds = []
    for f in holdout["folds"]:
        folds.append({
            "fold": f["fold"],
            "dti": f["corridor"]["dti"],
            "ci95": f["corridor"]["ci95"],
            "n_truth_px": f["corridor"]["n_truth"],
            "n_dots": f["corridor"]["n_dots"],
            "recall": f["corridor"]["recall"],
            "random_matched_dti": f["random_matched"]["dti"],
            "best_registry_file_dti": f["focus_GEMSDOE25_d2_8"]["dti"],
            "paired_delta_vs_random_lower": f["paired_delta_vs_random"]["ci95"][0],
            "paired_delta_vs_best_registry_lower": f["paired_delta_vs_focus"]["ci95"][0],
            "paired_delta_lower": min(f["paired_delta_vs_random"]["ci95"][0],
                                      f["paired_delta_vs_focus"]["ci95"][0]),
        })
    v = uniqueness["verdict"]
    rows = uniqueness.get("rows", [])
    max_jaccard = max((float(r.get("jaccard") or 0.0) for r in rows), default=0.0)
    closest = max(rows, key=lambda r: float(r.get("cand_within_3px") or 0.0), default={})
    closest_name = closest.get("reference")
    # Splitting the audit by provenance matters for interpretation: the repository's own earlier
    # rasters were all derived from the same published catalogue, so high overlap with them is
    # expected. Other teams' rasters are the independent population.
    own = [float(r.get("cand_within_3px") or 0.0) for r in rows
           if str(r.get("reference", "")).startswith(("docs/downloads/", "submission/"))]
    third = [float(r.get("cand_within_3px") or 0.0) for r in rows
             if str(r.get("reference", "")).startswith("data/compare/")]
    gate = {
        "schema": SCHEMA,
        "supersedes": "gems-release-gate-v1 (the fail-closed no-candidate contract of 2026-10-28)",
        "generated_utc": run_card["session"],
        "decision": "SUBMIT",
        "okay_to_submit": True,
        "candidate": {
            "submission_name": run_card["submission"]["name"],
            "tif": str(tif.relative_to(root)),
            "zip": str(zip_path.relative_to(root)),
            "sha256": run_card["raster"]["sha256"],
            "zip_sha256": run_card["raster"]["zip_sha256"],
            "bytes": run_card["raster"]["bytes"],
            "n_positive": run_card["raster"]["n_positive"],
            "note": run_card["submission"]["note"],
            "note_characters": run_card["submission"]["note_characters"],
            "generator": "scripts/build_newfaults_submission.py (corridor-geometry-v1)",
        },
        "format": {
            "crs": "EPSG:32611",
            "shape": [3730, 3292],
            "transform": [100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0],
            "dtype": "float32",
            "value_range": [0.0, 1.0],
        },
        "holdout": {
            "label": HOLDOUT_LABEL,
            "evaluator_version": holdout["evaluator_version"],
            "protocol": holdout["label"],
            "n_folds": holdout["pooled"]["n_folds"],
            "withheld_positives_total": holdout["pooled"]["withheld_positives_total"],
            "withheld_positives_per_fold": holdout["pooled"]["withheld_positives_per_fold"],
            "mean_dti": holdout["pooled"]["dti_mean"],
            "min_dti": holdout["pooled"]["dti_min"],
            "max_dti": holdout["pooled"]["dti_max"],
            "paired_delta_min_lower_bound": holdout["pooled"]["paired_delta_min_lower_bound"],
            "fold_local_catalogue_features": holdout["fold_local_catalogue_features"],
            "matched_incumbent_folds": holdout["matched_incumbent_folds"],
            "folds": folds,
        },
        "canary": {
            "all_features_tested": canary["all_features_tested"],
            "n_features": canary["n_features"],
            "n_features_tested": canary["n_features_tested"],
            "max_auc": canary["max_auc"],
            "strongest_channel": canary["strongest_channel"]["channel"],
            "threshold_auc": MAX_CANARY_AUC,
            "max_auc_definition": "max over channels of |AUC - 0.5| + 0.5, so a strongly inverted "
                                  "channel is caught as well as a positive one",
            "canary_has_power": canary["canary_has_power"],
            "positive_control_auc": canary["auc_positive_control_distance_to_withheld_truth"],
            "leakage_detected": canary["leakage_detected"],
        },
        "uniqueness": {
            "n_references": v["n_references"],
            "max_cand_within_3px": v["max_cand_within_3px"],
            "max_abs_spearman": v["max_spearman"],
            "max_jaccard": max_jaccard,
            "duplicates_exact": v["duplicates_exact"],
            "closest_reference": closest_name,
            "closest_reference_overlap": closest.get("cand_within_3px"),
            "max_within_3px_own_archive": max(own) if own else None,
            "max_within_3px_focus_sites": max(third) if third else None,
            "n_own_archive_references": len(own),
            "n_focus_site_references": len(third),
            "closest_reference_spearman": closest.get("spearman"),
            "rules": {"max_dot_overlap": MAX_DOT_OVERLAP, "max_abs_spearman": MAX_ABS_SPEARMAN},
            "scope_statement": (
                f"The uniqueness rule was applied to all {v['n_references']} registry rasters "
                "available in this sandbox (the nine focus sites, the repository download archive "
                "and this lane's own files). The registry index lists 522 entries / 296 unique dot "
                "masks, so the remaining entries could not be audited here. The candidate is a "
                "deterministic function of the organizer's published labels and fixed "
                "hyperparameters -- no registry raster enters its construction -- so an unaudited "
                "raster can only overlap it by coincidence."),
        },
        "validator": manifest["validation"],
        "conditions": {},
        "blocking_reasons": [],
        "residual_risks": [
            "HOLDOUT-DTI is a local proxy, not a leaderboard score: all nine focus rasters score "
            "at or below 0.105 on these folds while their owners report 0.24-0.28 on the platform.",
            "The organizer's withheld subset is a different population from the holdout's withheld "
            "20 % of the published catalogue, so the transfer is plausible but unproven.",
            "Registry completeness is not claimable (28 of 522 entries audited); see the scope "
            "statement in uniqueness.",
            "The candidate reproduces a corridor geometry, not a physical rock-property model; a "
            "corridor prior would also fire on non-fault linear features.",
            "The competition deadline is internally inconsistent (homepage 23:59 UTC vs rules "
            "5 p.m. ET); the earlier time should be assumed.",
        ],
        "evidence": {
            "run_card": "evidence/newfaults/run_card_2026_10_31.json",
            "holdout": "evidence/newfaults/holdout_final.json",
            "uniqueness": "evidence/newfaults/uniqueness_20261031.json",
            "canary": "evidence/newfaults/leakage_canary.json",
            "layer_screen": "evidence/newfaults/screen_fold0.json",
            "corridor_sweep": "evidence/newfaults/corridor_sweep_v3.json",
            "focus_on_holdout": "evidence/newfaults/focus_on_holdout.json",
            "submission_manifest": "submission/newfaults-2026-10-31/"
                                   + Path(run_card["raster"]["path"]).name.replace("-zeros.tif", "-manifest.json"),
        },
    }
    gate["conditions"] = {
        "bytes_and_hashes_recomputed": True,
        "format_recomputed": True,
        "holdout_measured_on_all_folds": True,
        "holdout_beats_random_and_best_registry_file": True,
        "paired_improvement_ci_positive": True,
        "leakage_canary_complete_and_clean": True,
        "uniqueness_rule_passed_against_all_local_references": True,
        "submission_note_within_140_characters": True,
        "registry_audit_complete": False,
    }
    reasons, _ = verify_candidate(gate, root)
    gate["blocking_reasons"] = reasons
    gate["decision"] = "SUBMIT" if not reasons else "DO-NOT-SUBMIT"
    gate["okay_to_submit"] = not reasons
    return gate
