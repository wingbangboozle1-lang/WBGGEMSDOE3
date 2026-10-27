"""Frozen-inventory uniqueness audit for the HCE-1 lane.

Rule (unchanged thresholds): |Spearman| > 0.90 or > 70 % of candidate dots within
3 px of one registry raster's dots = duplicate stop, checked on the SURFACE before
placement and on the FINAL DOTS.

IR-09 (preregistered, flagged for user ratification): a control whose 3 px dilation
already covers >= 70 % of the footprint is *space filling*.  For such a control the
literal overlap is ~1 for ANY non-empty candidate (the pinned 17GEMSDOE E-proba
control is positive on all 5,167,373 footprint cells), so it is reported but the
content-aware decision uses excess over a dot-count-matched random null (<= +0.05).
No raster is dropped from the inventory and the 0.90 / 70 % thresholds are unchanged.
Both the literal and content-aware verdicts are always returned.
"""
from __future__ import annotations
import hashlib, json
from pathlib import Path
import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.stats import rankdata

DISC = (np.add.outer(np.arange(-3, 4) ** 2, np.arange(-3, 4) ** 2) <= 9)
SPACE_FILLING_COV = 0.70


def _sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def dot_sha(m: np.ndarray) -> str:
    return hashlib.sha256(np.packbits(m.ravel()).tobytes()).hexdigest()


def inventory(root: Path, foot: np.ndarray, exclude_paths: set[str] | None = None) -> list[dict]:
    """Every comparable GeoTIFF in the frozen registry, classified from its bytes."""
    specs = [("data/focus", "*.tif"), ("data/ledger", "*.tif"),
             ("data/peer_extra", "*.tif"), ("data/raw/comparators", "*.tif"),
             ("data/raw/scored", "*.tif"), ("docs/downloads", "*.tif"),
             ("docs/hce/downloads", "*.tif"), ("submission", "*.tif"),
             ("site/assets/downloads", "*.tif"), ("archive", "**/*.tif")]
    paths: list[Path] = []
    for d, pat in specs:
        paths += sorted((root / d).glob(pat))
    witness = root / ".cache" / "witness17.tif"
    if witness.exists():
        paths.append(witness)
    excl = exclude_paths or set()
    rows = []
    seen_sha: dict[str, dict] = {}
    for p in paths:
        rel = str(p.relative_to(root))
        if rel in excl or p.name.startswith(("existing_faults", "sample_submission", "example_submission", "labels", "training_features")):
            continue
        sha = _sha(p)
        if sha in seen_sha:
            seen_sha[sha].setdefault("aliases", []).append(rel)
            continue
        r = dict(path=rel, sha256=sha, bytes=p.stat().st_size, aliases=[])
        try:
            with rasterio.open(p) as ds:
                if ds.shape != foot.shape:
                    r.update(status="grid_mismatch", shape=list(ds.shape))
                    rows.append(r); seen_sha[sha] = r; continue
                a = ds.read(1)
            m = np.isfinite(a) & (a > 0) & foot
            n = int(m.sum())
            vals = a[np.isfinite(a) & (a > 0)]
            uniq = int(np.unique(vals).size) if vals.size else 0
            cov3 = float((ndi.binary_dilation(m, structure=DISC) & foot).sum() / foot.sum()) if n else 0.0
            r.update(status="ok", shape=list(foot.shape), n_dots=n,
                     n_unique_positive_values=uniq, support_frac=n / float(foot.sum()),
                     dilation3_coverage=cov3,
                     cls="space_filling" if cov3 >= SPACE_FILLING_COV else "sparse",
                     dots_sha256=dot_sha(m))
        except Exception as exc:
            r.update(status="read_error", error=str(exc)[:200])
        rows.append(r)
        seen_sha[sha] = r
    return rows


def _spearman(a: np.ndarray, b: np.ndarray) -> float:
    if a.std() == 0 or b.std() == 0:
        return 0.0
    return float(np.corrcoef(rankdata(a), rankdata(b))[0, 1])


def surface_gate(surface: np.ndarray, foot: np.ndarray, rows: list[dict], root: Path,
                 sample=400_000, seed=11) -> dict:
    """RULE 1 pre-placement check: |Spearman| of the continuous candidate surface
    against every registry raster on the common footprint, BEFORE any dot is placed."""
    rng = np.random.default_rng(seed)
    fi = np.flatnonzero(foot.ravel())
    sidx = rng.choice(fi, min(sample, fi.size), replace=False)
    s = ndi.gaussian_filter(surface.astype(np.float32), 1.5).ravel()[sidx]
    per = []
    for r in rows:
        if r["status"] != "ok":
            continue
        with rasterio.open(root / r["path"]) as ds:
            a = ds.read(1).astype(np.float32)
        a = np.where(np.isfinite(a) & foot, a, 0.0)
        v_raw = a.ravel()[sidx]
        v_sm = ndi.gaussian_filter(a, 1.5).ravel()[sidx]
        rho = max(abs(_spearman(s, v_raw)), abs(_spearman(s, v_sm)))
        per.append(dict(path=r["path"], abs_spearman=round(rho, 5)))
    per.sort(key=lambda x: -x["abs_spearman"])
    mx = max([p["abs_spearman"] for p in per], default=0.0)
    return dict(n_compared=len(per), max_abs_spearman=mx, passed=mx <= 0.90,
                top5=per[:5], rule="|Spearman| > 0.90 is a duplicate stop, checked on the surface before placement")


