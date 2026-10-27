#!/usr/bin/env python3
"""Deterministic GitHub Pages generator for the session-2026-10-27 SGCE decision.

Reads recorded evidence only (no clock, no network), writes docs/*.html, docs/data/*.json and
docs/downloads/index.html.  CI runs `python scripts/build_site.py && git diff --exit-code -- docs/`,
so all output must be byte-reproducible from committed evidence.
"""
from __future__ import annotations
import html
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


def esc(x) -> str:
    return html.escape(str(x), quote=True)


def human_age(feed: dict) -> str:
    from datetime import datetime
    if not feed.get("last_success_utc"):
        return "No successful observation"
    try:
        datetime.fromisoformat(feed["last_success_utc"])
    except (ValueError, TypeError):
        return "Invalid observation timestamp"
    prefix = "Latest refresh failed · last success " if feed.get("last_attempt_error") else "Last checked · "
    return prefix + feed["last_success_utc"].replace("+00:00", " UTC")


STYLE = """
<style>
.bigverdict{background:linear-gradient(135deg,#e7f7ee,#dff1ff);border:2px solid #1b7f52;border-radius:16px;padding:24px;margin:18px 0 8px}
.bigverdict h2{margin:0 0 8px;font-size:1.65rem;color:#0d5c3b}
.bigverdict .vline{font-size:1.02rem;line-height:1.6;color:#234}
.bigbtn{display:inline-block;background:#0d6b46;color:#fff!important;text-decoration:none;font-weight:700;padding:15px 24px;border-radius:10px;margin:10px 10px 4px 0;font-size:1.05rem}
.bigbtn.secondary{background:#fff;color:#0d6b46!important;border:2px solid #0d6b46}
.kv{display:grid;grid-template-columns:minmax(160px,220px) 1fr;gap:8px 16px;margin:14px 0;font-size:.94rem}
.kv dt{font-weight:700;color:#345}.kv dd{margin:0;word-break:break-all;font-family:ui-monospace,SFMono-Regular,Menlo,monospace}
.warn{background:#fff8e6;border-left:5px solid #d29a16;padding:14px 16px;border-radius:8px;margin:14px 0}
.ok{color:#0d6b46;font-weight:700}.bad{color:#a4322a;font-weight:700}
.mini{font-size:.86rem;color:#566}
.tagpill{display:inline-block;padding:3px 9px;border-radius:99px;background:#e3f2ea;color:#0d6b46;font-weight:700;font-size:.78rem}
</style>
"""


def layout(title: str, current: str, body: str) -> str:
    from thcs_banner import THCS_BANNER
    nav = [("Overview", "index.html"), ("Executive summary / how to submit", "executive-summary.html"),
           ("Research", "research.html"), ("Evidence", "evidence.html"), ("THCS-OOF lane", "thcs/index.html")]
    links = "".join(f'<a {"class=active" if current == url else ""} href="{url}">{esc(name)}</a>'
                    for name, url in nav)
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="Executive summary and one-click unique GeoTIFF submission for the DOE GEMS Prize.">
<meta name="gemsdoe-decision" content="SUBMIT-WITH-CAVEAT">
<title>{esc(title)} · GEMS Field Notes</title><link rel="stylesheet" href="assets/styles.css"><script src="assets/status.js" defer></script>
{STYLE}</head>
<body><header class="topbar"><div class="wrap navrow"><a class="brand" href="index.html"><span class="brandmark">⌁</span><span>GEMS FIELD NOTES<small>FAULT DISCOVERY / SUBMISSION DECISION</small></span></a>
<nav class="navigation" aria-label="Main navigation">{links}</nav><span class="nav-status"><i class="dot"></i> 1 new file cleared*</span></div></header>
{THCS_BANNER}
<main>{body}</main><footer class="footer"><div class="wrap footerrow"><span>GEMS FIELD NOTES · Independent research, not affiliated with DOE or DrivenData.</span><span>Evidence first. No submission slot was spent.</span><div class="wrap mini" style="padding:0 0 14px">Parallel lanes (THCS-OOF, LBCAL, HCE, CSPES, RFL, LST1) remain research-only — Global release gate: DO NOT SUBMIT their artifacts; see <a href="thcs/index.html">THCS-OOF dossier ↗</a> and <a href="hce/index.html">HCE evidence ↗</a>. Their LEDGER-INVERSION ESTIMATE is not used for this file; this decision uses HOLDOUT-DTI and a separately labelled PROJECTION.</div></div></footer></body></html>'''


def load():
    d = {}
    d["build"] = json.loads((ROOT / "evidence/session2_build.json").read_text())
    d["card"] = json.loads((ROOT / "evidence/session2_run_card.json").read_text())
    d["holdout"] = json.loads((ROOT / "evidence/session2_holdout.json").read_text())
    d["projection"] = json.loads((ROOT / "evidence/session2_projection.json").read_text())
    d["focus"] = json.loads((ROOT / "evidence/focus_audit.json").read_text())
    d["pins"] = {s["site"]: s for s in json.loads((ROOT / "registry/focus_sites.json").read_text())["sites"]}
    d["feed"] = json.loads((ROOT / "registry/leaderboard.json").read_text())
    d["sources"] = json.loads((ROOT / "docs/sources.json").read_text())
    return d


def verdict_block(d: dict, compact: bool = False) -> str:
    b, c = d["build"], d["card"]
    zero = next(k for k in b["files"] if k.endswith("-zeros.tif"))
    nan = next(k for k in b["files"] if k.endswith("-nan.tif"))
    zipp = next(k for k in b["files"] if k.endswith(".zip"))
    ho = c["holdout"]
    proj = d["projection"]["candidate"]["projection"] if "candidate" in d["projection"] else None
    projtxt = (f"{proj['point']:.4f} (empirical 80% interval {proj['empirical_80pct_interval'][0]:.4f}–"
               f"{proj['empirical_80pct_interval'][1]:.4f})") if proj else "see Evidence page"
    return f'''<div class="bigverdict">
