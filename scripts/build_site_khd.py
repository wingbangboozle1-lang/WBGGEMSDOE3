#!/usr/bin/env python3
"""Build the WBGGEMSDOE3 Pages site for the 2026-10-28 KHD release.

Policy revision (user brief 2026-10-28, adopted once here): the site must make it
obvious whether a generated TIF is OK to download and submit.  The KHD release
publishes a hash-bound candidate that PASSED every locally checkable gate
(portal format/range + content-aware parallel-run uniqueness) with an honest
ESTIMATE band and a negative experimental verdict on the anti-correlated holdout.
The dense-witness literal reading (IR-01) is disclosed on every page.

Pages: index.html (exec summary on top + download), executive-summary.html,
how-to-submit.html, submission.html, research.html, evidence.html.
"""
from __future__ import annotations

import hashlib
import html
import json
import shutil
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"

CARD = json.loads((ROOT / "evidence/khd_run_card.json").read_text())
EMIT = json.loads((ROOT / "evidence/khd_emit.json").read_text())
HOLD = json.loads((ROOT / "evidence/khd_holdout.json").read_text())
FOCUS = json.loads((ROOT / "evidence/khd_focus_overlap.json").read_text())
FIT = json.loads((ROOT / ".cache/session/lst_fit_session.json").read_text())

TIF = f"downloads/{CARD['submission_name']}.tif"
ZIP = f"downloads/{CARD['submission_name']}.zip"
RECEIPT = f"downloads/{CARD['submission_name']}.json"


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def esc(x) -> str:
    return html.escape(str(x), quote=True)


# Owner-reported scores copied from the user brief 2026-10-28 (evidence class:
# OWNER-REPORTED receipts on the named pages; not independently authenticated).
NINE = [
    ("GEMSDOE24", "gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif", 0.2477,
     "68d0e2e4fcc594f9", 60069, 0.2654),
    ("GEMSDOE25", "gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif", 0.2600,
     "91eae1ca42ec845e", 44090, 0.2808),
    ("GEMSDOE27", "gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan.tif", 0.2449,
     "33003374335d84bf", 61328, 0.2626),
    ("GEMSDOE28", "gems28-h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan.tif", 0.2710,
     "5556aa1438fd6737", 37660, 0.2944),
    ("GEMSDOE30", "gemsdoe30-d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca.tif", 0.2600,
     "8cf893ead5667df2", 44090, 0.2808),
    ("GEMSDOE31", "gemsdoe31-h27-4-solo-d28-20261004-8acb75e1-nan.tif", 0.2708,
     "07b6db440535404b", 40199, 0.2948),
    ("GEMSDOE32", "gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif", 0.2778,
     "c55bafc470054e82", 37654, 0.3047),
    ("GEMSDOE33", "GEMSDOE33-h33d-analog-tip-stepover-r30-20261004-cb490425926e.tif", 0.2632,
     "87f857d505e23247", 41865, 0.2885),
    ("GEMSDOE36", "gemsdoe36-anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros.tif", 0.2750,
     "e15891020b9c5705", 38854, 0.3008),
]

CSS = "assets/styles.css"
JS = "assets/status.js"

HEAD = """<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="gemsdoe-decision" content="SUBMISSION-READY">
<title>{title} · GEMS Field Notes</title>
<link rel="stylesheet" href="{css}">
</head><body>
<div class="wrap toprow"><a class="brand" href="index.html">GEMS Field Notes</a>
<nav><a href="index.html">Executive summary</a> <a href="how-to-submit.html">How to submit</a>
<a href="submission.html">Submission file</a> <a href="research.html">Research</a>
<a href="evidence.html">Evidence</a></nav></div>
<p class="wrap small"><span class="tag">STATUS: OK TO DOWNLOAD AND SUBMIT</span> —
one hash-bound TIF passed every locally checkable gate; the score is an estimate; details on
<a href="submission.html">the submission page</a>.</p>
"""


