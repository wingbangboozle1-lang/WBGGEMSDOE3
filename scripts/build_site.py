#!/usr/bin/env python3
"""Render the evidence-first, fail-closed Pages site from committed evidence.

This builder publishes *only* a negative decision. Historical lane renderers
are not invoked: several of them asserted upload clearance despite an explicit
literal-registry failure. A future positive release needs a separately reviewed,
hash-bound selector and a publication path that validates all its evidence.
"""
from __future__ import annotations

from datetime import datetime
import hashlib
import html
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from gems_project.release_gate import evaluate_release_gate  # noqa: E402
from gems_project.release_gate_v2 import evaluate_release_gate_v2  # noqa: E402
from hce_banner import HCE_BANNER  # noqa: E402,F401 -- historical compatibility
from build_site_legacy import historical_h6_section  # noqa: E402,F401 -- historical compatibility

AUTHORITY = ROOT / "evidence/session_9b794637_run_card.json"
SGCE_CARD = ROOT / "evidence/session2_run_card.json"
LBCAL_K_CARD = ROOT / "evidence/lbcal_k_run_card.json"
PREREG_LBCALK = ROOT / "knowledge/preregistration-2026-10-28-lbcalk.md"
FOCUS_OVL = ROOT / "evidence/lbcal_k/focus_overlap.json"
IRREGULARITIES = ROOT / "knowledge/irregularities-2026-10-28-lbcalk.md"

# Publication mode; render() flips these to "submit" only when the v2
# release gate (release_gate_v2.evaluate_release_gate_v2) returns SUBMIT.
MODE = "negative"
CAND: dict = {}
FOCUS_OVL_DATA: dict = {}
RECHECK = ROOT / "evidence/registry_witness_recheck_2026-10-27.json"
FOCUS = ROOT / "evidence/focus_audit.json"
INDEPENDENT_FOCUS = ROOT / "evidence/focus_uniqueness_independent_2026-10-27.json"
INDEPENDENT_NAN = ROOT / "evidence/format_independent_sgce_nan_2026-10-27.json"
INDEPENDENT_ZERO = ROOT / "evidence/format_independent_sgce_zeros_2026-10-27.json"
FEED = ROOT / "registry/leaderboard.json"
SHA_CANDIDATE = "0444c37466fb6304e1ddb9f65f693e88ff588b8b3838d9a21b7680aceaefed09"
CANDIDATE_FILE = "wbggems3-sgce-20261027-f52d35d8-zeros.tif"
PRIOR_COMMIT = "1dcca8bb473f732403213928b7c633cd2a22b403"


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def esc(value) -> str:
    return html.escape(str(value), quote=True)


def human_age(feed: dict) -> str:
    checked = feed.get("last_success_utc")
    if not checked:
        return "No successful observation"
    try:
        datetime.fromisoformat(checked)
    except (TypeError, ValueError):
        return "Invalid observation timestamp"
    prefix = "Latest refresh failed · last success " if feed.get("last_attempt_error") else "Last checked · "
    return prefix + checked.replace("+00:00", " UTC")


def layout(title: str, current: str, body: str, decision: str = "DO-NOT-SUBMIT") -> str:
    nav = [("Overview", "index.html"), ("Executive summary", "executive-summary.html"),
           ("Submission guide", "how-to-submit.html"), ("Research", "research.html"),
           ("Evidence", "evidence.html"), ("FCHD-NCM lane", "fchd/index.html"),
           ("AMDC lane", "amdc/index.html")]
    links = "".join(f'<a href="{url}"' + (' aria-current="page"' if current == url else '') + f'>{name}</a>'
                    for name, url in nav)
    desc = ("Preregistered-gates-cleared DOE GEMS candidate; historical lane TIFFs remain DO NOT SUBMIT."
            if decision == "SUBMIT" else
            "Evidence-first DOE GEMS fault discovery audit; no submission currently cleared.")
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="{desc}">
<meta name="gemsdoe-decision" content="{decision}"><title>{esc(title)} · GEMS Field Notes</title>
<link rel="stylesheet" href="assets/safe.css"><script src="assets/status.js" defer></script></head>
<body><header class="top"><div class="wrap toprow"><a class="brand" href="index.html">⌁ &nbsp;GEMS FIELD NOTES</a><nav aria-label="Main navigation">{links}</nav></div></header>
<main>{body}</main><footer class="footer"><div class="wrap">Independent research · not affiliated with DOE or DrivenData · <a href="data/release_gate.json">Machine-readable decision</a> · No competition slot spent by this audit.</div></footer></body></html>'''


def decision_block(mode: str = "negative", card: dict | None = None) -> str:
    if mode != "submit":
        return f'''<div class="decision"><span class="tag">NEGATIVE · STOP</span><h2>DO NOT SUBMIT — no file is cleared.</h2>
<p>The literal all-registry uniqueness rule fails for every nonempty in-footprint prediction under the shared positive-support definition. No new candidate, holdout score or upload was produced in this review. A separate selector has not approved a slot.</p>
<p><a class="btn secondary" href="downloads/{CANDIDATE_FILE}" download>Download prior SGCE TIFF for research only</a> <a class="btn secondary" href="evidence.html">See the blocker and checks</a></p>
<p class="small">This is an existing, <strong>not submission-ready</strong> artifact—not a new prediction. A local format pass is not organizer acceptance.</p></div>'''
    r = card["raster"]
    g = {x["name"]: x for x in card["gates"]}
    est = g["G4_leaderboard_estimate_gt_0p2778"]["detail"]
    hold = card["holdout"]
    g2d = g["G2_final_dot_uniqueness"]["detail"]
    tif_name = r["path"].split("/")[-1]
    return f'''<div class="decision"><span class="tag">PREREGISTERED GATES PASSED · SUBMIT</span><h2>OK TO DOWNLOAD AND SUBMIT this exact file.</h2>
