"""Independent session-2 uniqueness audit (surface BEFORE placement, dots AFTER placement).

Reads registry/registry_session2.json and .cache/registry2/<dots_sha256>.npy built by
scripts/session2_registry.py.  Reports BOTH readings of the parallel-run rule:

* LITERAL: 3-px forward overlap of candidate dots into every registered positive support,
  including continuous probability fields and space-filling calibration lattices.  Under the
  registered 17GEMSDOE dense witness this is 100% for any nonempty candidate (IR-01); the result
  is reported, not hidden.
* CONTENT-AWARE (preregistered interpretation, flagged for user ratification): "dots" means a
  discrete sparse emission mask.  Continuous probability fields and lattices whose same-count
  random-placement null already reaches 70% are compared with the rank-correlation test and with
  overlap EXCESS over that null; no exemption is silent.

Thresholds are the user's unchanged |rho| > 0.90 and overlap > 0.70.
"""
from __future__ import annotations
import hashlib, json
from pathlib import Path
import numpy as np
from scipy import ndimage as ndi
from scipy.stats import rankdata

ROOT = Path(__file__).resolve().parents[2]
DISC = (np.add.outer(np.arange(-3, 4) ** 2, np.arange(-3, 4) ** 2) <= 9)


def unpack(pk: np.ndarray, shape) -> np.ndarray:
    return np.unpackbits(pk)[: shape[0] * shape[1]].reshape(shape).astype(bool)


def dots_sha(dots: np.ndarray) -> str:
    return hashlib.sha256(np.packbits(np.asarray(dots, bool).ravel()).tobytes()).hexdigest()


def surface_only_audit(surface: np.ndarray, foot: np.ndarray, max_rho: float = 0.90,
                       rng_seed: int = 11, surface_sample: int = 150_000) -> dict:
    """PRE-PLACEMENT gate: |Spearman| of the candidate density surface vs every registry raster."""
    reg = json.loads((ROOT / "registry" / "registry_session2.json").read_text())
    cache = ROOT / ".cache" / "registry2"
    by_dots: dict[str, list[dict]] = {}
    for e in reg["files"]:
        if (e.get("status") == "ok" and 0 < e["n_dots"]
                and (e["n_dots"] <= 1_000_000 or e.get("comparator_class") == "dense")):
            by_dots.setdefault(e["dots_sha256"], []).append(e)
    rng = np.random.default_rng(rng_seed)
    fi = np.flatnonzero(foot.ravel())
    sidx = rng.choice(fi, min(surface_sample, fi.size), replace=False)
    cs = rankdata(np.asarray(surface, np.float32).ravel()[sidx])
    worst = None
    rows = []
    for dsha, ents in by_dots.items():
        ref = unpack(np.load(cache / f"{dsha}.npy"), foot.shape)
        rv = ndi.gaussian_filter(ref.astype(np.float32), 1.5).ravel()[sidx]
        rho = float(np.corrcoef(cs, rankdata(rv))[0, 1]) if rv.std() > 0 else 0.0
        row = dict(example=ents[0]["path"], cls=ents[0].get("comparator_class", "sparse"),
                   abs_spearman=abs(rho), spearman=rho)
        rows.append(row)
        if worst is None or row["abs_spearman"] > worst["abs_spearman"]:
            worst = row
    rows.sort(key=lambda r: -r["abs_spearman"])
    return dict(n_comparators=len(rows), max_abs_spearman=worst["abs_spearman"] if worst else None,
                worst=worst, passed=bool(worst and worst["abs_spearman"] <= max_rho),
                top5=rows[:5], evidence_class="PRE-PLACEMENT SURFACE CHECK; no dots placed yet")


