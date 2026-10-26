"""Render a static, fail-closed GEMS research and submission site."""
from __future__ import annotations

import html
import json
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
DATE = "2026-10-26"

STYLE = r"""
:root{color-scheme:light;--ink:#172d36;--muted:#48616b;--line:#d5e0e2;--accent:#087e83;--danger:#9b2727;--danger-bg:#fff0ed;--amber:#8a4a08;--amber-bg:#fff7e9}*{box-sizing:border-box}body{margin:0;background:#f3f7f7;color:var(--ink);font:16px/1.65 system-ui,-apple-system,Segoe UI,sans-serif}a{color:#08666b;text-underline-offset:3px}a:focus-visible{outline:3px solid #ca6e20}header{background:#122f39;color:#fff;padding:22px max(5%,calc((100% - 1200px)/2))}header a{color:#acedef}.eyebrow{font-size:12px;letter-spacing:.15em;text-transform:uppercase}.brand{font-size:1.05rem;font-weight:700;margin:0 0 12px}nav{display:flex;gap:16px 24px;flex-wrap:wrap}main{max-width:1240px;margin:auto;padding:34px 24px 64px}h1{font-size:clamp(2rem,4vw,3.35rem);line-height:1.12;letter-spacing:-.04em;max-width:22ch}h2{margin:2.2rem 0 .65rem;line-height:1.3}p{max-width:95ch}.muted,small{color:var(--muted)}small{display:block;font-size:.86em}code{overflow-wrap:anywhere;font-size:.9em}pre{white-space:pre-wrap;background:#e5eeee;padding:16px;overflow:auto}.banner{border-left:7px solid var(--danger);background:var(--danger-bg);padding:22px 26px;margin:22px 0;border-radius:8px}.banner strong{display:block;color:var(--danger);font-size:1.35rem;letter-spacing:.02em}.audit{border-left-color:var(--amber);background:var(--amber-bg)}.audit strong{color:var(--amber)}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:14px;margin:20px 0}.card{padding:20px;background:#fff;border:1px solid var(--line);border-radius:12px}.card b.metric{display:block;font-size:1.8rem;line-height:1.25}.button{display:inline-block;background:var(--accent);color:white;padding:10px 15px;border-radius:6px;text-decoration:none;margin:6px 8px 6px 0;font-weight:650}.button.danger{background:var(--danger)}.button.secondary{background:#38515b}.scroll{overflow-x:auto;background:#fff;border:1px solid var(--line);border-radius:12px}table{border-collapse:collapse;width:100%;font-size:14px;min-width:760px}th,td{padding:13px 14px;text-align:left;border-bottom:1px solid var(--line);vertical-align:top}th{background:#e5f0ef}tr:last-child td{border-bottom:0}li{margin-bottom:9px}.pill{display:inline-block;border-radius:999px;padding:2px 9px;background:#f4dfdd;color:var(--danger);font-weight:700;font-size:.82em}.good{background:#e0f1e9;color:#185a3a}.callout{padding:16px 20px;background:#fff;border:1px solid var(--line);border-radius:10px}footer{border-top:1px solid var(--line);padding:22px;color:var(--muted);font-size:.9em}hr{border:0;border-top:1px solid var(--line);margin:30px 0}@media(max-width:640px){main{padding:24px 16px 48px}header{padding:18px 16px}nav{gap:10px 16px}.banner{padding:18px}}
"""


def esc(value) -> str:
    return html.escape(str(value), quote=True)


def page(title: str, body: str, active: str = "") -> str:
    links = [
        ("index.html", "Decision"),
        ("executive-summary.html", "Nine-site summary"),
        ("hypotheses.html", "Hypotheses"),
        ("research.html", "Research review"),
        ("submission.html", "Submission guide"),
        ("run-card.json", "Run card"),
    ]
    nav = "".join(
        f'<a href="{path}"{(" aria-current=page" if active == path else "")}>{label}</a>'
        for path, label in links
    )
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} · GEMS Evidence Lab</title><style>{STYLE}</style></head>
<body><header><div class="brand">WB-GEMS-DOE-3 · GEMS Evidence Lab</div><nav aria-label="Main">{nav}</nav></header>
<main id="content">{body}</main><footer>Snapshot: {DATE} · No competition upload performed · Research/audit only · Evidence over optimism</footer></body></html>'''


def load_inputs():
    return json.loads((ROOT / "research/input_manifest.json").read_text())


def focus_table(audit: dict, inputs: list[dict]) -> str:
    focus_rows = json.loads((ROOT / "knowledge/focus-sites.json").read_text())
    by_site = {int(row["site"]): row for row in focus_rows}
    rows = []
    for item in inputs[:9]:
        name = item["id"]
        site_number = int(name.removeprefix("GEMSDOE"))
        measured = audit["rows"][name]
        score = by_site[site_number]["reported"]
        comparisons = measured["comparisons"].values()
        max_rho = max(abs(float(x["final_binary_spearman"])) for x in comparisons)
        max_overlap = float(measured["max_overlap"])
        repo_url = f"https://github.com/{item['repo']}/blob/{item['ref']}/{item['path']}?raw=true"
        file_name = Path(item["path"]).name
        rows.append(f'''<tr>
