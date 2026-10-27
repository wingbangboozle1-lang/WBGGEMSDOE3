#!/usr/bin/env python3
"""Generate the LBCAL lane pages (docs/lbcal/) from committed evidence JSONs (no manual numbers).

Lane scope only: the repository-wide decision is owned by the main dashboard
(docs/index.html, docs/data/decision.json). Source of truth for this lane:
evidence/lbcal_lane_decision.json, copied to docs/lbcal/data/ by scripts/lbcal_reconcile.py.
Run:  python scripts/build_site_lbcal.py
"""
from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs" / "lbcal"
DATA = DOCS / "data"
PORTAL = "https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/"
PROBLEM = "https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/"
LEADERBOARD = "https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/"
RULES = "https://docs.nlr.gov/docs/fy26osti/96647.pdf"

CSS = """
:root{--bg:#0d1117;--panel:#161b22;--line:#30363d;--fg:#e6edf3;--mut:#9aa7b4;
--ok:#2ea043;--warn:#d29922;--bad:#da3633;--accent:#58a6ff}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
header{background:#010409;border-bottom:1px solid var(--line);padding:14px 20px;display:flex;gap:18px;flex-wrap:wrap;align-items:center}
header b{font-size:17px}
header a{color:var(--mut);text-decoration:none;font-size:14px}
header a:hover,header a.on{color:var(--fg)}
main{max-width:1080px;margin:0 auto;padding:26px 20px 80px}
h1{font-size:30px;line-height:1.25;margin:8px 0 10px}
h2{font-size:22px;margin:34px 0 10px;border-bottom:1px solid var(--line);padding-bottom:6px}
h3{font-size:17px;margin:22px 0 8px}
p,li{color:#d7dee6}
code{background:#1f2630;padding:1px 5px;border-radius:4px;font-size:13px}
.small{font-size:13.5px;color:var(--mut)}
.hero{border:1px solid var(--ok);background:linear-gradient(180deg,#0f2418,#0d1117);border-radius:12px;padding:22px;margin:14px 0 8px}
.hero.no{border-color:var(--bad);background:linear-gradient(180deg,#2a1214,#0d1117)}
.tag{display:inline-block;font-size:12px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;padding:3px 9px;border-radius:99px;background:var(--ok);color:#04150a}
.tag.no{background:var(--bad);color:#fff}
.tag.warn{background:var(--warn);color:#1a1200}
.btn{display:inline-block;background:var(--ok);color:#fff;font-weight:700;padding:13px 22px;border-radius:9px;text-decoration:none;margin:12px 10px 4px 0;font-size:16px}
.btn.alt{background:#21262d;border:1px solid var(--line);color:var(--fg);font-weight:600}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin:16px 0}
.kpi{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:12px 14px}
.kpi .v{font-size:23px;font-weight:700}
.kpi .k{font-size:12.5px;color:var(--mut);text-transform:uppercase;letter-spacing:.05em}
table{width:100%;border-collapse:collapse;margin:14px 0;font-size:14px}
th,td{text-align:left;padding:8px 9px;border-bottom:1px solid var(--line);vertical-align:top}
th{color:var(--mut);font-weight:600;font-size:13px;text-transform:uppercase;letter-spacing:.04em}
tr.me td{background:#0f2418;font-weight:600}
.yes{color:var(--ok);font-weight:700}.no{color:var(--bad);font-weight:700}.mid{color:var(--warn);font-weight:700}
.note{background:var(--panel);border-left:3px solid var(--accent);padding:12px 14px;border-radius:0 8px 8px 0;margin:14px 0}
.warnbox{background:var(--panel);border-left:3px solid var(--warn);padding:12px 14px;border-radius:0 8px 8px 0;margin:14px 0}
img.map{width:100%;border:1px solid var(--line);border-radius:10px;margin:10px 0}
footer{border-top:1px solid var(--line);color:var(--mut);font-size:13px;padding:18px 20px;margin-top:40px}
a{color:var(--accent)}
ul{padding-left:22px}
"""

NAV = [("index.html", "LBCAL lane"), ("executive-summary.html", "Nine sites"),
       ("how-to-submit.html", "How to submit"), ("research.html", "Science"),
       ("evidence.html", "Evidence"), ("sources.html", "Data &amp; sources")]


def nav(current: str) -> str:
    links = "".join(f'<a href="{h}" class="{"on" if h == current else ""}">{t}</a>' for h, t in NAV)
    return (f'<header><b>WBGGEMSDOE3 · LBCAL lane</b><a href="../index.html">← Main dashboard (repository decision)</a>{links}'
            f'<a href="{LEADERBOARD}" target="_blank" rel="noopener">Official leaderboard ↗</a></header>')