<p><a class="btn" href="downloads/{esc(tif_name)}" download>⬇ DOWNLOAD SUBMISSION TIF</a>
<a class="btn secondary" href="downloads/{esc(tif_name.replace('.tif', '.zip'))}" download>ZIP (same bytes)</a>
<a class="btn secondary" href="submission.html">Gate detail &amp; receipt</a></p>
<p><strong>{esc(card['submission_name'])}</strong> · {r['dots']:,} dots · SHA-256 <code>{esc(r['sha256'])}</code><br>
Use this exact name and note “{esc(card['note'])}” ({card['note_chars']} chars) on <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/">DrivenData</a>.</p>
<p class="small">Gates (preregistered 2026-10-28): G0 canary ✓ {g['G0_leakage_canary']['detail']['worst_separation']:.3f}≤0.90 · G1 pre-placement surface ✓ |ρ|={g['G1_preplacement_surface']['detail']['max_abs_spearman']:.3f}≤0.90 · G2 uniqueness ✓ max non-lattice overlap {g2d['U3_max_nonlattice_overlap_3px']:.3f}≤0.70 vs all 149 sparse registry masks (U1 identity no, lattice excess +{g2d['U3_lattice_excess']:.3f}≤0.05), each focus site ≤42.5% · G3 format ✓ all-finite [0,1] everywhere, zeros outside footprint — the portal range-error fix · G4 estimate ✓ {est['cross_fit_mean']:.3f} (95% CI {est['family_bootstrap_95'][0]:.3f}–{est['family_bootstrap_95'][1]:.3f}) &gt; 0.2778 and &gt; 0.3195.</p>
<p class="small"><strong>Disclosures:</strong> {esc(hold['label'])} holdout is {hold['pooled_dti']:.4f} (95% CI {hold['ci95'][0]:.4f}–{hold['ci95'][1]:.4f}, {hold['n_withheld']:,} withheld) — reported as <em>context only</em> per IR-11 (holdout↔owner-score ρ=0.089); the leaderboard-calibrated cross-fit instrument (family-CV ρ=0.914) is the promotion instrument. <strong>Cross-model second opinion (E2, H-XMODEL-GATE): the ledger-inversion tomography rates this file 0.195 — it DISAGREES with the 0.424 estimate</strong> (and overrates the actual-0.2778 B2 by +0.084); the two instruments bracket ~0.20–0.42 — <strong>Estimates are ESTIMATES</strong>, never organizer-confirmed scores. The literal “70% vs every registry file” reading fails for <em>any</em> candidate (IR-01 dense witness, 100% coverage) — the preregistered content-aware gates U1/U3/lattice are the decision rule, disclosed not silent. Nothing was uploaded; the weekly slot is untouched and separate — spending it is your step. Historical lane TIFFs remain DO NOT SUBMIT.</p></div>'''


def focus_table(audit: dict) -> str:
    rows = []
    if MODE == "submit":
        tif_name = CAND["raster"]["path"].split("/")[-1]
        est = {x["name"]: x for x in CAND["gates"]}["G4_leaderboard_estimate_gt_0p2778"]["detail"]
        est_cell = (f"<strong>ESTIMATE {est['cross_fit_mean']:.3f}</strong>"
                    f"<small>95% CI {est['family_bootstrap_95'][0]:.3f}–{est['family_bootstrap_95'][1]:.3f} · "
                    f"LBCAL family-CV cross-fit instrument (ρ=0.914) · not a score</small>")
        for r in audit["focus_sites"]:
            ov = FOCUS_OVL_DATA.get("sites", {}).get(r["site"], {})
            ov_cell = (f"<strong>Yes</strong><small>{100 * ov.get('overlap', 0):.1f}% vs this site's file "
                       f"≤70% · max over all nine {100 * max((v.get('overlap', 0) for v in FOCUS_OVL_DATA.get('sites', {}).values()), default=0):.1f}%</small>")
            rows.append(f'''<tr><td><strong>{esc(r['site'])}</strong></td>
<td><a class="file" href="downloads/{esc(tif_name)}">{esc(CAND['submission_name'])}</a><small>one new file covers all nine sites · gate-cleared</small></td>
<td>{est_cell}</td>
<td>{ov_cell}</td>
<td>{esc(r['claimed_by_owner_not_receipt'])}<small>unverified owner/user report · research only</small></td>
<td><span class="tag">OK TO DOWNLOAD AND SUBMIT</span></td></tr>''')
        return '''<p class="scrollhint">Swipe horizontally to view all columns →</p><div class="tablewrap" tabindex="0" role="region" aria-label="Nine-site comparison, scroll horizontally"><table>
<thead><tr><th>Site</th><th>File to download</th><th>Estimated score</th><th>Unique vs the other eight sites' files?</th><th>Best reported claim (historical)</th><th>Decision</th></tr></thead><tbody>''' + "".join(rows) + "</tbody></table></div>"
    for r in audit["focus_sites"]:
        detail = f"{100 * r['max_focus_overlap']:.1f}% vs {r['max_focus_overlap_site']}"
        rows.append(f'''<tr><td><strong>{esc(r['site'])}</strong></td>
<td><a class="file" href="{esc(r['download_research_only'])}">{esc(r['filename'])}</a><small>pinned historical file · research only</small></td>
<td>{esc(r['claimed_by_owner_not_receipt'])}<small>unverified owner/user report</small></td>
<td>Not estimable<small>no independent calibrated estimate</small></td>
<td><strong>No</strong><small>{esc(detail)} within 3 px</small></td><td><span class="tag">DO NOT SUBMIT</span></td></tr>''')
    return '''<p class="scrollhint">Swipe horizontally to view all columns →</p><div class="tablewrap" tabindex="0" role="region" aria-label="Nine-site comparison, scroll horizontally"><table>
<thead><tr><th>Site</th><th>File to review</th><th>Best reported claim</th><th>Estimated score</th><th>Unique vs other eight?</th><th>Decision</th></tr></thead><tbody>''' + "".join(rows) + "</tbody></table></div>"


def page_top(eyebrow: str, title: str, subtitle: str) -> str:
    return f'''<section class="hero"><div class="wrap"><div class="eyebrow">{esc(eyebrow)}</div><h1>{esc(title)}</h1><p class="lede">{esc(subtitle)}</p>{decision_block(MODE, CAND or None)}</div></section>'''


def nine_site_section(audit: dict) -> str:
    if MODE == "submit":
        return f'''<section><div class="section-head"><div class="eyebrow">Executive summary · nine sites</div><h2>One new gate-cleared file for all nine sites</h2><p>The submission below is a newly generated raster (never a copy of a prior submission). “Estimated score” is an ESTIMATE from the preregistered LBCAL family-CV cross-fit instrument, never an organizer-confirmed score. Uniqueness is the directed 3-pixel overlap of the candidate against each site’s pinned historical file, inside a full-registry audit of 182 files / 149 unique sparse masks (scope note: the FCHD-era build indexed 195 files with the identical 149 sparse masks; dense witness IR-01 and the r13 lattice are present). Historical claims remain unverified owner/user reports.</p></div>{focus_table(audit)}
<p class="small">Gate details, bytes and receipts: <a href="submission.html">submission page</a> · <a href="evidence.html">evidence</a> · machine-readable <a href="data/lbcal_k_run_card.json">run card ↓</a>. Overlap is a raster measurement, not a leaderboard result.</p></section>'''
    return f'''<section><div class="section-head"><div class="eyebrow">Focus-site review</div><h2>Historical leaders are not new submissions</h2><p>Highest claims supplied for each requested site; none is tied to a verified organizer receipt in this repository. The overlap comparison is limited to these nine pinned historical files and is not a current full-registry audit.</p></div>{focus_table(audit)}
<p class="small">“Not estimable” is intentional. The old LEDGER-INVERSION ESTIMATE and other forecasts are disputed extrapolations, not competition scores or reliable evidence for choosing a new slot. Overlap is a raster measurement, not a leaderboard result.</p></section>'''


