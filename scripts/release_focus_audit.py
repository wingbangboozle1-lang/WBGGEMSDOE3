#!/usr/bin/env python3
"""Measure the nine focus-site submissions from their bytes.

For each owner-reported "best" file this records: whether the bytes match the
pinned commit used by the previous review, the dot count, how much of the dot
set sits on / near / far from the competition catalogue mask, and the pairwise
3-px overlap with every other focus file. These are measurements, not scores.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
import itertools

import numpy as np
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems_release import shared  # noqa: E402

CACHE = ROOT / ".cache" / "comparators" / "focus9"
EVID = ROOT / "evidence" / "release"

# (site, owner-reported score at that pinned commit, commit, filename)
FILES = [
    ("GEMSDOE24", 0.2477, "5cfab74597cd1d0a271e4640b4cc34511e56ca59",
     "gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif"),
    ("GEMSDOE25", 0.2600, "bfb2dfdbdf1b87d67afc6facd422180f56ebc455",
     "gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif"),
    ("GEMSDOE27", 0.2449, "f1e32af867d9cf0081af20866c8241ec8678a432",
     "gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan.tif"),
    ("GEMSDOE28", 0.2710, "9c1be21e8f1be707347f737e42abf62ea669c819",
     "gems28-h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan.tif"),
    ("GEMSDOE30", 0.2600, "35ce8911e2c3287eed973eacd12c252e8cb3f34c",
     "gemsdoe30-d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca.tif"),
    ("GEMSDOE31", 0.2708, "78f9bf3ae82e5c78ca348aa37c0660c339e72f0e",
     "gemsdoe31-h27-4-solo-d28-20261004-8acb75e1-nan.tif"),
    ("GEMSDOE32", 0.2778, "8953b986b2ce6eb5ee8b7eda23fe3ad529720986",
     "gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif"),
    ("GEMSDOE33", 0.2632, "a24fb7c5031ee08b12440af4593057858fecef8e",
     "GEMSDOE33-h33d-analog-tip-stepover-r30-20261004-cb490425926e.tif"),
    ("GEMSDOE36", 0.2750, "b90418f852615aa0974cf9a53b92fa569ed133fc",
     "gemsdoe36-anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros.tif"),
]


def main() -> int:
    import rasterio

    EVID.mkdir(parents=True, exist_ok=True)
    footprint, catalogue = shared.load_masks()
    d_cat = distance_transform_edt(~catalogue)
    rows, dot_masks = [], {}
    for site, score, commit, name in FILES:
        path = CACHE / f"{site}__{name}"
        rec = {"site": site, "file": name, "pinned_commit": commit,
               "owner_reported_score": score, "owner_report_is_not_a_receipt": True}
        if not path.is_file():
            rec["status"] = "missing_bytes"
            rows.append(rec)
            continue
        with rasterio.open(path) as src:
            arr = src.read(1)
            rec.update(grid=[src.height, src.width], crs=str(src.crs),
                       transform=[float(v) for v in tuple(src.transform)[:6]],
                       dtype=str(arr.dtype), nodata=str(src.nodata))
        fin = np.isfinite(arr)
        dots = fin & (arr > 0) & footprint
        dot_masks[site] = dots
        vals = arr[fin]
        rec.update(
            sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            bytes=path.stat().st_size,
            dots=int(dots.sum()),
            value_min=float(vals.min()), value_max=float(vals.max()),
            value_unique=int(np.unique(vals).size),
            binary=bool(np.isin(np.unique(vals), [0.0, 1.0]).all()),
            finite_cells=int(fin.sum()),
            outside_footprint_nan=bool((~fin[~footprint]).all()),
        )
        d = d_cat[dots]
        rec.update(
            on_catalogue=int((dots & catalogue).sum()),
            frac_on_catalogue=float((dots & catalogue).sum() / max(1, dots.sum())),
            frac_within_1px=float((d <= 1.0).mean()), frac_within_2px=float((d <= 2.0).mean()),
            frac_within_3px=float((d <= 3.0).mean()), frac_within_4px=float((d <= 4.0).mean()),
            frac_beyond_3px=float((d > 3.0).mean()),
            median_distance_px=float(np.median(d)),
        )
        rows.append(rec)

    pairwise = {}
    for a, b in itertools.permutations([r["site"] for r in rows if r["site"] in dot_masks], 2):
        db = distance_transform_edt(~dot_masks[b])
        pairwise[f"{a}->{b}"] = float((db[dot_masks[a]] <= 3.0).mean())

    for rec in rows:
        if rec["site"] not in dot_masks:
            continue
        others = {k: v for k, v in pairwise.items() if k.startswith(rec["site"] + "->")}
        best = max(others, key=others.get)
        rec["max_overlap_within_3px"] = others[best]
        rec["max_overlap_with"] = best.split("->")[1]
        rec["unique_vs_focus_set"] = bool(others[best] < 0.70)

    out = {
        "generated_by": "scripts/release_focus_audit.py",
        "note": "owner_reported_score is the number the owner published on that site; "
                "it is not an organizer receipt, and these rows are measurements of bytes.",
        "dot_definition": "finite, within footprint, value > 0, not catalogue-masked",
        "sites": rows,
        "pairwise_overlap_within_3px": pairwise,
    }
    (EVID / "focus_sites.json").write_text(json.dumps(out, indent=2) + "\n")
    for rec in rows:
        print(f"{rec['site']} dots={rec.get('dots')} on_mask={rec.get('frac_on_catalogue', 0):.4f} "
              f"<=3px={rec.get('frac_within_3px', 0):.4f} median_d={rec.get('median_distance_px', 0):.1f} "
              f"max_ovl={rec.get('max_overlap_within_3px', 0):.3f}({rec.get('max_overlap_with', '-')}) "
              f"unique={rec.get('unique_vs_focus_set')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