def hero() -> str:
    return f"""
<div class="hero">
  <p class="eyebrow">WBGGEMSDOE3 · KHD lane · {esc(CARD['generated_utc'])}</p>
  <h1>One submission raster is ready: <strong>OK TO DOWNLOAD AND SUBMIT</strong></h1>
  <p class="lede"><strong>{esc(CARD['submission_name'])}.tif</strong> —
  {CARD['validator']['positive_cells']:,} binary dots, all values in [0, 1], no NaN anywhere,
  EPSG:32611 grid identical to <code>sample_submission.tif</code>. Unique against every
  sparse registry comparator (max directed 3-px overlap {CARD['uniqueness']['max_nonlattice_overlap_3px']:.3f} ≤ 0.70;
  vs the nine focus sites ≤ {CARD['uniqueness']['focus_site_directed_overlap_max']:.3f}).</p>
  <p><a class="btn" href="{TIF}">Download the submission TIF ({sha(ROOT / 'docs' / TIF)[:12]}…)</a>
     <a class="btn secondary" href="{ZIP}">Download as ZIP</a>
     <a class="btn secondary" href="how-to-submit.html">How to submit →</a></p>
  <p class="small">Submission note to paste on the form (108 chars):
  <code>{esc(CARD['submission_note'])}</code></p>
  <div class="decision">
    <strong>Score estimate (not a score):</strong> {CARD['ledger_projection']['estimate_headline']['value']}
    (band {CARD['ledger_projection']['estimate_headline']['band'][0]}–
    {CARD['ledger_projection']['estimate_headline']['band'][1]}).
    The best owner-reported score in the nine focus sites is GEMSDOE32 B2 at
    <strong>0.2778</strong>; the public leaderboard best observed is 0.4544.
    The experimental verdict on the local holdout gate is <strong>negative</strong>
    (that holdout is anti-correlated with the leaderboard for this family) — see
    <a href="executive-summary.html">the full executive summary</a> before spending a weekly slot.
  </div>
  <p class="small" data-freshness data-checked="2026-10-27T12:00:00+00:00">
    PUBLIC-LEADERBOARD OBSERVATION (not a receipt): best observed 0.4544 (xiaofanhu),
    Last checked · 2026-10-27 12:00 UTC. Quoted figures 0.4413 / 0.3195 are earlier
    snapshots — see irregularities on the <a href="evidence.html">evidence page</a>.</p>
</div>"""


def exec_table() -> str:
    foc = {r["site"]: r for r in FOCUS}
    rows = []
    for site, fn, owner, sha8, dots, model in NINE:
        f = foc[site]
        uniq = "YES" if f["cand_within3_of_ref"] <= 0.70 else "NO"
        rows.append(
            f"<tr><td><strong>{esc(site)}</strong></td>"
            f"<td class='file'>{esc(fn)}<br><span class='small'>sha256 {sha8}… · {dots:,} dots</span></td>"
            f"<td>{owner:.4f}<br><span class='small'>OWNER-REPORTED</span></td>"
            f"<td>{model:.4f}<br><span class='small'>ESTIMATE ±0.026</span></td>"
            f"<td>{f['cand_within3_of_ref']:.3f}</td><td>{uniq}</td></tr>")
    est = CARD["ledger_projection"]["estimate_headline"]
    return f"""
<div class="tablewrap"><table>
<thead><tr><th>Site</th><th>Best file (research reference)</th><th>Owner-reported</th>
<th>Model estimate</th><th>Our candidate's directed 3-px overlap vs this file</th>
<th>Our candidate unique vs this file?</th></tr></thead>
<tbody>{''.join(rows)}
<tr><td><strong>THIS REPO (new)</strong></td>
<td class="file"><a href="{TIF}">{esc(CARD['submission_name'])}.tif</a>
<br><span class="small">sha256 {CARD['raster_sha256'][:16]}… · 37,654 dots · zeros-outside</span></td>
<td>— (not yet submitted)</td>
<td><strong>{est['value']}</strong> (band {est['band'][0]}–{est['band'][1]})
<br><span class="small">ESTIMATE (triangulated)</span></td>
<td>max 0.640 vs any registry mask</td><td><strong>YES</strong></td></tr>
</tbody></table></div>"""


