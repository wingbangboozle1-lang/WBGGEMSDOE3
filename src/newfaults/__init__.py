"""New-fault detection lane (2026-10-31 session).

Goal: predict fault pixels of the *withheld* expert-compiled fault set that the
organizer scores in Phase 1 (official rules section 1.1: "submissions will be
evaluated against a privately withheld subset of the original new fault dataset
compiled by expert reviewers").

Everything here operates on the official, hash-pinned competition rasters that the
session restored from owner mirrors (see ``registry/data_manifest.json``):

* ``data/official/labels.tif``            catalogue given for training (60,988 px)
* ``data/official/training_features.tif`` 19 official feature bands
* ``data/official/sample_submission.tif`` official submission footprint (5,167,373 px)

The lane is deliberately separate from the archived, blocked code paths in
``src/gemsw`` (whose writers/auditers raise by design).  Reused without change:
``src/gemsw/metric.py`` -- the verified distance-weighted Tversky implementation.
"""

__all__ = ["data", "features", "holdout", "model", "emit", "audit"]
