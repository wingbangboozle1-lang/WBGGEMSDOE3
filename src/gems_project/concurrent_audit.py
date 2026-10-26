"""Read-only review of TIFFs merged by parallel agents; not a geological experiment."""
from __future__ import annotations

from datetime import datetime, timezone
import math
from pathlib import Path
import sys

import numpy as np
import rasterio

from .sources import download_github_file, sha256_file
from .template import ensure_template

ROOT = Path(__file__).resolve().parents[2]
REF = '966b9ad722df057ca21ac5d6666c54e4626c957c'
REPO = 'wingbangboozle1-lang/WBGGEMSDOE3'
BASE = 'docs/downloads/wb-gems-doe-3-stepover-damagezone-35000d-20261026T215413Z-'
ARTIFACTS = {
    'parallel_template': ('data/template_grid.tif', '6a1dde6f8db53b6a2c6f3a8edbc38a85c728ddb41c02754c164c0f70a5bbe21d', 'e0761b0766cbe203b1c6c53ee12307f7c93379f4'),
    'step_zeros': (BASE + 'zeros.tif', '5d4515665dc8f3f31aa0249a32a56002f86aef199c2033cb39d836bc41adb059', 'ae0aac0ee7643b31149883b7d46b5c2261914f70'),
    'step_nan_tag': (BASE + 'nan.tif', '58b34e2a24df99bc2857df2e6248075d65955592cd838e8e20dad2d1c1cfbd5a', 'c2319aec2575a8e0bcda0ff761a3fc2ceb28d06a'),
    'standin': ('site/assets/downloads/gems-hnew01-stepper-dblind-unique.tif', '0747772166aec53eb11d5f50f5d18d52b28243c18ba57b07645c0cdc5621656d', '8041d4319f754bde1938dc4778f87804b9be5e94'),
    'h80_archive': ('archive/concurrent-8488b95/submissions/unique_submissions/gems-unique-h80-hydrothermal-conduit-20261026-000000Z-unique-sha.tif', 'a40f70f3d0ceb96d75977a30d66faaa8071c01dd118f2c8c46ef8be2fd718aa1', '0ff1fe6e81ab827a44a0f041a9e20d7987fdd35c'),
}


def audit_concurrent(template_root: Path | None = None, cache: Path | None = None) -> dict:
    template = ensure_template(template_root)
    sys.path.insert(0, str(template / 'src'))
    from gems57.gates import format_report
    from gems57.uniqueness import _near
    cache = Path(cache) if cache else ROOT / '.cache' / 'concurrent-pinned'
    cache.mkdir(parents=True, exist_ok=True)
    files = {}
    for key, (path, sha, blob) in ARTIFACTS.items():
        files[key] = download_github_file(REPO, REF, path, cache / f'{key}.tif', sha, blob)
    sample = template / 'data/official/sample_submission.tif'
    labels = template / 'data/official/existing_faults.tif'
    from .audit import SAMPLE_SHA, LABEL_SHA, WITNESS, get_reference
    if not sample.is_file() or sha256_file(sample) != SAMPLE_SHA or not labels.is_file() or sha256_file(labels) != LABEL_SHA:
        raise ValueError('verified mirrored sample and fault raster are required')
    with rasterio.open(sample) as ds:
        shape, crs, transform = ds.shape, ds.crs, ds.transform
        foot = np.isfinite(ds.read(1))
    with rasterio.open(labels) as ds:
        if ds.shape != shape or ds.crs != crs or ds.transform != transform:
            raise ValueError('fault raster is not aligned to mirrored sample')
        catalogue = (ds.read(1) > 0) & foot
    witness_file = get_reference(WITNESS, ROOT / '.cache/references', 'witness17.tif')
    with rasterio.open(witness_file) as ds:
        if ds.shape != shape or ds.crs != crs or ds.transform != transform:
            raise ValueError('registry witness is not aligned')
        a = ds.read(1)
        witness_near = _near(np.isfinite(a) & (a > 0))
    rows = {}
    masks = {}
    for key, file in files.items():
        with rasterio.open(file) as ds:
            arr = ds.read(1)
            dots = np.isfinite(arr) & (arr > 0)
            same = bool(ds.count == 1 and ds.shape == shape and ds.crs == crs and ds.transform == transform)
            nodata = 'NaN' if isinstance(ds.nodata, float) and math.isnan(ds.nodata) else ds.nodata
            row = {'path_at_pinned_commit': ARTIFACTS[key][0], 'sha256': sha256_file(file),
                   'shape': list(ds.shape), 'crs': str(ds.crs), 'bands': ds.count, 'dtype': ds.dtypes[0],
                   'nodata': nodata, 'matches_mirrored_sample_grid': same,
                   'finite_cells': int(np.isfinite(arr).sum()), 'nan_cells': int(np.isnan(arr).sum()),
                   'infinite_cells': int(np.isinf(arr).sum()), 'positive_cells': int(dots.sum()),
                   'finite_min': float(arr[np.isfinite(arr)].min()) if np.isfinite(arr).any() else None,
                   'finite_max': float(arr[np.isfinite(arr)].max()) if np.isfinite(arr).any() else None}
            if same:
                masks[key] = dots
                row.update(outside_mirrored_footprint=int((dots & ~foot).sum()),
                           on_mirrored_catalogue_inside_footprint=int((dots & catalogue).sum()),
                           forward_overlap_registered_witness=(float(witness_near[dots].mean()) if dots.any() else None),
                           inside_footprint_overlap_registered_witness=(float(witness_near[dots & foot].mean()) if (dots & foot).any() else None))
        if key != 'parallel_template':
            report = format_report(file, sample, footprint=foot)
            report.pop('path', None)
            row['shared_format_report'] = report
            row['eligible_to_submit'] = False
        rows[key] = row
    rows['step_nan_tag']['same_decoded_positive_mask_as_zeros'] = bool(np.array_equal(masks['step_zeros'], masks['step_nan_tag']))
    return {
        'audit_version': 'wbggems-parallel-artifact-audit-v1',
        'checked_utc': datetime.now(timezone.utc).isoformat(),
        'evidence_class': 'RASTER-ARTIFACT-MEASUREMENT; not a holdout or organizer receipt',
        'source_commit': REF, 'source_repository': f'https://github.com/{REPO}/tree/{REF}',
        'template_provenance': 'Hash-pinned public owner mirror; not authenticated official origin.',
        'registered_witness_sha256': WITNESS['sha256'],
        'mirrored_footprint_cells': int(foot.sum()), 'artifacts': rows,
        'preplacement_surface_replayed': False, 'holdout_replayed': False,
        'conclusion': 'DO NOT SUBMIT: parallel step candidate fails the literal registered-witness overlap and shared footprint check; stand-ins do not match the sample grid.',
        'limitation': 'One witness proves failure, not complete current registry enumeration. Nothing here establishes portal acceptance, scores, or any account\'s upload history.',
    }