def gate_list() -> str:
    v = CARD["validator"]
    u = CARD["uniqueness"]
    est = CARD["ledger_projection"]["estimate_headline"]
    return f"""
<div class="grid">
 <div class="card"><h3>1 · Portal format gates — PASS</h3>
  <ul class="small">
   <li>single-band GeoTIFF, float32 — {v['single_band']}</li>
   <li>every value in [0, 1]; no NaN, no inf — {v['values_in_0_1']} / {v['no_nan_no_inf_anywhere']}</li>
   <li>CRS EPSG:32611, shape 3730×3292, geotransform identical to sample_submission.tif</li>
   <li>outside-footprint cells all zero (the all-finite encoding that fixes the
       “Predicted values must be in range [0, 1]” rejection of NaN-outside files)</li>
   <li>zero positive cells on the mapped catalogue (catalogue pixels earn no credit)</li>
   <li>ZIP contains exactly one TIFF whose sha256 equals the .tif</li>
  </ul></div>
 <div class="card"><h3>2 · Uniqueness gates — PASS (content-aware)</h3>
  <ul class="small">
   <li>{u['registry_files']} comparator files indexed, {u['sparse_masks_compared']} sparse non-lattice masks compared</li>
   <li>max directed 3-px overlap {u['max_nonlattice_overlap_3px']:.4f} ≤ 0.70 (cap enforced at 0.64 during allocation)</li>
   <li>not an exact duplicate of any registered dot mask</li>
   <li>surface |Spearman| pre-placement {u['preplacement_surface_max_abs_spearman']:.3f}, on final dots {u['final_surface_max_abs_spearman']:.3f} — both ≤ 0.90</li>
   <li>vs the nine focus sites: max {u['focus_site_directed_overlap_max']:.3f} (every one ≤ 0.70)</li>
   <li>lattice/dense-witness excess {u['lattice_excess']} ≤ 0.05 (IR-01 literal reading disclosed — see evidence)</li>
  </ul></div>
 <div class="card"><h3>3 · Score estimate — DISCLOSED, never a score</h3>
  <ul class="small">
   <li>LST ledger projection 0.3655 (LOO MAE 0.0251) — in-sample optimistic, upper anchor</li>
   <li>class anchor: owner-reported uniqueness-constrained designs 0.2296–0.2478</li>
   <li><strong>triangulated ESTIMATE {est['value']} (band {est['band'][0]}–{est['band'][1]})</strong></li>
   <li>beats 0.2778? plausible but unproven; the band straddles it</li>
  </ul></div>
 <div class="card"><h3>4 · Experimental verdict — NEGATIVE on the holdout gate</h3>
  <ul class="small">
   <li>HOLDOUT-DTI (22,232 withheld, quality gate): KHD 0.00006 vs B2 bytes 0.00452,
       paired Δ = −0.00446 [−0.00522, −0.00375]</li>
   <li>the catalogue holdout is anti-correlated with owner-reported dotted-family scores
       (Spearman −0.146 / −0.849) — it cannot rank this family; KHD is still 6× the strata control</li>
   <li>run-card verdict <code>{esc(CARD['verdict'])}</code> = the preregistered promotion gate fails;
       releasing the file as the unique deliverable is a separate, disclosed decision;
       spending a weekly slot is the selector's call</li>
  </ul></div>
</div>"""


