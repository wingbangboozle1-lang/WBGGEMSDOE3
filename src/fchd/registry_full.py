"""Full-Universe Comparator Registry & Knapsack-Constrained Contrarian Submodular Allocator.

Indexes ALL GeoTIFF comparators across:
  1. Focus-9 repositories (`data/comparators/`, `.cache/sites/`)
  2. 118 live ledger rasters (`data/ledger/`, `data/ledger_rasters/`)
  3. 14 addendum rasters (`data/ledger_addendum/`)
  4. 17 Oct 27 prompt peer rasters (`data/peer_extra/`)
  5. `17GEMSDOE` dense witness (`ab0a0a62...`) & `13GEMSDOE` spacing-5 lattice (`b4570b40...`)
  6. All prior `WBGGEMSDOE3` lane outputs (`submission/`, `docs/`)

Enforces both pre-placement continuous surface uniqueness (`|Spearman rho| <= 0.90`)
and post-placement sparse 3-px dot overlap (`<= 0.70`, plus lattice excess `<= +0.05`)
via matroid/knapsack-constrained lazy-greedy CELF submodular DTI maximization.
"""
from __future__ import annotations

import hashlib
import heapq
import json
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.stats import spearmanr

from src.gemsw.ledger import OFFS as KERNEL_OFFSETS

ROOT = Path(__file__).resolve().parents[2]
CACHE_DIR = ROOT / ".cache" / "fchd_registry"
GRID_SHAPE = (3730, 3292)

DENSE_WITNESS_DOT_HASH = "ab0a0a62eecf066a"
LATTICE_S5_DOT_HASH = "b4570b406efec198"


def _dot_hash16(foot_bool: np.ndarray) -> str:
    return hashlib.sha256(np.packbits(foot_bool).tobytes()).hexdigest()[:16]


def discover_all_comparator_tifs(exclude_Substring: str | None = "wbggems3-fchd") -> list[tuple[str, Path]]:
    """Collect every submission/comparator GeoTIFF on disk, excluding our own new FCHD output if re-run."""
    roots = [
        ("focus_comp", ROOT / "data" / "comparators"),
        ("focus_top", ROOT / "data"),
        ("scored_mirror", ROOT / "data" / "raw" / "scored"),
        ("scored_top", ROOT / "data" / "scored"),
        ("ledger", ROOT / "data" / "ledger"),
        ("ledger_rasters", ROOT / "data" / "ledger_rasters"),
        ("ledger_addendum", ROOT / "data" / "ledger_addendum"),
        ("peer_extra_20261027", ROOT / "data" / "peer_extra"),
        ("witness17", ROOT / ".cache"),
        ("sites_cache", ROOT / ".cache" / "sites"),
        ("wbggems3_sub", ROOT / "submission"),
        ("wbggems3_lbcal", ROOT / "evidence" / "lbcal"),
        ("wbggems3_docs", ROOT / "docs"),
    ]
    skip_names = {
        "training_features.tif", "labels.tif", "existing_faults.tif", "sample_submission.tif",
        "template_grid.tif",
        "topo_10m_derived_100m_u8.tif", "dem10_chi_100m_i16.tif", "dem10_chi_100m_sig_i32.tif",
        "blm_closed_claim_distance_m.tif", "tiger_road_distance_m.tif", "lidar_scarp_features_u8.tif",
        "geodawn_rad_u8.tif", "geodawn_extensions_u8.tif", "derived_sgmc_faults_100m_u8.tif",
    }
    found: list[tuple[str, Path]] = []
    seen_real: set[Path] = set()
    for group, base in roots:
        if not base.exists():
            continue
        if group == "witness17":
            it = [base / "witness17.tif"]
        elif group == "focus_top":
            it = sorted(base.glob("*.tif"))
        else:
            it = sorted(base.rglob("*.tif"))
        for p in it:
            if not p.is_file() or p.name in skip_names:
                continue
            if exclude_Substring and exclude_Substring in p.name:
                continue
            rp = p.resolve()
            if rp in seen_real:
                continue
            seen_real.add(rp)
            found.append((group, p))

    # Also check calibrated mirrors in data/raw/
    raw_dir = ROOT / "data" / "raw"
    if raw_dir.is_dir():
        for p in sorted(raw_dir.glob("*.tif")):
            if p.name in skip_names or (exclude_Substring and exclude_Substring in p.name):
                continue
            rp = p.resolve()
            if rp not in seen_real:
                seen_real.add(rp)
                found.append(("raw_calib", p))
    return found


