"""Independent historical raster forensics, not a holdout evaluator or model."""
import hashlib
import json
from pathlib import Path
import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]


def overlap_bound(footprint_pixels, covered_pixels, dots):
    if not 0 <= covered_pixels <= footprint_pixels or not 0 < dots <= footprint_pixels:
        raise ValueError('Invalid coverage or dot budget')
    uncovered = footprint_pixels - covered_pixels
    forced = max(0, dots - uncovered)
    return {'footprint_pixels': footprint_pixels, 'covered_pixels': covered_pixels,
            'uncovered_pixels': uncovered, 'dots': dots,
            'minimum_overlap': forced / dots,
            'guaranteed_duplicate': forced * 10 > dots * 7}


def inspect(path, template):
    with rasterio.open(template) as t, rasterio.open(path) as r:
        footprint = np.isfinite(t.read(1)) & (t.read_masks(1) > 0)
        if t.count != 1 or t.crs is None or not footprint.any():
            raise ValueError('Invalid template: one band, CRS and nonempty footprint required')
        grid_ok = r.count == 1 and (r.crs, r.shape, r.transform) == (t.crs, t.shape, t.transform)
        if not grid_ok:
            raise ValueError('Grid mismatch')
        a = r.read(1)
        finite = bool(np.isfinite(a[footprint]).all())
        bounded = bool(finite and np.all((a[footprint] >= 0) & (a[footprint] <= 1)))
        finite_values = a[np.isfinite(a)]
        numeric_range = bool(np.all((finite_values >= 0) & (finite_values <= 1)))
        return a, footprint, {'single_band': True, 'crs_shape_transform_match': True,
            'all_finite_values_in_0_1': numeric_range, 'no_inf_anywhere': bool(not np.isinf(a).any()),
            'no_nan_or_inf_inside': finite, 'inside_values_in_0_1': bounded,
            'outside_all_nan': bool(np.isnan(a[~footprint]).all()),
            'whole_grid_finite': bool(np.isfinite(a).all()),
            'crs': str(r.crs), 'shape': list(r.shape), 'transform': list(r.transform),
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def run():
    manifest = json.loads((ROOT / 'research/input_manifest.json').read_text())
    for x in manifest:
        if hashlib.sha256((ROOT / 'data' / x['dest']).read_bytes()).hexdigest() != x['sha256']:
            raise ValueError('Input hash mismatch')
    template = ROOT / 'data/sample_submission.tif'
    masks, rows = {}, {}
    for x in manifest[:9]:
        a, fp, check = inspect(ROOT / 'data' / x['dest'], template)
        if not check['inside_values_in_0_1']:
            raise ValueError('Invalid comparator range')
        if not np.isin(a[fp], [0, 1]).all():
            raise ValueError('Expected binary comparator for exact rank calculation')
        masks[x['id']] = fp & (a > 0)
        rows[x['id']] = {'format': check, 'dots': int(masks[x['id']].sum()), 'comparisons': {}}
    for b, mask_b in masks.items():
        distance = distance_transform_edt(~mask_b)
        nb, n = int(mask_b.sum()), int(fp.sum())
        for a, mask_a in masks.items():
            if a == b:
                continue
            na = int(mask_a.sum()); both = int((mask_a & mask_b).sum())
            # Spearman of two binary arrays equals their phi coefficient, including ties.
            rho = (n * both - na * nb) / np.sqrt(float(na * nb) * (n-na) * (n-nb))
            rows[a]['comparisons'][b] = {'final_binary_spearman': float(rho),
                'within_3px_fraction': float(np.mean(distance[mask_a] <= 3)),
                'same_support': bool(np.array_equal(mask_a, mask_b))}
    for row in rows.values():
        row['max_overlap'] = max(x['within_3px_fraction'] for x in row['comparisons'].values())
        row['unique_among_focus9'] = row['max_overlap'] <= .70 and all(abs(x['final_binary_spearman']) <= .90 for x in row['comparisons'].values())
        row['preplacement_surface_check'] = 'NOT RUN: source surfaces unavailable in this audit'
    lattice = next(x for x in manifest if x['dest'].startswith('scored/'))
    a, fp, _ = inspect(ROOT / 'data' / lattice['dest'], template)
    covered = int((fp & (distance_transform_edt(~(fp & (a > 0))) <= 3)).sum())
    bound = overlap_bound(int(fp.sum()), covered, 37654)
    faults, _, _ = inspect(ROOT / 'data/existing_faults.tif', template)
    distance = distance_transform_edt(~(fp & (faults > 0)))
    d28 = masks['GEMSDOE25']; b2 = masks['GEMSDOE32']
    forensic = {'b2_subset_of_d28': bool(np.all(~b2 | d28)),
                'd28_removed_dots': int((d28 & ~b2).sum()),
                'd28_added_dots': int((~d28 & b2).sum()),
                'equals_d28_euclidean_fault_distance_gt_2px': bool(np.array_equal(b2, d28 & (distance > 2))),
                'd25_d30_same_support': bool(np.array_equal(d28, masks['GEMSDOE30']))}
    result = {'kind': 'RASTER AUDIT — not HOLDOUT-DTI or organizer score',
              'scope': 'Nine pinned historical leaders plus a registered lattice; not the full live registry',
              'rows': rows, 'lattice_bound': bound, 'champion_forensics': forensic}
    (ROOT / 'docs/audit.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps({'lattice_bound': bound, 'champion_forensics': forensic}, indent=2))


if __name__ == '__main__':
    run()
