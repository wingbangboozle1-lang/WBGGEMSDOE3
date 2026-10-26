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


def binary_spearman(mask_a, mask_b, valid_pixels):
    na = int(mask_a.sum())
    nb = int(mask_b.sum())
    both = int((mask_a & mask_b).sum())
    denominator = np.sqrt(float(na * nb * (valid_pixels - na) * (valid_pixels - nb)))
    if denominator == 0:
        return None
    return float((valid_pixels * both - na * nb) / denominator)


def run():
    manifest = json.loads((ROOT / 'research/input_manifest.json').read_text())
    skipped_label_aliases = []
    for x in manifest:
        if x['id'] == 'existing_faults':
            # The pinned owner manifest states this TIFF is byte-identical to
            # labels.tif. Never fetch or use it as an independent catalogue.
            skipped_label_aliases.append(x['id'])
            continue
        if hashlib.sha256((ROOT / 'data' / x['dest']).read_bytes()).hexdigest() != x['sha256']:
            raise ValueError(f"Input hash mismatch: {x['id']}")
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
    lattice_values, fp, _ = inspect(ROOT / 'data' / lattice['dest'], template)
    lattice_mask = fp & (lattice_values > 0)
    distance_to_lattice = distance_transform_edt(~lattice_mask)
    covered = int((fp & (distance_to_lattice <= 3)).sum())
    bound = overlap_bound(int(fp.sum()), covered, 37654)

    candidate_path = ROOT / 'docs/downloads/wb-gems-doe-3-stepover-damagezone-35000d-20261026T215413Z-zeros.tif'
    candidate_values, _, candidate_format = inspect(candidate_path, template)
    candidate_dots = np.isfinite(candidate_values) & (candidate_values > 0.5)
    candidate_in_footprint = candidate_dots & fp
    candidate_outside_footprint = candidate_dots & ~fp
    registry_masks = {**masks, 'registered_r13_lattice_s5': lattice_mask}
    candidate_comparisons = {}
    valid_pixels = int(fp.sum())
    for name, peer_mask in registry_masks.items():
        peer_distance = distance_transform_edt(~peer_mask)
        overlap_all = float((peer_distance[candidate_dots] <= 3).mean()) if candidate_dots.any() else None
        overlap_inside = float((peer_distance[candidate_in_footprint] <= 3).mean()) if candidate_in_footprint.any() else None
        rho = binary_spearman(candidate_in_footprint, peer_mask, valid_pixels)
        candidate_comparisons[name] = {
            'candidate_total_dot_overlap_within_3px': overlap_all,
            'candidate_in_footprint_dot_overlap_within_3px': overlap_inside,
            'final_binary_spearman_on_scored_footprint': rho,
            'same_support_on_scored_footprint': bool(np.array_equal(candidate_in_footprint, peer_mask)),
        }
    candidate_overlaps = [x['candidate_total_dot_overlap_within_3px'] for x in candidate_comparisons.values() if x['candidate_total_dot_overlap_within_3px'] is not None]
    candidate_rhos = [abs(x['final_binary_spearman_on_scored_footprint']) for x in candidate_comparisons.values() if x['final_binary_spearman_on_scored_footprint'] is not None]
    candidate_recheck = {
        'kind': 'FINAL DOTS ONLY — not a surface audit, holdout, or organizer score',
        'source_class': 'Commit-pinned public owner mirrors; not organizer-authenticated or a complete live registry',
        'candidate_sha256': candidate_format['sha256'],
        'sample_sha256': next(x['sha256'] for x in manifest if x['id'] == 'sample_submission'),
        'lattice_sha256': lattice['sha256'],
        'scored_footprint_pixels': valid_pixels,
        'candidate_dots_total': int(candidate_dots.sum()),
        'candidate_dots_inside_scored_footprint': int(candidate_in_footprint.sum()),
        'candidate_positive_pixels_outside_scored_footprint': int(candidate_outside_footprint.sum()),
        'all_dot_overlap_max_within_3px': max(candidate_overlaps) if candidate_overlaps else None,
        'all_dot_overlap_max_raster': max(candidate_comparisons, key=lambda k: candidate_comparisons[k]['candidate_total_dot_overlap_within_3px']),
        'in_footprint_overlap_with_lattice_within_3px': candidate_comparisons['registered_r13_lattice_s5']['candidate_in_footprint_dot_overlap_within_3px'],
        'max_abs_final_binary_spearman': max(candidate_rhos) if candidate_rhos else None,
        'preplacement_surface_spearman': None,
        'preplacement_surface_status': 'NOT RUN: no continuous surface was supplied',
        'format_against_owner_mirror_sample': candidate_format,
        'registry_raster_count': len(candidate_comparisons),
        'registry_comparisons': candidate_comparisons,
    }
    d28 = masks['GEMSDOE25']; b2 = masks['GEMSDOE32']
    forensic = {
        'b2_subset_of_d28': bool(np.all(~b2 | d28)),
        'd28_removed_dots': int((d28 & ~b2).sum()),
        'd28_added_dots': int((~d28 & b2).sum()),
        'd25_d30_same_support': bool(np.array_equal(d28, masks['GEMSDOE30'])),
        'catalogue_distance_pruning_identity': 'NOT EVALUATED: the only pinned owner-mirrored existing_faults.tif is declared byte-identical to labels.tif and was deliberately not fetched or used.'
    }
    result = {'kind': 'RASTER AUDIT — not HOLDOUT-DTI or organizer score',
              'scope': 'Nine pinned historical leaders plus a registered lattice; not the full live registry',
              'input_provenance': 'Commit-pinned owner mirrors; not organizer-authenticated. The sample raster was used only for its finite/nodata footprint mask, not its values.',
              'skipped_label_aliases': skipped_label_aliases,
              'rows': rows, 'lattice_bound': bound, 'candidate_recheck': candidate_recheck,
              'champion_forensics': forensic}
    (ROOT / 'docs/audit.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    print(json.dumps({'lattice_bound': bound, 'candidate_recheck': candidate_recheck,
                      'champion_forensics': forensic,
                      'skipped_label_aliases': skipped_label_aliases}, indent=2))


if __name__ == '__main__':
    run()