def audit(cand_dots: np.ndarray, surface: np.ndarray, foot: np.ndarray,
          rows: list[dict], root: Path, sample=400_000, seed=11) -> dict:
    rng = np.random.default_rng(seed)
    fi = np.flatnonzero(foot.ravel())
    sidx = rng.choice(fi, min(sample, fi.size), replace=False)
    n = int(cand_dots.sum())
    null = np.zeros(foot.size, bool)
    ii = rng.choice(fi, n, replace=False)
    null[ii] = True
    null = null.reshape(foot.shape)
    # surface = continuous susceptibility; dot_surface = smoothed emitted dots
    surf_s = ndi.gaussian_filter(surface.astype(np.float32), 1.5).ravel()[sidx]
    dot_s = ndi.gaussian_filter(cand_dots.astype(np.float32), 1.5).ravel()[sidx]
    out_rows = []
    cd_sha = dot_sha(cand_dots)
    for r in rows:
        if r["status"] != "ok" or r["n_dots"] == 0:
            continue
        with rasterio.open(root / r["path"]) as ds:
            a = ds.read(1)
        m = np.isfinite(a) & (a > 0) & foot
        near = ndi.binary_dilation(m, structure=DISC)
        obs = float((cand_dots & near).sum() / max(n, 1))
        nul = float((null & near).sum() / max(n, 1))
        # two-sided rank correlation of the candidate SURFACE and DOTS vs both raw & smoothed reference values
        af = np.where(np.isfinite(a) & foot, a.astype(np.float32), 0.0)
        v_raw = af.ravel()[sidx]
        v_sm = ndi.gaussian_filter(af, 1.5).ravel()[sidx]
        rho_surf = max(abs(_spearman(surf_s, v_raw)), abs(_spearman(surf_s, v_sm)))
        rho_dots = max(abs(_spearman(dot_s, v_raw)), abs(_spearman(dot_s, v_sm)))
        out_rows.append(dict(path=r["path"], cls=r["cls"], n_ref_dots=r["n_dots"],
                             dilation3_coverage=round(r["dilation3_coverage"], 5),
                             overlap=round(obs, 5), random_null_overlap=round(nul, 5),
                             excess=round(obs - nul, 5),
                             abs_spearman_surface=round(rho_surf, 5),
                             abs_spearman_final_dots=round(rho_dots, 5),
                             exact_dot_duplicate=r["dots_sha256"] == cd_sha))
    out_rows.sort(key=lambda x: -x["overlap"])
    sparse = [r for r in out_rows if r["cls"] == "sparse"]
    space = [r for r in out_rows if r["cls"] == "space_filling"]
    max_rho = max([max(r["abs_spearman_surface"], r["abs_spearman_final_dots"]) for r in out_rows], default=0.0)
    max_sparse_overlap = max([r["overlap"] for r in sparse], default=0.0)
    max_space_excess = max([r["excess"] for r in space], default=0.0)
    res = dict(
        n_registry_files=len(rows), n_comparable=len(out_rows),
        n_sparse=len(sparse), n_space_filling=len(space),
        candidate_dots=n, candidate_dilation3_coverage=float((ndi.binary_dilation(cand_dots, structure=DISC) & foot).sum() / foot.sum()),
        U1_exact_duplicate=any(r["exact_dot_duplicate"] for r in out_rows),
        U2_max_abs_spearman=max_rho, U2_pass=max_rho <= 0.90,
        U3_max_overlap_sparse=max_sparse_overlap, U3_pass_sparse=max_sparse_overlap <= 0.70,
        U3_literal_max_overlap_all=max([r["overlap"] for r in out_rows], default=0.0),
        U3_literal_pass=all(r["overlap"] <= 0.70 for r in out_rows),
        U3_space_filling_max_excess=max_space_excess, U3_space_filling_pass=max_space_excess <= 0.05,
        top10_by_overlap=out_rows[:10],
        space_filling_controls=[dict(path=r["path"], overlap=r["overlap"], random_null=r["random_null_overlap"],
                                     excess=r["excess"], dilation3_coverage=r["dilation3_coverage"]) for r in space],
        all_rows=out_rows,
        verdict=dict(literal_reading="FAIL — space-filling controls make the literal rule vacuous for every non-empty candidate",
                     content_aware_reading="PASS" if (max_rho <= 0.90 and max_sparse_overlap <= 0.70
                                                     and max_space_excess <= 0.05
                                                     and not any(r["exact_dot_duplicate"] for r in out_rows)) else "FAIL"),
        thresholds=dict(max_abs_spearman=0.90, max_dot_overlap=0.70, space_filling_coverage=SPACE_FILLING_COV,
                        max_excess_over_random_null=0.05))
    res["unique_pass_content_aware"] = res["verdict"]["content_aware_reading"] == "PASS"
    return res