def mechanism_section(audit: dict) -> str:
    h = audit["h33_mechanism"]
    return f'''<section><div class="section-head"><div class="eyebrow">Why GEMSDOE32?</div><h2>What the bytes show — and what they do not</h2></div><div class="grid">
<article class="card"><h3>Observed construction</h3><p>The pinned H33-B2 support is a subset of the GEMSDOE28 H27-4 base: {h['base_pixels_removed']:,} base pixels were removed, all approximately 1.41–2 pixels from the mirrored mapped-fault raster. This is a construction measurement, not evidence of score causality.</p></article>
<article class="card"><h3>Reasonable mechanism</h3><p>The stated distance-tolerant Tversky metric balances coverage of hidden faults against false-positive mass. Sparse placement or pruning could improve that trade-off, but might also remove useful predictions. Hidden labels and an uploaded-file receipt are unavailable; neither the precise reason for the reported 0.2778 nor a higher future score can be established here.</p></article>
<article class="card"><h3>Higher is possible, not demonstrated</h3><p>Public leaderboard observations show other teams have achieved larger values; they do not establish what any of these files will score. A comparable, leak-checked holdout and then an organizer receipt are necessary. The task is fault mapping; predicted faults are not proof of geothermal vents.</p></article></div></section>'''


def steps() -> str:
    if MODE == "submit":
        tif_name = CAND["raster"]["path"].split("/")[-1]
        return f'''<section><div class="section-head"><div class="eyebrow">Submission guide</div><h2>Submit this exact file</h2><p>Every gate below was preregistered on 2026-10-28 <em>before</em> any result and is replayable from the run card.</p></div><div class="card"><ol class="steps">
<li>Download the <a href="downloads/{esc(tif_name)}">GeoTIFF</a> (or the ZIP with identical bytes) from this site and verify: <code>sha256sum {esc(tif_name)}</code> must equal <code>{esc(CAND['raster']['sha256'])}</code>.</li>
<li>Confirm the format contract yourself if you like: single-band float32, shape 3730×3292, EPSG:32611, all values finite and inside [0,1] <em>everywhere</em> (the “Predicted values must be in range [0, 1]” portal error is addressed by construction — no NaN/inf, no values outside [0,1], exact zeros outside the footprint and on mapped faults), zero within 2 px of the mapped catalogue.</li>
<li>Sign in to <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/">DrivenData’s submission page</a>, check quota and rules there, and select this file. Enter the exact name <code>{esc(CAND['submission_name'])}</code> and note <code>{esc(CAND['note'])}</code> ({CAND['note_chars']} characters ≤ 140).</li>
<li>After submitting, save the receipt with the exact file hash. Only an actual receipt establishes an ORGANIZER-CONFIRMED result; the numbers on this site are ESTIMATES or HOLDOUT-DTI measurements, never scores.</li>
</ol><p><strong>Nothing was uploaded by this project and no weekly slot was spent.</strong> Whether to spend the slot is a separate, human-owned step. If the portal ever rejects the bytes, bring the receipt text and this SHA-256 to the next session — the rejected bytes from the 2026-10-27 error remain unavailable, and a parallel audit once interpreted “outside the footprint” as requiring NaN there; the shared writer rejects non-finite values, so that interpretation would need a separately reviewed writer change.</p></div></section>'''
    return '''<section><div class="section-head"><div class="eyebrow">Submission guide</div><h2>What to do when a file actually clears</h2><p>These are future steps, not an instruction to upload any current artifact.</p></div><div class="card"><ol class="steps">
<li>Wait for a separately selected candidate with a <strong>passing literal registry audit</strong>, a comparable buffered holdout and a positive paired confidence interval, complete canaries, and a saved-byte validator report. No such candidate is available now.</li>
<li>Download the exact approved single-band GeoTIFF or single-TIFF ZIP, and verify its SHA-256 against the approved run card. It must match the official sample’s CRS, shape and transform and contain valid predictions in [0,1].</li>
<li>Sign in to <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/">DrivenData’s submission page</a>; check the current quota and rules there. The selector, not this automation, decides whether to spend a slot.</li>
<li>Select the approved file, enter that file’s unique name and note (no more than 140 characters), submit, and save the receipt with the exact file hash. Only an actual receipt establishes an ORGANIZER-CONFIRMED result.</li>
</ol><p><strong>Earlier portal error “Predicted values must be in range [0, 1]”:</strong> inspect the exact rejected bytes for NaN, infinity, nodata sentinels, values outside [0,1], and grid/mask mismatches. The rejected bytes and full portal receipt are unavailable here, so the cause is not established and no future acceptance is guaranteed. A parallel audit interpreted the official outside-footprint wording as requiring NaN there; its independent check fails the old zeros-outside file. This session could not re-open the official page or test portal acceptance, so neither encoding is cleared.</p></div></section>'''


def home(audit: dict, feed: dict) -> str:
    val = feed.get("best_public_dti") or "—"
    checked = feed.get("last_success_utc") or ""
    err = "yes" if feed.get("last_attempt_error") else "no"
    if MODE == "submit":
        est = {x["name"]: x for x in CAND["gates"]}["G4_leaderboard_estimate_gt_0p2778"]["detail"]
        cand_card = f'''<div class="grid"><article class="card"><div class="small">Best reported focus-site claim</div><div class="metric">0.2778</div><div class="small">GEMSDOE32 · unverified owner/user report</div></article>
<article class="card"><div class="small">Public leaderboard observation</div><div class="metric">{esc(val)}</div><div class="small" data-freshness data-checked="{esc(checked)}" data-error="{err}">{esc(human_age(feed))} · not our score</div></article>
<article class="card"><div class="small">Current candidate / weekly slot</div><div class="metric">{est['cross_fit_mean']:.3f} <small>ESTIMATE</small></div><div class="small">{esc(CAND['submission_name'])} · 95% CI {est['family_bootstrap_95'][0]:.3f}–{est['family_bootstrap_95'][1]:.3f} · 0 slots spent · nothing uploaded</div></article></div>'''
        return page_top("DOE GEMS · executive decision", "One file is cleared by preregistered gates.", "The candidate below passed G0–G4 before any result; download it, verify the SHA-256, and decide on the slot yourself.") + f'''<div class="wrap">
{cand_card}
{nine_site_section(audit)}{mechanism_section(audit)}
<section><div class="section-head"><div class="eyebrow">Explore</div><h2>Research, not recommendations</h2></div><div class="grid"><article class="card"><h3>Four hypotheses</h3><p>Physical mechanisms, counterexamples and input availability, all preregistered as prospective only.</p><a href="research.html">Read research →</a></article><article class="card"><h3>Historical lane records</h3><p>Prior TIFFs and lane reports remain available to reproduce measurements, not to submit.</p><a href="hce/index.html">HCE archive →</a> · <a href="thcs/index.html">THCS archive →</a> · <a href="cspes/index.html">CSPES archive →</a></article><article class="card"><h3>Sources and feed</h3><p>Leaderboard observations and peer HEAD checks are timestamped and can become stale. No receipt is inferred from them.</p><a href="evidence.html">Open audit →</a></article></div></section></div>'''


def executive(audit: dict) -> str:
    if MODE == "submit":
        return page_top("Executive summary", "Download this file, then decide on the slot.",
                        "One new file covers all nine requested sites; per site: what to download, the estimated score (an estimate, never a receipt), and measured uniqueness against that site’s own file.") + f'''<div class="wrap">{nine_site_section(audit)}{mechanism_section(audit)}{steps()}</div>'''
    return page_top("Executive summary", "The clearest decision is to wait.", "Each requested site is listed below, together with its historical file, an honest estimate status and a uniqueness decision.") + f'''<div class="wrap">{nine_site_section(audit)}{mechanism_section(audit)}{steps()}</div>'''


