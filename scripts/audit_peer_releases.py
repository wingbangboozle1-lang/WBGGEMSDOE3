#!/usr/bin/env python3
"""Read-only byte inspection of recently featured peer TIFFs against one witness.

These are existing public artifacts, fetched only for research. No file is
created as a model candidate, no holdout is run, and no slot is selected.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sys

import numpy as np
import rasterio
from scipy.ndimage import binary_dilation

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from gems_project.audit import LABEL_SHA, SAMPLE_SHA, WITNESS, get_reference, source_url  # noqa: E402
from gems_project.format_preflight import raster_report  # noqa: E402
from gems_project.sources import sha256_file  # noqa: E402
from gems_project.template import ensure_template  # noqa: E402


def audit() -> dict:
    template = ensure_template()
    sample = template / 'data/official/sample_submission.tif'
    labels = template / 'data/official/existing_faults.tif'
    if sha256_file(sample) != SAMPLE_SHA or sha256_file(labels) != LABEL_SHA:
        raise ValueError('pinned sample or fault mirror hash mismatch')
    with rasterio.open(sample) as ds:
        shape, crs, transform = ds.shape, ds.crs, ds.transform
        foot = np.isfinite(ds.read(1)) & (ds.read_masks(1) > 0)
    with rasterio.open(labels) as ds:
        if ds.count != 1 or ds.shape != shape or ds.crs != crs or ds.transform != transform:
            raise ValueError('fault mirror grid mismatch')
        faults = ds.read(1) > 0
    cache = ROOT / '.cache/references'
    witness_file = get_reference(WITNESS, cache, 'witness17.tif')
    with rasterio.open(witness_file) as ds:
        if ds.count != 1 or ds.shape != shape or ds.crs != crs or ds.transform != transform:
            raise ValueError('registered witness grid mismatch')
        a = ds.read(1)
    positive = np.isfinite(a) & (a > 0)
    yy, xx = np.mgrid[-3:4, -3:4]
    near = binary_dilation(positive, structure=yy*yy + xx*xx <= 9)
    rows = []
    manifest = json.loads((ROOT / 'registry/recent_featured.json').read_text())
    for item in manifest['artifacts']:
        file = get_reference(item, cache, item['site'] + '-recent.tif')
        report = raster_report(file, sample)
        with rasterio.open(file) as ds:
            if ds.count != 1 or ds.shape != shape or ds.crs != crs or ds.transform != transform:
                raise ValueError(f"unmatched candidate grid: {item['site']}")
            values = ds.read(1)
        selected = np.isfinite(values) & (values > 0)
        inside = selected & foot
        n, ni = int(selected.sum()), int(inside.sum())
        if not n:
            raise ValueError(f"empty positive support: {item['site']}")
        overlap = float(near[selected].mean())
        rows.append({
            'site': item['site'], 'filename': file.name, 'source_filename': Path(item['path']).name,
            'source': source_url(item), 'source_context': item['source_context'],
            'source_readme': f"https://github.com/{item['repo']}/blob/{item['ref']}/README.md",
            'sha256': report['sha256'], 'positive_inside': ni, 'positive_outside': n-ni,
            'positive_on_mirrored_fault_inside': int((inside & faults).sum()),
            'forward_overlap_witness_within_3px_all_positive': overlap,
            'overlap_witness_at_zero_inside': float(positive[inside].mean()) if ni else None,
            'local_allfinite_zero_diagnostic': report['format_ok'],
            'local_format_problems': report['problems'],
            'grid': {'crs': report['crs'], 'shape': report['shape'],
                     'transform': report['transform'], 'dtype': report['dtype']},
            'inside_nan': report['inside_nan_cells'],
            'inside_range': [report['inside_min'], report['inside_max']],
            'literal_duplicate': overlap > .70,
            'score': 'unknown; no organizer receipt or validated transfer estimate',
            'approved_for_submission': False,
        })
    return {
        'evidence_class': 'READ-ONLY ARTIFACT AUDIT; no new candidate, model experiment or slot',
        'checked_utc': datetime.now(timezone.utc).isoformat(),
        'sample_sha256': SAMPLE_SHA, 'fault_sha256': LABEL_SHA,
        'sample_provenance': 'public owner mirror, not organizer-authenticated',
        'witness_sha256': WITNESS['sha256'],
        'scope': 'one registered witness and saved bytes, not a full registry or holdout replay',
        'artifacts': rows, 'approved_for_submission': False,
    }


def main() -> int:
    try:
        report = audit()
        output = ROOT / 'evidence/recent_peer_audit.json'
        output.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    except Exception as exc:
        print(f'PEER ARTIFACT AUDIT INCOMPLETE / DO NOT SUBMIT: {exc}', file=sys.stderr)
        return 2
    print(f"Inspected {len(report['artifacts'])} existing peer files; no candidate created: {output.relative_to(ROOT)}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
