#!/usr/bin/env python3
"""Independent, re-runnable verifier for the nine focus-site TIFFs and the release candidate.

Why this exists: the README and the release gate quote overlap and format numbers that were
produced in earlier sessions.  This script re-derives them from the bytes on disk, so any
reviewer can re-run it without trusting a prior run card.  It does NOT fetch anything and
does NOT contact any portal.  Inputs:

* ``.cache/focus/<file>`` - the nine owner-published focus TIFFs.  They are populated by
  ``scripts/fetch_focus_tifs.py`` (GitHub API, pinned commit SHA + sha256 from
  ``registry/focus_sites.json``).
* ``docs/downloads/wbggems3-invdesign-anchor-20k-zeros.tif`` - the release candidate.
* ``data/template_grid.tif`` - the grid the portal requires (CRS / shape / transform).

Outputs ``evidence/focus_candidate_verify_2026-10-28.json`` with:

* per-file sha256 check against the registry pin,
* per-file format gate (finite inside footprint, values in [0, 1], CRS/shape/transform),
* the directed 3-px overlap matrix (fraction of row-file dots within 3 px of column-file dots),
* the Spearman rank correlation matrix on a 6x-subsampled grid (same as check_uniqueness.py).

Shared definitions: ``gemsw.exact.kernel_credit_field`` and ``gemsw.exact.RADIUS_PX`` (3.0).
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gemsw import exact as EX  # noqa: E402  (shared kernel, not a fork)

CANDIDATE = ROOT / "docs" / "downloads" / "wbggems3-invdesign-anchor-20k-zeros.tif"
TEMPLATE = ROOT / "data" / "template_grid.tif"
FOCUS_JSON = ROOT / "registry" / "focus_sites.json"
CACHE = ROOT / ".cache" / "focus"
OUT = ROOT / "evidence" / "focus_candidate_verify_2026-10-28.json"
OVERLAP_LIMIT = 0.70
SPEARMAN_LIMIT = 0.90


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_support(path: Path, grid_ref: dict) -> dict:
    """Return the format gate and the boolean dot support of one TIFF.

    NaN cells are treated as outside (0) for the support, but are counted and reported so a
    NaN-outside file is never silently repaired.
    """
    with rasterio.open(path) as ds:
        raw = ds.read(1).astype(np.float64)
        nodata = ds.nodata
        crs = ds.crs.to_string() if ds.crs else None
        transform = [float(v) for v in ds.transform][:6]
        shape = [ds.height, ds.width]
        count = ds.count
    finite = np.isfinite(raw)
    clean = np.where(finite, raw, 0.0)
    support = clean > 0
    gate = {
        "count": count,
        "shape": shape,
        "crs": crs,
        "transform": transform,
        "shape_match": shape == grid_ref["shape"],
        "crs_match": crs == grid_ref["crs"],
        "transform_match": np.allclose(transform, grid_ref["transform"], atol=1e-6),
        "n_nonfinite": int((~finite).sum()),
        "n_nan": int(np.isnan(raw).sum()),
        "min_finite": float(clean.min()),
        "max_finite": float(clean.max()),
        "range_01_ok": bool(clean.min() >= 0.0 and clean.max() <= 1.0),
        "n_positive_dots": int(support.sum()),
        "nodata": nodata,
    }
    gate["format_pass"] = bool(
        gate["count"] == 1 and gate["shape_match"] and gate["crs_match"]
        and gate["transform_match"] and gate["range_01_ok"]
    )
    return {"gate": gate, "support": support, "values": clean}


def directed_overlap(a: np.ndarray, b: np.ndarray) -> float:
    """Fraction of a's dots lying within RADIUS_PX (3 px) of at least one b dot."""
    if a.sum() == 0 or b.sum() == 0:
        return 0.0
    kb = EX.kernel_credit_field(b)
    return float((kb[a] > 0).mean())


def main() -> int:
    spec = json.loads(FOCUS_JSON.read_text())
    with rasterio.open(TEMPLATE) as ds:
        grid_ref = {
            "shape": [ds.height, ds.width],
            "crs": ds.crs.to_string(),
            "transform": [float(v) for v in ds.transform][:6],
        }

    items: dict[str, dict] = {}
    pins: list[dict] = []
    for f in spec["sites"]:
        name = Path(f["path"]).name
        local = CACHE / name
        if not local.exists():
            pins.append({"site": f["site"], "file": name, "present": False})
            continue
        digest = sha256(local)
        pins.append({
            "site": f["site"], "file": name, "present": True,
            "sha256_local": digest, "sha256_pin": f["sha256"],
            "sha256_match": digest == f["sha256"],
            "owner_reported": f["owner_reported"],
        })
        items[f["site"]] = read_support(local, grid_ref)

    cand = read_support(CANDIDATE, grid_ref)
    cand_sha = sha256(CANDIDATE)
    items["CANDIDATE"] = cand

    names = list(items)
    overlap = {a: {b: (None if a == b else round(directed_overlap(items[a]["support"], items[b]["support"]), 4))
                   for b in names} for a in names}
    rho = {}
    for a in names:
        rho[a] = {}
        for b in names:
            if a == b:
                rho[a][b] = 1.0
                continue
            r = spearmanr(items[a]["values"][::6, ::6].ravel(),
                          items[b]["values"][::6, ::6].ravel()).statistic
            rho[a][b] = round(float(r), 4)

    cand_vs = {b: overlap["CANDIDATE"][b] for b in names if b != "CANDIDATE"}
    cand_rev = {b: round(directed_overlap(items[b]["support"], cand["support"]), 4)
                for b in names if b != "CANDIDATE"}
    max_dir = max(cand_vs.values())
    max_rev = max(cand_rev.values())
    max_abs_rho = max(abs(rho["CANDIDATE"][b]) for b in names if b != "CANDIDATE")

    summary = {
        "schema": "gems-focus-candidate-verify-v1",
        "candidate": {
            "path": str(CANDIDATE.relative_to(ROOT)),
            "sha256": cand_sha,
            "gate": {k: v for k, v in cand["gate"].items()},
        },
        "pins": pins,
        "focus_gate": {s: items[s]["gate"] for s in items if s != "CANDIDATE"},
        "dots_per_file": {s: items[s]["gate"]["n_positive_dots"] for s in items},
        "directed_3px_overlap_row_to_col": overlap,
        "spearman_subsampled": rho,
        "candidate_directed_overlap_candidate_to_focus": cand_vs,
        "candidate_directed_overlap_focus_to_candidate": cand_rev,
        "limits": {"overlap": OVERLAP_LIMIT, "abs_spearman": SPEARMAN_LIMIT},
        "max_candidate_to_focus_overlap": max_dir,
        "max_focus_to_candidate_overlap": max_rev,
        "max_abs_spearman_candidate_to_focus": max_abs_rho,
        "focus_pair_max_overlap_excluding_self": max(
            overlap[a][b] for a in names for b in names if a != b and "CANDIDATE" not in (a, b)),
        "candidate_unique_on_focus_set": bool(
            max_dir <= OVERLAP_LIMIT and max_abs_rho <= SPEARMAN_LIMIT),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "candidate_sha256": cand_sha,
        "candidate_format_pass": cand["gate"]["format_pass"],
        "max_candidate_to_focus_overlap": max_dir,
        "max_focus_to_candidate_overlap": max_rev,
        "max_abs_spearman": round(max_abs_rho, 4),
        "unique_on_focus_set": summary["candidate_unique_on_focus_set"],
        "wrote": str(OUT.relative_to(ROOT)),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
