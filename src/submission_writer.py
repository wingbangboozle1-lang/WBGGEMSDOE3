"""Retired local writers. They are not submission-ready; see evidence/run_card.json."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import rasterio

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.validate import validate_submission

SUBMISSION_DIR = Path(__file__).resolve().parents[1] / "submission"


def write_submission(array, out_path, crs=None, transform=None,
                     nodata=None, dtype=np.float32):
    raise RuntimeError("BLOCKED: retired local writer/validator; see evidence/run_card.json")
    array = np.asarray(array, dtype=np.float64)
    if array.ndim != 2:
        raise ValueError("array must be 2D (single band)")
    if not np.all(np.isfinite(array)):
        raise ValueError("array contains NaN or inf")
    if array.min() < 0.0 or array.max() > 1.0:
        raise ValueError("array values must be in [0, 1]")

    height, width = array.shape
    profile = {"driver": "GTiff", "dtype": np.dtype(dtype).name, "width": width,
               "height": height, "count": 1, "compress": "deflate"}
    if crs is not None:
        profile["crs"] = crs
    if transform is not None:
        profile["transform"] = transform
    if nodata is not None:
        profile["nodata"] = nodata

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(out_path, "w", **profile) as dst:
        dst.write(array.astype(dtype), 1)
    return out_path


def conform_to_reference(array, reference_path, out_path):
    """Resize array to the reference grid shape and adopt its profile.

    Georeference-correct reprojection requires the source array to already carry
    a real transform/CRS. If the array shape matches the reference shape, we
    write it directly with the reference profile (georeference preserved).
    Otherwise we fall back to a bilinear resize and flag the output as
    NOT geometrically conformant (must be re-derived against the real grid
    before submission).
    """
    raise RuntimeError("BLOCKED: retired local writer/validator; see evidence/run_card.json")
    array = np.asarray(array, dtype=np.float64)
    with rasterio.open(reference_path) as ref:
        ref_profile = ref.profile.copy()
        ref_shape = (ref.height, ref.width)
        ref_dtype = ref.dtypes[0]

    out = np.clip(array, 0.0, 1.0)
    conformant = array.shape == ref_shape
    if not conformant:
        from PIL import Image
        im = Image.fromarray(out)
        im = im.resize((ref_shape[1], ref_shape[0]), Image.Resampling.BILINEAR)
        out = np.asarray(im, dtype=np.float64)
    out = np.clip(out, 0.0, 1.0)

    profile = ref_profile.copy()
    profile.update(count=1, dtype=str(ref_dtype), compress="deflate",
                   nodata=None)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(out_path, "w", **profile) as dst:
        dst.write(out.astype(ref_dtype), 1)
    return out_path, conformant


if __name__ == "__main__":
    raise SystemExit("BLOCKED: retired local writers are disabled; see evidence/run_card.json")
