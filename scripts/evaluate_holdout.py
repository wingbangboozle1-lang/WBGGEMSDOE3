"""Unmodified shared instrument API; caller must construct fold-local features.

This API does not certify the caller's feature lineage. Withhold entire buffered
segments before deriving catalogue features. Never pass a full-label emission
as hide-and-recover evidence. See knowledge/protocol.md.
"""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'vendor'))
from gems57.evaluate_holdout import evaluate, pooled_summary, VERSION  # noqa: E402,F401