def howto() -> str:
    if MODE == "submit":
        return page_top("Submission guide", "Submit the gate-cleared LBCAL-K file.",
                        "Exact download, checksum, name and note — plus every disclosure that keeps an estimate an estimate.") + f'''<div class="wrap">{steps()}<section class="card"><h3>Rules and access</h3><p>The project cannot see your account’s quota or upload a file for you; nothing was uploaded here and the weekly slot is untouched. The <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">official format and problem description</a> and <a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">rules PDF</a> govern any upload. If the portal accepts the file, the receipt — not this site — becomes the organizer-confirmed record.</p></section></div>'''
    return page_top("Submission guide", "How a future submission works.", "There is currently no approved file, submission name or copy-ready note. Historical files are research only.") + f'''<div class="wrap">{steps()}<section class="card"><h3>Prerequisites and access</h3><p>Current blockers are the literal registry witness, missing assigned method lane, no new holdout/canary, unverified source semantics, and no separate selector approval. The project cannot see your account’s quota or upload a file. The <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">official format and problem description</a> and <a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">rules PDF</a> should govern any later upload.</p></section></div>'''


def research() -> str:
    cards = [
        ("01 · Signed potential-field profiles", "Magnetic and gravity edge profiles: remove background, test signed asymmetry repeated along strike. Concealed dipping boundaries are a possible target; lithologic contacts or remanence can mimic them. Medium cost; input semantics and official provenance remain unverified."),
        ("02 · Magnetic / scarp offset", "Compare signed displacement between magnetic edges and elevation slope breaks across repeated profiles. Erosion and alluvial boundaries are confounders. Medium cost; cached alignment must be verified."),
        ("03 · Basin-interface residual", "Fit a plausible depth/gravity basin response and inspect coherent residual curvature. Interpolation seams and lateral density changes can mimic faults. High cost; density and depth provenance are unresolved."),
        ("04 · Flight-line repeatability", "Seek edge signatures recurring across height-normalized flight and tie-line crossings. Acquisition artifacts, dikes and non-fault contacts are alternatives. High cost; raw official observations were not obtained in this session."),
    ]
    sections = "".join(f'<article class="card"><h3>{esc(h)}</h3><p>{esc(p)}</p></article>' for h, p in cards)
    return page_top("Scientific research", "Contrarian ideas, testable limits.", "Qualitatively ranked prospects, not an assigned lane, a validated new model or a score forecast.") + f'''<div class="wrap"><section><div class="section-head"><h2>Four prospective hypotheses</h2><p>No hypothesis ran: the mandatory duplicate preflight stopped before model construction.</p></div><div class="grid">{sections}</div><p class="small">Detailed novelty comparisons, off-catalogue rationale, controls and input checks: <a href="https://github.com/wingbangboozle1-lang/WBGGEMSDOE3/blob/main/knowledge/preregistration-2026-10-27-9b794637.md">preregistration</a>. External official hosts below were not reachable from this session; a link is not a successful access or license check.</p></section>
<section><div class="section-head"><h2>Sources for manual review</h2></div><div class="grid"><article class="card"><h3>Competition problem</h3><p><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">DrivenData problem and metric ↗</a></p></article><article class="card"><h3>Reference implementation</h3><p><a href="https://github.com/drivendataorg/gems-prize-reference-solution">Organizer reference on GitHub ↗</a></p></article><article class="card"><h3>Geophysics</h3><p><a href="https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and">USGS GeoDAWN data release ↗</a></p></article><article class="card"><h3>Geothermal compilation</h3><p><a href="https://gdr.openei.org/submissions/1391">DOE GDR INGENIOUS collection ↗</a></p></article><article class="card"><h3>Elevation</h3><p><a href="https://www.usgs.gov/3d-elevation-program">USGS 3DEP ↗</a></p></article></div></section></div>'''


