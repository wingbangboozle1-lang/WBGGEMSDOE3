"""Ledger-Supervised Tomography (LST) of the hidden-truth density.

Exact identities (same as GEMSDOE32 LLI; derived from the official DTI definition, re-derived here):
  prediction p (masked to the scored domain = footprint minus catalogue), hidden binary truth g with
  per-pixel inclusion probability rho(y):
    E[TP_w] = sum_y rho(y) K_p(y),   K_p(y) = max_x p(x) k(d(x,y))            (exact by linearity)
    E[|G|]  = sum_y rho(y)
    E[M]   ~= (1/3) sum_y rho(y) C_p(y),  C_p(y) = sum_x p(x) k(d(x,y))        (line approximation)
    FP_w = N - M,  FN_w = |G| - TP_w,  DTI = TP / (TP + 0.2 FP + 0.8 FN)
  With rho = sum over columns c of lam_c * 1[y in column c] the observed live score s gives the LINEAR equation
    sum_c lam_c [A_ic (1-0.2 s) + 0.2 s B_ic - 0.8 s S_c] = 0.2 s N_i         (A=sum K, B=sum C/3, S=size)
  Rows are divided by D_i = 0.2 N_i + 0.8 G0 so that the residual is ~ a DTI error.
Every output about an unscored raster is a PROJECTION with the leave-one-out error quoted next to it.
"""
from __future__ import annotations
import numpy as np
from scipy.optimize import nnls
from .metric import kernel

OFFS = [(dy, dx, float(kernel(np.hypot(dy, dx)))) for dy in range(-3, 4) for dx in range(-3, 4)
        if float(kernel(np.hypot(dy, dx))) > 0.0]
G0 = 15000.0   # nominal public-truth mass used ONLY to scale row weights (not a fitted claim)


def credit_maps(p: np.ndarray):
    """Return (K, C) full-grid float32: K = max_x p k, C = sum_x p k (zero-padded shifts)."""
    H, W = p.shape
    K = np.zeros((H, W), np.float32)
    C = np.zeros((H, W), np.float32)
    for dy, dx, k in OFFS:
        ys0, ys1 = max(0, dy), min(H, H + dy)
        xs0, xs1 = max(0, dx), min(W, W + dx)
        src = p[max(0, -dy):min(H, H - dy), max(0, -dx):min(W, W - dx)] * np.float32(k)
        np.maximum(K[ys0:ys1, xs0:xs1], src, out=K[ys0:ys1, xs0:xs1])
        C[ys0:ys1, xs0:xs1] += src
    return K, C


def design_row(p: np.ndarray, active: np.ndarray, bins: dict[str, np.ndarray], nb: int) -> dict:
    """p: float32 full grid already masked to active (0 elsewhere). bins: name -> uint8 codes over active px."""
    K, C = credit_maps(p)
    ka, ca = K[active], C[active]
    names = list(bins)
    A = np.zeros((len(names), nb)); B = np.zeros((len(names), nb))
    for j, n in enumerate(names):
        A[j] = np.bincount(bins[n], weights=ka, minlength=nb)[:nb]
        B[j] = np.bincount(bins[n], weights=ca, minlength=nb)[:nb] / 3.0
    return dict(A=A, B=B, N=float(p.sum()), dots=int((p > 0).sum()))


def sizes(bins: dict[str, np.ndarray], nb: int) -> np.ndarray:
    return np.stack([np.bincount(bins[n], minlength=nb)[:nb] for n in bins]).astype(np.float64)


def build_system(A, B, N, S, s, cols: list[tuple[int, int]], ridge: float):
    """A,B: (n, F, nb); S: (F, nb); cols: list of (field, bin). Returns weighted X, y (with ridge rows)."""
    f = np.array([c[0] for c in cols]); b = np.array([c[1] for c in cols])
    a = A[:, f, b]; bb = B[:, f, b]; sz = S[f, b]
    sc = s[:, None]
    X = a * (1 - 0.2 * sc) + 0.2 * sc * bb - 0.8 * sc * sz[None, :]
    y = 0.2 * s * N
    w = 1.0 / (0.2 * N + 0.8 * G0)
    X = X * w[:, None]; y = y * w
    if ridge > 0:
        # ridge on lam scaled by column "mass" so that the penalty is comparable across columns
        scale = np.sqrt(np.maximum(sz, 1.0)) / np.sqrt(sz.mean() + 1e-9)
        X = np.vstack([X, ridge * np.diag(scale)]); y = np.r_[y, np.zeros(len(cols))]
    return X, y


def fit(A, B, N, S, s, cols, ridge=1e-3):
    X, y = build_system(A, B, N, S, s, cols, ridge)
    lam, _ = nnls(X, y, maxiter=20000)
    return lam


def project(lam, cols, A_i, B_i, N_i, S, G_floor=1.0):
    f = np.array([c[0] for c in cols]); b = np.array([c[1] for c in cols])
    tp = float((lam * A_i[f, b]).sum()); m = float((lam * B_i[f, b]).sum()); g = float((lam * S[f, b]).sum())
    g = max(g, G_floor)
    tp = min(tp, g)
    fp = max(N_i - m, 0.0); fn = g - tp
    return dict(dti=tp / (tp + 0.2 * fp + 0.8 * fn + 1e-12), tp=tp, g=g, fp=fp)


def loo(A, B, N, S, s, cols, ridge, groups=None):
    n = len(s)
    pred = np.zeros(n)
    idx = np.arange(n)
    if groups is None:
        groups = idx
    for g in np.unique(groups):
        te = groups == g
        tr = ~te
        lam = fit(A[tr], B[tr], N[tr], S, s[tr], cols, ridge)
        for i in idx[te]:
            pred[i] = project(lam, cols, A[i], B[i], N[i], S)["dti"]
    return pred
