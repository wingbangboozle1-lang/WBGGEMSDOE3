#!/usr/bin/env python3
"""PASS 2 — independent re-verification of the delivered bytes. Deliberately shares NO code with src/gemsw/{writer,uniq}.py:
rasterio+numpy+scipy only, distance-transform overlap instead of binary dilation, checks against every verified ledger raster."""
import hashlib, json, sys, zipfile, io
from pathlib import Path
import numpy as np, rasterio
from scipy import ndimage as ndi
ROOT = Path(__file__).resolve().parents[1]
card = json.load(open(ROOT / "evidence/lst1_run_card.json"))
name = card["submission_name"]
out = {"checks": {}}
def sha(b): return hashlib.sha256(b).hexdigest()
with rasterio.open(ROOT / "data/raw/sample_submission.tif") as t:
    tshape, ttr = t.shape, t.transform; foot = np.isfinite(t.read(1))
with rasterio.open(ROOT / "data/raw/labels.tif") as t:
    lab = (t.read(1) > 0) & foot
rows = {}
for kind in ("zeros.tif", "nan.tif", "zeros.zip"):
    p = ROOT / "docs/lst1/downloads" / f"{name}-{kind}"
    raw = p.read_bytes()
    rows[kind] = dict(sha256=sha(raw), matches_run_card=sha(raw) == card["raster_sha256"][p.name], bytes=len(raw))
    if kind.endswith("zip"):
        z = zipfile.ZipFile(p); assert len(z.namelist()) == 1 and z.namelist()[0].endswith(".tif"), z.namelist()
        inner = z.read(z.namelist()[0]); rows[kind]["zip_inner_equals_zeros_tif"] = inner == (ROOT / "docs/lst1/downloads" / f"{name}-zeros.tif").read_bytes()
        continue
    with rasterio.open(p) as ds:
        a = ds.read(1)
        c = dict(bands=ds.count, dtype=ds.dtypes[0], crs=str(ds.crs), shape_ok=ds.shape == tshape, transform_ok=ds.transform == ttr)
    ins = a[foot]
    c.update(footprint_px=int(foot.sum()), nan_in_footprint=int(np.isnan(ins).sum()), inf_in_footprint=int(np.isinf(ins).sum()),
             min=float(np.nanmin(a)), max=float(np.nanmax(a)), in_range=bool(((ins >= 0) & (ins <= 1)).all()),
             dots=int((ins > 0).sum()), on_catalogue=int((a[lab] > 0).sum()),
             outside_ok=bool(np.isnan(a[~foot]).all()) if kind.startswith("nan") else bool((a[~foot] == 0).all()))
    rows[kind]["checks"] = c
    if kind == "zeros.tif":
        dots = a > 0
ok = all(r["matches_run_card"] for r in rows.values()) and rows["zeros.zip"]["zip_inner_equals_zeros_tif"]
for k in ("zeros.tif", "nan.tif"):
    c = rows[k]["checks"]
    ok &= (c["bands"] == 1 and c["dtype"] == "float32" and c["crs"] == "EPSG:32611" and c["shape_ok"] and c["transform_ok"]
           and c["nan_in_footprint"] == 0 and c["inf_in_footprint"] == 0 and c["in_range"] and c["on_catalogue"] == 0 and c["outside_ok"] and c["dots"] > 0)
out["delivered_files"] = rows
# independent duplicate / overlap check vs every verified ledger raster (Euclidean distance transform, radius 3)
led = json.load(open(ROOT / "data/ledger/index.json"))
res = []
for e in led:
    if e["status"] != "verified": continue
    with rasterio.open(ROOT / e["local"]) as ds: r = ds.read(1)
    rd = np.isfinite(r) & (r > 0) & foot
    if rd.sum() == 0: continue
    near = ndi.distance_transform_edt(~rd) <= 3.0
    ov = float((dots & near).sum() / dots.sum())
    null = float((near & foot).sum() / foot.sum())          # analytic random-placement overlap (no sampling)
    lattice = null >= 0.70
    passed = (ov <= 0.70) if not lattice else (ov <= null + 0.05)
    res.append(dict(ref=e["submission"][:60], n_ref=int(rd.sum()), overlap=ov, null=null, lattice_like=lattice,
                    exact_same=bool(np.array_equal(rd, dots)), passes_rule=bool(passed)))
res.sort(key=lambda x: -x["overlap"])
out["ledger_overlap_top8"] = res[:8]
out["exact_duplicate_of_any_ledger_raster"] = any(x["exact_same"] for x in res)
out["max_overlap_non_lattice_ledger"] = max(x["overlap"] for x in res if not x["lattice_like"])
out["n_refs_failing_rule"] = [x["ref"] for x in res if not x["passes_rule"]]
ok &= (not out["exact_duplicate_of_any_ledger_raster"]) and not out["n_refs_failing_rule"]
out["independent_pass"] = bool(ok)
json.dump(out, open(ROOT / "evidence/verify_independent.json", "w"), indent=1)
print("independent pass:", ok, "max non-lattice ledger overlap:", round(out["max_overlap_non_lattice_ledger"], 3), "failing refs:", out["n_refs_failing_rule"])
for x in res[:6]: print(x)
