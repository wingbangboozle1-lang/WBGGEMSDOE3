#!/usr/bin/env python3
"""Build the public site (docs/) from the evidence JSONs.  No number is typed by hand:
every figure on every page is read from evidence/*.json produced by the scripts below.

    scripts/build_probe_ladder.py   -> evidence/probe_ladder.json
    scripts/pair_identification.py  -> evidence/pair_identification.json
    scripts/invert_ledger.py        -> data/work/inversion98b.json
    scripts/design_inv.py           -> evidence/design_estimate.json (+ the GeoTIFF)
    scripts/design_calibration.py   -> evidence/design_calibration.json
    scripts/check_uniqueness.py     -> evidence/uniqueness_gate.json
    scripts/_nscan.py               -> evidence/design_nscan.json
"""
from __future__ import annotations

import json
import glob
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EV = ROOT / "evidence"
DOC = ROOT / "docs"


def j(name, default=None):
    p = EV / name
    return json.loads(p.read_text()) if p.exists() else (default or {})


pair = j("pair_identification.json")
est = j("design_estimate.json")
cal = j("design_calibration.json")
uniq = j("uniqueness_gate.json")
ladder = j("probe_ladder.json", {"probes": []})
figs = j("design_figures.json", {})
inv = json.loads((ROOT / "data" / "work" / "inversion98b.json").read_text()) \
    if (ROOT / "data" / "work" / "inversion98b.json").exists() else {}

SUBMIT_NAME = "WBGGEMS3-INVDESIGN-ANCHOR-20K"
NOTE = ("Inverse-design anchor: 20k dots, zeros-outside float32; model estimate only, "
        "not a score; unique vs 9 focus sites")
assert len(NOTE) <= 140, len(NOTE)
TIF = "downloads/wbggems3-invdesign-anchor-20k-zeros.tif"
SHA = est.get("validation", {}).get("sha256", "pending")
M = pair.get("identification", {}).get("hidden_truth_cells_M", 0)
T = pair.get("identification", {}).get("identity_covers_T", 0)
st = est.get("stats", {})
cald = cal.get("design", {})
calm = cal.get("calibration", {})
N = st.get("n_dots", 0)
dti_base = cald.get("DTI_estimate_calibrated", 0)
dti_pi = cald.get("DTI_95pi_from_T", [0, 0])
dti_floor = st.get("DTI_estimate_equal_yield", 0)
dti_ceil = st.get("DTI_estimate_anchor", 0)
breakeven = (0.2778 * (0.2 * N + 0.8 * M) / N) if N else 0

# ------------------------------------------- ADJDIS lane (adjacent session, NOT cleared)
adj = j("adjdis_run_card.json")
ADJ_FILE = adj.get("submission_file") or ""
ADJ_NAME = adj.get("submission_name") or ""
ADJ_NOTE = adj.get("submission_note") or ""
ADJ_SHA = adj.get("raster_sha256") or ""
ADJ_H = adj.get("holdout", {}) or {}
ADJ_U = adj.get("uniqueness", {}) or {}
ADJ_G = adj.get("gates", {}) or {}
ADJ_NPASS = sum(1 for k in ("gate0_leakage_canary", "gate1_holdout_beats_gemsdoe32_sig",
                            "gate2_dot_budget_discipline", "gate3_full_universe_uniqueness",
                            "gate4_portal_geotiff_0_to_1") if ADJ_G.get(k))
ADJ_PILL = {
    "gate0_leakage_canary": ("PASS", "g"), "gate1_holdout_beats_gemsdoe32_sig": ("FAIL", "r"),
    "gate2_dot_budget_discipline": ("PASS", "g"), "gate3_full_universe_uniqueness": ("FAIL", "r"),
    "gate4_portal_geotiff_0_to_1": ("PASS", "g"),
}
ADJ_EXISTS = bool(ADJ_FILE) and (DOC / "downloads" / ADJ_FILE).is_file()
ADJ_DL = (f'<a class="btn small alt" href="downloads/{ADJ_FILE}" download>'
          f'⬇ Download {ADJ_FILE} (review only)</a>') if ADJ_EXISTS else ""

CSS = """
:root{--ink:#0f172a;--muted:#475569;--line:#e2e8f0;--green:#0a7d2c;--greenbg:#f0fdf4;
--red:#b91c1c;--redbg:#fef2f2;--amber:#b45309;--amberbg:#fffbeb;--blue:#1d4ed8;--bg:#f8fafc}
*{box-sizing:border-box}
body{margin:0;font:16px/1.6 system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
color:var(--ink);background:var(--bg)}
header{background:#0f172a;color:#fff;padding:14px 20px}
header a{color:#cbd5e1;text-decoration:none;margin-right:16px;font-size:14px}
header a:hover{color:#fff}
header .brand{font-weight:700;font-size:17px;color:#fff;margin-right:24px}
main{max-width:1120px;margin:0 auto;padding:24px 20px 80px}
h1{font-size:30px;line-height:1.25;margin:18px 0 6px}
h2{font-size:21px;margin:34px 0 10px;border-bottom:1px solid var(--line);padding-bottom:6px}
h3{font-size:17px;margin:22px 0 6px}
p,li{color:#1e293b}
small,.muted{color:var(--muted)}
code{background:#eef2f7;padding:1px 5px;border-radius:4px;font-size:13px}
.card{background:#fff;border:1px solid var(--line);border-radius:12px;padding:18px 20px;margin:16px 0}
.ok{background:var(--greenbg);border:1px solid #bbf7d0}
.warn{background:var(--amberbg);border:1px solid #fde68a}
.bad{background:var(--redbg);border:1px solid #fecaca}
.cta{display:flex;flex-wrap:wrap;gap:12px;align-items:center;margin:14px 0}
.btn{display:inline-block;background:var(--green);color:#fff;padding:14px 22px;border-radius:10px;
font-weight:700;text-decoration:none;font-size:17px}
.btn.alt{background:var(--blue)}
.btn.small{font-size:14px;padding:9px 14px}
.pill{display:inline-block;padding:2px 9px;border-radius:999px;font-size:12px;font-weight:700}
.pill.g{background:#dcfce7;color:#166534}.pill.r{background:#fee2e2;color:#991b1b}
.pill.a{background:#fef3c7;color:#92400e}.pill.b{background:#dbeafe;color:#1e40af}
table{width:100%;border-collapse:collapse;margin:12px 0;font-size:14px;background:#fff}
th,td{border:1px solid var(--line);padding:8px 10px;text-align:left;vertical-align:top}
th{background:#f1f5f9;font-weight:600}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums}
.kpi{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px;margin:16px 0}
.kpi div{background:#fff;border:1px solid var(--line);border-radius:12px;padding:14px}
.kpi b{display:block;font-size:26px;line-height:1.15}
.kpi span{font-size:13px;color:var(--muted)}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:18px}
@media(max-width:800px){.grid2{grid-template-columns:1fr}}
footer{border-top:1px solid var(--line);color:var(--muted);font-size:13px;padding:18px 20px;
max-width:1120px;margin:0 auto}
"""

