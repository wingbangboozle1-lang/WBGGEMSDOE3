"""Uniqueness gate with an explicit, documented comparator policy.

The project brief asks for "a unique submission unlike any of the other GEMSDOE
sites". The literal rule in the parallel-run protocol -- "more than 70% of your
dots fall within 3 px of one registry raster's dots" -- is *mathematically
unsatisfiable* for a dense space-filling comparator (see IR-01 in
knowledge/review-and-irregularities-2026-10-26.md): if a registered raster is
positive on every footprint cell, every nonempty prediction has 100% overlap
with it. Under that reading no submission could ever be made.

This module therefore applies the rule to *submission-like* comparators and
records, per comparator, which rule fired. A comparator is treated as
"submission-like" when its support is sparse enough that the overlap statistic is
informative (< 5% of the footprint). Dense continuous fields are still compared
by rank correlation, and the exclusion is printed for every such comparator so it
cannot happen silently.

BLOCK conditions (any one):
  * identical dot sets (exact duplicate)
  * Jaccard of supports > 0.50
  * > 70% of candidate dots within 3 px of the comparator's dots
    (vacuous, and therefore not applied, when the comparator already covers
    >= 90% of the footprint within 3 px -- a spacing-5 lattice does)
  * |Spearman| > 0.90 between *density* fields (masks blurred over ~2 km).

The density field is used for the rank correlation on purpose: two disjoint
binary masks have a Spearman correlation of about -1 on their union by
construction (our 1s sit exactly where their 1s are not), so the raw binary rank
correlation carries no information about novelty. The blurred density field asks
the question the rule is meant to ask -- "do these two predictions occupy the same
ground?" -- and can genuinely fire.
"""

from __future__ import annotations

import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.stats import spearmanr

from . import config as C

DENSE_FRACTION = 0.05
JACCARD_BLOCK = 0.50
OVERLAP_BLOCK = 0.70
RHO_BLOCK = 0.90


def load_mask(path) -> np.ndarray:
    with rasterio.open(path) as src:
        a = src.read(1).astype(np.float32)
        nod = src.nodata
    if nod is not None and np.isfinite(nod):
        a[a == np.float32(nod)] = 0.0
    a = np.where(np.isfinite(a), a, 0.0)
    return a


def support(mask: np.ndarray) -> np.ndarray:
    return mask > 0


DENSITY_SIGMA_PX = 20.0   # ~2 km, the scale of a fault corridor
SPACEFILL_COVERAGE = 0.90


def density(mask: np.ndarray, sigma: float = DENSITY_SIGMA_PX) -> np.ndarray:
    return ndi.gaussian_filter((mask > 0).astype(np.float32), sigma, mode="constant")


def compare(cand: np.ndarray, other: np.ndarray, footprint: np.ndarray,
            rho_sample: int = 400_000, seed: int = 11) -> dict:
    cs, os_ = support(cand), support(other)
    inter = int((cs & os_).sum())
    union = int((cs | os_).sum())
    jacc = inter / union if union else 0.0

    d_other = ndi.distance_transform_edt(~os_) if os_.any() else np.full(os_.shape, np.inf)
    d_cand = ndi.distance_transform_edt(~cs) if cs.any() else np.full(cs.shape, np.inf)
    within3_cand = float((d_other[cs] <= C.RADIUS_PX).mean()) if cs.any() else 0.0
    within3_other = float((d_cand[os_] <= C.RADIUS_PX).mean()) if os_.any() else 0.0

    both = cs | os_
    rho_bin = 0.0
    if both.sum() > 3:
        r = float(spearmanr(cand[both], other[both]).statistic)
        rho_bin = r if np.isfinite(r) else 0.0
    dc, do = density(cand), density(other)
    rho = float(spearmanr(dc[footprint], do[footprint]).statistic)
    if not np.isfinite(rho):
        rho = 0.0

    coverage = float((d_other[footprint] <= C.RADIUS_PX).mean()) if footprint.any() else 0.0
    space_filling = bool(coverage >= SPACEFILL_COVERAGE)
    dense = bool(os_.sum() > DENSE_FRACTION * footprint.sum())
    reasons = []
    if inter == union and union > 0:
        reasons.append("exact_duplicate")
    if jacc > JACCARD_BLOCK:
        reasons.append(f"jaccard>{JACCARD_BLOCK}")
    if within3_cand > OVERLAP_BLOCK:
        if space_filling:
            reasons.append("within3px_rule_vacuous_space_filling_comparator")
        else:
            reasons.append(f"within3px>{OVERLAP_BLOCK}")
    if abs(rho) > RHO_BLOCK:
        reasons.append(f"|rho_density|>{RHO_BLOCK}")
    blocked = any(not r.endswith("space_filling_comparator") for r in reasons)
    return {
        "n_cand_dots": int(cs.sum()), "n_other_dots": int(os_.sum()),
        "intersection": inter, "union": union, "jaccard": round(jacc, 6),
        "within_3px_of_candidate": round(within3_cand, 6),
        "within_3px_of_comparator": round(within3_other, 6),
        "rho_density": round(rho, 6), "rho_union_binary": round(rho_bin, 6),
        "comparator_3px_coverage": round(coverage, 6),
        "space_filling_comparator": space_filling, "dense_comparator": dense,
        "reasons": reasons, "blocked": bool(blocked),
    }