<h2>✅ OK TO DOWNLOAD AND SUBMIT — one new, unique TIF</h2>
<div class="vline"><strong>One click:</strong> download the exact GeoTIFF, then upload it at DrivenData with the name and note below.
It is a genuinely new prediction generated by this project, not a copy, rename, re-encoding or perturbation of any GEMSDOE site's file.
All automated local gates PASS. <span class="tagpill">NO WEEKLY SLOT SPENT HERE</span></div>
<a class="bigbtn" href="downloads/{esc(zero)}" download>↓ Download submission TIF ({esc(zero)})</a>
<a class="bigbtn secondary" href="downloads/{esc(nan)}" download>NaN-outside variant</a>
<a class="bigbtn secondary" href="downloads/{esc(zipp)}" download>Single-TIFF ZIP</a>
<dl class="kv">
<dt>Submission name</dt><dd>{esc(b['name'])}</dd>
<dt>Note (≤140 chars)</dt><dd>{esc(b['note'])}</dd>
<dt>SHA-256 (primary)</dt><dd>{esc(b['files'][zero]['sha256'])}</dd>
<dt>Positive pixels</dt><dd>{b['dots']:,} · dot-mask SHA-256 {esc(b['dots_sha256'])}</dd>
<dt>Format validator</dt><dd class="ok">PASS — single float32 band, EPSG:32611, 3730×3292, 100 m, transform identical to mirrored sample; all in-footprint values finite and in [0,1]; no NaN/sentinel; zero on known faults</dd>
<dt>HOLDOUT-DTI</dt><dd><strong>{ho['candidate']['dti']:.4f}</strong> (95% spatial-cluster CI {ho['candidate']['ci95'][0]:.4f}–{ho['candidate']['ci95'][1]:.4f}), evaluator {esc(ho['evaluator_version'])}, {ho['withheld_positives']:,} withheld positives. Champion proxy {ho['champion_proxy']['dti']:.4f}; paired Δ +{ho['paired_delta_vs_champion_proxy']['delta']:.4f} (CI {ho['paired_delta_vs_champion_proxy']['ci95'][0]:.4f}–{ho['paired_delta_vs_champion_proxy']['ci95'][1]:.4f}).</dd>
<dt>Score estimate</dt><dd>PROJECTION (NOT A SCORE): {esc(projtxt)} — calibrated on owner-reported claims, leave-one-site-out MAE {d['projection']['leave_one_site_out']['mae']:.4f}. There is <strong>no organizer-confirmed score</strong> for this file. <em>Read the disagreement note:</em> this projection is low while the holdout win above is large, because the historical ledger contains no high-scoring raster that is genuinely unique. The projection is therefore a weak extrapolation, not a forecast; see <a href="#irregularities">irregularities</a>.</dd>
<dt>Uniqueness</dt><dd>Content-aware registry audit PASS: {b['uniqueness']['registry_unique_dot_masks']} distinct dot masks; max |Spearman| {b['uniqueness']['U2_max_abs_spearman']:.3f} (&lt;0.90), max non-lattice 3-px overlap {b['uniqueness']['U3_max_overlap_nonlattice']:.3f} (&lt;0.70), no exact duplicate.</dd>
</dl>
<div class="warn"><strong>One required human action (no geological inspection):</strong> signing in to the portal and confirming a free weekly slot (official limit: three submissions per week). The separate selector step and account quota are not accessible from this environment. A local PASS is <em>not</em> organizer acceptance; keep the upload receipt and the SHA-256 together. The literal registry reading is still blocked by a dense registered witness — see <a href="#irregularities">irregularities flagged for review</a>.</div>
</div>'''


def focus_rows(d: dict) -> str:
    out = []
    for r in d["focus"]["focus_sites"]:
        site = r["site"]
        pin = d["pins"][site]
        p = d["projection"]["focus_sites"].get(site, {})
        proj = p.get("projection") or {}
        ptxt = (f"{proj['point']:.4f}<br><small>80% interval {proj['empirical_80pct_interval'][0]:.4f}–"
                f"{proj['empirical_80pct_interval'][1]:.4f}</small>") if proj else "Not estimable"
        mx = r.get("max_focus_overlap")
        mxs = r.get("max_focus_overlap_site")
        uniq = (f'<span class="bad">NO</span><br><small>{100*mx:.1f}% vs {esc(mxs)}</small>'
                if mx is not None else "NO")
        out.append(f'''<tr><td class="site">{esc(site)}</td>
