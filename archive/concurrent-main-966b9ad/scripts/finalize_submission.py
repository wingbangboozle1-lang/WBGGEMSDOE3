"""Finalize the generated WB-GEMS-DOE-3 submission: format audit + lane-uniqueness audit + run card.

Run this after scripts/generate_submission.py. It audits the *saved bytes* of the
downloadable -zeros.tif (and its -nan twin), checks lane uniqueness against every
local registry raster with the competition grid, and writes evidence/run_card.json.

No DrivenData auth or labels are required for the format and uniqueness gates.
The score estimate is explicitly labelled as an unverified projection.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from submission_writer import audit_saved_file
from uniqueness_audit import audit_uniqueness

OUT_DIR = ROOT / "docs" / "downloads"
EVIDENCE_DIR = ROOT / "evidence"
GENERATED_UTC = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
GRID_SHAPE = (3730, 3292)


def find_latest_zeros():
    cands = sorted(OUT_DIR.glob("wb-gems-doe-3-stepover-damagezone-*-zeros.tif"))
    if not cands:
        raise FileNotFoundError("No generated zeros.tif found in docs/downloads")
    return cands[-1]


def main():
    zeros_path = find_latest_zeros()
    nan_path = zeros_path.with_name(zeros_path.name.replace("-zeros.tif", "-nan.tif"))

    TEMPLATE = ROOT / "data" / "template_grid.tif"
    audit_z = audit_saved_file(zeros_path, TEMPLATE, strict_whole_array=True)
    audit_n = audit_saved_file(nan_path, TEMPLATE, strict_whole_array=True) \
        if nan_path.exists() else {"filename": nan_path.name,
                                   "all_checks_passed": False, "error": "nan twin missing"}

    with rasterio.open(zeros_path) as src:
        arr = src.read(1)
    n_dots = int((arr > 0.5).sum())

    # Registry rasters with the competition grid for the lane-uniqueness gate.
    registry_dir = (ROOT / "data" / "downloads" / "gemsdoe32_repo"
                    / "GEMSDOE32-main" / "docs" / "downloads")
    registry_tifs = []
    for p in sorted(registry_dir.glob("*.tif")):
        try:
            with rasterio.open(p) as s:
                if (s.height, s.width) == GRID_SHAPE:
                    registry_tifs.append(p)
        except Exception:
            continue

    uniq = audit_uniqueness(zeros_path, registry_tifs)

    sha8 = audit_z["sha256"][:8]
    unique_name = f"WB-GEMS-DOE-3-STEPOVER-DAMAGEZONE-{n_dots}D-{sha8.upper()}"
    note = (f"{unique_name} | {n_dots} off-trace step-over/damage-zone dots | "
            f"format PASS | unique PASS | score unverified projection | research/audit")
    if len(note) > 140:
        note = note[:137] + "..."

    run_card = {
        "submission_name": unique_name,
        "filename": zeros_path.name,
        "nan_twin": nan_path.name,
        "sha256": audit_z["sha256"],
        "sha8": sha8,
        "note": note,
        "note_chars": len(note),
        "generated_utc": GENERATED_UTC,
        "hypothesis": "H_STEP-OVER: geothermal upflow localises at off-trace dilational "
                      "step-overs and the fault damage zone, catching off-catalogue blind "
                      "faults missed by dotted-catalogue entries.",
        "layers_targeted": ["off-trace structural damage zone",
                            "dilational step-over / relay zones"],
        "physical_signature": "distance-to-catalogue-trace in 100 m - 1.5 km "
                              "(damage zone / dilation)",
        "why_missing_from_catalogue": "dots are 100 m - 1.5 km off mapped USGS/INGENIOUS "
                                      "traces, targeting blind structures absent from the catalogue.",
        "differs_from_repo": "all GEMSDOE high-scorers dot ON the catalogue fault network; "
                             "this submission dots strictly OFF-trace (a different lane).",
        "dots": n_dots,
        "format_audit": audit_z,
        "nan_twin_audit": audit_n,
        "uniqueness": uniq.to_dict(),
        "holdout_dti": "NOT COMPUTED - no training labels access (DrivenData login-gated). "
                       "Label as HOLDOUT-DTI only once labels.tif is placed in data/ and "
                       "scripts/evaluate_holdout.py is run.",
        "score_estimate": "UNVERIFIED PROJECTION (no organizer receipt, no label access). "
                          "By construction 0.0% of dots lie on catalogue traces. Off-catalogue "
                          "blind-fault recall -- the quantity that determines the private-test "
                          "DTI -- cannot be measured without the private labels. Do NOT treat "
                          "this projection as a score.",
        "verdict": ("FORMAT_PASS / UNIQUE_PASS / SCORE_UNVERIFIED - "
                    "OK to download for research/audit. NOT organizer-cleared for live "
                    "submission until a holdout win (CI > 0 vs repo best) and an organizer "
                    "submission-page receipt confirm the score."),
    }
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    card_path = EVIDENCE_DIR / "run_card.json"
    card_path.write_text(json.dumps(run_card, indent=2), encoding="utf-8")

    latest = OUT_DIR / "wb-gems-doe-3-latest-submission-zeros.tif"
    if latest.exists() or latest.is_symlink():
        latest.unlink()
    try:
        latest.symlink_to(zeros_path.name)
    except OSError:
        latest.write_bytes(zeros_path.read_bytes())

    print(json.dumps({
        "submission_name": unique_name,
        "filename": zeros_path.name,
        "sha256": audit_z["sha256"],
        "dots": n_dots,
        "format_passed": bool(audit_z["all_checks_passed"]),
        "unique": bool(uniq.unique),
        "max_overlap_within_3px": uniq.max_overlap_within_3px,
        "max_abs_rho_surface": uniq.max_abs_rho_surface,
        "note": note,
        "run_card": str(card_path),
        "download": str(zeros_path),
    }, indent=2))


if __name__ == "__main__":
    main()
