"""Validation against organizer-reported scores, using an external catalogue proxy.

Why not the public-catalogue holdout
------------------------------------
The scored faults are, by construction, the expert-mapped faults that are NOT in
the public USGS/INGENIOUS catalogue. A holdout built by withholding catalogue
segments is therefore an *anti*-proxy: measured on 11 archived submissions with
organizer-reported scores, the catalogue holdout gives Spearman -0.15 (the best
reported submission, 0.2778, ranks *worst* on it). That protocol is invalid here
and is retained only as a documented negative result.

What is used instead
--------------------
The USGS State Geologic Map Compilation (SGMC, Data Series 1052) maps faults from
state geological maps. Its faults that lie >300 m from every public-catalogue
fault are, by definition, "faults the Quaternary catalogue missed" -- the same
population the organizer's experts annotated. That set is an external catalogue
proxy (it is not the hidden ground truth, and no number derived from it is ever
called a competition score).

Two quantities are measured on it:

  h  = TP_w / mass          kernel-weighted hit rate (credit per unit of mass)
  DTI_proxy = official DTI computed with the proxy as truth

`DTI_proxy` is NOT comparable to the leaderboard, because the proxy is ~7x denser
than the hidden ground truth. The leaderboard-comparable estimate comes from the
exact metric identity

    DTI = TP_w / (0.2*(TP_w + FP_w) + 0.8*|G|)        [official closed form]

with FP_w ~= mass and TP_w = h * mass, and |G| = M fitted from the organizer-
reported scores of the archived submissions. The reported scores are the only
organizer feedback available, and they are used exactly once, to fit one scalar.
"""

from __future__ import annotations

import json

import numpy as np
import rasterio
from scipy import ndimage as ndi

from . import config as C
from . import io as gio
from . import metric as M

def _resolve_sgmc_tif():
    for rel in (
        "data/raw/external/derived_sgmc_faults_100m_u8.tif",
        ".cache/upstream/x24/data/external/derived_sgmc_faults_100m_u8.tif",
    ):
        cand = C.ROOT / rel
        if cand.exists():
            return cand
    return C.ROOT / "data/raw/external/derived_sgmc_faults_100m_u8.tif"


SGMC_TIF = _resolve_sgmc_tif()
SGMC_SOURCE = {
    "dataset": "USGS State Geologic Map Compilation (SGMC), Data Series 1052 (ver. 1.1)",
    "citation": ("Horton, J.D., San Juan, C.A., and Stoeser, D.B., 2017, The State Geologic Map "
                 "Compilation (SGMC) geodatabase of the conterminous United States (ver. 1.1, "
                 "August 2017): U.S. Geological Survey Data Series 1052, 46 p."),
    "doi_report": "https://doi.org/10.3133/ds1052",
    "doi_data": "https://doi.org/10.5066/F7WH2N65",
    "publication": "https://pubs.usgs.gov/publication/ds1052",
    "derived_by": "owner CI (buffedlizard55-lab/GEMSDOE24 data/external/derived_sgmc_faults_100m_u8.tif), "
                  "re-derived here from USGS SGMC fault attributes; not an organizer product",
}