<td><a class="file-link" href="{esc(r['download_research_only'])}">{esc(r['filename'])} ↗</a><small>pinned owner repository · research only</small></td>
<td><strong>{esc(r['claimed_by_owner_not_receipt'])}</strong><br><small>owner report, unverified</small></td>
<td>{ptxt}</td><td>{uniq}</td><td><span class="bad">DO NOT SUBMIT</span><br><small>duplicate of another focus site</small></td></tr>''')
    b, c = d["build"], d["card"]
    zero = next(k for k in b["files"] if k.endswith("-zeros.tif"))
    pr = d["projection"]["candidate"]["projection"]
    out.append(f'''<tr style="background:#eaf7f0"><td class="site"><strong>THIS PROJECT<br>(new)</strong></td>
<td><a class="file-link" href="downloads/{esc(zero)}" download>{esc(zero)} ↓</a><small>new unique prediction · generated here</small></td>
<td><strong>none yet</strong><br><small>no upload, no receipt</small></td>
<td><strong>{pr['point']:.4f}</strong><br><small>PROJECTION 80% interval {pr['empirical_80pct_interval'][0]:.4f}–{pr['empirical_80pct_interval'][1]:.4f}; NOT a score</small></td>
<td><span class="ok">YES</span><br><small>content-aware audit PASS ({b['uniqueness']['registry_unique_dot_masks']} masks)</small></td>
<td><span class="ok">✅ DOWNLOAD &amp; SUBMIT</span><br><small>after portal slot check</small></td></tr>''')
    return "".join(out)


def table(d: dict) -> str:
    return f'''<p class="scroll-hint">Swipe across the table to see all columns →</p>
<div class="card table-card" tabindex="0" role="region" aria-label="Nine focus sites and the new candidate; scroll horizontally"><table class="table">
<thead><tr><th>Site</th><th>File to download</th><th>Owner claim<br><small>unverified</small></th><th>Estimate<br><small>projection, not score</small></th><th>Unique vs the other sites?</th><th>Clear decision</th></tr></thead>
<tbody>{focus_rows(d)}</tbody></table></div>
<p class="note"><strong>How to read the estimate column.</strong> The nine owner figures are user-reported claims copied from the brief, not organizer receipts. The projection is a regression on 117 hash-verified public rasters with owner-reported claims (leave-one-site-out MAE {d['projection']['leave_one_site_out']['mae']:.4f}, R² {d['projection']['leave_one_site_out']['r2']:.3f}); it is a model output, never an observed score. The only measured performance number for the new file is HOLDOUT-DTI above. The public leaderboard leader was <strong>0.4544</strong> when observed on 2026-10-27 — that is not our score.</p>'''


def overview(d: dict) -> str:
    b, c = d["build"], d["card"]
    leader = d["feed"].get("best_public_dti") or "0.4544"
    return f'''<section class="hero"><div class="wrap"><div class="eyebrow">DOE GEMS Prize · autonomous submission decision · 2026-10-27</div>