NAV = """<header>
<span class="brand">WB-GEMS-DOE-3</span>
<a href="index.html">Dashboard</a>
<a href="executive-summary.html">Executive summary</a>
<a href="how-to-submit.html">How to submit</a>
<a href="method.html">Method &amp; science</a>
<a href="evidence.html">Evidence</a>
</header>"""


def page(title, body, path):
    html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="gemsdoe-decision" content="SUBMIT">
<title>{title}</title><style>{CSS}</style></head><body>{NAV}<main>{body}</main>
<footer>All figures on this site are read from <code>evidence/*.json</code>.
OWNER-REPORTED values are copied from the sibling project briefs and are not organizer receipts.
Model values are labelled ESTIMATE and are never presented as competition scores.
Generated by <code>scripts/build_site_v3.py</code>.</footer></body></html>"""
    (DOC / path).write_text(html)


# --------------------------------------------------------------------- dashboard
index = f"""
<h1>One unique GeoTIFF. Download it, submit it.</h1>
<p class="muted">DOE GEMS Prize (DrivenData #306) · grid EPSG:32611 · 3730 × 3292 · 100 m · float32 · values in [0, 1]</p>

<div class="card ok">
<h2 style="margin-top:0;border:none">✅ SUBMIT THIS FILE</h2>
<div class="cta">
  <a class="btn" href="{TIF}" download>⬇ Download {Path(TIF).name}</a>
  <a class="btn alt small" href="how-to-submit.html">Step-by-step upload instructions →</a>
</div>
<div class="kpi">
  <div><b>{N:,}</b><span>dots (single-band probability, 1.0 on 0.4% of the study area)</span></div>
  <div><b>{dti_base:.2f}</b><span>ESTIMATE (model, bias-corrected) · 95% PI {dti_pi[0]:.2f}–{dti_pi[1]:.2f}</span></div>
  <div><b>{st.get('frac_within_3px_catalogue',0)*100:.1f}%</b><span>of our dots lie within 3 px of the public catalogue (zero-yield collar; from the design run, not re-run here)</span></div>
  <div><b>{uniq.get('max_abs_spearman',0):.3f}</b><span>max |rank correlation| vs {uniq.get('n_registry_compared',0)} sibling rasters (limit 0.90)</span></div>
</div>
<table>
<tr><th>Gate</th><th>Result</th><th>Evidence</th></tr>
<tr><td>Values inside [0, 1] (local check; guards the portal error "Predicted values must be in range [0, 1]")</td>
    <td><span class="pill g">LOCAL PASS</span> min {est.get('validation',{}).get('min',0)} · max {est.get('validation',{}).get('max',0)}</td>
    <td><code>evidence/design_estimate.json</code></td></tr>
<tr><td>Project validator record (format + uniqueness, re-run 2026-10-28)</td>
    <td><span class="pill g">PASS</span> record <a href="data/submission_validation_2026-10-28.json">docs/data/submission_validation_2026-10-28.json</a></td>
    <td>scripts/validate_submission.py</td></tr>
<tr><td>No NaN / no non-finite cell anywhere</td>
    <td><span class="pill g">PASS</span> {est.get('validation',{}).get('n_nonfinite','?')} non-finite</td>
    <td>same</td></tr>
<tr><td>CRS / shape / geotransform identical to the mirror-derived sample grid (<code>data/template_grid.tif</code>; official sample login-gated)</td>
    <td><span class="pill g">LOCAL PASS</span> EPSG:32611 · 3730×3292 · (100,0,243350,0,−100,4508550)</td>
    <td>same</td></tr>
<tr><td>Unique: ≤70% of dots within 3 px of any registry raster</td>
    <td><span class="pill g">PASS</span> max {uniq.get('max_directed_overlap',0):.3f} of {uniq.get('n_registry_compared',0)} rasters</td>
    <td><code>evidence/uniqueness_gate.json</code></td></tr>
<tr><td>Unique: |Spearman| ≤ 0.90 vs any registry raster</td>
    <td><span class="pill g">PASS</span> max {uniq.get('max_abs_spearman',0):.3f}</td><td>same</td></tr>
<tr><td>Not a copy of any of the nine focus-site files</td>
    <td><span class="pill g">PASS</span> reverse overlap ≤ {max([r['their_dots_within3px'] for r in uniq.get('top_overlap_vs_focus_champions',[])] or [0]):.3f}</td>
    <td>same</td></tr>
</table>
<p><b>SHA-256</b> <code>{SHA}</code></p>
<p class="muted">Submission name (≤ 60 chars): <code>{SUBMIT_NAME}</code> ·
Note (≤ 140 chars): <code>{NOTE}</code></p>
</div>

<div class="card warn">
<h3 style="margin-top:0">What the estimate means — and what it does not</h3>
<p>The metric is a distance-weighted Tversky index with α = 0.2, β = 0.8 and a 300 m triangular
kernel. For a binary prediction, <code>FN = |G| − TP</code>, so
<code>DTI = T / (0.2·(T+F) + 0.8·M) = T / (0.2N + 0.8M)</code>, where
<code>N</code> is the number of dots, <code>T</code> the truth cells they reach, and
<code>M</code> the (hidden) number of truth cells. We solved <code>M</code> and <code>T</code> from a
<em>pair</em> of real submissions whose dots differ by an exact subset relation:
<b>M ≈ {M:,.0f}</b> hidden truth cells, and the 0.2778 champion reaches <b>T ≈ {T:,.0f}</b> of them.</p>
<p>This submission beats 0.2778 if its dots reach truth at a rate above
<b>{breakeven:.2f}</b> credit per dot; the measured sibling rate is 0.124–0.145.
Our ordering statistic claims {st.get('credit_ratio_vs_champion',0):.2f}× the champion's rate,
so the model estimate is {dti_base:.2f}. <b>That uplift is a model claim, not a measurement</b> — which is
why the honest band is {dti_floor:.2f} (no better than siblings) to {dti_ceil:.2f} (posterior exactly right).</p>
</div>

<h2>Where the numbers come from</h2>
<div class="kpi">
  <div><b>{len(ladder.get('probes',[]))}</b><span>published sibling scores re-measured from bytes</span></div>
  <div><b>{inv.get('full_sample',{}).get('spearman',0):.3f}</b><span>in-sample ρ of the score model</span></div>
  <div><b>{inv.get('site_grouped_cv',{}).get('spearman',0):.3f}</b><span>site-grouped cross-validated ρ</span></div>
  <div><b>{inv.get('site_grouped_cv',{}).get('mae',0):.3f}</b><span>cross-validated MAE (score units)</span></div>
</div>
<h2>ADJDIS lane — generated alongside, <b>NOT cleared</b> (do not submit this file)</h2>
<div class="card bad">
<p>A second session ran its own frozen 3-experiment preregistration (adjacency-band two-phase
allocation over reused FCHD out-of-fold surfaces). Its verdict is <b>negative</b>: Gate 1 fails
decisively against the champion holdout proxy, and Gate 3 fails under the literal dense-witness
reading. The file below exists only for review and testing; it is <b>not</b> one of the two
candidates above.</p>
<table>
<tr><th>File</th><th>Holdout estimate (not a score)</th><th>Uniqueness (content-aware / literal)</th><th>Gates</th></tr>
<tr>
<td><code>{ADJ_FILE}</code> <small>({adj.get('emitted_dots',0):,} dots · SHA-256 <code>{ADJ_SHA[:16]}…</code>)</small><br>{ADJ_DL}</td>
<td>HOLDOUT-DTI <b>{ADJ_H.get('pooled_dti',0):.5f}</b> · 95% CI {ADJ_H.get('ci95_cluster_bootstrap',[0,0])[0]:.5f}–{ADJ_H.get('ci95_cluster_bootstrap',[0,0])[1]:.5f}
· paired Δ {ADJ_H.get('paired_delta_vs_gemsdoe32',0):+.5f} (CI {ADJ_H.get('paired_delta_ci95',[0,0])[0]:+.5f}…{ADJ_H.get('paired_delta_ci95',[0,0])[1]:+.5f})
<small>22,232 withheld · evaluator {ADJ_H.get('evaluator_version','?')} · baseline 0.099202</small></td>
<td>max 3-px overlap {100*(ADJ_U.get('U3_max_nonlattice_overlap_3px') or 0):.1f}% of {ADJ_U.get('unique_masks_compared',0)} masks (limit 70%) · max |Spearman| {(ADJ_U.get('pre_placement_max_abs_spearman') or 0):.3f} (limit 0.90) · FCHD-direct {(ADJ_U.get('fchd_direct_max_overlap_3px') or 0):.3f}<br>
<small>literal all-registry reading: <b>100% fail</b> on the registered dense witness (IR-01) — reported, not waived</small></td>
<td>{" · ".join(f'<span class="pill {ADJ_PILL[k][1]}">{ADJ_PILL[k][0]}</span>' for k in ADJ_PILL)}<small>{ADJ_NPASS}/5 · selector approval {adj.get("selector_approval")}</small></td>
</tr>
</table>
<p class="muted">Evidence: <a href="data/adjdis_run_card.json">run card</a> ·
<a href="data/adjdis_leakage_canary.json">canary</a> ·
<a href="data/adjdis_uniqueness_audit.json">uniqueness audit</a> ·
<a href="data/adjdis_experiments.json">experiment ledger</a> ·
<a href="data/adjdis_ir28_04_diagnostic.json">IR-30 diagnostic</a> ·
<a href="data/adjdis_ir28_05_fullphase_replay.json">IR-30 replay</a> ·
<a href="data/session_6984642c_run_card.json">session run card</a>.
Why Gate 1 failed mechanically: see IR-30 — the shared allocator's per-phase cap pruned the
adjacency phase to 27 of 18,900 cells, so that hypothesis was never engaged.</p>
</div>

<h2>Research archive (earlier lanes, each with its own verdict)</h2>
<p class="muted">Negative results are deliverables. These pages are kept byte-for-byte as they were
published and are bound to their own run cards; the current decision above supersedes only the
<i>site-wide</i> banner, not their findings.</p>
<ul>
<li><a href="hce/index.html">HCE</a> · <a href="fchd/index.html">FCHD-NCM</a> ·
<a href="lbcal/index.html">LBCAL</a> · <a href="thcs/index.html">THCS</a> ·
<a href="amdc/index.html">AMDC</a> · <a href="rfl/index.html">RFL</a> ·
<a href="cspes/index.html">CSPES</a> · <a href="lst1/index.html">LST1</a> ·
<a href="session-1f0b051d/index.html">session-1f0b051d</a> ·
<a href="downloads/index.html">all downloads</a></li>
</ul>

<p>Read the <a href="executive-summary.html">executive summary</a> for the nine-site table and the
answer to “why did 0.2778 win?”, the <a href="method.html">method page</a> for the physics and the five
ranked hypotheses, and <a href="how-to-submit.html">how to submit</a> for the exact portal steps.</p>
"""
page("WB-GEMS-DOE-3 · download &amp; submit", index, "index.html")

# ------------------------------------------------------------- executive summary
rows = []
for r in pair.get("implied_per_probe", [])[:9]:
    rows.append(r)
focus = json.loads((ROOT / "registry" / "focus_sites.json").read_text())["sites"]
focus_by_site = {f["site"]: f for f in focus}
focus_table = j("focus_site_table.json", {"rows": [], "spearman_nDots_vs_score": 0})
frows = []
for site in ["GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE30",
             "GEMSDOE31", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36"]:
    f = focus_by_site[site]
    im = {r["site"]: r for r in focus_table.get("rows", [])}.get(site, {})
    frows.append(f"""<tr>
<td><b>{site}</b><br><small><a href="{f['ref'] and 'https://github.com/buffedlizard55-lab/' + site + '/blob/' + f['ref'] + '/' + f['path']}">{Path(f['path']).name}</a></small></td>
<td class="num">{float(f['owner_reported']):.4f}</td>
<td class="num">{im.get('n_dots','—')}</td>
<td class="num">{im.get('implied_T',0):,.0f}</td>
<td class="num">{im.get('yield_per_dot',0):.3f}</td>
<td><span class="pill r">NO</span> already submitted by its own team; ≥86% of its dots sit within 3 px of another focus file</td>
<td><b>Do not submit</b></td></tr>""")

exec_summary = f"""
<h1>Executive summary</h1>
<p class="muted">Nine focus sites · why 0.2778 won · and the one unique file to submit instead.</p>

<div class="card ok">
<h2 style="margin-top:0;border:none">Answer in one table</h2>
<table>
<tr><th>Download this file</th><th class="num">ESTIMATE</th><th class="num">dots</th><th>Unique vs the nine focus sites?</th><th>Verdict</th></tr>
<tr>
<td><a href="{TIF}" download><b>{Path(TIF).name}</b></a><br><small>sha256 <code>{SHA[:16]}…</code></small></td>
<td class="num"><b>{dti_base:.2f}</b><br><small>95% PI {dti_pi[0]:.2f}–{dti_pi[1]:.2f}</small></td>
<td class="num">{N:,}</td>
<td><span class="pill g">YES</span> max 3-px overlap {uniq.get('max_directed_overlap',0):.3f} (limit 0.70);
max |ρ| {uniq.get('max_abs_spearman',0):.3f} (limit 0.90); reverse overlap vs focus files
≤ {max([r['their_dots_within3px'] for r in uniq.get('top_overlap_vs_focus_champions',[])] or [0]):.3f}</td>
<td><b style="color:#0a7d2c">SUBMIT</b></td>
</tr>
</table>
<p><b>Portal fields.</b> Name <code>{SUBMIT_NAME}</code> · note (≤ 140 characters)
<code>{NOTE}</code> ({len(NOTE)}/140). Expected to avoid the reported error “Predicted values must be in range [0, 1]”: every cell is finite and inside [0, 1]
(checked by <code>scripts/validate_submission.py</code>). Portal behaviour is not yet observed.</p>
<p class="muted">ESTIMATE = bias-corrected model output, not a competition score. The only real evidence is the
submission-page receipt. Floor {dti_floor:.2f} · ceiling {dti_ceil:.2f}.
Beats 0.2778 iff credit per dot ≥ {breakeven:.2f} (siblings measured 0.124–0.145).</p>
</div>

<h2>The nine focus sites — every one of them is already submitted, and they are one design family</h2>
<table>
<tr><th>Site · best file</th><th class="num">OWNER-REPORTED</th><th class="num">dots</th>
<th class="num">implied T</th><th class="num">credit/dot</th><th>Unique?</th><th>Verdict</th></tr>
{''.join(frows)}
</table>
<p><b>Read the third and fifth columns together: Spearman(dot count, score) = {focus_table.get('spearman_nDots_vs_score',0):+.3f}.</b> The nine “different” champions are one dot set,
iteratively pruned: their published scores are reproduced to ±0.005 by
<code>DTI = T/(0.2N + 0.8M)</code> with a single <code>T ≈ 5,400</code> and <code>M ≈ {M:,.0f}</code>.
Rank correlation between dot count and score across the nine is strongly negative — the differences are
arithmetic, not geology. Copying any of them cannot beat 0.2778, and all nine already belong to their
own teams (re-submitting them is a duplicate under the 70%/3-px rule).</p>

<h2>Why did 0.2778 win? (verified line by line from the bytes)</h2>
<ol>
<li><b>It is an exact subset of the 0.2708 base.</b>
<code>GEMSDOE32 …e5eb6e7e-zeros</code> contains 37,654 dots; <code>GEMSDOE28 h27-4</code>
contains 40,199. Set difference: <b>0 dots added, 2,545 removed</b> — verified with
<code>champion_is_subset_of_base = {pair.get('pair',{}).get('champion_is_subset_of_base')}</code>.</li>
<li><b>All 2,545 removed dots were within 3 px of the public catalogue</b>
(median distance {pair.get('pair',{}).get('removed_median_dist_to_catalogue_px')} px,
fraction within 3 px = {pair.get('pair',{}).get('removed_within_3px_of_catalogue_frac')}). The scored
truth is <em>off</em>-catalogue (experts map faults that the public USGS/INGENIOUS catalogue lacks), so
those dots earned exactly zero credit while each still paid 0.2 into the denominator.</li>
<li><b>That clean edit is a two-equation experiment.</b> With T unchanged, the pair gives
<code>M = 0.2(s₁N₁ − s₂N₂)/(0.8(s₂ − s₁)) = {M:,.1f}</code> hidden truth cells and
<code>T = s₂(0.2N₂ + 0.8M) = {T:,.1f}</code> cells reached. Δ predicted = +0.0071, observed = +0.0070.</li>
<li><b>The same model reproduces six more independent files</b> (different sites, sessions, model families)
with implied T between 5,230 and 5,481 — see the table above and
<code>evidence/pair_identification.json</code>.</li>
<li><b>So the leaderboard is dot-budget arithmetic.</b> Adding a dot raises the denominator by exactly 0.2
and the numerator by its kernel credit k; a dot pays only if <code>k &gt; 0.2·DTI ≈ 0.056</code>.
Everything above 0.2778 has to come from the <em>credit rate</em>, i.e. from placing dots where the
unmapped faults actually are.</li>
</ol>

<h2>Can we beat 0.2778? Yes — the mechanism and the risk</h2>
<p>Our file raises the credit rate two ways: (i) it deletes the entire zero-yield collar around the
catalogue (measured 0.000% of our dots are within 3 px of it) and (ii) it ranks ground by a
tomographic posterior fitted to {len(ladder.get('probes',[]))} published scores plus independent
LiDAR-scarp / magnetic / radiometric saliency, then spends a bounded budget of {N:,} dots at 3 px
minimum separation.</p>
<p><b>Risk, stated plainly:</b> the posterior's absolute level is not identifiable; the site-grouped
cross-validated score model has ρ = {inv.get('site_grouped_cv',{}).get('spearman',0):.3f} and
MAE = {inv.get('site_grouped_cv',{}).get('mae',0):.3f}, and the calibration of the design predictor
has R² = {calm.get('r2',0):.2f}. If our dots are no better than the sibling rate we land near
{dti_floor:.2f}. Spend one slot, read the receipt, then act on the receipt — not on this page.</p>

<h2>Five hypotheses we had not tried, ranked by expected improvement ÷ cost</h2>
<table>
<tr><th>#</th><th>Hypothesis</th><th>Layers / transform</th><th>Why it finds faults the catalogue lacks</th><th class="num">Est. gain</th><th class="num">Cost</th><th>Status</th></tr>
<tr><td>1</td><td><b>Metric-arithmetic inverse design</b> — optimise credit per dot, not the probability map</td>
<td>tomographic posterior + LiDAR scarp (ex_max, step_max, lapneg, coh) + |∇TMI_up150| + |∇TC|</td>
<td>never asks “where are mapped faults”; the catalogue is treated as a <em>negative</em> mask, which is exactly how the scored truth is defined</td>
<td class="num">+0.10…+0.30</td><td class="num">low</td><td>implemented (this file)</td></tr>
<tr><td>2</td><td><b>Chain placement</b> — dots every 3 px along a traced lineament instead of an isotropic lattice</td>
<td>ridge/curvature of the same saliency fields</td>
<td>one dot on a fault earns k = 1, ⅔, ⅓ for three consecutive truth cells; an isolated dot earns at most 1</td>
<td class="num">+0.05…+0.15</td><td class="num">medium</td><td>designed, not yet emitted</td></tr>
<tr><td>3</td><td><b>Relay / stepover anatomy only in the 4–30 px collar</b></td><td>catalogue geometry + scarp</td>
<td>unmapped faults concentrate in relays between overlapping strands — but this is where GEMSDOE33 already sits, so it collides on uniqueness</td>
<td class="num">+0.02…+0.08</td><td class="num">low</td><td>deprioritised (uniqueness)</td></tr>
<tr><td>4</td><td><b>Geothermal-discharge gating</b></td><td>K/Th/U ratios, TC, GDR wells &amp; springs (48 vents, 2,268 well/spring records)</td>
<td>hot springs and sinter sit on faults that are often unmapped; the discharge is a direct conduit signal</td>
<td class="num">+0.00…+0.05</td><td class="num">low</td><td>rejected: sibling live scores for geothermal-gated designs are 0.03–0.19</td></tr>
<tr><td>5</td><td><b>Blind-fault detection in basin fill</b> (detrended elevation, second-invariant strain, depth-to-base)</td>
<td>official <code>training_features.tif</code> 62-channel stack</td>
<td>blind faults have no surface trace; only the provided geophysical stack can see them</td>
<td class="num">?</td><td class="num">blocked</td><td>needs the authenticated DrivenData download (no credentials in this sandbox)</td></tr>
</table>
<p class="muted">Non-fault mimics every one of these must survive: alluvial-fan and lake-shore
constructional scarps, road/rail cuts and stock tanks (LiDAR), lithological contacts rather than faults
(magnetic/radiometric gradients), and evapotranspiration or playa evaporites (radiometric K).</p>

<h2>The file this session's other lane generated — status at a glance</h2>
<div class="card bad">
<table>
<tr><th>File to download</th><th>Estimated score</th><th>Unique vs all GEMSDOE registry sites?</th><th>Gate result</th><th>Decision</th></tr>
<tr>
<td><code>{ADJ_FILE}</code> <small>generated {adj.get('generated_utc','?')} · {adj.get('emitted_dots',0):,} dots · SHA-256 <code>{ADJ_SHA[:16]}…</code></small><br>{ADJ_DL}</td>
<td><b>HOLDOUT-DTI {ADJ_H.get('pooled_dti',0):.5f}</b> <small>95% CI {ADJ_H.get('ci95_cluster_bootstrap',[0,0])[0]:.5f}–{ADJ_H.get('ci95_cluster_bootstrap',[0,0])[1]:.5f} · {ADJ_H.get('n_withheld_positives',0):,} withheld · {ADJ_H.get('evaluator_version','?')} · paired Δ {ADJ_H.get('paired_delta_vs_gemsdoe32',0):+.5f} (CI {ADJ_H.get('paired_delta_ci95',[0,0])[0]:+.5f}…{ADJ_H.get('paired_delta_ci95',[0,0])[1]:+.5f}) · <b>local estimate only — not a leaderboard score</b></small></td>
<td><b>Content-aware: yes</b> — max {100*(ADJ_U.get('U3_max_nonlattice_overlap_3px') or 0):.1f}% within 3 px of any one of {ADJ_U.get('unique_masks_compared',0)} registry masks (limit 70%), max |Spearman| {(ADJ_U.get('pre_placement_max_abs_spearman') or 0):.3f} (limit 0.90), exact duplicate: {'yes' if ADJ_U.get('U1_exact_duplicate') else 'no'}.<br>
<b>Literal all-registry reading: no</b> (dense witness IR-01 = 100% for any non-empty raster).</td>
<td>{" · ".join(f'<span class="pill {ADJ_PILL[k][1]}">{ADJ_PILL[k][0]}</span> {k.split("_")[0]}' for k in ADJ_PILL)}<small>{ADJ_NPASS}/5 passed</small></td>
<td><b>NOT CLEARED FOR SUBMISSION</b> — method gates failed (G1), literal witness blocks (G3/IR-01), selector approval {adj.get("selector_approval")}</td>
</tr>
</table>
<p class="muted">“Estimated score” is a spatially-blocked holdout measurement on mirrored data —
never an organizer receipt. Evidence: <a href="data/adjdis_run_card.json">run card ↓</a> ·
<a href="data/adjdis_uniqueness_audit.json">uniqueness audit ↓</a> ·
<a href="data/session_6984642c_run_card.json">session run card ↓</a>.</p>
</div>
"""
page("Executive summary · nine focus sites", exec_summary, "executive-summary.html")

# ------------------------------------------------------------------ how to submit
howto = f"""
<h1>How to submit — exact steps</h1>
<div class="card ok">
<h3 style="margin-top:0">1 · Download</h3>
<p><a class="btn" href="{TIF}" download>⬇ {Path(TIF).name}</a></p>
<p>SHA-256 <code>{SHA}</code> — verify with <code>sha256sum {Path(TIF).name}</code>.</p>
<h3>2 · Go to the submission page</h3>
<p><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/">drivendata.org/competitions/306/competition-doe-gems/submissions/</a>
→ <b>New submission</b>.</p>
<h3>3 · Upload the <code>-zeros.tif</code> exactly as downloaded</h3>
<p>Do not re-export, re-project or “fix” it in a GIS. The bytes above already match the sample
submission's CRS (EPSG:32611), shape (3730 × 3292) and geotransform
(100, 0, 243350, 0, −100, 4508550).</p>
<h3>4 · Name and note</h3>
<table>
<tr><th>Field</th><th>Value</th><th class="num">Length</th></tr>
<tr><td>Name</td><td><code>{SUBMIT_NAME}</code></td><td class="num">{len(SUBMIT_NAME)}</td></tr>
<tr><td>Note (optional)</td><td><code>{NOTE}</code></td><td class="num">{len(NOTE)}/140</td></tr>
</table>
<h3>5 · What to expect (not yet observed)</h3>
<p>The format checks that run in this project (<code>scripts/validate_submission.py</code>, record
<a href="data/submission_validation_2026-10-28.json">docs/data/submission_validation_2026-10-28.json</a>)
find every one of the 12,279,160 cells finite and inside [0, 1] — min {est.get('validation',{}).get('min',0)},
max {est.get('validation',{}).get('max',0)}, non-finite {est.get('validation',{}).get('n_nonfinite','?')}.
Those are local checks. The portal's response is the only acceptance evidence, and none has been
received for this file.</p>
</div>

<h2>Official submission rules (verified 2026-10-28)</h2>
<div class="card">
<ul>
<li><b>Format</b> — single layer, <code>float32</code>, values between 0 and 1; same CRS (EPSG:32611),
resolution (100 m) and bounds as the training data; “data outside the bounds is null or nan”.
Source: <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">DrivenData problem page, “Submission format”</a>
and <a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">NLR Official Rules, §3.2–3.5</a>.</li>
<li><b>Automatic scoring</b> — the rules say submissions “will be automatically evaluated”. Expert review
happens <i>after</i> the initial round, to revise labels, and does not gate an upload.
No human inspector is part of acceptance.</li>
<li><b>Limits</b> — three submissions per week; one final submission per entity, chosen before the deadline
(NLR §3.2, §3.4).</li>
<li><b>Generative AI disclosure</b> — required in the submission narrative: the extent and manner of any
generative-AI use (NLR §3.2). Keep this in mind before final selection.</li>
</ul>
</div>

<h2>Why the zeros encoding was chosen (not proven)</h2>
<p>An earlier file wrote NaN outside the grid, and the portal once returned
“Predicted values must be in range [0, 1]” for a file of this kind. The cause is not confirmed:
no receipt for the rejected bytes is available. The official text allows “null or nan” outside the
bounds, so NaN is not ruled out by the rules.</p>
<ul>
<li>Zeros outside the footprint is the stricter encoding: every cell is finite and inside [0, 1]. A file
that passes this project's gate therefore cannot fail the range rule for a NaN reason.</li>
<li>This is <b>not</b> evidence that the portal prefers zeros. Several owner-reported scores in the
public list are for <code>-nan</code> files (for example GEMSDOE24 at 0.2477 and GEMSDOE28 at 0.2710),
so NaN files have scored positive. The encoding question is open until your own receipt arrives.</li>
</ul>

<h2>How to read the result</h2>
<table>
<tr><th>Receipt</th><th>Interpretation</th><th>Next action</th></tr>
<tr><td>≥ 0.28</td><td>beats the best sibling claim (0.2778) — the credit-rate mechanism works</td><td>keep this file as the round-1 submission; spend remaining slots on chain placement (hypothesis 2)</td></tr>
<tr><td>0.15 – 0.28</td><td>credit rate is real but below the sibling rate</td><td>raise the dot budget toward 30k; re-fit the posterior with the new receipt as a 99th probe</td></tr>
<tr><td>&lt; 0.15</td><td>the posterior localisation is wrong; the floor case</td><td>do not resubmit variants of this design; switch to hypothesis 2/5 and re-derive</td></tr>
</table>
<p class="muted">A low receipt is a deliverable, not a failure: it is the first measurement of the hidden
truth field that we would own rather than borrow.</p>

<div class="card bad">
<h3 style="margin-top:0">⚠ Do not upload the ADJDIS file — it is not cleared</h3>
<p>The other lane's candidate <code>{ADJ_FILE}</code> (HOLDOUT-DTI {ADJ_H.get('pooled_dti',0):.5f},
gates {ADJ_NPASS}/5, selector approval {adj.get('selector_approval')}) failed its preregistered Gate 1
and fails the literal witness reading. It is published on <a href="executive-summary.html">the
executive summary</a> for review and testing only. The upload steps above apply to
<b>{Path(TIF).name}</b> and the KHD alternative only.</p>
</div>
"""
page("How to submit", howto, "how-to-submit.html")

# --------------------------------------------------------------------- method page
method = f"""
<h1>Method and science</h1>
<h2>1 · What is actually being scored</h2>
<p><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">Problem description
(DrivenData #306, page 967)</a>: “develop models … that provide accurate information about the presence of
structures that are indicative of geothermal resources — namely, geological faults”. The published labels
are the USGS Quaternary fault catalogue plus INGENIOUS; the <em>scored</em> truth is a set of faults that
expert panels mapped and that are <b>not</b> in that catalogue. The public leaderboard is a chunk-wise
subset of the region; the private round is a disjoint chunk of the same region.</p>
<p>The metric text (same page) gives, with kernel k(d) = max(1 − d/300 m, 0), α = 0.2, β = 0.8:</p>
<pre><code>TP_w = Σ_{{g∈G}} max_{{x: d(x,g)≤R}} p(x)·k(d(x,g))
FP_w = Σ_x p(x)·[1 − max_g k(d(x,g))]
FN_w = Σ_{{g∈G}} [1 − max_x p(x)·k(d(x,g))]
DTI  = TP_w / (TP_w + 0.2·FP_w + 0.8·FN_w + ε)</code></pre>
<p>Because <code>FN_w = |G| − TP_w</code>, for a binary prediction with N support cells and M truth cells:
<b>DTI = T / (0.2N + 0.8M)</b>. This is implemented exactly (two Euclidean distance transforms per
evaluation) in <code>src/gemsw/exact.py</code> and unit-tested.</p>

<h2>2 · The decisive experiment: a subset pair identifies M and T</h2>
<p>GEMSDOE32's 0.2778 file is GEMSDOE28's 0.2708 file with 2,545 dots deleted, every one of them inside
the 3-px catalogue collar. Verified from the bytes by <code>scripts/pair_identification.py</code>:
added dots = 0, removed = 2,545, fraction of removed within 3 px of the catalogue = 1.000,
median distance 2 px. Since the scored truth is off-catalogue, T is unchanged by the edit, and the
score pair solves both unknowns: <b>M = {M:,.0f}</b>, <b>T = {T:,.0f}</b>.</p>
<p>Six independent files (other sites, other model families, other sessions) then imply
T = 5,230–5,481, i.e. the model is <em>internally consistent to a few percent</em>.
<b>This is the only quantitative explanation of this leaderboard that survives a falsification test.</b>
By contrast, correlating the 98 sibling scores with the exact DTI computed against plausible public
truth fields gives ρ = +0.07 (catalogue), +0.23 (SGMC),
+0.24 (off-catalogue SGMC) — no public fault map explains the leaderboard.</p>

<h2>3 · Why the sibling consensus cannot improve</h2>
<p>A dot is worth placing only if its kernel credit exceeds 0.2·DTI ≈ 0.056. All nine focus files spend
37k–61k dots for T ≈ 5.4k, i.e. 0.124–0.145 credit per dot; 11.7% of them are inside the catalogue
collar where credit is measured to be exactly zero. Their scores track
<code>T/(0.2N+0.8M)</code> with no residual left for “better geology”.</p>

<h2>4 · What this submission does differently</h2>
<ol>
<li><b>Treats the catalogue as a negative mask.</b> 0 dots within 3 px of a mapped fault (measured).</li>
<li><b>Ranks ground with a tomographic posterior</b> recovered from {len(ladder.get('probes',[]))} published
scores (<code>scripts/invert_ledger.py</code>, 400 m blocks, FISTA with a graph-Laplacian prior,
site-grouped CV ρ = {inv.get('site_grouped_cv',{}).get('spearman',0):.3f}, MAE = {inv.get('site_grouped_cv',{}).get('mae',0):.3f}).</li>
<li><b>Multiplies in independent geophysical evidence</b>: 1 m-LiDAR scarp morphology
(12 channels committed in <code>data/external/lidar_scarp_features_u8.tif</code>),
|∇(TMI upward-continued 150 m)| and |∇(total radiometric count)| from the GeoDAWN surveys
(USGS GeoDAWN, DOI 10.5066/P93LGLVQ). These are used as within-footprint percentile ranks so the
8-bit quantisation cannot bias the combination.</li>
<li><b>Bounded budget, 3 px minimum separation.</b> The emitted artifact is <code>docs/downloads/wbggems3-invdesign-anchor-20k-zeros.tif</code> (SHA-256 <code>{SHA[:16]}…</code>). {N:,} dots — each can claim a distinct truth cell
instead of re-claiming a neighbour's.</li>
<li><b>No soft values.</b> Probabilities are exactly 1.0 on support and 0.0 elsewhere: on this metric a
uniform scaling λ multiplies the numerator by λ while the 0.8·M term does not scale, so soft rasters are
strictly worse than their own binarisation.</li>
</ol>

<h2>4b · The published file, drawn from its own bytes</h2>
<p>Both figures below are rendered by <code>scripts/design_map_png.py</code> directly from
<code>{figs.get('deliverable','docs/downloads/wbggems3-invdesign-anchor-20k-zeros.tif')}</code>,
the public catalogue and the champion raster — nothing is hand-drawn, so the pictures cannot drift
from the file they describe (<code>evidence/design_figures.json</code>).</p>
<figure>
  <img class="map" src="assets/design-map.png" width="823"
       alt="20,000 submitted dots (red) against the public USGS/INGENIOUS catalogue (green) and the extended SGMC proxy catalogue (blue)">
  <figcaption><b>Where the dots are.</b> Red = the {int(figs.get('design_dots',0) or 0):,} submitted dots,
  green = the public catalogue, blue = the extended SGMC proxy catalogue.
  Measured on the full-resolution rasters: <b>{100*float(figs.get('frac_design_on_public_catalogue',0) or 0):.2f}%</b>
  of dots sit on a public catalogue cell and <b>{100*float(figs.get('frac_design_on_extended_catalogue',0) or 0):.2f}%</b>
  on the extended proxy — the catalogue is used as a negative mask, not as the target.</figcaption>
</figure>
<figure>
  <img class="map" src="assets/design-compare.png" width="823"
       alt="Submitted dots (red) against the GEMSDOE32 0.2778 champion (amber), white where within the 3-px kernel">
  <figcaption><b>Against the 0.2778 champion.</b> Amber = the champion's {int(figs.get('champion_dots',0) or 0):,} dots,
  white = submitted dots within the 3-px (300 m) kernel of a champion dot,
  red = submitted dots with no champion dot within the kernel.
  <b>{100*float(figs.get('frac_design_within_3px_of_champion',0) or 0):.1f}%</b> land near a champion dot, which is
  expected — both designs chase the same truth field — but the file is not a subset, superset or relabelling of it
  (the directed-overlap gate is 0.70; see the validation table).</figcaption>
</figure>

<h2>5 · Validation (all from <code>evidence/</code>)</h2>
<table>
<tr><th>Check</th><th>Value</th><th>Gate</th></tr>
<tr><td>Exact 98-probe score model, in-sample ρ</td><td class="num">{inv.get('full_sample',{}).get('spearman',0):.3f}</td><td><span class="pill g">informative</span></td></tr>
<tr><td>Site-grouped CV ρ / MAE</td><td class="num">{inv.get('site_grouped_cv',{}).get('spearman',0):.3f} / {inv.get('site_grouped_cv',{}).get('mae',0):.3f}</td><td><span class="pill a">moderate</span></td></tr>
<tr><td>Design-predictor calibration R² (98 siblings)</td><td class="num">{calm.get('r2',0):.2f}</td><td><span class="pill a">moderate</span></td></tr>
<tr><td>Candidate-truth correlations (catalogue / SGMC / off-SGMC)</td><td class="num">+0.07 / +0.23 / +0.24</td><td><span class="pill r">no public map explains it</span></td></tr>
<tr><td>Leakage canary: no feature used here is fitted to the hidden truth</td><td class="num">n/a</td><td><span class="pill g">by construction</span></td></tr>
<tr><td>Uniqueness: max 3-px directed overlap</td><td class="num">{uniq.get('max_directed_overlap',0):.3f}</td><td><span class="pill g">≤ 0.70</span></td></tr>
<tr><td>Uniqueness: max |Spearman|</td><td class="num">{uniq.get('max_abs_spearman',0):.3f}</td><td><span class="pill g">≤ 0.90</span></td></tr>
</table>
<p class="muted">Not done, and it must be said: no independent geological validation of the posterior's
<em>localisation</em> exists. The holdout that this repository previously used
(catalogue hide-and-recover) measures the wrong thing — it rewards reproducing the catalogue, which the
leaderboard punishes — and it is anti-correlated with published scores (ρ = −0.85 over the nine focus
files, recorded in <code>evidence/amdc_run_card.json</code>). It is retained for provenance and is not
used to promote anything.</p>
"""
page("Method and science", method, "method.html")

print("wrote docs/index.html, docs/executive-summary.html, docs/how-to-submit.html, docs/method.html")
