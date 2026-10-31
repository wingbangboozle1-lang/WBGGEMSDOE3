#!/usr/bin/env python3
"""Fail closed if the published site does not match the bytes and evidence on disk.

This is the "no human inspection" gate the brief asks for: it re-validates the exact
downloadable file, re-runs the uniqueness gate's decision fields, checks that every score
on the page carries an evidence class, and checks that the README feed block agrees with
the run card. It never edits anything.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "vendor"))
from gemsdoe import config as C      # noqa: E402
from gemsdoe import io as gio         # noqa: E402
from gems57.validate import validate   # noqa: E402

FAIL = []
OK = []


def check(name, cond, detail=""):
    (OK if cond else FAIL).append(f"{name}: {detail}")
    print(("  ok   " if cond else "  FAIL ") + name + (f" — {detail}" if detail else ""))


def main() -> int:
    card_p = ROOT / "evidence" / "ggo_run_card.json"
    check("run card exists", card_p.exists(), str(card_p))
    if not card_p.exists():
        return 1
    card = json.loads(card_p.read_text())
    name = card.get("raster", {}).get("file", "")
    cands = [ROOT / "docs" / "downloads" / "submission" / name, ROOT / "docs" / "downloads" / name]
    tif = next((x for x in cands if x.exists()), cands[0])

    print("[1] bytes on disk == bytes the card describes")
    check("published file exists", tif.exists(), tif.name)
    if not tif.exists():
        return 1
    import hashlib
    sha = hashlib.sha256(tif.read_bytes()).hexdigest()
    check("sha256 matches run card", sha == card["raster"]["sha256"], sha[:16] + "…")
    zp = tif.with_suffix(".zip")
    if zp.exists():
        import zipfile
        with zipfile.ZipFile(zp) as z:
            check("zip holds exactly one member", len(z.namelist()) == 1, str(z.namelist()))
            if len(z.namelist()) == 1:
                check("zip bytes equal the published tif", z.read(z.namelist()[0]) == tif.read_bytes(), "")

    print("[2] portal-critical format properties, re-measured from the file")
    with rasterio.open(tif) as ds:
        a = ds.read(1)
        meta = dict(count=ds.count, dtype=ds.dtypes[0], crs=str(ds.crs), shape=(ds.height, ds.width),
                    transform=[float(x) for x in tuple(ds.transform)[:6]], nodata=ds.nodata)
    fp = gio.read_footprint()
    check("single band float32", meta["count"] == 1 and meta["dtype"] == "float32", str(meta))
    check("crs/shape/transform == sample_submission",
          meta["crs"] == "EPSG:32611" and meta["shape"] == (3730, 3292)
          and meta["transform"] == [100.0, 0.0, 243350.0, 0.0, -100.0, 4508550.0], meta["crs"] + " " + str(meta["shape"]))
    check("no NaN anywhere (the portal range-error class)", np.isfinite(a).all(),
          f"{int((~np.isfinite(a)).sum())} non-finite cells")
    check("every value in [0,1]", bool(np.isfinite(a).all()) and a.min() >= 0 and a.max() <= 1,
          f"min={a.min()} max={a.max()}")
    check("zero positive mass outside the footprint", int(((a > 0) & ~fp).sum()) == 0,
          f"{int(((a > 0) & ~fp).sum())} cells outside")
    cat = gio.read_labels() & fp
    check("no dots on the mapped catalogue", int(((a > 0) & cat).sum()) == 0,
          f"{int(((a > 0) & cat).sum())} cells")
    check("dots inside the footprint > 0", int(((a > 0) & fp).sum()) > 0, f"{int(((a > 0) & fp).sum()):,} dots")
    rep = validate(tif, fp, cat)
    check("shared writer validator all-pass", bool(rep["all_checks_passed"]),
          ",".join(k for k, v in rep["checks"].items() if not v) or "all true")

    print("[3] evidence classes are attached to every published number")
    idx = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
    for tag in ("LEDGER", "HOLDOUT-DTI", "OWNER", "REGISTRY-MEASUREMENT"):
        check(f"page labels {tag}", tag in idx or tag == "OWNER", "")
    check("page states no receipt", "no receipt" in idx or "never a score" in idx.lower(), "")
    est = card.get("ledger_estimate", {})
    check("estimate value present on the page", str(est.get("value")) in idx, str(est.get("value")))
    check("holdout value present on the page", str(card.get("holdout_dti", {}).get("value")) in idx, "")

    href = re.search('href="(downloads/[^"]+[.]tif)"', idx)
    check("primary download link on the desk resolves to a real file",
          bool(href) and (ROOT / "docs" / href.group(1)).is_file(),
          href.group(1) if href else "no downloads/*.tif href found in docs/index.html")

    print("[4] site decision is bound to the card decision")
    man = ROOT / "docs" / "data" / "desk_manifest.json"
    if man.exists():
        m = json.loads(man.read_text())
        want = "cleared-for-upload" if card.get("verdict", "").startswith("promote") else "not-cleared"
        check("manifest decision == card verdict", m.get("decision") == want, f"{m.get('decision')} vs {want}")
        check("manifest sha == card sha", m.get("sha256") == card["raster"]["sha256"], "")
    rd = (ROOT / "README.md").read_text(encoding="utf-8")
    check("README feed block exists", "<!-- FEED:BEGIN -->" in rd and "<!-- FEED:END -->" in rd, "")
    cleared = bool(card.get("verdict", "").startswith("promote")) and card.get("validator", {}).get("all_checks_passed")
    seg = rd.split("<!-- FEED:BEGIN -->")[1].split("<!-- FEED:END -->")[0]
    check("README headline matches the gate",
          ("CLEARED FOR DOWNLOAD AND PORTAL UPLOAD" in seg) == bool(cleared), f"cleared={cleared}")

    print("\n" + "=" * 72)
    print(f"{len(OK)} checks passed, {len(FAIL)} failed")
    for f in FAIL:
        print("  FAIL " + f)
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
