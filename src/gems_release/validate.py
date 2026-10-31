"""Strict submission validation and the automated uniqueness gate.

Two independent gates, both fail-closed and both run without human input:

``validate_format``
    Every requirement transcribed from the official submission-format text, each
    one reported as its own named check with the measured value that decided it.
``uniqueness_audit``
    Compares the candidate against every locally available sibling raster and
    fails if the candidate is a byte duplicate, if more than ``MAX_OVERLAP`` of
    its dots fall within 3 px of one comparator's dots, or if its absolute Spearman
    rank correlation with a comparator exceeds ``MAX_RANK_RHO``.

Dot definition (recorded protocol revision, ``knowledge/protocol.md``):
a *dot* is a cell with a strictly positive value **that is not catalogue-masked**.
Continuous registry rasters are compared on their rank field (Spearman) and on
their own top-N support, never by the literal "value > 0" rule, because that rule
declares a smooth probability surface to be a 5.17M-dot map and makes the 70 %
overlap test vacuous for every possible submission.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from scipy.ndimage import distance_transform_edt

from . import shared

MAX_OVERLAP = 0.70
MAX_RANK_RHO = 0.90
EPSG = 32611
SHAPE = (3730, 3292)
TRANSFORM = (100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)


def _spearman(a: np.ndarray, b: np.ndarray) -> float:
    """Spearman rank correlation with *average* ranks for ties.

    ``np.argsort(np.argsort(x))`` is NOT a valid rank transform for tied data:
    NumPy 2's stable default resolves ties by position, which injects a spurious
    monotone trend in index order. On two independent 2 %-density binary fields
    that artefact returns rho ~ 0.92 instead of ~0.00. Average ranks (SciPy
    ``rankdata``) are the correct tie handling and reproduce
    ``scipy.stats.spearmanr`` exactly (unit-tested).
    """
    from scipy.stats import rankdata

    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    if a.size < 100 or a.size != b.size:
        return float("nan")
    ra = rankdata(a) - (a.size + 1) / 2.0
    rb = rankdata(b) - (b.size + 1) / 2.0
    den = np.sqrt((ra @ ra) * (rb @ rb))
    return float(ra @ rb / den) if den > 0 else float("nan")


def read_raster(path: Path) -> np.ndarray:
    import rasterio

    with rasterio.open(path) as src:
        return src.read(1)


def validate_format(path: Path, footprint: np.ndarray, catalogue: np.ndarray,
                    collar_px: float = 3.0) -> dict:
    """Fail-closed format validation against the official submission text."""
    import rasterio

    checks = {}
    detail = {}
    with rasterio.open(path) as src:
        checks["single_band"] = src.count == 1
        checks["dtype_float32"] = src.dtypes[0] == "float32"
        checks["shape_3730x3292"] = (src.height, src.width) == SHAPE
        checks["crs_epsg32611"] = str(src.crs) == f"EPSG:{EPSG}"
        checks["geotransform_match"] = tuple(src.transform)[:6] == TRANSFORM
        arr = src.read(1)
        nodata = src.nodata
    detail.update(nodata=str(nodata), dtype=str(arr.dtype))

    finite = np.isfinite(arr)
    inside = footprint
    checks["finite_inside_footprint"] = bool(finite[inside].all())
    checks["nan_outside_footprint"] = bool((~finite[~inside]).all())
    vals = arr[inside]
    checks["values_finite_and_in_0_1"] = bool(np.isfinite(vals).all()
                                              and (vals >= 0.0).all() and (vals <= 1.0).all())
    dot = inside & finite & (arr > 0)
    detail.update(in_footprint_min=float(vals.min()), in_footprint_max=float(vals.max()),
                  in_footprint_cells=int(inside.sum()), finite_cells=int(finite.sum()),
                  dots=int(dot.sum()), dot_value=sorted({float(v) for v in arr[dot]})[:5])
    checks["has_dots"] = int(dot.sum()) > 0
    checks["no_dot_on_catalogue_mask"] = bool(not (dot & catalogue).any())
    if dot.any():
        d_cat = distance_transform_edt(~catalogue)
        min_d = float(d_cat[dot].min())
        detail["min_distance_to_catalogue_px"] = min_d
        checks["dots_outside_collar"] = bool(min_d > collar_px)
    else:
        detail["min_distance_to_catalogue_px"] = None
        checks["dots_outside_collar"] = False
    detail["sha256"] = shared.sha256_file(path)
    detail["bytes"] = path.stat().st_size
    passed = bool(all(checks.values()))
    return {"passed": passed, "checks": checks, "detail": detail,
            "rules_source": shared.SOURCES["metric"]["url"]}


def _dots_of(arr: np.ndarray, footprint: np.ndarray, mask: np.ndarray,
             top_n: int | None = None) -> np.ndarray:
    ok = footprint & np.isfinite(arr) & (arr > 0) & ~mask
    if top_n is not None and ok.sum() > top_n:
        vals = np.where(ok, arr, -np.inf)
        flat = vals.ravel()
        idx = np.argpartition(-flat, top_n)[:top_n]
        out = np.zeros(arr.size, bool)
        out[idx] = True
        return out.reshape(arr.shape)
    return ok


def uniqueness_audit(candidate: Path, footprint: np.ndarray, catalogue: np.ndarray,
                     comparators: list[dict], step: int = 7,
                     max_overlap: float = MAX_OVERLAP,
                     max_rho: float = MAX_RANK_RHO) -> dict:
    """Automated duplicate/lane audit against every listed comparator."""
    import rasterio

    with rasterio.open(candidate) as src:
        cand = src.read(1)
    cand_dots = _dots_of(cand, footprint, catalogue)
    cand_sha = shared.sha256_file(candidate)
    # Dot-mask of the study area for the correlation test (exclude masked cells).
    test_mask = footprint & ~catalogue
    idx = np.flatnonzero(test_mask.ravel())
    idx = idx[::step]
    cand_v = np.where(np.isfinite(cand.ravel()[idx]), cand.ravel()[idx], 0.0)

    rows = []
    for comp in comparators:
        path = Path(comp["path"])
        if not path.is_file():
            rows.append({"site": comp.get("site"), "file": comp.get("name", path.name),
                         "status": "missing", "path": str(path)})
            continue
        with rasterio.open(path) as src:
            arr = src.read(1)
            shape_ok = (src.height, src.width) == SHAPE and str(src.crs) == f"EPSG:{EPSG}"
            tr_ok = tuple(src.transform)[:6] == TRANSFORM
        rec = {"site": comp.get("site"), "file": comp.get("name", path.name),
               "sha256": shared.sha256_file(path), "grid_compatible": bool(shape_ok and tr_ok)}
        rec["byte_identical"] = bool(rec["sha256"] == cand_sha)
        if not (shape_ok and tr_ok):
            rec["status"] = "grid_mismatch"
            rows.append(rec)
            continue
        n_cand_dots = int(cand_dots.sum())
        comp_dots = _dots_of(arr, footprint, catalogue, top_n=n_cand_dots)
        rec["n_dots"] = int(comp_dots.sum())
        rec["values"] = "binary" if np.isin(arr[np.isfinite(arr)], [0.0, 1.0]).all() else "continuous"
        if cand_dots.any() and comp_dots.any():
            d = distance_transform_edt(~comp_dots)
            ov = float((d[cand_dots] <= 3.0).mean())
            inter = int((cand_dots & comp_dots).sum())
            union = int((cand_dots | comp_dots).sum())
            rec["overlap_within_3px"] = ov
            rec["jaccard"] = float(inter / max(1, union))
        else:
            rec["overlap_within_3px"] = None
            rec["jaccard"] = None
        comp_v = np.where(np.isfinite(arr.ravel()[idx]), arr.ravel()[idx], 0.0)
        rec["spearman_rho"] = _spearman(cand_v, comp_v)
        rec["status"] = "compared"
        rows.append(rec)

    compared = [r for r in rows if r.get("status") == "compared"]
    worst_overlap = max((r["overlap_within_3px"] for r in compared
                         if r["overlap_within_3px"] is not None), default=0.0)
    worst_rho = max((abs(r["spearman_rho"]) for r in compared
                     if r["spearman_rho"] is not None), default=0.0)
    checks = {
        "no_byte_duplicate": not any(r.get("byte_identical") for r in compared),
        f"max_overlap_below_{max_overlap}": worst_overlap < max_overlap,
        f"max_abs_rho_below_{max_rho}": worst_rho <= max_rho,
        "at_least_one_comparator": bool(compared),
    }
    return {"passed": bool(all(checks.values())), "checks": checks,
            "worst_overlap_within_3px": worst_overlap, "worst_abs_spearman": worst_rho,
            "candidate_dots": int(cand_dots.sum()), "candidate_sha256": cand_sha,
            "thresholds": {"max_overlap": max_overlap, "max_rank_rho": max_rho},
            "dot_definition": "value > 0 and not catalogue-masked; comparators are "
                              "restricted to their own top-N support where N is the "
                              "candidate's dot count",
            "comparators": rows}
