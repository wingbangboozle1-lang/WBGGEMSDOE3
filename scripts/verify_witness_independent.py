#!/usr/bin/env python3
"""Independent re-measurement of the registered dense witness (2026-10-29).

This deliberately does NOT import the project's audit/uniqueness helpers. It reads the
two hash-pinned public owner-mirror rasters fetched by scripts/recheck_registry_witness.py
--fetch into .cache/verification/ and recomputes the facts the uniqueness gate relies on:

  * grid equality (shape, CRS, affine transform) between sample and witness;
  * the in-bounds footprint (finite sample cells with a valid mask);
  * how many footprint cells are positive (finite and > 0) in the witness;
  * the witness value distribution inside the footprint;
  * the value thresholds that a top-N ("dot = highest-N cells") reading would imply.

It writes measurements only. It does not decide eligibility, does not build a candidate,
does not run a holdout, and does not assert organizer provenance.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / ".cache/verification"
SAMPLE = CACHE / "owner-sample-submission.tif"
WITNESS = CACHE / "17gemsdoe-witness.tif"
OUT = ROOT / "evidence/witness_independent_stats_2026-10-29.json"
SAMPLE_PIN = "2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc"
WITNESS_PIN = "ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be"
# Dot counts of focus submissions (owner files); used only to pick top-N thresholds.
TOP_N = {"GEMSDOE32 B2 (37,654 dots)": 37654, "GEMSDOE30/25 d2-8 (44,090 dots)": 44090,
         "GEMSDOE24 d1-5 (60,069 dots)": 60069}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main() -> int:
    for path, pin in ((SAMPLE, SAMPLE_PIN), (WITNESS, WITNESS_PIN)):
        if not path.is_file():
            raise SystemExit(f"missing {path}; run scripts/recheck_registry_witness.py --fetch first")
        if sha256(path) != pin:
            raise SystemExit(f"SHA-256 mismatch for {path.name}")
    with rasterio.open(SAMPLE) as s, rasterio.open(WITNESS) as w:
        grid_equal = (s.shape == w.shape and s.crs == w.crs and s.transform == w.transform)
        if not grid_equal or s.count != 1 or w.count != 1:
            raise SystemExit("sample and witness grids differ or are not single-band")
        sample = s.read(1)
        witness = w.read(1).astype("float64")
        mask = s.read_masks(1) > 0
        footprint = np.isfinite(sample) & mask
        witness_finite = np.isfinite(witness)
        witness_pos = witness_finite & (witness > 0)
        inside = witness[footprint]
        out = {
            "schema": "witness-independent-stats-v1",
            "evidence_class": "RASTER MEASUREMENT (independent re-computation); not HOLDOUT-DTI, not a competition score",
            "checked_utc": datetime.now(timezone.utc).isoformat(),
            "inputs": {
                "sample": {"file": str(SAMPLE.relative_to(ROOT)), "sha256": SAMPLE_PIN,
                           "source": "https://github.com/buffedlizard55-lab/57GEMSDOE/blob/822a0ce5546c7b6749cdd82eb145b6b3e616603d/data/bridge/sample_submission.tif",
                           "provenance": "public owner mirror, not an organizer download"},
                "witness": {"file": "17gemsdoe-witness.tif", "sha256": WITNESS_PIN,
                            "source": "https://github.com/buffedlizard55-lab/17GEMSDOE/blob/6fc71d19d49dca4960d5434bd81b6dd06fcc030a/docs/downloads/17GEMSDOE_E-proba-multiscale_20260930T044527Z.tif",
                            "provenance": "public owner mirror, not an organizer download"},
            },
            "grid": {"shape": list(s.shape), "crs": str(s.crs), "transform": list(s.transform)[:6],
                     "dtype": s.dtypes[0], "grid_equal": bool(grid_equal)},
            "footprint_cells": int(footprint.sum()),
            "witness": {
                "finite_cells_all": int(witness_finite.sum()),
                "positive_cells_all": int(witness_pos.sum()),
                "positive_cells_inside_footprint": int((witness_pos & footprint).sum()),
                "footprint_cells_not_positive": int((footprint & ~witness_pos).sum()),
                "inside_min": float(inside.min()),
                "inside_max": float(inside.max()),
                "inside_mean": float(inside.mean()),
                "inside_quantiles": {str(q): float(np.quantile(inside, q))
                                     for q in (0.01, 0.1, 0.5, 0.9, 0.99, 0.999)},
                "inside_distinct_values": int(np.unique(inside).size),
                "inside_exact_zero": int((inside == 0).sum()),
            },
            "top_n_reading": {
                label: {"n": n, "value_threshold_for_top_n": float(np.partition(inside, -n)[-n])}
                for label, n in TOP_N.items()
            },
            "interpretation": (
                "Under the literal rule 'dot = finite value > 0', the witness has a dot in every "
                "footprint cell, so any nonempty in-footprint candidate has 100% directed 3-px "
                "overlap. The witness is a continuous score surface (non-binary values), so the "
                "literal 'dot' definition is the decision point, not a geological finding."
            ),
            "not_asserted": ["organizer provenance", "complete registry coverage",
                             "any candidate's overlap (no candidate exists)", "any score"],
        }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"Wrote {OUT.relative_to(ROOT)}: positive in footprint "
          f"{out['witness']['positive_cells_inside_footprint']}/{out['footprint_cells']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
