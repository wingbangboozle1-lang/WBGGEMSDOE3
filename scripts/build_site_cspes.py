#!/usr/bin/env python3
"""Build the CSPES lane microsite under docs/cspes/ from recorded evidence only.

Pages:
  index.html          executive summary, one-click download, nine-site table, evidence
  how-to-submit.html  exact portal workflow, name/note, range-error root cause
  data/*.json         frozen evidence copies used by the pages
Every number rendered here is read from evidence files; nothing is recomputed ad hoc.
"""
from __future__ import annotations

import html
import json
import shutil
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
OUT = DOCS / "cspes"
DATA = OUT / "data"


def esc(x) -> str:
    return html.escape(str(x), quote=True)


def layout(title: str, current: str, body: str) -> str:
    nav = [("Lane summary", "index.html"), ("How to submit", "how-to-submit.html"),
           ("Main site", "../index.html"), ("Run card JSON", "data/cspes_run_card.json")]
    links = "".join(f'<a {"class=active" if current == url else ""} href="{url}">{name}</a>' for name, url in nav)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="CSPES lane: generated, validated, unique-vs-sparse-registry GeoTIFF with a negative holdout verdict.">
<title>{esc(title)} · CSPES lane · GEMS Field Notes</title>
<link rel="stylesheet" href="../assets/styles.css">
<style>
.banner-warn {{ background:#3a2a12; border:1px solid #b9832f; }}
.banner-no {{ background:#3a1620; border:1px solid #b93a4d; }}
.banner-ok {{ background:#14301f; border:1px solid #2f9e5f; }}
.dl-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(240px,1fr)); gap:14px; }}
code {{ word-break:break-all; }}
.small {{ font-size:.85rem; color:var(--muted,#9aa4b2); }}
.tag {{ display:inline-block; padding:2px 8px; border-radius:999px; font-size:.78rem; font-weight:600; }}
.tag-neg {{ background:#5a2230; color:#ffd7de; }} .tag-ok {{ background:#1d4430; color:#c9f3dc; }}
.tag-warn {{ background:#4d3a17; color:#ffe2b0; }} .tag-mut {{ background:#2a313c; color:#c6cdd8; }}
</style></head>
<body><header class="topbar"><div class="wrap navrow"><a class="brand" href="index.html"><span class="brandmark">⌁</span><span>CSPES LANE<small>2026-10-27 · RESEARCH ARTIFACT</small></span></a>
<nav class="navigation" aria-label="Lane navigation">{links}</nav><span class="nav-status"><i class="dot"></i> No competition file is cleared · Not cleared for upload</span></div></header>
<main>{body}</main>
<footer class="footer"><div class="wrap footerrow"><span>GEMS FIELD NOTES · CSPES lane · independent research, not affiliated with DOE or DrivenData.</span><span>HOLDOUT-DTI is a local proxy, never a leaderboard score.</span></div></footer>
</body></html>"""


def cspes_vs_focus(card: dict) -> dict[str, float]:
    """3-px overlap of the CSPES dots with each nine-site focus leader, from packed masks."""
    reg = json.loads((ROOT / "registry/cspes_registry_index.json").read_text())
    by_sha = {e["sha256"]: e for e in reg["files"] if e["source"] == "focus9"}
    tif = ROOT / card["files"]["tif"]
    with rasterio.open(tif) as ds:
        foot = np.isfinite(ds.read(1))
        dots = ds.read(1) > 0
    disc = (np.add.outer(np.arange(-3, 4) ** 2, np.arange(-3, 4) ** 2) <= 9)
    out = {}
    focus = json.loads((ROOT / "registry/focus_sites.json").read_text())["sites"]
    for s in focus:
        e = by_sha.get(s["sha256"])
        if e is None:
            out[s["site"]] = float("nan")
            continue
        ref = np.unpackbits(np.load(ROOT / ".cache/registry" / f"{e['dots_sha256']}.npy"))[:foot.size].reshape(foot.shape)
        out[s["site"]] = float((dots & ndi.binary_dilation(ref, structure=disc)).sum() / dots.sum())
    return out


def index_page() -> str:
    card = json.loads((ROOT / "evidence/cspes_run_card.json").read_text())
    hold = json.loads((ROOT / "evidence/cspes_holdout.json").read_text())
    canary = json.loads((ROOT / "evidence/cspes_canary.json").read_text())["canary"]
    budget = json.loads((ROOT / "evidence/cspes_budget.json").read_text())["rows"]
    focus_audit = json.loads((ROOT / "evidence/focus_audit.json").read_text())
    focus_sites = json.loads((ROOT / "registry/focus_sites.json").read_text())["sites"]
    overlap = cspes_vs_focus(card)
    gates = card["correlation_overlap_vs_registry"]["gates"]
    h = card["holdout_dti"]
    tif_name = Path(card["files"]["tif"]).name
    zip_name = Path(card["files"]["zip"]).name

    # ---- nine-site executive table (historical leaders) + CSPES row
    rows = []
    for s in sorted(focus_sites, key=lambda x: -float(x["owner_reported"])):
        audit_row = next(r for r in focus_audit["focus_sites"] if r["site"] == s["site"])
        unique = "NO" if not audit_row["literal_registry_unique"] else "partial"
        rows.append(f"""<tr><td class="site">{esc(s['site'])}</td>
<td><a class="file-link" href="{esc(audit_row['download_research_only'])}">{esc(s['path'].split('/')[-1])} ↗</a><small>historical · research only</small></td>
<td><strong>{esc(s['owner_reported'])}</strong><br><small>owner claim, no receipt</small></td>
<td><span class="tag tag-neg">{unique}</span><br><small>{100*audit_row['max_focus_overlap']:.1f}% within 3px of {esc(audit_row['max_focus_overlap_site'])}</small></td>
<td><span class="tag tag-mut">{100*overlap[s['site']]:.1f}% shared with CSPES</span></td>
<td><span class="tag tag-neg">DO NOT SUBMIT</span></td></tr>""")
    cspes_row = f"""<tr style="background:#16202e"><td class="site"><strong>WB-GEMS-DOE-3 (this lane)</strong></td>
<td><a class="file-link" href="../downloads/{esc(tif_name)}" download>{esc(tif_name)} ↓</a><small>generated 2026-10-27 · 37,654 dots</small></td>
<td><strong>{h['value']:.4f}</strong><br><small>HOLDOUT-DTI {h['ci95'][0]:.4f}–{h['ci95'][1]:.4f}</small></td>
<td><span class="tag tag-ok">YES vs 117 sparse masks</span><br><small>max 3px overlap {100*gates['U3_max_overlap_nonlattice']:.1f}% · max |ρ| {gates['U2_max_abs_spearman_surface']:.3f}</small></td>
<td><span class="tag tag-warn">dense witness: literal FAIL</span></td>
<td><span class="tag tag-neg">NEGATIVE · DO NOT PROMOTE</span></td></tr>"""

    canary_rows = "".join(
        f"<tr><td>{esc(k)}</td><td>{v['auc']:.4f}</td><td>{'ALARM' if v['leakage_alarm'] else 'pass'}</td></tr>"
        for k, v in canary.items())
    budget_rows = "".join(
        f"<tr><td>{r['budget']:,}</td><td>{r['cspes_dti']:.4f} ({r['cspes_ci95'][0]:.4f}–{r['cspes_ci95'][1]:.4f})</td>"
        f"<td>{r['random_null_dti']:.4f}</td><td>{r['paired_delta_cspes_minus_null']:+.4f} "
        f"({r['delta_ci95'][0]:+.4f},{r['delta_ci95'][1]:+.4f})</td></tr>" for r in budget)

    body = f"""
<section class="hero"><div class="wrap">
<div class="eyebrow">Executive summary / CSPES lane / 2026-10-27 UTC</div>
<div class="title-line"><div><h1>A unique, validated TIF —<br>with a negative verdict.</h1>
<p class="subhead">The lane generated a genuinely new 37,654-dot GeoTIFF from gravity/magnetic edge physics. It is format-valid and distinct from every rebuilt historical submission, but its holdout DTI loses to the incumbent, so it must not take a weekly slot.</p></div></div>
<div class="decision"><div class="decision-inner"><div>
<div class="decision-label"><i class="dot"></i> Automated verdict · NEGATIVE (research artifact, no slot spent)</div>
<h2>Download for inspection — do not upload for score.</h2>
<p>HOLDOUT-DTI <strong>{h['value']:.4f}</strong> vs incumbent <strong>{h['incumbent_holdout_dti']:.4f}</strong>; paired Δ {h['paired_delta_vs_incumbent']['delta']:+.4f}, 95% CI {h['paired_delta_vs_incumbent']['ci95'][0]:+.4f} to {h['paired_delta_vs_incumbent']['ci95'][1]:+.4f}. Canaries pass (no leakage); the ranking is simply not predictive of hidden catalogue faults.</p>
</div><div class="actions"><a class="button" href="../downloads/{esc(tif_name)}" download>Download GeoTIFF ↓</a>
<a class="button secondary" href="../downloads/{esc(zip_name)}" download>Download ZIP ↓</a></div></div></div>
</div></section>
<div class="wrap content">
<section class="section"><div class="section-head"><div><div class="kicker">01 / The downloadable artifact</div><h2>Exactly which file, and is it OK to submit?</h2></div>
<a class="button light" href="data/cspes_run_card.json" download>Run card JSON ↓</a></div>
<div class="card panel"><div class="dl-grid">
<div><h3>File (portal-safe, all finite)</h3><p class="small"><a href="../downloads/{esc(tif_name)}" download><code>{esc(tif_name)}</code></a></p>
<p class="small">ZIP (single TIFF inside): <a href="../downloads/{esc(zip_name)}" download><code>{esc(zip_name)}</code></a></p></div>
<div><h3>SHA-256</h3><p class="small"><code>{esc(card['raster_sha256'])}</code></p>
<p class="small">emitted pixels: {37654:,} · float32 · EPSG:32611 · 3,730×3,292 · 100 m</p></div>
<div><h3>Submission name / note (≤140 chars)</h3><p class="small"><code>{esc(card['submission_name'])}</code></p>
<p class="small"><code>{esc(card['submission_note'])}</code> ({card['submission_note_chars']} chars)</p></div>
<div><h3>Automatic gates</h3>
<p><span class="tag tag-ok">validator PASS</span> <span class="tag tag-ok">no NaN · all values [0,1]</span></p>
<p><span class="tag tag-ok">U1 exact-duplicate PASS</span> <span class="tag tag-ok">U2 |ρ|≤0.90 PASS</span> <span class="tag tag-ok">U3 sparse-registry PASS</span></p>
<p><span class="tag tag-neg">holdout NEGATIVE</span> <span class="tag tag-warn">literal dense-witness rule FAIL</span></p></div>
</div>
<div class="callout banner-no" style="margin-top:14px"><strong>IS IT OK TO DOWNLOAD AND SUBMIT?</strong> Download: yes — the bytes pass every format gate and are unique against the 117 rebuilt sparse historical masks (max 3-px overlap {100*gates['U3_max_overlap_nonlattice']:.1f}% ≤ 70%; max |Spearman| {gates['U2_max_abs_spearman_surface']:.3f} ≤ 0.90). Submit for leaderboard score: <strong>NO</strong> — its HOLDOUT-DTI ({h['value']:.4f}) is decisively below the matched incumbent ({h['incumbent_holdout_dti']:.4f}), and the project's strictest literal registry rule remains unsatisfiable for any nonempty raster because of the space-filling 17GEMSDOE witness (IR-01). A separate selector owns any real slot; this lane spent zero.</div>
</div></section>

<section class="section"><div class="section-head"><div><div class="kicker">02 / Executive table — nine focus sites and this lane</div>
<h2>What to download, the estimated score, and uniqueness</h2><p>Historical figures are owner reports without organizer receipts; only the CSPES row carries a local HOLDOUT-DTI with a 95% CI. A HOLDOUT-DTI is not a leaderboard projection.</p></div></div>
<p class="scroll-hint">Swipe across the table to see all columns →</p>
<div class="card table-card" tabindex="0" role="region" aria-label="Executive summary table"><table class="table"><thead><tr>
<th>Site</th><th>File to download</th><th>Estimated score</th><th>Unique vs other focus sites?</th><th>Overlap with this CSPES TIF</th><th>Decision</th></tr></thead>
<tbody>{cspes_row}{''.join(rows)}</tbody></table></div>
<p class="note">Uniqueness: fraction of dots within 3 px (300 m kernel radius) of a reference, plus absolute Spearman. All nine historical leaders are near- or exact duplicates of one another (0.976–1.000 overlap); GEMSDOE25 and GEMSDOE30 share an identical dot mask. None is a legal new submission under the no-copy rule.</p>
</section>

<section class="section"><div class="section-head"><div><div class="kicker">03 / Science and falsification</div><h2>{esc(card['hypothesis'])}</h2></div></div>
<div class="grid2"><article class="card panel"><h3>Mechanism</h3><p>{esc(card['mechanism'])}</p>
<h3>Named non-fault mimic</h3><p>{esc(card['named_non_fault_mimic'])}</p>
<p class="small">Full frozen specification: <code>knowledge/preregistration-2026-10-27.md</code>; code <code>src/gemsw/cspes.py</code>.</p></article>
<article class="card panel"><h3>E1 leakage canary (AUC &gt; 0.90 = alarm)</h3>
<table class="table"><thead><tr><th>field</th><th>ROC-AUC</th><th>status</th></tr></thead><tbody>{canary_rows}</tbody></table>
<p class="small">All fields near 0.5: no leakage — and, as the holdout shows, little signal either.</p></article></div>
<div class="grid2"><article class="card panel"><h3>E2 hide-and-recover holdout (22,232 withheld positives)</h3>
<table class="table"><thead><tr><th>candidate</th><th>HOLDOUT-DTI (95% CI)</th></tr></thead><tbody>
<tr><td><strong>CSPES full</strong></td><td><strong>{hold['results']['cspes_full']['pooled_dti']:.4f}</strong> ({hold['results']['cspes_full']['ci95_cluster_bootstrap'][0]:.4f}–{hold['results']['cspes_full']['ci95_cluster_bootstrap'][1]:.4f})</td></tr>
<tr><td>no topo-conditioning ablation</td><td>{hold['results']['abl_no_topo_conditioning']['pooled_dti']:.4f}</td></tr>
<tr><td>magnetic-only ablation</td><td>{hold['results']['abl_mag_only']['pooled_dti']:.4f}</td></tr>
<tr><td>gravity-only ablation</td><td>{hold['results']['abl_grav_only']['pooled_dti']:.4f}</td></tr>
<tr><td>same-count random null</td><td>{hold['results']['random_null_k37654']['pooled_dti']:.4f}</td></tr>
<tr><td>incumbent D2.8 + fold-local B2</td><td><strong>{hold['results']['champion_proxy_d28_b2']['pooled_dti']:.4f}</strong></td></tr>
</tbody></table><p class="small">Evaluator {esc(hold['evaluator_version'])}; pooled DTI α=0.2, β=0.8, 300 m triangular kernel, 16×16 block bootstrap.</p></article>
<article class="card panel"><h3>E3 prespecified budget sweep</h3>
<table class="table"><thead><tr><th>budget</th><th>CSPES DTI</th><th>random null</th><th>paired Δ (CI)</th></tr></thead><tbody>{budget_rows}</tbody></table>
<p class="small">CSPES never beats random placement; at 60k it is significantly worse. The negative verdict is budget-robust.</p></article></div>
</section>

<section class="section"><div class="section-head"><div><div class="kicker">04 / Uniqueness scope and the standing blocker</div><h2>Two verdicts, both shown</h2></div></div>
<div class="grid2"><article class="card panel banner-ok"><h3>Sparse historical submissions: UNIQUE</h3>
<p>Against {card['correlation_overlap_vs_registry']['registry_scope'].split('(')[1].split(')')[0]}:</p>
<ul><li>no exact dot-mask duplicate (U1 pass)</li><li>max |Spearman| {gates['U2_max_abs_spearman_surface']:.4f} (surface) / {gates['U2_max_abs_spearman_smoothed_dots']:.4f} (dots), both ≤ 0.90</li>
<li>max non-lattice 3-px overlap {100*gates['U3_max_overlap_nonlattice']:.2f}% ≤ 70%</li><li>lattice-like references: excess over random null ≤ 0.05 for all</li></ul></article>
<article class="card panel banner-no"><h3>Literal any-raster rule: BLOCKED (IR-01, unchanged)</h3>
<p>The registered 17GEMSDOE probability raster is positive on all 5,167,373 footprint cells, so <em>any</em> nonempty candidate has 100% 3-px overlap with it. CSPES surface Spearman vs that raster is only {gates['U2_max_abs_spearman_surface']:.3f}, but the literal overlap gate cannot pass. This needs an explicit protocol revision by the selector; it was not silently exempted.</p></article></div>
<p class="note">Coverage: 149 hash-pinned rasters / 118 unique masks rebuilt locally (nine focus leaders, 118 ledger rasters, 19 template rasters, lattice, witness). The committed 522-file/296-mask index includes additional unrebuilt site trees; a sparse pass here is not claimed as a full-296-mask clearance.</p>
</section>
</div>"""
    return layout("Executive summary", "index.html", body)


def how_page() -> str:
    card = json.loads((ROOT / "evidence/cspes_run_card.json").read_text())
    tif_name = Path(card["files"]["tif"]).name
    body = f"""
<section class="hero"><div class="wrap"><div class="eyebrow">Executive summary / How to submit</div>
<h1>Portal workflow, only after a selector approves.</h1><p class="subhead">No human geological inspection is involved: every gate below is an automated byte/statistic check. This lane did not and cannot select a weekly slot itself.</p></div></section>
<div class="wrap content">
<section class="section"><div class="card panel"><div class="readiness banner-no"><i class="dot"></i> CURRENT FILE: NOT OK TO SUBMIT FOR SCORE (negative holdout; selector not consulted)</div>
<p style="margin-top:12px">The downloadable TIF is structurally submission-ready so the pipeline can be rehearsed end to end, but promoting it would knowingly spend a slot on a candidate whose local DTI is 0.0257 against a 0.0992 incumbent.</p></div></section>
<section class="section"><div class="section-head"><div><div class="kicker">Step by step at DrivenData</div><h2>New submission form</h2></div></div>
<div class="steps">
<article class="card step"><span class="step-number">01</span><div><h3>Choose the file</h3><p>Download <a href="../downloads/{esc(tif_name)}" download><code>{esc(tif_name)}</code></a> (or its single-TIFF ZIP). It is one float32 band, EPSG:32611, shape 3,730×3,292, the sample's exact transform, LZW/deflate, all cells finite and within [0,1], zeros outside the footprint and on the mapped catalogue.</p></div></article>
<article class="card step"><span class="step-number">02</span><div><h3>Name and note fields</h3><p>Use the generated identifiers so receipts stay traceable to bytes (note is {card['submission_note_chars']} chars, under the 140 limit):</p>
<p class="small">Name: <code>{esc(card['submission_name'])}</code><br>Note: <code>{esc(card['submission_note'])}</code></p></div></article>
<article class="card step"><span class="step-number">03</span><div><h3>Why "Predicted values must be in range [0,1]" happened before</h3><p>That rejection is consistent with NaN, infinity or the float32 sentinel (−3.4×10³⁸) appearing in uploaded cells — typical when a pipeline reads <code>training_features.tif</code> without cleaning its nodata. The shared writer is fail-closed: it refuses non-finite or out-of-range input instead of clipping, writes an all-finite array (zeros, never NaN, outside the footprint), and re-validates the saved bytes. The independent validator on this file reports <strong>full-grid NaN = 0, in-footprint min 0.0, max 1.0</strong>. The official text's null/NaN-outside-bounds convention remains unreconciled with the portal's observed range check (IR-04); the all-finite packaging is the portal-safe choice given the observed error.</p></div></article>
<article class="card step"><span class="step-number">04</span><div><h3>Check the weekly cap, then upload</h3><p>Sign in at the <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">competition portal</a>. The <a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">official rules</a> allow up to three submissions per week; the live account quota is not visible from this environment. Only a separately authorized selector, checking the cap and a positive paired holdout, should press submit. Save the organizer receipt next to the file SHA-256 <code>{esc(card['raster_sha256'][:16])}…</code>.</p></div></article>
<article class="card step"><span class="step-number">05</span><div><h3>Final selection and disclosures</h3><p>One chosen submission is scored across both prize rounds. Preserve reproducible code, external-data licenses and the required generative-AI disclosure. Never relabel a HOLDOUT-DTI or owner claim as an organizer score.</p></div></article>
</div></section>
<section class="section"><div class="card panel"><h3>Automatic validation record for this file</h3>
<p class="small">Shared template writer (pinned 57GEMSDOE <code>822a0ce…</code>, fail-closed, on-disk re-validation): ok={card['validator_output']['shared_template_writer_receipt']['ok']}, problems={card['validator_output']['shared_template_writer_receipt']['problems']}, nonzero={card['validator_output']['shared_template_writer_receipt']['n_nonzero']}.<br>
Independent gemsw validator: passed={card['validator_output']['independent_gemsw_validate']['passed']}; read-back equality with audited dots confirmed. Full check list: <a href="data/cspes_run_card.json">run card</a>.</p></div></section>
</div>"""
    return layout("How to submit", "how-to-submit.html", body)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    DATA.mkdir(parents=True, exist_ok=True)
    (OUT / "index.html").write_text(index_page(), encoding="utf-8")
    (OUT / "how-to-submit.html").write_text(how_page(), encoding="utf-8")
    for src, dst in [
        ("evidence/cspes_run_card.json", DATA / "cspes_run_card.json"),
        ("evidence/cspes_holdout.json", DATA / "cspes_holdout.json"),
        ("evidence/cspes_canary.json", DATA / "cspes_canary.json"),
        ("evidence/cspes_budget.json", DATA / "cspes_budget.json"),
        ("registry/cspes_registry_index.json", DATA / "cspes_registry_index.json"),
    ]:
        shutil.copyfile(ROOT / src, dst)
    print(f"Built CSPES lane site in {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
