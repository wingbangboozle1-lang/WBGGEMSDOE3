#!/usr/bin/env python3
"""Read-only inspection of the two historical LST1 TIFFs and their archive.

This does not create a candidate, assess model performance, or approve upload.
Pinned comparator bytes must already be restored by audit_focus.py.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import sys
import zipfile

import numpy as np
import rasterio
from scipy.ndimage import binary_dilation

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from gems_project.audit import SAMPLE_SHA, WITNESS  # noqa: E402
from gems_project.format_preflight import raster_report  # noqa: E402
from gems_project.sources import sha256_file  # noqa: E402
from gems_project.template import COMMIT  # noqa: E402

NAMES = ('wbggems3-lst1-hybrid-20261026-0a0229da-zeros.tif',
         'wbggems3-lst1-hybrid-20261026-0a0229da-nan.tif')


def build_report(sample: Path, witness: Path, folder: Path) -> dict:
    if sha256_file(sample) != SAMPLE_SHA or sha256_file(witness) != WITNESS['sha256']:
        raise ValueError('pinned sample or witness hash mismatch')
    with rasterio.open(sample) as ds:
        shape, crs, transform = ds.shape, ds.crs, ds.transform
        foot = np.isfinite(ds.read(1)) & (ds.read_masks(1) > 0)
    with rasterio.open(witness) as ds:
        if ds.count != 1 or ds.shape != shape or ds.crs != crs or ds.transform != transform:
            raise ValueError('witness grid mismatch')
        w = ds.read(1)
    positive = np.isfinite(w) & (w > 0)
    yy, xx = np.mgrid[-3:4, -3:4]
    near = binary_dilation(positive, structure=(yy * yy + xx * xx <= 9))
    results = []
    for name in NAMES:
        file = folder / name
        fmt = raster_report(file, sample)
        with rasterio.open(file) as ds:
            if ds.count != 1 or ds.shape != shape or ds.crs != crs or ds.transform != transform:
                raise ValueError(f'archive grid mismatch: {name}')
            arr = ds.read(1)
            nodata = 'nan' if ds.nodata is not None and np.isnan(ds.nodata) else ds.nodata
        selected = np.isfinite(arr) & (arr > 0)
        inside = selected & foot
        n, ni = int(selected.sum()), int(inside.sum())
        inside_values, outside_values = arr[foot], arr[~foot]
        results.append({
            'filename': name, 'sha256': sha256_file(file), 'bytes': file.stat().st_size,
            'crs': fmt['crs'], 'shape': fmt['shape'], 'transform': fmt['transform'],
            'band_count': 1, 'dtype': fmt['dtype'], 'nodata': nodata,
            'inside_nan': int(np.isnan(inside_values).sum()),
            'inside_infinity': int(np.isinf(inside_values).sum()),
            'inside_range': [float(inside_values.min()), float(inside_values.max())],
            'inside_finite_range_0_1': bool(np.isfinite(inside_values).all() and
                                            (inside_values >= 0).all() and (inside_values <= 1).all()),
            'outside_nan': int(np.isnan(outside_values).sum()),
            'outside_zero': int((outside_values == 0).sum()),
            'positive_inside': ni, 'positive_outside': n - ni,
            'overlap_witness_at_zero_inside': float(positive[inside].mean()) if ni else None,
            'forward_overlap_witness_within_3px_all_positive': float(near[selected].mean()) if n else None,
            'forward_overlap_witness_within_3px_inside': float(near[inside].mean()) if ni else None,
            'local_allfinite_zero_policy': fmt['format_ok'],
            'local_format_problems': fmt['problems'],
            'verdict': 'RESEARCH ONLY / DO NOT SUBMIT; literal duplicate stop',
            'portal_acceptance': 'unknown',
        })
    archive = folder / NAMES[0].replace('.tif', '.zip')
    with zipfile.ZipFile(archive) as z:
        entries = z.infolist()
        if len(entries) != 1 or entries[0].filename != NAMES[0]:
            raise ValueError('unexpected archive contents')
        bad = z.testzip()
        h = hashlib.sha256()
        with z.open(entries[0]) as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                h.update(chunk)
        member_sha = h.hexdigest()
    return {
        'audit': 'read-only archive artifact inspection; no experiment or competition slot',
        'checked_utc': datetime.now(timezone.utc).isoformat(),
        'sample_sha256': SAMPLE_SHA, 'sample_provenance': 'public owner mirror, not organizer-authenticated',
        'witness_sha256': WITNESS['sha256'],
        'overlap_definition': 'finite and >0 support; directed Euclidean radius 3 pixels',
        'tiffs': results,
        'zip': {'filename': archive.name, 'sha256': sha256_file(archive),
                'crc_test_passed': bad is None, 'single_expected_member': True,
                'member_sha256': member_sha, 'matches_tiff': member_sha == results[0]['sha256']},
        'score': 'unknown; historical holdout is not established as fold-local',
        'approved_for_submission': False,
    }


def main() -> int:
    sample = ROOT / '.cache' / f'57GEMSDOE-{COMMIT}' / 'data/official/sample_submission.tif'
    witness = ROOT / '.cache/references/witness17.tif'
    try:
        report = build_report(sample, witness, ROOT / 'submission')
    except Exception as error:
        print(f'ARCHIVE AUDIT INCOMPLETE / DO NOT SUBMIT: {error}', file=sys.stderr)
        return 2
    output = ROOT / 'evidence/archive_audit.json'
    output.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    print(f"Archive inspected, no candidate created: {output.relative_to(ROOT)}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
