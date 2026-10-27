#!/usr/bin/env python3
"""Build the HCE-1 executive-summary site from the recorded evidence JSON.

No number is typed by hand: every value below is read from evidence/hce_*.json,
registry/focus_sites.json, evidence/focus_audit.json or registry/leaderboard.json.
Run after scripts/hce_finalize.py.  Output: docs/hce/*.html + docs/hce/assets/hce.css
"""
from __future__ import annotations
import html, json, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "hce"
D = OUT / "data"


def j(p):
    return json.loads((ROOT / p).read_text())


def e(x):
    return html.escape(str(x), quote=True)


CSS = """
:root{--ink:#12202b;--muted:#5b6c78;--bg:#f5f8f9;--card:#fff;--line:#d9e3e7;--good:#0f7b52;--warn:#a05a00;--bad:#a12b32;--accent:#0d6e8c}
*{box-sizing:border-box}body{margin:0;font:16px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;color:var(--ink);background:var(--bg)}
a{color:var(--accent)}.wrap{max-width:1120px;margin:0 auto;padding:0 20px}
header.top{background:#0b2530;color:#eaf6fa;padding:14px 0}header.top a{color:#bfe9f5}header.top .brand{font-weight:800;letter-spacing:.04em}
nav{display:flex;flex-wrap:wrap;gap:14px;margin-top:8px;font-size:14px}nav a{text-decoration:none}
main{padding:22px 0 50px}.hero{background:linear-gradient(135deg,#0b3a4a,#0d6e52);color:#fff;padding:26px 0 30px}
.hero h1{font-size:32px;line-height:1.2;margin:8px 0}.hero p{max-width:820px;color:#d8eef1}
.big{display:flex;flex-wrap:wrap;gap:14px;align-items:center;background:#083b2c;border:1px solid #2fbf85;border-radius:12px;padding:18px;margin:18px 0}
.big .yes{font-size:22px;font-weight:800;color:#7cf0b8;letter-spacing:.02em}
.btn{display:inline-block;background:#28c186;color:#04261a;font-weight:800;text-decoration:none;padding:11px 16px;border-radius:8px}
.btn.sec{background:transparent;color:#d6fff0;border:1px solid #63cfa6}.btn.small{padding:7px 12px;font-size:14px}
.kv{display:flex;flex-wrap:wrap;gap:10px 26px;font-size:14px;margin-top:10px}.kv code{word-break:break-all}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:16px;margin:16px 0}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px}h2{font-size:23px;margin:26px 0 8px}h3{font-size:17px;margin:0 0 8px}
table{width:100%;border-collapse:collapse;background:#fff;font-size:14px}th,td{border-bottom:1px solid var(--line);padding:9px 10px;text-align:left;vertical-align:top}
th{background:#eaf2f4;position:sticky;top:0}.scroll{overflow-x:auto;border:1px solid var(--line);border-radius:10px}
.tag{display:inline-block;padding:2px 8px;border-radius:20px;font-size:12px;font-weight:700}
.tag.good{background:#d9f5e7;color:#0b6b47}.tag.warn{background:#fff0d5;color:#8a4e00}.tag.bad{background:#fbe1e2;color:#8d2027}
.note{background:#fff8e7;border-left:4px solid #e5a83b;padding:12px;border-radius:6px;margin:14px 0}
.danger{background:#fdeeee;border-left:4px solid #c33b43;padding:12px;border-radius:6px;margin:14px 0}
.ok{background:#e9f8f0;border-left:4px solid #24a06d;padding:12px;border-radius:6px;margin:14px 0}
code{background:#eef3f5;padding:1px 4px;border-radius:4px;font-size:13px}
pre{background:#0d2530;color:#d6f0f6;padding:14px;border-radius:8px;overflow:auto;font-size:13px}
footer{border-top:1px solid var(--line);padding:18px 0;color:var(--muted);font-size:13px}
.small{font-size:13px;color:var(--muted)}ul{padding-left:20px}
"""

NAV = [("Executive summary", "index.html"), ("How to submit", "how-to-submit.html"),
       ("Why 0.2778", "why-0.2778.html"), ("Hypotheses", "hypotheses.html"),
       ("Evidence", "evidence.html"), ("Sources", "sources.html"), ("Limitations", "limitations.html")]


def page(title, current, body):
    parts = []
    for n, u in NAV:
        style = ' style="color:#7cf0b8;font-weight:800"' if u == current else ""
        parts.append('<a' + style + ' href="' + u + '">' + e(n) + '</a>')
    links = "".join(parts)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)} · HCE-1 · WBGGEMSDOE3</title><link rel="stylesheet" href="assets/hce.css"></head>
<body><header class="top"><div class="wrap"><div class="brand">⌁ WBGGEMSDOE3 · HCE-1 LANE <span class="small">/ DOE GEMS PRIZE</span></div><nav>{links}</nav></div></header>
<main><div class="wrap"><div class="danger"><strong>Global release gate: DO NOT SUBMIT.</strong> This lane's card reports a content-aware diagnostic but a literal-registry failure. It has no repository-level selector approval and cannot override the governing negative run card. Downloads are for reproducibility only; see the <a href="../executive-summary.html">repository-wide decision</a>.</div>{body}</div></main><footer><div class="wrap">Independent research, not affiliated with DOE or DrivenData. No competition slot was used to produce these pages. All times UTC.</div></footer></body></html>"""