# Organizer-reported scores (owner submission logs; no upload receipts were available).
# These are the ONLY organizer numeric feedback in the project.
REPORTED = [
    ("GEMSDOE32 h33-2-b2 (champion)", 0.2778,
     ".cache/upstream/x32/docs/downloads/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif"),
    ("GEMSDOE25 dotted-h19-5-d2-8", 0.2600,
     ".cache/upstream/x24/docs/downloads/gems24-h25-1-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif"),
    ("GEMSDOE24 dotted-h19-5-d1-5", 0.2477,
     ".cache/upstream/x24/docs/downloads/gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif"),
    ("GEMSDOE19 h19-5 powerlaw", 0.1922,
     ".cache/upstream/x24/inputs/gems19-h19-5-powerlaw-budget-multiline-corroborated-20260930-e27054cf-allfinite.tif"),
    ("GEMSDOE19 h19-4 multiline", 0.1894,
     ".cache/upstream/x24/inputs/gems19-h19-4-multiline-corroborated-openness-thermal-pop-20260930-691e4dfa-allfinite.tif"),
    ("GEMSDOE10 h28 dotted-ridge", 0.1839,
     ".cache/upstream/x24/inputs/calibration/gems10-h28-dotted-ridge-20260928T020256236880Z-6452ae1d00.tif"),
    ("8GEMSDOE Hedge-v2", 0.1563,
     ".cache/upstream/x24/inputs/calibration/8GEMSDOE_Hedge-v2_submission.tif"),
    ("GEMSDOE ens12 adopted", 0.1563,
     ".cache/upstream/x24/inputs/calibration/gemsdoe-ens12-adopted-7f00890a.tif"),
    ("GEMSDOE10 h25 ctx-ridge", 0.1280,
     ".cache/upstream/x24/inputs/calibration/gems10-h25-ctx-ridge-20260927T232947704150Z-6452ae1d00.tif"),
    ("13GEMSDOE lattice s5", 0.0904,
     ".cache/upstream/x24/inputs/calibration/13gems_20261001_r13-lattice-s5_v2_nan-outside.tif"),
    ("GEMSDOE9 placeholder", 0.0107,
     ".cache/upstream/x24/inputs/calibration/gemsdoe9-PLACEHOLDER-2314b599.tif"),
]


def sgmc_only_gt(valid=None) -> np.ndarray:
    """SGMC faults further than 300 m from every public-catalogue fault."""
    valid = gio.read_footprint() if valid is None else valid
    with rasterio.open(SGMC_TIF) as src:
        sgmc = src.read(1) > 0
    cat = gio.read_labels()
    d_cat = ndi.distance_transform_edt(~cat)
    return sgmc & (d_cat > C.RADIUS_PX) & valid


def density_match(gt: np.ndarray, target_px: int = 8400, seed: int = 20261027) -> np.ndarray:
    """Subsample whole connected segments so the proxy matches the hidden-GT density.

    The hidden |G| is unknown; the rigorous lower bound from the archived scores is
    |G| >= 8.4e3 px (see `gt_lower_bound`). Matching that density makes DTI_proxy
    numerically comparable to a leaderboard score instead of ~7x too large.
    """
    lab, n = ndi.label(gt, structure=np.ones((3, 3), bool))
    if n == 0:
        return gt
    idx = np.arange(1, n + 1)
    sizes = ndi.sum(gt, lab, idx).astype(np.int64)
    rng = np.random.default_rng(seed)
    order = rng.permutation(n)
    keep, tot = [], 0
    for i in order:
        if tot >= target_px:
            break
        keep.append(idx[i])
        tot += int(sizes[i])
    return np.isin(lab, keep)


def load_raster(path) -> np.ndarray:
    with rasterio.open(path) as src:
        a = src.read(1).astype(np.float32)
    return np.where(np.isfinite(a), a, 0.0)


def profile(pred: np.ndarray, gt: np.ndarray, valid: np.ndarray) -> dict:
    ev = M.FastDTI(gt, valid=valid)
    r = ev.evaluate(pred)
    return {"dti_proxy": r["dti"], "tp_w": r["tp"], "fp_w": r["fp"], "n_truth": r["n_truth"],
            "mass": r["mass"], "hit_rate": r["tp"] / max(r["mass"], 1e-9),
            "capture": r["tp"] / max(r["n_truth"], 1)}


SGMC_OFF_CATALOGUE_PX: float = 62122.0


def score_from_profile(h: float, mass_: float, n_truth: float, n_proxy: float = SGMC_OFF_CATALOGUE_PX) -> float:
    """Prevalence-calibrated diagnostic proxy (DIAGNOSTIC-ONLY; NOT ORGANIZER-CONFIRMED; NOT HOLDOUT-DTI).

    Fixes IR-21: hit rate ``h = TP_proxy / mass`` measured on ``n_proxy`` off-catalogue SGMC pixels
    must be scaled by ``n_truth / n_proxy`` (i.e. ``TP_target = capture * n_truth``) and bounded
    by ``n_truth`` so the DTI identity ``0 <= TP_w <= |G|`` is never violated.
    """
    if n_truth <= 0.0 or mass_ <= 0.0 or h <= 0.0:
        return 0.0
    capture = min(max((h * mass_) / max(n_proxy, 1.0), 0.0), 1.0)
    tp = capture * n_truth
    fp = max(mass_ - tp, 0.0)
    return float(tp / (C.ALPHA * (tp + fp) + C.BETA * n_truth + C.EPS))


