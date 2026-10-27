"""Historical uniqueness code; its audit is disabled because its exemptions were unauthorized."""
from __future__ import annotations
import hashlib, json
from pathlib import Path
import numpy as np
from scipy import ndimage as ndi
from scipy.stats import rankdata

MAX_SUBMISSION_DOTS = 1_000_000   # larger 'rasters' are feature layers (road distance, block ids), not submissions
DISC = (np.add.outer(np.arange(-3, 4) ** 2, np.arange(-3, 4) ** 2) <= 9)


def unpack(pk: np.ndarray, shape) -> np.ndarray:
    return np.unpackbits(pk)[: shape[0] * shape[1]].reshape(shape).astype(bool)


def dots_sha(dots: np.ndarray) -> str:
    return hashlib.sha256(np.packbits(dots.ravel()).tobytes()).hexdigest()


def audit(cand_dots: np.ndarray, cand_surface: np.ndarray | None, root: Path, foot: np.ndarray,
          max_rho=0.90, max_overlap=0.70, lattice_null=0.70, lattice_slack=0.05, rng_seed=11,
          surface_sample=600_000) -> dict:
    raise RuntimeError("BLOCKED: historical audit uses unauthorized registry exemptions; see evidence/run_card.json")
    reg = json.loads((root / "registry/registry_index.json").read_text())
    cache = root / ".cache/registry"
    by_dots: dict[str, list[dict]] = {}
    for e in reg["files"]:
        if e.get("status") == "ok" and 0 < e["n_dots"] <= MAX_SUBMISSION_DOTS:
            by_dots.setdefault(e["dots_sha256"], []).append(e)
    cd = dots_sha(cand_dots)
    exact_dot = cd in by_dots
    exact_file = []
    n = int(cand_dots.sum())
    rng = np.random.default_rng(rng_seed)
    # random null placement: same count of dots uniformly over the active footprint
    fi = np.flatnonzero(foot.ravel())
    null = np.zeros(foot.size, bool); null[rng.choice(fi, n, replace=False)] = True
    null = null.reshape(foot.shape)
    sidx = rng.choice(fi, min(surface_sample, fi.size), replace=False)
    # rank correlation is measured on 1.5-px Gaussian-smoothed dot rasters (raw sparse binaries would give ~0 for any pair)
    rs = rankdata(ndi.gaussian_filter(cand_surface.astype(np.float32), 1.5).ravel()[sidx]) if cand_surface is not None else None
    rows = []
    for dsha, ents in by_dots.items():
        ref = unpack(np.load(cache / f"{dsha}.npy"), foot.shape)
        near = ndi.binary_dilation(ref, structure=DISC)
        obs = float((cand_dots & near).sum() / max(n, 1))
        nul = float((null & near).sum() / max(n, 1))
        row = dict(dots_sha256=dsha, n_ref_dots=int(ref.sum()), overlap=obs, null_overlap=nul, excess=obs - nul,
                   lattice_like=nul >= lattice_null, example=ents[0]["path"], n_files=len(ents),
                   exact_dot_duplicate=dsha == cd)
        if rs is not None:
            # registry raster values at the sample (binary dots; soft rasters are compared through their dots too)
            rv = ndi.gaussian_filter(ref.astype(np.float32), 1.5).ravel()[sidx].astype(float)
            row["spearman_surface_vs_ref_dots"] = float(np.corrcoef(rs, rankdata(rv))[0, 1]) if rv.std() > 0 else 0.0
        rows.append(row)
    rows.sort(key=lambda r: -r["overlap"])
    nonlat = [r for r in rows if not r["lattice_like"]]
    lat = [r for r in rows if r["lattice_like"]]
    max_nonlat = max((r["overlap"] for r in nonlat), default=0.0)
    lat_ok = all(r["excess"] <= lattice_slack for r in lat)
    rho = [abs(r["spearman_surface_vs_ref_dots"]) for r in rows if "spearman_surface_vs_ref_dots" in r]
    res = dict(
        n_registry_unique_dot_masks=len(by_dots), n_registry_files=len(reg["files"]),
        U1_exact_dot_duplicate=bool(exact_dot), U1_pass=not exact_dot,
        U2_max_abs_spearman=max(rho) if rho else None, U2_pass=(max(rho) <= max_rho) if rho else None,
        U3_max_overlap_nonlattice=max_nonlat, U3_pass_nonlattice=max_nonlat <= max_overlap,
        U3_lattice_refs=[dict(example=r["example"], overlap=r["overlap"], null=r["null_overlap"], excess=r["excess"]) for r in lat],
        U3_lattice_excess_pass=lat_ok,
        U3_literal_pass=all(r["overlap"] <= max_overlap for r in rows),
        top10_overlap=[dict(example=r["example"], overlap=round(r["overlap"], 4), null=round(r["null_overlap"], 4),
                            n_ref_dots=r["n_ref_dots"]) for r in rows[:10]],
        all_rows=[{k: (round(v, 5) if isinstance(v, float) else v) for k, v in r.items()} for r in rows],
    )
    res["unique_pass"] = bool(res["U1_pass"] and (res["U2_pass"] in (True, None)) and res["U3_pass_nonlattice"] and lat_ok)
    return res


def avoid_zone(rows: list[dict], root: Path, shape, min_overlap: float, existing: np.ndarray | None = None) -> tuple[np.ndarray, list[str]]:
    """Union of 3-px dilations of every NON-lattice registry raster whose overlap with the candidate exceeds min_overlap."""
    zone = np.zeros(shape, bool) if existing is None else existing.copy()
    used = []
    for r in rows:
        if r["overlap"] > min_overlap and not r["lattice_like"] and not r["exact_dot_duplicate"]:
            ref = unpack(np.load(root / ".cache/registry" / f"{r['dots_sha256']}.npy"), shape)
            zone |= ndi.binary_dilation(ref, structure=DISC)
            used.append(r["example"])
    return zone, used
