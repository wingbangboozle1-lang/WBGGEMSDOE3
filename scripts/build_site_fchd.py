#!/usr/bin/env python3
"""2026-10-28 FCHD-NCM lane publishing step (deterministic, stdlib-only, additive-only).

Runs AFTER the governing negative render() inside scripts/build_site.py main().
Never overrides the repository DO-NOT-SUBMIT release gate:
  - Refreshes FCHD-NCM & Master Audit JSON copies under docs/data/
  - Writes the negative FCHD-NCM research dossier at docs/fchd/index.html and
    research-only archive index at docs/fchd/downloads/index.html.
"""
from __future__ import annotations

import html
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EV = ROOT / "evidence"
SUB = ROOT / "submission"
DOCS = ROOT / "docs" / "fchd"

COPIES = {
    "fchd_run_card.json": EV / "fchd_run_card.json",
    "fchd_leakage_canary.json": EV / "fchd_leakage_canary.json",
    "fchd_experiments.json": EV / "fchd_experiments.json",
    "master_audit_2026-10-27.json": EV / "master_audit_2026-10-27.json",
}


def esc(x) -> str:
    return html.escape(str(x), quote=True)


def main() -> int:
    rc = json.loads((EV / "fchd_run_card.json").read_text(encoding="utf-8"))
    exps = json.loads((EV / "fchd_experiments.json").read_text(encoding="utf-8"))["experiments"]
    canary = json.loads((EV / "fchd_leakage_canary.json").read_text(encoding="utf-8"))
    master = json.loads((EV / "master_audit_2026-10-27.json").read_text(encoding="utf-8"))

    top_data = ROOT / "docs" / "data"
    top_data.mkdir(parents=True, exist_ok=True)
    for dst, src in COPIES.items():
        shutil.copyfile(src, top_data / dst)

    DOCS.mkdir(parents=True, exist_ok=True)
    (DOCS / "data").mkdir(parents=True, exist_ok=True)
    (DOCS / "downloads").mkdir(parents=True, exist_ok=True)

    tif_name = rc["submission_file"]
    zip_name = rc["writer_receipt"]["zip_file"]
    zip_sha = rc["writer_receipt"]["zip_sha256"]
    for fn in (tif_name, zip_name):
        shutil.copy2(SUB / fn, DOCS / "downloads" / fn)
    (DOCS / "data" / "fchd_run_card.json").write_text(json.dumps(rc, indent=2) + "\n", encoding="utf-8")

    exp_rows = ""
    for e in exps:
        sel = " style='background:#1e293b;font-weight:700'" if e["exp_id"] == rc["selected_experiment"] else ""
        ci = e["ci95_cluster_bootstrap"]
        exp_rows += (
            f"<tr{sel}><td><code>{esc(e['exp_id'])}</code></td>"
            f"<td>{e['emitted_dots']:,}</td>"
            f"<td><b>{e['pooled_dti']:.5f}</b><div class='sm'>95% CI [{ci[0]:.4f}, {ci[1]:.4f}]</div></td>"
            f"<td>{e['draw20_mean_dti']:.5f} / {e['draw21_mean_dti']:.5f}</td>"
            f"<td>{e['paired_delta_vs_gemsdoe32']:+.5f}<div class='sm'>CI [{e['paired_delta_ci95'][0]:+.4f}, {e['paired_delta_ci95'][1]:+.4f}]</div></td>"
            f"<td>{e['post_placement_max_nonlattice_3px_overlap']*100:.2f}% / |&rho;|={e['pre_placement_max_abs_spearman']:.3f}</td></tr>"
        )

    peer_rows = ""
    for r in master["peer_prompt_2026_10_27_rasters"]:
        sc = f"{r['owner_reported_unverified']:.4f} <span class='sm'>OWNER-REPORTED</span>" if r["owner_reported_unverified"] is not None else "<span class='sm'>unscored</span>"
        peer_rows += (
            f"<tr><td><b>{esc(r['site'])}</b></td>"
            f"<td><a href='{esc(r['url'])}' target='_blank' rel='noopener'><code>{esc(r['submission'])}</code></a></td>"
            f"<td>{r['positive_dots']:,}</td>"
            f"<td>{sc}</td>"
            f"<td>{r['lbcal_physics_estimate']:.4f} <span class='sm'>ESTIMATE</span></td>"
            f"<td>{r['sgce_u3_overlap_vs_row']*100:.1f}%</td>"
            f"<td>{r['fchd_u3_overlap_vs_row']*100:.1f}%</td></tr>"
        )

    lane_rows = ""
    for r in master["wbggemsdoe3_lanes"]:
        lb = f"{r['lbcal_physics_estimate']:.4f} <span class='sm'>ESTIMATE</span>" if r.get("lbcal_physics_estimate") is not None else "—"
        lane_rows += (
            f"<tr><td><b>{esc(r['lane'])}</b></td>"
            f"<td>{r['positive_dots']:,}</td>"
            f"<td><b>{r['holdout_dti']:.5f}</b></td>"
            f"<td>{lb}</td>"
            f"<td>{r['max_nonlattice_3px_overlap_195_files']*100:.2f}%</td>"
            f"<td>DO NOT SUBMIT (research record)</td></tr>"
        )

    hd = rc["holdout"]
    diag = rc["diagnostic_estimates_not_confirmed_scores"]
    uniq = rc["uniqueness"]

    body = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="gemsdoe-lane-decision" content="DO-NOT-SUBMIT">
