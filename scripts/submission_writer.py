"""Shared writer import, not a private fork. Format packaging is not promotion.

Use only after a lane is assigned, fold-local holdout beats the incumbent,
feature canaries pass, and full-registry novelty is established. This module
intentionally has no autonomous competition-upload command.
"""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'vendor'))
from gems57.submission_writer import write_submission  # noqa: E402,F401
