#!/usr/bin/env python3
"""E2 — H-XMODEL-GATE: cross-model second opinion for the LBCAL-K candidate.

Preregistered 2026-10-28 (knowledge/preregistration-2026-10-28-lbcalk.md,
rank 2): "promote only a design that BOTH the feature-based LBCAL model and
the location-based tomography model rate above the 0.2778 champion."

This script:
  1. loads the stage-1 probe operators (data/work/probes_f4.npz, built from
     the 118 verified ledger rasters by scripts/build_probe_set.py);
  2. solves the full-sample ledger inversion (script invert_ledger settings);
  3. predicts a DTI ESTIMATE for the shipped 60k design AND for calibration
     comparators (B2 = GEMSDOE32's own raster whose actual owner-reported
     score is 0.2778; the failed E1 design; FCHD; SGCE);
  4. applies the preregistered H-XMODEL-GATE (> 0.2778) and writes
     evidence/lbcal_k/e2_crossmodel.json + evidence/lbcal_k_run_card_e2.json.

Every number here is a LEDGER-INVERSION ESTIMATE built from owner-reported
scores — never a holdout, never an organizer-confirmed score.
"""
from __future__ import annotations

import importlib.util
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

CHAMPION_OWNER = 0.2778
STATED_HIGH = 0.3195
OUT = ROOT / "evidence" / "lbcal_k"


def log(*a):
    print(f"[{time.strftime('%H:%M:%S')}]", *a, flush=True)


