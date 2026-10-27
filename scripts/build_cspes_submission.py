#!/usr/bin/env python3
"""Build, audit, validate and package the CSPES lane artifact.

Steps (all automatic; no slot is selected and nothing is uploaded):
  1. Rebuild the deterministic CSPES dots and prove byte-equality with the dots
     scored in the holdout (data/work_cspes_dots.npy).
  2. Pre-placement surface gate: |Spearman| of the continuous CSPES surface against
     every registry raster (sparse dot masks and the dense witness's raw probabilities).
  3. Final-dot gate: exact-mask, |Spearman| on 1.5-px smoothed rasters, 3-px overlap
     with random-null and excess-over-null for lattice-like references, plus the
     literal overlap against the space-filling witness.
  4. Package through the PINNED SHARED template writer (all-finite [0,1] policy,
     on-disk re-validation) and independently re-validate with gemsw.writer.
  5. Emit evidence/cspes_run_card.json containing every run-card field.
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from scipy.stats import rankdata

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems_project.template import ensure_template  # noqa: E402
from gemsw import cspes as C, grid as G, uniq, writer as W  # noqa: E402

T0 = time.time()
rng = np.random.default_rng(11)
K = C.DEFAULT_BUDGET


def log(msg: str) -> None:
    print(f"[{time.time() - T0:6.1f}s] {msg}", flush=True)


# ---------------------------------------------------------------- 1. deterministic dots
g = G.load_grid()
bands = C.read_cspes_bands(ROOT / "data/raw/training_features.tif")
fields = C.build_surface(bands, g.foot)
dots = C.place_dots(fields.surface, g.foot, g.labels, budget=K)
packed_holdout = np.load(ROOT / "data/work_cspes_dots.npy")
holdout_dots = np.unpackbits(packed_holdout)[: g.foot.size].reshape(g.foot.shape).astype(bool)
assert np.array_equal(dots, holdout_dots), "packaged dots differ from holdout-scored dots"
assert int((dots & g.labels).sum()) == 0, "dots fall on the mapped catalogue"
assert int((dots & ~g.foot).sum()) == 0, "dots fall outside the footprint"
log(f"deterministic dots rebuilt: {int(dots.sum())}, identical to holdout bytes")

# ---------------------------------------------------------------- 2+3. uniqueness gates
reg = json.loads((ROOT / "registry/cspes_registry_index.json").read_text())
fi = np.flatnonzero(g.foot.ravel())
sidx = rng.choice(fi, 600_000, replace=False)
null = np.zeros(g.foot.size, bool)
null[rng.choice(fi, int(dots.sum()), replace=False)] = True
null = null.reshape(g.foot.shape)

# pre-placement: continuous CSPES surface ranks on the sample
s_surf = rankdata(fields.surface.ravel()[sidx])
# final-dot surface ranks on the same sample (1.5-px Gaussian smoothing, shared convention)
s_dot = rankdata(ndi.gaussian_filter(dots.astype(np.float32), 1.5).ravel()[sidx])

rows = []
witness_rows = []
for e in reg["files"]:
    ref = uniq.unpack(np.load(ROOT / ".cache/registry" / f"{e['dots_sha256']}.npy"), g.foot.shape)
    near = ndi.binary_dilation(ref, structure=uniq.DISC)
    overlap = float((dots & near).sum() / max(int(dots.sum()), 1))
    null_overlap = float((null & near).sum() / max(int(dots.sum()), 1))
    rv_dot = ndi.gaussian_filter(ref.astype(np.float32), 1.5).ravel()[sidx].astype(float)
    rho_dot = float(np.corrcoef(s_dot, rankdata(rv_dot))[0, 1]) if rv_dot.std() > 0 else 0.0
    rho_surf = None
    if e["dense"]:
        # continuous probabilities of the witness itself, not its all-true dot mask
        with rasterio.open(ROOT / e["path"]) as ds:
            wv = ds.read(1).astype(float)
        wfin = np.isfinite(wv.ravel()[sidx])
        rho_surf = float(np.corrcoef(s_surf[wfin], rankdata(wv.ravel()[sidx][wfin]))[0, 1])
        witness_rows.append({"path": e["path"], "n_dots": e["n_dots"],
                             "literal_3px_overlap": overlap,
                             "surface_spearman_vs_witness_proba": rho_surf})
    row = {"source": e["source"], "example": e["path"], "n_ref_dots": e["n_dots"],
           "overlap": round(overlap, 6), "null_overlap": round(null_overlap, 6),
           "excess": round(overlap - null_overlap, 6),
           "lattice_like": null_overlap >= 0.70, "dense": e["dense"],
           "abs_spearman_dots": round(abs(rho_dot), 6),
           "abs_spearman_surface": None if rho_surf is None else round(abs(rho_surf), 6),
           "exact_dot_duplicate": e["dots_sha256"] == uniq.dots_sha(dots)}
    rows.append(row)

rows.sort(key=lambda r: -r["overlap"])
sparse = [r for r in rows if not r["dense"]]
lattice = [r for r in sparse if r["lattice_like"]]
nonlattice = [r for r in sparse if not r["lattice_like"]]
gates = {
    "U1_exact_dot_duplicate_any": any(r["exact_dot_duplicate"] for r in rows),
    "U2_max_abs_spearman_surface": max([r["abs_spearman_surface"] for r in rows if r["abs_spearman_surface"] is not None],
                                       default=max(r["abs_spearman_dots"] for r in rows)),
    "U2_max_abs_spearman_smoothed_dots": max(r["abs_spearman_dots"] for r in rows),
    "U3_max_overlap_nonlattice": max((r["overlap"] for r in nonlattice), default=0.0),
    "U3_lattice_refs": [{"example": r["example"], "overlap": r["overlap"], "excess": r["excess"]} for r in lattice],
    "U3_lattice_excess_pass": all(r["excess"] <= 0.05 for r in lattice),
    "U3_literal_any_raster_max_overlap": max(r["overlap"] for r in rows),
    "top10_overlap": [{k: r[k] for k in ("example", "overlap", "null_overlap", "n_ref_dots")} for r in rows[:10]],
}
gates["U1_pass"] = not gates["U1_exact_dot_duplicate_any"]
gates["U2_pass_0.90"] = gates["U2_max_abs_spearman_surface"] <= 0.90 and gates["U2_max_abs_spearman_smoothed_dots"] <= 0.90
gates["U3_pass_sparse_registry"] = gates["U3_max_overlap_nonlattice"] <= 0.70 and gates["U3_lattice_excess_pass"]
gates["U3_literal_pass_including_dense_witness"] = gates["U3_literal_any_raster_max_overlap"] <= 0.70
log(json.dumps({k: v for k, v in gates.items() if k != "top10_overlap"}, indent=1))

# ---------------------------------------------------------------- 4. shared-template writer
tpl = ensure_template()
sys.path.insert(0, str(tpl / "src"))
from gems57.submission_writer import write_submission  # noqa: E402

tag = uniq.dots_sha(dots)[:8]
name = f"wbggems3-cspes-edgestab-37654d-20261027-{tag}-zeros"
note = ("CSPES grav/RTP edge-stability lane; label-independent; holdout 0.0257<0.0992; "
        "negative, research only, no slot")
assert len(name) <= 140 and len(note) <= 140
pred = dots.astype(np.float32)  # all-finite 0/1 field; zeros outside footprint and on catalogue
out_dir = ROOT / "docs/downloads"
out_dir.mkdir(parents=True, exist_ok=True)
out_tif = out_dir / f"{name}.tif"
if out_tif.exists():
    raise FileExistsError(out_tif)
sample = ROOT / "data/raw/sample_submission.tif"
receipt = write_submission(out_tif, pred, sample, g.foot, note=note, name=name, catalogue=g.labels)
log(f"shared writer committed {out_tif.name}")

# independent re-validation of the saved bytes (gemsw strict validator, zeros convention)
indep = W.validate(out_tif, sample, g.foot, g.labels, mode="zeros")
log("independent validator PASSED" if indep["passed"] else f"independent validator FAILED: {indep}")
with rasterio.open(out_tif) as ds:
    back = ds.read(1)
assert np.array_equal(back > 0, dots), "saved bytes != audited dots"
assert np.isfinite(back).all() and back.min() >= 0.0 and back.max() <= 1.0

# mirror the primary TIF into submission/ for the repo's submission inventory
sub_copy = ROOT / "submission" / out_tif.name
sub_copy.write_bytes(out_tif.read_bytes())

# ---------------------------------------------------------------- 5. run card
holdout = json.loads((ROOT / "evidence/cspes_holdout.json").read_text())
budget = json.loads((ROOT / "evidence/cspes_budget.json").read_text())
canary = json.loads((ROOT / "evidence/cspes_canary.json").read_text())
card = {
    "lane": "CSPES — cross-scale potential-field edge stability",
    "hypothesis": "Scale-persistent, orientation-collinear gravity and RTP magnetic gradient edges, topo-conditioned, mark buried structural boundaries missing from the surface catalogue.",
    "mechanism": "Multi-scale (sigma=2,5 px) gradient persistence P_g*P_m times polarity-invariant grav/mag collinearity (0.5+0.5A) times topographic conditioning (1-0.5T); label-independent ranks; greedy 2-px NMS, K=37,654.",
    "named_non_fault_mimic": "Lithologic contact / volcanic margin / aeromagnetic acquisition stripe.",
    "holdout_dti": {
        "label": "HOLDOUT-DTI",
        "value": holdout["results"]["cspes_full"]["pooled_dti"],
        "evaluator_version": holdout["evaluator_version"],
        "withheld_positives": holdout["n_withheld_positives"],
        "ci95": holdout["results"]["cspes_full"]["ci95_cluster_bootstrap"],
        "matched_incumbent": "champion_proxy_d28_b2",
        "incumbent_holdout_dti": holdout["results"]["champion_proxy_d28_b2"]["pooled_dti"],
        "paired_delta_vs_incumbent": holdout["paired_cspes_minus_champion"],
        "budget_sweep_experiment3": budget["rows"],
        "canary": canary["canary"],
    },
    "correlation_overlap_vs_registry": {
        "registry_scope": f"lane-local rebuild: {reg['n_files_indexed']} files / {reg['n_unique_dot_masks']} unique masks "
                          f"({reg['n_sparse_submission_masks']} sparse submissions + 1 dense witness); committed 522-file index not fully rebuilt",
        "gates": gates,
        "witness_literal": witness_rows,
        "all_rows_file": "registry/cspes_registry_index.json",
    },
    "raster_sha256": receipt["sha256"],
    "validator_output": {
        "shared_template_writer_receipt": {"ok": receipt["template_report"]["ok"],
                                           "problems": receipt["template_report"]["problems"],
                                           "n_nonzero": receipt["template_report"].get("n_nonzero")},
        "independent_gemsw_validate": {"passed": indep["passed"], "checks": indep["checks"],
                                       "emitted_pixels": indep["emitted_pixels"],
                                       "in_footprint_min": indep["in_footprint_min"],
                                       "in_footprint_max": indep["in_footprint_max"],
                                       "full_grid_nan": indep["full_grid_nan"]},
        "readback_equals_audited_dots": True,
        "required": "no NaN inside footprint; values in [0,1]; single float32 band; CRS/shape/transform equal sample",
    },
    "submission_name": name,
    "submission_note": note,
    "submission_note_chars": len(note),
    "files": {"tif": f"docs/downloads/{name}.tif", "zip": f"docs/downloads/{name}.zip",
              "receipt": f"docs/downloads/{name}.json", "submission_copy": f"submission/{name}.tif"},
    "verdict": "negative",
    "verdict_reason": "Paired HOLDOUT-DTI delta vs the matched incumbent is -0.0736 with 95% CI [-0.0883,-0.0587]; CSPES does not beat random placement at any tested budget. The artifact is format-valid and unique against the rebuilt sparse registry but must not be promoted to a weekly slot.",
    "selector_approval": False,
    "slots_spent": 0,
    "experiments_used": 3,
    "run_time_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "elapsed_s": round(time.time() - T0, 1),
}
(ROOT / "evidence/cspes_run_card.json").write_text(json.dumps(card, indent=1, allow_nan=False) + "\n")
log("wrote evidence/cspes_run_card.json")
print(json.dumps(card["correlation_overlap_vs_registry"]["gates"], indent=1))