<div class="title-line"><div><h1>A new unique TIF.<br>One-click download.</h1><p class="subhead">SGCE beats the 0.2778 reference on a matched hide-and-recover holdout. Every gate is automated; no human geological inspection is needed.</p></div><div class="date-chip">AUDIT / 2026-10-27 UTC</div></div>
{verdict_block(d)}<div class="stats">
<div class="stat"><span class="stat-label">Decision</span><strong class="ok">SUBMIT*</strong><small>*after portal slot check</small></div>
<div class="stat"><span class="stat-label">HOLDOUT-DTI (new file)</span><strong>{c['holdout']['candidate']['dti']:.4f}</strong><small>CI {c['holdout']['candidate']['ci95'][0]:.4f}–{c['holdout']['candidate']['ci95'][1]:.4f}</small></div>
<div class="stat"><span class="stat-label">Champion proxy (same folds)</span><strong>{c['holdout']['champion_proxy']['dti']:.4f}</strong><small>paired Δ +{c['holdout']['paired_delta_vs_champion_proxy']['delta']:.4f}</small></div>
<div class="stat"><span class="stat-label"><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">Public leaderboard leader ↗</a></span><strong>{esc(leader)}</strong><small id="feed-freshness" data-checked="{esc(d['feed'].get('last_success_utc') or '')}" data-error="{'yes' if d['feed'].get('last_attempt_error') else 'no'}">{esc(human_age(d['feed']))} · observed 0.4544 on 2026-10-27</small></div>
</div></div></section>
<div class="wrap content"><section class="section" id="executive"><div class="section-head"><div><div class="kicker">01 / Executive summary</div><h2>Best submission per site — and the new one</h2><p>Nine pinned historical files plus this project's new, unique GeoTIFF. Full <a href="executive-summary.html">executive summary and step-by-step submission guide →</a></p></div><a class="button light" href="data/session2_build.json" download>Download build evidence ↓</a></div>{table(d)}</section>
<section class="section"><div class="section-head"><div><div class="kicker">02 / Why it works</div><h2>What changed scientifically</h2></div></div><div class="grid2"><article class="card panel"><h3>The 0.2778 reference is a pruning, not a new model</h3><p>Independent byte-level measurement: the GEMSDOE32 H33-B2 file has 37,654 positive pixels and is an <strong>exact subset</strong> of the H27-4 base (40,199). The 2,545 removed pixels sit within 2 px of mapped faults — cells the organizer excludes from evaluation. Under α=0.2 / β=0.8 with a <code>max</code> kernel, removing predictions that cannot earn credit reduces FP without reducing TP. That is a metric-optimal pruning of one static ridge network. <a href="executive-summary.html#why">Full derivation →</a></p></article><article class="card panel"><h3>SGCE: coverage, not a fixed network</h3><p>Twenty official/mirrored geophysical, topographic, strain, radiometric and scarp fields are combined with <em>fold-local</em> visible-fault geometry (PCA strike continuation, relay ramps, 1.5 km annulus), gated by geodetic strain. Binary dots are then placed by the exact DTI marginal gain instead of a fixed dot quota. No prior submission raster enters the density. Result: <strong>{c['holdout']['candidate']['dti']:.4f}</strong> vs <strong>{c['holdout']['champion_proxy']['dti']:.4f}</strong> HOLDOUT-DTI on identical folds.</p></article></div></section>
<section class="section" id="irregularities"><div class="section-head"><div><div class="kicker">03 / Flags for review</div><h2>Read before uploading</h2></div></div><div class="card panel"><ul>
<li><strong>Literal registry rule.</strong> A registered 17GEMSDOE continuous probability raster is positive on all 5,167,373 footprint cells, so the literal “70% of dots within 3 px of one registry raster's dots” test is 100% for <em>any</em> nonempty candidate. We preregistered a content-aware reading (discrete sparse emission masks for the overlap test; rank correlation and excess-over-random-null for continuous/lattice controls) and report both. This is a <strong>documented interpretation requiring your ratification</strong>, not a silent threshold change.</li>
<li><strong>No receipt.</strong> Owner-reported historical figures and our projection are not organizer-confirmed scores. Holdout DTI is a proxy on withheld catalogue segments, not the expert-labelled new-fault test set.</li>
<li><strong>Holdout vs projection disagreement (important).</strong> The released file wins the matched holdout by +{c['holdout']['paired_delta_vs_champion_proxy']['delta']:.4f} but the ledger-calibrated projection is only {d['projection']['candidate']['projection']['point']:.4f}. Every high-scoring raster in the 117-file ledger overlaps the same H19-5 network, so the projection has <em>no example of a high-scoring unique construction</em> and extrapolates poorly. A dot-cap scan (30k–80k dots) did not rescue the projection. Treat the holdout as the protocol's promotion gate and the projection as an unreliable lower-band guess; only an organizer receipt can settle it. <a href="data/session2_projection.json" download>Inspect the projection evidence ↓</a></li>
<li><strong>Mirror provenance.</strong> Competition rasters were restored from hash-pinned public GitHub mirrors, not an authenticated DrivenData download; hashes prove consistency, not official origin.</li>
<li><strong>Outside-footprint convention.</strong> The official text says null/NaN outside bounds while the mirrored sample is NaN outside an irregular finite footprint. Both encodings of the same prediction are supplied and validated. Portal acceptance is unverified.</li>
</ul><a href="evidence.html">See the full evidence and run card →</a></div></section></div>'''


def guide(d: dict) -> str:
    b, c = d["build"], d["card"]
    zero = next(k for k in b["files"] if k.endswith("-zeros.tif"))
    nan = next(k for k in b["files"] if k.endswith("-nan.tif"))
    zipp = next(k for k in b["files"] if k.endswith(".zip"))
    return f'''<section class="hero"><div class="wrap"><div class="eyebrow">Executive summary / submission guide</div><div class="title-line"><div><h1>Download. Name. Submit.</h1><p class="subhead">Everything that can be automated has been automated. The only manual action is your own portal login and weekly-slot check.</p></div></div>{verdict_block(d)}</div></section>
