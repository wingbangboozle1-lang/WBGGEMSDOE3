"""Dot emission, exact DTI evaluation and the strict submission writer.

Emission policy (each line is a decision traceable to an official statement or a
measured number in this repository):

1. **Binary 1.0 dots.** The metric is linear in ``p`` for the false-positive
   term and capped-at-1 for the true-positive term, so for a selected location
   ``p = 1`` is weakly optimal; a fractional value buys nothing.
2. **Zero inside the footprint away from dots.** A low continuous background is
   catastrophic under a pooled denominator: 5.17M cells at p = 0.01 add ~5·10^4
   FP mass, larger than ``0.8·|G|`` for any plausible |G|.
3. **NaN outside the footprint.** The official format says "data outside the
   bounds is null or nan"; the official sample submission uses NaN there.
4. **Nothing on the catalogue mask, nothing within the collar.** Masked cells are
   excluded from the score entirely (staff post, topic 11516) so a dot there is
   wasted; a dot *near* the mask is an active cell with no new-fault truth within
   its own kernel support and therefore pure false-positive mass.
5. **Minimum separation.** Dots are spaced at least ``NMS_PX`` apart so the
   budget covers distinct structure instead of thick blobs.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from scipy.ndimage import distance_transform_edt

from . import shared

DEFAULT_COLLAR_PX = 3.0
DEFAULT_NMS_PX = 2


def allowed_mask(footprint: np.ndarray, catalogue: np.ndarray,
                 collar_px: float = DEFAULT_COLLAR_PX,
                 valid: np.ndarray | None = None) -> tuple[np.ndarray, np.ndarray]:
    """Cells that may receive a dot: in footprint, off the mask, outside the collar."""
    d_cat = distance_transform_edt(~catalogue)
    ok = footprint & (d_cat > collar_px)
    if valid is not None:
        ok &= valid
    return ok, d_cat


def select_dots(score: np.ndarray, allowed: np.ndarray, k: int,
                nms_px: int = DEFAULT_NMS_PX, candidate_cap: int = 400_000) -> np.ndarray:
    """Greedy highest-score selection with Chebyshev separation ``nms_px``."""
    if k <= 0:
        return np.zeros(allowed.shape, bool)
    s = np.where(allowed & np.isfinite(score), score, -np.inf)
    flat = s.ravel()
    nz = np.flatnonzero(np.isfinite(flat) & (flat > -np.inf))
    if nz.size == 0:
        return np.zeros(allowed.shape, bool)
    if nz.size > candidate_cap:
        part = np.argpartition(-flat[nz], candidate_cap)[:candidate_cap]
        nz = nz[part]
    order = nz[np.argsort(-flat[nz], kind="stable")]
    w = allowed.shape[1]
    blocked = np.zeros(allowed.shape, bool)
    keep = np.empty(min(k, order.size), np.int64)
    n = 0
    for idx in order:
        r, c = divmod(int(idx), w)
        if blocked[r, c]:
            continue
        keep[n] = idx
        n += 1
        blocked[max(0, r - nms_px):r + nms_px + 1, max(0, c - nms_px):c + nms_px + 1] = True
        if n == keep.size:
            break
    dots = np.zeros(allowed.shape, bool)
    if n:
        dots.ravel()[keep[:n]] = True
    return dots


def evaluate(dots: np.ndarray, fold: dict) -> dict:
    """Exact official-formula DTI for a binary dot field on one fold."""
    metric = shared.shared_metric()
    known = fold["visible"]
    return metric.dti_binary(dots, fold["truth"], valid=fold["footprint"], known=known)


def pool(terms: list[dict]) -> dict:
    """Pool per-fold additive terms into one DTI (the leaderboard's aggregation)."""
    metric = shared.shared_metric()
    tp = sum(t["tp"] for t in terms)
    fp = sum(t["fp"] for t in terms)
    fn = sum(t["fn"] for t in terms)
    dti = metric.dti_from_components(tp, fp, fn)
    n_truth = int(sum(t["n_truth"] for t in terms))
    n_emitted = int(sum(t["n_emitted"] for t in terms))
    return dict(dti=float(dti), tp=float(tp), fp=float(fp), fn=float(fn),
                n_truth=n_truth, n_emitted=n_emitted,
                recall=float(tp / max(1e-12, n_truth)))


def assignment_blocks(terms: list[dict], block_side: int = 200) -> np.ndarray:
    """Per-spatial-block (tp, fp, fn, n_truth) rows for a paired block bootstrap.

    The official score is pooled, so the bootstrap resamples physical 20 km
    blocks and recomputes the pooled index on each resample; it is a conditional
    uncertainty statement about *this* holdout, not a leaderboard interval.
    """
    rows = []
    for fold, t in zip(terms["folds"], terms["terms"]):
        rows.append(t.get("blocks"))
    return np.concatenate([r for r in rows if r is not None], axis=0) if rows else np.zeros((0, 4))


def bootstrap_ci(block_terms: np.ndarray, draws: int = 1000, seed: int = 20261031) -> list:
    """95% percentile CI of the pooled DTI over physical spatial blocks."""
    metric = shared.shared_metric()
    if block_terms.size == 0:
        return [float("nan"), float("nan")]
    rng = np.random.default_rng(seed)
    n = block_terms.shape[0]
    out = np.empty(draws)
    for i in range(draws):
        pick = rng.integers(0, n, n)
        t = block_terms[pick].sum(axis=0)
        out[i] = metric.dti_from_components(t[0], t[1], t[2])
    return [float(np.quantile(out, 0.025)), float(np.quantile(out, 0.975))]


def block_terms(dots: np.ndarray, fold: dict, block_side: int = 200) -> np.ndarray:
    """(n_blocks, 4) additive terms on globally aligned blocks."""
    metric = shared.shared_metric()
    covers, q, _ = metric.max_cover(np.where(fold["active"], dots.astype(np.float64), 0.0),
                                    fold["truth"])
    h, w = dots.shape
    ncols = (w + block_side - 1) // block_side
    nrows = (h + block_side - 1) // block_side
    terms = np.zeros((nrows * ncols, 4))
    y, x = np.nonzero(fold["truth"])
    ids = (y // block_side) * ncols + (x // block_side)
    terms[:, 0] = np.bincount(ids, weights=covers, minlength=terms.shape[0])
    terms[:, 2] = np.bincount(ids, weights=1.0 - covers, minlength=terms.shape[0])
    terms[:, 3] = np.bincount(ids, minlength=terms.shape[0])
    y, x = np.nonzero(dots & fold["active"])
    ids = (y // block_side) * ncols + (x // block_side)
    terms[:, 1] = np.bincount(ids, weights=1.0 - q[y, x], minlength=terms.shape[0])
    return terms


def write_submission(path: Path, dots: np.ndarray, footprint: np.ndarray,
                     value: float = 1.0) -> dict:
    """Write a submission-compatible single-band float32 GeoTIFF.

    Inside the footprint: ``value`` on dots, 0.0 elsewhere (all finite, in [0,1]).
    Outside the footprint: NaN, per the official format text.
    """
    import rasterio
    from affine import Affine

    dots = np.asarray(dots, bool)
    footprint = np.asarray(footprint, bool)
    if dots.shape != footprint.shape:
        raise ValueError("shape mismatch")
    if (dots & ~footprint).any():
        raise ValueError("refusing to write dots outside the footprint")
    data = np.zeros(dots.shape, np.float32)
    data[dots] = np.float32(value)
    data[~footprint] = np.nan
    transform = Affine(100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(
        path, "w", driver="GTiff", height=data.shape[0], width=data.shape[1],
        count=1, dtype="float32", crs="EPSG:32611", transform=transform,
        nodata=np.nan, compress="deflate", predictor=2,
    ) as dst:
        dst.write(data, 1)
    return dict(path=str(path), sha256=shared.sha256_file(path),
                bytes=path.stat().st_size, dots=int(dots.sum()),
                value=value, outside="nan", inside="finite 0/1")