<td><strong>{esc(name)}</strong><small>Peer-maintained project</small></td>
<td><a href="{esc(repo_url)}">{esc(file_name)}</a><small>Commit-pinned historical raster; audit/reference only</small></td>
<td><strong>USER-REPORTED {esc(score)}</strong><small>No byte-linked organizer receipt in this review</small></td>
<td>Not estimated<small>No new candidate HOLDOUT-DTI or calibrated forecast</small></td>
<td><strong>{max_overlap:.2%}</strong><small>Max directed overlap within 3 px; stop threshold &gt;70%</small><strong>|ρ|max {max_rho:.4f}</strong><small>Final binary raster; stop threshold &gt;0.90</small></td>
<td><span class="pill">NO</span><small>Fails at least one rule within the pinned focus-nine subset</small></td>
</tr>''')
    return '<div class="scroll" role="region" aria-label="Nine-site audit table" tabindex="0"><table><thead><tr><th>Site</th><th>Historical file</th><th>Reported result</th><th>New candidate estimate</th><th>Measured focus-nine novelty</th><th>Unique?</th></tr></thead><tbody>' + "".join(rows) + "</tbody></table></div>"


def candidate_panel(card: dict) -> str:
    artifact = card["artifact"]
    registry = card["registry_comparison"]
    measured = registry["measured_subset"]
    footprint = registry["registered_lattice_coverage_bound"]
    old = registry["prior_58_raster_report"]
    file_path = Path(artifact["path"]).name
    return f'''<div class="banner" role="status">
<strong>DO NOT SUBMIT — existing artifact fails the literal uniqueness gate</strong>
<p>A previous merged change added this candidate. It is available only for audit/research; this review did not generate it or rerun a geological experiment.</p>
<p><a class="button danger" href="downloads/{esc(file_path)}" download>Download for audit only — NOT for submission</a>
<a class="button secondary" href="run-card.json">Open current decision card</a></p>
<p><b>File:</b> <code>{esc(artifact['filename'])}</code><br><b>SHA-256:</b> <code>{esc(artifact['sha256'])}</code><br><b>Reported dots:</b> {int(artifact['dots']):,}</p>
</div>
<div class="cards">
<div class="card"><b class="metric">{float(measured['candidate_total_dot_overlap_max_within_3px']):.2%}</b>Measured fraction of all candidate dots within 3 px of the registered lattice in a 10-raster pinned owner-mirror subset; threshold is 70%.</div>
<div class="card"><b class="metric">{float(measured['candidate_in_footprint_dot_overlap_with_lattice_within_3px']):.2%}</b>Measured overlap among the {int(footprint['candidate_dots_inside_scored_footprint']):,} dots inside the owner-mirrored scored footprint; {int(footprint['candidate_dots_outside_scored_footprint']):,} additional positive cells lie outside that mask.</div>
<div class="card"><b class="metric">NO HOLDOUT-DTI</b>No evaluator CI, feature-by-feature leakage canary, defensible score estimate, or ORGANIZER-CONFIRMED receipt.</div>
</div>
<section class="card"><h2>Why the old uniqueness pass is superseded</h2>
<p>The legacy report gave maximum within-3-pixel overlap {float(old['reported_overlap_fraction_max_within_3px']):.2%} and maximum |ρ| {float(old['reported_abs_spearman_max']):.4f} against {int(old['reported_registry_raster_count'])} local rasters. Its “surface” comparison loaded the final binary TIFF, so the correlation is not a pre-placement continuous-surface result. A separate pinned owner-mirror recheck including the registered lattice measures {float(measured['candidate_total_dot_overlap_max_within_3px']):.2%} final-dot overlap with that lattice—above the 70% stop threshold. These comparison scopes do not establish full-registry clearance; the mirrors are not organizer-authenticated and the complete live registry is unavailable.</p>
<p><b>Format:</b> the candidate passes numeric/range/grid checks against the repository's all-zero grid, but the owner-mirrored sample mask shows {int(footprint['candidate_dots_outside_scored_footprint']):,} positive cells outside its finite footprint. The sample is not organizer-authenticated, so outside-footprint convention and portal acceptance remain unverified.</p></section>'''