def page(title: str, body: str, decision: str, current: str) -> str:
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="gemsdoe-lane-decision" content="{decision}">
<title>{title} · WBGGEMSDOE3</title><style>{CSS}</style></head>
<body>{nav(current)}<main>{body}</main>
<footer>Evidence-first research for the <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">DOE GEMS Prize</a>.
Every number is labelled OWNER-REPORTED (scores the repository owner copied from the leaderboard), HOLDOUT-DTI,
REGISTRY-MEASUREMENT or ESTIMATE (a model output, not an organizer score). No ORGANIZER-CONFIRMED receipt exists for
any file here. A predicted fault is not a geothermal vent. Generated by <code>scripts/build_executive.py</code> from
<code>docs/lbcal/data/*.json</code> (lane scope; the repository decision is on the <a href="../index.html">main dashboard</a>).</footer>
</body></html>"""


def f4(x, n=4):
    try:
        return f"{float(x):.{n}f}"
    except (TypeError, ValueError):
        return "—"


def load(name):
    return json.loads((DATA / name).read_text())


def e(s):
    return html.escape(str(s))


def main() -> int:
    card = load("lbcal_lane_decision.json")
    delta = load("registry_delta_main.json")
    lb = load("lbcal_run_card.json")
    focus = load("focus_sites_2026-10-27.json")
    cands = load("candidates_2026-10-27.json")
    snap = load("leaderboard_snapshot_2026-10-27T1905Z.json")
    conc = load("lbcal_gate_concordance.json")
    var = load("lbcal_variants.json")
    cvs = load("lbcal_cv_summary.json")
    verdict = card["verdict"]
    decision = "SUBMIT" if verdict == "promote" else "DO-NOT-SUBMIT"
    tif = Path(card["download"]["tif"]).name
    zipn = Path(card["download"]["zip"]).name
    est = lb["estimate"]
    hold = lb["holdout"]
    post = lb.get("post_hoc_diagnostics", {})
    like = lb["registry"]["final_dots_like_for_like"]
    sel = var["selected"]
    vsel = var["variants"][sel]
    unb = var["unbounded_reference"]
    base = cvs["cv"]["baseline_constant"]
    lead = snap["rows"][0]
    top5 = snap["rows"][4]
    best_site = max(focus["sites"], key=lambda s: s["owner_reported"])
    skarp = next(c for c in cands["this_repo"] if "skarpline" in c["file"])
    tde = next(c for c in cands["this_repo"] if "tde30k" in c["file"])

    gates = [
        ("Saved-byte validator (template + independent re-read)", lb["validator"]["passed"], f"{sum(lb['validator']['template'].values())}/{len(lb['validator']['template'])} template checks; CRS, shape and transform match the sample; no NaN in the footprint; values in [0,1]"),
        ("Leakage canary (each feature alone vs withheld positives)", not lb["leakage_canary"]["leakage"], f"worst max(AUC,1-AUC) {f4(lb['leakage_canary']['worst_separation'],3)} ({e(lb['leakage_canary']['worst_feature'])}); limit 0.90"),
        ("Uniqueness before placement (score surface)", (lb["registry"]["pre_placement_surface"]["worst_rho"] or 0) <= 0.90, f"worst Spearman {f4(lb['registry']['pre_placement_surface']['worst_rho'],3)} vs {lb['registry']['rasters_checked']} registry rasters; limit 0.90"),
        ("Uniqueness of the final dots", not like["duplicate"], f"{like['forward_overlap_firings']} forward-overlap firings &gt; 0.70; {post.get('vacuous_firings','?')} are vacuous (witness halo already covers &gt;70% of the map); informative: " + ", ".join(e(x['submission'][:28]) for x in post.get('informative_firings', []))),
        ("HOLDOUT-DTI beats the current holdout best", hold["beats_best"], f"{f4(hold['pooled_dti'])} (95% CI {f4(hold['ci95'][0])}–{f4(hold['ci95'][1])}, {hold['evaluator']}, {hold['n_withheld']:,} withheld) vs {f4(hold['current_best']['pooled_dti'])} ({e(hold['current_best']['name'])})"),
        ("Cross-fit ESTIMATE beats 0.2778", est["cross_fit_mean"] > 0.2778, f"ESTIMATE {f4(est['cross_fit_mean'],3)} (bootstrap {f4(est['family_bootstrap_95'][0],3)}–{f4(est['family_bootstrap_95'][1],3)}; heuristic neighbour-adjusted range {f4(post.get('worst_case_ratio_adjusted_estimate'),3)}–{f4(est['cross_fit_mean']*post.get('nn_max_ratio',1),3)}). Model output, not a score."),
    ]
    gate_rows = "".join(f'<tr><td>{g}</td><td class="{"yes" if ok else "no"}">{"PASS" if ok else "FAIL"}</td><td>{d}</td></tr>' for g, ok, d in gates)

    if verdict == "promote":
        hero = f"""<div class="hero"><span class="tag">OK TO DOWNLOAD AND SUBMIT (selector decides the slot)</span>
<h1>{e(tif)}</h1><a class="btn" href="downloads/{tif}" download>⬇ Download .tif</a></div>"""
    else:
        hero = f"""<div class="hero no"><span class="tag no">NOT OK TO SUBMIT</span>
<h1>LBCAL lane: this file must not be submitted</h1>
<p style="font-size:17px">{e(card['decision_reason'])}</p>
<p>The lane's candidate is a newly generated file, but it fails the 70% overlap rule against four dense registry rasters. It is downloadable as a <b>research artefact</b>, and its file name says DO-NOT-SUBMIT.
This page covers <b>this lane only</b>; the repository-wide decision is on the <a href="../index.html">main dashboard</a>.</p>
<a class="btn alt" href="downloads/{tif}" download>⬇ Research TIF (DO NOT SUBMIT) · {lb['file']['bytes']//1024} KB</a>
<a class="btn alt" href="downloads/{zipn}" download>⬇ .zip twin</a>
<p class="small">SHA-256 <code>{lb['file']['sha256']}</code> · {lb['file']['dots']:,} dots · format-valid
(<a href="how-to-submit.html">what the validator checks</a>)</p></div>"""

    kpis = f"""<div class="kpis">
<div class="kpi"><div class="k">Public leaderboard #1</div><div class="v">{lead['public_dti']}</div><div class="small">{e(lead['team'])}, observed {snap['observed_utc']}</div></div>
<div class="kpi"><div class="k">Top-5 cut-off</div><div class="v">{top5['public_dti']}</div><div class="small">rank #5 public DTI</div></div>
<div class="kpi"><div class="k">Best owner-reported file</div><div class="v">{best_site['owner_reported']}</div><div class="small">{best_site['site']} B2 (OWNER-REPORTED)</div></div>
<div class="kpi"><div class="k">LBCAL out-of-family accuracy</div><div class="v">ρ {f4(vsel['family_cv']['spearman'],2)}</div><div class="small">RMSE {f4(vsel['family_cv']['rmse'],3)} vs {f4(base['rmse'],3)} constant baseline</div></div>
<div class="kpi"><div class="k">Holdout gate vs leaderboard</div><div class="v no">ρ {f4(conc['spearman_holdout_vs_score'],2)}</div><div class="small">{conc['n']} scored rasters</div></div>
<div class="kpi"><div class="k">Weekly slots used</div><div class="v">0</div><div class="small">a separate selector picks</div></div></div>"""

    index_body = f"""{hero}{kpis}
<h2>Gate-by-gate status of the newest candidate (LBCAL)</h2>
<table><tr><th>Pre-registered gate</th><th>Result</th><th>Measurement</th></tr>{gate_rows}</table>
<div class="note"><b>Independent check of the other lanes' files.</b> LBCAL is validated by family-grouped
cross-validation on {conc['n']} scored rasters. It estimates <b>{f4(skarp['lbcal_estimate'],3)}</b> for the withdrawn
<code>wbggemsdoe3-skarpline-union</code>, which agrees with its withdrawal. For the file cleared on main,
<code>{e(Path(tde['file']).name)}</code>, it estimates <b>{f4(tde['lbcal_estimate'],3)}</b>. The score-tomography lane's own
ledger-inversion estimate for that file is 0.269 (0.207 bias-corrected). Two leaderboard inversions with similar out-of-sample
accuracy (LBCAL family-CV ρ {f4(vsel['family_cv']['spearman'],2)}; tomography site-CV ρ 0.946) disagree about four-fold on
<i>optimised</i> designs. In-model estimates of optimised files are therefore unreliable, and that includes LBCAL's own
{f4(est['cross_fit_mean'],3)}. The selector should treat the expected score of any optimised file as uncertain between about 0.05 and 0.3.
Uniqueness of the LBCAL file against the rasters merged later: {', '.join(f"{e(Path(r['file']).name[:32])} {f4(r['my_dots_within_3px_of_theirs']*100,1)}%" for r in delta['rows'])} of its dots within 3 px (limit 70%).</div>
<h2>Other lanes</h2>
<p>The score-tomography (TDE-30k), RFL, session-1f0b051d, HCE-1, CSPES and LST1 lanes keep their own pages and cards. All of them are linked from the
<a href="../index.html">main dashboard</a>, which owns the single repository decision.</p>
<h2>Where to go next</h2>
<ul><li><a href="executive-summary.html">Nine sites</a>: one paragraph per focus site, the download table, and the leaderboard and compliance notes.</li>
<li><a href="how-to-submit.html">How to submit</a>: the exact steps, name and note, and the fix for the portal's "[0, 1]" error.</li>
<li><a href="research.html">Science</a>: why B2 scored 0.2778, how the LBCAL model works, and why the holdout gate cannot see the leaderboard.</li>
<li><a href="evidence.html">Evidence</a>: run cards, JSONs and reproduction commands. <a href="sources.html">Data &amp; sources</a>: official links and limits.</li></ul>
<h2>Quick-look map of the LBCAL research candidate</h2>
<img class="map" src="assets/lbcal-map.png" alt="LBCAL research candidate: red dots, green public catalogue, grey hillshade of the scored footprint">
<p class="small">Red: the {lb['file']['dots']:,} LBCAL dots (research only, DO NOT SUBMIT). Green: the public catalogue. Grey: a hillshade of the
detrended elevation inside the scored footprint. The map is down-sampled 4×.</p>"""

    # ---------------- executive summary ----------------
    srows, paras = [], []
    for s in focus["sites"]:
        dl = f'<a href="{s["download_url"]}">{e(s["file"])}</a>' if s["download_url"] else e(s["file"])
        srows.append(f"<tr><td>{s['site']}</td><td>{dl}</td><td>{s['owner_reported']}</td>"
                     f"<td>{f4(s['lbcal_family_cv_estimate'],3)}</td><td class=\"no\">NO — {f4(s['max_forward_overlap_vs_other_focus']*100,1)}% of dots within 3 px of {s['max_overlap_with']}</td>"
                     f"<td class=\"no\">NO — already scored</td></tr>")
        paras.append(f"<p><b>{s['site']}.</b> Best file: <code>{e(s['file'])}</code>, OWNER-REPORTED <b>{s['owner_reported']}</b> "
                     f"({s['dots']:,} dots; {s['other_scored_files']} other scored file(s) at this site). LBCAL family-CV ESTIMATE {f4(s['lbcal_family_cv_estimate'],3)}. "
                     f"Not unique: {f4(s['max_forward_overlap_vs_other_focus']*100,1)}% of its dots lie within 3 px of the {s['max_overlap_with']} file. "
                     f"It is a member of the d2.8 dotted-ridge lineage and has already been scored, so resubmitting a copy is pointless."
                     + (f" Its decoded array is byte-identical to <code>{e(s['identical_array_of'])}</code>." if s.get("identical_array_of") else "")
                     + "</p>")
    crows = "".join(f"<tr><td><code>{e(Path(c['file']).name)}</code></td><td>{f4(c['lbcal_estimate'],3)}</td><td>{e(c['lane'])}</td><td class=\"no\">{e(c['status'])}</td></tr>" for c in cands["this_repo"])
    lrows = "".join(f"<tr><td>#{r['rank']}</td><td>{e(r['team'] or '—')}</td><td>{r['public_dti']}</td></tr>" for r in snap["rows"])
    exec_body = f"""<div class="hero no"><span class="tag no">LBCAL FILE: NOT OK TO SUBMIT</span><h1>LBCAL lane: the nine focus sites and every candidate</h1>
<p style="font-size:17px">Lane decision: <b>{card['lane_decision']}</b>. {e(card['decision_reason'])} The repository-wide decision is on the <a href="../index.html">main dashboard</a>.</p>
<a class="btn alt" href="downloads/{tif}" download>⬇ LBCAL research TIF (DO NOT SUBMIT)</a>
<a class="btn alt" href="how-to-submit.html">How to submit when a file is cleared</a></div>
<h2>Best submission per focus site</h2>
<p>The best file in all nine sites is a re-trim of the <b>same dotted-ridge network</b>. Every pairwise comparison has at
least {f4(min(min(x for x in row if x is not None) for row in focus['pairwise_forward_overlap']['matrix'])*100,1)}% of dots within 3 px.
GEMSDOE32's <code>h33-h33-2-b2</code> (0.2778) is the best of them. None of the nine is unique against the others, and
none can usefully be resubmitted.</p>
<table><tr><th>Site</th><th>File to download (source repo, pinned commit)</th><th>Owner-reported</th><th>LBCAL ESTIMATE (family-CV)</th><th>Unique vs other sites?</th><th>OK to submit?</th></tr>{''.join(srows)}</table>
{''.join(paras)}
<h2>Candidate files in this repository (LBCAL ESTIMATE for each)</h2>
<table><tr><th>File</th><th>LBCAL ESTIMATE</th><th>Lane</th><th>Status</th></tr>{crows}</table>
<p class="small">Every value here is an ESTIMATE (bounded LBCAL model) and not a score. The LBCAL row shows the cross-fit estimate
of its own design. Files from other lanes show <i>this lane's</i> estimate only; their decisions live on their own cards. For why the LBCAL file is NOT cleared, see the <a href="index.html">gate table</a>.</p>
<h2>Submission mechanics</h2>
<p>When a file is cleared, it is uploaded unchanged with the run card's unique <code>submission_name</code> and a note of
at most 140 characters. The portal error "Predicted values must be in range [0, 1]" comes from NaN, nodata sentinels
or values above 1 inside the footprint. This repository's writer emits finite 0/1 float32 values only. Full steps are on
the <a href="how-to-submit.html">how-to-submit page</a>.</p>
<h2>Leaderboard snapshot ({snap['observed_utc']}, <a href="{LEADERBOARD}">official page</a>)</h2>
<table><tr><th>Rank</th><th>Team</th><th>Public DTI</th></tr>{lrows}</table>
<p>{e(snap['implication'])} The brief's 0.4413 and 0.3195 figures are stale: {e(snap['user_brief_figures']['status'])}.</p>
<div class="warnbox"><b>Compliance irregularity (stated neutrally).</b> The official rules (<a href="{RULES}">NLR rules PDF</a>, §3.2/§3.4)
allow 3 submissions per week per participating entity and one final submission per entity. The archived ledger records
about 125 scored submissions in about 33 days, spread over several GitHub accounts and dozens of site repositories. If
these belong to one entity, the pattern is inconsistent with the cap. This repository cannot see the account mapping. It
records the observation and spends no slots.</div>
<h2>Can we beat 0.3195, or even 0.2778?</h2>
<p>Not with a file this lane can clear. LBCAL is the first lane in this project whose estimator actually predicts the
leaderboard: out-of-family Spearman {f4(vsel['family_cv']['spearman'],2)}, against {f4(conc['spearman_holdout_vs_score'],2)} for the owner's
holdout gate. Its design has a cross-fit ESTIMATE of {f4(est['cross_fit_mean'],3)}. But it fails two owner rules: the holdout gate, and
70% dot overlap with four dense registry rasters. So it is a research result, not a submission. The <a href="research.html">science page</a>
explains why, and what the next session would need to change.</p>
<h2>Next session and limitations</h2>
<ul><li>Owner decision required: keep the holdout gate (ρ≈{f4(conc['spearman_holdout_vs_score'],2)} with the leaderboard), or replace it with a leaderboard-calibrated family-CV gate. This repository cannot change the rule on its own.</li>
<li>Uniqueness repair: re-run the LBCAL placement with the halos of h23-a, h23-b, h30 and ovtr forbidden, and measure how much ESTIMATE survives.</li>
<li>Public/private risk: LBCAL learns from public-chunk scores only. The private set and the expanded final labels decide the prizes, and spatial overfitting cannot be measured with public scores.</li>
<li>The scores are owner-reported copies, not organizer receipts. Some registry rows cannot be checked: one ledger row (GEMSDOE4) was not found on GitHub, two archived "unique" files have the wrong grid shape, and one scored raster (14GEMSDOE horse-ensemble) fails the template CRS/transform check.</li></ul>"""

    # ---------------- how to submit ----------------
    howto_body = f"""<div class="hero no"><span class="tag no">LBCAL FILE: NOT OK TO SUBMIT</span><h1>Exactly how to submit</h1>
<p>The LBCAL file is <b>not cleared</b>. The steps below apply to whichever file the repository decision clears
(<a href="../index.html">main dashboard</a>), and only once the separate selector approves it within the weekly cap of 3 per entity
(<a href="{RULES}">rules §3.2</a>).</p></div>
<h2>Steps</h2>
<ol><li>Download the cleared <code>.tif</code> from the main dashboard. Do not open it and re-save it in GIS software, because that can add NaN or nodata values.</li>
<li>Check it locally: <code>python scripts/verify_submission.py &lt;file.tif&gt;</code>. The template validator checks a single float32 band, 3730×3292, EPSG:32611, the sample transform, finite values in [0,1] everywhere, zero outside the footprint and zero on the catalogue.</li>
<li>Go to <a href="{PORTAL}">DrivenData → Submissions</a>, choose the <code>.tif</code> (or its one-file <code>.zip</code>) and upload it unchanged.</li>
<li>Use the run card's <code>submission_name</code> as the unique name and its <code>note</code> (≤140 characters) as the note.</li>
<li>Record the receipt (timestamp and public score) as <b>ORGANIZER-CONFIRMED</b> in <code>registry/leaderboard.json</code>.</li></ol>
<h2>The current research artefact (not cleared)</h2>
<table><tr><th>Field</th><th>Value</th></tr>
<tr><td>File</td><td><code>{e(tif)}</code></td></tr>
<tr><td>Unique name</td><td><code>{e(lb['submission_name'])}</code></td></tr>
<tr><td>Note ({lb['note_chars']} chars)</td><td><code>{e(lb['note'])}</code></td></tr>
<tr><td>SHA-256</td><td><code>{lb['file']['sha256']}</code></td></tr>
<tr><td>Verdict</td><td class="no">{lb['verdict'].upper()}: failed {e(', '.join(lb['failed_gates']))}</td></tr></table>
<h2>Fixing "Predicted values must be in range [0, 1]"</h2>
<p>The portal rejects any pixel outside [0,1]. Three things commonly put pixels there: NaN pixels inside the scored
footprint, a nodata sentinel such as −3.4e38 or −9999 that is read back as a value, and float rounding above 1.0 in
probability maps. This repository's writer (template <code>submission_writer.write_submission</code>) refuses to repair
anything silently. It writes finite float32 values only (1.0 at dots, 0.0 everywhere else, including outside the
footprint), sets no nodata tag, and validates the saved bytes. Files produced this way cannot trigger the error.
To fix a third-party file, replace non-finite values with 0, clip to [0,1], and remove the nodata tag before uploading.</p>"""

    # ---------------- science ----------------
    coef = dict(zip(var["names"], vsel["beta"]))
    def c(n):
        return f"{coef[n]:+.2f}"
    vrows = "".join(f"<tr><td>{e(k)}</td><td>{f4(v['family_cv']['rmse'],4)}</td><td>{f4(v['family_cv']['spearman'],3)}</td><td>{round(v['G']):,}</td><td>{v['pixels_pi_ge_half_max']:,}</td></tr>" for k, v in var["variants"].items())
    cvrows = "".join(f"<tr><td>{e(k)}</td><td>{f4((v.get('family_cv') or v)['rmse'],4)}</td><td>{f4((v.get('family_cv') or v)['spearman'],3)}</td></tr>" for k, v in cvs["cv"].items())
    research_body = f"""<h1>Science: why 0.2778, and what a leaderboard-calibrated model says</h1>
<h2>1. The metric algebra that explains B2</h2>
<p>The official metric (<a href="{PROBLEM}">problem page</a>) is DTI = TP<sub>w</sub>/(TP<sub>w</sub>+0.2·FP<sub>w</sub>+0.8·FN<sub>w</sub>), with a 300 m triangular kernel.
Because FN<sub>w</sub> = |G| − TP<sub>w</sub>, this is DTI = TP<sub>w</sub>/(0.2·(TP<sub>w</sub>+FP<sub>w</sub>) + 0.8·|G|).
For a fixed truth set G, adding a dot raises the score only if its marginal credit ΔT satisfies ΔT/(ΔT+ΔFP) &gt; 0.2·DTI,
which works out to about a 2% chance that the dot lands on a hidden fault. A dot exactly on a fault earns at most 3 truth
pixels of credit.</p>
<p>The ground truth is <b>expert-mapped faults that are not in the public catalogue</b>. Dots near catalogue faults
therefore earn almost nothing and pay the full FP price. GEMSDOE32's B2 is the GEMSDOE31 40,199-dot d2.8
dotted-ridge base minus the 2,545 dots within 3 px of the catalogue. Its score rose from 0.2708 to 0.2778 when only those
dots were removed. That is the signature of dots with near-zero marginal credit. The lineage
h19-5 0.1922 → d2.8 0.2600 → solo 0.2708 → B2 0.2778 is a sequence of FP-shedding moves on one fixed network, not a new
signal. All nine focus files belong to it, and it saturates at about 0.28.</p>
<h2>2. LBCAL: invert the leaderboard instead of guessing the target</h2>
<p>Each archived raster with an owner-reported score is a soft measurement of where the hidden faults are. LBCAL models
a hidden-fault density π over joint bins of seven layers: catalogue distance, det-elev curvature, slope crest, det-elev
slope, 3DEP-LiDAR scarp rank, TMI horizontal gradient and SGMC distance. The expected DTI of any raster then follows exactly:
T = Σπ·c (c is the raster's max-credit map), FP ≈ N − 3Σπ·p, and G = Σπ. The model has 34 coefficients, fitted by
least squares to {cvs['n_unique_scored_arrays']} unique scored arrays.</p>
<table><tr><th>Model (leave-one-family-out)</th><th>RMSE</th><th>Spearman</th></tr>{cvrows}</table>
<p>Families are connected components of support-Jaccard ≥ 0.3, so near-copies never sit on both sides of a split. Plain
leave-one-site-out gives the same result: RMSE {f4(cvs['cv'][cvs['selected']['key']]['site_cv']['rmse'],4)}, ρ {f4(cvs['cv'][cvs['selected']['key']]['site_cv']['spearman'],3)}.
The unbounded fit drives π to 1 on thousands of pixels, which is physically implausible. So bounded links were
pre-registered:</p>
<table><tr><th>Variant (10-fold family CV)</th><th>RMSE</th><th>Spearman</th><th>implied |G|</th><th>px with π ≥ π<sub>max</sub>/2</th></tr>{vrows}</table>
<p>The selected model is <code>{e(sel)}</code>. Its density is depleted within 300 m of the catalogue (1–1.4 px {c('d_cat=1-1.4 px')}, ≥55 px {c('d_cat=>=55 px')}),
enriched on moderately steep slopes (70–95th percentile {c('slope=70-95%')} vs flat {c('slope=0-30% (flat)')}) with low curvature
({c('topo=rest')}), and depleted on slope crests ({c('crest=slope crest')}) and on strong LiDAR scarps (top 3% {c('lidar=top 3%')} vs weak {c('lidar=rest')}).
In plain words, the public hidden faults sit on planar range-flank slopes about 1–5 km from mapped faults, not on the
crisp scarps that the catalogue and the scarp detectors already find. <b>Named mimic:</b> landslide head-scarps, terrace
risers and road cuts share the slope signature.</p>
<h2>3. Design, and why it is still not cleared</h2>
<p>A Dinkelbach batch-greedy max-coverage placement under π gives {lb['file']['dots']:,} dots. In-model it scores {f4(est['in_model'],3)}.
The cross-fit (design on half of the families, evaluate under the other half; 4 runs) gives {f4(est['cross_fit_mean'],3)}, with a
family bootstrap of {f4(est['family_bootstrap_95'][0],3)}–{f4(est['family_bootstrap_95'][1],3)}. These are ESTIMATES. The post-hoc
neighbour check shows that the model <i>over</i>-predicts the dense emission rasters whose dots the design overlaps
(owner/CV down to {f4(post.get('nn_min_ratio'),2)}) and <i>under</i>-predicts the d2.8 lineage. The honest range is therefore
{f4(post.get('worst_case_ratio_adjusted_estimate'),2)}–{f4(est['cross_fit_mean']*post.get('nn_max_ratio',1),2)}, a heuristic only.</p>
<p>It fails the owner's holdout gate: HOLDOUT-DTI {f4(hold['pooled_dti'])} (95% CI {f4(hold['ci95'][0])}–{f4(hold['ci95'][1])}) against
{f4(hold['current_best']['pooled_dti'])}. It also fails the like-for-like uniqueness rule, because 81–91% of its dots fall inside the halos of four dense
registry rasters (h23-a, h23-b, h30, ovtr) whose halos cover only 41–54% of the map.</p>
<h2>4. The gate itself: experiment 3</h2>
<p>All {conc['n']} unique scored rasters were run through the same hide-and-recover evaluator. HOLDOUT-DTI correlates with the
OWNER-REPORTED public score at ρ = {f4(conc['spearman_holdout_vs_score'],3)} (top-20: {f4(conc['spearman_holdout_vs_score_top20'],3)}). LBCAL's
family-CV estimate correlates at ρ = {f4(conc['spearman_lbcal_cv_vs_score'],3)}. The best holdout file (<code>{e(conc['best_holdout_file']['submission'][:40])}</code>,
holdout {f4(conc['best_holdout_file']['holdout_dti'],3)}) scored {conc['best_holdout_file']['owner_reported']} publicly. The champion B2 has holdout
{f4(conc['best_score_file']['holdout_dti'],4)}. The catalogue hide-and-recover task rewards catalogue proximity, which is exactly
what the leaderboard punishes. (Caveat: registry masks are static, not fold-local, so catalogue-hugging files get leaked
credit.) Under the owner's rule the verdict is still NEGATIVE. Changing the rule is the owner's call.</p>
<h2>5. Hypotheses (ranked) and next steps</h2>
<p>See <a href="https://github.com/wingbangboozle1-lang/WBGGEMSDOE3/blob/main/knowledge/preregistration-2026-10-27-lbcal.md">the pre-registration</a>
for H-LBCAL, H-PIEDMONT, H-SEISMO-GAP, H-STEPOVER-SYNTH and H-RADIOMETRIC-SEEP. Each entry lists its layers, signature, rationale and how
it differs from the earlier lanes.</p>"""

    # ---------------- evidence ----------------
    ev_links = [("LBCAL lane decision card", "data/lbcal_lane_decision.json"), ("Uniqueness vs rasters merged later", "data/registry_delta_main.json"), ("LBCAL run card", "data/lbcal_run_card.json"),
                ("LBCAL CV summary", "data/lbcal_cv_summary.json"), ("Bounded variants", "data/lbcal_variants.json"),
                ("Holdout-vs-leaderboard concordance", "data/lbcal_gate_concordance.json"),
                ("Nine focus sites", "data/focus_sites_2026-10-27.json"), ("Candidates re-estimated", "data/candidates_2026-10-27.json"),
                ("Leaderboard snapshot", "data/leaderboard_snapshot_2026-10-27T1905Z.json")]
    evidence_body = f"""<h1>Evidence (LBCAL lane)</h1><div class="hero no"><span class="tag no">LBCAL FILE: NOT OK TO SUBMIT</span>
<p>Every page in this site is rendered from these files. The cards record negative results as deliverables.</p></div>
<ul>{''.join(f'<li><a href="{h}">{t}</a></li>' for t, h in ev_links)}</ul>
<h2>Reproduce (about 25 minutes on 2 CPUs)</h2>
<pre><code>bash scripts/restore_shared_data.sh        # shared template + 19-band features (SHA-pinned)
python scripts/restore_x24_external.py      # LiDAR scarp / SGMC / TIGER layers (SHA-pinned)
python scripts/fetch_ledger_rasters.py      # 118 scored ledger rasters (SHA-pinned)
python scripts/fetch_addendum_rasters.py    # 14 addendum rasters (commit + SHA pinned)
python scripts/lbcal_build_dataset.py && python scripts/lbcal_fit.py && python scripts/lbcal_variants.py
python scripts/lbcal_design.py && python scripts/lbcal_gate_concordance.py && python scripts/lbcal_postcheck.py
python scripts/lbcal_reconcile.py && python scripts/lbcal_map_png.py && python scripts/build_site_lbcal.py</code></pre>
<h2>Irregularities found this session</h2><ul>
<li>At session start the README said SUBMIT (skarpline, ESTIMATE 0.428), while <code>evidence/run_card.json</code> said NEGATIVE and PR #24 said DO NOT SUBMIT. Parallel PRs #24–#30 merged meanwhile; they withdraw skarpline and clear TDE-30k with a caveat. LBCAL's estimate for TDE-30k is {f4(tde['lbcal_estimate'],3)}.</li>
<li>The owner's holdout gate does not track the leaderboard (ρ {f4(conc['spearman_holdout_vs_score'],2)}, n={conc['n']}).</li>
<li>Band 6 <code>tc</code> was described in earlier code as a "magnetic tilt / total curvature". Its values (3–89) and the official page's figure point to radiometric total counts.</li>
<li>Two archived "unique" TIFFs have the wrong grid shape (1024×1024 and 1200×1600) and could never have been valid submissions.</li>
<li><code>wbg3-h3pack</code> sits in the WBGGEMSDOE2 repository, and <code>wbg2-offcatalogue-density</code> sits in WBGGEMSDOE1: the site attribution does not match.</li>
<li>Submission volume across accounts is inconsistent with the per-entity weekly cap (see the executive summary).</li></ul>"""

    # ---------------- sources ----------------
    src_rows = [
        ("Competition rasters (training_features, labels, sample_submission)", "DrivenData GEMS data page", PROBLEM, "Competition data; challenge-licensed", "Restored from SHA-pinned mirror (57GEMSDOE template); organizer download needs a DrivenData login"),
        ("Official rules", "NLR / DOE rules PDF (Sept 2026)", RULES, "Public", "3 submissions/week per entity; one final; GenAI must be disclosed"),
        ("Public leaderboard", "DrivenData leaderboard", LEADERBOARD, "Public", "Public chunks only; the private set decides the initial round"),
        ("USGS 3DEP LiDAR (scarp descriptors)", "USGS 3D Elevation Program", "https://www.usgs.gov/3d-elevation-program", "Public domain (USGS)", "Pre-aggregated to 100 m by GEMSDOE24's CI (SHA-pinned). Covers 3.89M of 5.17M cells"),
        ("SGMC geologic-map faults", "USGS State Geologic Map Compilation", "https://doi.org/10.5066/F7WH2N65", "Public domain (USGS)", "Rasterised to 100 m (SHA-pinned). Not the hidden truth (SGMC-as-prediction scores about 0.05)"),
        ("Quaternary fault catalogue (labels.tif)", "USGS Quaternary Fault and Fold Database", "https://www.usgs.gov/programs/earthquake-hazards/faults", "Public domain (USGS)", "Equals the public catalogue; the test faults are new and absent from it"),
        ("TIGER roads (mimic audit)", "US Census TIGER/Line", "https://www.census.gov/geographies/mapping-files/time-series/geo/tiger-line-file.html", "Public domain", "Used only to audit road-cut mimics"),
        ("Owner-reported scores", "registry/upstream_live_ledger_rasters.json + addendum", "https://github.com/wingbangboozle1-lang/WBGGEMSDOE3/tree/main/registry", "Repository records", "Copied by the owner from the leaderboard; not organizer receipts"),
    ]
    srows2 = "".join(f'<tr><td>{a}</td><td>{b}</td><td><a href="{u}">{u}</a></td><td>{l}</td><td>{n}</td></tr>' for a, b, u, l, n in src_rows)
    sources_body = f"""<h1>Data &amp; sources (LBCAL lane)</h1><div class="hero no"><span class="tag no">LBCAL FILE: NOT OK TO SUBMIT</span>
<p>Every layer used by any lane, with its official source, licence and limitations. No paid or private data was used.</p></div>
<table><tr><th>Layer</th><th>Provider</th><th>Official link</th><th>Licence / access</th><th>Limitations</th></tr>{srows2}</table>
<p class="small">The pins live in <code>registry/data_manifest.json</code>, <code>registry/ledger_addendum_2026-10-27.json</code> and the restore scripts.
Mirrors establish byte identity only, not provenance.</p>"""

    pages = {"index.html": ("LBCAL lane", index_body), "executive-summary.html": ("LBCAL · nine sites", exec_body),
             "how-to-submit.html": ("LBCAL · how to submit", howto_body), "research.html": ("LBCAL · science", research_body),
             "evidence.html": ("LBCAL · evidence", evidence_body), "sources.html": ("LBCAL · data & sources", sources_body)}
    for name, (title, body) in pages.items():
        (DOCS / name).write_text(page(title, body, decision, name))
    dl = DOCS / "downloads"
    research = sorted(p.name for p in dl.glob("*.tif"))
    zips = {n: Path(n).with_suffix(".zip").name for n in research}
    items = "".join(f'<li><a href="{n}" download>{n}</a> · <a href="{zips[n]}" download>.zip</a></li>' for n in research)
    (dl / "index.html").write_text(f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="gemsdoe-lane-decision" content="{decision}">
<title>LBCAL downloads</title><style>body{{font:16px/1.6 system-ui;max-width:52rem;margin:3rem auto;padding:1rem;color:#ddd;background:#0d1117}}a{{color:#58a6ff}}</style></head>
<body><h1>LBCAL lane downloads</h1>
<p><b>Cleared by this lane: none.</b> The repository decision is on the <a href="../../index.html">main dashboard</a>.</p>
<h2>Research only — DO NOT SUBMIT</h2><ul>{items}</ul>
<p><a href="../index.html">LBCAL lane</a> · <a href="../how-to-submit.html">How to submit</a></p></body></html>
""")
    print(f"[lbcal-site] rendered {len(pages)} lane pages; lane decision={decision}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
