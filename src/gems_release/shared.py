"""Shared, provenance-checked access to the pinned template and the grid.

The competition rasters and the pinned evaluator live in the SHA-verified
57GEMSDOE template archive (``src/gems_project/template.py``). This module is a
thin, read-only bridge: it never copies, rewrites or forks the shared tools.
"""
from __future__ import annotations

import functools
import hashlib
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]

#: Official statements this pipeline is built on. Each entry is a claim plus the
#: URL a reviewer can open to check it. Numbers below are transcribed, not
#: inferred.
SOURCES = {
    "metric": {
        "url": "https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/",
        "claims": [
            "DTI(alpha=0.2, beta=0.8) with a triangular kernel, R = 300 m",
            "TP_w = sum_g max_x p(x) k(d(x,g))",
            "FP_w = sum_{x: p(x)>0} p(x) [1 - max_g k(d(x,g))]",
            "FN_w = sum_g [1 - max_x p(x) k(d(x,g))]",
            "submission: single-band float32 GeoTIFF, EPSG:32611, 100 m, "
            "same bounds, values in [0,1], null/nan outside the bounds",
        ],
    },
    "known_fault_masking": {
        "url": "https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516",
        "claims": [
            "staff chrisk-dd, Sep 16: pixels of known USGS/INGENIOUS faults are "
            "masked / excluded from evaluation and do not count towards penalty terms",
            "re-evaluation will also mask/exclude the existing faults",
        ],
    },
    "leaderboard_aggregation": {
        "url": "https://community.drivendata.org/t/leaderboard-aggregation-pooled-over-public-test-pixels-or-mean-of-per-chunk-scores/11550",
        "claims": [
            "staff Chris Kucharczyk, Oct 1: public score pools over all public pixels "
            "and computes a single Tversky index",
            "private leaderboard is computed the same way",
            "final re-evaluation is on the entire GeoDAWN area",
        ],
    },
    "labels_definition": {
        "url": "https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/",
        "claims": [
            "labels come from USGS Quaternary fault maps and INGENIOUS",
            "the initial-round test set is expert-mapped faults absent from the public database",
        ],
    },
}

BAND_NAMES = {
    1: "mag_anom", 2: "rtp", 3: "tmi_hg", 4: "geod_2ndinv", 5: "iso_grav_anom_slope",
    6: "tc", 7: "geod_shearrate", 8: "geod_dilaterate", 9: "tmi_vg",
    10: "deq_n100a15", 11: "iso_grav_anom_vg", 12: "det_elev", 13: "iso_grav_anom",
    14: "tmi", 15: "depth_to_base_surf", 16: "ieq_n100a15", 17: "cond_surf",
    18: "iso_grav_anom_hg", 19: "det_elev_slope",
}
BAND_INDEX = {v: k for k, v in BAND_NAMES.items()}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


@functools.lru_cache(maxsize=1)
def template_root() -> Path:
    """Locate (and if needed restore) the SHA-pinned shared template."""
    sys.path.insert(0, str(ROOT / "src"))
    from gems_project.template import ensure_template  # noqa: PLC0415

    root = ensure_template()
    tpl_src = str(root / "src")
    if tpl_src not in sys.path:
        sys.path.insert(0, tpl_src)
    return root


def shared_metric():
    """The pinned shared metric module (``gems57.metric``). Never forked."""
    template_root()
    from gems57 import metric  # noqa: PLC0415

    return metric


def shared_evaluator():
    template_root()
    from gems57 import evaluate_holdout  # noqa: PLC0415

    return evaluate_holdout


def data_path(name: str) -> Path:
    """Path inside the pinned template's ``data/`` directory."""
    return template_root() / "data" / name


def band_plane(index: int) -> np.ndarray:
    """Read band ``index`` (1-based) of the official feature stack as float32.

    Uses the template's own ``band-NN.npy`` cache when present (it is produced by
    ``scripts/prepare_data.py --cache-bands`` and is bit-identical to the GeoTIFF
    band), otherwise reads the GeoTIFF.
    """
    root = template_root()
    cache = root / ".cache" / "features" / f"band-{index:02d}.npy"
    if cache.is_file():
        return np.load(cache)
    import rasterio  # noqa: PLC0415

    with rasterio.open(root / "data" / "official" / "training_features.tif") as src:
        return src.read(index).astype(np.float32, copy=False)


def load_masks() -> tuple[np.ndarray, np.ndarray]:
    """Return ``(footprint, catalogue)`` boolean grids from the pinned rasters.

    ``footprint`` is the set of finite cells of ``sample_submission.tif`` (the
    scored study area). ``catalogue`` is the mapped-fault mask
    (``existing_faults.tif == 1``), which the official scorer excludes.
    """
    import rasterio  # noqa: PLC0415

    root = template_root() / "data" / "official"
    with rasterio.open(root / "sample_submission.tif") as src:
        footprint = np.isfinite(src.read(1))
    with rasterio.open(root / "existing_faults.tif") as src:
        catalogue = src.read(1) == 1
    return footprint, catalogue & footprint


def provenance() -> dict:
    """SHA-256 of every input raster this pipeline can read."""
    root = template_root() / "data"
    names = [
        "official/labels.tif", "official/existing_faults.tif",
        "official/sample_submission.tif", "official/training_features.tif",
        "external/sgmc_faults_100m.tif", "external/derived_sgmc_faults_100m.tif",
        "external/trace_segments_utm11.csv",
    ]
    out = {}
    for name in names:
        p = root / name
        out[name] = {"exists": p.is_file(),
                     "sha256": sha256_file(p) if p.is_file() else None,
                     "bytes": p.stat().st_size if p.is_file() else None}
    return {"template": str(root.parent), "files": out}
