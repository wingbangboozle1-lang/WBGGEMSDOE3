#!/usr/bin/env python3
"""Rebuild a lane-local uniqueness registry from every locally restorable,
hash-pinned historical raster.

Sources (all byte-checked at fetch time; see data/ledger/index.json and
research/input_manifest.json):
  data/GEMSDOE*.tif            nine focus-site leaders (restore_comparators.py)
  data/ledger/*.tif            118 owner-ledger scored rasters (fetch_ledger_rasters.py)
  data/scored/*.tif            spacing-5 lattice null
  <template>/registry/rasters  19 rasters shipped inside the pinned shared template
  17GEMSDOE E-proba witness    fetched by pinned SHA (the IR-01 space-filling raster)
  submission/*.tif             this repo's own prior LST1 lane (included to prove
                               the new lane differs from it too)

Output: .cache/registry/<dots_sha>.npy packed masks + registry/cspes_registry_index.json.
The committed 522-file registry_index.json is never modified; coverage is reported exactly.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems_project.template import ensure_template  # noqa: E402
from gems_project.audit import WITNESS, get_reference  # noqa: E402
from gemsw.grid import EXPECTED_SHAPE  # noqa: E402

CACHE = ROOT / ".cache/registry"
CACHE.mkdir(parents=True, exist_ok=True)


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def gather_paths() -> list[tuple[str, Path]]:
    paths: list[tuple[str, Path]] = []
    for p in sorted((ROOT / "data").glob("GEMSDOE*.tif")):
        paths.append(("focus9", p))
    for p in sorted((ROOT / "data/ledger").glob("*.tif")):
        paths.append(("ledger", p))
    scored = ROOT / "data/scored"
    if scored.is_dir():
        for p in sorted(scored.glob("*.tif")):
            paths.append(("lattice", p))
    tpl = ensure_template()
    for p in sorted((tpl / "registry/rasters").glob("*.tif")):
        paths.append(("template19", p))
    for p in sorted((ROOT / "submission").glob("*.tif")):
        paths.append(("own-prior-lane", p))
    witness = get_reference(WITNESS, ROOT / ".cache/witness", "witness_17GEMS_Eproba.tif")
    paths.append(("dense-witness", witness))
    return paths


def main() -> int:
    with rasterio.open(ROOT / "data/raw/sample_submission.tif") as ds:
        foot = np.isfinite(ds.read(1))
        assert ds.shape == EXPECTED_SHAPE
    entries, skipped, seen = [], {}, set()
    for source, p in gather_paths():
        try:
            with rasterio.open(p) as ds:
                if ds.shape != EXPECTED_SHAPE:
                    skipped.append({"path": str(p.relative_to(ROOT)), "reason": f"shape {ds.shape}"})
                    continue
                if ds.crs is None or ds.crs.to_epsg() != 32611:
                    skipped.append({"path": str(p.relative_to(ROOT)), "reason": f"crs {ds.crs}"})
                    continue
                a = ds.read(1)
        except Exception as exc:  # noqa: BLE001
            skipped.append({"path": str(p), "reason": repr(exc)})
            continue
        dots = np.isfinite(a) & (a > 0) & foot
        n = int(dots.sum())
        dsha = hashlib.sha256(np.packbits(dots.ravel()).tobytes()).hexdigest()
        rel = str(p.relative_to(ROOT)) if str(p).startswith(str(ROOT)) else str(p)
        entry = {"source": source, "path": rel, "sha256": sha256_file(p),
                 "dots_sha256": dsha, "n_dots": n,
                 "dense": n > 1_000_000, "binary": bool(set(np.unique(a[np.isfinite(a)]).tolist()) <= {0.0, 1.0})}
        entries.append(entry)
        if dsha not in seen:
            seen.add(dsha)
            np.save(CACHE / f"{dsha}.npy", np.packbits(dots.ravel()))
    sparse = [e for e in entries if not e["dense"]]
    out = {
        "built_utc": "2026-10-27",
        "footprint_cells": int(foot.sum()),
        "n_files_indexed": len(entries),
        "n_unique_dot_masks": len(seen),
        "n_sparse_submission_masks": len({e['dots_sha256'] for e in sparse}),
        "n_dense_masks": sum(1 for e in entries if e["dense"]),
        "skipped": skipped,
        "files": entries,
        "coverage_note": ("Lane-local rebuild from hash-pinned restorable rasters; the committed "
                          "522-file/296-mask registry_index.json covers additional unrebuilt .cache/sites trees."),
    }
    (ROOT / "registry/cspes_registry_index.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: v for k, v in out.items() if k != "files"}, indent=1))
    print("first entries:", [(e["source"], e["n_dots"]) for e in entries[:6]])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
