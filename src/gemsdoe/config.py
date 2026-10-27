"""Single source of truth for the GEMS Prize problem geometry and metric constants.

Every constant here is traceable to an official source (recorded in `SOURCE`):

* metric constants (alpha=0.2, beta=0.8, R=300 m) and the submission format
  (single-band float32 GeoTIFF, EPSG:32611, 100 m, same bounds):
  https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/
* grid geometry (3730 x 3292, origin 243350 / 4508550, 100 m):
  measured from the official `sample_submission.tif` bytes, SHA-256
  2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc,
  which is pinned in registry/data_manifest.json.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# ---- competition grid (measured, not assumed) -------------------------------
HEIGHT = 3730
WIDTH = 3292
CRS = "EPSG:32611"
PIXEL_M = 100.0
ORIGIN_X = 243350.0
ORIGIN_Y = 4508550.0
TOTAL_PIXELS = HEIGHT * WIDTH
FOOTPRINT_PIXELS = 5_167_373  # finite cells of official sample_submission.tif
FEATURE_VALID_PIXELS = 5_165_852  # finite cells of band 1 of training_features.tif

# ---- metric constants (official) -------------------------------------------
ALPHA = 0.2
BETA = 0.8
RADIUS_M = 300.0
RADIUS_PX = RADIUS_M / PIXEL_M  # 3.0
EPS = 1e-12

# ---- data locations ---------------------------------------------------------
# Hash-verified official competition rasters (see registry/data_manifest.json).
DATA_DIR = ROOT / ".cache" / "data"
FEATURES_TIF = DATA_DIR / "training_features.tif"
LABELS_TIF = DATA_DIR / "labels.tif"
SAMPLE_TIF = DATA_DIR / "sample_submission.tif"

CACHE_DIR = ROOT / ".cache" / "gemsdoe"
FEATURE_STACK = CACHE_DIR / "feature_stack.npy"  # memmap (n_feat, H, W) float32
FEATURE_NAMES = CACHE_DIR / "feature_names.json"

# ---- official SHA-256 pins (integrity of the exact bytes used) -------------
SHA256 = {
    "training_features.tif": "4371c82e3b8339b807bdffcf4ef59a225520fe2988d521be208ae33743123bc5",
    "labels.tif": "7ba308ccdc4418b31a178f4f1ef21aaa6e152e4028f2f6f64b01f7eb25ae4093",
    "sample_submission.tif": "2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc",
}

# ---- band semantics (from the official data dictionary in the owner mirror's
# fixture manifest, which transcribes the competition data-tab band list) -----
BAND_NAMES = [
    "mag_anom",            # 1  magnetic anomaly
    "rtp",                 # 2  reduced-to-pole magnetic anomaly
    "tmi_hg",              # 3  TMI horizontal gradient
    "geod_2ndinv",         # 4  geodetic strain 2nd invariant
    "iso_grav_anom_slope", # 5  isostatic gravity anomaly slope
    "tc",                  # 6  magnetic tilt angle / total curvature
    "geod_shearrate",      # 7  geodetic shear rate
    "geod_dilaterate",     # 8  geodetic dilatation rate
    "tmi_vg",              # 9  TMI vertical gradient
    "deq_n100a15",         # 10 distance to earthquake
    "iso_grav_anom_vg",    # 11 isostatic gravity anomaly vertical gradient
    "det_elev",            # 12 detrended elevation
    "iso_grav_anom",       # 13 isostatic gravity anomaly
    "tmi",                 # 14 total magnetic intensity
    "depth_to_base_surf",  # 15 depth to basement surface
    "ieq_n100a15",         # 16 earthquake intensity / density
    "cond_surf",           # 17 conductivity surface
    "iso_grav_anom_hg",    # 18 isostatic gravity anomaly horizontal gradient
    "det_elev_slope",      # 19 detrended elevation slope
]
N_BANDS = len(BAND_NAMES)

SOURCE = {
    "problem": "https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/",
    "overview": "https://www.drivendata.org/competitions/306/competition-doe-gems/",
    "data": "https://www.drivendata.org/competitions/306/competition-doe-gems/data/",
    "leaderboard": "https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/",
    "rules_pdf": "https://docs.nlr.gov/docs/fy26osti/96647.pdf",
    "reference_solution": "https://github.com/drivendataorg/gems-prize-reference-solution",
    "geodawn": "https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and",
    "ingenious": "https://gdr.openei.org/submissions/1391",
    "epsg": "https://epsg.io/32611",
    "tversky": "https://en.wikipedia.org/wiki/Tversky_index",
}
