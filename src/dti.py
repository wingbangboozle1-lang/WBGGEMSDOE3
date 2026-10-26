"""
DTI (Distance-based Target Index) metric.

Interpretation of the competition metric used for holdout evaluation:

The GEMS scoring metric rewards predictions that fall close to true geothermal
fault/target features within a spatial kernel, while penalising distant or
diffuse predictions.  This module implements a *pooled DTI* consistent with the
protocol description:

    pooled DTI = alpha * (prediction-side kernel-weighted hit rate)
               + beta  * (target-side kernel-weighted coverage)

with alpha = 0.2, beta = 0.8 and a 300 m triangular kernel
    w(d) = max(0, 1 - d / 300).

The target side (beta) dominates, so the score is essentially a recall-style
measure of how much of the true fault network is recovered within 300 m, with a
small precision-style penalty (alpha) for predictions far from any target.

NOTE: The official, closed-form competition metric is not public.  This is a
faithful, documented interpretation used *only* for holdout self-evaluation.
Any number produced here is labelled HOLDOUT-DTI and is never presented as an
organiser-confirmed score.  Replace `pooled_dti` with the official definition
when it becomes available.
"""

from __future__ import annotations

import numpy as np
from scipy import ndimage


def triangular_kernel_weights(distances_m: np.ndarray, bandwidth_m: float = 300.0) -> np.ndarray:
    """Triangular kernel weight w(d) = max(0, 1 - d / bandwidth)."""
    d = np.asarray(distances_m, dtype=np.float64)
    w = 1.0 - d / float(bandwidth_m)
    return np.clip(w, 0.0, 1.0)


def _distance_transform_inside(mask: np.ndarray, pixel_size_m: float) -> np.ndarray:
    """
    Distance (in metres) from every pixel to the nearest True pixel of `mask`.
    Pixels inside `mask` have distance 0.
    """
    mask = np.asarray(mask, dtype=bool)
    if not mask.any():
        return np.full(mask.shape, np.inf, dtype=np.float64)
    # distance_transform_edt returns distance to nearest zero; invert so we get
    # distance to nearest True (non-zero) pixel.
    dist_px = ndimage.distance_transform_edt(~mask)
    return dist_px * float(pixel_size_m)


def pooled_dti(
    prediction: np.ndarray,
    target: np.ndarray,
    pixel_size_m: float,
    bandwidth_m: float = 300.0,
    alpha: float = 0.2,
    beta: float = 0.8,
    pred_threshold: float = 0.5,
) -> dict:
    """
    Compute pooled DTI between a soft prediction raster and a binary target.

    Parameters
    ----------
    prediction : (H, W) float, values in [0, 1]
    target : (H, W) bool, True = geothermal fault / target present
    pixel_size_m : metres per pixel (assumes square pixels)
    bandwidth_m : kernel half-width in metres (default 300)
    alpha, beta : pooling weights (default 0.2 / 0.8)
    pred_threshold : threshold to binarise prediction for the precision side

    Returns
    -------
    dict with keys:
        dti          : pooled DTI score
        alpha_term   : prediction-side (precision-like) component
        beta_term    : target-side (coverage/recall-like) component
        alpha, beta, bandwidth_m, pred_threshold, pixel_size_m : echoes
    """
    prediction = np.asarray(prediction, dtype=np.float64)
    target = np.asarray(target, dtype=bool)

    if prediction.shape != target.shape:
        raise ValueError(f"shape mismatch: prediction {prediction.shape} vs target {target.shape}")

    if not np.all(np.isfinite(prediction)):
        raise ValueError("prediction contains NaN / inf")
    if prediction.min() < 0.0 or prediction.max() > 1.0:
        raise ValueError("prediction values must lie in [0, 1]")

    # Distance from every pixel to the nearest prediction pixel (above threshold)
    pred_mask = prediction >= pred_threshold
    dist_to_pred = _distance_transform_inside(pred_mask, pixel_size_m)

    # Distance from every pixel to the nearest target pixel
    dist_to_target = _distance_transform_inside(target, pixel_size_m)

    # --- Prediction side (precision-like): for pixels we flag, how close is a target?
    if pred_mask.any():
        # weight each flagged pixel by kernel(distance to nearest target)
        pred_weights = triangular_kernel_weights(dist_to_target[pred_mask], bandwidth_m)
        alpha_term = float(pred_weights.mean())
    else:
        alpha_term = 0.0

    # --- Target side (coverage / recall-like): for every target pixel, how close is a prediction?
    if target.any():
        tar_weights = triangular_kernel_weights(dist_to_pred[target], bandwidth_m)
        beta_term = float(tar_weights.mean())
    else:
        beta_term = 0.0

    dti = alpha * alpha_term + beta * beta_term

    return {
        "dti": float(dti),
        "alpha_term": float(alpha_term),
        "beta_term": float(beta_term),
        "alpha": float(alpha),
        "beta": float(beta),
        "bandwidth_m": float(bandwidth_m),
        "pred_threshold": float(pred_threshold),
        "pixel_size_m": float(pixel_size_m),
        "n_pred_pixels": int(pred_mask.sum()),
        "n_target_pixels": int(target.sum()),
    }


def dti_curve(
    prediction: np.ndarray,
    target: np.ndarray,
    pixel_size_m: float,
    thresholds: tuple[float, ...] = (0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9),
    **kwargs,
) -> list[dict]:
    """Evaluate pooled DTI across a range of prediction thresholds; returns list of dicts."""
    results = []
    for t in thresholds:
        r = pooled_dti(prediction, target, pixel_size_m, pred_threshold=t, **kwargs)
        r["pred_threshold"] = t
        results.append(r)
    return results


if __name__ == "__main__":
    # Smoke test: synthetic prediction & target
    rng = np.random.default_rng(0)
    H = W = 200
    target = np.zeros((H, W), dtype=bool)
    target[80:120, 80:120] = True  # a square fault patch
    dist = _distance_transform_inside(target, 30.0)
    # soft prediction concentrated near the target + some noise
    prediction = np.clip(1.0 - dist / 600.0 + 0.1 * rng.standard_normal((H, W)), 0, 1)
    res = pooled_dti(prediction, target, pixel_size_m=30.0)
    print(res)
