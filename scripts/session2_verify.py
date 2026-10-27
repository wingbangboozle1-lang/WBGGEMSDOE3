#!/usr/bin/env python3
"""PASS-2 INDEPENDENT verifier for the released SGCE TIFF.

Deliberately shares NO code with src/gemsw/{writer,uniq2,sgce}.py: rasterio + numpy + scipy only,
Euclidean distance-transform overlap (radius 3) instead of binary dilation, and a fresh read of
every hash-verified ledger raster.  Fails closed.  Writes evidence/session2_verify_independent.json.
"""
from __future__ import annotations
import hashlib, json, sys, zipfile
from pathlib import Path
import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "evidence" / "session2_verify_independent.json"


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def main() -> int:
    card = json.loads((ROOT / "evidence/session2_run_card.json").read_text())
    build = json.loads((ROOT / "evidence/session2_build.json").read_text())
    name = card["submission_name"]
    with rasterio.open(ROOT / "data/raw/sample_submission.tif") as t:
        tshape, ttr, tcrs = t.shape, t.transform, t.crs
        foot = np.isfinite(t.read(1))
    with rasterio.open(ROOT / "data/raw/labels.tif") as t:
        lab = (t.read(1) > 0) & foot
    res = dict(evidence_class="INDEPENDENT-FILE-MEASUREMENT; not a competition score",
               submission_name=name, checks={}, errors=[])
    rows = {}
    for kind in ("zeros.tif", "nan.tif", "zeros.zip"):
        p = ROOT / "docs" / "downloads" / f"{name}-{kind}"
        raw = p.read_bytes()
        h = sha(raw)
        rows[kind] = dict(sha256=h, bytes=len(raw),
                          matches_build=h == build["files"][p.name]["sha256"])
        if not rows[kind]["matches_build"]:
            res["errors"].append(f"{p.name}: hash mismatch")
        if kind.endswith(".zip"):
            with zipfile.ZipFile(p) as z:
                names = z.namelist()
                rows[kind]["single_tiff"] = len(names) == 1 and names[0].endswith(".tif")
                inner = z.read(names[0])
                rows[kind]["inner_equals_primary_tif"] = (
                    sha(inner) == rows["zeros.tif"]["sha256"])
            if not (rows[kind]["single_tiff"] and rows[kind]["inner_equals_primary_tif"]):
                res["errors"].append("zip content mismatch")
            continue
        with rasterio.open(p) as ds:
            a = ds.read(1)
            c = dict(bands=ds.count, dtype=ds.dtypes[0], crs=str(ds.crs),
                     shape_ok=ds.shape == tshape, transform_ok=ds.transform == ttr,
                     crs_ok=ds.crs == tcrs)
        ins = a[foot]
        c.update(footprint_px=int(foot.sum()), nan_in_footprint=int(np.isnan(ins).sum()),
                 inf_in_footprint=int(np.isinf(ins).sum()),
                 min=float(np.nanmin(ins)), max=float(np.nanmax(ins)),
                 in_range=bool(((ins >= 0) & (ins <= 1)).all()),
                 dots=int((ins > 0).sum()), on_catalogue=int((a[lab] > 0).sum()),
                 outside_ok=bool(np.isnan(a[~foot]).all()) if kind.startswith("nan")
                 else bool((a[~foot] == 0).all()))
        rows[kind]["checks"] = c
        ok = (c["bands"] == 1 and c["dtype"] == "float32" and c["crs_ok"] and c["shape_ok"]
              and c["transform_ok"] and c["nan_in_footprint"] == 0 and c["inf_in_footprint"] == 0
              and c["in_range"] and c["on_catalogue"] == 0 and c["outside_ok"] and c["dots"] > 0)
        if not ok:
            res["errors"].append(f"{p.name}: format check failed")
        if kind == "zeros.tif":
            dots = a > 0
            if sha(np.packbits(dots.ravel()).tobytes()) != build["dots_sha256"]:
                res["errors"].append("primary TIFF dot mask != audited dot mask")
    res["delivered_files"] = rows

    # Independent overlap vs every hash-verified ledger raster (Euclidean DT, radius 3).
    led = json.loads((ROOT / "data/ledger/index.json").read_text())
    overlaps = []
    for e in led:
        if e.get("status") != "verified":
            continue
        p = ROOT / e["local"]
        if not p.is_file():
            continue
        with rasterio.open(p) as ds:
            r = ds.read(1)
        rd = np.isfinite(r) & (r > 0) & foot
        if rd.sum() == 0:
            continue
        near = ndi.distance_transform_edt(~rd) <= 3.0
        ov = float((dots & near).sum() / dots.sum())
        null = float((near & foot).sum() / foot.sum())
        overlaps.append(dict(ref=e["submission"], overlap=round(ov, 5), null=round(null, 5),
                             lattice_like=bool(null >= 0.70), n_ref=int(rd.sum()),
                             exact_same=bool(np.array_equal(rd, dots))))
    overlaps.sort(key=lambda x: -x["overlap"])
    res["ledger_overlap_top8"] = overlaps[:8]
    res["exact_duplicate_of_any_ledger_raster"] = any(x["exact_same"] for x in overlaps)
    res["max_overlap_non_lattice"] = max((x["overlap"] for x in overlaps if not x["lattice_like"]), default=0.0)
    res["max_lattice_excess"] = max((x["overlap"] - x["null"] for x in overlaps if x["lattice_like"]), default=0.0)
    if res["exact_duplicate_of_any_ledger_raster"]:
        res["errors"].append("exact duplicate of a ledger raster")
    if res["max_overlap_non_lattice"] > 0.70:
        res["errors"].append("independent overlap > 0.70")
    if res["max_lattice_excess"] > 0.05:
        res["errors"].append("independent lattice excess > 0.05")
    res["passed"] = not res["errors"]
    json.dump(res, open(OUT, "w"), indent=1, default=float)
    print(json.dumps({k: res[k] for k in ("passed", "errors", "max_overlap_non_lattice",
                                          "max_lattice_excess", "exact_duplicate_of_any_ledger_raster")}, indent=1))
    return 0 if res["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
