"""Historical local metric helpers; the old holdout/CI wrappers are disabled.

This is not the pinned shared template. Its former hide_and_recover masked the
entire non-withheld domain rather than visible fault pixels, and its CI averaged
block DTIs instead of bootstrapping pooled metric terms. Do not use those
wrappers to score candidates. Use the pinned shared evaluator after prerequisites
are resolved; no private replacement is provided here.

WB-GEMS-DOE-3 historical distance-weighted Tversky Index (DTI).

The historical code attempted to implement the following published metric; its
implementation is disabled and is not evidence of organizer equivalence:

    k(d) = max(1 - d / R, 0),  R = 300 m = 3 px at 100 m resolution
    DTI(alpha=0.2, beta=0.8) = TP_w / (TP_w + 0.2 FP_w + 0.8 FN_w + eps)

Holdout protocol ("hide-and-recover"):
    * withhold whole fault segments with a buffer (positives hidden from the model)
    * derive catalogue-based features only from the VISIBLE faults
    * mask visible faults pixel-exactly
    * score pooled DTI on the held-out positives
    * 95% CI from spatially-blocked bootstrap over blocks

All numbers are labelled HOLDOUT-DTI (evaluator version, # withheld positives,
95% CI). A projection is never written as a score.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np

ALPHA = 0.2
BETA = 0.8
RADIUS_PX = 3.0  # 300 m at 100 m resolution
EPS = 1e-12


def _kernel(d: np.ndarray, radius: float = RADIUS_PX) -> np.ndarray:
    return np.maximum(1.0 - np.asarray(d, dtype=np.float64) / radius, 0.0)


def dti_components(pred: np.ndarray, truth: np.ndarray,
                   valid: Optional[np.ndarray] = None,
                   known: Optional[np.ndarray] = None) -> dict:
    """Disabled historical TP_w / FP_w / FN_w wrapper.

    `pred` : soft or binary predictions in [0, 1], same shape as `truth`
    `truth`: boolean ground-truth fault pixels
    `valid`: scored domain mask (defaults to all True)
    `known`: catalogue faults masked out of scoring (hide-and-recover positives)
    """
    raise RuntimeError("BLOCKED: historical local metric is not the required shared evaluator")


@dataclass
class HoldoutResult:
    evaluator_version: str
    n_withheld: int
    dti: float
    ci_lo: float
    ci_hi: float
    n_blocks: int
    block_dtis: list

    def to_dict(self):
        return {
            "evaluator_version": self.evaluator_version,
            "n_withheld_positives": self.n_withheld,
            "dti": round(self.dti, 6),
            "ci_95_lo": round(self.ci_lo, 6),
            "ci_95_hi": round(self.ci_hi, 6),
            "n_blocks": self.n_blocks,
            "block_dtis": [round(x, 6) for x in self.block_dtis],
        }


def spatial_block_ci(dti_values, n_blocks: int) -> tuple:
    """Retired: averaging block DTIs is not a pooled-component bootstrap."""
    raise RuntimeError("BLOCKED: historical block-mean CI is not the shared pooled evaluator")


def hide_and_recover(predictions: np.ndarray, truth: np.ndarray,
                     valid: Optional[np.ndarray],
                     withhold_mask: np.ndarray,
                     evaluator_version: str = "WB-GEMS-DOE-3-HIDE-RECOVER-v1.0") -> HoldoutResult:
    """Evaluate predictions on held-out fault segments.

    `withhold_mask` marks whole fault segments (with buffer) that are hidden from
    scoring inputs and used as the held-out positive set. Catalogue (known) faults
    are masked so they cannot leak into the score.
    """
    raise RuntimeError("BLOCKED: historical wrapper masks non-withheld pixels and does not implement the required shared holdout")
