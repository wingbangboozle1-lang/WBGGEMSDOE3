#!/usr/bin/env python3
"""Shared submission GeoTIFF writer and automated multi-gate validator (GEMSDOE31).

Reuses ``scripts/build_submission.py`` and ``src/gemsdoe31/submission.py`` without private forks.
Writes:
* ``<outdir>/<name>-nan.tif``       (official null/NaN outside footprint convention)
* ``<outdir>/<name>-allfinite.tif`` (defensive zero-outside convention)
* ``<outdir>/<name>-nan.zip``       (single-GeoTIFF zip archive)
* ``<outdir>/<name>-format-check.json`` (full machine-verified format & gate receipt)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from build_submission import footprint_mask, write_variants  # noqa: E402
from gemsdoe31.submission import sha256_file, validate_submission  # noqa: E402
from scipy.ndimage import distance_transform_edt  # noqa: E402


def write_validated_submission_variants(
    dots: np.ndarray,
    template_path: Path,
    labels_path: Path,
    out_dir: Path,
    submission_name: str,
    note: str,
    receipt_path: Path | None = None,
) -> dict:
    """Write ``-nan.tif``, ``-allfinite.tif``, ``-nan.zip`` enforcing B>2 px collar & strict validation."""
    if len(note) > 140:
        raise ValueError(f"Submission note exceeds 140 characters ({len(note)}): {note!r}")
    footprint = footprint_mask(template_path)
    with rasterio.open(labels_path) as src:
        catalogue = (src.read(1) == 1) & footprint
    d_cat = distance_transform_edt(~catalogue)
    clean_dots = np.asarray(dots, dtype=bool) & footprint & (d_cat > 2.0)

    out_dir.mkdir(parents=True, exist_ok=True)
    paths = write_variants(clean_dots, footprint, out_dir / submission_name, name=submission_name)
    rep_nan = validate_submission(paths["nan"], template_path, convention="nan-outside")
    rep_fin = validate_submission(paths["allfinite"], template_path, convention="all-finite")
    if not rep_nan["ok_to_upload_format_only"] or not rep_fin["ok_to_upload_format_only"]:
        raise RuntimeError(f"Validation failed: nan={rep_nan['hard_failures']} allfinite={rep_fin['hard_failures']}")

    payload = {
        "schema_version": 1,
        "submission_name": submission_name,
        "submission_note": note,
        "submission_note_length": len(note),
        "ok_to_download_and_submit": bool(rep_nan["ok_to_upload_format_only"] and rep_fin["ok_to_upload_format_only"]),
        "primary_nan_variant": {
            "path": str(paths["nan"]),
            "zip_path": str(paths["zip"]),
            "sha256": rep_nan["sha256"],
            "zip_sha256": sha256_file(paths["zip"]),
            "bytes": rep_nan["bytes"],
            "zip_bytes": paths["zip"].stat().st_size,
            "validator_output": rep_nan,
        },
        "fallback_allfinite_variant": {
            "path": str(paths["allfinite"]),
            "sha256": rep_fin["sha256"],
            "bytes": rep_fin["bytes"],
            "validator_output": rep_fin,
        },
        "collar_check": {
            "emitted_dots": int(clean_dots.sum()),
            "dots_on_catalogue_exact": int((clean_dots & catalogue).sum()),
            "dots_within_200m_of_catalogue": int((clean_dots & (d_cat <= 2.0)).sum()),
        },
    }
    if receipt_path is not None:
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        receipt_path.write_text(json.dumps(payload, indent=2) + "\n")
    return payload


def emit_and_validate_submission(
    dots_mask: np.ndarray,
    *,
    template_path: Path,
    labels_path: Path,
    outdir: Path,
    name: str,
    note: str,
    values: np.ndarray | None = None,
    gate_summary: dict | None = None,
) -> dict:
    """Write ``-nan.tif``, ``-allfinite.tif``, ``-nan.zip`` and verify every format & range invariant."""
    if len(note) > 140:
        raise ValueError(f"Submission note exceeds 140 characters ({len(note)} chars): {note!r}")
    footprint = footprint_mask(template_path)
    if dots_mask.shape != footprint.shape:
        raise ValueError(f"dots_mask shape {dots_mask.shape} != template {footprint.shape}")

    clean_dots = np.asarray(dots_mask, dtype=bool) & footprint
    with rasterio.open(labels_path) as src:
        catalogue = (src.read(1) == 1) & footprint

    stem = outdir / name
    paths = write_variants(clean_dots, footprint, stem, name=name, values=values)

    val_nan = validate_submission(paths["nan"], template_path, convention="nan-outside")
    val_fin = validate_submission(paths["allfinite"], template_path, convention="all-finite")
    if not val_nan["ok_to_upload_format_only"] or not val_fin["ok_to_upload_format_only"]:
        raise RuntimeError(
            f"Generated TIFF failed strict validator: nan={val_nan['hard_failures']} "
            f"allfinite={val_fin['hard_failures']}"
        )

    payload = {
        "schema_version": 1,
        "name": name,
        "note": note,
        "note_length": len(note),
        "dots": int(clean_dots.sum()),
        "dots_on_catalogue": int((clean_dots & catalogue).sum()),
        "files": {
            k: str(v.relative_to(ROOT) if v.is_absolute() and v.is_relative_to(ROOT) else v)
            for k, v in paths.items()
        },
        "validation": {"nan": val_nan, "allfinite": val_fin},
        "automated_gates": gate_summary,
        "warnings": [
            "Format validation is local and automated. It cannot prove live DrivenData organizer acceptance.",
            "Promotion to an actual weekly DrivenData slot remains a separate human selector step within the 3/week cap.",
        ],
    }
    receipt_path = stem.with_name(stem.name + "-format-check.json")
    receipt_path.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mask-npy", type=Path, required=True, help="Boolean/float 2D .npy mask of emitted dots")
    parser.add_argument("--template", type=Path, default=ROOT / ".cache/data/sample_submission.tif")
    parser.add_argument("--labels", type=Path, default=ROOT / ".cache/data/labels.tif")
    parser.add_argument("--outdir", type=Path, default=ROOT / "docs/downloads")
    parser.add_argument("--name", required=True)
    parser.add_argument("--note", required=True, help="Short portal comment (<= 140 chars)")
    parser.add_argument("--gates-json", type=Path, default=None)
    args = parser.parse_args()

    arr = np.load(args.mask_npy, allow_pickle=False)
    dots = np.nan_to_num(arr, nan=0.0) > 0.5
    gates = json.loads(args.gates_json.read_text()) if args.gates_json and args.gates_json.is_file() else None
    receipt = emit_and_validate_submission(
        dots,
        template_path=args.template.resolve(),
        labels_path=args.labels.resolve(),
        outdir=args.outdir.resolve(),
        name=args.name,
        note=args.note,
        gate_summary=gates,
    )
    print(
        json.dumps(
            {
                "name": receipt["name"],
                "dots": receipt["dots"],
                "dots_on_catalogue": receipt["dots_on_catalogue"],
                "nan_sha256": receipt["validation"]["nan"]["sha256"],
                "allfinite_sha256": receipt["validation"]["allfinite"]["sha256"],
                "format_ok_nan": receipt["validation"]["nan"]["ok_to_upload_format_only"],
                "format_ok_allfinite": receipt["validation"]["allfinite"]["ok_to_upload_format_only"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