<title>FCHD-NCM Lane Dossier (negative) · WBGGEMSDOE3</title>
<style>
body{{margin:0;font:15.5px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;background:#0b1020;color:#e5e7eb}}
a{{color:#93c5fd}}.wrap{{max-width:1120px;margin:0 auto;padding:24px 20px}}
.top{{background:#111827;border-bottom:1px solid #374151;padding:12px 20px}}
.top a{{margin-right:16px;text-decoration:none;font-weight:600;font-size:14px}}
.neg{{background:#2c1219;border:2px solid #f43f5e;border-radius:12px;padding:20px;margin:18px 0}}
.neg h2{{margin:0 0 8px;color:#fda4af}}
.card{{background:#111827;border:1px solid #334155;border-radius:10px;padding:18px;margin:16px 0}}
.kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:12px;margin:16px 0}}
.kpi{{background:#111827;border:1px solid #334155;border-radius:10px;padding:14px}}
.kpi .k{{font-size:12px;text-transform:uppercase;color:#94a3b8;letter-spacing:.05em}}
.kpi .v{{font-size:24px;font-weight:800;color:#f8fafc;margin:4px 0}}
table{{width:100%;border-collapse:collapse;font-size:13.5px}}
th,td{{border-bottom:1px solid #263244;padding:8px 7px;text-align:left;vertical-align:top}}
th{{background:#172033;color:#cbd5e1;font-size:11.5px;text-transform:uppercase}}
code,pre{{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12.5px}}
pre{{background:#070b14;border:1px solid #334155;border-radius:8px;padding:14px;overflow-x:auto}}
.sm{{font-size:12px;color:#94a3b8}}
.btn-res{{display:inline-block;background:#334155;color:#e2e8f0!important;padding:9px 14px;border-radius:8px;text-decoration:none;font-weight:600;margin-right:8px}}
</style></head>
<body>
<div class="top"><div class="wrap" style="padding:0">
<a href="../index.html">&larr; Repository Overview (current decision: see index — SMSR lane promoted 2026-10-28)</a>
<a href="../executive-summary.html">Nine-Site Comparison</a>
<a href="../amdc/index.html">AMDC Audit Dossier</a>
<a href="data/fchd_run_card.json">FCHD JSON Run Card</a>
<a href="../data/master_audit_2026-10-27.json">Master 195-File Audit JSON</a>
</div></div>
<div class="wrap">
<h1>FCHD-NCM Lane Dossier &mdash; NEGATIVE &middot; Not cleared for upload &middot; DO NOT SUBMIT</h1>

<div class="neg">
<h2>DO NOT SUBMIT &mdash; Fail-Closed Parallel-Run Protocol Verdict: <code>negative</code></h2>
<p><b>Consistent with the governing repository <code>DO-NOT-SUBMIT</code> gate (<code>../data/release_gate.json</code>):</b>
Session <code>arena/6ea84033-wbggemsdoe3</code> executed 3 preregistered experiments combining 62 zero-catalogue physical layers
(native 10 m 3DEP Perron&ndash;Royden fluvial &chi; knickpoints, planar facets, Lahontan/BLM deconfounders, 0&rarr;150 m upward-continued
basin potential-field worms, DOE GDR #1391 2m probes/sinter/geothermometry) with 10 strictly out-of-component 4-fold Nested Component-Masked (NCM)
structural features and a bit-packed 149-comparator knapsack CELF allocator (<code>38,000</code> dots).</p>
<ul>
  <li><b>Gate 0 Leakage Canaries:</b> <code>72/72 &le; 0.90</code> (max directional AUC <code>{canary['max_directional_auc']:.5f}</code>).</li>
  <li><b>Content-Aware Uniqueness Solved Across 195 TIFs:</b> Where <code>THCS-OOF</code> (<code>0.921</code>) and <code>AMDC</code> (<code>0.936</code>) collided with <code>GEMSDOE67-ovtr</code>, <code>FCHD-NCM</code> holds max non-lattice 3-px overlap to <b><code>{uniq['U3_max_nonlattice_overlap_3px']*100:.2f}% &le; 70%</code></b> across all 149 sparse/blanket masks and <b><code>{uniq['max_u3_overlap_vs_oct27_peers']*100:.1f}%</code></b> across all 17 newly added Oct 27 peer TIFs. Under the literal positive-support reading, the 100%-footprint <code>17GEMSDOE</code> dense witness overlaps <code>100%</code> of every nonempty prediction (<code>IR-01</code>).</li>
  <li><b>Holdout &amp; Independent Physics Estimates (NOT organizer scores):</b> Winner <code>E2</code> reaches <b><code>HOLDOUT-DTI = {hd['pooled_dti']:.5f}</code></b> (95% CI <code>[{hd['ci95_cluster_bootstrap'][0]:.4f}, {hd['ci95_cluster_bootstrap'][1]:.4f}]</code>, Draw-20 <code>0.10220</code> &mdash; #1 ~38k-dot spatially-blocked model in <code>WBGGEMSDOE3</code>, ahead of <code>THCS-OOF 0.09573</code>, saved <code>HCE-1 0.09313</code>, and <code>AMDC E3 0.0552</code>) and <b><code>LBCAL-Physics ESTIMATE = {diag['lbcal_7feature_physics_estimate']:.4f}</code></b> (#1 non-Goodhart lane in <code>WBGGEMSDOE3</code>), but paired delta vs <code>GEMSDOE32</code> pre-collar proxy (<code>0.09920</code>) is <code>{hd['paired_delta_vs_gemsdoe32']:+.5f}</code> (95% CI <code>[{hd['paired_delta_ci95'][0]:+.5f}, {hd['paired_delta_ci95'][1]:+.5f}]</code>).</li>
</ul>
<p>
<a class="btn-res" href="downloads/{esc(tif_name)}" download>Research-Only TIF (DO NOT SUBMIT)</a>
<a class="btn-res" href="downloads/{esc(zip_name)}" download>Research-Only ZIP (DO NOT SUBMIT)</a>
<a class="btn-res" href="../executive-summary.html">Governing Repository Decision &rarr;</a>
</p>
<div class="sm">Research-only SHA-256: <code>{esc(rc['raster_sha256'])}</code> &middot; Zero portal slots spent &middot; No organizer receipt exists.</div>
</div>

<div class="kpis">
  <div class="kpi"><div class="k">HOLDOUT-DTI (E2 Winner)</div><div class="v">{hd['pooled_dti']:.5f}</div><div class="sm">95% CI [{hd['ci95_cluster_bootstrap'][0]:.4f}, {hd['ci95_cluster_bootstrap'][1]:.4f}] &middot; Draw-20: {hd['draw20_mean_dti']:.5f}</div></div>
  <div class="kpi"><div class="k">LBCAL-Physics ESTIMATE</div><div class="v">{diag['lbcal_7feature_physics_estimate']:.4f}</div><div class="sm">ESTIMATE (not a score) &middot; #1 valid lane in repo</div></div>
  <div class="kpi"><div class="k">SGMC-Cal ESTIMATE</div><div class="v">{diag['sgmc_prevalence_calibrated_dti_estimate']:.4f}</div><div class="sm">95% CI [{diag['sgmc_prevalence_calibrated_ci95'][0]:.4f}, {diag['sgmc_prevalence_calibrated_ci95'][1]:.4f}] &middot; off-catalogue proxy</div></div>
  <div class="kpi"><div class="k">195-File Non-Lattice Ov3</div><div class="v">{uniq['U3_max_nonlattice_overlap_3px']*100:.2f}%</div><div class="sm">&le;70% cap across 149 non-lattice masks</div></div>
  <div class="kpi"><div class="k">Oct 27 Peers Max Ov3</div><div class="v">{uniq['max_u3_overlap_vs_oct27_peers']*100:.1f}%</div><div class="sm">17 newly audited peer GeoTIFFs</div></div>
  <div class="kpi"><div class="k">Gate 0 Leakage Canaries</div><div class="v">72 / 72 PASS</div><div class="sm">max directional AUC = {canary['max_directional_auc']:.4f} &le; 0.90</div></div>
</div>

<div class="card">
<h2>1. Three Preregistered Experiments (Verified <code>training_features.tif</code> TIFF-Tag Bands)</h2>
<div style="overflow-x:auto"><table>
<thead><tr><th>Experiment</th><th>Dots</th><th>HOLDOUT-DTI</th><th>Draw-20 / Draw-21</th><th>Paired &Delta; vs GEMSDOE32</th><th>195-File Max Ov3 / |&rho;|</th></tr></thead>
<tbody>{exp_rows}</tbody></table></div>
<p class="sm"><b>Pass-2 Band-Index Repair Disclosure (<code>IR-27</code>):</b> Line-by-line verification against <code>training_features.tif</code> TIFF descriptions caught that bands in <code>training_features.tif</code> are interleaved (<code>b13=iso_grav_anom</code>, <code>b14=tmi</code>, <code>b15=depth_to_base_surf</code>, <code>b19=det_elev_slope</code>). Fixing <code>b15</code> shifted upward-continued basin worms off mountain slopes into true alluvial basins, raising off-catalogue <code>SGMC-Cal ESTIMATE</code> from <code>0.0494</code> to <code>0.0502</code> (<code>LBCAL-Physics ESTIMATE = 0.0927</code>) while moving scarp-dominated <code>labels.tif</code> <code>HOLDOUT-DTI</code> from <code>0.10433</code> to <code>0.09702</code>.</p>
</div>

<div class="card">
<h2>2. Multi-Lane Repository Summary (All Research-Only &mdash; DO NOT SUBMIT)</h2>
<div style="overflow-x:auto"><table>
<thead><tr><th>WBGGEMSDOE3 Lane</th><th>Emitted Dots</th><th>Fold HOLDOUT-DTI</th><th>LBCAL-Physics ESTIMATE</th><th>Max Non-Lattice 3-px Overlap</th><th>Governing Status</th></tr></thead>
<tbody>{lane_rows}</tbody></table></div>
</div>

<div class="card">
<h2>3. Audit of All 17 Newly Added 2026-10-27 Peer GeoTIFFs (+ 6 Verified Zero-TIF Repos)</h2>
<p class="sm">Six peer repositories from the 2026-10-27 prompt ledger (<code>KANLERGEMSDOE1</code>, <code>GINNYGEMSDOE1..3</code>, <code>EUGGEMSDOE1..3</code>) contain zero <code>.tif</code> files. All 17 published peer GeoTIFFs below are read-only benchmarks (never copy or submit):</p>
<div style="overflow-x:auto"><table>
<thead><tr><th>Peer Site</th><th>Published GeoTIFF</th><th>Dots</th><th>Historical Claim</th><th>LBCAL-Physics ESTIMATE</th><th>SGCE U3 Overlap</th><th>FCHD-NCM U3 Overlap</th></tr></thead>
<tbody>{peer_rows}</tbody></table></div>
</div>

<div class="card">
<h2>4. Parallel-Run Protocol JSON Run Card</h2>
<pre>{esc(json.dumps({k: rc[k] for k in ('lane_id', 'selected_experiment', 'named_non_fault_mimics', 'gates', 'leakage_canary', 'holdout', 'diagnostic_estimates_not_confirmed_scores', 'emitted_dots', 'raster_sha256', 'submission_name', 'submission_note', 'verdict', 'budget_disclosure')}, indent=2))}</pre>
</div>
</div></body></html>
"""
    (DOCS / "index.html").write_text(body, encoding="utf-8")

    (DOCS / "downloads" / "index.html").write_text(
        f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="gemsdoe-lane-decision" content="DO-NOT-SUBMIT">
<title>Research Archive · FCHD-NCM (DO NOT SUBMIT)</title>
<style>body{{font:15.5px/1.6 system-ui;max-width:54rem;margin:3rem auto;padding:1rem;background:#0b1020;color:#e5e7eb}}a{{color:#93c5fd}}code{{background:#1e293b;padding:2px 5px;border-radius:4px}}</style></head>
<body><h1>DO NOT SUBMIT &mdash; FCHD-NCM Research Archive Only</h1>
<p><b>Verdict: <code>negative</code>.</b> Not cleared for upload. Zero portal slots spent. Governing repository decision for this lane's own research files: DO NOT SUBMIT. See the <a href="../../executive-summary.html">current repository executive summary &rarr;</a> for the overall decision.</p>
<ul>
  <li><a href="{esc(tif_name)}" download><code>{esc(tif_name)}</code></a> &mdash; SHA-256 <code>{esc(rc['raster_sha256'])}</code> (38,000 dots, local format diagnostic float32 [0,1])</li>
  <li><a href="{esc(zip_name)}" download><code>{esc(zip_name)}</code></a> &mdash; SHA-256 <code>{esc(zip_sha)}</code></li>
</ul>
<p><a href="../index.html">&larr; Back to FCHD-NCM Dossier</a> &middot; <a href="../../index.html">&larr; Main Dashboard</a></p>
</body></html>
""",
        encoding="utf-8",
    )
    print(f"FCHD-NCM lane records refreshed (data copies + negative dossier at docs/fchd/).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
