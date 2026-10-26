"""Fold-aware candidate builder: LST density -> Dinkelbach allocation with an H19-5 overlap quota.

Everything that touches the catalogue uses ONLY the `visible` catalogue passed in, so the same function builds
the real candidate (visible = full catalogue) and each hold-out cell's candidate (visible = cell-visible faults).
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
from scipy import ndimage as ndi
from . import alloc as A, uniq

CAT_EDGES = [1.01, 2.01, 3.01, 5.01, 10.01, 20.01, 50.01]
CAT_CODES = np.array([1, 2, 3, 4, 5, 6, 7, 0], np.uint8)
H_EDGES = [0.01, 1.01, 2.01, 3.01, 5.01, 10.01]


def cat_code(d: np.ndarray) -> np.ndarray:
    return CAT_CODES[np.digitize(d, CAT_EDGES, right=True)]


def h_code(d: np.ndarray) -> np.ndarray:
    return np.digitize(d, H_EDGES, right=True).astype(np.uint8)


# Declared BEFORE any hold-out run (docs/research/hypotheses.md, W1'): within-stratum modulation fields.
MOD_FIELDS = ["dist_sgmc_fault", "lidar_upface_max", "lidar_downface_max", "gradmag_det_elev_s6", "log_det_elev_s3",
              "det_elev_slope"]
ON_SHARE_FINAL = 0.62   # share of dots allowed within 3 px of the H19-5 network (lowered from 0.64 by the uniqueness repair loop)
MOD_SHRINK = 0.5      # weight applied to the naive-Bayes log-odds (features are correlated)
MOD_CLIP = 1.5        # |log modulation| clip


def load_model(path: Path) -> dict:
    z = np.load(path, allow_pickle=True)
    names = [str(n) for n in z["fields"]]
    tab = np.zeros(64)
    fidx = {int(i): n for i, n in zip(z["field_idx"], names)}
    for (f, b), l in zip(z["cols"], z["lam"]):
        assert fidx[int(f)] == "NUIS_catxH", "final model must be stratum-only"
        tab[int(b)] = l
    boot = np.asarray(z["lam_boot"])
    return dict(strat_lambda=np.quantile(boot, 0.25, axis=0), strat_lambda_median=np.quantile(boot, 0.5, axis=0),
                lam_boot=boot, lam_point=tab, ridge=float(z["ridge"]), resid_q=z["resid_q"])


def modulation(bins_foot: dict, foot: np.ndarray, vis: np.ndarray, active_dom: np.ndarray) -> np.ndarray:
    """Naive-Bayes log-odds from the VISIBLE catalogue (positives) vs other active pixels, deciles of each field."""
    pos = vis[foot]
    neg = active_dom[foot] & ~pos
    lo = np.zeros(int(foot.sum()), np.float32)
    for f in MOD_FIELDS:
        c = bins_foot[f]
        pc = np.bincount(c[pos], minlength=10)[:10].astype(float) + 1.0
        nc = np.bincount(c[neg], minlength=10)[:10].astype(float) + 1.0
        l = np.log((pc / pc.sum()) / (nc / nc.sum()))
        l[0] = 0.0                       # missing -> neutral
        lo += l[c].astype(np.float32)
    m = np.exp(np.clip(MOD_SHRINK * lo, -MOD_CLIP, MOD_CLIP)).astype(np.float32)
    return m


def density(model: dict, bins_foot: dict, foot: np.ndarray, vis: np.ndarray, h_dist: np.ndarray, use_mod: bool = True):
    """rho(y) = lambda_stratum(cat x H) * m(y)/mean_stratum(m).  Zero outside the footprint and on the visible catalogue."""
    d_cat = ndi.distance_transform_edt(~vis)
    code = (cat_code(d_cat[foot]) * 8 + h_code(h_dist[foot])).astype(np.uint8)
    base = model["strat_lambda"][code].astype(np.float32)
    act = ~vis[foot]
    if use_mod:
        m = modulation(bins_foot, foot, vis, foot & ~vis)
        # normalise within each stratum so that the stratum totals (what the ledger identified) are unchanged
        s_sum = np.bincount(code[act], weights=m[act], minlength=64)
        s_cnt = np.bincount(code[act], minlength=64)
        mean_m = np.where(s_cnt > 0, s_sum / np.maximum(s_cnt, 1), 1.0).astype(np.float32)
        base = base * m / mean_m[code]
    base[~act] = 0.0
    rho = np.zeros(foot.shape, np.float32)
    rho[foot] = base
    return rho, d_cat


def build(model, bins_foot, foot, vis, h_dots, h_dist, region=None, avoid=None, n_cap=60000, on_share=0.66, b_px=2.01,
          mu0=0.25, iters=3, use_mod=True, verbose=False):
    """ON pool (within 3 px of H19-5): positive-gain dots only.  OFF pool: exactly (1-s)/s * n_on best dots
    even if their model gain is negative (the explicit PRICE of the uniqueness quota).
    Returns dict(dots, n, n_on, n_off, expected, expected_without_quota, mu, rho)."""
    rho, d_cat = density(model, bins_foot, foot, vis, h_dist, use_mod)
    sl = region if region is not None else (slice(None), slice(None))
    rho_c = rho[sl]
    cand = (foot & ~vis & (d_cat > b_px))[sl]
    near_h = ndi.binary_dilation(h_dots, structure=uniq.DISC)[sl]
    off_ok = ~near_h if avoid is None else (~near_h & ~avoid[sl])
    mu, out = mu0, None
    for it in range(iters):
        on = A.allocate(rho_c, cand & near_h, mu, n_max=n_cap, verbose=verbose)
        n_on = int(on["dots"].sum())
        n_off_req = int(round((1 - on_share) / on_share * n_on))
        off = A.allocate(rho_c, cand & off_ok, mu, n_max=n_off_req, init_dots=on["dots"], min_gain=-1e6)
        dots = off["dots"]
        e = A.expected_dti(rho_c, dots)
        e0 = A.expected_dti(rho_c, on["dots"])
        out = dict(dots=dots, n=int(dots.sum()), n_on=n_on, n_off=int(dots.sum()) - n_on, expected=e,
                   expected_without_quota=e0, mu=mu)
        if verbose:
            print(f"iter {it}: mu={mu:.4f} model DTI {e['dti']:.4f} (without quota {e0['dti']:.4f}) n={out['n']} on={n_on}", flush=True)
        if abs(e["dti"] - mu) < 5e-4:
            break
        mu = float(e["dti"])
    full = np.zeros(foot.shape, bool)
    full[sl] = out["dots"]
    out["dots"] = full
    out["rho"] = rho
    return out