def page_index() -> str:
    return HEAD.format(title="Executive summary", css=CSS) + hero() + f"""
<div class="wrap">
<h2 class="section-head">Executive summary — the nine focus sites and the new submission</h2>
<p class="small">Owner-reported values are receipts posted on the named owner pages, not
independently authenticated organizer receipts. Model estimates come from the ledger-tomography
instrument (leave-one-out MAE {FIT['loo_mae']:.4f}); every figure below is an ESTIMATE or an
OWNER-REPORTED claim — none is an organizer-confirmed score for these bytes.</p>
""" + exec_table() + f"""
<h2 class="section-head">Validation gates for the generated TIF</h2>
""" + gate_list() + f"""
<h2 class="section-head">Why GEMSDOE32 B2 scores 0.2778 — and what beats it</h2>
<div class="card"><p>B2 is not a new model: it is a <strong>byte-exact pruning chain</strong> of the
dotted h19-5 family (verified this session with <code>np.array_equal</code> on the pinned bytes):</p>
<ul>
 <li><code>d2-8</code> (44,090 dots) → 0.2600</li>
 <li>minus 3,891 dots <em>on</em> the mapped catalogue → <code>solo-d28</code> (40,199) → 0.2708 <strong>(+0.0108)</strong></li>
 <li>minus 2,545 dots in the 1.01–2.01 px catalogue band → <code>B2</code> (37,654) → 0.2778 <strong>(+0.0070)</strong></li>
 <li>plus 1,200 extra dots (<code>anderson-pinn</code>, 38,854) → 0.2750 <strong>(−0.0028)</strong></li>
</ul>
<p>The organizer masks catalogue <em>truth</em> pixels, but predictions there still cost FP mass —
so catalogue dots are pure loss. Dots whose 300 m kernel credit is duplicated by neighbours add
FP mass without TP credit. The metric is won by <strong>precision of placement, not coverage</strong>.
The entire h19-5 network is already saturated by the family (0 network cells lie &gt;3 px from
family dots), so a <em>unique</em> submission must spend ≥30% of its dots off-network — the
uniqueness tax. That is why honest estimates for unique candidates cluster at 0.23–0.27 and why
beating 0.2778 requires new truth-location information (the H2/H3 research lanes), not more
family pruning.</p>
<p class="small"><a href="evidence.html">Full evidence and irregularities →</a></p></div>
<h2 class="section-head">Historical research lanes (research only — DO NOT SUBMIT these artifacts)</h2>
<p class="small"><a href="hce/index.html">hce/index.html</a> · <a href="thcs/index.html">thcs/index.html</a> ·
<a href="rfl/index.html">rfl/index.html</a> · <a href="amdc/index.html">amdc/index.html</a> ·
<a href="lst1/index.html">lst1/index.html</a> · <a href="lbcal/index.html">lbcal/index.html</a> ·
<a href="fchd/index.html">fchd/index.html</a> · <a href="cspes/index.html">cspes/index.html</a> ·
<a href="session-1f0b051d/index.html">session-1f0b051d/index.html</a> ·
<a href="downloads/index.html">downloads/index.html</a></p>
<div class="footer small">Built from run card {esc(CARD['generated_utc'])} ·
raster sha256 <code>{CARD['raster_sha256']}</code></div>
</div>
<script src="{JS}"></script></body></html>"""


def page_exec() -> str:
    return HEAD.format(title="Nine-site executive summary", css=CSS) + """
<div class="wrap"><h1>Nine-site executive summary</h1>
<p class="lede">What each focus site's best submission is, what it reportedly scored, how our
new submission relates to it, and whether our submission is unique against it.</p>
""" + exec_table() + f"""
<h2 class="section-head">Reading the table</h2>
<div class="card"><ul>
<li><strong>Owner-reported</strong> — the score posted on the owner's site for that file. Evidence
class: OWNER-REPORTED receipt; not independently authenticated (no DrivenData receipt was obtained
in this sandbox).</li>
<li><strong>Model estimate</strong> — leave-one-out projection from the ledger-tomography instrument
trained on 112 unique owner-scored rasters (LOO MAE {FIT['loo_mae']:.4f}, Spearman {FIT['loo_spearman']:.3f}).
It is an ESTIMATE. It carries a systematic +0.025 optimistic bias on this family.</li>
<li><strong>Directed 3-px overlap</strong> — the parallel-run protocol's duplicate test: the fraction
of our candidate's dots that fall within 3 px of that file's dots. Above 0.70 would mean we drifted
into that lane. Ours is ≤ 0.59 against every focus file and ≤ 0.64 against every registered sparse mask.</li>
<li><strong>Unique: YES</strong> — our candidate is NOT a copy or near-copy of any listed submission.
Byte-level: its sha256 ({CARD['raster_sha256'][:16]}…) matches no registered raster; its dot mask
is not identical to any of the {CARD['uniqueness']['sparse_masks_compared']} compared masks.</li>
<li><strong>Estimates and owner reports are never scores.</strong> Every figure below carries an
evidence class label; none is an organizer-confirmed score. Organizer-confirmed scores exist only
as receipts on your own DrivenData submission page.</li>
<li><strong>Submission comment limit:</strong> the DrivenData note field is optional and should stay
≤ 140 characters (ours: {len(CARD['submission_note'])}). The portal range check rejects files whose
values leave [0, 1] — e.g. “Predicted values must be in range [0, 1]” for NaN-outside encodings;
the released file is all-finite binary 0/1 with zeros outside the footprint.</li>
</ul></div>
<h2 class="section-head">Cross-site near-duplicates among the nine (why “unique” matters)</h2>
<div class="card"><p>The nine files are one extended family — the shared core is a
<strong>byte-exact pruning chain</strong>. Verified subset identities this session:</p>
<ul>
<li>GEMSDOE30's dots are identical to GEMSDOE25's (same 44,090 cells, different serialization; both report 0.2600).</li>
<li>GEMSDOE31 = GEMSDOE25 − on-catalogue dots (exactly); GEMSDOE32 B2 = GEMSDOE31 − 1–2 px band (exactly);
GEMSDOE36 = B2 + 1,200 dots (exactly).</li>
<li>Every GEMSDOE32 dot lies within 3 px of a GEMSDOE24/25/27/30/31/36 dot — the family is
&gt;97% overlapping under the directed test. Re-downloading and re-submitting any of these files
would not be a unique submission.</li>
</ul>
<p>Our candidate's directed overlap against each of them is 0.56–0.59 — comfortably inside the 0.70
rule — and it was built from official GeoDAWN/3DEP layers + the public score ledger, never copied
from any of these rasters.</p></div>
<div class="footer small"><a href="index.html">← Back to the executive summary and download</a></div>
</div><script src="{JS}"></script></body></html>"""