def audit(cand_dots: np.ndarray, cand_surface: np.ndarray | None, foot: np.ndarray,
          max_rho: float = 0.90, max_overlap: float = 0.70, lattice_null: float = 0.70,
          lattice_slack: float = 0.05, rng_seed: int = 11, surface_sample: int = 150_000) -> dict:
    reg = json.loads((ROOT / "registry" / "registry_session2.json").read_text())
    cache = ROOT / ".cache" / "registry2"
    by_dots: dict[str, list[dict]] = {}
    for e in reg["files"]:
        if (e.get("status") == "ok" and 0 < e["n_dots"]
                and (e["n_dots"] <= 1_000_000 or e.get("comparator_class") == "dense")):
            by_dots.setdefault(e["dots_sha256"], []).append(e)
    cd = dots_sha(cand_dots)
    n = int(np.asarray(cand_dots).sum())
    rng = np.random.default_rng(rng_seed)
    fi = np.flatnonzero(foot.ravel())
    null = np.zeros(foot.size, bool)
    null[rng.choice(fi, n, replace=False)] = True
    null = null.reshape(foot.shape)
    sidx = rng.choice(fi, min(surface_sample, fi.size), replace=False)
    if cand_surface is not None:
        rs = rankdata(np.asarray(cand_surface, np.float32).ravel()[sidx])
    else:
        rs = None
    rows = []
    for dsha, ents in by_dots.items():
        ref = unpack(np.load(cache / f"{dsha}.npy"), foot.shape)
        near = ndi.binary_dilation(ref, structure=DISC)
        obs = float((cand_dots & near).sum() / max(n, 1))
        nul = float((null & near).sum() / max(n, 1))
        cls = ents[0].get("comparator_class", "sparse")
        row = dict(dots_sha256=dsha, comparator_class=cls, n_ref_dots=int(ref.sum()),
                   positive_fraction=ents[0]["positive_fraction_of_footprint"],
                   overlap=obs, null_overlap=nul, excess=obs - nul,
                   lattice_like=bool(nul >= lattice_null or cls == "dense"),
                   example=ents[0]["path"], n_files=len(ents), exact_dot_duplicate=bool(dsha == cd))
        if rs is not None:
            rv = ndi.gaussian_filter(ref.astype(np.float32), 1.5).ravel()[sidx]
            row["spearman_surface"] = float(np.corrcoef(rs, rankdata(rv))[0, 1]) if rv.std() > 0 else 0.0
        del ref, near
        rows.append(row)
    rows.sort(key=lambda r: -r["overlap"])
    strict = [r for r in rows if not r["lattice_like"]]
    lat = [r for r in rows if r["lattice_like"]]
    max_strict = max((r["overlap"] for r in strict), default=0.0)
    rho = [abs(r["spearman_surface"]) for r in rows if "spearman_surface" in r]
    res = dict(
        registry_files=reg["n_files"], registry_unique_dot_masks=len(by_dots),
        n_candidate_dots=n,
        U1_exact_dot_duplicate=bool(cd in by_dots),
        U2_max_abs_spearman=(max(rho) if rho else None),
        U2_pass=(max(rho) <= max_rho) if rho else None,
        U3_max_overlap_nonlattice=max_strict,
        U3_pass_nonlattice=max_strict <= max_overlap,
        U3_lattice_refs=[dict(example=r["example"], cls=r["comparator_class"], overlap=round(r["overlap"], 5),
                              null=round(r["null_overlap"], 5), excess=round(r["excess"], 5),
                              n_ref_dots=r["n_ref_dots"]) for r in lat],
        U3_lattice_excess_pass=all(r["excess"] <= lattice_slack for r in lat),
        literal_pass=all(r["overlap"] <= max_overlap for r in rows),
        literal_witness=dict(example=rows[0]["example"], overlap=rows[0]["overlap"]),
        top10=[dict(example=r["example"], cls=r["comparator_class"], overlap=round(r["overlap"], 5),
                    null=round(r["null_overlap"], 5), excess=round(r["excess"], 5),
                    n_ref_dots=r["n_ref_dots"]) for r in rows[:10]],
        all_rows=rows,
    )
    res["content_aware_pass"] = bool(not res["U1_exact_dot_duplicate"] and res["U2_pass"]
                                     and res["U3_pass_nonlattice"] and res["U3_lattice_excess_pass"])
    return res
