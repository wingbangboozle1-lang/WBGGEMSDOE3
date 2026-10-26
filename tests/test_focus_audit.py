from __future__ import annotations

import numpy as np
import pytest

from scripts.audit_focus_site_masks import directed_overlap_within_radius, dilate_euclidean


def test_euclidean_dilation_uses_circular_not_square_neighborhood():
    reference = np.zeros((9, 9), dtype=bool)
    reference[4, 4] = True
    near = dilate_euclidean(reference, radius_px=3.0)

    assert bool(near[4, 7]) is True
    assert bool(near[7, 4]) is True
    assert bool(near[7, 7]) is False


def test_directed_overlap_counts_candidate_positives_only():
    reference = np.zeros((9, 9), dtype=bool)
    candidate = np.zeros((9, 9), dtype=bool)
    reference[4, 4] = True
    candidate[4, 7] = True
    candidate[0, 0] = True

    fraction = directed_overlap_within_radius(candidate, reference, radius_px=3.0)

    assert fraction == pytest.approx(0.5)


def test_directed_overlap_rejects_grid_mismatch():
    with pytest.raises(ValueError, match="share a grid"):
        directed_overlap_within_radius(np.zeros((2, 2)), np.zeros((3, 3)))
