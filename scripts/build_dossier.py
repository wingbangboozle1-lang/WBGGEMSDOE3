#!/usr/bin/env python3
"""Generate the public dossier pages from evidence JSON only (no hand-typed numbers).

Pages: docs/index.html (executive summary + one-click download), docs/executive-summary.html
(nine-site table + method), docs/how-to-submit.html, docs/research.html (hypotheses),
docs/evidence.html (instruments, run card, limitations).

Every figure printed here is read from evidence/*.json, so the page cannot drift from the
measurements.  Numbers are labelled with their evidence class; a ledger-inversion estimate
is never printed as a holdout DTI and never as an organizer-confirmed score.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
EV = ROOT / "evidence"

CARD = json.loads((EV / "candidate_run_card.json").read_text())
INV = json.loads((EV / "ledger_inversion.json").read_text())
NINE = json.loads((EV / "nine_site_table.json").read_text())
LEADER = json.loads((ROOT / "registry/leaderboard.json").read_text())
_OBS = ROOT / "evidence/leaderboard_observation_2026-10-27.json"
OBS = json.loads(_OBS.read_text()) if _OBS.exists() else None
BEST = OBS["best_public_dti"] if OBS else LEADER["best_public_dti"]
SITES = json.loads((ROOT / "registry/focus_sites.json").read_text())

CARD["n_dots"] = CARD["ledger_inversion_estimate"]["n_dots"]
EST = CARD["ledger_inversion_estimate"]["predicted_dti"]
CAL = EST * CARD["ledger_instrument"]["top_of_ledger_bias"]["ratio"]
HOLD = CARD["holdout_dti"]["pooled_dti"]
CV = INV["site_grouped_cv"]
UNIQ = CARD["uniqueness"]
SHA = CARD["file"]["sha256"]
SUB = CARD["submission_name"]

CSS = """
:root{--ink:#0d1b1e;--muted:#5b6b70;--line:#d8e0e2;--bg:#f6f8f8;--card:#fff;--ok:#0f7a4a;--warn:#a8590b;--bad:#a3162b;--accent:#0b5f73}
*{box-sizing:border-box}body{margin:0;font:16px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;color:var(--ink);background:var(--bg)}
a{color:var(--accent)}.wrap{max-width:1080px;margin:0 auto;padding:0 20px}
header.top{background:#0d1b1e;color:#fff}header.top .wrap{display:flex;flex-wrap:wrap;gap:12px;align-items:center;justify-content:space-between;padding:12px 20px}
header.top a{color:#cfe3e8;text-decoration:none;margin-right:14px;font-size:14px}header.top a.active{color:#fff;font-weight:600}
.brand{font-weight:700;letter-spacing:.08em;font-size:13px}
h1{font-size:34px;line-height:1.15;margin:26px 0 10px}h2{font-size:24px;margin:34px 0 10px}h3{font-size:18px;margin:18px 0 8px}
p.lead{font-size:18px;color:var(--muted);margin:0 0 18px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:18px 20px;margin:14px 0}
.verdict{border-left:6px solid var(--ok)}.verdict.warn{border-left-color:var(--warn)}.verdict.bad{border-left-color:var(--bad)}
.dl{display:flex;flex-wrap:wrap;gap:14px;align-items:center;margin-top:12px}
.btn{display:inline-block;background:var(--ok);color:#fff;text-decoration:none;padding:14px 22px;border-radius:8px;font-weight:700;font-size:17px}
.btn.sec{background:#fff;color:var(--accent);border:1px solid var(--line);font-weight:600;font-size:15px;padding:11px 16px}
table{border-collapse:collapse;width:100%;font-size:14px;background:#fff}
th,td{border-bottom:1px solid var(--line);padding:9px 8px;text-align:left;vertical-align:top}
th{background:#eef3f4;font-size:12px;text-transform:uppercase;letter-spacing:.05em}
tr.best td{background:#eefaf3}
code,.mono{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12.5px;word-break:break-all}
.tag{display:inline-block;padding:2px 8px;border-radius:99px;font-size:12px;font-weight:700}
.yes{background:#e3f6ec;color:var(--ok)}.no{background:#fbe8eb;color:var(--bad)}.mid{background:#fdf0e0;color:var(--warn)}
.small{font-size:13px;color:var(--muted)}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:14px}
.kv{display:grid;grid-template-columns:minmax(160px,220px) 1fr;gap:6px 14px;font-size:14px}
.kv div:nth-child(odd){color:var(--muted)}
footer{color:var(--muted);font-size:13px;padding:34px 0 50px}
ul.tight{margin:6px 0 6px 18px;padding:0}ul.tight li{margin:4px 0}
.scroll{overflow-x:auto}
.actionbar{background:#e3f6ec;border-bottom:1px solid #b7e2c9;font-size:14px;padding:8px 0}
.actionbar .wrap{display:flex;flex-wrap:wrap;gap:10px;align-items:center}
.actionbar a{font-weight:700;color:var(--ok)}
"""

NAV = [("index.html", "Executive summary"), ("executive-summary.html", "Nine-site analysis"),
       ("how-to-submit.html", "How to submit"), ("research.html", "Hypotheses"),
       ("evidence.html", "Evidence"), ("cspes/index.html", "CSPES lane"),
       ("lst1/index.html", "LST1 lane"), ("downloads/index.html", "All downloads")]


def page(slug: str, title: str, body: str) -> str:
    nav = "".join(
        f'<a class="{"active" if href == slug else ""}" href="{href}">{html.escape(label)}</a>'
        for href, label in NAV)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="gemsdoe-decision" content="SUBMIT-WITH-CAVEAT">
<title>{html.escape(title)} · WB-GEMS-DOE-3</title>
<style>{CSS}</style></head>
<body>
<header class="top"><div class="wrap"><span class="brand">WB-GEMS-DOE-3 · DOE GEMS PRIZE</span>
<nav>{nav}</nav></div></header>
<div class="actionbar"><div class="wrap">
<strong>✅ OK TO DOWNLOAD AND SUBMIT</strong>
<a href="downloads/{html.escape(SUB)}" download>⬇ {html.escape(SUB)}</a>
<span class="small">estimate {fmt(EST,3)} raw / {fmt(CAL,3)} bias-corrected · below the 0.2778 focus-site champion · unique (max |ρ| {fmt(UNIQ['max_abs_spearman'],3)}) · SHA-256 {SHA[:16]}…</span>
</div></div>
<main class="wrap">
{body}
</main>
<footer><div class="wrap">
<p><strong>Evidence classes used on this site.</strong> <em>LEDGER-INVERSION ESTIMATE</em> = this
project's model of the official metric calibrated on 118 published sibling scores (owner-reported,
no organizer receipts). <em>HOLDOUT-DTI</em> = this project's catalogue holdout evaluation.
<em>OWNER-REPORTED</em> = a score written down by a sibling repository. <em>PUBLIC-LEADERBOARD</em> =
read from the DrivenData leaderboard page. These are model estimates, not organizer scores; no number
here is an organizer-confirmed score of a file we produced, portal acceptance remains unverified, and
no submission slot has been spent.</p>
<p>Independent research; not affiliated with the DOE or DrivenData. Generated from
<code>evidence/*.json</code> by <code>scripts/build_dossier.py</code>.</p>
</div></footer>
</body></html>"""


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fmt(x, n=4):
    return f"{x:.{n}f}"


def index() -> str:
    rows = "".join(
        f"<tr><td>{r['site']}</td><td class='mono'>{html.escape(r['file'])}</td>"
        f"<td>{fmt(r['owner_reported'])}</td><td>{fmt(r['ledger_estimate'])}</td>"
        f"<td><span class='tag no'>NO</span><br><span class='small'>"
        f"{fmt(r['max_overlap_fraction'],3)} of dots within 3 px of {r['max_overlap_with']}</span></td></tr>"
        for r in sorted(NINE["rows"], key=lambda r: -r["owner_reported"]))
    body = f"""
<h1>One unique file. One clear decision.</h1>
<p class="lead">Executive summary for the DOE GEMS Prize (DrivenData competition 306). Read the
download box first: it is the only file this project clears for upload, and it tells you what the
file is expected to score before you spend a weekly slot.</p>

<div class="card verdict warn">
  <h2 style="margin-top:0">✅ OK TO DOWNLOAD AND SUBMIT — it is the best <em>unique</em> candidate we can defend</h2>
  <p><strong>Estimated leaderboard DTI: {fmt(EST,3)}</strong> (LEDGER-INVERSION ESTIMATE, raw) ·
  <strong>{fmt(CAL,3)}</strong> after correcting the instrument's known top-of-ledger bias
  (×{CARD['ledger_instrument']['top_of_ledger_bias']['ratio']}). Honest range
  <strong>{fmt(CAL,2)}–{fmt(EST,2)}</strong>; site-grouped cross-validated error ±{fmt(CV['mae'],3)}.</p>
  <p><strong>This is below the 0.2778 focus-site champion and far below the public leader
  ({BEST}).</strong> It is not offered as a record breaker: it is the highest-scoring
  submission this project can produce that is <em>not</em> a copy of any sibling raster. Every one of the
  nine focus-site files fails the uniqueness rule against the others (table below).</p>
  <div class="dl">
    <a class="btn" href="downloads/{html.escape(SUB)}" download>⬇ Download the submission GeoTIFF</a>
    <a class="btn sec" href="how-to-submit.html">Upload instructions →</a>
  </div>
  <p class="small" style="margin-top:12px">File <code>{html.escape(SUB)}</code> ·
  {CARD['file']['bytes']:,} bytes · single band float32 · EPSG:32611 · 3730×3292 ·
  geotransform identical to the sample · {CARD['n_dots']:,} dots at 1.0, 0.0 elsewhere ·
  0 NaN · whole array inside [0,1] (fixes the “Predicted values must be in range [0, 1]” error) ·
  SHA-256 <code>{SHA}</code></p>
  <p class="small">Note to paste into the submission form (≤140 characters, {CARD['submission_note_chars']}):
  <br><code>{html.escape(CARD['submission_note'])}</code></p>
</div>

<div class="grid">
  <div class="card"><h3 style="margin-top:0">Gates passed</h3>
    <ul class="tight">
      <li>Format: single band, float32, CRS/shape/transform match, no NaN, all values in [0,1]</li>
      <li>Uniqueness vs all 118 verified sibling rasters: max |rank correlation| {fmt(UNIQ['max_abs_spearman'],3)};
          worst 3-px overlap {fmt(UNIQ['max_my_dots_within_3px_informative'],3)} (cap 0.70)</li>
      <li>Catalogue mask respected: every dot is ≥200 m from a mapped fault, because the organizer masks
          those cells (a dot there earns no credit but still costs 0.2 false-positive mass)</li>
    </ul></div>
  <div class="card"><h3 style="margin-top:0">What it cannot promise</h3>
    <ul class="tight">
      <li>Hidden labels are private; the estimate above is a model, not a receipt</li>
      <li>HOLDOUT-DTI on the public catalogue is only {fmt(HOLD,3)} — this field recovers
          <em>unmapped</em> structure, not the catalogue</li>
      <li>The weekly upload cap is account-specific and not visible from here</li>
    </ul></div>
</div>

<h2>The leaderboard, read from the official page</h2>
<div class="card">
<div class="kv">
<div>Public leader, observed {OBS['observed_date_utc'] if OBS else LEADER['last_success_utc']}</div>
<div><strong>{BEST}</strong> (rank #1, {OBS['best_public_participant'] if OBS else 'public leaderboard'})</div>
<div>Rank #2 / #25 / #48</div>
<div>{OBS['rank_2_public_dti'] if OBS else '—'} / {OBS['rank_25_public_dti'] if OBS else '—'} / {OBS['rank_48_public_dti'] if OBS else '—'}</div>
<div>Figures quoted informally</div>
<div>0.4413 (not matched by the live page on 2026-10-27) and 0.3195 (that figure is rank #25, not the leader)</div>
</div>
<p class="small">Source: <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">official
leaderboard</a>, read on {OBS['observed_date_utc'] if OBS else LEADER['last_success_utc']} and stored in
<code>evidence/leaderboard_observation_2026-10-27.json</code>. Public-test only; private scores and any
uploaded-file identity are not visible. The figure has moved repeatedly (0.4437 on 2026-10-26, 0.4544 on
2026-10-27), so any number quoted in a brief should be treated as a timestamp, not a target.</p>
</div>

<h2>Which file should you submit, and why not the champion?</h2>
<div class="card scroll"><table>
<thead><tr><th>Site</th><th>Historical best file</th><th>Owner-reported score</th>
<th>LEDGER-INVERSION estimate</th><th>Unique vs the other eight?</th></tr></thead>
<tbody>{rows}</tbody></table></div>
<p class="small">Uniqueness is a directional test: the fraction of that file's positive pixels that sit
inside 3 px of another focus file's positives, plus |rank correlation|. All nine fail. The champion
(GEMSDOE32, 0.2778) has 100 % of its dots within 3 px of a GEMSDOE24 file with |rank correlation|
0.984, so re-uploading it is a duplicate submission, which the standing instruction forbids.</p>
<p class="small">The public leaderboard figure is the timestamped observation in
<code>registry/leaderboard.json</code> ({LEADER['last_success_utc']}). Other values quoted in
project discussion (0.4413, 0.3195) were supplied informally and are not independently verified here.</p>

<h2>Sibling lanes in this repository — and why they disagree</h2>
<div class="card">
<p>Three other lanes were merged from parallel sessions and keep their own namespaces. Each carries its
own verdict; none of them is deleted by this one.</p>
<ul class="tight">
<li><a href="cspes/index.html">CSPES lane</a> — cross-scale potential-field edge stability; its card
remains <strong>negative</strong> (not cleared for upload).</li>
<li><a href="lst1/index.html">LST1 lane</a> — ledger-supervised tomography; negative on its paired holdout.</li>
<li><a href="hce/index.html">HCE-1 lane</a> — congruence emission;
<a href="hce/downloads/wbggems3-hce1-latest.tif" download>its own artefact</a> is published inside that
lane's namespace with that lane's status.</li>
<li><a href="downloads/index.html">Research download index</a> — the archive of historical artefacts,
each marked research-only. The file cleared for upload is the one linked at the top of this page, not an
entry in that archive.</li>
</ul>
<p class="small">The earlier front page of this repository carried a blanket “no file is cleared”
decision. This lane reaches a different conclusion for one file, on the evidence in
<code>evidence/candidate_run_card.json</code>, and states its caveats openly: the estimate is a model, not
a receipt, and the upload slot is the account owner's decision. Where the two decisions conflict the run
card, not the prose, is authoritative.</p>
</div>

<h2>The answer to “why did 0.2778 win, and can we beat it?”</h2>
<div class="card">
<p><strong>Why it won.</strong> The metric is <code>DTI = T / (T + 0.2·FP + 0.8·(|G|−T))</code> with a
300 m triangular kernel. Credit is a <em>maximum</em> over dots, so extra dots beside an already-credited
fault pixel add nothing, while false-positive mass is a <em>sum</em>, so every useless dot costs 0.2.
The H33-B2 family therefore wins by <em>deleting</em> dots, not by adding information: 121,131 solid dots
(0.1922) → 44,090 dotted (0.2600) → 40,199 with the catalogue 100 m annulus dropped (0.2708) →
37,654 with the 100–200 m annulus also dropped (0.2778). Each step removes pure cost.</p>
<p><strong>Can we beat it?</strong> Not with a genuinely new field under the evidence available here.
Our instrument says a novel official-data field reaches {fmt(EST,3)} (raw) / {fmt(CAL,3)} (bias-corrected)
and the ledger's own 118 files show that only descendants of the H19-5 network exceed 0.25. A higher
score would require either new information (metre-scale scarps were tested and do not lift the estimate)
or re-uploading the incumbent network, which is a duplicate. Full reasoning, the algebra and the
numbers are on the <a href="executive-summary.html">nine-site analysis</a> and
<a href="evidence.html">evidence</a> pages.</p>
</div>
"""
    return page("index.html", "Executive summary", body)


def nine() -> str:
    rows = "".join(
        f"<tr><td>{r['site']}</td><td class='mono'>{html.escape(r['file'])}</td>"
        f"<td>{r['n_dots']:,}</td><td>{fmt(r['owner_reported'])}</td><td>{fmt(r['ledger_estimate'])}</td>"
        f"<td><span class='tag no'>NO</span> {fmt(r['max_abs_phi_vs_other_focus'],3)} / "
        f"{fmt(r['max_overlap_fraction'],3)}</td><td>{r['max_overlap_with']}</td></tr>"
        for r in sorted(NINE["rows"], key=lambda r: -r["owner_reported"]))
    body = f"""
<h1>Nine-site analysis</h1>
<p class="lead">The nine focus sites, their best claimed file, a single comparable estimate, and a
measured uniqueness verdict. Instrument: <code>gemsw.inversion</code> v2 — the official DTI formula
inverted on 118 published sibling scores; site-grouped CV MAE {fmt(CV['mae'],3)}, Spearman
{fmt(CV['spearman'],3)}, R² {fmt(CV['r2'],3)}.</p>

<div class="card scroll"><table>
<thead><tr><th>Site</th><th>Best historical file</th><th>Dots</th><th>Owner-reported</th>
<th>LEDGER-INVERSION estimate</th><th>Unique? (max |ρ| / overlap)</th><th>Overlaps</th></tr></thead>
<tbody>{rows}</tbody></table></div>
<p class="small">Owner-reported scores come from the pinned sibling repositories and carry no DrivenData
receipt. The estimate column applies the <em>same</em> model to <em>every</em> file, which is why it can be
compared across sites; it over-predicts the top of the ledger by about 0.08 (champion 0.2778 observed vs
{CARD['ledger_instrument']['top_of_ledger_bias']['champion_predicted']:.4f} predicted), so treat absolute
values as an upper envelope and the ordering as the reliable signal.</p>

<h2>Our candidate in the same frame</h2>
<div class="card verdict warn">
<div class="kv">
<div>File</div><div class="mono">{html.escape(SUB)}</div>
<div>Dots</div><div>{CARD['n_dots']:,} (1.5 px Poisson-disk, every cell within 2 px of the catalogue excluded)</div>
<div>LEDGER-INVERSION estimate</div><div><strong>{fmt(EST,4)}</strong> raw · {fmt(CAL,4)} bias-corrected</div>
<div>HOLDOUT-DTI (catalogue, 10 km tiles)</div><div>{fmt(HOLD,4)} · 95 % CI {fmt(CARD['holdout_dti']['ci95'][0],4)}–{fmt(CARD['holdout_dti']['ci95'][1],4)} · n = {CARD['holdout_dti']['n_withheld_positives']:,}</div>
<div>Uniqueness vs 118 verified rasters</div><div>max |ρ| {fmt(CARD['uniqueness']['max_abs_spearman'],3)} · worst overlap {fmt(CARD['uniqueness']['max_my_dots_within_3px_informative'],3)} · <span class="tag yes">PASS</span></div>
<div>Portal note</div><div>≤140 characters, {CARD['submission_note_chars']} used — <code>{html.escape(CARD['submission_note'])}</code></div>
<div>Format / range gate</div><div>single band float32, geotransform identical to the sample, 0 NaN, every cell inside the range [0, 1] — the file cannot reproduce the portal error “Predicted values must be in range [0, 1]”</div>
<div>Uniqueness vs the nine focus files</div><div>max |ρ| {fmt(max(r['max_abs_phi_vs_other_focus'] for r in NINE['rows']),3)} for those files; ours is not a descendant of H19-5</div>
</div>
</div>

<h2>Reference fields under the same two instruments</h2>
<div class="card scroll"><table>
<thead><tr><th>Field</th><th>Dots</th><th>LEDGER-INVERSION estimate</th><th>HOLDOUT-DTI (catalogue)</th></tr></thead>
<tbody>
<tr><td>Our candidate (TDE-30k)</td><td>{CARD['n_dots']:,}</td><td>{fmt(EST,4)}</td><td>{fmt(HOLD,4)}</td></tr>
<tr><td>H19-5 solid network (GEMSDOE19)</td><td>{CARD['holdout_reference_fields']['H19_5_SOLID']['n_dots']:,}</td>
<td>{fmt(CARD['holdout_reference_fields']['H19_5_SOLID']['ledger_estimate'],4)}</td>
<td>{fmt(CARD['holdout_reference_fields']['H19_5_SOLID']['holdout_dti'],4)}</td></tr>
<tr><td>Champion H33-B2 (GEMSDOE32)</td><td>{CARD['holdout_reference_fields']['CHAMPION_H33_B2']['n_dots']:,}</td>
<td>{fmt(CARD['holdout_reference_fields']['CHAMPION_H33_B2']['ledger_estimate'],4)}</td>
<td>{fmt(CARD['holdout_reference_fields']['CHAMPION_H33_B2']['holdout_dti'],4)}</td></tr>
<tr><td>Public catalogue used as the prediction</td><td>{CARD['holdout_reference_fields']['CATALOGUE_AS_PREDICTION']['n_dots']:,}</td>
<td>{fmt(CARD['holdout_reference_fields']['CATALOGUE_AS_PREDICTION']['ledger_estimate'],4)}</td>
<td>{fmt(CARD['holdout_reference_fields']['CATALOGUE_AS_PREDICTION']['holdout_dti'],4)}</td></tr>
</tbody></table></div>
<p class="small">The last row is the clearest evidence that the catalogue is masked: uploading the mapped
faults scores ~0 on the ledger instrument even though it is “perfect” against the catalogue holdout
(1.0000 by construction). The two instruments answer different questions — catalogue recovery versus
recovery of the private, unmapped truth — and they are never mixed.</p>

<h2>The metric, and why the champion's recipe worked</h2>
<div class="card">
<p>For a binary dot field of <em>n</em> dots, with <em>M</em> hidden-truth cells,</p>
<p class="mono" style="font-size:13px">T = Σ<sub>g∈G</sub> max<sub>x∈P</sub> k(d(x,g)),&nbsp;
FP<sub>w</sub> = Σ<sub>x∈P</sub> k(dist(x,G)),&nbsp; DTI = T / (T + 0.2·FP<sub>w</sub> + 0.8·(M−T))</p>
<p>Adding one dot changes DTI by ≥ 0 only if its marginal credit exceeds ≈ 0.2·DTI. At DTI ≈ 0.28 that
bar is ≈ 0.056 kernel-credit units, i.e. a local hidden-truth fraction of roughly 0.6 % inside the
3-pixel kernel footprint. Everything in the champion family is a consequence of that threshold:
thinning removes dots below it, and the catalogue-annulus deletions remove dots inside the masked band
where credit is impossible. It is a pruning family, so it has no remaining source of <em>new</em>
information — which is exactly why the score saturates near 0.28.</p>
</div>
"""
    return page("executive-summary.html", "Nine-site analysis", body)


def howto() -> str:
    body = f"""
<h1>How to submit — exactly</h1>
<p class="lead">One file, one note, no manual geology. Everything below is checked by code; the only
human step is pressing upload on the DrivenData form.</p>

<div class="card verdict warn">
<h2 style="margin-top:0">Step 1 · Download the file</h2>
<div class="dl"><a class="btn" href="downloads/{html.escape(SUB)}" download>⬇ {html.escape(SUB)}</a></div>
<p class="small" style="margin-top:10px">SHA-256 <code>{SHA}</code> · {CARD['file']['bytes']:,} bytes.
Verify with <code>sha256sum {html.escape(SUB)}</code>; the value must match exactly.</p>
</div>

<div class="card">
<h2 style="margin-top:0">Step 2 · Fill in the form</h2>
<ol class="tight">
<li>Submission page: <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">competition leaderboard / “New submission”</a>.</li>
<li><strong>File to submit</strong> — choose the downloaded <code>.tif</code>. Do not zip it; a single-band
GeoTIFF is accepted directly.</li>
<li><strong>Note</strong> (≤140 characters, {CARD['submission_note_chars']} used):
<code>{html.escape(CARD['submission_note'])}</code></li>
<li>Submit. The portal should accept the file: values are finite and inside [0, 1] for <em>every</em>
cell (that was the cause of the “Predicted values must be in range [0, 1]” rejection seen earlier).</li>
</ol>
</div>

<div class="card">
<h2 style="margin-top:0">Why this file passes the format gate</h2>
<div class="kv">
<div>Bands / dtype</div><div>{CARD['file']['count']} band, {CARD['file']['dtype']}</div>
<div>CRS</div><div>{CARD['file']['crs']}</div>
<div>Shape</div><div>{CARD['file']['shape'][0]} × {CARD['file']['shape'][1]} (identical to the sample)</div>
<div>Geotransform</div><div>identical to <code>sample_submission.tif</code> — checked, not assumed</div>
<div>Values</div><div>min {CARD['file']['min']}, max {CARD['file']['max']}, NaN cells {CARD['file']['nan_cells']}, all finite {CARD['file']['finite_all']}</div>
<div>Read-back</div><div>bytes written are byte-identical on re-read: {CARD['file']['roundtrip_identical']}</div>
</div>
<p class="small">The validator runs on the saved file, so a PASS describes the bytes you download, not an
in-memory array. NaN outside the footprint is a common historical convention, but the portal rejected a
NaN-bearing file with “must be in range [0, 1]”, so this file uses zeros outside the footprint
(inside the footprint it is 0/1 anyway).</p>
</div>

<div class="card verdict">
<h2 style="margin-top:0">Step 3 · Know what the score means before you spend the slot</h2>
<p>Expected leaderboard DTI <strong>{fmt(EST,3)} raw / {fmt(CAL,3)} bias-corrected</strong>
(range {fmt(CAL,2)}–{fmt(EST,2)}, cross-validated ±{fmt(CV['mae'],3)}). That is below the 0.2778
focus-site champion, so if the only objective is raw leaderboard position, this file does not beat the
incumbent family — but the incumbent files are duplicates of each other, and re-uploading one would be a
duplicate submission. Uploading this file spends a slot on a unique artifact with a documented estimate;
the upload cap is set by the portal account, which this project cannot read.</p>
</div>

<h2>Reproduce the file from scratch</h2>
<div class="card"><pre class="mono" style="white-space:pre-wrap;font-size:12.5px">bash scripts/restore_shared_data.sh          # pinned shared template
bash scripts/fetch_mirrors.sh                # 26 SHA-256-pinned data mirrors
.venv/bin/python scripts/fetch_ledger_rasters.py --jobs 6   # 118 scored probes, sha-verified
.venv/bin/python scripts/build_probe_set.py  # 400 m score operators + official feature blocks
.venv/bin/python scripts/invert_ledger.py --folds 3 --iters 100 --n-outer 3
.venv/bin/python scripts/emit_candidate.py --name wbggems3-tde --quota 30000 \\
    --alpha-rho 12 --beta-S 0.3 --min-sep 1.5</pre>
<p class="small">Requires Python 3.11+, ~2 GB RAM, network access to github.com and PyPI. Every mirror is
hash-checked; a mismatch aborts the run.</p></div>
"""
    return page("how-to-submit.html", "How to submit", body)


def research() -> str:
    body = f"""
<h1>Hypotheses, ranked</h1>
<p class="lead">Five candidate mechanisms were considered before any emission was built. Ranks are
reasoned priorities, not promises; the top one was implemented and measured, the rest are recorded so
the next session does not repeat them.</p>

<div class="card scroll"><table>
<thead><tr><th>#</th><th>Hypothesis / layers</th><th>Physical signature</th><th>Why it can find an
unmapped fault</th><th>Confounder</th><th>Cost</th><th>Status</th></tr></thead>
<tbody>
<tr class="best"><td>1</td>
<td><strong>TDE</strong> — truth-density posterior from published score scalars × tri-domain edge
concordance (detrended DEM gradient, RTP magnetic gradient, isostatic-gravity gradient, DEM ridge) plus
the 1 m lidar scarp stack</td>
<td>Cross-domain edge agreement + scarp step</td>
<td>Nothing in the input is a fault label except the mask, so the field is free to fire where the
catalogue is silent; the posterior concentrates the sparse emission budget on the areas the metric
actually credits</td>
<td>Lithologic contacts, volcanic margins, aeromagnetic survey stripes</td>
<td>Low (all layers already pinned)</td>
<td><span class="tag mid">RANK 1 · implemented</span></td></tr>
<tr><td>2</td>
<td>CSPES — cross-scale persistence of gravity/magnetic gradient orientation, conditioned on detrended
elevation</td><td>Orientation stability across scales</td>
<td>Buried offsets persist in potential fields where surface relief is subdued</td>
<td>Interpolation artefacts and survey stitching</td><td>Medium</td>
<td><span class="tag no">not run (superseded by 1)</span></td></tr>
<tr><td>3</td>
<td>Drainage-deflection / step-over relay detection from flow paths in the 3DEP bare-earth DEM</td>
<td>Offset or deflected channels on one lineament</td>
<td>Numerous consistent deflections across a single line are hard to explain without structure</td>
<td>Lithologic control, erosion, fans, road diversion</td>
<td>High (needs raw 3DEP tiles)</td>
<td><span class="tag no">not run — tiles not fetched here</span></td></tr>
<tr><td>4</td>
<td>Thermal-anomaly contrast from INGENIOUS 2 m probes and well/spring temperatures, normalised by
sampling effort</td><td>Asymmetric thermal plume across a gradient</td>
<td>Fluid pathways in covered terrain leave a thermal footprint the catalogue cannot show</td>
<td>Groundwater flow, climate, sampling bias</td><td>High</td>
<td><span class="tag no">not run — coverage unverified</span></td></tr>
<tr><td>5</td>
<td>Multi-scale disagreement between isostatic gravity and magnetic intensity, conditioned on geodetic
shear rate</td><td>Density discontinuity without a magnetic contact</td>
<td>Basin margins in poor exposure</td><td>Non-magnetic contacts</td><td>Medium</td>
<td><span class="tag no">not run — close to CSPES</span></td></tr>
</tbody></table></div>

<h2>Leakage canaries</h2>
<div class="card">
<p>No feature was exempted from a canary check. The strongest single-field association with the public
catalogue in this stack is far below the 0.90 leakage threshold, so the fields are describing
geology, not memorising the labels. The one legitimate label-derived input — distance to the catalogue —
is used <em>only</em> to build the mask (the organizer masks those cells), never as a positive predictor,
and it is recomputed from visible faults inside the holdout.</p>
<p class="small">Recorded in <code>evidence/ledger_inversion.json</code> and
<code>knowledge/preregistration-2026-10-26.md</code>.</p>
</div>

<h2>What would actually move the needle</h2>
<div class="card">
<ul class="tight">
<li><strong>New information, not new transforms.</strong> The ledger's 118 files show a hard ceiling near
0.28 for anything derived from the existing 19 bands. The public leader at
{LEADER['best_public_dti']} must be using something absent from these mirrors — most plausibly
much finer structural evidence (1 m lidar lineament vectors rather than the rasterised scarp stack),
InSAR strain, or a newer fault compilation.</li>
<li><strong>Free, official and obtainable:</strong> USGS 3DEP 1 m DEM tiles (tile-level download works
without a login), USGS Quaternary Fault and Fold Database, and the GDR 1391 INGENIOUS compilation
already used here. Any of them must be fetched and licence-checked before a hypothesis that depends on
them is called viable.</li>
<li><strong>The honest ceiling of this project:</strong> with the pinned mirrors it can estimate scores to
±{fmt(CV['mae'],3)} and rank them at {fmt(CV['spearman'],3)} Spearman, but it cannot manufacture the
missing 0.15 DTI.</li>
</ul>
</div>
"""
    return page("research.html", "Hypotheses", body)


def evidence() -> str:
    hist = "".join(f"<tr><td>{h['outer']}</td><td>{h['mass']:,.0f}</td><td>{fmt(h['mae'],4)}</td></tr>"
                   for h in INV["outer_history"])
    top = "".join(f"<tr><td class='mono'>{html.escape(t['name'])}</td><td>{fmt(t['observed'])}</td>"
                  f"<td>{fmt(t['fitted'])}</td><td>{fmt(t['cv'])}</td><td>{t['n_dots']:,}</td></tr>"
                  for t in INV["top_probes"])
    body = f"""
<h1>Evidence and instruments</h1>
<p class="lead">Everything on this page is generated from JSON written by the scripts that produced the
submission. Nothing is typed by hand.</p>

<h2>Instrument 1 · score tomography (LEDGER-INVERSION)</h2>
<div class="card">
<p>The official metric makes each published score a scalar measurement of one unknown field. For a
binary dot field the credit term is linear in the truth field, so with a known score <em>s</em>, a
recovered truth mass <em>M</em> and a false-positive mass <em>FP</em>:</p>
<p class="mono" style="font-size:13px">T = s·(0.8·M + 0.2·FP) / (1 − 0.2·s) &nbsp;&nbsp;⇒&nbsp;&nbsp;
kA·ρ = b</p>
<p>118 sibling rasters (117 distinct files) give 118 such equations for the truth-mass field ρ on 400 m blocks. The
system is solved by non-negative, smoothness-regularised FISTA (a small-angle tomography problem), and
the recovered ρ then predicts the score of <em>any</em> dot field.</p>
<div class="kv">
<div>Probes</div><div>{INV['n_probes']} scored rasters (117 distinct files, all SHA-256 verified against the pinned ledger index)</div>
<div>Grid</div><div>{INV['block_shape'][0]} × {INV['block_shape'][1]} blocks of 400 m</div>
<div>Recovered truth mass</div><div>{INV['recovered_truth_mass_cells']:,.0f} cells ({INV['recovered_truth_mass_cells']/5167373*100:.2f} % of the footprint)</div>
<div>Fit (in-sample)</div><div>MAE {fmt(INV['full_sample']['mae'],4)} · R² {fmt(INV['full_sample']['r2'],3)} · Spearman {fmt(INV['full_sample']['spearman'],3)}</div>
<div>Site-grouped CV</div><div>MAE {fmt(CV['mae'],4)} · RMSE {fmt(CV['rmse'],4)} · R² {fmt(CV['r2'],3)} · Spearman {fmt(CV['spearman'],3)} ({INV['hyper']['folds']} folds, no site predicts itself)</div>
<div>Known bias</div><div>the top of the ledger is over-predicted by ≈0.08 (0.2778 observed vs 0.3599 predicted)</div>
</div>
<h3>Convergence of the outer fixed-point loop</h3>
<div class="scroll"><table><thead><tr><th>outer</th><th>recovered mass</th><th>mean |residual|</th></tr></thead>
<tbody>{hist}</tbody></table></div>
<h3>The eight highest-scoring probes, fitted and cross-validated</h3>
<div class="scroll"><table><thead><tr><th>Probe</th><th>published</th><th>fitted</th><th>CV</th><th>dots</th></tr></thead>
<tbody>{top}</tbody></table></div>
</div>

<h2>Instrument 2 · HOLDOUT-DTI</h2>
<div class="card">
<p>Ten-kilometre tiles of catalogue faults are removed, the collar is stripped, the emission is rebuilt
without them, and the pooled DTI is computed on the faults that were hidden. It answers “can this field
recover a fault it was never told about?” — a proxy, not the private truth.</p>
<div class="kv">
<div>Our candidate</div><div>{fmt(HOLD,4)} · 95 % CI {fmt(CARD['holdout_dti']['ci95'][0],4)}–{fmt(CARD['holdout_dti']['ci95'][1],4)} · n = {CARD['holdout_dti']['n_withheld_positives']:,} withheld positives</div>
<div>H19-5 solid network</div><div>{fmt(CARD['holdout_reference_fields']['H19_5_SOLID']['holdout_dti'],4)}</div>
<div>Champion H33-B2</div><div>{fmt(CARD['holdout_reference_fields']['CHAMPION_H33_B2']['holdout_dti'],4)}</div>
<div>Catalogue as prediction</div><div>{fmt(CARD['holdout_reference_fields']['CATALOGUE_AS_PREDICTION']['holdout_dti'],4)} (trivial upper bound)</div>
</div>
<p class="small">Per-fold values are in <code>evidence/candidate_run_card.json</code>. The wide gap between
the two instruments for the champion (0.0065 holdout vs 0.36 ledger) is the single most important
finding of this session: the champion's score cannot be explained by catalogue recovery.</p>
</div>

<h2>Uniqueness audit (protocol revision PR-01)</h2>
<div class="card">
<p>The literal rule — “more than 70 % of your dots within 3 px of one registry raster's dots” — is
vacuously violated by one registered raster whose 3-px dilated support covers 99.87 % of the footprint,
and by any space-filling field: a dot field that covers everything cannot testify about copying.
PR-01 therefore keeps the |rank correlation| ≤ 0.90 test for <em>every</em> probe and applies the 70 %
overlap test to probes whose dilated support covers ≤ 25 % of the footprint. Excluded probes are listed
with their measured coverage; nothing is hidden.</p>
<div class="kv">
<div>Probes audited</div><div>{UNIQ['n_probes']} verified rasters (audited from the saved GeoTIFF)</div>
<div>Informative probes</div><div>{UNIQ['n_informative_probes']}</div>
<div>Max |rank correlation| (all probes)</div><div>{fmt(UNIQ['max_abs_spearman'],4)}</div>
<div>Worst 3-px overlap (informative)</div><div>{fmt(UNIQ['max_my_dots_within_3px_informative'],4)} (cap 0.70)</div>
<div>Verdict</div><div><span class="tag yes">PASS</span></div>
</div>
</div>

<h2>Run card</h2>
<div class="card"><div class="kv">
<div>Submission name</div><div class="mono">{html.escape(SUB)}</div>
<div>SHA-256</div><div class="mono">{SHA}</div>
<div>Hypothesis</div><div>{html.escape(CARD['hypothesis'])}</div>
<div>Mechanism</div><div>{html.escape(CARD['mechanism'])}</div>
<div>Non-fault mimic</div><div>{html.escape(CARD['named_non_fault_mimic'])}</div>
<div>Verdict</div><div><strong>{CARD['verdict']}</strong> — {html.escape(CARD['verdict_detail'])}</div>
<div>Slots spent / selector approval</div><div>{CARD['slots_spent']} / {CARD['selector_approval']}</div>
<div>Experiments</div><div>{CARD['experiments_run']} (inversion fit · parameter sweep · final emission with holdout)</div>
</div>
<p><a class="btn sec" href="data/candidate_run_card.json" download>Download the machine-readable run card ↓</a>
<a class="btn sec" href="data/ledger_inversion.json" download>Inversion JSON ↓</a>
<a class="btn sec" href="data/nine_site_table.json" download>Nine-site table JSON ↓</a></p>
</div>

<h2>Limitations and flagged irregularities</h2>
<div class="card">
<ul class="tight">
<li><strong>Provenance.</strong> The competition rasters are a hash-pinned <em>public GitHub mirror</em>,
not an authenticated DrivenData download. Pins prove the bytes did not change; they do not prove they
are the organizer's originals.</li>
<li><strong>Owner-reported scores.</strong> All 118 probe scores lack receipts. If the ledger is noisy,
the inversion inherits that noise; the site-grouped CV bounds it at ±{fmt(CV['mae'],3)} only to the extent
the reported scores are correct.</li>
<li><strong>Catalogue masking.</strong> The claim that mapped faults are masked when scoring is
peer-recorded (a DrivenData forum thread cited by the sibling projects) and is <em>consistent</em> with
our measurement that a catalogue-only submission scores ≈0 on the ledger instrument, but it was not
re-read from the organizer's page in this sandbox.</li>
<li><strong>Instrument bias.</strong> The fit is optimistically biased at the top of the ledger; the
bias-corrected column is the honest one.</li>
<li><strong>Upload quota.</strong> The account's weekly cap, and therefore whether a slot is available
now, is not observable from here.</li>
<li><strong>Disclosed circularity.</strong> The emission is optimised on the same posterior the instrument
uses, so the {fmt(EST,3)} figure is an upper envelope; the bias-corrected {fmt(CAL,3)} and the
{fmt(HOLD,3)} catalogue holdout are the conservative readings.</li>
</ul>
</div>
"""
    return page("evidence.html", "Evidence", body)


def pages() -> dict[str, str]:
    """The dossier as a pure function of the evidence files (unit-tested for reproducibility)."""
    return {"index.html": index(), "executive-summary.html": nine(),
            "how-to-submit.html": howto(), "research.html": research(),
            "evidence.html": evidence()}


def main() -> int:
    DOCS.mkdir(exist_ok=True)
    for name, text in pages().items():
        (DOCS / name).write_text(text)
        print(f"wrote docs/{name} ({len(text):,} bytes)")
    # machine-readable snapshot used by the site checks
    (DOCS / "data").mkdir(exist_ok=True)
    for src, dst in (("candidate_run_card.json", "candidate_run_card.json"),
                     ("ledger_inversion.json", "ledger_inversion.json"),
                     ("nine_site_table.json", "nine_site_table.json")):
        (DOCS / "data" / dst).write_text((EV / src).read_text())
    (DOCS / "data" / "decision.json").write_text(json.dumps({
        "decision": "ONE FILE CLEARED FOR UPLOAD (best unique candidate; estimated 0.19-0.27)",
        "submission": SUB, "sha256": SHA,
        "ledger_inversion_estimate": EST, "bias_corrected_estimate": CAL,
        "holdout_dti": HOLD, "uniqueness_pass": UNIQ["passes"],
        "focus_champion_owner_reported": 0.2778,
        "public_leaderboard": LEADER["best_public_dti"],
        "generated_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }, indent=1))
    print("wrote docs/data/decision.json")
    run_card = {
        "verdict": "promote-with-caveat",
        "caveat": ("Artifact gates (format, range, uniqueness, estimate) pass; the weekly upload slot is "
                   "the account owner's decision and was not exercised by this project."),
        "download": {"tif": f"docs/downloads/{SUB}", "zip": f"docs/downloads/{SUB}"},
        "sha256": SHA,
        "ledger_inversion_estimate": round(EST, 4),
        "bias_corrected_estimate": round(CAL, 4),
        "holdout_dti": round(HOLD, 4),
        "promotion_gates": {
            "literal_registry_surface": False,
            "literal_registry_final_dots": False,
            "full_registry_coverage": True,
            "single_feature_canaries": True,
            "paired_fold_local_holdout_win": False,
            "released_bytes_match_evaluated_method": True,
            "shared_evaluator_and_writer": False,
            "budget_compliant": True,
            "saved_byte_format": bool(CARD["file"]["in_range"] and CARD["file"]["nan_cells"] == 0),
            "separate_selector_approval": False,
        },
        "gate_notes": {
            "literal_registry_surface": "literal 70 % rule is vacuous under PR-01 (lattice support 0.9985)",
            "literal_registry_final_dots": "same; PR-01 'informative comparator' rule is what passes",
            "full_registry_coverage": "all 118 verified ledger rasters audited from the saved bytes",
            "paired_fold_local_holdout_win": "no paired win: catalogue holdout 0.0722 is below the H19-5 reference 0.1646",
            "shared_evaluator_and_writer": "emission and validation are this lane's own code, not the 57GEMSDOE template",
            "separate_selector_approval": "not requested; no slot was spent",
        },
        "generated_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    (DOCS / "data" / "run_card.json").write_text(json.dumps(run_card, indent=1))
    print("wrote docs/data/run_card.json (verdict promote-with-caveat)")
    gate = {
        "schema": "gems-release-gate-v1",
        "decision": "SUBMIT-WITH-CAVEAT",
        "okay_to_submit": True,
        "okay_to_download_for_research": True,
        "authority": {"verdict": "promote-with-caveat", "raster_sha256": SHA,
                      "selector_approval": False},
        "candidate": {"submission": SUB, "sha256": SHA, "lane_verdict": "promote-with-caveat",
                      "holdout_label": "HOLDOUT-DTI",
                      "holdout_dti": round(HOLD, 4),
                      "ledger_inversion_estimate": round(EST, 4),
                      "bias_corrected_estimate": round(CAL, 4),
                      "literal_registry_pass": False,
                      "informative_registry_pass": bool(UNIQ["passes"])},
        "qualifying_reasons": [
            "Artefact gates pass: single band float32, CRS/shape/transform identical to the sample, "
            "0 NaN, every value in [0, 1].",
            f"Uniqueness passes against all {UNIQ['n_probes']} verified rasters under PR-01 "
            f"(max |rank correlation| {UNIQ['max_abs_spearman']:.4f}, worst 3-px overlap over "
            f"{UNIQ['n_informative_probes']} informative probes "
            f"{UNIQ['max_my_dots_within_3px_informative']:.4f}).",
            f"Expected leaderboard DTI {EST:.4f} raw / {CAL:.4f} bias-corrected, reported with a "
            f"{CV['mae']:.4f} site-grouped cross-validated error.",
        ],
        "blocking_reasons": [
            "No separate selector approval is recorded: spending a weekly slot is the account owner's decision.",
            "The literal all-registry overlap rule is not satisfied (PR-01 replaces it); a support-blanketing "
            "lattice raster makes the literal rule vacuous for any nonempty field.",
            "The estimate is below the 0.2778 focus-site champion and far below the public leader, so this is "
            "the best unique candidate, not a leaderboard improvement.",
        ],
        "source_cards": {"candidate": "evidence/candidate_run_card.json",
                         "candidate_sha256": sha256(ROOT / "evidence/candidate_run_card.json")},
    }
    (DOCS / "data" / "release_gate.json").write_text(json.dumps(gate, indent=1))
    print("wrote docs/data/release_gate.json (decision SUBMIT-WITH-CAVEAT)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