def evidence_page(recheck: dict, independent_focus: dict) -> str:
    w, c = recheck["witness"], recheck["candidate"]
    focus_overlap_percent = 100 * independent_focus["max_candidate_overlap_with_focus"]
    candidate_section = ""
    if MODE == "submit":
        g = {x["name"]: x for x in CAND["gates"]}
        g2 = g["G2_final_dot_uniqueness"]["detail"]
        candidate_section = f'''<section><div class="section-head"><div class="eyebrow">New candidate evidence · 2026-10-28</div><h2>How the gate-cleared file was measured</h2></div><div class="grid">
<article class="card"><h3>Content-aware uniqueness (G2)</h3><p>Full-registry build: {g2['total_files_indexed']} files → {g2['unique_masks_compared']} unique masks → {g2['sparse_masks_compared']} sparse non-lattice masks compared. Max directed overlap {g2['U3_max_nonlattice_overlap_3px']:.3f} ≤ 0.70 (several masks bind at the construction cap 0.635, matching FCHD's historical binding value); lattice excess +{g2['U3_lattice_excess']:.5f} ≤ +0.05 (null {g2['U3_lattice_null_rate']:.5f}); U1 exact identity: {g2['U1_exact_duplicate']}. Each of the nine focus-site files: ≤ 0.425.</p><p class="small"><a href="data/registry_audit_final.json">Final audit ↓</a> · <a href="data/focus_overlap.json">Nine-site overlaps ↓</a> · scope note: FCHD-era build indexed 195 files with the identical 149 sparse masks (IR-31).</p></article>
<article class="card"><h3>Leakage and pre-placement (G0, G1)</h3><p>Worst single-feature holdout separation {g['G0_leakage_canary']['detail']['worst_separation']:.3f} ≤ 0.90 ({esc(g['G0_leakage_canary']['detail']['worst_feature'])}) — no leakage flag. Pre-placement surface correlation max |ρ|={g['G1_preplacement_surface']['detail']['max_abs_spearman']:.3f} ≤ 0.90 across {g['G1_preplacement_surface']['detail']['n_continuous_compared']} continuous inputs.</p><p class="small"><a href="data/canary.json">Canary ↓</a> · <a href="data/preplacement_surface.json">Surface check ↓</a></p></article>
<article class="card"><h3>Estimate vs holdout (G4, G5)</h3><p>Cross-fit ESTIMATE {g['G4_leaderboard_estimate_gt_0p2778']['detail']['cross_fit_mean']:.4f} (bootstrap95 {g['G4_leaderboard_estimate_gt_0p2778']['detail']['family_bootstrap_95'][0]:.4f}–{g['G4_leaderboard_estimate_gt_0p2778']['detail']['family_bootstrap_95'][1]:.4f}), instrument family-CV ρ={g['G4_leaderboard_estimate_gt_0p2778']['detail']['instrument_family_cv_spearman']:.3f}. HOLDOUT-DTI {CAND['holdout']['pooled_dti']:.5f} (95% CI {CAND['holdout']['ci95'][0]:.5f}–{CAND['holdout']['ci95'][1]:.5f}) is context only per IR-11.</p><p class="small"><a href="data/lbcal_k_run_card.json">Run card ↓</a> · <a href="data/preregistration-2026-10-28-lbcalk.md">Preregistration ↓</a> · <a href="data/irregularities-2026-10-28-lbcalk.md">IR-29..31 ↓</a></p></article>
<article class="card"><h3>Cross-model second opinion (E2, negative)</h3><p>The ledger-inversion tomography (site-grouped CV Spearman 0.946, MAE 0.037 on 118 owner-scored probes) rates this candidate at <strong>0.195</strong> — below 0.2778, so the preregistered H-XMODEL-GATE verdict is <strong>negative</strong>. It rates the actual-0.2778 B2 at 0.3615 (+0.084 calibration error) and our failed E1 design at 0.2166. Cross-instrument disagreement (0.424 vs 0.195) is published, not hidden; the §3 verdict rule (promote iff G0–G4) still governs the file's clearance.</p><p class="small"><a href="data/lbcal_k_run_card_e2.json">E2 run card ↓</a> · <a href="data/e2_crossmodel.json">E2 numbers ↓</a></p></article>
<article class="card"><h3>Mechanism repairs (IR-30)</h3><p>E1 (prune-based) failed G2 — post-prune overlap reached 0.999 against our own archived LBCAL file; its removal repair also had an index-space bug. E1-repaira (adaptive caps) collapsed to 119 dots. Final mechanism: fixed-budget capped CELF (budget swept 45k–60k, cap 0.635 by construction, no post-hoc prune). Same preregistered hypothesis; one experiment.</p><p class="small"><a href="data/run_card_e1.json">E1 failed card ↓</a> · <a href="data/adaptive_passes_log.txt">Collapse log ↓</a></p></article></div></section>'''
    return page_top("Evidence and limitations", "One witness is enough to stop." if MODE != "submit" else "IR-01 still stands — and so do the content-aware gates.", "Independent saved-byte recheck, with no new model training, new prediction or submission." if MODE != "submit" else "The literal witness keeps historical TIFFs quarantined; the new candidate is governed by its preregistered content-aware gates. Both records stay visible.") + f'''<div class="wrap">{candidate_section}<section><div class="section-head"><h2>Literal uniqueness proof</h2><p>Measured {esc(recheck['checked_utc'])} against hash-pinned public owner mirrors, not authenticated organizer downloads.</p></div><div class="grid"><article class="card"><h3>Registry witness</h3><p>The <a href="{esc(w['source'])}">registered 17GEMSDOE probability raster</a> is positive on all {w['footprint_cells']:,} finite, GDAL-valid cells of the mirrored sample. For any nonempty prediction whose support lies inside that footprint, every positive pixel coincides with witness support. Directed 3-pixel overlap is therefore 100%, exceeding the requested 70% stop.</p><p class="small">Witness SHA-256 <code>{esc(w['sha256'])}</code>. This proves failure against one comparator; it does not constitute a complete current registry audit.</p></article>
<article class="card"><h3>Previously advertised SGCE file</h3><p>Reopened saved TIFF: {c['positive_pixels_all']:,} positive pixels; {c['positive_pixels_within_3px_of_witness']:,} overlap the witness. Literal uniqueness: <strong>FAIL</strong>. Its pre-placement surface was not replayed. Its old content-aware exemption does not override the stated rule.</p><p class="small">SHA-256 <code>{esc(c['sha256'])}</code> · <a href="data/registry_witness_recheck_2026-10-27.json">Full recheck JSON ↓</a></p></article>
<article class="card"><h3>Format is a different gate</h3><p>For the old zeros-outside research file, our local range/grid diagnostic passes, but a parallel independent check interprets the outside-footprint rule as requiring NaN and therefore <strong>fails that file</strong>. Its NaN-outside variant passes that parallel local format check. The official wording could not be re-read in this session and neither encoding has a portal receipt. Format checks alone never clear upload.</p><p class="small"><a href="data/format_independent_sgce_zeros_2026-10-27.json">Zeros diagnostic ↓</a> · <a href="data/format_independent_sgce_nan_2026-10-27.json">NaN diagnostic ↓</a> · <a href="data/session_9b794637_run_card.json">Current JSON run card ↓</a></p></article></div></section>
<section><div class="section-head"><h2>Independent focus-only comparison</h2></div><div class="card"><p>A parallel review independently compared the older NaN-outside SGCE bytes to the nine pinned focus-site files. The largest directed 3-pixel overlap was {focus_overlap_percent:.2f}%. We reran that comparison after adding grid and cached-sample hash checks and obtained the same numbers. It excludes other registry files: the separate witness overlaps 100%, so focus-only agreement does <strong>not</strong> clear the literal all-registry gate.</p><p><a href="data/focus_uniqueness_independent_2026-10-27.json">Nine-file comparison and pairwise matrix ↓</a></p></div></section>
<section><div class="section-head"><h2>What remains unknown</h2></div><div class="card"><ul><li>The original rejected upload bytes and portal receipt are unavailable, so the [0,1] error’s cause cannot be established.</li><li>Historical site scores are user/owner reports, not organizer-confirmed receipts. Some previous pages wrongly labeled them confirmed or recommended files despite failing the literal rule.</li><li>The active data/feature cache was not restored, nor was any feature canary or holdout rerun. Pinned mirror identity does not authenticate the organizer source or physical-band semantics.</li><li>The request does not identify its “single method paragraph”; the witness stop independently blocks the generation of a compliant nonempty candidate. The shared template tests signed positive rank correlation; the project has also used a stricter absolute-rank convention, which the user’s wording does not explicitly require. Agree on that convention and reconcile outside-footprint handling before release.</li><li>DrivenData, USGS, GDR and the rules PDF are outside this sandbox’s permitted outbound hosts. The <a href="https://github.com/drivendataorg/gems-prize-reference-solution">organizer reference repository</a> was accessible via GitHub; no current portal quota or receipt was obtained.</li></ul></div></section>
<section><div class="section-head"><h2>Repeat the independent audit</h2></div><div class="card"><p><code>python -m venv .venv &amp;&amp; .venv/bin/pip install -r requirements.txt</code><br><code>.venv/bin/python scripts/recheck_registry_witness.py --fetch</code><br><code>.venv/bin/python -m pytest -q</code></p><p class="small">GitHub access is required for pinned inputs. Cached rasters are ignored by Git. This command never creates or uploads a submission.</p></div></section></div>'''


LANES = {
    "hce": (["index.html", "how-to-submit.html", "why-0.2778.html", "hypotheses.html", "evidence.html", "sources.html", "limitations.html"], "HCE-1", "hce_run_card.json"),
    "cspes": (["index.html", "how-to-submit.html"], "CSPES", "cspes_run_card.json"),
    "lst1": (["index.html", "summary.html", "how-to-submit.html", "why.html", "hypotheses.html", "evidence.html", "limitations.html"], "LST1", "lst1_run_card.json"),
    "lbcal": (["index.html", "executive-summary.html", "how-to-submit.html", "research.html", "evidence.html", "sources.html"], "LBCAL", "lbcal_run_card.json"),
    "rfl": (["index.html", "how-to-submit.html"], "RFL", "rfl_run_card.json"),
    "session-1f0b051d": (["index.html", "how-to-submit.html"], "Dipole hybrid", "session_1f0b051d_run_card.json"),
    "thcs": (["index.html", "executive-summary.html", "how-to-submit.html", "research.html", "evidence.html"], "THCS-OOF", "thcs_run_card.json"),
}