def build():
    audit = json.loads((DOCS / "audit.json").read_text())
    card = json.loads((ROOT / "evidence/run_card.json").read_text())
    inputs = load_inputs()
    sites = focus_table(audit, inputs)
    candidate = candidate_panel(card)
    lane = card["lane"]
    measured = card["registry_comparison"]["measured_subset"]

    decision = f'''<div class="eyebrow">Integrated review · {DATE}</div>
<h1>Submission decision</h1>
{candidate}
<section class="card"><h2>What is blocking release?</h2><ul>
<li><b>Lane:</b> {esc(lane['status'])}; no single method paragraph was assigned.</li>
<li><b>Literal registry rule:</b> the 35,000-dot artifact has a measured {float(measured['candidate_total_dot_overlap_max_within_3px']):.2%} within-3-pixel overlap with the registered lattice in the pinned audit subset, above the 70% stop rule. Do not tune placement to evade the control.</li>
<li><b>Scientific validation:</b> required labels, cached feature stack, segment folds, and a matched fold-local baseline are absent. No HOLDOUT-DTI or leakage canary exists.</li>
<li><b>Registry:</b> no complete live manifest is available. The measured duplicate against one registered control is sufficient to reject this artifact; it does not certify other candidates.</li>
<li><b>Submission selector:</b> no current weekly cap/usage check, upload, or organizer receipt was performed.</li>
</ul><p><strong>Download for audit: YES. Submit: NO. Score estimate: none.</strong> A numerical projection is not a score.</p></section>
<section class="card"><h2>Use this project safely</h2><p>Start with the <a href="executive-summary.html">nine-site executive summary</a>, review the <a href="hypotheses.html">ranked proposals</a>, and read the <a href="research.html">full scientific review</a>. The <a href="../knowledge/protocol.md">release protocol</a> and <a href="run-card.json">current JSON card</a> define the gates. No submission slot has been selected or spent.</p></section>'''
    (DOCS / "index.html").write_text(page("Submission decision", decision, "index.html"))

    guide = f'''<div class="eyebrow">Executive summary · nine focus projects</div>
<h1>Historical results are not a new submission score.</h1>
<div class="banner"><strong>Current decision: DO NOT SUBMIT</strong><p>The existing H_STEP-OVER TIFF is downloadable for audit only and fails the literal registered-lattice overlap gate. No new candidate estimate, compliant HOLDOUT-DTI, or organizer receipt is available.</p><p>Among the nine site claims, the highest listed value is GEMSDOE32 at 0.2778, labelled <b>USER-REPORTED</b>—not ORGANIZER-CONFIRMED. Other conflicting leaderboard values have not been independently checked.</p></div>
<h2>Nine-site comparison</h2>
<p>Uniqueness values below are computed from the commit-pinned historical binary rasters in <code>docs/audit.json</code>. They compare the focus-nine subset only—not the full evolving competition registry. The directional overlap and final-binary rank correlation are not continuous-surface tests. Site score claims remain owner/user reports with no receipt binding the raster bytes to the displayed value.</p>
{sites}
<section class="card"><h2>What may be downloaded?</h2><p>The only project candidate presently linked from the decision page is the earlier 35,000-dot GeoTIFF, for audit/research only. Its SHA-256 is <code>{esc(card['artifact']['sha256'])}</code>. It is <b>not approved for a competition upload</b>; do not spend a weekly slot on it.</p><p>No new candidate leaderboard estimate is defensible. The candidate has no HOLDOUT-DTI; do not infer a score from dot count, novelty, historic site scores, or a model label.</p><a class="button secondary" href="index.html">Return to the decision and audit-only file</a></section>
<section class="card"><h2>How a future submission becomes eligible</h2><ol>
<li>Assign the explicit single method lane, authenticate data provenance and the shared template, and freeze the complete registry including calibration/null entries.</li>
<li>Run each feature alone through the leakage canary. Treat AUC &gt;0.90 as leakage until disproven.</li>
<li>Use buffered whole-segment hide-and-recover folds; derive catalogue features from visible faults only, mask visible faults pixel-exactly, and evaluate with the shared pooled DTI (α=0.2, β=0.8, 300 m triangular kernel). Report evaluator version, withheld-positive count, and 95% CI.</li>
<li>Require a paired improvement over a same-fold incumbent with a positive lower confidence bound. Check the continuous surface before placement and final dots against every registry raster; stop on either literal duplicate threshold.</li>
<li>Reuse the shared submission writer. Reopen saved bytes and verify the actual sample grid, single band, finite/range policy, CRS, shape, transform, hash, and note length. Do not silently clamp invalid values.</li>
<li>A separate selector checks the current organizer submission cap and remaining slots. Only an approved, fully gated artifact receives a release download link.</li>
<li>Only then submit the exact hash through the organizer page, use a note of no more than 140 characters, and retain the matching receipt. This project has not performed that step.</li>
</ol></section>
<section class="card"><h2>Format-error prevention</h2><p>For a future candidate, run a read-only local check against the authenticated sample:</p><pre>python scripts/check_candidate.py candidate.tif --template data/sample_submission.tif</pre><p>The current authenticated sample is absent, and a local pass alone would not prove portal acceptance or scientific eligibility.</p></section>'''
    (DOCS / "executive-summary.html").write_text(page("Executive summary and submission guide", guide, "executive-summary.html"))

    submission = f'''<div class="eyebrow">Submission guide · fail closed</div><h1>How to submit—only after clearance</h1>
<div class="banner"><strong>DO NOT SUBMIT THE CURRENT TIFF</strong><p>A GeoTIFF exists in the repository for audit/research, but its measured 97.87% lattice overlap fails the strict uniqueness gate, and required holdout/data/lane gates are missing. The audit-only download link is on the <a href="index.html">decision page</a>; it is not a submission link.</p></div>
<section class="card"><h2>Before an eligible release exists</h2><ol>
<li>Resolve the method lane, authenticated training inputs, labels, fold definitions, complete registry, and incumbent baseline.</li>
<li>Complete leakage canaries and the prescribed buffered whole-segment holdout. Record HOLDOUT-DTI with evaluator version, withheld positives, and 95% CI; keep it separate from organizer scores.</li>
<li>Pass both continuous-surface and final-dot uniqueness gates, then validate the saved GeoTIFF against the authenticated sample and the shared writer.</li>
<li>Obtain separate selector approval for a live weekly slot. No automatic upload or slot selection is available in this project.</li>
<li>Download only the exact artifact hash authorized in the current run card. The current run card says <b>negative</b>; no authorized submission file is published.</li>
</ol></section>
<section class="card"><h2>Once a future candidate is explicitly approved</h2><ol>
<li>Open the official <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">DOE GEMS competition page</a> and use its submission form.</li>
<li>Select the approved single-band GeoTIFF (or a ZIP containing only that TIFF, if the official form permits it).</li>
<li>Enter the exact run-card name and a note no longer than 140 characters.</li>
<li>Save the returned receipt, timestamp, score, and exact file SHA-256. Only a receipt that binds the file to the result is <code>ORGANIZER-CONFIRMED</code>.</li>
</ol><p>A local HOLDOUT-DTI is not an organizer score, and a successful local range check does not prove the portal will accept a file.</p></section>
<section class="card"><h2>Range validation</h2><p>Run the read-only validator against the official sample when available:</p><pre>python scripts/check_candidate.py candidate.tif --template data/sample_submission.tif</pre><p>It cannot authorize a submission. Never silently clip model output or substitute a repository template for the authenticated sample.</p></section>'''
    (DOCS / "submission.html").write_text(page("Submission guide", submission, "submission.html"))

    research_html = markdown.markdown((ROOT / "research/REVIEW.md").read_text(), extensions=["tables", "fenced_code"])
    (DOCS / "research.html").write_text(page("Scientific review", research_html, "research.html"))
    hypotheses_html = markdown.markdown((ROOT / "knowledge/hypotheses.md").read_text(), extensions=["tables", "fenced_code"])
    (DOCS / "hypotheses.html").write_text(page("Ranked geological hypotheses", hypotheses_html, "hypotheses.html"))

    (DOCS / "run-card.json").write_text(json.dumps(card, indent=2, ensure_ascii=False, allow_nan=False) + "\n")


if __name__ == "__main__":
    build()