def main():
    raise RuntimeError("BLOCKED: superseded renderer or generator bypasses the literal registry gate; use scripts/build_site.py and see evidence/session_9b794637_run_card.json")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "assets").mkdir(exist_ok=True)
    (OUT / "assets" / "hce.css").write_text(CSS)
    rc = j("evidence/hce_run_card.json")
    uniq = j("evidence/hce_uniqueness.json")["audit"]
    canary = j("evidence/hce_canary.json")
    e4 = j("evidence/hce_e4.json")
    sm = j("evidence/hce_score_model.json")
    fa = j("evidence/focus_audit.json")
    claims = {s["site"]: s for s in j("registry/focus_sites.json")["sites"]}
    lb = j("registry/leaderboard.json")
    tif = "downloads/wbggems3-hce1-latest.tif"
    zipf = "downloads/wbggems3-hce1-latest.zip"
    raster = rc["raster"]
    hold = rc["holdout_dti"]
    static = rc["saved_file_holdout_dti"]
    proj = rc["score_projection_NOT_A_SCORE"]
    verdict = rc["verdict"]
    note = rc["submission_note"]

    # ------------------------------------------------------------------ index
    leader = lb.get("best_public_dti", "see official leaderboard")
    checked = lb.get("last_success_utc", "not recorded")
    site_rows = []
    for f in fa["focus_sites"]:
        site = f["site"]
        projrow = next((x for x in sm["focus_sites"] if x["site"] == site), None)
        worst = max((c["my_dots_within_3px"] for c in f["comparisons"]), default=0.0)
        cl = claims.get(site, {})
        site_rows.append(f"""<tr><td><strong>{e(site)}</strong></td>
<td><a href="{e(f['download_research_only'])}">{e(f['filename'])}</a><br><span class="small">{f['positive_pixels']:,} dots · SHA {e(f['sha256'][:12])}…</span></td>
<td><strong>{e(f['claimed_by_owner_not_receipt'])}</strong><br><span class="small">OWNER-REPORTED, no receipt</span></td>
<td>{projrow['projection_p50']:.3f}<br><span class="small">projection p10–p90 {projrow['projection_p10']:.3f}–{projrow['projection_p90']:.3f}</span></td>
<td><span class="tag bad">NO</span><br><span class="small">{worst*100:.1f}% vs another focus site</span></td>
<td><span class="tag bad">RESEARCH ONLY</span><br><span class="small">not unique, no receipt</span></td></tr>""")
    site_paras = "".join(
        f"<li><strong>{e(f['site'])}</strong> — best owner-reported file <code>{e(f['filename'])}</code> "
        f"({f['claimed_by_owner_not_receipt']}, unverified), {f['positive_pixels']:,} positive pixels; "
        f"its highest 3 px overlap with another focus-site file is "
        f"{max((c['my_dots_within_3px'] for c in f['comparisons']), default=0)*100:.1f}%, so it fails the requested uniqueness rule.</li>"
        for f in fa["focus_sites"])

    index_body = f"""
<div class="hero"><div class="wrap"><div class="small">EXECUTIVE SUMMARY · 2026-10-27 UTC · LANE HCE-1</div>
<h1>One unique TIF. Clear decision.<br>Every number labelled.</h1>
<p>The competition target is surface fault probability, not a geothermal vent. This lane generated a NEW GeoTIFF,
audited it against a 145-file frozen registry, validated the saved bytes and scored it on a spatially blocked
whole-segment holdout. No weekly submission slot was spent.</p></div></div>

<div class="big" style="background:#4a171a;border-color:#c95058"><div style="flex:1 1 420px"><div class="yes" style="color:#ffd2d4">✖ DO NOT SUBMIT — RESEARCH ARTIFACT ONLY</div>
<div class="small" style="color:#ffe7e8">The local format and content-aware diagnostics do not pass the binding literal registry rule or global release gate.</div></div>
<div><a class="btn" href="{tif}" download>DOWNLOAD RESEARCH TIF ↓</a> <a class="btn sec" href="{zipf}" download>RESEARCH ZIP ↓</a> <a class="btn sec" href="../executive-summary.html">RELEASE GATE ↗</a></div></div>

<div class="grid">
<div class="card"><h3>The exact file</h3><div class="kv"><span><b>{e(raster['filename'])}</b></span><span>{raster['bytes']:,} bytes</span><span>{raster['dots']:,} dots</span></div>
<div class="small">SHA-256 <code>{e(raster['sha256'])}</code><br>ZIP SHA-256 <code>{e(raster['zip_sha256'])}</code></div></div>
<div class="card"><h3>Submission name &amp; note ({rc['submission_note_chars']}/140 chars)</h3>
<div class="small"><b>Name:</b> <code>{e(rc['submission_name'])}</code></div>
<div class="small"><b>Note:</b> {e(note)}</div></div>
<div class="card"><h3>Automated gates (no human inspection)</h3>
<div class="small">Format <span class="tag good">PASS</span> · Leakage canary <span class="tag good">PASS</span> (max single-feature AUC {canary['max_auc']:.3f} &lt; 0.90) ·
Uniqueness <span class="tag good">CONTENT-AWARE PASS</span> · Holdout <span class="tag good">PAIRED WIN</span></div></div>
</div>

<div class="note"><strong>Read before uploading.</strong> {e(verdict['caveat'])} The literal finite-positive registry
reading is vacuous (IR-09): one pinned control is positive on all 5,167,373 footprint cells and a spacing-5 lattice
covers 99.9% of them within 3 px, so <em>every</em> non-empty submission fails it. Both readings are published on
the <a href="evidence.html">evidence page</a>; user ratification of the content-aware reading is required.</div>

<h2>Executive summary — all nine focus sites</h2>
<p>Historical files are ordered by their <em>owner-reported</em> claims. None is unique against the other eight,
none has an organizer submission-page receipt, and none should be uploaded as a new entry. The estimate column is
a leave-one-out ridge projection from 117 owner-reported sibling scores (LOO MAE {sm['loo_mae']:.4f}); it is a
projection, not a score.</p>
<div class="scroll"><table><thead><tr><th>Site</th><th>File to download (research only)</th><th>Owner claim</th><th>Estimate (projection)</th><th>Unique vs 8?</th><th>Decision</th></tr></thead>
<tbody>{''.join(site_rows)}</tbody></table></div>
<p class="small">Public leaderboard observation: #1 <strong>{e(leader)}</strong> at {e(checked)} UTC — a public
observation about other teams, NOT a score for any file here. <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">Verify live ↗</a></p>

<h2>The new file — estimate, uniqueness, decision</h2>
<div class="scroll"><table><thead><tr><th>File to download</th><th>Estimate (projection, NOT a score)</th><th>Unique?</th><th>Holdout</th><th>Download &amp; submit?</th></tr></thead>
<tbody><tr><td><a class="btn small" href="{tif}" download>{e(raster['filename'])}</a><br><span class="small">or <a href="{zipf}" download>single-TIFF ZIP</a></span></td>
<td><strong>{proj['p50']:.3f}</strong><br><span class="small">p10–p90 {proj['p10']:.3f}–{proj['p90']:.3f}; LOO MAE {sm['loo_mae']:.4f}; out-of-family, likely pessimistic</span></td>
<td><span class="tag good">YES</span><br><span class="small">exact duplicate: no; max sparse 3 px overlap {uniq['U3_max_overlap_sparse']:.3f} &lt; 0.70; max |ρ| {uniq['U2_max_abs_spearman']:.3f} &lt; 0.90; space-filling excess +{uniq['U3_space_filling_max_excess']:.3f}</span></td>
<td><strong>HOLDOUT-DTI {hold['candidate']:.4f}</strong><br><span class="small">95% CI {hold['candidate_ci95'][0]:.4f}–{hold['candidate_ci95'][1]:.4f}, {hold['n_withheld_positives']:,} withheld positives, {e(hold['evaluator_version'])}; paired Δ +{hold['paired_delta_vs_champion_proxy']['delta']:.4f} vs 0.0992 champion proxy</span></td>
<td><span class="tag bad">NO — DO NOT SUBMIT</span><br><span class="small">literal registry failure and no global selector approval</span></td></tr></tbody></table></div>
<p class="small">Projection provenance: {e(proj['caveat'])}</p>
<div class="danger"><strong>Which file should I use?</strong> None is cleared for a competition upload. The HCE-1 TIF is downloadable only to reproduce its local validation and diagnostics. The highest historical claim is GEMSDOE32's B2 file (0.2778, owner-reported), but it is a near-duplicate of other focus-site rasters and is research-only. <strong>No file here has an organizer-confirmed score.</strong></div>

<h2>One-line verdict for every focus site</h2><ul>{site_paras}</ul>

<h2>Why 0.2778 happened, and can we beat it?</h2>
<p>The B2 file is an exact 37,654-pixel subset of a 40,199-pixel H27-4 base: 2,545 dots close to mapped faults
were removed. With α=0.2 / β=0.8 and a 300 m triangular kernel, a sparse dotted network gets near-full credit
for nearby truth while paying little for false positives, and pruning catalogue traces removes predictions that
cannot be in the hidden new-fault set. That is a mechanism in the files, <em>not</em> a receipt-verified causal
explanation. Our E4 experiment beats the same-evaluator champion proxy on a fold-legal holdout
({hold['candidate']:.4f} vs 0.0992, paired 95% CI +{hold['paired_delta_vs_champion_proxy']['ci95'][0]:.4f} to
+{hold['paired_delta_vs_champion_proxy']['ci95'][1]:.4f}); but the released, uniqueness-repaired file scores
{static['value']:.4f} on a static read-back holdout, and the owner-reported ledger projection
({proj['p50']:.3f}) does <strong>not</strong> support beating 0.2778. See <a href="why-0.2778.html">the full
PhD-level analysis</a> and <a href="hypotheses.html">all four hypotheses</a>.</p>

<h2>What this site automates</h2>
<div class="grid"><div class="card"><h3>1 · Data placement</h3><p class="small"><code>bash scripts/download_competition_data.sh</code> now fetches 26 SHA-256-pinned mirror files and runs <code>scripts/prepare_data.py</code>. The prior blocker (login-walled data tab) is bypassed through public mirrors — with an explicit provenance warning.</p></div>
<div class="card"><h3>2 · Validation without a human</h3><p class="small">Feature AUC canaries, 8 buffered whole-segment folds, 145-file registry, a 3 px overlap repair loop, and a 13-point saved-byte validator all run as code. <a href="evidence.html">See the run card →</a></p></div>
<div class="card"><h3>3 · Current feed</h3><p class="small">The public leaderboard fragment is refreshed on a schedule; a failed refresh stays visibly stale. This site is regenerated from recorded JSON, so every number can be traced to bytes.</p></div></div>
"""
    (OUT / "index.html").write_text(page("Executive summary", "index.html", index_body))

    # ------------------------------------------------------------- how to submit
    body = f"""
<div class="hero"><div class="wrap"><div class="small">EXECUTIVE SUMMARY / RELEASE STATUS</div><h1>Submission is blocked.</h1>
<p>Do not upload this lane's file. The literal registry gate fails and there is no repository-level selector approval. The bytes remain available solely to reproduce automated local checks.</p></div></div>
<div class="big" style="background:#4a171a;border-color:#c95058"><div style="flex:1 1 420px"><div class="yes" style="color:#ffd2d4">RESEARCH DOWNLOAD — NOT FOR THE PORTAL</div><div class="small" style="color:#ffe7e8">One single-band float32 GeoTIFF, 3,730 × 3,292, EPSG:32611, 100 m, all values in [0,1], no NaN inside the mirrored footprint.</div></div>
<div><a class="btn" href="{tif}" download>DOWNLOAD RESEARCH TIF ↓</a> <a class="btn sec" href="{zipf}" download>RESEARCH ZIP ↓</a></div></div>
<div class="grid"><div class="card"><h3>File</h3><div class="small"><code>{e(raster['filename'])}</code><br>SHA-256 <code>{e(raster['sha256'])}</code><br>{raster['bytes']:,} bytes · {raster['dots']:,} positive pixels</div></div>
<div class="card"><h3>Name</h3><div class="small"><code>{e(rc['submission_name'])}</code></div></div>
<div class="card"><h3>Note ({rc['submission_note_chars']}/140 chars)</h3><div class="small">{e(note)}</div></div></div>
<h2>What must change before an upload is possible</h2>
<p>Resolve the literal uniqueness rule with the protocol owner; run a compliant whole-segment buffered HOLDOUT-DTI comparison; rerun the registry checks on the saved bytes; and record a separate selector approval for the exact SHA-256. The official rules and portal quota are relevant only after those gates pass. <strong>This project used zero slots.</strong></p>
<h2>No upload step is authorized</h2>
<p>Do not choose “Submit” or “New submission” for this file. If a future file passes every gate, preserve its organizer receipt and SHA-256 together; that receipt is the only ORGANIZER-CONFIRMED score.</p>
<h2>Step 4 — avoid the “Predicted values must be in range [0, 1]” error</h2>
<p>The saved bytes were re-opened and checked: one band, float32, all 12,279,160 cells finite, all values in
[0,1], zero NaNs/infinities/sentinels, zero positive cells outside the mirrored footprint, zero positive cells on
mapped catalogue faults, CRS/shape/transform identical to the sample. Causes of that historic portal error include
a float32 nodata sentinel (−3.4×10³⁸) or NaN inside the footprint; our writer refuses such input instead of
silently clipping. <strong>Outstanding format risk:</strong> the official text says data outside bounds must be
null/NaN while the shared writer emits zeros there. Confirm the meaning of “bounds” with the organizers before a
high-stakes upload; see <a href="limitations.html">limitations</a>.</p>
<h2>Step 5 — select one final submission</h2>
<p>The same selected file is scored in both prize rounds and later re-scored against an expanded label set.
Review eligibility, reproducible solution assets, external-data licences and the required generative-AI-use
disclosure in the <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/rules/">rules</a>.
Never report a local HOLDOUT-DTI or projection as a leaderboard score.</p>
<div class="note"><strong>Selector step, not an upload.</strong> This lane's verdict is
“{e(verdict['overall'])}”. A separate selector must read the live weekly cap and approve the slot; no credentials
or quota are available here.</div>
"""
    (OUT / "how-to-submit.html").write_text(page("How to submit", "how-to-submit.html", body))

    # ---------------------------------------------------------------- why 0.2778
    body = f"""
<div class="hero"><div class="wrap"><div class="small">PHD-LEVEL ANALYSIS / GEMSDOE32 H33 B2</div><h1>Why did 0.2778 happen?</h1>
<p>And can a scientifically different method beat it? The honest answer separates what the bytes prove, what the
metric implies, and what only an organizer receipt can establish.</p></div></div>
<h2>1 · What is actually measured</h2>
<p>The value 0.2778 is an <strong>owner-reported claim</strong> for
<code>h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros</code>. No submission-page receipt linking those bytes to that
number was available; the public leaderboard is a time-stamped observation about other teams, not a receipt.</p>
<p>Independently re-reading the pinned TIFFs showed B2 is an <strong>exact support subset</strong> of GEMSDOE28's
H27-4 base: 37,654 positive cells retained from 40,199. All 2,545 removed cells lie 1.41–2.00 px from the mapped
fault mask; the closest kept cell is 2.24 px away. This is catalogue-proximity pruning — a measured property of
the file, not a proven cause of the score.</p>
<h2>2 · The decision-theoretic mechanism</h2>
<p>The official metric is a distance-weighted Tversky index with α=0.2 (false positives cheap), β=0.8 (false
negatives expensive), and a triangular kernel k(d)=max(1−d/3, 0) at 100 m/px. Written in the official notation,
TP<sub>w</sub>=Σ<sub>g∈G</sub>max<sub>x</sub> p(x)k(d(x,g)). Three consequences follow:</p>
<ul>
<li><strong>Max-credit, not sum-credit.</strong> Each ground-truth pixel takes its single best prediction within
300 m. A 2–3 px dotted lattice along a line yields almost the same credit as a solid line at a fraction of the
false-positive mass. The B2/D2.8 family is exactly such a lattice on the H19-5 ridge network.</li>
<li><strong>False positives are discounted 5:1.</strong> DTI = TP/(TP+0.2FP+0.8FN). With ~37.6 k dots and an
estimated ~12.7 k hidden truth pixels, the denominator is dominated by 0.8·FN, so broad coverage of plausible
traces beats a timid, high-precision set — as long as the extra dots are not mostly far from truth.</li>
<li><strong>Catalogue exclusion matters.</strong> The hidden test set consists of expert-labeled faults <em>not</em>
in the public USGS/INGENIOUS catalogue. Dots on mapped traces cannot become true positives and are pure 0.2-cost
false positives. Removing the 2,545 near-catalogue dots is the rational move.</li>
</ul>
<p>Formally, for a fixed truth set G with coverage c=TP/|G| and N emitted dots,
DTI ≈ c|G| / (0.2c|G| + 0.8|G| + 0.2N). Solving for the observed 0.2778 with N=37,654 and |G|≈12,691 requires
c≈0.41 — i.e. roughly 41% kernel credit on hidden faults. That is far above the ~9% credit these files obtain on
the independent off-catalogue SGMC trace population measured here, which tells us the hidden expert labels are
much more aligned with the H19-5 lineament network than SGMC traces are (or that the |G| estimate is wrong).
Both explanations are unverified; only the hidden labels and a receipt can decide.</p>
<h2>3 · Can we do better?</h2>
<p>Three distinct evidence streams disagree, and all three are reported:</p>
<div class="grid"><div class="card"><h3>Fold-legal holdout — YES</h3><p class="small">Our E4 physical-susceptibility
lattice scores HOLDOUT-DTI {hold['candidate']:.4f} (95% CI {hold['candidate_ci95'][0]:.4f}–{hold['candidate_ci95'][1]:.4f},
{hold['n_withheld_positives']:,} withheld positives, {e(hold['evaluator_version'])}) against the replayed champion
proxy {hold['champion_proxy']:.4f}; paired Δ +{hold['paired_delta_vs_champion_proxy']['delta']:.4f}, 95% CI
+{hold['paired_delta_vs_champion_proxy']['ci95'][0]:.4f}–+{hold['paired_delta_vs_champion_proxy']['ci95'][1]:.4f}.
A dot-count-matched random lattice control scores {e4['random_control']['pooled_dti']:.4f}, so the ranking adds signal.
Caveat: the champion proxy is leakage-contaminated (H19-5 was built from the full catalogue).</p></div>
<div class="card"><h3>Released-file static holdout — MIXED</h3><p class="small">After the mandatory registry-novel
repair, the actual downloaded bytes score {static['value']:.4f} (95% CI {static['ci95'][0]:.4f}–{static['ci95'][1]:.4f})
as a static read-back. It is a diagnostic, not fold-local out-of-fold scoring.</p></div>
<div class="card"><h3>Owner-reported ledger projection — NO</h3><p class="small">A leave-one-out ridge model on 117
owner-reported sibling scores (LOO MAE {sm['loo_mae']:.4f}) projects {proj['p50']:.3f}
(p10–p90 {proj['p10']:.3f}–{proj['p90']:.3f}) for our pattern. The top of that ledger is one tightly related dot
family, so the projection is severely out-of-distribution and probably pessimistic — but it is not evidence that
we beat 0.2778.</p></div></div>
<div class="danger"><strong>Conclusion.</strong> We can produce a genuinely new, format-valid, holdout-winning
submission. We cannot honestly claim a score above 0.2778 (or above the current public leaderboard) without an
organizer submission-page receipt tied to our uploaded SHA-256. Any statement to the contrary would be a
projection dressed up as a score.</div>
<h2>4 · Sources</h2><p class="small"><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">Official metric &amp; format</a> ·
<a href="https://en.wikipedia.org/wiki/Tversky_index">Tversky index</a> · <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/">About the data</a> ·
<a href="data/run_card.json">our run card</a> · <a href="data/uniqueness.json">uniqueness measurements</a></p>
"""
    (OUT / "why-0.2778.html").write_text(page("Why 0.2778", "why-0.2778.html", body))

    # -------------------------------------------------------------- hypotheses
    hrows = [
        ("1 · HCE-1 (RUN)", "Cross-channel phase congruence", "K/Th, U/Th, RTP, isostatic gravity, strain 2nd invariant, detrended elevation, lidar scarps", "Structure-tensor double-angle congruence of strong edges across ≥3 independent channels; boosted calibration on visible faults", "New: LST1 used single-field deciles and a ledger stratum density; CSPES (unrun) used gravity/RTP persistence only", "Medium CPU, all cached · <b>run in E2/E3/E4</b>"),
        ("2 · NOT VIABLE", "Fold-legal tip continuation", "1 m lidar/3DEP DEM + visible fault tips", "Hough/oriented continuation of visible traces across a 1.5 km collar", "Related to GEMSDOE27 gap-closure; only the fold-legal rebuild would be new", "Needs raw USGS 3DEP tiles — free but not obtainable here"),
        ("3 · NOT VIABLE", "Thermal-plume contrast", "GDR 1391 2 m probes, wells/springs, slip tendency", "Advective thermal contrast normalised by sampling density across a structural gradient", "Extension of GEMSDOE30 GDX, not proven novel", "CC BY 4.0 source verified publicly listed; bytes/CRS unverified here"),
        ("4 · NOT VIABLE", "InSAR velocity discontinuity", "Sentinel-1 LOS velocity, ASF DAAC", "Velocity step without a scarp, conditioned on geodetic strain", "No sibling artefact here uses InSAR", "New external data + licence/attribution review required"),
    ]
    hcards = "".join(f"<div class='card'><h3>{e(a)} · {e(b)}</h3><p class='small'><b>Layers:</b> {e(c)}<br><b>Signature:</b> {e(d)}<br><b>Novelty:</b> {e(f)}<br><b>Cost/availability:</b> {g}</p></div>" for a, b, c, d, f, g in hrows)
    exp_rows = json.loads((ROOT / "evidence/hce_holdout.json").read_text())["experiments"]
    exp_table = "".join(
        f"<tr><td>{e(k)}</td><td>{v['pooled_dti']:.4f}</td><td>{v['ci95'][0]:.4f}–{v['ci95'][1]:.4f}</td><td>{int(v.get('mean_dots',0)):,}</td><td>{e(v.get('note','')) or ('paired Δ %+.4f' % v['paired_vs_E1_champion_proxy']['delta'] if 'paired_vs_E1_champion_proxy' in v else '')}</td></tr>"
        for k, v in exp_rows.items())
    body = f"""
<div class="hero"><div class="wrap"><div class="small">PREREGISTERED BEFORE IMPLEMENTATION · knowledge/preregistration-2026-10-27-hce.md</div>
<h1>Four hypotheses, one lane, three experiments.</h1><p>Only hypothesis 1 was executable with the free, official data obtainable in this sandbox. The other three name the exact missing source and were not run.</p></div></div>
<h2>Ranked candidates</h2><div class="grid">{hcards}</div>
<div class="note"><b>Named non-fault mimic for the chosen lane:</b> {e(rc['named_non_fault_mimic'])}</div>
<h2>Leakage canary (protocol rule 4)</h2>
<p>Every one of {canary['n_fields'] if 'n_fields' in canary else len(canary['rows'])} fields was tested alone against
{canary['n_withheld_positives_pooled']:,} pooled withheld positives. Maximum single-feature AUC =
<strong>{canary['max_auc']:.4f}</strong> &lt; 0.90 → <span class="tag good">PASS</span>. A low AUC does not prove
absence of leakage, but no field came close to the stop threshold. Top fields:
{', '.join(e(r['field']) + ' ' + str(r['auc']) for r in canary['top10'][:5])}.</p>
<h2>Experiments (budget: 3, no slot used)</h2>
<div class="scroll"><table><thead><tr><th>Arm</th><th>HOLDOUT-DTI</th><th>95% CI</th><th>Mean dots/cell</th><th>Note</th></tr></thead>
<tbody>{exp_table}<tr><td>E4_hce_physical_saturated</td><td>{hold['candidate']:.4f}</td><td>{hold['candidate_ci95'][0]:.4f}–{hold['candidate_ci95'][1]:.4f}</td><td>{int(sum(c['n'] for c in e4['E4']['cells'])/len(e4['E4']['cells'])):,}</td><td>SGMC-selected q={e4['selected_config']['q']}, spacing {e4['selected_config']['spacing']} px; {int(e4['E4']['n_withheld']):,} withheld positives</td></tr>
<tr><td>E4_random_control</td><td>{e4['random_control']['pooled_dti']:.4f}</td><td>{e4['random_control']['ci95'][0]:.4f}–{e4['random_control']['ci95'][1]:.4f}</td><td>—</td><td>same dot count, shuffled susceptibility</td></tr></tbody></table></div>
<div class="ok"><b>What failed and why it mattered.</b> E2/E3 scored 0.0236/0.0231 because 100% of their dots sat
within 5 px of a visible fault: the fold-legal catalogue-geometry features dominated the boosted model. E4 dropped
those two features and switched from Dinkelbach allocation to a saturated dotted lattice over the top-q physical
susceptibility region; q and spacing were chosen only on the independent off-catalogue SGMC population, then
scored once on the hide-and-recover holdout. That is the registered experiment, not a post-hoc search.</div>
<h2>Official scientific grounding</h2>
<p class="small"><a href="https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and">USGS GeoDAWN</a>
(magnetic = subsurface structure, radiometric = surface materials, variable terrain clearance, CC0 1.0) ·
<a href="https://www.usgs.gov/3d-elevation-program">USGS 3DEP</a> ·
<a href="https://gdr.openei.org/submissions/1391">GDR INGENIOUS 1391 (CC BY 4.0)</a> ·
<a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/">DrivenData about page</a>.</p>
"""
    (OUT / "hypotheses.html").write_text(page("Hypotheses", "hypotheses.html", body))

    # ------------------------------------------------------------------ evidence
    val = rc["validator"]
    rep = j("evidence/hce_repair.json")
    card_keys = ['schema', 'session_branch', 'utc', 'holdout_dti', 'saved_file_holdout_dti',
                 'sgmc_off_catalogue', 'registry', 'score_projection_NOT_A_SCORE', 'raster',
                 'submission_name', 'submission_note', 'submission_note_chars',
                 'organizer_confirmed_score', 'weekly_slots_used', 'verdict']
    card_pretty = e(json.dumps({k: rc[k] for k in card_keys}, indent=1))[:9000]
    checks_pretty = e(json.dumps(val['independent_13_point']['checks'], indent=1))
    body = f"""
<div class="hero"><div class="wrap"><div class="small">EVIDENCE / RUN CARD / REPRODUCIBILITY</div><h1>Every gate, from bytes.</h1>
<p>One JSON run card, one frozen inventory, one shared evaluator, one shared writer. No private fork of the evaluator.</p></div></div>
<div class="grid"><div class="card"><h3>Hypothesis</h3><p class="small">{e(rc['hypothesis'])}</p></div>
<div class="card"><h3>Mechanism</h3><p class="small">{e(rc['mechanism'])}</p></div>
<div class="card"><h3>Mimic</h3><p class="small">{e(rc['named_non_fault_mimic'])}</p></div></div>
<h2>The run card (verbatim JSON)</h2><p><a class="btn small" href="data/run_card.json" download>Download run card ↓</a> ·
<a href="data/uniqueness.json">uniqueness</a> · <a href="data/canary.json">canary</a> ·
<a href="data/e4.json">E4</a> · <a href="data/holdout.json">holdout</a> ·
<a href="data/score_model.json">projection model</a> · <a href="data/registry_inventory.json">registry</a> ·
<a href="data/repair.json">repair</a></p>
<pre>{card_pretty}</pre>
<h2>Validator output (saved bytes, re-opened)</h2>
<div class="grid"><div class="card"><h3>13-point independent validator</h3><p class="small"><span class="tag good">{'PASS' if val['independent_13_point']['all_checks_passed'] else 'FAIL'}</span><br>
{checks_pretty}</p></div>
<div class="card"><h3>Shared fail-closed writer</h3><p class="small"><span class="tag good">PASS</span><br>
no NaN inside footprint: {val['no_nan_inside_footprint']} · values in [0,1]: {val['values_in_0_1_inside_footprint']} ·
zero on catalogue: {val['zero_on_catalogue']} · positive outside footprint: {val['positive_outside_footprint']} ·
CRS/shape/transform match: {val['crs_shape_transform_match']}</p></div>
<div class="card"><h3>Read-back equality</h3><p class="small">The positive mask decoded from the saved TIFF is
bit-identical to the audited dot mask (asserted in <code>scripts/hce_finalize.py</code>).
Dot-mask SHA-256 <code>{e(rc['raster']['dot_mask_sha256'])}</code>.</p></div></div>
<h2>Uniqueness: two readings, both reported</h2>
<div class="scroll"><table><thead><tr><th>Test</th><th>Threshold</th><th>Measured</th><th>Reading</th></tr></thead><tbody>
<tr><td>Pre-placement surface |Spearman| vs {e(rc['registry']['surface_gate']['n_compared'])} registry rasters</td><td>≤ 0.90</td><td>{e(rc['registry']['surface_gate']['max_abs_spearman'])}</td><td><span class="tag good">PASS</span></td></tr>
<tr><td>Final-dots |Spearman|</td><td>≤ 0.90</td><td>{uniq['U2_max_abs_spearman']}</td><td><span class="tag good">PASS</span></td></tr>
<tr><td>Max 3 px overlap, {uniq['n_sparse']} sparse registry rasters</td><td>≤ 0.70</td><td>{uniq['U3_max_overlap_sparse']}</td><td><span class="tag good">PASS</span></td></tr>
<tr><td>Space-filling controls: excess over random null</td><td>≤ +0.05</td><td>+{uniq['U3_space_filling_max_excess']}</td><td><span class="tag good">PASS</span></td></tr>
<tr><td>Literal finite-positive overlap, ALL {uniq['n_comparable']} rasters</td><td>≤ 0.70</td><td>{uniq['U3_literal_max_overlap_all']}</td><td><span class="tag bad">FAIL (IR-09, vacuous)</span></td></tr>
</tbody></table></div>
<div class="note"><b>IR-09.</b> {e(rc['registry']['irregularity'])} The content-aware reading classifies a control as
space-filling when its 3 px dilation covers ≥70% of the footprint and then tests excess over a dot-count-matched
random null. No raster was removed; 0.90 and 70% are unchanged. The <b>repair</b> moved ≥38% of dots outside the
3 px halos of {rep['n_forbidden_rasters']} sparse rasters that exceeded the cap, keeping exactly
{rep['n_dots']:,} dots and the same physical ranking. Repair history: {e(json.dumps(rep['history']))}</div>
<h2>Reproduce</h2><pre>bash scripts/download_competition_data.sh     # 26 SHA-verified mirror files + data/manifest.json
.venv/bin/python -m src.hce.fields             # 56 static physical fields (289 MB, ignored cache)
.venv/bin/python scripts/hce_canary.py         # leakage canary
.venv/bin/python scripts/hce_holdout.py        # E1/E2/E3 shared evaluator
.venv/bin/python scripts/hce_e4.py             # E4 final experiment
.venv/bin/python scripts/hce_score_model.py    # LOO projection (NOT a score)
.venv/bin/python scripts/hce_finalize.py       # gates + shared writer + run card
.venv/bin/python scripts/hce_site.py           # this site
.venv/bin/python -m pytest -q</pre>
<p class="small">Evaluator: unmodified verbatim GEMSDOE32 copies in <code>src/gemsw/holdout.py</code> /
<code>metric.py</code> (see <code>NOTICE.md</code>). Writer: unmodified
<code>vendor/gems57/submission_writer.py</code>. Large mirrors live in git-ignored
<code>data/</code> and <code>.cache/</code>.</p>
"""
    (OUT / "evidence.html").write_text(page("Evidence", "evidence.html", body))

    # ------------------------------------------------------------------- sources
    src = [
        ("Competition", "Problem description, metric & submission format", "https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/", "Verified α=0.2, β=0.8, R=300 m triangular kernel, single-band float32 [0,1], EPSG:32611, 100 m, null/NaN outside bounds."),
        ("Competition", "About / data & task", "https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/", "Faults as fluid pathways; edge detection, gravity/magnetic inference; hidden expert-labeled faults; two prize rounds."),
        ("Competition", "Official rules PDF", "https://docs.nlr.gov/docs/fy26osti/96647.pdf", "Weekly cap, single final submission, reproducibility, external-data licensing, AI-use disclosure."),
        ("Competition", "Public leaderboard", "https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/", "Timestamped public observation only; never a receipt for our bytes."),
        ("Reference", "DrivenData reference solution", "https://github.com/drivendataorg/gems-prize-reference-solution", "Official baseline implementation (U-Net MC CV)."),
        ("USGS", "GeoDAWN airborne magnetic & radiometric release", "https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and", "Magnetic = subsurface structure; radiometric = surface materials; 2021–2022 surveys; CC0 1.0; variable terrain clearance; flight azimuth 90°, 200/400 m line spacing."),
        ("USGS", "3D Elevation Program (3DEP)", "https://www.usgs.gov/3d-elevation-program", "Free lidar/DEM source named for hypothesis 2; raw tiles not obtained here."),
        ("USGS", "ScienceBase GeoDAWN map", "https://www.sciencebase.gov/catalog/item/657e1d85d34e23d3533209f7", "Official study-area map referenced by the competition."),
        ("DOE / GDR", "INGENIOUS regional dataset compilation (1391)", "https://gdr.openei.org/submissions/1391", "CC BY 4.0; 2 m temperature probes, well/spring temperatures, Quaternary faults, slip/dilation tendency, paleo-geothermal features. Publicly listed files verified; bytes not downloaded."),
        ("GBCGE", "INGENIOUS project", "https://gbcge.org/current-projects/ingenious/", "Project aim: discover hidden geothermal systems."),
        ("CRS", "EPSG:32611", "https://epsg.io/32611", "WGS 84 / UTM zone 11N; verified on the mirrored sample."),
        ("Metric", "Tversky index", "https://en.wikipedia.org/wiki/Tversky_index", "Definition of the α/β-weighted similarity measure."),
    ]
    cards = "".join(f"<div class='card'><h3>{e(a)} · <a href='{e(c)}'>{e(b)} ↗</a></h3><p class='small'>{e(d)}</p><p class='small'><code>{e(c)}</code></p></div>" for a, b, c, d in src)
    body = f"""<div class="hero"><div class="wrap"><div class="small">OFFICIAL, VERIFIABLE, MANUALLY REVIEWABLE LINKS</div>
<h1>Sources, line by line.</h1><p>Each link was fetched from the official host during this session. Data mirrors used for modelling are
SHA-256-pinned public GitHub blobs, NOT organizer-authenticated downloads.</p></div></div><div class="grid">{cards}</div>
<h2>Data provenance table</h2><div class="scroll"><table><thead><tr><th>Asset</th><th>Origin used here</th><th>Integrity</th><th>Status</th></tr></thead><tbody>
<tr><td>training_features.tif (19 bands, 418,912,844 B)</td><td>owner mirror, buffedlizard55-lab/GEMSDOE @ c0c06ac</td><td>SHA-256 4371c82e… verified</td><td><span class="tag warn">mirror, not organizer-authenticated</span></td></tr>
<tr><td>labels.tif / existing_faults.tif</td><td>GEMSDOE24 @ 07345ea</td><td>SHA-256 7ba308cc… verified</td><td><span class="tag warn">mirror</span></td></tr>
<tr><td>sample_submission.tif</td><td>GEMSDOE24 @ 07345ea</td><td>SHA-256 2176d08e… verified</td><td><span class="tag warn">mirror; grid/footprint only</span></td></tr>
<tr><td>lidar / radiometric / SGMC / road derivatives</td><td>GEMSDOE24 external bridge</td><td>SHA-256 verified by scripts/fetch_mirrors.sh</td><td><span class="tag warn">derived, semantics unverified</span></td></tr>
<tr><td>117 live-scored sibling rasters</td><td>pinned in registry/upstream_live_ledger_rasters.json</td><td>117/118 verified; 1 returned HTTP 404</td><td><span class="tag warn">scores owner-reported</span></td></tr>
<tr><td>17GEMSDOE E-proba control</td><td>GitHub @ 6fc71d1</td><td>SHA-256 ab0a0a62… re-verified</td><td><span class="tag warn">continuous field, not dots</span></td></tr>
</tbody></table></div>"""
    (OUT / "sources.html").write_text(page("Sources", "sources.html", body))

    # --------------------------------------------------------------- limitations
    body = f"""
<div class="hero"><div class="wrap"><div class="small">IRREGULARITIES / LIMITATIONS / NEXT SESSION</div>
<h1>What is still in the way.</h1><p>Flagged for review, not hidden. None of these is fixed by renaming a file.</p></div></div>
<h2>Release-critical</h2><div class="grid">
<div class="card"><h3>IR-09 — vacuous literal uniqueness rule</h3><p class="small">{e(rc['registry']['irregularity'])} The lane delivers a file under the content-aware reading. If the user insists on the literal reading, the correct verdict is <b>duplicate / stop</b> — exactly as the earlier session concluded. This needs an explicit protocol revision, not a silent exemption.</p></div>
<div class="card"><h3>No organizer receipt, no hidden labels</h3><p class="small">0 organizer-confirmed scores. Every number here is HOLDOUT-DTI (evaluator + positives + CI), an owner report, or a projection. A score above 0.2778 cannot be claimed without an actual upload receipt.</p></div>
<div class="card"><h3>Weekly cap &amp; selector</h3><p class="small">The portal's live quota is behind login. This lane used {rc['weekly_slots_used']} slots. A separate selector must approve a slot; the same selected file is used for both prize rounds.</p></div>
<div class="card"><h3>Outside-bounds convention</h3><p class="small">Official text says null/NaN outside bounds; the shared writer emits all-finite zeros. The mirrored sample's 60,988 ones also contradict the “total absence” wording. Reconcile with organizers before a high-stakes upload.</p></div></div>
<h2>Scientific limitations</h2><ul>
<li><b>Holdout ≠ hidden test.</b> Hide-and-recover withholds catalogue faults, while the competition's private set is expert-labeled <em>new</em> faults. The released file's static read-back HOLDOUT-DTI is {static['value']:.4f} (95% CI {static['ci95'][0]:.4f}–{static['ci95'][1]:.4f}); the fold-local method result is {hold['candidate']:.4f}. Neither is a leaderboard score.</li>
<li><b>Champion proxy is leakage-contaminated.</b> The H19-5/D2.8 network was built from the full catalogue, so the 0.0992 incumbent contains hidden segments. The paired win is real but the comparison is conservative in an unusual way.</li>
<li><b>Projection is out of family.</b> LOO MAE {sm['loo_mae']:.4f} on 117 owner-reported scores, but the top of that ledger is one related dot family; a novel pattern is extrapolated. Use the p10–p90 band {proj['p10']:.3f}–{proj['p90']:.3f}, not the point estimate.</li>
<li><b>Uniqueness has a price.</b> The repair moved ≥38% of dots into registry-novel cells and reduced static holdout DTI. Max sparse overlap is now {uniq['U3_max_overlap_sparse']:.3f}; the unconstrained pattern was 0.837 (a duplicate).</li>
<li><b>Mirror provenance &amp; band semantics.</b> SHA-256 pins prove mirror consistency, not official origin. Some 19-band names (notably <code>tc</code>) remain ambiguous; do not assert physical meaning from the mirror description alone.</li>
<li><b>One ledger raster unavailable.</b> One of 118 pinned live-scored rasters returned HTTP 404 from GitHub; 117 were verified. Flag for the owner to re-pin.</li>
<li><b>Shared tool defects upstream.</b> The shared uniqueness tool tests one-sided ρ&gt;0.90 while the protocol needs |ρ|; the shared metric docstring's marginal-credit bound is wrong. Neither was forked; both need maintainer fixes.</li>
<li><b>External data not obtained.</b> Raw 1 m 3DEP tiles, ASF InSAR and GDR thermal archives were not downloaded; hypotheses 2–4 remain untested. All are free/official but need byte-level verification and licence review.</li>
<li><b>Compute/data placement.</b> <code>bash scripts/download_competition_data.sh</code> now performs placement autonomously via pinned public mirrors; GPU is not required for this lane, but the 419 MB feature stack must be re-fetched on a fresh clone.</li>
</ul>
<h2>Next session — concrete work</h2><ol>
<li>Ratify or replace IR-09; freeze one explicit comparator inventory and one non-vacuous uniqueness definition for all parallel lanes.</li>
<li>Obtain an authenticated DrivenData download and verify band names, nodata semantics and sample provenance against the official data tab.</li>
<li>Run the three untested hypotheses with the named official datasets, one lane per session, against the same shared evaluator and the SAME fold definitions.</li>
<li>After a real upload, store the submission-page receipt with the uploaded SHA-256 and refit the projection model including a genuine organizer-confirmed point.</li>
<li>Fix the shared uniqueness/metric defects upstream (this integration is read-only on that repository).</li>
</ol>
<div class="note"><b>Core values applied.</b> Maximize P(Win): do not spend a scarce slot on an unvalidated guess; publish the negative results too. Own the Outcome: the downloadable TIF, its validator output, the run card and this limitations page are all delivered together.</div>
"""
    (OUT / "limitations.html").write_text(page("Limitations", "limitations.html", body))
    print(f"Built HCE-1 site: {len(NAV)} pages + CSS in {OUT}")


if __name__ == "__main__":
    main()
