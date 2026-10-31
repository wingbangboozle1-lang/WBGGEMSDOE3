#!/usr/bin/env python3
"""Build the catalogue-independent structural feature planes.

Writes ``data/work/planes/<name>.npy`` (float32, robust z-scores, NaN where the
source band is invalid) plus ``evidence/release/feature_registry.json``.

Usage::

    python scripts/release_build_features.py            # all planes
    python scripts/release_build_features.py --only topo_ridge mag_hg_line
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems_release import features, shared  # noqa: E402

OUT = ROOT / "data" / "work" / "planes"
EVID = ROOT / "evidence" / "release"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", default=None)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    EVID.mkdir(parents=True, exist_ok=True)
    footprint, _catalogue = shared.load_masks()
    get = features.build_band_reader()

    names = ["topo_ridge", "topo_valley", "topo_curv", "topo_relief",
             "mag_hg_line", "mag_vg_line", "mag_low_line",
             "grav_hg_line", "grav_bp_line", "strain_line", "seis_line",
             "cond_line", "depth_bp_line", "concord"]
    if args.only:
        names = [n for n in names if n in args.only]

    registry, built = [], set()
    if (EVID / "feature_registry.json").is_file():
        registry = json.loads((EVID / "feature_registry.json").read_text())["planes"]

    for name in names:
        dest = OUT / f"{name}.npy"
        t0 = time.time()
        if dest.is_file() and not args.force:
            print(f"[skip] {name} exists")
            continue
        if name == "concord":
            invalid = ~footprint
            plane = features.concordance_plane(get)
            meta = dict(name="concord", bands=list(features.CONCORD_CATEGORIES),
                        category="fusion",
                        target="multi-physics strike concordance",
                        mimic="any single-physics linear artefact that coincides "
                              "by chance with one other category")
        else:
            spec = features.PLANES[name]
            band_valid = None
            for b in spec["bands"]:
                v = np.isfinite(get(b))
                band_valid = v if band_valid is None else (band_valid & v)
            invalid = ~band_valid
            plane = spec["fn"](get)
            meta = dict(name=name, bands=spec["bands"], category=spec["category"],
                        target=spec["target"], mimic=spec["mimic"])
        plane = features.sanitise(plane, invalid)
        z = features.robust_z(plane)
        np.save(dest, z, allow_pickle=False)
        ok = np.isfinite(z) & footprint
        meta.update(
            path=str(dest.relative_to(ROOT)), dtype="float32",
            sha256=shared.sha256_file(dest),
            footprint_valid=int(ok.sum()),
            footprint_valid_fraction=float(ok.sum() / max(1, footprint.sum())),
            z_min=float(np.nanmin(z)), z_max=float(np.nanmax(z)),
            z_median=float(np.nanmedian(z[ok])),
            seconds=round(time.time() - t0, 1),
        )
        registry = [r for r in registry if r["name"] != name] + [meta]
        built.add(name)
        print(f"[plane] {name:14s} valid {meta['footprint_valid']:>9,d} "
              f"({meta['footprint_valid_fraction']:.3f}) z[{meta['z_min']:+.2f},"
              f"{meta['z_max']:+.2f}] {meta['seconds']}s", flush=True)

    registry.sort(key=lambda r: r["name"])
    (EVID / "feature_registry.json").write_text(json.dumps({
        "generated_by": "scripts/release_build_features.py",
        "design_rule": "no plane uses the fault catalogue; catalogue is used only "
                       "for supervised labels under spatial blocking and for the "
                       "official masking geometry",
        "provenance": shared.provenance(),
        "planes": registry,
    }, indent=2) + "\n")
    print(f"[done] {len(registry)} planes -> {EVID/'feature_registry.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
