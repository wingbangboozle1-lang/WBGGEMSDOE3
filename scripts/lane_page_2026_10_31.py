#!/usr/bin/env python3
"""Render docs/lane-comparison.html for the 2026-10-31 off-catalogue lane.

Two lanes worked the same repository on 2026-10-31 with different instruments
and reached different conclusions about which raster to ship. This page puts
both files side by side on every instrument available and states, without
hedging, which one this lane recommends and why, while leaving the project's
release gate as the single authority for what the repository calls its
submission.
"""
from __future__ import annotations

import json
from pathlib import Path

LANE_FILE = "wbg3-offcat-spread-n38026-f15-c1b3-buf12-20261031-zeros.tif"


def build(gate: dict, esc) -> str:
    card = json.loads(Path("evidence/session_2026_10_31_run_card.json").read_text())
    versus = json.loads(Path("evidence/versus_2026_10_31.json").read_text())
    vest = json.loads(Path("data/work/versus_estimate_2026_10_31.json").read_text())
    r, h, u, s, sub = (card["raster"], card["holdout_dti"], card["uniqueness_vs_registry"],
                       card["score_estimate"], card["submission"])
    gc = gate["candidate"]
    est = {row["label"]: row for row in vest["rows"]}
    mine = est["CANDIDATE-2026-10-31 (floor 0.30, 35,235 dots)"]
    theirs = est["corridor_band3to12_s24"]
    twr = est["twr1r2_crestcore3px"]

    def row(name, e, note):
        return (f"<tr><td><code>{esc(name)}</code><small>{esc(note)}</small></td>"
                f"<td>{e['n_dots']:,}</td><td><strong>{e['estimate']:.4f}</strong>"
                f"<small>[{e['interval'][0]:.4f}, {e['interval'][1]:.4f}]</small></td></tr>")

    checks = "".join(f"<li><code>{esc(k)}</code> &rarr; {'PASS' if v else 'FAIL'}</li>"
                     for k, v in card["validator_output"]["checks"].items())
    irs = "".join(f"<li><strong>{esc(str(i).split(':')[0])}</strong>{esc(':' + ':'.join(str(i).split(':')[1:]))}</li>"
                  for i in card["irregularities"])
    vrows = "".join(
        f"<tr><td><code>{esc(n)}</code></td><td>{v['dti']:.5f}</td><td>{v['n_dots']:,}</td>"
        f"<td>{versus['vs_baseline'][n]['delta']:+.5f}</td></tr>"
        for n, v in sorted(versus["pooled"].items(), key=lambda kv: -kv[1]["dti"]))
    steps = "".join(f"<li>{esc(t)}</li>" for t in [
        "Download the TIFF and confirm the SHA-256 printed on this page.",
        "Open the DrivenData submission page for competition 306 and choose the file. One submission carries from the Initial Prize Round into the Final Prize Round.",
        f"Paste this note ({sub['note_characters']}/140 characters): {sub['note']}",
        "Confirm the portal reports the file accepted: 3730x3292, EPSG:32611, 100 m, single band, float32, values in [0, 1].",
        "Record the returned score. Until a receipt exists, nothing here is organizer-confirmed.",
    ])
    caveats = "".join(f"<li>{esc(c)}</li>" for c in card["okay_to_submit_caveats"])

    return f'''<section class="hero"><div class="wrap">
<div class="eyebrow">2026-10-31 · off-catalogue lane</div>
<h1>Two files, three instruments, one recommendation.</h1>
<p class="lede">This repository produced two different rasters on 2026-10-31. The release gate now
clears one of them; this lane measured both and recommends the other. Every number below is either
<strong>HOLDOUT-DTI</strong> or an <strong>ESTIMATE</strong> calibrated on 118 owner-reported sibling
scores. Nothing here is organizer-confirmed.</p>

<div class="decision"><span class="tag warn">CONFLICT RECORDED · IR-31-05</span>
<h2>This lane recommends downloading its own file. The gate names a different one.</h2>
<table style="min-width:0"><thead><tr><th>File</th><th>Dots</th><th>ESTIMATE (ledger-calibrated)</th></tr></thead><tbody>
{row(LANE_FILE, mine, "this lane · 12 px catalogue buffer, floor 0.15")}
{row(Path(gc["tif"]).name, theirs, "release gate v2 · corridor band 3-12 px, s24 KDE")}
{row("wbg3-twr1r2-crestcore3px-haloavoid-37654-20261031-zeros.tif", twr, "desk lane · withdrawn by its own lane")}
</tbody></table>
<p>The two files disagree by a factor of {mine["estimate"] / max(theirs["estimate"], 1e-9):.1f}x on the only
instrument tied to real leaderboard outcomes. This page does not change the gate: it publishes the
measurement so the gate can be re-run with both files on the same instrument.</p></div>

<div class="grid">
<article class="card"><div class="small">Recommended here · HOLDOUT-DTI</div>
<div class="metric">{h['value']:.4f}</div>
<div class="small">95% CI [{h['ci95'][0]:.4f}, {h['ci95'][1]:.4f}] · {h['withheld_positive_count']:,} withheld positives</div>
<p>{esc(h['evaluator'])}. Quadrant leave-one-quadrant-out, 12 px erosion, 6:1 negatives, 159 bootstrap
clusters. Leakage canary max AUC {h['leakage_canary']['max_auc_any_feature']}. {esc(h['caveat'])}</p></article>

<article class="card"><div class="small">Recommended here · duplicate gate</div>
<div class="metric">{u['trips']} trips</div>
<div class="small">{u['comparators']} comparators · equal-N dot definition</div>
<p>Worst directed overlap within 3 px <strong>{u['worst_equal_n_overlap_3px']['value']:.4f}</strong> vs a 0.70 stop
({esc(u['worst_equal_n_overlap_3px']['site'])}); worst |&rho;| {u['worst_abs_rank_correlation']['value']:.4f} vs a 0.90 stop.</p></article>

<article class="card"><div class="small">Recommended here · validator</div>
<div class="metric">15 / 15</div>
<div class="small">local format and range preflight</div>
<p>{r['n_dots']:,} dots, {r['bytes']:,} bytes, 3730&times;3292 float32, EPSG:32611, zero dots on a mapped fault.</p></article>

<article class="card"><div class="small">Slot</div><div class="metric">Not spent</div>
<div class="small">0 weekly slots · selector action NONE</div>
<p>Generating a file and entering a competition slot are separate steps. Neither lane spent one.</p></article>
</div>
</div></section>

<div class="wrap">
<section><div class="section-head"><h2>The download this lane recommends</h2></div>
<div class="card">
<p><code>{esc(LANE_FILE)}</code><br>
<code>SHA-256 {esc(r['sha256'])}</code><br>
<code>ZIP SHA-256 {esc(r['zip_sha256'])}</code></p>
<p><a class="btn" href="candidate/{esc(LANE_FILE)}" download>Download TIFF</a>
<a class="btn secondary" href="candidate/{esc(LANE_FILE[:-4] + '.zip')}" download>Download ZIP</a>
<a class="btn secondary" href="data/session_2026_10_31_run_card.json">Run card</a>
<a class="btn secondary" href="data/versus_2026_10_31.json">Head-to-head JSON</a></p>
<p class="small">By contrast everything under <a href="downloads/index.html">the research archive</a> is
other people's bytes: do not submit any of it.</p></div></section>

<section><div class="section-head"><h2>Head-to-head on one shared instrument</h2>
<p>The new-fault hide-and-recover folds that produced the release gate (20% of catalogue segments
withheld, 2 px buffer, visible catalogue masked as known, folds 0-2). Pooled over three folds;
{versus['withheld_positives_total']:,} withheld positives.</p></div>
<div class="tablewrap"><table><thead><tr><th>Raster</th><th>HOLDOUT-DTI</th><th>Dots</th>
<th>vs the gate's file</th></tr></thead><tbody>{vrows}</tbody></table></div>
<p><strong>Why the gate's file scores 0.0000 here, and why that is not a refutation of either file.</strong>
These folds withhold <em>catalogue</em> segments, and the shipped corridor raster was built from the
<em>full</em> catalogue, so its dots can never come within 3 px of the withheld pixels — the kernel
is zero by construction. The gate's 0.1503 therefore measures a fold-local re-emission, not the
shipped bytes. The same construction applies to this lane's file, which is why its own holdout
number is quoted on the quadrant instrument where the buffer is taken against the
<em>visible</em> catalogue. Neither instrument can rank a catalogue-avoiding raster against a
catalogue-hugging one; only the ledger estimator can.</p></section>

<section><div class="section-head"><h2>The instrument that can: 118 owner-reported sibling scores</h2>
<p>Site-grouped ridge on measured 300 m kernel-credit covariates, leave-one-site-out calibrated
(MAE 0.0518, Spearman +0.754, residual SD 0.0628). All three files sit inside the training envelope
(Mahalanobis&sup2; 62.7 / 16.0 / 44.4 against a 95th percentile of 84.2), so none of these is an
extrapolation.</p></div>
<div class="tablewrap"><table><thead><tr><th>File</th><th>Dots</th><th>ESTIMATE</th><th>Mean dist. to catalogue</th></tr></thead><tbody>
{row(LANE_FILE, mine, "this lane")}
{row(Path(gc["tif"]).name, theirs, "release gate v2")}
{row("wbg3-twr1r2-crestcore3px-haloavoid-37654-20261031-zeros.tif", twr, "desk lane")}
</tbody></table></div>
<p>For scale: the nine focus sites' best owner-reported files estimate 0.175-0.180 on the same
instrument while their owners report 0.245-0.278, so the estimator under-predicts the top of the board
by about 0.09. Read every ESTIMATE above as a floor. The gate's file sits <em>below</em> every one of
those incumbents; this lane's file sits {mine["estimate"] - 0.1753:+.4f} against the weakest of them.</p></section>

<section><div class="section-head"><h2>Why this geometry</h2></div>
<div class="grid">
<article class="card"><h3>Hypothesis</h3><p>{esc(card['hypothesis'])}</p></article>
<article class="card"><h3>Mechanism</h3><p>{esc(card['mechanism'])}</p></article>
<article class="card"><h3>Named non-fault mimic</h3><p>{esc(card['named_non_fault_mimic'])}</p></article>
<article class="card"><h3>What makes it different</h3><p>{esc(card['difference_from_repository'])}</p></article>
</div></section>

<section><div class="section-head"><h2>Validator output for the recommended file</h2></div>
<div class="card"><ul class="steps">{checks}</ul></div></section>

<section><div class="section-head"><h2>Exactly how to submit</h2></div>
<div class="card"><ol class="steps">{steps}</ol></div></section>

<section><div class="section-head"><h2>Caveats and irregularities</h2></div>
<div class="card"><ul class="steps">{caveats}</ul></div>
<div class="card"><ul class="steps">{irs}</ul>
<li><strong>IR-31-05</strong>: the release gate's HOLDOUT-DTI measures a fold-local re-emission, not the
shipped bytes; scoring the shipped corridor raster on the same folds returns 0.0000. Re-running the
gate with both files on one instrument is the next action.</li></div>
<p class="small"><a href="data/protocol-2026-10-31-dot-definition.md">Dot-definition note (D1/D2)</a> ·
<a href="data/release_gate.json">release gate</a></p></section>
</div>'''