def build_or_load_full_registry(foot: np.ndarray, force: bool = False) -> dict:
    """Index all unique footprint dot-masks and dilated-3px masks in .cache/fchd_registry/."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    idx_path = CACHE_DIR / "full_registry_index.json"
    d3_pack_path = CACHE_DIR / "nonlattice_d3_packed.npy"
    lat_d3_path = CACHE_DIR / "lattice_d3_packed.npy"
    surf_sample_path = CACHE_DIR / "continuous_surfaces_sample.npz"

    files = discover_all_comparator_tifs()
    file_sig = hashlib.sha256(
        "\n".join(f"{g}:{p.relative_to(ROOT)}:{p.stat().st_size}" for g, p in files).encode()
    ).hexdigest()[:16]

    if not force and idx_path.is_file() and d3_pack_path.is_file() and surf_sample_path.is_file():
        idx = json.loads(idx_path.read_text())
        if idx.get("file_sig") == file_sig:
            return {
                "index": idx,
                "d3_packed": np.load(d3_pack_path, mmap_mode="r"),
                "lat_d3_packed": np.load(lat_d3_path) if lat_d3_path.is_file() else None,
                "surf_samples": dict(np.load(surf_sample_path)),
            }

    n_foot = int(foot.sum())
    n_pack = (n_foot + 7) // 8
    rng = np.random.default_rng(20261027)
    surf_sub_idx = np.sort(rng.choice(n_foot, size=250_000, replace=False))

    dot_groups: dict[str, dict] = {}
    d3_rows: list[np.ndarray] = []
    d3_meta: list[dict] = []
    lat_d3_vec: np.ndarray | None = None
    surf_samples: dict[str, np.ndarray] = {"_sub_idx": surf_sub_idx}

    struct7 = np.ones((7, 7), dtype=bool)
    n_scanned = 0

    for group, p in files:
        try:
            with rasterio.open(p) as ds:
                if ds.count != 1 or ds.shape != GRID_SHAPE:
                    continue
                arr = ds.read(1)
        except Exception:
            continue
        n_scanned += 1
        rel = str(p.relative_to(ROOT))
        fin = np.isfinite(arr)
        pos2d = fin & (arr > 0) & foot
        pos_foot = pos2d[foot]
        n_dots = int(pos_foot.sum())
        if n_dots == 0:
            continue

        # Record continuous surface sample if > 5 distinct positive values
        pos_vals = arr[pos2d]
        uniq_v = np.unique(np.round(pos_vals[: min(50_000, pos_vals.size)], 5))
        is_continuous = uniq_v.size > 5
        if is_continuous and len(surf_samples) < 80:
            v_foot = np.where(np.isfinite(arr[foot]), arr[foot], 0.0).astype(np.float32)
            key = f"{group}:{p.stem[:48]}"
            surf_samples[key] = v_foot[surf_sub_idx]

        dhash = _dot_hash16(pos_foot)
        if dhash in dot_groups:
            dot_groups[dhash]["files"].append(rel)
            if group not in dot_groups[dhash]["groups"]:
                dot_groups[dhash]["groups"].append(group)
            continue

        d3_2d = ndi.binary_dilation(pos2d, structure=struct7)
        d3_foot = d3_2d[foot]
        cov3 = float(d3_foot.mean())

        # Classify mask kind per IR-01 / IR-09
        if dhash == DENSE_WITNESS_DOT_HASH or n_dots > 2_000_000 or cov3 > 0.999:
            kind = "dense_witness_full_footprint"
        elif dhash == LATTICE_S5_DOT_HASH or cov3 > 0.90:
            kind = "uniform_lattice"
            lat_d3_vec = np.packbits(d3_foot)
        else:
            kind = "sparse_fault_prediction"

        entry = {
            "dot_hash": dhash,
            "kind": kind,
            "dots": n_dots,
            "cov3_footprint": round(cov3, 6),
            "is_continuous": bool(is_continuous),
            "primary_file": rel,
            "groups": [group],
            "files": [rel],
        }
        dot_groups[dhash] = entry
        if kind == "sparse_fault_prediction":
            d3_rows.append(np.packbits(d3_foot))
            d3_meta.append(entry)

    d3_mat = np.stack(d3_rows, axis=0) if d3_rows else np.zeros((0, n_pack), dtype=np.uint8)
    np.save(d3_pack_path, d3_mat)
    if lat_d3_vec is not None:
        np.save(lat_d3_path, lat_d3_vec)
    np.savez(surf_sample_path, **surf_samples)

    idx_doc = {
        "schema": "fchd-full-registry-v1",
        "file_sig": file_sig,
        "files_scanned": n_scanned,
        "unique_dot_masks": len(dot_groups),
        "sparse_nonlattice_masks": len(d3_meta),
        "continuous_surfaces_sampled": len(surf_samples) - 1,
        "sparse_entries": d3_meta,
        "all_entries": list(dot_groups.values()),
    }
    idx_path.write_text(json.dumps(idx_doc, indent=2) + "\n")
    return {
        "index": idx_doc,
        "d3_packed": np.load(d3_pack_path, mmap_mode="r"),
        "lat_d3_packed": lat_d3_vec,
        "surf_samples": surf_samples,
    }


def check_surface_correlations(surface_2d: np.ndarray, foot: np.ndarray, reg: dict) -> dict:
    """Gate U2 pre-placement continuous surface Spearman |rho| <= 0.90."""
    surf_foot = np.asarray(surface_2d[foot], dtype=np.float32)
    sub_idx = reg["surf_samples"]["_sub_idx"]
    cand_sub = surf_foot[sub_idx]
    rows = []
    for k, ref_sub in reg["surf_samples"].items():
        if k == "_sub_idx":
            continue
        r, _ = spearmanr(cand_sub, ref_sub)
        rf = 0.0 if not np.isfinite(r) else float(r)
        rows.append({"comparator": k, "spearman": round(rf, 5), "abs_spearman": round(abs(rf), 5)})
    rows.sort(key=lambda d: -d["abs_spearman"])
    worst = rows[0]["abs_spearman"] if rows else 0.0
    return {
        "n_continuous_compared": len(rows),
        "max_abs_spearman": worst,
        "passed_le_0p90": bool(worst <= 0.90),
        "top10": rows[:10],
    }


def audit_dots_against_full_registry(dots_2d: np.ndarray, foot: np.ndarray, reg: dict) -> dict:
    """Audit binary dot mask against EVERY unique comparator in the full registry."""
    dots_foot = dots_2d[foot].astype(bool)
    n_cand = int(dots_foot.sum())
    cand_hash = _dot_hash16(dots_foot)
    n_foot = int(foot.sum())

    exact_dup = any(e["dot_hash"] == cand_hash for e in reg["index"]["all_entries"])

    d3_packed = reg["d3_packed"]
    sparse_entries = reg["index"]["sparse_entries"]
    cand_idx = np.flatnonzero(dots_foot)
    byte_idx = cand_idx >> 3
    bit_mask = (1 << (7 - (cand_idx & 7))).astype(np.uint8)

    overlaps = []
    for i, entry in enumerate(sparse_entries):
        comp_pack = d3_packed[i]
        in_d3 = (comp_pack[byte_idx] & bit_mask) != 0
        ov = float(in_d3.sum()) / max(n_cand, 1)
        overlaps.append({
            "dot_hash": entry["dot_hash"],
            "primary_file": entry["primary_file"],
            "groups": entry["groups"],
            "comparator_dots": entry["dots"],
            "comparator_cov3": entry["cov3_footprint"],
            "overlap_3px": round(ov, 5),
        })
    overlaps.sort(key=lambda d: -d["overlap_3px"])
    max_nonlat = overlaps[0]["overlap_3px"] if overlaps else 0.0

    # Lattice null excess check (IR-09)
    lat_ov = None
    lat_null = None
    lat_excess = None
    if reg["lat_d3_packed"] is not None:
        lp = reg["lat_d3_packed"]
        in_lat = (lp[byte_idx] & bit_mask) != 0
        lat_ov = float(in_lat.sum()) / max(n_cand, 1)
        # Null rate = coverage of lattice d3 across footprint
        lat_full = np.unpackbits(lp)[:n_foot].astype(bool)
        lat_null = float(lat_full.mean())
        lat_excess = lat_ov - lat_null

    # Dense witness literal record (IR-01)
    has_witness = any(e["kind"] == "dense_witness_full_footprint" for e in reg["index"]["all_entries"])

    # Peer-specific summary (Oct 27 newly added peers + Focus-9 + WBGGEMSDOE3 prior lanes)
    peer27_top = [r for r in overlaps if "peer_extra_20261027" in r["groups"]][:10]
    addendum_top = [r for r in overlaps if "ledger_addendum" in r["groups"]][:10]
    wbg_prior_top = [r for r in overlaps if "wbggems3_sub" in r["groups"] or "wbggems3_docs" in r["groups"]][:10]
    focus_top = [r for r in overlaps if "focus_comp" in r["groups"] or "sites_cache" in r["groups"]][:10]

    return {
        "candidate_dots": n_cand,
        "candidate_dot_hash": cand_hash,
        "total_files_indexed": reg["index"]["files_scanned"],
        "unique_masks_compared": reg["index"]["unique_dot_masks"],
        "sparse_masks_compared": len(sparse_entries),
        "U1_exact_duplicate": exact_dup,
        "U3_max_nonlattice_overlap_3px": max_nonlat,
        "U3_nonlattice_pass_le_0p70": bool(max_nonlat <= 0.70),
        "U3_lattice_overlap_3px": round(lat_ov, 6) if lat_ov is not None else None,
        "U3_lattice_null_rate": round(lat_null, 6) if lat_null is not None else None,
        "U3_lattice_excess": round(lat_excess, 6) if lat_excess is not None else None,
        "U3_lattice_excess_pass_le_0p05": bool(lat_excess is None or lat_excess <= 0.05),
        "dense_witness_present": has_witness,
        "literal_all_files_max_overlap": 1.0 if has_witness else max_nonlat,
        "content_aware_all_gates_pass": bool(
            (not exact_dup) and (max_nonlat <= 0.70) and (lat_excess is None or lat_excess <= 0.05)
        ),
        "top15_nonlattice": overlaps[:15],
        "top_focus_sites": focus_top,
        "top_peer_prompt_20261027": peer27_top,
        "top_ledger_addendum": addendum_top,
        "top_wbggems3_prior_lanes": wbg_prior_top,
    }


def _compute_gain_map(p: np.ndarray, cov: np.ndarray) -> np.ndarray:
    H, W = p.shape
    g = np.zeros((H, W), dtype=np.float32)
    for dy, dx, kw in KERNEL_OFFSETS:
        r0, r1 = max(0, -dy), min(H, H - dy)
        c0, c1 = max(0, -dx), min(W, W - dx)
        rem = np.maximum(np.float32(kw) - cov[r0 + dy : r1 + dy, c0 + dx : c1 + dx], 0.0)
        g[r0:r1, c0:c1] += p[r0 + dy : r1 + dy, c0 + dx : c1 + dx] * rem
    return g


def _update_cov_map(cov: np.ndarray, ys: np.ndarray, xs: np.ndarray) -> None:
    H, W = cov.shape
    for dy, dx, kw in KERNEL_OFFSETS:
        ty = ys + dy
        tx = xs + dx
        ok = (ty >= 0) & (ty < H) & (tx >= 0) & (tx < W)
        t = (ty[ok], tx[ok])
        cov[t] = np.maximum(cov[t], np.float32(kw))


def celf_knapsack_allocate(
    prob_2d: np.ndarray,
    eligible_2d: np.ndarray,
    foot: np.ndarray,
    reg: dict,
    budget_k: int,
    max_overlap_cap: float = 0.64,
    batch_per_round: int = 2200,
    max_rounds: int = 80,
) -> tuple[np.ndarray, dict]:
    """Vectorized 7x7-NMS Submodular DTI Allocator with Exact Multi-Comparator Knapsack Cap.

    Dots >= 7 px apart have strictly disjoint 3-px kernels (exact independence), so each NMS
    round extracts independent 7x7 local maxima in C (`scipy.ndimage.maximum_filter`) while
    capping overlap `|(S & dilate3(B_j))| / |S| <= max_overlap_cap` across all sparse
    non-lattice registry comparators in ~2-4 seconds total.
    """
    H, W = prob_2d.shape
    dots = np.zeros((H, W), dtype=bool)
    if budget_k <= 0 or not np.any(eligible_2d):
        return dots, {"selected": 0}

    p = np.where(np.isfinite(prob_2d) & (prob_2d > 0.0), prob_2d, 0.0).astype(np.float32)
    allowed = (eligible_2d & foot).copy()
    cov = np.zeros((H, W), dtype=np.float32)

    # Map (r, c) -> footprint flat index [0 .. n_foot-1]
    n_foot = int(foot.sum())
    foot_idx_grid = np.full((H, W), -1, dtype=np.int32)
    foot_idx_grid[foot] = np.arange(n_foot, dtype=np.int32)
    fy, fx = np.nonzero(foot)

    d3_packed = np.asarray(reg["d3_packed"])
    n_comp = int(d3_packed.shape[0])
    hard_cap_hits = max(1, int(np.floor(max_overlap_cap * budget_k)))
    comp_hits = np.zeros(n_comp, dtype=np.int32)
    comp_masked = np.zeros(n_comp, dtype=bool)

    selected = 0
    sel_y_list: list[np.ndarray] = []
    sel_x_list: list[np.ndarray] = []
    sel_g_list: list[np.ndarray] = []
    blocked_by_knapsack = 0

    # Restrict entire work to bounding box of `allowed` (4x smaller inside quadrant holdout cells!)
    ay0, ax0 = np.nonzero(allowed)
    B_r0 = max(0, int(ay0.min()) - 7)
    B_r1 = min(H, int(ay0.max()) + 8)
    B_c0 = max(0, int(ax0.min()) - 7)
    B_c1 = min(W, int(ax0.max()) + 8)
    Hs, Ws = B_r1 - B_r0, B_c1 - B_c0

    p_s = p[B_r0:B_r1, B_c0:B_c1]
    cov_s = cov[B_r0:B_r1, B_c0:B_c1]
    allow_s = allowed[B_r0:B_r1, B_c0:B_c1]

    # Exact initial gain map computed ONCE on subgrid; subsequent rounds update ONLY the 13x13 dirty neighborhood!
    g_s = _compute_gain_map(p_s, cov_s)
    batch_per_round = max(batch_per_round, 3400)

    def _mask_out_comparator(j: int) -> None:
        if comp_masked[j]:
            return
        comp_masked[j] = True
        in_foot_j = np.unpackbits(d3_packed[j])[:n_foot].astype(bool)
        allowed[fy[in_foot_j], fx[in_foot_j]] = False

    for _rd in range(max_rounds):
        room = budget_k - selected
        if room <= 0 or not allow_s.any():
            break

        g_masked = np.where(allow_s, g_s, np.float32(-1e9))
        loc = ndi.maximum_filter(g_masked, size=7, mode="constant", cval=-1e9)
        cand_sub = (g_masked >= loc) & (g_masked > 1e-9) & allow_s
        if not cand_sub.any():
            break

        ly, lx = np.nonzero(cand_sub)
        gv = g_s[ly, lx]
        order = np.argsort(-gv)
        take = min(order.size, room, batch_per_round)
        order = order[:take]
        ly_sel = ly[order].astype(np.int32)
        lx_sel = lx[order].astype(np.int32)
        ys = ly_sel + B_r0
        xs = lx_sel + B_c0
        gv = gv[order]

        if n_comp > 0:
            fidx = foot_idx_grid[ys, xs]
            b_idx = fidx >> 3
            b_msk = (1 << (7 - (fidx & 7))).astype(np.uint8)
            in_mat = (d3_packed[:, b_idx] & b_msk[None, :]) != 0
            if int(comp_hits.max()) + take < hard_cap_hits:
                comp_hits += in_mat.sum(axis=1, dtype=np.int32)
            else:
                keep = np.zeros(take, dtype=bool)
                sat_now = comp_hits >= hard_cap_hits
                for k_i in range(take):
                    col = in_mat[:, k_i]
                    if np.any(col & sat_now):
                        blocked_by_knapsack += 1
                        continue
                    keep[k_i] = True
                    comp_hits += col
                    newly = (comp_hits >= hard_cap_hits) & (~sat_now)
                    if newly.any():
                        sat_now |= newly
                        for j_sat in np.flatnonzero(newly):
                            _mask_out_comparator(int(j_sat))
                ys, xs, gv = ys[keep], xs[keep], gv[keep]
                ly_sel, lx_sel = ly_sel[keep], lx_sel[keep]

            for j_sat in np.flatnonzero((comp_hits >= hard_cap_hits) & (~comp_masked)):
                _mask_out_comparator(int(j_sat))

        if ys.size == 0:
            continue

        dots[ys, xs] = True
        allowed[ys, xs] = False
        _update_cov_map(cov_s, ly_sel, lx_sel)
        selected += int(ys.size)
        sel_y_list.append(ys)
        sel_x_list.append(xs)
        sel_g_list.append(gv)

        if selected >= budget_k:
            break

        # Exact incremental gain update strictly on pixels within 6 px (Chebyshev) of newly placed dots
        # Separable O(1)/px maximum_filter(size=13) is 80x faster than non-separable 13x13 binary_dilation!
        round_mask = np.zeros((Hs, Ws), dtype=np.uint8)
        round_mask[ly_sel, lx_sel] = 1
        dirty = (ndi.maximum_filter(round_mask, size=13) > 0) & allow_s
        uy, ux = np.nonzero(dirty)
        if uy.size > 0:
            ng = np.zeros(uy.size, dtype=np.float32)
            for dy, dx, kw in KERNEL_OFFSETS:
                ty = uy + dy
                tx = ux + dx
                ok = (ty >= 0) & (ty < Hs) & (tx >= 0) & (tx < Ws)
                if ok.all():
                    rem = np.maximum(np.float32(kw) - cov_s[ty, tx], 0.0)
                    ng += p_s[ty, tx] * rem
                else:
                    rem = np.maximum(np.float32(kw) - cov_s[ty[ok], tx[ok]], 0.0)
                    ng[ok] += p_s[ty[ok], tx[ok]] * rem
            g_s[uy, ux] = ng

    # Safety post-guard if `selected < budget_k`: ensure max_overlap <= max_overlap_cap on actual `selected`
    if selected > 0 and selected < budget_k and n_comp > 0:
        all_y = np.concatenate(sel_y_list)
        all_x = np.concatenate(sel_x_list)
        all_g = np.concatenate(sel_g_list)
        actual_cap = max(1, int(np.floor(max_overlap_cap * selected)))
        if int(comp_hits.max()) > actual_cap:
            fidx_all = foot_idx_grid[all_y, all_x]
            b_idx = fidx_all >> 3
            b_msk = (1 << (7 - (fidx_all & 7))).astype(np.uint8)
            in_all = (d3_packed[:, b_idx] & b_msk[None, :]) != 0
            # Drop lowest-gain dots inside offending comparators
            asc = np.argsort(all_g)
            alive = np.ones(all_y.size, dtype=bool)
            cur_n = selected
            for idx_d in asc:
                viol = comp_hits > int(np.floor(max_overlap_cap * cur_n))
                if not viol.any():
                    break
                if np.any(in_all[viol, idx_d]):
                    alive[idx_d] = False
                    dots[all_y[idx_d], all_x[idx_d]] = False
                    comp_hits -= in_all[:, idx_d]
                    cur_n -= 1
            selected = cur_n

    return dots, {
        "selected": selected,
        "budget_k": budget_k,
        "hard_cap_hits": hard_cap_hits,
        "max_empirical_overlap": round(float(comp_hits.max()) / max(selected, 1), 5) if n_comp > 0 and selected > 0 else 0.0,
        "comparators_capped": int(comp_masked.sum()),
        "blocked_by_knapsack": blocked_by_knapsack,
    }