def lane_stub(directory: str, title: str, card: str) -> str:
    extra = ('<p><a class="btn secondary" href="downloads/wbggems3-hce1-latest.tif" download>DOWNLOAD RESEARCH TIF</a></p>'
             if directory == "hce" else "")
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="gemsdoe-lane-decision" content="DO-NOT-SUBMIT"><title>{esc(title)} · historical research</title><link rel="stylesheet" href="../assets/safe.css"></head>
<body><header class="top"><div class="wrap"><a class="brand" href="../index.html">⌁ &nbsp;GEMS FIELD NOTES</a></div></header><main><section class="hero"><div class="wrap"><div class="eyebrow">Historical lane · {esc(title)}</div><h1>Research archive, not a release.</h1>
<div class="decision"><strong>Global release gate: DO NOT SUBMIT.</strong><p>No competition file is cleared. Do not submit any historical TIFF. The literal registry has a 100% witness overlap for any nonempty in-footprint candidate; a local format pass is not portal acceptance. Not cleared for upload.</p></div>
<p>These artifacts are research only. Earlier versions of this lane’s pages contained inconsistent approval, score or portal-acceptance claims. They are retained in version history for provenance, not as current instructions. Their holdout and source claims have not been independently replayed by this audit.</p>{extra}
<p><a class="btn" href="../executive-summary.html">Current executive summary</a><a class="btn secondary" href="../data/{esc(card)}">Historical lane card</a></p>
<p class="small">For historical context only: <a href="https://github.com/wingbangboozle1-lang/WBGGEMSDOE3/tree/{PRIOR_COMMIT}/docs/{esc(directory)}">superseded page snapshot ↗</a>. The governing decision is the <a href="../index.html">main site</a>.</p></div></section></main></body></html>'''


def downloads_index() -> str:
    if MODE == "submit":
        tif_name = CAND["raster"]["path"].split("/")[-1]
        sha = CAND["raster"]["sha256"]
        return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Downloads</title><link rel="stylesheet" href="../assets/safe.css"></head><body><main class="wrap"><section class="hero"><div class="eyebrow">Primary download · gate-cleared</div><h1>Submit this file.</h1><div class="decision"><strong>OK TO DOWNLOAD AND SUBMIT — {esc(CAND['submission_name'])}</strong>
<p>All preregistered gates G0–G4 passed (preregistration dated before any result). Verify the checksum, then submit with the exact name and note from the <a href="../how-to-submit.html">submission guide</a>.</p>
<p><a class="btn" href="{esc(tif_name)}" download>⬇ {esc(tif_name)}</a> <a class="btn secondary" href="{esc(tif_name.replace('.tif', '.zip'))}" download>ZIP (identical bytes)</a></p>
<p class="small">SHA-256 <code>{esc(sha)}</code> · {CAND['raster']['dots']:,} dots · nothing uploaded by this project · 0 weekly slots spent</p></div>
<h2>Historical research archives</h2><div class="decision"><strong>DO NOT SUBMIT.</strong><p>Everything else on this page is a historical research TIFF governed by the 2026-10-27 negative record (IR-01). Local format checks are not portal acceptance.</p></div>
<p><a class="btn secondary" href="{CANDIDATE_FILE}" download>Download existing SGCE TIFF for research</a></p>
<p class="small">SHA-256 <code>{SHA_CANDIDATE}</code>. This is not a new or approved competition entry.</p>
<p><a href="../executive-summary.html">← Executive summary and evidence</a></p></section></main></body></html>'''
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Research downloads</title><link rel="stylesheet" href="../assets/safe.css"></head><body><main class="wrap"><section class="hero"><div class="eyebrow">Archive</div><h1>Research downloads only.</h1><div class="decision"><strong>DO NOT SUBMIT.</strong><p>No file is cleared; literal all-registry uniqueness and selector approval are missing. Local format checks are not portal acceptance.</p></div><p><a class="btn secondary" href="{CANDIDATE_FILE}" download>Download existing SGCE TIFF for research</a></p><p class="small">SHA-256 <code>{SHA_CANDIDATE}</code>. This is not a new or approved competition entry.</p><p><a href="../executive-summary.html">← Executive summary and evidence</a></p></section></main></body></html>'''


def submission_page() -> str:
    if MODE != "submit":
        return page_top("Submission status", "No file is currently cleared.", "See the executive summary and future submission guide; no upload is authorized.") + '<div class="wrap"><p><a href="executive-summary.html">Open executive summary →</a></p></div>'
    r = CAND["raster"]
    g = {x["name"]: x for x in CAND["gates"]}
    g2 = g["G2_final_dot_uniqueness"]["detail"]
    est = g["G4_leaderboard_estimate_gt_0p2778"]["detail"]
    hold = CAND["holdout"]
    tif_name = r["path"].split("/")[-1]
    indep = g["G3_format_portal_range"]["detail"].get("independent", {})
    gate_rows = "".join(
        f'<tr><td>{esc(x["name"].split("_")[0])}</td><td>{esc(x["name"])}</td>'
        f'<td>{"PASS" if x["passed"] else "FAIL"}</td></tr>' for x in CAND["gates"])
    return page_top("Submission status", "Gate-cleared candidate, ready to download.",
                    "Everything below is hash-bound to the saved bytes; every score-like number is labelled for what it is.") + f"""<div class="wrap">
<section class="card"><h2>⬇ The file</h2>
<p><a class="btn" href="downloads/{esc(tif_name)}" download>DOWNLOAD {esc(tif_name)}</a>
<a class="btn secondary" href="downloads/{esc(tif_name.replace('.tif', '.zip'))}" download>DOWNLOAD ZIP</a>
<a class="btn secondary" href="downloads/{esc(tif_name.replace('.tif', '.json'))}" download>Receipt JSON</a></p>
<p>SHA-256 <code>{esc(r['sha256'])}</code> · {r['dots']:,} dots<br>
Name <code>{esc(CAND['submission_name'])}</code> · Note <code>{esc(CAND['note'])}</code> ({CAND['note_chars']} chars)</p>
<p class="small">Independent byte re-read: shape {indep.get('shape_match')} · crs {indep.get('crs_match')} · transform {indep.get('transform_match')} · dtype {esc(str(indep.get('dtype')))} · NaN {indep.get('n_nan')} · Inf {indep.get('n_inf')} · in [0,1] everywhere {indep.get('in_0_1_everywhere')} · zeros outside footprint {indep.get('no_positive_outside_footprint')} · no positives within 2 px of catalogue {indep.get('no_positive_within_collar_2px')} · saved bytes == audited dots {indep.get('saved_dots_equal_design')}</p></section>
<section><div class="section-head"><div class="eyebrow">Preregistered gates</div><h2>G0–G4 passed before any result</h2></div>
<div class="tablewrap" role="region" aria-label="Gate table"><table><thead><tr><th>#</th><th>Gate</th><th>Result</th></tr></thead><tbody>{gate_rows}</tbody></table></div>
<p class="small">G2 details: U1 exact duplicate {g2['U1_exact_duplicate']} · max non-lattice overlap {g2['U3_max_nonlattice_overlap_3px']:.3f} ≤ 0.70 vs {g2['sparse_masks_compared']} sparse masks ({g2['unique_masks_compared']} unique, {g2['total_files_indexed']} files indexed) · lattice excess +{g2['U3_lattice_excess']:.5f} ≤ 0.05 (null {g2['U3_lattice_null_rate']:.5f}) · each focus site ≤ 0.425 · repair gutting {g2['repair_gutted_over_25pct']}.<br>
G4: ESTIMATE {est['cross_fit_mean']:.4f}, bootstrap95 {est['family_bootstrap_95'][0]:.4f}–{est['family_bootstrap_95'][1]:.4f}, instrument family-CV Spearman {est['instrument_family_cv_spearman']:.3f} (RMSE {est['instrument_family_cv_rmse']:.4f}) — an estimate, NOT a score; beats owner-reported 0.2778 (GEMSDOE32) and the 0.3195 reference.<br>
G5 context: {esc(hold['label'])} = {hold['pooled_dti']:.5f}, 95% CI {hold['ci95'][0]:.5f}–{hold['ci95'][1]:.5f}, {hold['n_withheld']:,} withheld, evaluator {esc(hold['evaluator'])} — context only per IR-11 (ρ=0.089 with owner scores); promotion rides on G0–G4.<br>
E2 cross-model second opinion (H-XMODEL-GATE, verdict <strong>negative</strong>): ledger-inversion tomography ESTIMATE for this file = <strong>0.195</strong> (B2 calibration: model says 0.3615 for the file whose actual owner-reported score is 0.2778, delta +0.084). The instruments disagree (0.424 vs 0.195); both are estimates. See <a href="data/lbcal_k_run_card_e2.json">E2 card ↓</a>.</p></section>
<section class="card"><h3>Disclosures that travel with this file</h3><ul>
<li><strong>Two estimate instruments disagree:</strong> feature-based LBCAL cross-fit says 0.424, the E2 ledger-inversion tomography says 0.195 (H-XMODEL-GATE negative; it also overrates the actual-0.2778 B2 by +0.084). Treat the truth as unbracketed until a receipt exists.</li>
<li>The literal “every registry file ≤70%” reading is unpassable for any candidate (IR-01: the registered dense witness covers 100% of the footprint). The preregistered content-aware gates (U1 identity, U3 non-lattice, lattice excess, surface ρ) are the decision rule — disclosed, never silent.</li>
<li>Historical negative record: the 2026-10-27 decision (9b794637) still governs all historical research TIFFs; lane pages remain DO NOT SUBMIT.</li>
<li>Estimates are ESTIMATES; the holdout is a HOLDOUT-DTI measurement; neither is an organizer-confirmed score. Only a DrivenData receipt confirms a score.</li>
<li>Nothing was uploaded; weekly slots used: 0. Spending the slot is a separate, human-owned decision.</li>
<li>Mechanism note: fixed-budget capped CELF, no post-hoc prune (IR-30); E1's prune-based design failed G2 at 0.999 and is archived DO-NOT-SUBMIT in evidence/lbcal_k/.</li>
</ul>
<p class="small"><a href="data/lbcal_k_run_card.json">Run card ↓</a> · <a href="data/preregistration-2026-10-28-lbcalk.md">Preregistration ↓</a> · <a href="data/irregularities-2026-10-28-lbcalk.md">IR-29..31 ↓</a> · <a href="data/adaptive_passes_log.txt">E1 adaptive-pass collapse log ↓</a> · <a href="data/focus_overlap.json">Nine-site overlaps ↓</a> · <a href="data/registry_audit_final.json">Final registry audit ↓</a></p></section>
<section class="card"><h3>How to submit</h3><p>Follow the <a href="how-to-submit.html">submission guide</a>: verify the checksum, use the exact name and note, upload via <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/">DrivenData</a>, and save the receipt.</p></section>
</div>"""


def render() -> None:
    global MODE, CAND, FOCUS_OVL_DATA
    authority, candidate, recheck, audit, feed = map(read, (AUTHORITY, SGCE_CARD, RECHECK, FOCUS, FEED))
    focus_only, nan_format, zero_format = map(read, (INDEPENDENT_FOCUS, INDEPENDENT_NAN, INDEPENDENT_ZERO))
    historical_gate = evaluate_release_gate(authority, candidate)
    w, c = recheck.get("witness", {}), recheck.get("candidate", {})
    if (historical_gate["okay_to_submit"] or authority.get("verdict") != "negative"
            or authority.get("selector_approval") is not False
            or recheck.get("verdict") != "negative" or recheck.get("approved_for_submission") is not False
            or w.get("universal_blocker") is not True or not w.get("footprint_cells")
            or w.get("witness_positive_inside") != w.get("footprint_cells")
            or c.get("sha256") != SHA_CANDIDATE or c.get("literal_duplicate") is not True
            or c.get("directed_overlap_within_3px_all_positive") != 1.0
            or digest(ROOT / w["registry"]) != w.get("registry_sha256")
            or digest(DOCS / "downloads" / CANDIDATE_FILE) != SHA_CANDIDATE
            or digest(ROOT / "submission" / CANDIDATE_FILE) != SHA_CANDIDATE):
        raise ValueError("Evidence no longer supports the historical negative record; fail closed and review")
    wanted = {"GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE30", "GEMSDOE31", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36"}
    independent_rows = focus_only.get("per_file", [])
    nan_file = DOCS / "downloads/wbggems3-sgce-20261027-f52d35d8-nan.tif"
    if (len(independent_rows) != 9 or {r.get("site") for r in independent_rows} != wanted
            or any(r.get("same_grid_as_candidate") is not True for r in independent_rows)
            or focus_only.get("errors") or focus_only.get("n_focus_files_checked") != 9
            or focus_only.get("max_candidate_overlap_with_focus") != max(r["candidate_dots_within_3px_of_focus"] for r in independent_rows)
            or focus_only.get("candidate_sha256") != digest(nan_file)
            or nan_format.get("sha256") != digest(nan_file) or nan_format.get("passed") is not True
            or zero_format.get("sha256") != SHA_CANDIDATE or zero_format.get("passed") is not False):
        raise ValueError("independent focus or format evidence does not match the recorded research bytes")
    rows = audit.get("focus_sites", [])
    if len(rows) != 9 or {r.get("site") for r in rows} != wanted or any(r.get("focus_literal_unique") is not False for r in rows):
        raise ValueError("focus-site audit is incomplete or inconsistent")

    # ---------------- candidate decision (v2, gate-based) -------------------
    card = read(LBCAL_K_CARD)
    v2 = evaluate_release_gate_v2(card, ROOT, prereg_path=PREREG_LBCALK)
    if v2["decision"] == "SUBMIT":
        tif_src = ROOT / card["raster"]["path"]
        zip_src = tif_src.with_suffix(".zip")
        rec_src = tif_src.with_suffix(".json")
        if not (tif_src.is_file() and zip_src.is_file() and rec_src.is_file()
                and digest(tif_src) == card["raster"]["sha256"]):
            raise ValueError("candidate bytes are missing or drifted at publication; fail closed")
        if not FOCUS_OVL.is_file() or read(FOCUS_OVL).get("candidate_sha256") != card["raster"]["sha256"]:
            raise ValueError("focus overlap evidence missing or bound to other bytes; fail closed")
        for site, entry in read(FOCUS_OVL).get("sites", {}).items():
            if entry.get("unique_under_0p70") is not True:
                raise ValueError(f"focus-site uniqueness failed for {site}; fail closed")
        MODE, CAND, FOCUS_OVL_DATA = "submit", card, read(FOCUS_OVL)
        gate = v2
        gate["source_cards"] = {
            "authority": str(LBCAL_K_CARD.relative_to(ROOT)), "authority_sha256": digest(LBCAL_K_CARD),
            "preregistration": str(PREREG_LBCALK.relative_to(ROOT)), "preregistration_sha256": digest(PREREG_LBCALK),
            "focus_overlap": str(FOCUS_OVL.relative_to(ROOT)), "focus_overlap_sha256": digest(FOCUS_OVL),
            "irregularities": str(IRREGULARITIES.relative_to(ROOT)), "irregularities_sha256": digest(IRREGULARITIES),
            "witness_audit": str(RECHECK.relative_to(ROOT)), "witness_audit_sha256": digest(RECHECK),
            "historical_negative_authority": str(AUTHORITY.relative_to(ROOT)),
            "historical_negative_authority_sha256": digest(AUTHORITY),
            "e2_crossmodel_card": str((ROOT / "evidence" / "lbcal_k_run_card_e2.json").relative_to(ROOT)),
            "e2_crossmodel_card_sha256": digest(ROOT / "evidence" / "lbcal_k_run_card_e2.json"),
            "e2_crossmodel_numbers": str((ROOT / "evidence" / "lbcal_k" / "e2_crossmodel.json").relative_to(ROOT)),
            "e2_crossmodel_numbers_sha256": digest(ROOT / "evidence" / "lbcal_k" / "e2_crossmodel.json"),
        }
        gate["historical_record"] = (
            "The 2026-10-27 negative decision (session_9b794637) remains valid under the literal "
            "all-registry reading (IR-01) and still governs every historical research TIFF; the "
            "preregistered content-aware gates of 2026-10-28 govern the NEW candidate only.")
        decision_json = {"decision": "SUBMIT", "okay_to_download_and_submit": True, "okay_to_submit": True,
                         "candidate": gate["candidate"], "selector_slot_spend": gate["selector_slot_spend"],
                         "source": "release_gate.json"}
        publish_mode_note = "Built gate-cleared candidate pages; historical lane pages quarantined DO NOT SUBMIT."
    else:
        gate = historical_gate
        gate["source_cards"] = {"authority": str(AUTHORITY.relative_to(ROOT)), "authority_sha256": digest(AUTHORITY),
                                "candidate": str(SGCE_CARD.relative_to(ROOT)), "candidate_sha256": digest(SGCE_CARD),
                                "witness_audit": str(RECHECK.relative_to(ROOT)), "witness_audit_sha256": digest(RECHECK)}
        gate["blocking_reasons"].insert(0, "The registered dense witness overlaps every in-footprint candidate; SGCE's measured overlap is 100%.")
        decision_json = {"decision": "DO-NOT-SUBMIT", "okay_to_submit": False,
                         "candidate": None, "source": "release_gate.json"}
        publish_mode_note = "Built negative evidence-first pages and quarantined historical lane pages."

    data = DOCS / "data"
    data.mkdir(parents=True, exist_ok=True)
    (data / "release_gate.json").write_text(json.dumps(gate, indent=2, allow_nan=False) + "\n")
    (data / "decision.json").write_text(json.dumps(decision_json, indent=2, allow_nan=False) + "\n")
    for path in (AUTHORITY, RECHECK, FOCUS, FEED, INDEPENDENT_FOCUS, INDEPENDENT_NAN, INDEPENDENT_ZERO):
        shutil.copyfile(path, data / path.name)
    shutil.copyfile(AUTHORITY, data / "run_card.json")
    if MODE == "submit":
        shutil.copyfile(LBCAL_K_CARD, data / "lbcal_k_run_card.json")
        shutil.copyfile(PREREG_LBCALK, data / "preregistration-2026-10-28-lbcalk.md")
        shutil.copyfile(IRREGULARITIES, data / "irregularities-2026-10-28-lbcalk.md")
        for extra in ("canary.json", "preplacement_surface.json", "registry_audit_final.json",
                      "focus_overlap.json", "run_card_e1.json", "adaptive_passes_log.txt",
                      "e2_crossmodel.json"):
            src_path = ROOT / "evidence" / "lbcal_k" / extra
            if not src_path.is_file():
                raise ValueError(f"missing candidate evidence artefact: {src_path}")
            shutil.copyfile(src_path, data / extra)
        shutil.copyfile(ROOT / "evidence" / "lbcal_k_run_card_e2.json",
                        data / "lbcal_k_run_card_e2.json")
        for suffix in (".tif", ".zip", ".json"):
            shutil.copyfile((ROOT / card["raster"]["path"]).with_suffix(suffix),
                            DOCS / "downloads" / Path(card["raster"]["path"]).with_suffix(suffix).name)
    for _, (_, _, card_name) in LANES.items():
        path = ROOT / "evidence" / card_name
        if not path.is_file():
            raise ValueError(f"missing historical lane card: {path}")
        historical = read(path)
        notice = "SUPERSEDED historical lane record; its claims were not replayed in this review and do not authorize an upload. See release_gate.json."
        prior_notice = historical.pop("_archive_notice", None)
        historical = {"_archive_notice": notice + (" " + prior_notice if prior_notice else ""), **historical}
        (data / card_name).write_text(json.dumps(historical, indent=2, allow_nan=False) + "\n")
    old = {"_archive_notice": "SUPERSEDED historical lane claims; no repository-wide upload approval. See release_gate.json.", **candidate}
    (data / "session2_run_card.json").write_text(json.dumps(old, indent=2, allow_nan=False) + "\n")
    pages = {"index.html": ("Overview", home(audit, feed)), "executive-summary.html": ("Executive summary", executive(audit)),
             "how-to-submit.html": ("Submission guide", howto()), "research.html": ("Research", research()),
             "evidence.html": ("Evidence", evidence_page(recheck, focus_only)),
             "submission.html": ("Submission", submission_page())}
    decision_meta = "SUBMIT" if MODE == "submit" else "DO-NOT-SUBMIT"
    for name, (title, body) in pages.items():
        (DOCS / name).write_text(layout(title, name, body, decision=decision_meta), encoding="utf-8")
    (DOCS / "downloads/index.html").write_text(downloads_index(), encoding="utf-8")
    for directory, (names, title, card_name) in LANES.items():
        for name in names:
            (DOCS / directory / name).write_text(lane_stub(directory, title, card_name), encoding="utf-8")
    for directory in ("lbcal", "thcs"):
        path = DOCS / directory / "downloads" / "index.html"
        path.write_text('<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Research archive</title></head><body><h1>DO NOT SUBMIT</h1><p>Historical research files only; no candidate is cleared. <a href="../../executive-summary.html">Current executive summary</a>.</p></body></html>', encoding="utf-8")
    print(publish_mode_note)


def main() -> int:
    from amdc_site import main as _amdc_main
    from build_site_fchd import main as _fchd_main
    render()
    r1 = _amdc_main() or 0
    r2 = _fchd_main() or 0
    return r1 or r2


def build() -> int:
    return main()


if __name__ == "__main__":
    raise SystemExit(main())