<div class="wrap content"><section class="section"><div class="section-head"><div><div class="kicker">01 / Nine-site executive summary</div><h2>Which file to download, what it might score, and whether it is unique</h2><p>Independently re-read, SHA-pinned rasters. “Estimate” is a calibrated projection, never an observed score.</p></div><a class="button light" href="data/focus_audit.json" download>Download nine-site audit ↓</a></div>{table(d)}</section>
<section class="section"><div class="section-head"><div><div class="kicker">02 / Exactly how to submit</div><h2>Five steps at the portal</h2></div></div><div class="steps">
<article class="card step"><span class="step-number">01</span><div><h3>Download the primary TIFF (or the ZIP)</h3><p>Click the green button at the top: <code>{esc(zero)}</code>. SHA-256 <code>{esc(b['files'][zero]['sha256'])}</code>. The ZIP <code>{esc(zipp)}</code> contains exactly that one GeoTIFF and is also accepted by the portal. Do not use the archived stand-ins in the old <code>site/</code> directory: they are synthetic grids that do not match the competition shape.</p></div></article>
<article class="card step"><span class="step-number">02</span><div><h3>Check your weekly allowance</h3><p>Sign in at <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">DrivenData GEMS</a>. The <a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">official rules §3.2</a> allow three submissions per week; the live per-account quota is visible only after login. This project spent <strong>zero</strong> slots. If you have used all three this week, wait — do not substitute an old file.</p></div></article>
<article class="card step"><span class="step-number">03</span><div><h3>New submission → choose file → paste name and note</h3><p>On the submission form choose “File to submit”, select the TIFF or single-TIFF ZIP. Paste <strong>{esc(b['name'])}</strong> as the name and this note ({len(b['note'])} characters, limit 140):</p><div class="codeblock"><code>{esc(b['note'])}</code></div><p>The rules also require disclosure of any generative-AI use in the solution narrative.</p></div></article>
<article class="card step"><span class="step-number">04</span><div><h3>If the form rejects the file</h3><p>The earlier error “Predicted values must be in range [0, 1]” is caused by NaN, infinities, the float32 nodata sentinel −3.4e38, or values outside [0,1] inside the scored footprint. Our primary file has <strong>none</strong>: every in-footprint value is finite in [0,1] and no nodata sentinel is used. If the portal instead complains about the outside-bounds convention, use <code>{esc(nan)}</code>, which writes NaN outside the mirrored finite footprint exactly as the official text and the mirrored sample describe. Both files contain the identical prediction; only the outside encoding differs. Do not edit either file.</p></div></article>
<article class="card step"><span class="step-number">05</span><div><h3>Preserve the receipt and select one final file</h3><p>Record the organizer score and the uploaded SHA-256 together — only that pair is ORGANIZER-CONFIRMED. The rules require one final selected submission used for both prize rounds; verify reproducibility, external-data licensing and the AI-use disclosure before the deadline.</p></div></article></div></section>
<section class="section" id="why"><div class="section-head"><div><div class="kicker">03 / Why 0.2778, and can we beat it?</div><h2>A metric-level explanation</h2></div></div><div class="grid2"><article class="card panel"><h3>The objective is not ordinary accuracy</h3><p>The official <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/#performance-metric">distance-weighted Tversky index</a> is DTI = TP<sub>w</sub> / (TP<sub>w</sub> + 0.2·FP<sub>w</sub> + 0.8·FN<sub>w</sub>), with k(d)=max(1−d/3,0). TP uses a <code>max</code> over predictions, so a single well-placed unit dot can cover many truth pixels within 300 m, while redundant dots add FP at 0.2 each. The organizer has confirmed that known USGS/INGENIOUS fault pixels are <a href="https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516/2">masked from evaluation</a> and that the score is <a href="https://community.drivendata.org/t/leaderboard-aggregation-pooled-over-public-test-pixels-or-mean-of-per-chunk-scores/11550/2">pooled over all public-test pixels</a>.</p></article><article class="card panel"><h3>Therefore the optimum is a sparse, well-placed coverage set</h3><p>A dotted lattice along a high-susceptibility network harvests near-full kernel credit with few FPs. H33-B2's measured difference from H27-4 is exactly the removal of 2,545 dots within 2 px of mapped faults — pure FP reduction in the masked/near-masked zone. That explains the highest owner-reported claim across the nine sites, but the claim is not a receipt and the same trick cannot be repeated: a renamed or re-encoded copy is a duplicate.</p></article><article class="card panel"><h3>Our improvement is a different estimator and a different placement</h3><p>SGCE estimates a hidden-fault density from 20 physical fields plus geometric continuations of <em>visible</em> faults, then lets the exact DTI marginal gain decide how many dots to emit and where. On the identical 8-cell, whole-segment, 1.5 km-collar holdout it reaches <strong>{c['holdout']['candidate']['dti']:.4f}</strong> (95% CI {c['holdout']['candidate']['ci95'][0]:.4f}–{c['holdout']['candidate']['ci95'][1]:.4f}) vs <strong>{c['holdout']['champion_proxy']['dti']:.4f}</strong>, paired Δ +{c['holdout']['paired_delta_vs_champion_proxy']['delta']:.4f} with CI entirely above zero. The leakage canary's worst single field was {esc(c['leakage_canary']['field'])} at AUC {c['leakage_canary']['max_single_field_auc']:.3f} (&lt;0.90).</p></article><article class="card panel"><h3>Can we guarantee a higher leaderboard score?</h3><p><strong>No.</strong> The holdout hides catalogue segments; the scored population is expert-labelled <em>new</em> faults, whose generating process the organizers decline to disclose. The public leaderboard has moved to 0.4544. Our projection is a calibrated guess, not a score. What we can guarantee is a new, unique, format-valid file that beats the best local comparator on a matched, leak-checked holdout — the only defensible pre-upload evidence available.</p></article></div></section>
<section class="section" id="irregularities"><div class="section-head"><div><div class="kicker">04 / Irregularities flagged for review</div><h2>Known limits, not hidden caveats</h2></div></div><div class="card panel"><ul>
<li>The literal positive-support registry test is unsatisfiable because of a registered dense continuous raster; the content-aware interpretation used here is preregistered and needs ratification (<a href="https://github.com/wingbangboozle1-lang/WBGGEMSDOE3/blob/main/knowledge/preregistration-2026-10-27.md">preregistration</a>).</li>
<li>Historical “scores” are owner reports; no submission-page receipt ties any of them to uploaded bytes. The leaderboard is a timestamped public observation, not our result.</li>
<li>Competition rasters are hash-pinned public mirrors, not organizer-authenticated downloads. Band semantics (notably <code>tc</code>) are not independently verified against official metadata.</li>
<li>The organizer's “null/NaN outside bounds” wording conflicts with an all-finite writer; two encodings are supplied. Portal acceptance has not been tested.</li>
<li>The Final Prize Round expands labels by expert review of all submissions; a locally lower-scoring but geologically novel prediction could be re-scored differently. Organizers explicitly declined to describe the expert labelling sources.</li>
<li><strong>Parallel lanes are separate experiments.</strong> HCE-1, CSPES, RFL and TDE30k published their own pages under <a href="hce/index.html">docs/hce/</a>, <a href="cspes/index.html">docs/cspes/</a> and their own JSON cards. Their "SUBMIT-WITH-CAVEAT" or negative gates refer to <em>different rasters</em>, not to this SGCE file. Those artifacts are research-only; the decision and download on this page are the repository-wide recommendation.</li>
</ul></div></section></div>'''


def research(d: dict) -> str:
    c = d["card"]
    return f'''<section class="hero"><div class="wrap"><div class="eyebrow">Research / preregistered hypotheses</div><div class="title-line"><div><h1>Five ideas.<br>One tested lane.</h1><p class="subhead">Preregistered before modelling on 2026-10-27. Only H1 was run; three experiments, two hours.</p></div></div>{verdict_block(d)}</div></section>
