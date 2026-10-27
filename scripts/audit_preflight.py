"""Read-only audits. No command spends a weekly slot or promotes a candidate."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'vendor'))
sys.path.insert(0, str(ROOT / 'src'))
from gems_project.format_preflight import raster_report  # noqa: E402
from gems_project.template import COMMIT  # noqa: E402


def template_integrity():
    pin = json.loads((ROOT / 'evidence/template-pin.json').read_text())
    return {f['path']: (ROOT / f['path']).is_file() and
            hashlib.sha256((ROOT / f['path']).read_bytes()).hexdigest() == f['sha256']
            for f in pin['files']}


def preflight():
    # Data restoration belongs to the pinned template cache, not the old
    # imagined data/feature_stack.npy layout. Presence alone is not clearance.
    shared = ROOT / '.cache' / f'57GEMSDOE-{COMMIT}'
    required = {
        'sample_mirror': shared / 'data/official/sample_submission.tif',
        'label_mirror': shared / 'data/official/labels.tif',
        'fault_mirror': shared / 'data/official/existing_faults.tif',
        'feature_mirror': shared / 'data/official/training_features.tif',
    }
    present = {key: path.is_file() for key, path in required.items()}
    cache = shared / '.cache/features'
    bands = sum((cache / f'band-{i:02}.npy').is_file() for i in range(1, 20))
    pins = template_integrity()
    return dict(status='BLOCKED', inputs=present, cached_bands_present=bands,
                template_hashes=pins, approved_for_submission=False,
                note=('Presence does not authenticate a mirror. The literal duplicate '
                      'witness, shared-tool irregularities, holdout and selector remain '
                      'separate blockers; see evidence/run_card.json.'))


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
    selected = (d > 0) & v
    if not selected.any(): return dict(status='INDETERMINATE', reason='no dots', passed=False)
    peer_dots = (b > 0) & v
    overlap = float((distance_transform_edt(~peer_dots)[selected] <= 3).mean()) if peer_dots.any() else 0.0
    # Overlap alone is a stop even if one field is constant and rho undefined.
    if overlap > .70:
        return dict(status='DUPLICATE_STOP', spearman=None,
                    directed_overlap_within_3px=overlap, passed=False,
                    reason='overlap threshold exceeded; rank not evaluated')
    if np.ptp(a[v]) == 0 or np.ptp(b[v]) == 0:
        return dict(status='INDETERMINATE', reason='constant rank field',
                    directed_overlap_within_3px=overlap, passed=False)
    rho = float(spearmanr(a[v], b[v]).statistic)
    if not np.isfinite(rho):
        return dict(status='INDETERMINATE', reason='undefined rank correlation',
                    directed_overlap_within_3px=overlap, passed=False)
    # Protocol says exceeds, so equality alone is not duplicate.
    duplicate = abs(rho) > .90
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
    return 0 if report.get('format_ok', False) else 2

if __name__ == '__main__': raise SystemExit(main())
