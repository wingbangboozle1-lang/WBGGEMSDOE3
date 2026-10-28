"""Independent read-only artifact audit; not a model or a scoring evaluator."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import math
import sys

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

from .sources import download_github_file, sha256_file
from .template import ensure_template

ROOT = Path(__file__).resolve().parents[2]
SAMPLE_SHA = "2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc"
LABEL_SHA = "7ba308ccdc4418b31a178f4f1ef21aaa6e152e4028f2f6f64b01f7eb25ae4093"
WITNESS = {
    "repo": "buffedlizard55-lab/17GEMSDOE",
    "ref": "6fc71d19d49dca4960d5434bd81b6dd06fcc030a",
    "path": "docs/downloads/17GEMSDOE_E-proba-multiscale_20260930T044527Z.tif",
    "sha256": "ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be",
    "blob_sha1": "374c88b1da2b803e2ed160de467fd71ae114010d",
}
LATTICE = {
    "repo": "buffedlizard55-lab/GEMSDOE24",
    "ref": "07345ea0604953d7efb858d9cfbc21e20c7aca0b",
    "path": "inputs/calibration/13gems_20261001_r13-lattice-s5_v2_nan-outside.tif",
    "sha256": "b4570b406efec198eb2f4d142ad8d0d6184b14b66f2f52b5c4d697f0647dc9b2",
}
H31 = {
    "repo": "buffedlizard55-lab/GEMSDOE27",
    "ref": "bef7ae8e8f63b69d299c9214c75988c8f5055f9c",
    "path": "docs/downloads/gems27-h31-drcg-wl-celf28-20261026-cf8e1bbef244-allfinite.tif",
    "sha256": "2c002b02792419864bd3b29a218e543cb41e3f07b3b57c29ef35c6e39e184bfe",
    "blob_sha1": "b6d4e55739b982d2a2486b97886637b61b141767",
}
BASE = {
    "repo": "buffedlizard55-lab/GEMSDOE28",
    "ref": "9c1be21e8f1be707347f737e42abf62ea669c819",
    "path": "docs/downloads/gems28-h27-4-r1-solo-d2-8-20261003-8acb75e1f2cc-nan.tif",
    "sha256": "ab02300152248fdda04e988e2cd2a0c13f35eec42fcf670a15e8b76b19e24a73",
}


def source_url(entry: dict) -> str:
    return f"https://github.com/{entry['repo']}/blob/{entry['ref']}/{entry['path']}"


def raw_download_url(entry: dict) -> str:
    return f"https://github.com/{entry['repo']}/raw/{entry['ref']}/{entry['path']}"


def get_reference(entry: dict, cache: Path, name: str) -> Path:
    return download_github_file(entry["repo"], entry["ref"], entry["path"], cache / name,
                                entry["sha256"], entry.get("blob_sha1"))


def universal_witness(foot: np.ndarray, reference_positive: np.ndarray) -> dict:
    """Prove the literal forward-overlap block if every allowed cell is positive.

    Positivity is the shared registry's definition of a dot. This is a counting
    proof, not an assertion that a continuous probability is geologically a dot.
    Empty candidates and positive support outside the template footprint are not
    valid shared-writer candidates and are not considered by this proof.
    """
    foot = np.asarray(foot, dtype=bool)
    positive = np.asarray(reference_positive, dtype=bool)
    if foot.ndim != 2 or foot.shape != positive.shape:
        raise ValueError("witness and footprint grids must match")
    n = int(foot.sum())
    if not n:
        raise ValueError("empty footprint cannot establish a blocker")
    covered = int(np.count_nonzero(foot & positive))
    return {
        "footprint_cells": n,
        "witness_positive_inside": covered,
        "uncovered_cells": n - covered,
        "witness_positive_outside": int(np.count_nonzero(~foot & positive)),
        "inside_fraction": covered / n,
        "universal_blocker": covered == n,
        "logic": "Any nonempty in-footprint candidate has overlap 1.0 at distance zero if universal_blocker is true; therefore its 3-pixel overlap exceeds 0.70.",
    }


def binary_spearman(a: np.ndarray, b: np.ndarray, valid: np.ndarray) -> float | None:
    """Exact full-footprint Spearman for binary fields, including tied ranks."""
    a = np.asarray(a, bool)
    b = np.asarray(b, bool)
    valid = np.asarray(valid, bool)
    if a.shape != b.shape or a.shape != valid.shape:
        raise ValueError("binary rank inputs must share a grid")
    n = int(valid.sum())
    if not n:
        raise ValueError("empty footprint")
    na = int(np.count_nonzero(a & valid))
    nb = int(np.count_nonzero(b & valid))
    if na in (0, n) or nb in (0, n):
        return None
    both = int(np.count_nonzero(a & b & valid))
    p, q = na / n, nb / n
    rho = (both / n - p * q) / math.sqrt(p * (1 - p) * q * (1 - q))
    return float(max(-1.0, min(1.0, rho)))


def violates_literal_protocol(overlap: float, rank_correlation: float | None) -> bool:
    """Apply the project's conservative two-sided rank policy and the literal overlap stop.

    The current user wording says correlation > 0.90; it does not explicitly
    specify |rho|. The absolute-value check is a stricter project convention,
    not evidence that the upstream signed test violates the user's wording.
    """
    if not math.isfinite(overlap) or not 0.0 <= overlap <= 1.0:
        raise ValueError("overlap must be a finite fraction")
    if rank_correlation is not None and (not math.isfinite(rank_correlation) or abs(rank_correlation) > 1.0):
        raise ValueError("rank correlation must be finite and between -1 and 1")
    return overlap > 0.70 or (rank_correlation is not None and abs(rank_correlation) > 0.90)


def _read_aligned(path: Path, shape, crs, transform):
    with rasterio.open(path) as ds:
        if ds.count != 1 or ds.shape != shape or ds.crs != crs or ds.transform != transform:
            raise ValueError(f"wrong raster band count, shape, CRS, or affine transform: {path}")
        return ds.read(1), ds.dtypes[0], ds.nodata


def _receipt_row(entry: dict, arr: np.ndarray, dtype: str, nodata, foot: np.ndarray, file: Path):
    inside = arr[foot]
    finite_in = np.isfinite(inside)
    if not finite_in.all() or ((inside < 0) | (inside > 1)).any():
        raise ValueError(f"invalid finite or range values inside footprint: {file}")
    if not np.isin(inside, (0, 1)).all():
        raise ValueError(f"focus comparison requires binary predictions: {file}")
    # Compare decoded prediction content, not different TIFF encodings or outside-nodata modes.
    positive = np.isfinite(arr) & (arr > 0)
    if (positive & ~foot).any():
        raise ValueError(f"positive prediction outside the footprint: {file}")
    decoded = hashlib.sha256(np.packbits(positive[foot]).tobytes()).hexdigest()
    return {
        "site": entry["site"], "filename": Path(entry["path"]).name,
        "source": source_url(entry), "download_research_only": raw_download_url(entry),
        "claimed_by_owner_not_receipt": entry["owner_reported"],
        "leaderboard_estimate": None, "sha256": sha256_file(file),
        "decoded_support_sha256": decoded, "dtype": dtype,
        "nodata": "nan" if isinstance(nodata, float) and math.isnan(nodata) else nodata,
        "finite_inside": bool(finite_in.all()), "inside_min": float(inside.min()),
        "inside_max": float(inside.max()), "positive_pixels": int(positive.sum()),
        "nan_inside": int(np.isnan(inside).sum()),
        "whole_array_strict_finite_0_1": bool(np.isfinite(arr).all() and (arr >= 0).all() and (arr <= 1).all()),
        "comparison_scope": "other eight pinned focus-site historical rasters only; not a full registry clearance",
    }, positive


def audit(template_root: Path | None = None, cache: Path | None = None) -> dict:
    template = ensure_template(template_root)
    sys.path.insert(0, str(template / "src"))
    # Use exactly the shared template's literal positive-support, 3-pixel morphology.
    from gems57.uniqueness import _near

    cache = Path(cache) if cache else ROOT / ".cache" / "references"
    cache.mkdir(parents=True, exist_ok=True)
    sample = template / "data/official/sample_submission.tif"
    labels = template / "data/official/existing_faults.tif"
    if not sample.is_file() or sha256_file(sample) != SAMPLE_SHA:
        raise ValueError("sample template missing or SHA-256 differs from the public bridge pin")
    if not labels.is_file() or sha256_file(labels) != LABEL_SHA:
        raise ValueError("fault raster missing or SHA-256 differs from the public bridge pin")
    with rasterio.open(sample) as ds:
        shape, crs, transform = ds.shape, ds.crs, ds.transform
        foot = np.isfinite(ds.read(1))

    witness_file = get_reference(WITNESS, cache, "witness17.tif")
    witness, _, _ = _read_aligned(witness_file, shape, crs, transform)
    wpositive = np.isfinite(witness) & (witness > 0)
    proof = universal_witness(foot, wpositive)
    proof.update({"source": source_url(WITNESS), "sha256": sha256_file(witness_file),
                  "shared_definition": "finite and >0; forward overlap within Euclidean radius 3 pixels",
                  "registry_evidence": "57GEMSDOE evidence/uniqueness_session6_full_registry_696.json includes this raster"})
    index = json.loads((template / "evidence/uniqueness_session6_full_registry_696.json").read_text())
    if not any(row.get("sha256") == WITNESS["sha256"] for row in index.get("rows", [])):
        raise ValueError("witness not found in pinned shared registry evidence")

    lattice_file = get_reference(LATTICE, cache, "lattice.tif")
    lattice, _, _ = _read_aligned(lattice_file, shape, crs, transform)
    lattice_near = _near(np.isfinite(lattice) & (lattice > 0))
    lattice_result = {
        "source": source_url(LATTICE), "sha256": sha256_file(lattice_file),
        "footprint_within_3px": int(np.count_nonzero(lattice_near & foot)),
        "footprint_fraction_within_3px": float(lattice_near[foot].mean()),
        "footprint_uncovered": int(np.count_nonzero(foot & ~lattice_near)),
        "is_universal": bool(lattice_near[foot].all()),
    }
    manifest = json.loads((ROOT / "registry/focus_sites.json").read_text())
    rows, masks = [], {}
    for entry in manifest["sites"]:
        r = dict(entry, repo=f"buffedlizard55-lab/{entry['site']}")
        file = get_reference(r, cache, f"{r['site']}.tif")
        arr, dtype, nodata = _read_aligned(file, shape, crs, transform)
        row, mask = _receipt_row(r, arr, dtype, nodata, foot, file)
        rows.append(row)
        masks[r["site"]] = mask

    near = {site: _near(mask) for site, mask in masks.items()}
    for row in rows:
        site = row["site"]
        m = masks[site]
        if not m.any():
            raise ValueError(f"empty historical raster: {site}")
        comparisons = []
        for other in rows:
            if other["site"] == site:
                continue
            target = other["site"]
            comparisons.append({
                "site": target,
                "my_dots_within_3px": float(near[target][m].mean()),
                "spearman_binary_full_footprint": binary_spearman(m, masks[target], foot),
                "decoded_footprint_identical": bool(np.array_equal(m[foot], masks[target][foot])),
            })
        worst = max(comparisons, key=lambda x: x["my_dots_within_3px"])
        worst_rho = max((x for x in comparisons if x["spearman_binary_full_footprint"] is not None),
                        key=lambda x: abs(x["spearman_binary_full_footprint"]), default=None)
        row["comparisons"] = comparisons
        row["max_focus_overlap"] = worst["my_dots_within_3px"]
        row["max_focus_overlap_site"] = worst["site"]
        row["max_focus_rank_correlation"] = worst_rho["spearman_binary_full_footprint"] if worst_rho else None
        row["max_focus_rank_correlation_note"] = "signed value with greatest absolute magnitude"
        row["focus_literal_unique"] = not any(
            violates_literal_protocol(c["my_dots_within_3px"], c["spearman_binary_full_footprint"])
            for c in comparisons)
        row["literal_registry_unique"] = False if proof["universal_blocker"] else None
        row["ok_to_submit"] = False

    base_file = get_reference(BASE, cache, "GEMSDOE28-h27-base.tif")
    base_arr, _, _ = _read_aligned(base_file, shape, crs, transform)
    base = np.isfinite(base_arr) & (base_arr > 0)
    champion = masks["GEMSDOE32"]
    cat_arr, _, _ = _read_aligned(labels, shape, crs, transform)
    cat = (cat_arr > 0) & foot

    # Recheck a different site's upload recommendation against the mandatory
    # full-registry witness. Local format validity does not authorize a slot.
    from gems57.gates import format_report
    h31_file = get_reference(H31, cache, "GEMSDOE27-H31.tif")
    h31, _, _ = _read_aligned(h31_file, shape, crs, transform)
    h31_mask = np.isfinite(h31) & (h31 > 0)
    if not h31_mask.any():
        raise ValueError("GEMSDOE27 H31 review file has no predictions")
    h31_format = format_report(h31_file, sample, footprint=foot)
    # Do not save local filesystem paths in a reusable evidence artifact.
    h31_format.pop("path", None)
    h31_review = {
        "source": source_url(H31), "sha256": sha256_file(h31_file),
        "scope_of_other_site_claim": "The GEMSDOE27 landing page describes a 27-raster uniqueness check; it is not the full registered witness set.",
        "literal_forward_overlap_vs_registered_witness": float(_near(wpositive)[h31_mask].mean()),
        "positive_pixels": int(h31_mask.sum()), "format_report": h31_format,
        "verdict": "DO NOT SUBMIT: fails literal any-registry overlap gate",
        "surface_check": "not replayed", "holdout_check": "not replayed",
    }
    removed = base & ~champion
    distance = distance_transform_edt(~cat)
    mechanism = {
        "comparison": "GEMSDOE32 H33 B2 vs GEMSDOE28 H27-4 base; binary decoded arrays only",
        "base_source": source_url(BASE), "base_sha256": sha256_file(base_file),
        "base_positive": int(base.sum()), "champion_positive": int(champion.sum()),
        "champion_is_subset_of_base": bool(not (champion & ~base).any()),
        "base_pixels_removed": int(removed.sum()),
        "removed_min_distance_to_catalogue_pixels": float(distance[removed].min()) if removed.any() else None,
        "removed_max_distance_to_catalogue_pixels": float(distance[removed].max()) if removed.any() else None,
        "kept_min_distance_to_catalogue_pixels": float(distance[champion].min()) if champion.any() else None,
        "interpretation": "Observed pruning, not proof of score causality: hidden labels and authenticated score receipts are unavailable.",
    }
    return {
        "audit_version": "wbggems-preflight-v1", "checked_utc": datetime.now(timezone.utc).isoformat(),
        "evidence_class": "RASTER-ARTIFACT-MEASUREMENT; no new HOLDOUT-DTI or organizer-confirmed candidate score",
        "template": {"source": "https://github.com/buffedlizard55-lab/57GEMSDOE/tree/822a0ce5546c7b6749cdd82eb145b6b3e616603d", "sample_sha256": SAMPLE_SHA, "sample_provenance": "public owner mirror; not authenticated as an organizer download", "shape": list(shape), "crs": str(crs), "affine": list(transform)[:6]},
        "witness": proof, "lattice": lattice_result, "focus_sites": rows,
        "gems27_h31_conflicting_site_advice": h31_review,
        "h33_mechanism": mechanism,
        "status": "STOP_DUPLICATE_UNIVERSAL_WITNESS" if proof["universal_blocker"] else "INCOMPLETE_REGISTRY_AUDIT",
        "model_experiments_run": 0, "preplacement_surface_created": False,
        "candidate_dots_placed": False, "submission_tif_created": False,
        "weekly_slots_used": 0,
        "limitations": ["One witness proves a failure, not a complete current registry inventory.", "Owner scores have no authenticated submission-page receipts.", "No leakage canaries, holdout evaluation, or GeoTIFF validator were run on a new candidate because the mandatory stop precedes candidate generation.", "The data mirror is hash-pinned, but not authenticated as the official DrivenData download.", "The shared uniqueness tool checks signed positive rho, while the independent audit conservatively checks absolute rho. The user's wording says correlation > 0.90 but does not explicitly specify an absolute-value test; the convention needs clarification, not a claim of an upstream defect.", "The official outside-bounds null/NaN wording and the shared all-finite zero-outside writer differ; their interpretation and portal acceptance are unverified."],
    }
