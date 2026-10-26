"""
Submission validation gates.

A generated GeoTIFF must pass ALL of the following before it is considered safe
to download and submit:

  1. Single-band GeoTIFF
  2. No NaN / inf inside the submission footprint
  3. All values in [0, 1]
  4. CRS, shape, and geotransform match the competition reference grid
     (sample_submission.tif / training_features.tif)
  5. Finite file size, readable by rasterio

Any failure is a hard block: the file is flagged NOT OK to submit.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import numpy as np
import rasterio


@dataclass
class ValidationResult:
    ok: bool
    passed: list[str]
    failed: list[str]
    metrics: dict
    sha256: str

    @property
    def summary(self) -> str:
        status = "PASS" if self.ok else "BLOCK"
        lines = [f"[{status}] submission validation", f"sha256: {self.sha256}"]
        for p in self.passed:
            lines.append(f"  PASS: {p}")
        for f in self.failed:
            lines.append(f"  FAIL: {f}")
        lines.append("  metrics: " + ", ".join(f"{k}={v}" for k, v in self.metrics.items()))
        return "\n".join(lines)


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def validate_submission(
    submission_path: str,
    reference_path: str | None = None,
    *,
    require_single_band: bool = True,
    value_range: tuple[float, float] = (0.0, 1.0),
) -> ValidationResult:
    passed: list[str] = []
    failed: list[str] = []
    metrics: dict = {}

    # --- readability & band count
    try:
        with rasterio.open(submission_path) as src:
            bands = src.count
            crs = src.crs
            transform = src.transform
            shape = (src.height, src.width)
            dtype = src.dtypes[0] if bands else None
            data = src.read(1) if bands >= 1 else None
    except Exception as exc:
        return ValidationResult(
            ok=False,
            passed=[],
            failed=[f"could not open GeoTIFF: {exc}"],
            metrics={},
            sha256=sha256_file(submission_path),
        )

    metrics.update(
        bands=int(bands),
        crs=str(crs),
        transform=str(transform),
        shape=[int(shape[0]), int(shape[1])],
        dtype=str(dtype),
    )

    if require_single_band and bands != 1:
        failed.append(f"expected single-band GeoTIFF, got {bands} band(s)")
    else:
        passed.append(f"single-band GeoTIFF ({bands} band)")

    # --- NaN / inf inside footprint
    if data is not None:
        n_nonfinite = int((~np.isfinite(data)).sum())
        metrics["n_nonfinite_pixels"] = n_nonfinite
        if n_nonfinite > 0:
            failed.append(f"{n_nonfinite} NaN/inf pixels inside footprint")
        else:
            passed.append("no NaN or inf inside footprint")

        # --- values in [0, 1]
        vmin = float(np.nanmin(data))
        vmax = float(np.nanmax(data))
        metrics["value_min"] = vmin
        metrics["value_max"] = vmax
        lo, hi = value_range
        if vmin < lo or vmax > hi:
            failed.append(f"values outside [{lo}, {hi}]: min={vmin}, max={vmax}")
        else:
            passed.append(f"all values in [{lo}, {hi}] (min={vmin:.4f}, max={vmax:.4f})")
    else:
        failed.append("no raster band to validate")

    # --- CRS / shape / transform match reference
    if reference_path is not None:
        try:
            with rasterio.open(reference_path) as ref:
                ref_crs = ref.crs
                ref_transform = ref.transform
                ref_shape = (ref.height, ref.width)
            crs_match = crs == ref_crs
            trans_match = transform == ref_transform
            shape_match = shape == ref_shape
            metrics["crs_match"] = bool(crs_match)
            metrics["transform_match"] = bool(trans_match)
            metrics["shape_match"] = bool(shape_match)
            metrics["reference_crs"] = str(ref_crs)
            metrics["reference_transform"] = str(ref_transform)
            metrics["reference_shape"] = [int(ref_shape[0]), int(ref_shape[1])]
            if crs_match and trans_match and shape_match:
                passed.append("CRS / shape / geotransform match reference grid")
            else:
                failed.append(
                    "CRS/shape/transform mismatch vs reference "
                    f"(crs={crs_match}, transform={trans_match}, shape={shape_match})"
                )
        except Exception as exc:
            failed.append(f"could not open reference grid: {exc}")
    else:
        passed.append("no reference grid supplied (skipping CRS/shape/transform check)")

    ok = len(failed) == 0
    return ValidationResult(ok=ok, passed=passed, failed=failed, metrics=metrics, sha256=sha256_file(submission_path))


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("usage: python -m src.validate <submission.tif> [reference.tif]")
        sys.exit(2)
    ref = sys.argv[2] if len(sys.argv) > 2 else None
    res = validate_submission(sys.argv[1], ref)
    print(res.summary)
    sys.exit(0 if res.ok else 1)
