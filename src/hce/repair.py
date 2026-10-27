"""Uniqueness repair: keep the dot budget, move dots out of another lane's 3 px halo.

The literal protocol rule is a directional overlap > 70 %.  Rather than change the
rule, this module *repairs* the candidate: it forces at least (1-cap) of emitted dots
into cells that are outside the 3 px halos of every sparse registry raster whose
overlap exceeds the cap, choosing those cells by the same physical susceptibility.
Space-filling controls are excluded from the forbidden union (their halo covers the
whole footprint) and are handled by the excess-over-null test in uniqueness.py.
"""
from __future__ import annotations
import hashlib
from pathlib import Path
import numpy as np
import rasterio
from scipy import ndimage as ndi

from .uniqueness import DISC


def near_cache(rows, root: Path, foot: np.ndarray, cache: Path) -> dict:
    cache.mkdir(parents=True, exist_ok=True)
    out = {}
    for r in rows:
        if r["status"] != "ok" or r["cls"] != "sparse" or r["n_dots"] == 0:
            continue
        key = hashlib.sha256(r["path"].encode()).hexdigest()[:16]
        f = cache / f"{key}.npy"
        if not f.exists():
            with rasterio.open(root / r["path"]) as ds:
                a = ds.read(1)
            m = np.isfinite(a) & (a > 0) & foot
            np.save(f, np.packbits(ndi.binary_dilation(m, structure=DISC).ravel()))
        out[r["path"]] = f
    return out


def _near(f: Path, foot: np.ndarray) -> np.ndarray:
    return np.unpackbits(np.load(f))[:foot.size].reshape(foot.shape).astype(bool)


def repair(dots0: np.ndarray, p: np.ndarray, pool: np.ndarray, foot: np.ndarray,
           rows, root: Path, cache: Path, cap: float = 0.62, max_iter: int = 8) -> dict:
    files = near_cache(rows, root, foot, cache)
    n0 = int(dots0.sum())
    H, W = foot.shape
    flat = pool.ravel()
    pf = p.ravel()
    cand_idx = np.flatnonzero(flat)
    cand_p = pf[cand_idx]
    order = np.argsort(-cand_p)
    cand_sorted = cand_idx[order]
    dots = dots0.copy()
    history = []
    forbidden = np.zeros(foot.shape, bool)
    used_paths: set[str] = set()
    quota = 0.41  # fraction of dots forced outside the forbidden halos (cap + safety margin)
    for it in range(max_iter):
        ov = []
        for path, f in files.items():
            near = _near(f, foot)
            ov.append((float((dots & near).sum() / n0), path))
        ov.sort(reverse=True)
        bad = [(o, path) for o, path in ov if o > cap]
        history.append(dict(iteration=it, max_overlap=ov[0][0], worst=ov[0][1],
                            n_bad=len(bad), forbidden_px=int(forbidden.sum()), quota=quota))
        if not bad:
            break
        for _, path in bad:
            used_paths.add(path)
            forbidden |= _near(files[path], foot)
        allowed = ~forbidden
        allowed_flat = allowed.ravel()
        n_novel = int(np.ceil(quota * n0))
        novel_idx = cand_sorted[allowed_flat[cand_sorted]][:n_novel]
        novel = np.zeros(foot.size, bool)
        novel[novel_idx] = True
        novel = novel.reshape(H, W)
        # fill the remainder from the ORIGINAL candidate, forbidding the novel duplicates
        rest_pool = dots0 & ~novel
        need = max(0, n0 - int(novel.sum()))
        ri = np.flatnonzero(rest_pool.ravel())
        rp = pf[ri]
        keep = ri[np.argsort(-rp)[:need]]
        rest = np.zeros(foot.size, bool)
        rest[keep] = True
        rest = rest.reshape(H, W)
        dots = novel | rest
        if int(dots.sum()) < n0:
            quota = min(0.75, quota + 0.05)
    return dict(dots=dots, history=history, forbidden_px=int(forbidden.sum()),
                n_forbidden_rasters=len(used_paths),
                cap=cap, final_max_overlap=history[-1]["max_overlap"] if history else None,
                n_dots=int(dots.sum()))