def _fit_m(obs: list[dict], lo: float = 1e3, hi: float = 3e5, n: int = 600) -> float:
    """Grid-search |G| minimising the sum of squared errors against reported scores."""
    if not obs:
        return float("nan")
    best_m, best_err = float("nan"), float("inf")
    reps = np.array([o["reported"] for o in obs])
    for mg in np.geomspace(lo, hi, n):
        preds = np.array([score_from_profile(o["hit_rate"], o["mass"], mg) for o in obs])
        err = float(np.sum((preds - reps) ** 2))
        if err < best_err:
            best_err, best_m = err, float(mg)
    return best_m


def fit_gt_size(obs: list[dict], robust: bool = True) -> dict:
    """Fit the single unknown |G| to organizer-reported scores; report LOO quality.

    `robust=True` uses a trimmed fit: files whose fitted residual exceeds 4x the
    median absolute residual are dropped and |G| is refitted once. Both the full
    and the trimmed fit are reported so the outliers stay visible.
    """
    obs = [dict(o) for o in obs]
    m_all = _fit_m(obs)
    used = obs
    if robust and len(obs) >= 6:
        res = [(abs(score_from_profile(o["hit_rate"], o["mass"], m_all) - o["reported"]), i)
               for i, o in enumerate(obs)]
        med = float(np.median([r for r, _ in res])) + 1e-9
        keep = [i for r, i in res if r <= 4.0 * med] or [i for _, i in res]
        if 4 <= len(keep) < len(obs):
            used = [obs[i] for i in keep]
    m_fit = _fit_m(used)
    for o in obs:
        o["predicted"] = score_from_profile(o["hit_rate"], o["mass"], m_fit)
        o["residual"] = o["predicted"] - o["reported"]
        o["used_in_fit"] = any(o is u for u in used)
    preds = np.array([o["predicted"] for o in obs])
    reps = np.array([o["reported"] for o in obs])
    ss_tot = float(np.sum((reps - reps.mean()) ** 2))
    r2 = float(1.0 - np.sum((preds - reps) ** 2) / ss_tot) if ss_tot > 0 else float("nan")
    loo = []
    for i in range(len(obs)):
        sub = [dict(o) for j, o in enumerate(obs) if j != i and obs[j]["used_in_fit"]]
        if not sub:
            continue
        m_i = _fit_m(sub)
        loo.append((obs[i]["reported"], score_from_profile(obs[i]["hit_rate"], obs[i]["mass"], m_i)))
    loo_err = [a - b for a, b in loo]
    return {
        "M_trimmed": float(m_fit), "M_all_files": float(m_all),
        "n_used": int(sum(1 for o in obs if o["used_in_fit"])), "n_total": len(obs),
        "r2": r2, "spearman": _spearman(reps, preds),
        "residual_rms": float(np.sqrt(np.mean(np.square([o["residual"] for o in obs])))),
        "residual_median_abs": float(np.median(np.abs([o["residual"] for o in obs]))),
        "loo_rms": float(np.sqrt(np.mean(np.square(loo_err)))) if loo_err else float("nan"),
        "loo_spearman": _spearman(np.array([a for a, _ in loo]), np.array([b for _, b in loo])) if loo else float("nan"),
        "observations": obs,
    }


def _spearman(a, b) -> float:
    from scipy.stats import spearmanr
    r = spearmanr(a, b).statistic
    return float(r) if np.isfinite(r) else float("nan")


def build_reported_observations(valid=None, gt=None) -> list[dict]:
    valid = gio.read_footprint() if valid is None else valid
    gt = sgmc_only_gt(valid) if gt is None else gt
    obs = []
    for label, reported, rel in REPORTED:
        p = C.ROOT / rel
        pred = load_raster(p)
        pr = profile(pred, gt, valid)
        obs.append({"label": label, "reported": float(reported), "path": rel,
                    "mass": pr["mass"], "hit_rate": pr["hit_rate"],
                    "dti_proxy": pr["dti_proxy"], "capture": pr["capture"]})
    return obs
