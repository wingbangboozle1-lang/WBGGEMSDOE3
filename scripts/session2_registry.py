#!/usr/bin/env python3
"""Rebuild the local comparator registry from hash-verified local TIFFs (session 2026-10-27).

This does NOT modify the committed registry/registry_index.json. It writes
registry/registry_session2.json plus packed dot masks in the ignored .cache/registry2/.
Every file is re-read from disk; nothing is copied into a submission.
"""
from __future__ import annotations
import hashlib, json, sys
from pathlib import Path
import numpy as np, rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gemsw.grid import load_grid, EXPECTED_SHAPE  # noqa: E402

CACHE = ROOT / ".cache" / "registry2"
CACHE.mkdir(parents=True, exist_ok=True)


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def sources():
    for p in sorted((ROOT / ".cache" / "sites").rglob("*.tif")):
        yield "focus-site", p
    for p in sorted((ROOT / "data" / "ledger").glob("*.tif")):
        yield "ledger", p
    for p in sorted((ROOT / "data" / "raw" / "scored").glob("*.tif")):
        yield "scored-mirror", p
    for p in sorted((ROOT / "submission").glob("*.tif")):
        yield "this-repo-research", p
    for p in sorted((ROOT / "site").rglob("*.tif")):
        yield "this-repo-standin", p
    w = ROOT / ".cache" / "witness" / "17GEMSDOE_E-proba-multiscale.tif"
    if w.exists():
        yield "registered-continuous-witness", w
    for p in sorted((ROOT / "data" / "raw" / "external").glob("*.tif")):
        yield "feature-layer", p
    for name in ("labels.tif", "existing_faults.tif", "sample_submission.tif"):
        yield "template", ROOT / "data" / "raw" / name


def main() -> None:
    g = load_grid()
    out, seen = [], {}
    for origin, p in sources():
        rel = str(p.relative_to(ROOT))
        e = dict(origin=origin, path=rel, bytes=p.stat().st_size, sha256=sha256_file(p))
        try:
            with rasterio.open(p) as ds:
                e.update(shape=list(ds.shape), count=ds.count, dtype=ds.dtypes[0], crs=str(ds.crs))
                if ds.shape != EXPECTED_SHAPE or ds.count != 1:
                    e["status"] = "grid_mismatch"
                    out.append(e)
                    continue
                a = ds.read(1)
        except Exception as ex:  # noqa: BLE001
            e.update(status=f"unreadable:{type(ex).__name__}")
            out.append(e)
            continue
        fin = np.isfinite(a)
        inside = a[g.foot]
        dots = fin & (a > 0) & g.foot
        vals = np.unique(inside[np.isfinite(inside)])
        e.update(
            nan_in_footprint=int((~np.isfinite(inside)).sum()),
            out_of_range_in_footprint=int(((inside < 0) | (inside > 1)).sum()),
            n_dots=int(dots.sum()),
            positive_fraction_of_footprint=round(float(dots.sum() / g.foot.sum()), 6),
            binary=bool(len(vals) <= 2 and set(vals.tolist()) <= {0.0, 1.0}),
            status="ok",
        )
        if origin in ("feature-layer", "template"):
            e["comparator_class"] = "feature"
        elif e["positive_fraction_of_footprint"] > 0.15:
            # Space-filling continuous fields (e.g. the 17GEMSDOE witness) are not "dots".
            e["comparator_class"] = "dense"
        elif not e["binary"]:
            # Soft-probability submissions with SPARSE support are still discrete emission masks:
            # they are judged by the literal 3-px overlap rule, not the lattice excess exemption.
            e["comparator_class"] = "soft-sparse"
        else:
            e["comparator_class"] = "sparse"
        pk = np.packbits(dots.ravel())
        dsha = hashlib.sha256(pk.tobytes()).hexdigest()
        e["dots_sha256"] = dsha
        if dsha not in seen:
            seen[dsha] = rel
            np.save(CACHE / f"{dsha}.npy", pk)
        e["dots_first_seen_in"] = seen[dsha]
        out.append(e)
    report = dict(
        built_utc="2026-10-27",
        source="hash-verified local TIFFs restored from pinned public GitHub mirrors; NOT organizer-authenticated",
        n_files=len(out),
        n_ok=sum(1 for e in out if e["status"] == "ok"),
        n_unique_dot_masks=len(seen),
        classes={c: sum(1 for e in out if e.get("comparator_class") == c)
                 for c in ("sparse", "dense", "continuous", "feature")},
        files=out,
    )
    (ROOT / "registry" / "registry_session2.json").write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps({k: report[k] for k in ("n_files", "n_ok", "n_unique_dot_masks", "classes")}, indent=1))


if __name__ == "__main__":
    main()