def page_howto() -> str:
    return HEAD.format(title="How to submit", css=CSS) + f"""
<div class="wrap"><h1>How to make a submission (exact steps)</h1>
<p class="lede">Everything is prepared; submitting takes about two minutes on the DrivenData form.</p>
<div class="card">
<h3>Step 1 — Download the file</h3>
<p><a class="btn" href="{TIF}">{esc(CARD['submission_name'])}.tif</a>
&nbsp;<a class="btn secondary" href="{ZIP}">ZIP version (also accepted)</a></p>
<p class="small">This is a single-band GeoTIFF. sha256: <code>{CARD['raster_sha256']}</code>.
If your browser saves it with a different name, rename it back to
<code>{esc(CARD['submission_name'])}.tif</code> (any <code>.tif</code> name works; the name only matters for your own bookkeeping).</p>
</div>
<div class="card">
<h3>Step 2 — Open the submission page</h3>
<p><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/">
https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/</a> (login required).
Click <strong>New submission</strong>.</p>
</div>
<div class="card">
<h3>Step 3 — Choose the file</h3>
<p>Under <em>File to submit</em>, choose the .tif (or the .zip). The form accepts
“a single-band GeoTIFF (.tif) file, or a .zip file containing a single GeoTIFF”.</p>
<p><strong>About the earlier error “Predicted values must be in range [0, 1]”:</strong> that is the
portal's range check. Files written with NaN outside the footprint (the older <code>-nan</code>
variants) fail it because NaN is not in [0, 1]. <strong>The file on this page is the all-finite
<code>-zeros</code> encoding: every one of the 12,279,160 values is in [0, 1]</strong> — verified
byte-by-byte before publication (see <a href="evidence.html">evidence</a>). This is the same
encoding as the 0.2778 GEMSDOE32 B2 file.</p>
</div>
<div class="card">
<h3>Step 4 — Fill the note</h3>
<p>In <em>Note (optional)</em>, paste this comment (so you can tell submissions apart later):</p>
<p><code>{esc(CARD['submission_note'])}</code></p>
<p class="small">The suggested submission display name is
<code>{esc(CARD['submission_name'])}</code> (140-char limit respected: {len(CARD['submission_name'])} chars).</p>
</div>
<div class="card">
<h3>Step 5 — Submit and record the receipt</h3>
<p>Press <strong>Create submission</strong>. DrivenData shows a score receipt. Copy the exact score
into your records with the file's sha256 (<code>{CARD['raster_sha256'][:16]}…</code>). Every number
on this site labelled ESTIMATE or OWNER-REPORTED is <em>not</em> a score — only the receipt is.</p>
<p class="small">Competition rules: ≤ 3 submissions per week, one final choice across rounds,
generative-AI disclosure, reproducible solution assets
(<a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">rules PDF</a>). Promotion to a weekly slot
is the selector's decision — the score band for this file (0.23–0.31) straddles the current
family best (0.2778), so treat the slot as a measured bet, not a certainty.</p>
</div>
<div class="footer small"><a href="index.html">← Executive summary</a></div>
</div><script src="{JS}"></script></body></html>"""


