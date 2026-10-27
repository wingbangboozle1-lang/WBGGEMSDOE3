"""Log-linear hidden-fault density fitted to owner-reported leaderboard scores.

    log pi(cell) = b0 + sum_f b_f[level_f(cell)]

Expected official DTI of prediction i (see package docstring for the derivation):

    T_i = sum_cell pi * C_i            (truth-side credit, exact given pi)
    K_i = min(3 * sum_cell pi * P_i, N_i)  (prediction-side kernel mass, line-process approx.)
    G   = sum_cell pi * n_px
    DTI_i = T_i / (0.2 * (T_i + N_i - K_i) + 0.8 * G)

Fitting minimises sum_i (DTI_i - s_i)^2 + lam * ||b_f||^2 (intercept unpenalised)
with an analytic Jacobian.  Nothing here touches hidden labels; the scores are
OWNER-REPORTED public-leaderboard values.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.optimize import least_squares

from . import features as F

ALPHA, BETA = 0.2, 0.8
K_FACTOR = 3.0
PI_MAX_DEFAULT = None  # None -> log link clipped at 1; float -> pi = pi_max * sigmoid(eta)


def link(eta, pi_max=None):
    """Return pi and d pi / d eta for the chosen link."""
    if pi_max is None:
        pi = np.exp(np.clip(eta, -30, 0))
        return pi, pi * (eta < 0)
    sig = 1.0 / (1.0 + np.exp(-np.clip(eta, -40, 40)))
    pi = pi_max * sig
    return pi, pi * (1.0 - sig)


def design_matrix(feature_subset=F.FEATURES) -> tuple[np.ndarray, list[str]]:
    """One-hot (cell x parameter) matrix; column 0 is the intercept."""
    lv = F.decode_cells()
    cols = [np.ones(F.n_cells())]
    names = ["intercept"]
    for f in feature_subset:
        for l in range(F.LEVELS[f]):
            cols.append((lv[f] == l).astype(np.float64))
            names.append(f"{f}={F.LEVEL_NAMES[f][l]}")
    return np.stack(cols, axis=1), names


@dataclass
class Fit:
    beta: np.ndarray
    names: list[str]
    lam: float
    feature_subset: tuple
    cost: float
    success: bool
    pi_max: float | None = None

    def pi(self, M: np.ndarray) -> np.ndarray:
        return link(M @ self.beta, self.pi_max)[0]


def predict(beta, M, C, P, N, n_px, pi_max=None):
    pi = link(M @ beta, pi_max)[0]
    T = C @ pi
    K = np.minimum(K_FACTOR * (P @ pi), N)
    G = float(n_px @ pi)
    D = ALPHA * (T + N - K) + BETA * G
    return T / np.maximum(D, 1e-12), dict(T=T, K=K, G=G, D=D, pi=pi)


def _residuals_and_jac(beta, M, C, P, N, n_px, s, w, lam, pi_max=None):
    pi, dpi = link(M @ beta, pi_max)
    T = C @ pi
    Kraw = K_FACTOR * (P @ pi)
    clip = Kraw > N
    K = np.where(clip, N, Kraw)
    G = float(n_px @ pi)
    D = ALPHA * (T + N - K) + BETA * G
    y = T / D
    Mpi = M * dpi[:, None]                # d pi / d beta
    dT = C @ Mpi                          # (n_obs, n_par)
    dK = np.where(clip[:, None], 0.0, K_FACTOR * (P @ Mpi))
    dG = n_px @ Mpi                       # (n_par,)
    dD = ALPHA * (dT - dK) + BETA * dG[None, :]
    dy = (dT * D[:, None] - T[:, None] * dD) / (D[:, None] ** 2)
    sw = np.sqrt(w)
    r = np.concatenate([sw * (y - s), np.sqrt(lam) * beta[1:]])
    J = np.vstack([sw[:, None] * dy, np.hstack([np.zeros((beta.size - 1, 1)), np.sqrt(lam) * np.eye(beta.size - 1)])])
    return r, J


def fit(C, P, N, n_px, s, M, names, lam=1e-3, w=None, beta0=None, feature_subset=F.FEATURES,
        pi_max=None) -> Fit:
    s = np.asarray(s, float)
    w = np.ones_like(s) if w is None else np.asarray(w, float)
    if beta0 is None:
        beta0 = np.zeros(M.shape[1])
        base = 15000.0 / float(n_px.sum())
        beta0[0] = np.log(base) if pi_max is None else np.log(base / (pi_max - base))
    cache = {}

    def fun(b):
        r, J = _residuals_and_jac(b, M, C, P, N, n_px, s, w, lam, pi_max)
        cache["J"] = J
        return r

    def jac(b):
        return cache["J"] if "J" in cache else _residuals_and_jac(b, M, C, P, N, n_px, s, w, lam, pi_max)[1]

    res = least_squares(fun, beta0, jac=jac, method="trf", x_scale="jac", max_nfev=400)
    return Fit(beta=res.x, names=names, lam=lam, feature_subset=tuple(feature_subset),
               cost=float(res.cost), success=bool(res.success), pi_max=pi_max)


def spearman(a, b) -> float:
    from scipy.stats import spearmanr
    return float(spearmanr(a, b).correlation)