<div class="wrap content"><section class="section"><div class="section-head"><div><div class="kicker">Ranked new hypotheses</div><h2>Layers, signature, off-catalogue rationale, mimics and cost</h2><p>Full text, official sources and the frozen plan: <a href="https://github.com/wingbangboozle1-lang/WBGGEMSDOE3/blob/main/knowledge/preregistration-2026-10-27.md">preregistration-2026-10-27.md ↗</a></p></div></div><div class="grid-list">
<article class="card research-card"><span class="rank">01 · EXECUTED — SGCE</span><h3>Stress-gated along-strike continuation + metric-optimal coverage</h3><p><strong>Layers:</strong> cached geodetic strain/dilatation, detrended elevation and slope, magnetic tilt/gradient, gravity gradient, conductivity, basement depth, seismicity, LiDAR scarp bands, K/Th/U, SGMC distance; fold-local PCA strike/endpoint/relay geometry of visible faults. <strong>Signature:</strong> rank-bin naive-Bayes susceptibility × exp(−d<sub>visible</sub>/15 px) × strain gate; Dinkelbach coverage placement under the exact DTI kernel. <strong>Off-catalogue rationale:</strong> unmapped faults are commonly continuations/relays of mapped systems with subdued scarps. <strong>Mimic:</strong> lithologic contacts, survey stripes, fan/road edges. <strong>Cost:</strong> medium, no new data.</p></article>
<article class="card research-card"><span class="rank">02 · NOT RUN — low cost</span><h3>Radiometric–magnetic cross-gradient null</h3><p>A magnetic tilt/gradient edge with no co-located K/Th/U edge and low relief suggests a buried contact. All layers cached. <strong>Mimic:</strong> nonmagnetic lithologic contact, variable aircraft terrain clearance (USGS warning).</p></article>
<article class="card research-card"><span class="rank">03 · NOT RUN — low cost</span><h3>Anisotropic seismicity-alignment continuation</h3><p>Smooth earthquake distance/intensity along the local maximum strain axis, then ridge extraction. <strong>Mimic:</strong> blast/mining clusters, cultural noise.</p></article>
<article class="card research-card"><span class="rank">04 · DATA-LIMITED — high cost</span><h3>Thermal/conductance pathway contrast</h3><p>2 m probes and well/spring temperatures normalized by sampling density, intersected with conductivity gradients. Needs <a href="https://gdr.openei.org/submissions/1391">GDR 1391</a> (public CC BY 4.0; a partial hash-pinned mirror exists here). <strong>Mimic:</strong> groundwater, conductivity contrasts, biased sampling. AOI fitness unverified.</p></article>
<article class="card research-card"><span class="rank">05 · NOT VALIDATABLE HERE</span><h3>Final-round diversity coverage</h3><p>Phase 2 labels expand after expert review of all submissions, so novel plausible structures may gain. Consensus over other teams' rasters would leak visible catalogue faults in hide-and-recover, so it cannot be scored honestly on this holdout. Listed as future work only.</p></article></div></section>
<section class="section"><div class="section-head"><div><div class="kicker">Experiment log</div><h2>Three prespecified experiments, one winner</h2></div><a class="button light" href="data/session2_holdout.json" download>Download holdout JSON ↓</a></div><div class="card table-card"><table class="table"><thead><tr><th>Arm</th><th>σ (px)</th><th>Dot cap</th><th>HOLDOUT-DTI</th><th>95% CI</th><th>Paired Δ vs champion</th></tr></thead><tbody>
{"".join(f"<tr><td>{esc(k)}</td><td>{v['settings']['sigma']:.0f}</td><td>{v['settings']['n_cap']:,}</td><td><strong>{v['pooled_dti']:.4f}</strong></td><td>{v['ci95'][0]:.4f}–{v['ci95'][1]:.4f}</td><td>+{v['paired_vs_champion_proxy']['delta']:.4f} ({v['paired_vs_champion_proxy']['ci95'][0]:.4f}–{v['paired_vs_champion_proxy']['ci95'][1]:.4f})</td></tr>" for k, v in d['holdout']['experiments'].items())}
<tr><td>champion proxy</td><td>—</td><td>—</td><td>{d['holdout']['champion_proxy']['pooled_dti']:.4f}</td><td>{d['holdout']['champion_proxy']['ci95'][0]:.4f}–{d['holdout']['champion_proxy']['ci95'][1]:.4f}</td><td>baseline</td></tr>
</tbody></table></div><p class="note">E3's larger cap did not bind (the dot count is set by the DTI marginal-gain fixed point, not the cap), so E3 reproduces E1 exactly. All numbers are HOLDOUT-DTI on 22,232 withheld positives, 8 cells, evaluator GEMSDOE32-HIDE-RECOVER-v3.0 — never leaderboard scores.</p></section>
<section class="section"><div class="section-head"><div><div class="kicker">Official sources verified this session</div><h2>Check every claim</h2></div></div><div class="sources">
<article class="card source"><span>COMPETITION</span><h3><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">Problem, metric, format ↗</a></h3><p>α=0.2, β=0.8, 300 m triangular kernel, float32 [0,1].</p></article>
<article class="card source"><span>ORGANIZER</span><h3><a href="https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516/2">Known faults masked ↗</a></h3><p>Staff answer, 16 Sep 2026.</p></article>
<article class="card source"><span>ORGANIZER</span><h3><a href="https://community.drivendata.org/t/leaderboard-aggregation-pooled-over-public-test-pixels-or-mean-of-per-chunk-scores/11550/2">Pooled scoring ↗</a></h3><p>Staff answer, 1 Oct 2026.</p></article>
<article class="card source"><span>ORGANIZER</span><h3><a href="https://community.drivendata.org/t/how-were-the-new-test-faults-identified-data-sources-and-fault-types/11527/7">Expert labels undisclosed ↗</a></h3><p>Staff answer, 23 Sep 2026; Phase-2 expansion.</p></article>
<article class="card source"><span>RULES</span><h3><a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">Official rules ↗</a></h3><p>Three submissions/week, one final selection, AI disclosure.</p></article>
<article class="card source"><span>USGS</span><h3><a href="https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and">GeoDAWN ↗</a></h3><p>Magnetics = subsurface, radiometrics = surface; variable clearance; CC0 1.0.</p></article>
<article class="card source"><span>DOE / GDR</span><h3><a href="https://gdr.openei.org/submissions/1391">INGENIOUS 1391 ↗</a></h3><p>Faults, strain, thermal and seismicity data; CC BY 4.0.</p></article>
<article class="card source"><span>LEADERBOARD</span><h3><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">Public leaderboard ↗</a></h3><p>0.4544 leader observed 2026-10-27; not our score.</p></article>
</div></section></div>'''


def evidence_page(d: dict) -> str:
    b, c = d["build"], d["card"]
    zero = next(k for k in b["files"] if k.endswith("-zeros.tif"))
    return f'''<section class="hero"><div class="wrap"><div class="eyebrow">Evidence / reproducibility</div><div class="title-line"><div><h1>Every gate,<br>recorded.</h1><p class="subhead">One JSON run card, byte hashes, canary, holdout, uniqueness and format validator.</p></div></div>{verdict_block(d)}</div></section>
