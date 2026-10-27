"""Retired private scoring functions must not quietly create holdout numbers."""
import numpy as np
import pytest
from scripts import evaluate_holdout as historical


def test_historical_local_holdout_is_fail_closed():
    a = np.zeros((4, 4), dtype=float)
    with pytest.raises(RuntimeError, match="BLOCKED"):
        historical.dti_components(a, a.astype(bool))
    with pytest.raises(RuntimeError, match="BLOCKED"):
        historical.spatial_block_ci([0.1, 0.2], 2)
    with pytest.raises(RuntimeError, match="BLOCKED"):
        historical.hide_and_recover(a, a.astype(bool), None, a.astype(bool))