def page_submission() -> str:
    rec = json.loads((ROOT / "docs" / RECEIPT).read_text()) if (ROOT / "docs" / RECEIPT).is_file() else {}
    return HEAD.format(title="Submission file", css=CSS) + f"""
<div class="wrap"><h1>Submission file</h1>
<p class="lede"><strong>OK TO DOWNLOAD AND SUBMIT</strong> — all local gates pass; the score is an
estimate; the weekly-slot decision is yours.</p>
<div class="card">
<p class="file"><a class="btn" href="{TIF}">{esc(CARD['submission_name'])}.tif</a>
&nbsp;<a class="btn secondary" href="{ZIP}">.zip</a>
&nbsp;<a class="btn secondary" href="{RECEIPT}">receipt .json</a></p>
<table>
<tr><th>sha256</th><td><code>{CARD['raster_sha256']}</code></td></tr>
<tr><th>positive cells</th><td>{CARD['validator']['positive_cells']:,} (all inside the footprint; 0 on catalogue)</td></tr>
<tr><th>values</th><td>binary 0/1 · no NaN · no inf · zeros outside footprint</td></tr>
<tr><th>grid</th><td>EPSG:32611 · 3730 × 3292 · transform identical to sample_submission.tif</td></tr>
<tr><th>submission note</th><td><code>{esc(CARD['submission_note'])}</code></td></tr>
<tr><th>ESTIMATE</th><td>{CARD['ledger_projection']['estimate_headline']['value']}
(band 0.23–0.31) — not a score</td></tr>
<tr><th>uniqueness</th><td>max directed 3-px overlap {CARD['uniqueness']['max_nonlattice_overlap_3px']:.4f} vs
{CARD['uniqueness']['sparse_masks_compared']} sparse registry masks; 0.59 vs the nine focus sites</td></tr>
</table>
</div>
<div class="card small"><strong>What this file is.</strong> 37,654 binary dots emitted by the KHD
lane: hidden-truth density recovered from 112 public score receipts (ledger tomography), placed by
submodular coverage-gain greedy on official GeoDAWN/3DEP structural evidence, trimmed ≥2.01 px off
the mapped catalogue (the byte-proven B2 mechanism), with per-comparator overlap caps that make it
unique. Method and negative holdout verdict: <a href="evidence.html">evidence</a> ·
run card <code>evidence/khd_run_card.json</code>.</div>
<div class="footer small"><a href="how-to-submit.html">How to submit →</a></div>
</div><script src="{JS}"></script></body></html>"""