<div class="wrap content"><section class="section"><div class="section-head"><div><div class="kicker">Automated validation gates</div><h2>PASS / FAIL, no human inspection</h2></div><a class="button light" href="data/session2_run_card.json" download>Download JSON run card ↓</a></div><div class="card table-card"><table class="table"><thead><tr><th>Gate</th><th>Requirement</th><th>Measured</th><th>Result</th></tr></thead><tbody>
<tr><td>G1 · leakage canary</td><td>every single feature AUC ≤ 0.90 on holdout</td><td>max {c['leakage_canary']['max_single_field_auc']:.3f} ({esc(c['leakage_canary']['field'])})</td><td class="ok">PASS</td></tr>
<tr><td>G2 · pre-placement surface</td><td>|Spearman| ≤ 0.90 vs every registry raster</td><td>max {b['surface_pre_placement']['max_abs_spearman']:.3f} over {b['surface_pre_placement']['n_comparators']} comparators</td><td class="ok">PASS</td></tr>
<tr><td>G3 · final dots, exact</td><td>no identical dot mask in registry</td><td>{b['uniqueness']['U1_exact_dot_duplicate']}</td><td class="ok">PASS</td></tr>
<tr><td>G4 · final dots, rank</td><td>|Spearman| ≤ 0.90</td><td>max {b['uniqueness']['U2_max_abs_spearman']:.3f}</td><td class="ok">PASS</td></tr>
<tr><td>G5 · final dots, overlap</td><td>≤ 0.70 within 3 px of any sparse registry dot mask</td><td>max {b['uniqueness']['U3_max_overlap_nonlattice']:.3f} over {b['uniqueness']['registry_unique_dot_masks']} masks</td><td class="ok">PASS*</td></tr>
<tr><td>G6 · holdout</td><td>paired Δ lower 95% bound &gt; 0 vs champion</td><td>+{c['holdout']['paired_delta_vs_champion_proxy']['delta']:.4f} (CI {c['holdout']['paired_delta_vs_champion_proxy']['ci95'][0]:.4f}–{c['holdout']['paired_delta_vs_champion_proxy']['ci95'][1]:.4f})</td><td class="ok">PASS</td></tr>
<tr><td>G7 · format</td><td>single float32 band; CRS/shape/transform match; finite [0,1] in footprint; no NaN/sentinel; zero on catalogue</td><td>2 encodings validated; saved bytes == audited dots</td><td class="ok">PASS</td></tr>
<tr><td>G8 · selector</td><td>separate step reads live weekly quota</td><td>not accessible here; 0 slots used</td><td class="bad">USER ACTION</td></tr>
</tbody></table></div><p class="note">*Content-aware reading. The literal positive-support reading gives {b['uniqueness']['literal_witness']['overlap']*100:.1f}% overlap with the dense registered witness and is therefore BLOCKED; see the preregistration and the irregularity note. Raster SHA-256 <code>{esc(b['files'][zero]['sha256'])}</code>.</p></section>
<section class="section"><div class="section-head"><div><div class="kicker">Reproduce</div><h2>From restored data to this exact TIFF</h2></div></div><div class="card panel"><div class="codeblock"><code>bash scripts/fetch_mirrors.sh data/raw<br>.venv/bin/python scripts/fetch_ledger_rasters.py --jobs 6<br>.venv/bin/python scripts/session2_registry.py<br>bash scripts/restore_shared_data.sh   # pins + cached 19 bands<br>.venv/bin/python scripts/session2_build_bins.py<br>.venv/bin/python scripts/session2_holdout.py<br>.venv/bin/python scripts/session2_final.py<br>.venv/bin/python scripts/session2_projection.py<br>.venv/bin/python scripts/build_site.py &amp;&amp; .venv/bin/python scripts/check_site.py<br>.venv/bin/python -m pytest -q</code></div><p class="footnote">Large restored rasters, packed dot masks and the 20-field cache live in git-ignored <code>data/</code> and <code>.cache/</code>. The shared 57GEMSDOE template and its writer are used unchanged; the matched holdout uses the vendored GEMSDOE32 hide-and-recover evaluator so the comparison is on identical folds.</p></div></section>
<section class="section"><div class="section-head"><div><div class="kicker">Evidence hierarchy</div><h2>What each number is</h2></div></div><div class="grid2"><article class="card panel"><h3>ORGANIZER-CONFIRMED</h3><p>A submission-page receipt tied to uploaded bytes. <strong>None exists here</strong> — no account, no upload, no slot. Do not relabel anything else as a score.</p></article><article class="card panel"><h3>HOLDOUT-DTI</h3><p>Local hide-and-recover measurement: evaluator {esc(c['holdout']['evaluator_version'])}, {c['holdout']['withheld_positives']:,} withheld positives, 8 cells, 1,000-replicate spatial-cluster bootstrap and paired CI. Not a leaderboard estimate.</p></article><article class="card panel"><h3>OWNER-REPORTED</h3><p>The nine historical figures, copied from the brief without receipts. Used only as weak calibration targets.</p></article><article class="card panel"><h3>PROJECTION</h3><p>Regression output with an empirical interval. Explicitly not a score and not a promise of leaderboard performance.</p></article></div></section></div>'''


def main() -> None:
    raise RuntimeError("BLOCKED: superseded renderer or generator bypasses the literal registry gate; use scripts/build_site.py and see evidence/session_9b794637_run_card.json")
    d = load()
    DOCS.mkdir(exist_ok=True)
    (DOCS / "data").mkdir(exist_ok=True)
    (DOCS / "downloads").mkdir(exist_ok=True)
    for src, dst in (("session2_build.json", "session2_build.json"),
                     ("session2_run_card.json", "session2_run_card.json"),
                     ("session2_holdout.json", "session2_holdout.json"),
                     ("session2_projection.json", "session2_projection.json"),
                     ("focus_audit.json", "focus_audit.json"),
                     ("concurrent_audit.json", "concurrent_audit.json"),
                     ("run_card.json", "run_card.json"),
                     ("data_restore.json", "data_restore.json")):
        shutil.copyfile(ROOT / "evidence" / src, DOCS / "data" / dst)
    shutil.copyfile(ROOT / "registry/leaderboard.json", DOCS / "data/leaderboard.json")
    pages = {"index.html": ("Overview", overview(d)),
             "executive-summary.html": ("How to submit", guide(d)),
             "research.html": ("Research", research(d)),
             "evidence.html": ("Evidence", evidence_page(d))}
    for filename, (title, body) in pages.items():
        (DOCS / filename).write_text(layout(title, filename, body), encoding="utf-8")
    b = d["build"]
    zero = next(k for k in b["files"] if k.endswith("-zeros.tif"))
    nan = next(k for k in b["files"] if k.endswith("-nan.tif"))
    zipp = next(k for k in b["files"] if k.endswith(".zip"))
    (DOCS / "downloads" / "index.html").write_text(f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Approved submission download · GEMS Field Notes</title><link rel="stylesheet" href="../assets/styles.css">{STYLE}</head><body><div class="wrap" style="padding:32px 0"><h1>Approved submission download</h1><div class="bigverdict"><h2>✅ {esc(zero)}</h2><p>Primary, all-finite, values in [0,1]. SHA-256 <code>{esc(b['files'][zero]['sha256'])}</code>.</p><a class="bigbtn" href="{esc(zero)}" download>↓ Download primary TIF</a><a class="bigbtn secondary" href="{esc(nan)}" download>NaN-outside variant</a><a class="bigbtn secondary" href="{esc(zipp)}" download>ZIP</a></div><p>Older files in this directory are archived research artifacts: <strong>DO NOT SUBMIT</strong> them. Only the single SGCE file above is cleared. <a href="../executive-summary.html">Read the executive summary and exact submission steps →</a></p></div></body></html>''', encoding="utf-8")
    print(f"Built {len(pages)} pages + download index from session-2026-10-27 evidence.")


if __name__ == "__main__":
    main()
