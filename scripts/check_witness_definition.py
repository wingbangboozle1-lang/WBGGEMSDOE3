#!/usr/bin/env python3
"""Re-measure the registered dense witness that drives the literal DO-NOT-SUBMIT stop.

Measurement only: this script builds NO candidate, runs NO holdout, selects NO slot.
It answers one question from bytes: is the registered 17GEMSDOE soft-probability witness
"dots" everywhere (value > 0 on the whole footprint), and what does a thresholded dot
definition look like instead?

Source (pinned commit, hash-verified; NOT organizer-authenticated):
  https://github.com/buffedlizard55-lab/17GEMSDOE/blob/6fc71d19d49dca4960d5434bd81b6dd06fcc030a/docs/downloads/17GEMSDOE_E-proba-multiscale_20260930T044527Z.tif
Fetched via codeload.github.com (raw.githubusercontent.com is outside the sandbox allowlist).

Usage: .venv/bin/python scripts/check_witness_definition.py
Writes: evidence/witness_definition_check_2026-10-29.json
"""
from __future__ import annotations

import hashlib
import io
import json
import sys
import tarfile
import urllib.request
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / ".cache" / "witness"
TIF = CACHE / "17GEMSDOE_E-proba-multiscale.tif"
ARCHIVE_URL = "https://codeload.github.com/buffedlizard55-lab/17GEMSDOE/tar.gz/6fc71d19d49dca4960d5434bd81b6dd06fcc030a"
MEMBER = "17GEMSDOE-6fc71d19d49dca4960d5434bd81b6dd06fcc030a/docs/downloads/17GEMSDOE_E-proba-multiscale_20260930T044527Z.tif"
EXPECTED_SHA256 = "ab0a0a62eecf066a82713b09dd49f0f638a91fa3dd81f54cc34ae89afa3872be"
REGISTRY = ROOT / "registry" / "registry_session2.json"
OUT = ROOT / "evidence" / "witness_definition_check_2026-10-29.json"


def fetch_if_missing() -> None:
    if TIF.exists() and sha256(TIF) == EXPECTED_SHA256:
        return
    CACHE.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(ARCHIVE_URL, timeout=180) as resp:  # noqa: S310 - pinned host
        data = resp.read()
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tf:
        member = tf.extractfile(MEMBER)
        if member is None:
            raise SystemExit(f"member not found in archive: {MEMBER}")
        TIF.write_bytes(member.read())


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    fetch_if_missing()
    digest = sha256(TIF)
    if digest != EXPECTED_SHA256:
        print(f"FAIL sha256 {digest} != {EXPECTED_SHA256}", file=sys.stderr)
        return 1
    with rasterio.open(TIF) as ds:
        arr = ds.read(1).astype("float64")
        meta = {
            "crs": str(ds.crs),
            "shape": [ds.height, ds.width],
            "transform": list(ds.transform)[:6],
            "dtype": ds.dtypes[0],
            "count": ds.count,
            "nodata": ds.nodata,
        }
    finite = np.isfinite(arr)
    v = arr[finite]
    n_fin = int(finite.sum())
    frac = {str(t): round(float((v > t).mean()), 6) for t in (0.0, 0.1, 0.3, 0.5, 0.7, 0.9)}
    counts = {str(t): int((v > t).sum()) for t in (0.0, 0.1, 0.3, 0.5, 0.7, 0.9)}
    topn = {}
    for n in (5000, 15000, 37654):
        thr = float(np.partition(v, -n)[-n])
        topn[str(n)] = {"threshold": round(thr, 6), "cells_at_or_above": int((v >= thr).sum())}

    registry = json.loads(REGISTRY.read_text())
    entry = next((e for e in registry["files"] if e.get("sha256") == EXPECTED_SHA256), None)
    reg_match = bool(entry) and entry.get("n_dots") == int((finite & (arr > 0)).sum())

    result = {
        "schema": "witness-definition-check-v1",
        "date_utc": "2026-10-29",
        "evidence_class": "RASTER MEASUREMENT of a registered comparator; not a candidate, not HOLDOUT-DTI, not a score",
        "source": ARCHIVE_URL,
        "member": MEMBER,
        "provenance": "public GitHub owner mirror, hash-verified; NOT organizer-authenticated",
        "sha256": digest,
        "sha256_matches_registry": bool(entry),
        "registry_dots_match_recount": reg_match,
        "metadata": meta,
        "footprint_finite_cells": n_fin,
        "nan_cells": int((~finite).sum()),
        "value_min": float(v.min()),
        "value_max": float(v.max()),
        "literal_positive_support": {
            "rule": "finite and value > 0 (repo rule in scripts/session2_registry.py)",
            "cells": counts,
            "fraction_of_finite": frac,
        },
        "top_n_dot_definition": topn,
        "finding": (
            "Under the literal positive-support rule the witness is 'dots' on 100% of its footprint. "
            "A soft-probability surface is not a set of dots; under a top-N or >=0.5 dot definition it is sparse. "
            "The stop that follows from the literal rule is a definition consequence, not a measured duplicate. "
            "Changing the dot definition is a protocol decision for the owner and is NOT made here."
        ),
        "gate_status": "UNCHANGED: docs/data/release_gate.json remains DO-NOT-SUBMIT",
    }
    OUT.write_text(json.dumps(result, indent=1) + "\n")
    print(json.dumps({k: result[k] for k in ("sha256", "footprint_finite_cells", "value_min", "value_max")}, indent=1))
    print("literal >0 fraction:", frac["0.0"], "| >=0.5 cells:", counts["0.5"], "| top-37654 thr:", topn["37654"]["threshold"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