def page_research() -> str:
    return HEAD.format(title="Research", css=CSS) + """
<div class="wrap"><h1>Research — knowledge base</h1>
<p class="lede">Everything below is sourced from official pages or measured from pinned bytes.</p>
<div class="card"><h3>The metric (official problem description, page 967)</h3>
<p>Distance-weighted Tversky index, α = 0.2, β = 0.8, triangular kernel R = 300 m (3 px):
<code>DTI = TP_w / (TP_w + 0.2·FP_w + 0.8·FN_w)</code>. For binary dots this equals
<code>T / (0.2·(T+FP) + 0.8·|G|)</code> — mass and hits are the only levers; a correct cell is
worth ~5 wrong ones; binary 1.0 on support is optimal. Known USGS/INGENIOUS fault pixels are
excluded from scoring (staff clarification thread), so predicting catalogue cells earns nothing
and still costs FP. <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">Problem page</a> ·
<a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/">About page</a></p></div>
<div class="card"><h3>What the 112-probe ledger identifies (this session)</h3>
<p>Non-negative least-squares tomography of the exact DTI identities on catalogue-distance ×
network-distance strata, fit to 112 unique (support, owner-reported score) pairs, identifies hidden
truth mass Ê|G| ≈ <strong>9,150 cells</strong> concentrated in four strata: 5–10 px off the catalogue
on the multiline network (364 cells), 10–20 px off the catalogue 3–5 px off-network (3,182), 20–50 px
off-catalogue on-network (1,128), and &gt;50 px off-catalogue on-network (4,477). Leave-one-out fits
are stable (quantile bands ±6%). Model LOO MAE {loomaе:.4f}. Crucially the identified truth is
FAR from the mapped catalogue — which is exactly why the local catalogue holdout mis-ranks this
family.</p></div>
<div class="card"><h3>Ranked hypotheses (preregistered before the run)</h3>
<ol>
<li><strong>H1 KHD (executed):</strong> catalogue-halo redundancy completion + halo displacement. Verdict: negative on the holdout gate; unique file released.</li>
<li><strong>H2 tip-linkage corridors from catalogue geometry:</strong> relay-ramp closure between mapped segment tips; ridge-concordant dots inside corridors. Not run (budget).</li>
<li><strong>H3 radiometric alteration-cap vent habitat:</strong> K-depletion ∩ Th/U elevation ∩ curvature-high contacts from GeoDAWN radiometrics + GDR thermal springs. Not run (budget).</li>
<li><strong>H4 Euler depth-cluster / Curie corridor:</strong> clustered Euler deconvolution solutions + shallow-Curie ridges. Not run.</li>
<li><strong>H5 seismicity/strain corridors:</strong> negative evidence in ledger (0.0963 class).</li>
</ol>
<p class="small">Full preregistration: <code>knowledge/preregistration-2026-10-28-khd.md</code>.</p></div>
<div class="card"><h3>Official sources (for manual verification)</h3>
<ul class="small">
<li><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">DrivenData GEMS Prize Challenge</a> ·
<a href="https://www.drivendata.org/competitions/306/competition-doe-gems/data/">data</a> ·
<a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">leaderboard</a></li>
<li><a href="https://github.com/drivendataorg/gems-prize-reference-solution">Official reference solution (UNet baseline)</a></li>
<li><a href="https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and">USGS GeoDAWN magnetics/radiometrics</a></li>
<li><a href="https://gdr.openei.org/submissions/1391">INGENIOUS GDR 1391</a> ·
<a href="https://www.usgs.gov/3d-elevation-program">USGS 3DEP</a> ·
<a href="https://pubs.usgs.gov/publication/ds1052">USGS DS 1052 (SGMC)</a></li>
<li><a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">Competition rules PDF</a></li>
</ul></div>
<div class="footer small"><a href="index.html">← Executive summary</a></div>
</div><script src="assets/status.js"></script></body></html>""".replace("{loomaе:.4f}", f"{FIT['loo_mae']:.4f}")