def main() -> int:
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    spec = importlib.util.spec_from_file_location("invert_ledger", ROOT / "scripts" / "invert_ledger.py")
    inv = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(inv)

    probes_file = inv.WORK / f"probes_f{inv.FACTOR}.npz"
    if not probes_file.is_file():
        raise SystemExit(f"missing {probes_file} — run scripts/build_probe_set.py first")
    D = inv.load()
    n = len(D["scores"])
    log(f"loaded {n} probes, kA {D['kA'].shape}, blocks {D['block_shape']}")

    # ---- full-sample inversion (same hyper-parameters as invert_ledger main)
    idx = np.arange(n)
    fit = inv.solve(D, idx, lam_smooth=1.0, lam_l1=0.0, n_iter=120,
                    mass0=180_000.0, n_outer=3)
    rho = fit["rho"]
    log(f"inversion mass={fit['mass']:,.0f} history_mae={fit['history'][-1]['mae']:.4f}")

    prior = json.loads((ROOT / "docs" / "data" / "ledger_inversion.json").read_text())

    from gemsw import grid as G
    from gemsw import inversion as INV
    import rasterio
    g = G.load_grid()
    card = json.loads((ROOT / "evidence" / "lbcal_k_run_card.json").read_text())

    comparators = [
        ("LBCAL-K-60k (candidate)", ROOT / card["raster"]["path"], None),
        ("GEMSDOE32 B2 (actual 0.2778)", ROOT / ".cache" / "focus" / "GEMSDOE32.tif", 0.2778),
        ("E1 failed design (0.999 overlap, archived)",
         ROOT / "evidence" / "lbcal_k" / "wbggems3-lbcalk-60k-20261028T165833Z-4f0a58dc-zeros-DO-NOT-SUBMIT.tif", None),
        ("FCHD-NCM 38k (holdout 0.0970)",
         next((ROOT / "submission" / p for p in sorted((ROOT / "submission").glob("wbggems3-fchd-ncm-*.tif"))
               if not p.name.endswith("-nan.tif")), None), None),
        ("SGCE zeros (holdout-era research file)",
         ROOT / "docs" / "downloads" / "wbggems3-sgce-20261027-f52d35d8-zeros.tif", None),
    ]
    results = []
    for label, path, actual in comparators:
        if path is None or not path.is_file():
            results.append(dict(label=label, status="missing"))
            log(f"{label}: MISSING")
            continue
        with rasterio.open(path) as src:
            arr = src.read(1)
        dots = np.isfinite(arr) & (arr > 0.0)
        ps = INV.build_probe_set([dots], [float("nan")], [label], g.foot, g.labels,
                                 factor=inv.FACTOR)
        est, parts = inv.predict(np.ascontiguousarray(ps.kA), np.ascontiguousarray(ps.nblocks),
                                 rho, D["act_count"])
        row = dict(label=label, path=str(path.relative_to(ROOT)), dots=int(dots.sum()),
                   estimate=round(float(est[0]), 5),
                   T=round(float(parts["T"][0]), 1), FP=round(float(parts["FP"][0]), 1),
                   truth_mass=round(float(parts["mass"]), 1),
                   actual_owner_reported=actual)
        results.append(row)
        log(f"{label}: ESTIMATE {est[0]:.5f} (dots {row['dots']:,})")

    mine = next(r for r in results if r["label"].startswith("LBCAL-K"))
    b2 = next((r for r in results if r["label"].startswith("GEMSDOE32")), None)
    gate_pass = bool(mine.get("estimate", 0) > CHAMPION_OWNER)
    calibration = None
    if b2 and b2.get("actual_owner_reported"):
        calibration = round(b2["estimate"] - b2["actual_owner_reported"], 5)

    payload = dict(
        schema="lbcal-k-e2-crossmodel-v1",
        evidence_class="LEDGER-INVERSION ESTIMATE (owner-reported scores, no organizer receipts)",
        utc=datetime.now(timezone.utc).isoformat(),
        instrument="gemsw.inversion v2 tomography, 400 m blocks, exact EDT kernel, "
                   "full-sample solve (lam_smooth=1.0, lam_l1=0, iters=120, mass0=180k, n_outer=3)",
        instrument_quality_site_grouped_cv=prior["site_grouped_cv"],
        instrument_quality_note="CV metrics copied from docs/data/ledger_inversion.json "
                                "(same probe inputs; that run's CV, reported as context)",
        probes_sha256_file=str(probes_file.relative_to(ROOT)),
        n_probes=n,
        results=results,
        b2_calibration_delta=calibration,
        gate=dict(name="H-XMODEL-GATE", rule="tomography ESTIMATE > 0.2778 (prereg rank 2)",
                  value=mine.get("estimate"), passed=gate_pass,
                  lbcalk_e1_estimate=0.4237,
                  both_models_above_champion=bool(gate_pass and 0.4237 > CHAMPION_OWNER)),
        verdict="promote" if gate_pass else "negative",
        disclosures=[
            "Estimate, never a score or receipt (IR-11 applies to holdout; this is a third instrument).",
            "Probes are owner-reported scores from sibling repositories.",
            "B2 calibration row is diagnostic: the model's error on B2 bounds how much "
            "weight this second opinion deserves.",
        ],
        wall_seconds=round(time.time() - t0, 1),
    )
    (OUT / "e2_crossmodel.json").write_text(json.dumps(payload, indent=1, default=float) + "\n")
    card_e2 = dict(
        schema="parallel-run card v1 (owner protocol rule 5)",
        lane="LBCAL-K-E2", version="crossmodel-gate-v1",
        session_branch="arena/08f7423a-wbggemsdoe3",
        utc=datetime.now(timezone.utc).isoformat(),
        hypothesis="H-XMODEL-GATE (prereg 2026-10-28 rank 2): both the feature-LBCAL model "
                   "and the location-tomography model rate the candidate above 0.2778.",
        verdict=payload["verdict"],
        failed_gates=[] if gate_pass else ["H-XMODEL-GATE"],
        gates=[dict(name="H-XMODEL-GATE", passed=gate_pass, detail=payload["gate"])],
        estimate=dict(cross_model_estimate=mine.get("estimate"),
                      b2_calibration_delta=calibration,
                      label="LEDGER-INVERSION ESTIMATE -- NOT a score"),
        holdout=dict(label="HOLDOUT-DTI", note="not re-run in E2; E1 value reported as context"),
        budget=dict(experiments_run=2, experiments_max=3, weekly_slots_used=0,
                    wall_seconds=round(time.time() - t0, 1)),
        artifacts=dict(crossmodel_json="evidence/lbcal_k/e2_crossmodel.json"),
    )
    (ROOT / "evidence" / "lbcal_k_run_card_e2.json").write_text(
        json.dumps(card_e2, indent=1, default=float) + "\n")
    log(f"E2 VERDICT {payload['verdict']}; candidate={mine.get('estimate')} "
        f"B2_calibration={calibration} ({payload['wall_seconds']}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
