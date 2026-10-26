#!/usr/bin/env python3
"""Index every GeoTIFF in the nine focus sites + the verified ledger/scored rasters.

For each file: sha256, grid check, dot mask (finite & >0 & in-footprint), dot-mask sha256, format flags
(NaN inside footprint, values outside [0,1], sentinel), and whether it is a binary or soft raster.
Dot masks are de-duplicated and stored packed in .cache/registry/<dotsha>.npy (git-ignored);
the committed output is registry/registry_index.json.
"""
from __future__ import annotations
import hashlib, json, sys
from pathlib import Path
import numpy as np, rasterio
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gemsw.grid import load_grid, EXPECTED_SHAPE

SITES = ["GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE30", "GEMSDOE31", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36"]


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def main() -> None:
    g = load_grid()
    cache = ROOT / ".cache" / "registry"
    cache.mkdir(parents=True, exist_ok=True)
    files: list[tuple[str, Path]] = []
    for s in SITES:
        base = ROOT / ".cache" / "sites" / s
        files += [(s, p) for p in sorted(base.rglob("*.tif")) if ".git" not in p.parts]
    files += [("ledger", p) for p in sorted((ROOT / "data" / "ledger").glob("*.tif"))]
    files += [("scored-mirror", p) for p in sorted((ROOT / "data" / "raw" / "scored").glob("*.tif"))]
    out, seen = [], {}
    for site, p in files:
        rel = str(p.relative_to(ROOT))
        e = dict(site=site, path=rel, bytes=p.stat().st_size, sha256=sha256_file(p))
        try:
            with rasterio.open(p) as ds:
                e.update(shape=list(ds.shape), count=ds.count, dtype=ds.dtypes[0], crs=str(ds.crs))
                if ds.shape != EXPECTED_SHAPE or ds.count != 1:
                    e["status"] = "grid_mismatch"; out.append(e); continue
                a = ds.read(1)
        except Exception as ex:  # noqa
            e.update(status=f"unreadable:{type(ex).__name__}"); out.append(e); continue
        fin = np.isfinite(a)
        inf = a[g.foot]
        e["nan_in_footprint"] = int((~np.isfinite(inf)).sum())
        e["out_of_range_in_footprint"] = int(((inf < 0) | (inf > 1)).sum())
        e["finite_outside_footprint"] = int(fin[~g.foot].sum())
        e["on_catalogue_positive"] = int(((a > 0) & g.labels).sum())
        dots = fin & (a > 0) & g.foot
        e["n_dots"] = int(dots.sum())
        vals = np.unique(inf[np.isfinite(inf)])
        e["binary"] = bool(len(vals) <= 2 and set(vals.tolist()) <= {0.0, 1.0})
        pk = np.packbits(dots.ravel())
        ds_ = hashlib.sha256(pk.tobytes()).hexdigest()
        e["dots_sha256"] = ds_
        e["status"] = "ok"
        if ds_ not in seen:
            seen[ds_] = rel
            np.save(cache / f"{ds_}.npy", pk)
        e["dots_first_seen_in"] = seen[ds_]
        out.append(e)
    uniq = len(seen)
    (ROOT / "registry" / "registry_index.json").write_text(json.dumps(
        dict(n_files=len(out), n_unique_dot_masks=uniq, files=out), indent=1))
    print(f"files={len(out)} ok={sum(1 for e in out if e['status']=='ok')} unique_dot_masks={uniq} "
          f"grid_mismatch={[e['path'] for e in out if e['status']!='ok']}")


if __name__ == "__main__":
    main()