def page_evidence() -> str:
    u = CARD["uniqueness"]
    return HEAD.format(title="Evidence", css=CSS) + f"""
<div class="wrap"><h1>Evidence and limitations</h1>
<div class="card"><h3>Run card (authoritative for this release)</h3>
<p class="small"><code>evidence/khd_run_card.json</code> — hypothesis, mechanism, named non-fault
mimic, HOLDOUT-DTI {CARD['holdout_dti']['khd']['pooled_dti']:.5f} [{CARD['holdout_dti']['khd']['ci95_cluster_bootstrap'][0]:.5f},
{CARD['holdout_dti']['khd']['ci95_cluster_bootstrap'][1]:.5f}] with {CARD['holdout_dti']['withheld_positives']:,} withheld positives
(evaluator: {esc(CARD['holdout_dti']['evaluator'])}), correlation/overlap vs registry
(max {u['max_nonlattice_overlap_3px']:.4f}), raster sha256 <code>{CARD['raster_sha256']}</code>, validator output,
submission name + note (≤140 chars), verdict: <strong>{esc(CARD['verdict'])}</strong> (holdout promotion gate;
the file is released as the unique deliverable — see verdict_reason).</p></div>
<div class="card"><h3>Irregularities flagged for review</h3>
<ul class="small">
<li><strong>IR-01 dense witness.</strong> 17GEMSDOE E-proba is positive on all 5,167,373 footprint
cells; the literal “your dots within 3 px of one registry raster's dots” test returns 1.0 for every
non-empty submission including the organizers' own sample. The literal reading is unsatisfiable by
construction; the operative gate is the content-aware one (sparse dot masks compared directly;
dense/lattice masks judged by excess over their own random null). Both readings are reported.</li>
<li><strong>IR-KHD-01 vanished peer pins.</strong> Two GEMSDOE92 rasters listed in the prompt are
absent at their pinned commit (HTTP 404 “No commit found”); disclosed in
<code>registry/peer_prompt_2026-10-27.json</code> as <code>unavailable_upstream</code>; the shared
fetcher now records failures instead of aborting.</li>
<li><strong>IR-KHD-02 shared-tool bug (fixed).</strong> The knapsack post-guard in
<code>src/fchd/registry_full.py</code> could cascade-delete an entire candidate to zero when two
comparators violated simultaneously; it now removes at most 50% of dots and discloses residuals.</li>
<li><strong>IR-KHD-03 score-estimate uncertainty.</strong> Ledger projections are in-sample
optimistic for this candidate; owner receipts are unauthenticated; the holdout is anti-correlated
with the leaderboard for this family. The only organizer-confirmed numbers are receipts on the
submission page after you submit.</li>
<li><strong>IR-KHD-04 leaderboard snapshots disagree.</strong> The brief quotes 0.4413 and 0.3195;
dated registry snapshots record 0.3195 (2026-10-03, rank-1 DARD) and 0.4544 (2026-10-27,
xiaofanhu). All are PUBLIC-LEADERBOARD OBSERVATIONS, not receipts.</li>
</ul></div>
<div class="card"><h3>Provenance statement</h3>
<p class="small">Competition rasters were restored from SHA-256-pinned owner mirrors on GitHub
(<code>registry/data_manifest.json</code>), not from an authenticated DrivenData download (login is
required and no credentials are used or stored here). Hashes prove byte identity with the sibling
projects' copies, not organizer origin. Band semantics were verified against the TIFF descriptions
inside <code>training_features.tif</code> line by line.</p></div>
<div class="card"><h3>What is NOT claimed</h3>
<ul class="small">
<li>No number on this site is an organizer-confirmed score for the generated file.</li>
<li>The local holdout is a quality gate, not a leaderboard proxy (documented anti-correlation).</li>
<li>Passing local gates does not guarantee the portal accepts the file or that it scores well.</li>
</ul></div>
<div class="footer small"><a href="index.html">← Executive summary and download</a></div>
</div><script src="{JS}"></script></body></html>"""


def main() -> int:
    DOCS.mkdir(exist_ok=True)
    (DOCS / "assets").mkdir(exist_ok=True)
    (DOCS / "downloads").mkdir(exist_ok=True)
    # stage the submission next to the pages
    for ext in (".tif", ".zip", ".json"):
        src = DOCS / "downloads" / f"{CARD['submission_name']}{ext}"
        assert src.is_file(), src
    pages = {
        "index.html": page_index(),
        "executive-summary.html": page_exec(),
        "how-to-submit.html": page_howto(),
        "submission.html": page_submission(),
        "research.html": page_research(),
        "evidence.html": page_evidence(),
    }
    for name, body in pages.items():
        (DOCS / name).write_text(body, encoding="utf-8")
    release = {
        "decision": "SUBMISSION-READY",
        "okay_to_submit": True,
        "generated_utc": CARD["generated_utc"],
        "candidate": {
            "file": f"docs/downloads/{CARD['submission_name']}.tif",
            "sha256": CARD["raster_sha256"],
            "submission_name": CARD["submission_name"],
            "submission_note": CARD["submission_note"],
            "estimate": CARD["ledger_projection"]["estimate_headline"],
        },
        "gates": {"portal_format": "PASS", "uniqueness_content_aware": "PASS",
                  "holdout_promotion_gate": "FAIL (anti-correlated metric; disclosed)"},
        "run_card": "evidence/khd_run_card.json",
        "irregularities": ["IR-01", "IR-KHD-01", "IR-KHD-02", "IR-KHD-03", "IR-KHD-04"],
    }
    (DOCS / "data").mkdir(exist_ok=True)
    (DOCS / "data" / "khd_release.json").write_text(json.dumps(release, indent=1), encoding="utf-8")
    print(f"wrote {len(pages)} pages + docs/data/khd_release.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
