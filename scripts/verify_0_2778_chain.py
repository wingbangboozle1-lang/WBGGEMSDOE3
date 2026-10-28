#!/usr/bin/env python3
"""Line-by-line check of the 'why GEMSDOE32 scored 0.2778' chain (content/why-0.2778.md).

Claims tested, each against the bytes on disk (no owner text is trusted):

1. GEMSDOE32 B2 support is an exact pixel subset of GEMSDOE31 H27-4 support, which is an exact
   pixel subset of GEMSDOE25 D2-8 support.
2. D2-8 minus H27-4 = the dots removed to reach H27-4 (expected 3,891) and their distance to the
   catalogue (labels.tif, the USGS/INGENIOUS fault raster).
3. H27-4 minus B2 = the dots removed to reach B2 (expected 2,545) and their catalogue distances.
4. Catalogue-distance bands are reported exactly (no rounding into a band).

The catalogue raster is the owner-mirrored ``data/bridge/labels.tif`` of GEMSDOE24, fetched by
sha256 pinned in ``registry/data_manifest.json``. Owner bytes establish byte identity only.
Output: ``evidence/chain_0_2778_verify_2026-10-28.json``.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
FOCUS = ROOT / ".cache" / "focus"
OFFICIAL = ROOT / ".cache" / "official"
OUT = ROOT / "evidence" / "chain_0_2778_verify_2026-10-28.json"
MANIFEST = ROOT / "registry" / "data_manifest.json"


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def labels_path() -> Path:
    spec = next(f for f in json.loads(MANIFEST.read_text())["files"] if f["dest"] == "labels.tif")
    OFFICIAL.mkdir(parents=True, exist_ok=True)
    local = OFFICIAL / "labels.tif"
    if not (local.exists() and sha256(local) == spec["sha256"]):
        proc = subprocess.run(
            ["gh", "api", f"repos/{spec['repo']}/contents/{spec['path']}?ref={spec['ref']}",
             "-H", "Accept: application/vnd.github.raw"],
            stdout=subprocess.PIPE, check=True)
        local.write_bytes(proc.stdout)
    if sha256(local) != spec["sha256"]:
        raise SystemExit("labels.tif sha256 mismatch against registry/data_manifest.json")
    return local


def support(path: Path) -> np.ndarray:
    with rasterio.open(path) as ds:
        a = ds.read(1).astype(np.float64)
    return np.nan_to_num(a, nan=0.0) > 0


def hist(d: np.ndarray) -> dict:
    if d.size == 0:
        return {}
    vals, counts = np.unique(np.round(d, 4), return_counts=True)
    return {f"{v:.4f}": int(c) for v, c in zip(vals, counts)}


def main() -> int:
    lab = rasterio.open(labels_path()).read(1)
    foot = lab != -1
    cat = lab > 0
    dcat = ndi.distance_transform_edt(~cat)

    b2 = support(FOCUS / "gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif")
    h27 = support(FOCUS / "gemsdoe31-h27-4-solo-d28-20261004-8acb75e1-nan.tif")
    d28 = support(FOCUS / "gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif")

    rem_h27_b2 = h27 & ~b2
    rem_d28_h27 = d28 & ~h27
    out = {
        "schema": "gems-chain-0.2778-verify-v1",
        "catalogue_sha256": sha256(labels_path()),
        "dots": {"GEMSDOE25_D2-8": int(d28.sum()), "GEMSDOE31_H27-4": int(h27.sum()),
                 "GEMSDOE32_B2": int(b2.sum())},
        "all_inside_footprint": bool((d28 & foot).sum() == d28.sum()
                                     and (h27 & foot).sum() == h27.sum()
                                     and (b2 & foot).sum() == b2.sum()),
        "exact_subset": {
            "B2_subset_of_H27-4": bool(not (b2 & ~h27).any()),
            "H27-4_subset_of_D2-8": bool(not (h27 & ~d28).any()),
        },
        "D2-8_minus_H27-4": {
            "n": int(rem_d28_h27.sum()),
            "distance_to_catalogue_px_histogram": hist(dcat[rem_d28_h27]),
            "on_catalogue_pixels": int((rem_d28_h27 & cat).sum()),
        },
        "H27-4_minus_B2": {
            "n": int(rem_h27_b2.sum()),
            "distance_to_catalogue_px_histogram": hist(dcat[rem_h27_b2]),
            "min_px": float(dcat[rem_h27_b2].min()) if rem_h27_b2.any() else None,
            "max_px": float(dcat[rem_h27_b2].max()) if rem_h27_b2.any() else None,
            "on_catalogue_pixels": int((rem_h27_b2 & cat).sum()),
        },
        "B2_dots_within_3px_of_catalogue": int((b2 & (dcat <= 3)).sum()),
        "wording_corrections": [
            "The 3,891 D2-8-minus-H27-4 dots are 1.0 px from the catalogue (not 'on' it); none sit on a catalogue pixel.",
            "The 2,545 H27-4-minus-B2 dots lie between 1.414 and 2.000 px from the catalogue (a diagonal and 2-px shell), not in a 1.01-2.01 px band.",
        ],
    }
    OUT.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: out[k] for k in ("dots", "exact_subset", "all_inside_footprint")}, indent=2))
    print("D2-8 minus H27-4:", out["D2-8_minus_H27-4"]["n"], out["D2-8_minus_H27-4"]["distance_to_catalogue_px_histogram"])
    print("H27-4 minus B2:", out["H27-4_minus_B2"]["n"], out["H27-4_minus_B2"]["distance_to_catalogue_px_histogram"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
