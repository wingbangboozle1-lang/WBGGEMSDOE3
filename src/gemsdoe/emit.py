"""Metric-aware emission: turn a fault-likelihood field into a submission surface.

Everything here follows from the official metric, algebraically:

    DTI = TP_w / ( alpha*(TP_w + FP_w) + beta*|G| ),  alpha=0.2, beta=0.8

Consequences (each tested numerically in tests/test_gemdoe_metric.py):

1. For a *fixed support* S, scaling the surface up by c>0 changes DTI to
   c*TP / (0.2*c*(TP+FP) + 0.8|G|), which is strictly increasing in c.
   => On a chosen support, the optimal surface is the indicator 1_S (level 1.0).
   Soft probabilities are only useful as a *hedge* when support is uncertain.

2. Adding mass at a cell x is worth it only if the expected kernel-weighted
   credit there exceeds 0.2*TP*(1-k_x)/(0.2*FP+0.8|G|). With realistic values
   (TP~0.5|G|, FP~0.2|G|) that is a ~20-25% chance that a truth pixel lies
   within the 300 m kernel. This sets the operating point of the support.

3. Pixels on the public catalogue can never earn credit on the initial prize
   round (the scored faults are by construction *not* in the public catalogue),
   so they are pure false-positive mass and are suppressed.

`catalogue_suppression` implements point 3; `threshold_sweep` selects the
operating point of point 2 on the hide-and-recover surrogate.
"""

from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi

from . import config as C


def quantile_threshold(prob: np.ndarray, valid: np.ndarray, support_fraction: float) -> float:
    """Threshold that keeps `support_fraction` of the valid cells."""
    v = prob[valid]
    q = 1.0 - float(support_fraction)
    return float(np.quantile(v, q))


def binary_support(prob: np.ndarray, valid: np.ndarray, threshold: float,
                   min_size: int = 0) -> np.ndarray:
    s = valid & (prob >= threshold)
    if min_size > 0:
        lab, n = ndi.label(s, structure=np.ones((3, 3), bool))
        if n:
            sizes = np.bincount(lab.ravel())
            keep = sizes >= min_size
            keep[0] = False
            s = keep[lab]
    return s


def emit(prob: np.ndarray, support: np.ndarray, level: float = 1.0,
         halo: int = 0, halo_scale: float = 0.5) -> np.ndarray:
    """Indicator surface on `support` (official range [0,1]); optional soft halo ring."""
    out = np.zeros(prob.shape, dtype=np.float32)
    out[support] = np.float32(level)
    if halo > 0:
        ring = ndi.binary_dilation(support, iterations=halo) & ~support
        out[ring] = (np.float32(halo_scale) * prob[ring]).astype(np.float32)
    return np.clip(out, 0.0, 1.0)


def catalogue_suppression(support: np.ndarray, catalogue: np.ndarray,
                          radius_px: int = 0) -> np.ndarray:
    """Remove support cells on (or within `radius_px` of) the public catalogue.

    radius_px=0 removes only catalogue cells themselves, which is the set that is
    *provably* worth zero TP credit in the initial prize round. Larger radii also
    remove potential extension/relay targets, so they must be justified on the
    holdout rather than assumed.
    """
    if radius_px <= 0:
        return support & ~catalogue
    kill = ndi.binary_dilation(catalogue, iterations=radius_px)
    return support & ~kill


def despeckle(support: np.ndarray, keep_components: int = 0) -> np.ndarray:
    """Drop the smallest connected components (isolated single-pixel noise)."""
    if keep_components <= 0:
        return support
    lab, n = ndi.label(support, structure=np.ones((3, 3), bool))
    if n == 0:
        return support
    sizes = np.bincount(lab.ravel())
    sizes[0] = 0
    order = np.argsort(sizes)[::-1][:keep_components]
    keep = np.zeros(sizes.size, bool)
    keep[order] = True
    keep[0] = False
    return keep[lab]


def expected_score(tp: float, mass_: float, n_truth: float,
                   alpha: float = C.ALPHA, beta: float = C.BETA) -> float:
    """DTI from the three aggregate terms (FP approximated by total mass)."""
    fp = max(mass_ - tp, 0.0)  # mass that earns no credit; conservative (FP >= mass-TP)
    return tp / (alpha * (tp + fp) + beta * n_truth + C.EPS)


def score_from_hit_rate(hit_rate: float, mass_: float, n_truth: float) -> float:
    """DTI implied by an assumed kernel-weighted hit rate and a fixed mass."""
    tp = hit_rate * mass_
    return expected_score(tp, mass_, n_truth)


def required_hit_rate(target_dti: float, mass_: float, n_truth: float) -> float:
    """Inverse of score_from_hit_rate: hit rate needed to reach `target_dti`."""
    # target = h*m / (0.2*(h*m + m) + 0.8*n)  =>  h = target*(0.2*m + 0.8*n) / (m*(1 - 0.2*target))
    return target_dti * (0.2 * mass_ + 0.8 * n_truth) / (mass_ * (1.0 - 0.2 * target_dti))


def optimal_mass_for(hit_rate: float, n_truth: float, target_dti: float | None = None) -> dict:
    """Score as a function of support size at a fixed hit rate.

    DTI(m) = h*m / (0.2*m*(1+h) + 0.8*n) is *increasing* in m only while the hit
    rate is held constant; because hit rate falls as the support grows, the
    optimum is empirical (selected on the surrogate), not analytic.
    """
    out = {}
    for frac in (0.001, 0.002, 0.003, 0.005, 0.01, 0.02, 0.05):
        m = frac * C.FOOTPRINT_PIXELS
        out[frac] = score_from_hit_rate(hit_rate, m, n_truth)
    return out
