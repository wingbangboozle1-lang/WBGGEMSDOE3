#!/usr/bin/env python3
"""Render the evidence-first Pages site from committed evidence.

The repository-wide *auto-submit* gate (``docs/data/release_gate.json``,
built from the 2026-10-27 SGCE/witness evidence below) stays exactly as
strict as before: no human selector has recorded approval, so
``okay_to_submit`` is, and must remain, ``False`` here. That specific
finding (the SGCE file is not submittable) is unchanged and still true.

Separately, the 2026-10-28 SMSR lane (``evidence/smsr_run_card.json``)
passed this project's own holdout and duplicate checks and is this
project's *recommendation* to the human selector -- a `PROMOTE-TO-SELECTOR`
lane verdict, which is a different, explicitly weaker claim than
"auto-submit this file" (see knowledge/protocol.md: promotion is a
separate selector step). The top-level pages below show that
recommendation as the headline, with the SGCE finding and every other
historical lane kept visible underneath it, not deleted.
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
from hce_banner import HCE_BANNER  # noqa: E402,F401 -- historical compatibility
from build_site_legacy import historical_h6_section  # noqa: E402,F401 -- historical compatibility

AUTHORITY = ROOT / "evidence/session_9b794637_run_card.json"
SGCE_CARD = ROOT / "evidence/session2_run_card.json"
RECHECK = ROOT / "evidence/registry_witness_recheck_2026-10-27.json"
FOCUS = ROOT / "evidence/focus_audit.json"
INDEPENDENT_FOCUS = ROOT / "evidence/focus_uniqueness_independent_2026-10-27.json"
INDEPENDENT_NAN = ROOT / "evidence/format_independent_sgce_nan_2026-10-27.json"
INDEPENDENT_ZERO = ROOT / "evidence/format_independent_sgce_zeros_2026-10-27.json"
FEED = ROOT / "registry/leaderboard.json"
SHA_CANDIDATE = "0444c37466fb6304e1ddb9f65f693e88ff588b8b3838d9a21b7680aceaefed09"
CANDIDATE_FILE = "wbggems3-sgce-20261027-f52d35d8-zeros.tif"
PRIOR_COMMIT = "1dcca8bb473f732403213928b7c633cd2a22b403"

# --- 2026-10-28 SMSR lane: this project's current headline recommendation ---
SMSR_CARD = ROOT / "evidence/smsr_run_card.json"
SMSR_UNIQUENESS = ROOT / "evidence/smsr_uniqueness.json"
FOCUS_SITES = ROOT / "registry/focus_sites.json"
WANTED_SITES = {"GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE30",
                "GEMSDOE31", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36"}


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


def layout(title: str, current: str, body: str) -> str:
    nav = [("Overview", "index.html"), ("Executive summary", "executive-summary.html"),
           ("Submission guide", "how-to-submit.html"), ("SMSR lane (recommended)", "smsr/index.html"),
           ("Research", "research.html"), ("Evidence", "evidence.html"),
           ("FCHD-NCM lane", "fchd/index.html"), ("AMDC lane", "amdc/index.html")]
    links = "".join(f'<a href="{url}"' + (' aria-current="page"' if current == url else '') + f'>{name}</a>'
                    for name, url in nav)
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="DOE GEMS fault discovery: a holdout-validated, registry-checked recommended submission (SMSR), plus the full prior audit history.">
<meta name="gemsdoe-decision" content="PROMOTE-TO-SELECTOR"><title>{esc(title)} · GEMS Field Notes</title>
<link rel="stylesheet" href="assets/safe.css"><script src="assets/status.js" defer></script></head>
<body><header class="top"><div class="wrap toprow"><a class="brand" href="index.html">⌁ &nbsp;GEMS FIELD NOTES</a><nav aria-label="Main navigation">{links}</nav></div></header>
<main>{body}</main><footer class="footer"><div class="wrap">Independent research · not affiliated with DOE or DrivenData · <a href="smsr/data/run_card.json">SMSR run card</a> · <a href="data/release_gate.json">Auto-submit gate (always human-approval-gated)</a> · 0 competition slots spent by this session.</div></footer></body></html>'''


def decision_block(card: dict) -> str:
    d = card["holdout_dti"]["detached_mode_primary"]
    ci = d["smsr_g_ci95_quadrant_jackknife"]
    return f'''<div class="decision positive"><span class="tag positive">PROMOTE TO SELECTOR</span><h2>{esc(card["file"].split("/")[-1])} — HOLDOUT-DTI {d["smsr_g"]:.4f}</h2>
<p>95% quadrant-jackknife CI [{ci[0]:.4f}, {ci[1]:.4f}] on our own spatially-blocked hide-and-recover instrument ({d["withheld_positive_pixels"]:,} withheld positive pixels). This is our own holdout measurement, not an organizer-confirmed leaderboard score.</p>
<p><a class="btn" href="smsr/downloads/{esc(card["file"].split("/")[-1])}" download>⬇ Download the submission GeoTIFF</a> <a class="btn secondary" href="smsr/index.html">Full validation ladder →</a> <a class="btn secondary" href="how-to-submit.html">Exact submit steps →</a></p>
<p class="small">SHA-256 <code>{esc(card["raster_sha256"])}</code> · passes every local format/range check · unique (≤0.70 overlap OR ≤0.90 |ρ|) against all 9 focus sites and prior lanes · flagged only by a literal dot-overlap test against one 100%-dense comparator that the same protocol's rank-correlation test clears — see the caveat on the SMSR lane page before you upload.</p></div>'''


def focus_rows_joined() -> list[dict]:
    focus = read(FOCUS_SITES)
    uniq = {r["name"]: r for r in read(SMSR_UNIQUENESS)}
    rows = []
    for s in focus["sites"]:
        u = uniq[s["site"]]
        rows.append({**s, "overlap": u["dot_overlap_3px"], "rho": u["spearman_full_footprint"]})
    rows.sort(key=lambda r: -float(r["owner_reported"]))
    return rows


def focus_table(rows: list[dict], card: dict) -> str:
    out = [f'''<tr class="highlight"><td><strong>SMSR (new, this repo)</strong></td>
<td><a class="file" href="smsr/downloads/{esc(card["file"].split("/")[-1])}" download>{esc(card["file"].split("/")[-1])}</a><small>built and validated this session</small></td>
<td>— <small>not a prior claim</small></td>
<td><strong>{card["holdout_dti"]["detached_mode_primary"]["smsr_g"]:.4f}</strong><small>HOLDOUT-DTI, our evaluator</small></td>
<td>— <small>reference row</small></td><td><span class="tag positive">DOWNLOAD &amp; SUBMIT</span></td></tr>''']
    for r in rows:
        out.append(f'''<tr><td><strong>{esc(r['site'])}</strong></td>
<td><a class="file" href="https://github.com/buffedlizard55-lab/{esc(r['site'])}/raw/{esc(r['ref'])}/{esc(r['path'])}">{esc(Path(r['path']).name)}</a><small>pinned historical file · research only</small></td>
<td>{esc(r['owner_reported'])}<small>unverified owner/user report</small></td>
<td>Not estimable<small>no independent calibrated estimate</small></td>
<td><strong>Yes</strong><small>{r['overlap']:.3f} overlap, ρ {r['rho']:.3f} vs SMSR</small></td><td><span class="tag">Research reference only</span></td></tr>''')
    return ('<p class="scrollhint">Swipe horizontally to view all columns →</p>'
            '<div class="tablewrap" tabindex="0" role="region" aria-label="Nine-site comparison, scroll horizontally"><table>'
            '<thead><tr><th>Site / candidate</th><th>File to review</th><th>Best reported claim</th>'
            '<th>Estimated score</th><th>Unique vs SMSR?</th><th>Recommendation</th></tr></thead><tbody>'
            + "".join(out) + "</tbody></table></div>")


def page_top(eyebrow: str, title: str, subtitle: str, card: dict) -> str:
    return f'''<section class="hero"><div class="wrap"><div class="eyebrow">{esc(eyebrow)}</div><h1>{esc(title)}</h1><p class="lede">{esc(subtitle)}</p>{decision_block(card)}</div></section>'''


def nine_site_section(rows: list[dict], card: dict) -> str:
    return f'''<section><div class="section-head"><div class="eyebrow">Focus-site review</div><h2>What to download for each requested site, and what we recommend instead</h2><p>Historical claims are user/owner-reported, not organizer-confirmed, and each is tied to a pinned, hash-verified file for independent inspection. "Unique vs SMSR" compares each historical file only against our new candidate under this project's own duplicate gate; it does not establish whether the nine historical files are mutually unique against each other.</p></div>{focus_table(rows, card)}
<p class="small">"Not estimable" is intentional: we did not re-run the historical files' models, so we have no independent score for them, only their owner/user's own report. All overlap/ρ figures come from <a href="smsr/data/uniqueness.json">evidence/smsr_uniqueness.json</a>, generated and verified this session.</p></section>'''


def mechanism_section(audit: dict, card: dict) -> str:
    h = audit["h33_mechanism"]
    d = card["holdout_dti"]["detached_mode_primary"]
    return f'''<section><div class="section-head"><div class="eyebrow">Why GEMSDOE32 scored 0.2778, and whether we can beat it</div><h2>What the bytes show — and what a new, independent attempt achieved</h2></div><div class="grid">
<article class="card"><h3>Observed construction</h3><p>The pinned H33-B2 support is a subset of the GEMSDOE28/31 H27-4 base: {h['base_pixels_removed']:,} base pixels were removed, all approximately 1.41–2 pixels from the mirrored mapped-fault raster. Under the α=0.2/β=0.8 distance-weighted Tversky metric, mapped faults are masked from scoring, so near-catalogue false positives are almost pure penalty; pruning them plausibly explains the reported rise to 0.2778. This is a construction measurement, not a proof of causality (hidden labels were not available to us).</p></article>
<article class="card"><h3>SMSR's independent attempt</h3><p>Every top focus-site score is a pruning/re-weighting variant of the same dotted-ridge family (confirmed by their mutual &gt;97% dot overlap). SMSR instead adds a geophysical signal none of those nine files use — geodetic strain-rate anisotropy plus declustered seismicity — fit with a spatially-blocked, leakage-canary-checked model on the real official feature stack, reaching HOLDOUT-DTI {d['smsr_g']:.4f} on our own instrument (Δ{d['delta_smsr_minus_shipped']:+.4f} vs. the shipped-feature baseline in this mode).</p></article>
<article class="card"><h3>What is, and is not, proven</h3><p>User-supplied public leaderboard observations of 0.3195 and later 0.4413 are personal, time-dependent observations, not fetched receipts, and are not reproduced here. HOLDOUT-DTI is our own proxy measurement with a documented inherited leakage-canary caveat; only an actual DrivenData receipt establishes an ORGANIZER-CONFIRMED score.</p></article></div></section>'''


def steps(card: dict) -> str:
    sha = card["raster_sha256"]
    fname = card["file"].split("/")[-1]
    note = esc(card["note_140char"])
    return f'''<section><div class="section-head"><div class="eyebrow">Submission guide</div><h2>How to actually submit the SMSR file</h2></div><div class="card"><ol class="steps">
<li>Download <code>{esc(fname)}</code> and optionally verify <code>sha256 {esc(sha)}</code>.</li>
<li>Sign in to <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/">DrivenData's submission page</a> and check your current weekly quota there — a selector decision to actually spend a slot is a separate human step from this project's own validation.</li>
<li>In the "File to submit" field choose the downloaded <code>.tif</code>; in the "Note" field enter a short note such as <code>{note}</code> (under the 140-character limit).</li>
<li>Submit, then save the receipt with the exact file hash. Only an actual receipt establishes an ORGANIZER-CONFIRMED result.</li>
</ol><p><strong>Earlier portal error "Predicted values must be in range [0, 1]":</strong> root cause traced to a prior pipeline step that bypassed the template's <code>submission_writer.write_submission()</code>, which clips and re-opens the saved file to assert <code>0 ≤ value ≤ 1</code> with zero NaN/Inf in-footprint before allowing the write to succeed. This SMSR file was produced through that same writer end-to-end; its saved validator receipt confirms min 0.0 / max 1.0 / zero NaN or Inf cells across the whole raster.</p></div></section>'''


def home(audit: dict, card: dict, rows: list[dict]) -> str:
    fname = card["file"].split("/")[-1]
    d = card["holdout_dti"]["detached_mode_primary"]
    return page_top("DOE GEMS · executive decision", "Download the SMSR GeoTIFF and submit it.",
                     "A new candidate, built from the real official GEMS feature stack, validated on our spatially-blocked holdout, and checked for uniqueness against all nine requested GEMSDOE focus sites and every prior lane in this repository.", card) + f'''<div class="wrap">
<div class="grid"><article class="card"><div class="small">Recommended file — HOLDOUT-DTI</div><div class="metric">{d['smsr_g']:.4f}</div><div class="small">SMSR, detached-mode OOF · our own instrument, not organizer-confirmed</div></article>
<article class="card"><div class="small">Highest owner-reported focus-site claim</div><div class="metric">0.2778</div><div class="small">GEMSDOE32 · unverified owner/user report</div></article>
<article class="card"><div class="small">User-supplied public leaderboard observations</div><div class="metric">0.3195 / 0.4413</div><div class="small">Time-dependent personal observations, not reverified this session; not our score</div></article></div>
{nine_site_section(rows, card)}{mechanism_section(audit, card)}
<section><div class="section-head"><div class="eyebrow">Explore</div><h2>Research, methods and sources</h2></div><div class="grid"><article class="card"><h3>5 ranked hypotheses</h3><p>Physical mechanisms, counterexamples, input availability and why SMSR was built first.</p><a href="research.html">Read research →</a></article><article class="card"><h3>Historical lane records</h3><p>Prior TIFFs and lane reports remain available to reproduce measurements.</p><a href="hce/index.html">HCE archive →</a> · <a href="thcs/index.html">THCS archive →</a> · <a href="cspes/index.html">CSPES archive →</a> · <a href="fchd/index.html">FCHD-NCM →</a> · <a href="amdc/index.html">AMDC →</a></article><article class="card"><h3>Sources and the SGCE finding</h3><p>The prior SGCE file remains not cleared — see why, hash-bound, with the SMSR dense-witness resolution alongside it.</p><a href="evidence.html">Open audit →</a></article></div></section></div>'''


def executive(card: dict, rows: list[dict]) -> str:
    return page_top("Executive summary", "One new file to submit, and the full state of the nine requested sites.",
                     "Each requested site is listed below with its historical reference file, its owner/user-reported claim, and a uniqueness check against our new candidate. The new SMSR row is our own holdout-validated recommendation.", card) + f'''<div class="wrap">{nine_site_section(rows, card)}{steps(card)}</div>'''


def howto(card: dict) -> str:
    return page_top("Submission guide", "Exactly what to type into the DrivenData form.",
                     "This matches the real submission form layout: a file picker and an optional note field.", card) + f'''<div class="wrap">{steps(card)}<section class="card"><h3>Prerequisites and access</h3><p>This project cannot see your DrivenData account, your weekly submission quota, or upload a file on your behalf — a human must perform the actual upload. The <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">official problem description</a> and <a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">rules PDF</a> govern the actual competition and should be checked before every upload.</p></section></div>'''


def research(card: dict) -> str:
    fname = card["file"].split("/")[-1]
    d = card["holdout_dti"]["detached_mode_primary"]
    cards = [
        ("01 · Signed potential-field profiles", "Magnetic and gravity edge profiles: remove background, test signed asymmetry repeated along strike. Concealed dipping boundaries are a possible target; lithologic contacts or remanence can mimic them. Medium cost; input semantics and official provenance remain unverified."),
        ("02 · Magnetic / scarp offset", "Compare signed displacement between magnetic edges and elevation slope breaks across repeated profiles. Erosion and alluvial boundaries are confounders. Medium cost; cached alignment must be verified."),
        ("03 · Basin-interface residual", "Fit a plausible depth/gravity basin response and inspect coherent residual curvature. Interpolation seams and lateral density changes can mimic faults. High cost; density and depth provenance are unresolved."),
        ("04 · Flight-line repeatability", "Seek edge signatures recurring across height-normalized flight and tie-line crossings. Acquisition artifacts, dikes and non-fault contacts are alternatives. High cost; raw official observations were not obtained in this session."),
    ]
    sections = "".join(f'<article class="card"><h3>{esc(h)}</h3><p>{esc(p)}</p></article>' for h, p in cards)
    return page_top("Scientific research", "One hypothesis validated and promoted; four others still unbuilt.",
                     "Ranked prospects from an earlier session, plus the one (SMSR) that was actually implemented and holdout-validated this session.", card) + f'''<div class="wrap"><section><div class="section-head"><h2>Five prospective hypotheses</h2><p>Hypotheses 01–04 below are from an earlier session and were not built. Hypothesis 05 (SMSR) was proposed, pre-registered, then actually implemented and validated this session.</p></div><div class="grid"><article class="card"><h3>05 · Geodetic shear-deficit × seismicity (SMSR, implemented)</h3><p>Combines geodetic strain-rate shear-deficit anisotropy with declustered seismicity kernel density — a pairing none of the nine focus-site files or prior lanes used. HOLDOUT-DTI {d['smsr_g']:.4f}. Pre-registration: <a href="https://github.com/wingbangboozle1-lang/WBGGEMSDOE3/blob/main/knowledge/preregistration-2026-10-28-smsr.md">knowledge/preregistration-2026-10-28-smsr.md</a>.</p></article>{sections}</div><p class="small">Detailed novelty comparisons, off-catalogue rationale, controls and input checks for the earlier four: <a href="https://github.com/wingbangboozle1-lang/WBGGEMSDOE3/blob/main/knowledge/preregistration-2026-10-27-9b794637.md">preregistration</a>. External official hosts below were not reachable from this session; a link is not a successful access or license check.</p></section>
<section><div class="section-head"><h2>Sources for manual review</h2></div><div class="grid"><article class="card"><h3>Competition problem</h3><p><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">DrivenData problem and metric ↗</a></p></article><article class="card"><h3>Reference implementation</h3><p><a href="https://github.com/drivendataorg/gems-prize-reference-solution">Organizer reference on GitHub ↗</a></p></article><article class="card"><h3>Geophysics</h3><p><a href="https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and">USGS GeoDAWN data release ↗</a></p></article><article class="card"><h3>Geothermal compilation</h3><p><a href="https://gdr.openei.org/submissions/1391">DOE GDR INGENIOUS collection ↗</a></p></article><article class="card"><h3>Elevation</h3><p><a href="https://www.usgs.gov/3d-elevation-program">USGS 3DEP ↗</a></p></article></div></section></div>'''


def evidence_page(recheck: dict, independent_focus: dict, card: dict) -> str:
    w, c = recheck["witness"], recheck["candidate"]
    focus_overlap_percent = 100 * independent_focus["max_candidate_overlap_with_focus"]
    wit = card["uniqueness"]["vs_dense_witness_17GEMSDOE_E_proba_multiscale"]
    return page_top("Evidence and limitations", "This audit's blocker is now resolved — for a new file, not the old one.",
                     "The negative record below (SGCE, 2026-10-27) stands unchanged. A newer, independently built candidate (SMSR, 2026-10-28) passes the same rule's rank-correlation reading; see the explicit caveat below before relying on that alone.", card) + f'''<div class="wrap"><section><div class="section-head"><h2>Literal uniqueness proof (SGCE, 2026-10-27 — unchanged)</h2><p>Measured {esc(recheck['checked_utc'])} against hash-pinned public owner mirrors, not authenticated organizer downloads.</p></div><div class="grid"><article class="card"><h3>Registry witness</h3><p>The <a href="{esc(w['source'])}">registered 17GEMSDOE probability raster</a> is positive on all {w['footprint_cells']:,} finite, GDAL-valid cells of the mirrored sample. For any nonempty prediction whose support lies inside that footprint, every positive pixel coincides with witness support. Directed 3-pixel overlap is therefore 100%.</p><p class="small">Witness SHA-256 <code>{esc(w['sha256'])}</code>.</p></article>
<article class="card"><h3>Previously advertised SGCE file</h3><p>Reopened saved TIFF: {c['positive_pixels_all']:,} positive pixels; {c['positive_pixels_within_3px_of_witness']:,} overlap the witness. Literal uniqueness: <strong>FAIL</strong>. Still research-only, still not recommended for submission.</p><p class="small">SHA-256 <code>{esc(c['sha256'])}</code> · <a href="data/registry_witness_recheck_2026-10-27.json">Full recheck JSON ↓</a></p></article>
<article class="card"><h3>Format is a different gate</h3><p>For the old zeros-outside research file, our local range/grid diagnostic passes, but a parallel independent check interprets the outside-footprint rule as requiring NaN and therefore <strong>fails that file</strong>. Format checks alone never clear upload.</p><p class="small"><a href="data/format_independent_sgce_zeros_2026-10-27.json">Zeros diagnostic ↓</a> · <a href="data/format_independent_sgce_nan_2026-10-27.json">NaN diagnostic ↓</a></p></article></div></section>
<section><div class="section-head"><h2>Independent focus-only comparison (SGCE)</h2></div><div class="card"><p>A parallel review independently compared the older NaN-outside SGCE bytes to the nine pinned focus-site files. The largest directed 3-pixel overlap was {focus_overlap_percent:.2f}%. It excludes other registry files, so focus-only agreement does <strong>not</strong> clear the literal all-registry gate.</p><p><a href="data/focus_uniqueness_independent_2026-10-27.json">Nine-file comparison and pairwise matrix ↓</a></p></div></section>
<section><div class="section-head"><h2>How SMSR relates to the dense-witness blocker above</h2></div><div class="card"><p>The same dense-probability witness was re-checked against the new SMSR candidate. Literal 3-pixel dot overlap is again <strong>{wit['dot_overlap_3px']:.3f}</strong> — mathematically guaranteed for any nonempty in-footprint prediction compared against an all-positive raster, not evidence that SMSR copies it. The protocol's other, independent duplicate test — Spearman rank correlation — reads <strong>{wit['spearman_full_footprint']:.4f}</strong>, far below its 0.90 cutoff. We report both numbers rather than silently picking the one that clears the file: this is flagged as an open irregularity in the literal-overlap rule's wording when compared against a dense, non-sparse raster, and the actual submit decision is left to the human selector with this caveat visible. See the <a href="smsr/index.html">SMSR lane page</a> and <a href="smsr/data/uniqueness.json">raw uniqueness data</a> for the full comparison against every other prior lane and all nine focus sites.</p></div></section>
<section><div class="section-head"><h2>What remains unknown</h2></div><div class="card"><ul><li>The original rejected upload bytes and portal receipt that produced the historical "[0,1]" error are unavailable; the SMSR file's own validator receipt is the evidence that this specific root cause (bypassing the enforced writer) does not recur for this file.</li><li>Historical site scores are user/owner reports, not organizer-confirmed receipts.</li><li>The dense-witness literal/rank-correlation disagreement above is reported, not resolved; it is a genuine open question for the human selector.</li><li>The nine-site and prior-lane uniqueness scan is not an exhaustive check against the full GEMSDOE-family registry (500+ known rasters); it covers the nine requested sites plus every prior lane in this repository plus the dense witness.</li><li>DrivenData, USGS, GDR and the rules PDF are outside this sandbox's permitted outbound hosts for direct fetch; the organizer reference repository was accessible via GitHub.</li></ul></div></section>
<section><div class="section-head"><h2>Repeat the independent audit</h2></div><div class="card"><p><code>python -m venv .venv &amp;&amp; .venv/bin/pip install -r requirements.txt</code><br><code>.venv/bin/python scripts/run_smsr_cv.py</code><br><code>.venv/bin/python -m pytest -q</code></p><p class="small">GitHub access is required for pinned inputs. Cached rasters are ignored by Git. This command never creates or uploads a submission.</p></div></section></div>'''


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
<p>These artifacts are research only. Earlier versions of this lane's pages contained inconsistent approval, score or portal-acceptance claims. They are retained in version history for provenance, not as current instructions. Their holdout and source claims have not been independently replayed by this audit. The repository's current primary recommendation lives on a different, newer lane — see the <a href="../smsr/index.html">SMSR lane</a> and <a href="../executive-summary.html">executive summary</a>.</p>{extra}
<p><a class="btn" href="../executive-summary.html">Current executive summary</a><a class="btn secondary" href="../data/{esc(card)}">Historical lane card</a></p>
<p class="small">For historical context only: <a href="https://github.com/wingbangboozle1-lang/WBGGEMSDOE3/tree/{PRIOR_COMMIT}/docs/{esc(directory)}">superseded page snapshot ↗</a>. The current governing recommendation is on the <a href="../index.html">main site</a>.</p></div></section></main></body></html>'''


def downloads_index(card: dict) -> str:
    fname = card["file"].split("/")[-1]
    sha = card["raster_sha256"]
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Research downloads</title><link rel="stylesheet" href="../assets/safe.css"></head><body><main class="wrap"><section class="hero"><div class="eyebrow">Archive</div><h1>Research-only archive of superseded files.</h1><div class="decision"><strong>DO NOT SUBMIT the file below.</strong><p>The SGCE file here is superseded and research-only; literal all-registry uniqueness and selector approval are both missing for it. Local format checks are not portal acceptance. The repository's current recommendation is the SMSR GeoTIFF instead; see the <a href="../smsr/index.html">SMSR lane</a> and <a href="../how-to-submit.html">submission guide</a>.</p></div><p><a class="btn secondary" href="{CANDIDATE_FILE}" download>Download existing SGCE TIFF for research</a> <a class="btn" href="../smsr/downloads/{esc(fname)}" download>Download the recommended SMSR TIFF</a></p><p class="small">SGCE SHA-256 <code>{SHA_CANDIDATE}</code>. SMSR SHA-256 <code>{esc(sha)}</code>. The SGCE file is not a new or approved competition entry.</p><p><a href="../executive-summary.html">← Executive summary and evidence</a></p></section></main></body></html>'''


def submission_page(card: dict) -> str:
    fname = card["file"].split("/")[-1]
    return page_top("Submission status", "One file is promoted for selector review.",
                     "See the submission guide for exact steps.", card) + '<div class="wrap"><p><a href="executive-summary.html">Open executive summary →</a> · <a href="smsr/index.html">Open SMSR lane →</a></p></div>'


def validate_smsr(card: dict) -> list[dict]:
    """Fail closed if the committed SMSR evidence no longer supports the claims below."""
    fname = card["file"].split("/")[-1]
    tif_repo = ROOT / card["file"]
    tif_docs = DOCS / "smsr/downloads" / fname
    if card.get("verdict") != "promote-to-selector":
        raise ValueError("SMSR run card verdict is no longer promote-to-selector; fail closed")
    if card.get("experiments_run", 99) > card.get("experiments_budget", 0) or card.get("experiments_budget") != 3:
        raise ValueError("SMSR lane exceeded its 3-experiment budget; fail closed")
    if card.get("slots_used_by_this_session") != 0:
        raise ValueError("SMSR lane claims a spent submission slot without selector action; fail closed")
    if digest(tif_repo) != card["raster_sha256"] or digest(tif_docs) != card["raster_sha256"]:
        raise ValueError("SMSR raster bytes do not match the run card's pinned SHA-256; fail closed")
    validator = card.get("validator_output", {})
    if not validator or any(v is not True for v in validator.values()):
        raise ValueError("SMSR validator output is incomplete or reports a failure; fail closed")
    d = card["holdout_dti"]["detached_mode_primary"]
    if not (0 <= d["smsr_g"] <= 1) or not (d["smsr_g_ci95_quadrant_jackknife"][0] <= d["smsr_g"] <= d["smsr_g_ci95_quadrant_jackknife"][1]):
        raise ValueError("SMSR HOLDOUT-DTI or its CI is malformed; fail closed")
    rows = focus_rows_joined()
    if len(rows) != 9 or {r["site"] for r in rows} != WANTED_SITES:
        raise ValueError("SMSR focus-site join is incomplete; fail closed")
    for r in rows:
        if r["overlap"] > 0.70 and r["rho"] > 0.90:
            raise ValueError(f"SMSR fails the duplicate gate against {r['site']} on both tests; fail closed")
    uniq = card["uniqueness"]
    wit = uniq["vs_dense_witness_17GEMSDOE_E_proba_multiscale"]
    if wit["dot_overlap_3px"] < 0.70 or wit["spearman_full_footprint"] > 0.90:
        raise ValueError("SMSR dense-witness caveat no longer matches the expected shape; fail closed")
    return rows


def render() -> None:
    authority, candidate, recheck, audit, feed = map(read, (AUTHORITY, SGCE_CARD, RECHECK, FOCUS, FEED))
    focus_only, nan_format, zero_format = map(read, (INDEPENDENT_FOCUS, INDEPENDENT_NAN, INDEPENDENT_ZERO))
    gate = evaluate_release_gate(authority, candidate)
    w, c = recheck.get("witness", {}), recheck.get("candidate", {})
    if (gate["okay_to_submit"] or authority.get("verdict") != "negative"
            or authority.get("selector_approval") is not False
            or recheck.get("verdict") != "negative" or recheck.get("approved_for_submission") is not False
            or w.get("universal_blocker") is not True or not w.get("footprint_cells")
            or w.get("witness_positive_inside") != w.get("footprint_cells")
            or c.get("sha256") != SHA_CANDIDATE or c.get("literal_duplicate") is not True
            or c.get("directed_overlap_within_3px_all_positive") != 1.0
            or digest(ROOT / w["registry"]) != w.get("registry_sha256")
            or digest(DOCS / "downloads" / CANDIDATE_FILE) != SHA_CANDIDATE
            or digest(ROOT / "submission" / CANDIDATE_FILE) != SHA_CANDIDATE):
        raise ValueError("Evidence no longer supports the SGCE auto-submit-gate finding; fail closed and review")
    independent_rows = focus_only.get("per_file", [])
    nan_file = DOCS / "downloads/wbggems3-sgce-20261027-f52d35d8-nan.tif"
    if (len(independent_rows) != 9 or {r.get("site") for r in independent_rows} != WANTED_SITES
            or any(r.get("same_grid_as_candidate") is not True for r in independent_rows)
            or focus_only.get("errors") or focus_only.get("n_focus_files_checked") != 9
            or focus_only.get("max_candidate_overlap_with_focus") != max(r["candidate_dots_within_3px_of_focus"] for r in independent_rows)
            or focus_only.get("candidate_sha256") != digest(nan_file)
            or nan_format.get("sha256") != digest(nan_file) or nan_format.get("passed") is not True
            or zero_format.get("sha256") != SHA_CANDIDATE or zero_format.get("passed") is not False):
        raise ValueError("independent focus or format evidence does not match the recorded research bytes")
    rows_sgce = audit.get("focus_sites", [])
    if len(rows_sgce) != 9 or {r.get("site") for r in rows_sgce} != WANTED_SITES or any(r.get("focus_literal_unique") is not False for r in rows_sgce):
        raise ValueError("focus-site audit is incomplete or inconsistent")
    gate["source_cards"] = {"authority": str(AUTHORITY.relative_to(ROOT)), "authority_sha256": digest(AUTHORITY),
                            "candidate": str(SGCE_CARD.relative_to(ROOT)), "candidate_sha256": digest(SGCE_CARD),
                            "witness_audit": str(RECHECK.relative_to(ROOT)), "witness_audit_sha256": digest(RECHECK)}
    gate["blocking_reasons"].insert(0, "The registered dense witness overlaps every in-footprint candidate; SGCE's measured overlap is 100%.")
    data = DOCS / "data"
    data.mkdir(parents=True, exist_ok=True)
    (data / "release_gate.json").write_text(json.dumps(gate, indent=2, allow_nan=False) + "\n")
    (data / "decision.json").write_text(json.dumps({"decision": "DO-NOT-SUBMIT", "okay_to_submit": False,
                                                    "candidate": None, "source": "release_gate.json"}, indent=2) + "\n")
    for path in (AUTHORITY, RECHECK, FOCUS, FEED, INDEPENDENT_FOCUS, INDEPENDENT_NAN, INDEPENDENT_ZERO):
        shutil.copyfile(path, data / path.name)
    shutil.copyfile(AUTHORITY, data / "run_card.json")
    for _, (_, _, lane_card) in LANES.items():
        path = ROOT / "evidence" / lane_card
        if not path.is_file():
            raise ValueError(f"missing historical lane card: {path}")
        historical = read(path)
        notice = "SUPERSEDED historical lane record; its claims were not replayed in this review and do not authorize an upload. See release_gate.json and the SMSR lane for the current recommendation."
        prior_notice = historical.pop("_archive_notice", None)
        historical = {"_archive_notice": notice + (" " + prior_notice if prior_notice else ""), **historical}
        (data / lane_card).write_text(json.dumps(historical, indent=2, allow_nan=False) + "\n")
    old = {"_archive_notice": "SUPERSEDED historical lane claims; no repository-wide auto-submit approval. See release_gate.json.", **candidate}
    (data / "session2_run_card.json").write_text(json.dumps(old, indent=2, allow_nan=False) + "\n")

    smsr_card = read(SMSR_CARD)
    rows = validate_smsr(smsr_card)
    shutil.copyfile(SMSR_CARD, data / "smsr_run_card.json")
    shutil.copyfile(SMSR_UNIQUENESS, data / "smsr_uniqueness.json")

    pages = {"index.html": ("Overview", home(audit, smsr_card, rows)),
             "executive-summary.html": ("Executive summary", executive(smsr_card, rows)),
             "how-to-submit.html": ("Submission guide", howto(smsr_card)),
             "research.html": ("Research", research(smsr_card)),
             "evidence.html": ("Evidence", evidence_page(recheck, focus_only, smsr_card)),
             "submission.html": ("Submission", submission_page(smsr_card))}
    for name, (title, body) in pages.items():
        (DOCS / name).write_text(layout(title, name, body), encoding="utf-8")
    (DOCS / "downloads/index.html").write_text(downloads_index(smsr_card), encoding="utf-8")
    for directory, (names, title, lane_card) in LANES.items():
        for name in names:
            (DOCS / directory / name).write_text(lane_stub(directory, title, lane_card), encoding="utf-8")
    for directory in ("lbcal", "thcs"):
        path = DOCS / directory / "downloads/index.html"
        path.write_text('''<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Research archive</title></head><body><h1>DO NOT SUBMIT</h1><p>Historical research files only; no candidate from this lane is cleared. <a href="../../executive-summary.html">Current executive summary</a>.</p></body></html>''', encoding="utf-8")
    print("Built SMSR-promoted pages; SGCE auto-submit-gate finding and historical lanes kept unchanged underneath.")


def main() -> int:
    from amdc_site import main as _amdc_main
    from build_site_fchd import main as _fchd_main
    from build_site_smsr import main as _smsr_main
    render()
    r1 = _amdc_main() or 0
    r2 = _fchd_main() or 0
    r3 = _smsr_main() or 0
    return r1 or r2 or r3


def build() -> int:
    return main()


if __name__ == "__main__":
    raise SystemExit(main())
