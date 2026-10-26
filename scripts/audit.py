"""Read-only audits. No command spends a weekly slot or promotes a candidate."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'vendor'))


def template_integrity():
    pin = json.loads((ROOT / 'evidence/template-pin.json').read_text())
    return {f['path']: (ROOT / f['path']).is_file() and
            hashlib.sha256((ROOT / f['path']).read_bytes()).hexdigest() == f['sha256']
            for f in pin['files']}


def preflight():
    paths = ['data/training_features.tif', 'data/existing_faults.tif',
             'data/sample_submission.tif', 'data/feature_stack.npy',
             'data/segment_folds.json', 'data/registry_manifest.json',
             'data/lane.json']
    present = {p: (ROOT / p).is_file() for p in paths}
    pins = template_integrity()
    return dict(status='BLOCKED' if not all(present.values()) or not all(pins.values()) else 'INPUTS_PRESENT_NOT_VALIDATED',
                inputs=present, template_hashes=pins, approved_for_submission=False,
                note='Presence is not provenance, leakage clearance, uniqueness, holdout improvement or selector authorization.')


def raster_report(candidate, sample):
    import numpy as np
    import rasterio
    problems = []
    with rasterio.open(candidate) as p, rasterio.open(sample) as s:
        if p.count != 1: problems.append('not single band')
        if p.crs is None or p.crs != s.crs: problems.append('CRS mismatch or missing')
        if p.shape != s.shape: problems.append('shape mismatch')
        if p.transform != s.transform: problems.append('transform mismatch')
        if p.nodata is not None: problems.append('nodata must be unset for the all-finite release policy')
        finite = True; in_range = True
        for _, window in p.block_windows(1):
            a = p.read(1, window=window)
            finite &= bool(np.isfinite(a).all())
            in_range &= bool(((a >= 0) & (a <= 1)).all())
        if not finite: problems.append('NaN or infinity present')
        if not in_range: problems.append('values outside [0,1]')
    return dict(format_ok=not problems, problems=problems,
                sha256=hashlib.sha256(Path(candidate).read_bytes()).hexdigest(),
                approved_for_submission=False,
                note='Format only; does not establish uniqueness, score or organizer acceptance.')


def novelty(surface, dots, peer, valid):
    """Exact common-footprint rank correlation and directed within-3px overlap.

    Call for EVERY registry raster both before placement and after emission.
    Missing data and constant fields are indeterminate and fail closed.
    """
    import numpy as np
    from scipy.stats import spearmanr
    from scipy.ndimage import distance_transform_edt
    a, d, b, v = map(np.asarray, (surface, dots, peer, valid))
    if a.ndim != 2 or any(x.shape != a.shape for x in (d, b, v)):
        raise ValueError('matching 2D grids required')
    v = v.astype(bool)
    if not v.any() or not np.isfinite(a[v]).all() or not np.isfinite(b[v]).all():
        raise ValueError('nonempty finite common footprint required')
    if not np.isfinite(d).all() or (d < 0).any() or (d > 1).any():
        raise ValueError('dots must be finite in [0,1]')
    if np.any((d > 0) & ~v): raise ValueError('dots outside footprint')
    if np.ptp(a[v]) == 0 or np.ptp(b[v]) == 0:
        return dict(status='INDETERMINATE', reason='constant rank field', passed=False)
    selected = (d > 0) & v
    if not selected.any(): return dict(status='INDETERMINATE', reason='no dots', passed=False)
    peer_dots = (b > 0) & v
    overlap = float((distance_transform_edt(~peer_dots)[selected] <= 3).mean()) if peer_dots.any() else 0.0
    rho = float(spearmanr(a[v], b[v]).statistic)
    # Protocol says exceeds, so equality alone is not duplicate.
    duplicate = rho > .90 or overlap > .70
    return dict(status='DUPLICATE_STOP' if duplicate else 'PASS_THIS_PEER_ONLY',
                spearman=rho, directed_overlap_within_3px=overlap, passed=not duplicate)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('preflight')
    r = sub.add_parser('raster'); r.add_argument('candidate'); r.add_argument('sample')
    args = parser.parse_args()
    report = preflight() if args.command == 'preflight' else raster_report(args.candidate, args.sample)
    print(json.dumps(report, indent=2, allow_nan=False))
    return 0 if report.get('format_ok', report.get('status') == 'INPUTS_PRESENT_NOT_VALIDATED') else 2

if __name__ == '__main__': raise SystemExit(main())
