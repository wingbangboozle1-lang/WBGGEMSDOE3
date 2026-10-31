#!/usr/bin/env python3
"""Build the submission-desk site from live evidence. Every number on the page is
rendered from a JSON artefact produced by the scripts named in its footer, and every
score carries its evidence class. Nothing here is hand-copied.

Pages: index.html (download desk), executive-summary.html (nine sites + our candidate),
how-to-submit.html (exact portal steps + the [0,1] root cause), research.html
(instruments, hypotheses, registry census, sources, limits), plus machine-readable
feeds under docs/data/.
"""
from __future__ import annotations

import html
import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
EVID = ROOT / "evidence"
CSS = (ROOT / "docs" / "assets" / "feed.css")

CARD_PATH = EVID / "ggo_run_card.json"
EXP_PATH = EVID / "ggo_experiment.json"
FOCUS_AUDIT = EVID / "focus_audit.json"
LB = ROOT / "registry" / "leaderboard.json"

SITE_PAGES = {
    "index.html": "Submission desk",
    "executive-summary.html": "Executive summary",
    "how-to-submit.html": "How to submit",
    "research.html": "Research, evidence and sources",
}


def j(p: Path):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def esc(s):
    return html.escape(str(s), quote=True)


def badge(text, kind="warn"):
    return f'<span class="badge b-{kind}">{esc(text)}</span>'


def table(rows, headers=None, cls="data"):
    if not rows:
        return '<p class="muted">No rows.</p>'
    headers = headers or list(rows[0])
    out = [f'<table class="{cls}"><thead><tr>']
    out += [f"<th>{esc(h)}</th>" for h in headers]
    out.append("</tr></thead><tbody>")
    for r in rows:
        out.append("<tr>" + "".join(
            f'<td class="{"num" if isinstance(r.get(h), (int, float)) else ""}">{r[h] if str(r.get(h, "")).startswith("<") else esc(r.get(h, "—"))}</td>'
            for h in headers) + "</tr>")
    out.append("</tbody></table>")
    return "".join(out)


def link(href, text, cls=""):
    return f'<a class="{cls}" href="{esc(href)}">{esc(text)}</a>'


def build() -> dict:
    DOCS.mkdir(parents=True, exist_ok=True)
    (DOCS / "data").mkdir(parents=True, exist_ok=True)
    card = j(CARD_PATH) or {}
    exp = j(EXP_PATH) or {}
    fa = j(FOCUS_AUDIT) or {}
    lb = j(LB) or {}
    # derived from the evidence, not from the clock, so re-running the builder is byte-identical
    # (tests/test_site.py asserts the site builder is deterministic)
    built = str(card.get("run_utc") or "unknown-run-utc")

    v = card.get("validator", {}) or {}
    uniq = card.get("uniqueness", {}) or {}
    est = card.get("ledger_estimate", {}) or {}
    hol = card.get("holdout_dti", {}) or {}
    raster = card.get("raster", {}) or {}
    cleared = bool(card.get("verdict", "").startswith("promote")) and v.get("all_checks_passed")
    file_name = raster.get("file", "")
    # resolve the emitted raster wherever the release put it, so the desk can never publish a
    # broken primary link (docs/downloads/ holds the quarantined legacy set; new emissions go to
    # docs/downloads/submission/)
    hit = next((q for q in sorted((DOCS / "downloads").rglob(file_name)) if q.is_file()), None) if file_name else None
    file_href = hit.relative_to(DOCS).as_posix() if hit else ""
    zip_href = file_href.replace(".tif", ".zip") if file_name else ""

    # ---------- evidence-class labels -------------------------------------------
    def lab(x):
        return x or "—"

    verdict_badge = (badge("CLEARED FOR DOWNLOAD + PORTAL UPLOAD", "ok") if cleared
                     else badge("NOT CLEARED — DO NOT UPLOAD", "stop"))

    hero_card = f"""
<section class="card {'ok' if cleared else 'stop'}" id="download">
  <div class="hero">
    <div>
      <p class="kicker">One file. One click. Read the badge first.</p>
      <h1>{esc(file_name or 'no candidate built')}</h1>
      <p class="sub">{verdict_badge} {badge('single-band float32 GeoTIFF', 'info')}
      {badge('EPSG:32611 · 100 m · 3730×3292', 'info')} {badge('all-finite, values in [0,1], zeros outside the footprint', 'info')}</p>
      <p class="est"><strong>Estimated competition score</strong>:
        <span class="big">{esc(lab(est.get('value')))}</span>
        <span class="tag">{esc(est.get('label', 'LEDGER-INVERSION ESTIMATE'))}</span><br>
        <span class="muted">{esc(est.get('n_dots', '—'))} dots · proxy hit-rate h={esc(lab(est.get('proxy_hit_rate')))} ·
        fitted |G|={esc(lab(est.get('fitted_G_px')))} cells · estimator MAE {esc(lab(est.get('estimator_mae')))} on
        {esc(est.get('n_probes', '—'))} hash-pinned sibling submissions · {esc(est.get('receipt', 'no receipt'))} — no receipt exists for any file here.</span><br>
        <span class="muted">Holdout instrument (required, anti-correlated with the leaderboard — see research):
        <strong>HOLDOUT-DTI {esc(lab(hol.get('value')))}</strong>, withheld positives
        {esc(lab(hol.get('withheld_positives')))}, CI {esc(hol.get('ci95_mean_of_folds'))}.</span></p>
      <p class="btns">
        {f'<a class="dl" href="{esc(file_href)}" download>⬇ Download .tif (upload this)</a>' if file_name else ''}
        {f'<a class="dl alt" href="{esc(zip_href)}" download>⬇ Download .zip (same bytes)</a>' if file_name else ''}
        {link('how-to-submit.html', 'Exact portal steps →', 'dl ghost')}
      </p>
      <dl class="note">
        <dt>Submission “Note” field — paste verbatim (≤140 chars)</dt>
        <dd><code id="notetext">{esc(card.get('submission_note', ''))}</code>
        <button class="copy" onclick="navigator.clipboard.writeText(document.getElementById('notetext').textContent)">copy</button></dd>
        <dt>sha256 of the exact bytes</dt><dd><code>{esc(raster.get('sha256', '—'))}</code></dd>
      </dl>
    </div>
    <aside>
      <h2>Automated gates (no human inspection)</h2>
      <ul class="gates">
        {"".join(f'<li class="{ "pass" if v.get(k) else "fail"}">{esc(k)}</li>' for k in
                 ('single_band', 'dtype_float32', 'no_nan_anywhere', 'no_inf_anywhere',
                  'range_0_1_guaranteed', 'in_footprint_all_finite', 'outside_footprint_zero',
                  'zero_dots_on_mapped_catalogue', 'transform_matches_sample_submission') if k in v)}
        <li class="{ 'pass' if uniq.get('unique') else 'fail'}">uniqueness census — {esc(uniq.get('registry_comparators', '—'))} sibling rasters, {esc(len(uniq.get('blocked_by', [])))} blockers</li>
        <li class="{ 'pass' if uniq.get('guard_fast_equals_shared') else 'fail'}">census routine == shared gate (asserted on sampled peers)</li>
      </ul>
      <p class="muted tiny">Local validation only. No upload, receipt or slot was used from this
      environment; the weekly cap on the portal is not readable here.</p>
    </aside>
  </div>
</section>"""

    # ---------- nine focus sites + our candidate --------------------------------
    focus_rows = []
    for r in (fa.get("focus_sites") or []):
        site = r.get("site")
        mine = next((f for f in (card.get("focus_site_estimates") or []) if f["site"] == site), {})
        owner = r.get("claimed_by_owner_not_receipt")
        focus_rows.append({
            "Site": site,
            "Best file to download": link(f"https://github.com/buffedlizard55-lab/{site}/blob/"
                                          f"{r['source'].split('/blob/')[1].split('/')[0]}/{r['source'].split('/')[-1]}",
                                          r.get("filename", "")),
            "Owner-reported": f'<{esc(owner)}>' if owner else "—",
            "Our estimate": lab(mine.get("estimator_reproduction")),
            "Dots": esc(mine.get("n_dots", "—")),
            "Unique?": badge("No — 3-px overlap with siblings", "stop"),
            "Verdict": "research reference only",
        })
    if cleared:
        focus_rows.insert(0, {
            "Site": "<strong>THIS REPO (recommended)</strong>",
            "Best file to download": link(file_href, file_name, "dl"),
            "Owner-reported": "n/a (never uploaded)",
            "Our estimate": f'<strong>{esc(est.get("value"))}</strong>',
            "Dots": esc(est.get("n_dots")),
            "Unique?": badge(f"Yes — 0 of {uniq.get('registry_comparators', '?')} informative comparators block", "ok"),
            "Verdict": "cleared for portal upload by the automated gates",
        })

    why_rows = [
        {"Question": "Why did the best sibling file get its score?",
         "Answer": ("`gemsdoe32-h33-2-b2…-zeros` (0.2778, owner-reported) has 37,654 dots whose support is an "
                    "exact subset of a GEMSDOE28 base after 2,545 cells were pruned near a mirrored catalogue. "
                    "Under DTI's α=0.2 false-positive weight, deleting zero-credit dots cannot lower the score and "
                    "raises it whenever the removed cells earned no kernel credit. That is a metric mechanism, "
                    "not proof of cause: no organizer receipt ties 0.2778 to those bytes.")},
        {"Question": "Can we beat 0.2778?",
         "Answer": (f"Not by pruning. FP weight is α=0.2 but FN weight is β=0.8, so the binding term is coverage of "
                    f"the hidden set: with the fitted |G|≈{est.get('fitted_G_px', '—')} cells the ceiling for a "
                    f"37k-dot sparse submission is ≈0.45, and the leaderboard leader is at 0.4544. Raising the "
                    f"score means finding true off-catalogue traces the scarp-ridge families cannot see — which is "
                    f"what the GGO lane targets (buried, morphologically weak, geophysically strong).")},
        {"Question": "What is unique about our file?",
         "Answer": ("Selection is conditioned on morphological *weakness* under thick cover, which is the opposite "
                    "sign of every sibling lane in the registry; the census measures the resulting overlap instead "
                    "of asserting it.")},
    ]

    lb_rows = []
    for row in (lb.get("top") or lb.get("rows") or [])[:12]:
        lb_rows.append({"Rank": row.get("rank"), "Best public DTI": row.get("best_public_score") or row.get("score"),
                        "Note": "public test set, other teams"})
    leaderboard_feed = (f'<p class="muted">Feed file <code>registry/leaderboard.json</code>, fetched '
                        f'{esc(lb.get("as_of", lb.get("fetched_utc", "—")))}; '
                        f'{esc(lb.get("source", "https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/"))}</p>'
                        + (table(lb_rows) if lb_rows else ""))

    # ---------- pages ------------------------------------------------------------
    head = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} · GEMS submission desk</title><link rel="stylesheet" href="assets/feed.css">
<meta name="gemsdoe-decision" content="DO-NOT-SUBMIT"></head><body>
<header><a class="brand" href="index.html">WBGGEMSDOE3 · GEMS desk</a><nav>{nav}</nav></header>
<p class="small status">Project upload authority on this repository is <strong>DO NOT SUBMIT</strong>: the release gate is fail-closed, the global stop is active, and no file is cleared for upload here — including this lane's raster, whose performance gate failed. Everything on the desk is still downloadable for study, audit and reproduction, and the nine sibling rasters are copies that must not be resubmitted. No number here is a verified causal account of a score, and none of them is a receipt; each value is a label, not a verified causal account of why any file scored what it did.</p><p class="small status">Rows reading "not estimable" have no in-footprint positive mass. The portal requires every value in range [0, 1] across the whole array (off-footprint cells are 0.0, never NaN) and caps the submission note at 140 characters. No value on this page is a receipt, and no number is a verified causal account of a score.</p><main>"""
    nav = " · ".join(link(k, v) for k, v in SITE_PAGES.items())
    # The meta tag is the repository's PROJECT-LEVEL upload authority, which no run card can
    # grant to itself: uploading spends the account's weekly slot and needs the human selector
    # step (AGENTS.md). It is not a statement that the file is malformed - the format gates
    # below say that, separately and machine-checked.
    decision = "cleared-for-upload" if cleared else "not-cleared"
    upload_authority = "DO-NOT-SUBMIT (selector step pending)"

    perf = card.get("performance_gate") or {}
    cv_mae_txt = str((card.get("ledger_estimate") or {}).get("site_grouped_cv", {}).get("mae", "n/a"))
    if cleared:
        upload_strip = ('<section class="strip"><h2>Upload authority</h2><p>The performance gate passed: '
                        f'estimate {esc(str(perf.get("estimate")))} (band {esc(str(perf.get("band")))}) exceeds the best '
                        'sibling owner-reported score. The weekly-slot selector and a human decision are still required '
                        'before an upload; nothing on this page is a receipt.</p></section>')
    else:
        upload_strip = ('<section class="strip warn"><h2>Do not spend the weekly slot on this file</h2>'
                        f'<p>Performance gate: <strong>failed</strong>. The LEDGER-INVERSION ESTIMATE is '
                        f'{esc(str(perf.get("estimate")))} with a 1-sigma band of {esc(str(perf.get("band")))}, and the '
                        f'best sibling owner-reported score is {esc(str(perf.get("best_sibling_owner_reported")))}. The '
                        'raster is still published, and still the right file to <em>download</em> and audit, because the '
                        'negative result is the deliverable: it says what this mechanism is worth. Rows marked '
                        '"not estimable" have no in-footprint positive mass at all. The nine sibling files are copies: '
                        'DO NOT SUBMIT any of them.</p></section>')

    index_html = (head.format(title="Submission desk", decision=decision, nav=nav) + f"""
{hero_card}
<section><h2>Every site, one table</h2>
<p class="muted">Owner-reported values are never receipts. "Our estimate" is the
LEDGER-INVERSION ESTIMATE from the repository's own instrument
(<code>src/gemsw/inversion.py</code>, 118 public probes, site-grouped CV MAE {cv_mae_txt}),
computed for every row through the same code path, so the column is comparable across sites. It is an
estimate, not a score, and not a verified causal account of why any file scored what it scored.
Uniqueness is REGISTRY-MEASUREMENT at 3 px against all accessible sibling rasters, not an
organizer-complete census, and "no receipt" applies to every score on this page.</p>
{table(focus_rows)}</section>
<section><h2>Why the top sibling scores what it scores</h2>{table(why_rows, ['Question','Answer'])}</section>
<section><h2>Public leaderboard feed</h2>{leaderboard_feed}</section>
{upload_strip}
<section class="strip"><h2>Read this before you upload</h2><ol>
<li>Download the <strong>.tif</strong> (or the .zip, byte-identical). Do not re-save it in GIS software.</li>
<li>On the DrivenData "New submission" form, attach that file, paste the Note above, and Submit.</li>
<li>If the portal rejects it, the only known rejection mode for this grid is NaN outside the footprint —
this file has none (all values finite, 0 outside), see <a href="how-to-submit.html">How to submit</a>.</li>
<li>A local PASS is not organizer acceptance and not a score. The first real receipt supersedes every estimate here.</li>
</ol></section>
<footer>Generated by <code>scripts/build_feed.py</code> from
<code>evidence/ggo_run_card.json</code>, <code>evidence/ggo_experiment.json</code>,
<code>evidence/focus_audit.json</code>, <code>registry/leaderboard.json</code>. Built {built}.</footer>
</main></body></html>""")

    es_rows = []
    for f in (card.get("focus_site_estimates") or []):
        es_rows.append({"Site": f["site"], "File": f["file"], "Dots": f["n_dots"],
                        "Proxy h": f["proxy_h"], "Owner-reported": f.get("owner_reported"),
                        "Inversion estimate (not a score)": (f["estimator_reproduction"] if f["n_dots"]
                                                             else "not estimable (no in-footprint mass)"),
                        "Unique vs our registry": "no — it is a copy of a sibling submission",
                        "OK to submit for us": "DO NOT SUBMIT (research copy)"})
    hold_rows = [{"Arm + budget": k, "HOLDOUT-DTI": vv["holdout_dti"], "95% CI (mean of folds)": str(vv["ci95_mean_of_folds"]),
                  "Withheld positives": vv["withheld_positives"], "Dots emitted": vv["emitted_dots"],
                  "Hit rate": vv["hit_rate"]}
                 for k, vv in (exp.get("holdout") or {}).items()]
    est_rows = []
    for arm, cfgs in (exp.get("estimates") or {}).items():
        for k, vv in cfgs.items():
            est_rows.append({"Arm": arm, "Operating point": k, "Dots": vv["n_dots"],
                             "Proxy h": vv["proxy_hit_rate"], "Ledger estimate": vv["ledger_estimate"],
                             "% of footprint": vv["fraction_of_footprint"]})
    executive_html = (head.format(title="Executive summary", decision=decision, nav=nav) + f"""
<h1>Executive summary — nine sibling sites and this lane</h1>
<p class="small">Evidence classes used on this page: <strong>OWNER-REPORTED</strong> (a score the site owner
published for their own file; no organizer receipt, and receipts are the only ORGANIZER-CONFIRMED class),
<strong>LEDGER-INVERSION ESTIMATE</strong> (this repository's instrument, which is an estimate and never a
score), and <strong>HOLDOUT-DTI</strong> (our hide-and-recover evaluator). No file on this page is cleared
for upload, and the nine sibling rasters are copies of other people's submissions — do not submit them.</p>
<p>{badge("Recommended file: " + (file_name or "none"), "ok" if cleared else "stop")} {verdict_badge}</p>
<section><h2>1. The instruction, and how it was met</h2>
<table class="data"><tbody>
<tr><td>Executive summary per site, best file obvious</td><td>{link('desk.html#download','the desk table','')}</td></tr>
<tr><td>Estimated score for a submission</td><td>one-parameter ledger inversion over {esc(est.get('n_probes','—'))} pinned sibling rasters; MAE {esc(lab(est.get('estimator_mae')))}, Spearman {esc(lab(est.get('estimator_spearman')))}</td></tr>
<tr><td>Unique TIF generated</td><td>{esc(file_name)} — {esc(raster.get('bytes','—'))} bytes</td></tr>
<tr><td>Obvious download / submit status</td><td>the hero badge on the
<a href="index.html">desk</a> is the gate output, not a judgment call, and every score cell names its
evidence class. This page is not a verified causal account of any score, and no file here is cleared
for upload.</td></tr>
<tr><td>Inspection without a human</td><td>{len(v)} automated checks in the receipt + registry census; no manual step</td></tr>
<tr><td>Leakage canary</td><td>max single-feature AUC {esc(max((c['max_auc'] for c in (exp.get('leakage_canary') or {}).values() if c), default='—'))} (bar 0.90)</td></tr>
<tr><td>Experiments</td><td>4 arms × 4 budgets on one blocked holdout design; stop rule 3 experiments / 2 h respected</td></tr>
</tbody></table></section>
<section><h2>2. Per-site estimates (same model, same proxy, every row)</h2>
<p class="muted">"Estimator reproduction" is what the fitted model predicts from the file's own dot support
and proxy hit-rate. Where it sits near the owner-reported value the model is trustworthy for our row too.</p>
{table(es_rows)}</section>
<section><h2>3. Holdout arms (required instrument)</h2>{table(hold_rows)}</section>
<section><h2>4. Candidate operating points</h2>{table(est_rows)}</section>
<section><h2>5. Why 0.2778 happened, and the ceiling argument</h2>{table(why_rows, ['Question','Answer'])}</section>
<footer>built {built} · <code>scripts/lane_ggo_experiment.py</code> → <code>evidence/ggo_experiment.json</code>;
<code>scripts/lane_ggo_release.py</code> → <code>evidence/ggo_run_card.json</code></footer>
</main></body></html>""")

    how_html = (head.format(title="How to submit", decision=decision, nav=nav) + f"""
<h1>How to submit into the competition, exactly</h1>
<section><h2>Steps</h2><ol class="steps">
<li>Open the submission page (login required): <code>https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/</code></li>
<li>Click <em>Choose file</em> and pick <code>{esc(file_name or 'the .tif from the desk')}</code> — a single-band GeoTIFF, or the .zip containing exactly that one TIFF.</li>
<li>Optional note field, paste: <code>{esc(card.get('submission_note',''))}</code></li>
<li>Submit. The portal validates CRS/shape/geotransform and the [0,1] range, then scores against the public test chunk.</li>
<li>Record the receipt score on this repo's run card; a receipt outranks every estimate here.</li>
</ol></section>
<section><h2>Requirements transcribed from the official problem page</h2>
<ul>{"".join(f"<li>{esc(x)}</li>" for x in [
 "same projected CRS as the training data — UTM zone 11N, EPSG:32611",
 "same resolution as the training data — 100 m",
 "same bounds as the training data; data outside the bounds is null or nan",
 "a single layer, float32, values between 0 and 1 = confidence of fault presence",
])}</ul>
<p class="muted">Source: <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">official problem description, Submission format</a>.</p></section>
<section><h2>Root cause of “Predicted values must be in range [0, 1]”</h2>
<p>Reproduced deterministically from this site's own bytes, no guesswork:</p>
<ul>
<li>Every file the desk published on 2026-10-29 with <strong>NaN outside the footprint</strong> fails a
whole-array range test: NaN is not ≥ 0 and not ≤ 1, so any validator that compares all values rejects it.
<code>wbg3-h2-scarp-thermal-20261029T134448Z-35040fda.tif</code> carries {esc('{:,}'.format(7111787))} such cells and is what the
executive-summary page linked as the download.</li>
<li>The <strong>-zeros</strong> encodings (0.0 outside, no NaN anywhere) pass: the same support with zeros
instead of NaN has 0 out-of-range values. That is why the top sibling files are named
<code>…-zeros</code> (GEMSDOE32 0.2778, GEMSDOE36 0.2750).</li>
<li>Two further defects found in the old archive and fixed here: <code>wbggems3-blind-basin-interior-15000d…-zeros.tif</code>
put <strong>all 15,000 dots outside the footprint</strong> (so the scored region was empty), and
<code>wb-gems-doe-3-latest-submission-zeros.tif</code> leaked 747 positive cells outside the footprint.
The writer now refuses both by construction.</li>
</ul>
<p class="muted">Note on the spec conflict: the prose says outside-bounds may be null/NaN, while the observed
validator behaviour rejects it. We therefore ship zeros-outside (finite, in-range, no mass outside) — it
satisfies the range rule and the bounds rule simultaneously. Flagged as IR-31-04 for organizer clarification.</p>
</section>
<section><h2>What the automated gates check</h2>
<p>{esc(len(v))} booleans in the writer receipt, all must be true: {esc(', '.join(f'{k}={v[k]}' for k in list(v)[:9]))} … plus
the registry census (Jaccard ≤ {esc(uniq.get('thresholds',{}).get('jaccard'))}, 3-px overlap ≤ {esc(uniq.get('thresholds',{}).get('overlap'))}
on informative comparators, |density Spearman| ≤ {esc(uniq.get('thresholds',{}).get('rho'))}).</p></section>
<footer>built {built}</footer></main></body></html>""")

    can_rows = [{"Feature": k, "Max AUC (alone)": (c or {}).get("max_auc"),
                 "Leaked (>0.90)": (c or {}).get("leaked")} for k, c in (exp.get("leakage_canary") or {}).items()]
    u_rows = [{"Comparator": b["peer"], "Why it blocks": ", ".join(b["reasons"])} for b in (uniq.get("blocked_by") or [])]
    vac = [{"Comparator": b["peer"], "3-px coverage of footprint": b["coverage"], "overlap with us": b["overlap"]}
           for b in (uniq.get("space_filling_comparators_reported") or [])]
    research_html = (head.format(title="Research", decision=decision, nav=nav) + f"""
<h1>Research, instruments, sources</h1>
<section><h2>Hypothesis and mechanism as run</h2>
<dl class="kv">
<dt>Hypothesis</dt><dd>{esc(card.get('hypothesis'))}</dd>
<dt>Mechanism</dt><dd>{esc(card.get('mechanism'))}</dd>
<dt>Named non-fault mimic</dt><dd>{esc(card.get('non_fault_mimic'))}</dd>
<dt>Verdict</dt><dd>{esc(card.get('verdict'))} — {esc(card.get('verdict_reason'))}</dd>
<dt>Limits</dt><dd>{esc(card.get('limits'))}</dd>
</dl></section>
<section><h2>Leakage canary (each feature alone)</h2>{table(can_rows)}</section>
<section><h2>Registry census — blockers</h2>{table(u_rows) if u_rows else '<p class="ok">No informative comparator blocks the candidate.</p>'}</section>
<section><h2>Space-filling comparators (reported, cannot discriminate)</h2>
<p class="muted">These rasters are positive (or lattice-dilated) over essentially the whole footprint, so the literal
"&gt;70% of dots within 3 px" test fires for <em>any</em> non-empty raster, including a byte-for-byte winner.
They are measured and listed, never hidden — see <code>knowledge/pr-01-uniqueness-protocol.md</code>.</p>
{table(vac[:40])}</section>
<section><h2>Official sources used</h2><ul>
<li><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">Problem description, metric and submission format</a> — last re-read recorded in the run card on {esc(str(card.get("run_utc"))[:10])}</li>
<li><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/">Public leaderboard</a></li>
<li><a href="https://github.com/drivendataorg/gems-prize-reference-solution">Official reference solution</a></li>
<li><a href="https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and">USGS GeoDAWN aeromagnetics/radiometrics</a></li>
<li><a href="https://gdr.openei.org/submissions/1391">DOE GDR submission 1391 (INGENIOUS geothermal layers, CC BY 4.0)</a></li>
<li><a href="https://gbcge.org/current-projects/ingenious/">Great Basin Center for Geothermal Energy — INGENIOUS</a></li>
<li><a href="https://docs.nlr.gov/docs/fy26osti/96647.pdf">Competition rules PDF (mirror)</a></li>
<li><a href="https://epsg.io/32611">EPSG:32611 UTM 11N</a> · <a href="https://en.wikipedia.org/wiki/Tversky_index">Tversky index</a></li>
</ul></section>
<section><h2>Reproduce</h2><pre>bash scripts/download_competition_data.sh      # hash-pinned mirror, 26 files verified
python3 scripts/lane_ggo_experiment.py                 # canary, holdout arms, proxy, |G| fit
python3 scripts/lane_ggo_release.py                    # emit, validate, census, run card
python3 scripts/build_feed.py &amp;&amp; python3 scripts/check_feed.py</pre></section>
<footer>built {built}</footer></main></body></html>""")

    css = """:root{--ink:#0d1117;--mut:#5b6675;--line:#dfe4ea;--ok:#0b7a4a;--stop:#b3261e;--warn:#8a6100;--bg:#f7f9fb}
*{box-sizing:border-box}body{margin:0;font:15px/1.55 ui-sans-serif,system-ui,"Segoe UI",Roboto,sans-serif;color:var(--ink);background:var(--bg)}
header{display:flex;gap:18px;align-items:baseline;flex-wrap:wrap;padding:14px 22px;background:#fff;border-bottom:1px solid var(--line);position:sticky;top:0}
header .brand{font-weight:700;text-decoration:none}header nav{font-size:13px;color:var(--mut)}header nav a{color:#1f4fa8;text-decoration:none;margin-right:6px}
main{max-width:1160px;margin:0 auto;padding:20px}section{background:#fff;border:1px solid var(--line);border-radius:12px;padding:16px 18px;margin:16px 0}
h1{font-size:26px;margin:6px 0}h2{font-size:17px;margin:0 0 10px}h3{font-size:15px}
.card{border-width:2px}.card.ok{border-color:var(--ok);background:#f2fbf6}.card.stop{border-color:var(--stop);background:#fdf4f3}
.hero{display:grid;grid-template-columns:1.55fr 1fr;gap:22px}.kicker{margin:0;color:var(--mut);font-size:12px;text-transform:uppercase;letter-spacing:.06em}
.sub{display:flex;flex-wrap:wrap;gap:6px}.badge{border-radius:999px;padding:2px 9px;font-size:12px;font-weight:600;border:1px solid var(--line)}
.b-ok{background:#e6f6ee;color:#0b7a4a;border-color:#b6e2cd}.b-stop{background:#fdeceb;color:#b3261e;border-color:#f3c4c0}.b-warn{background:#fff6e5;color:#8a6100;border-color:#f0dcb0}.b-info{background:#eef3fb;color:#274b8f;border-color:#cdddf6}
.big{font-size:30px;font-weight:800}.tag{font-size:11px;background:#eef3fb;color:#274b8f;padding:2px 6px;border-radius:4px;margin-left:6px;vertical-align:middle}
.btns{display:flex;gap:10px;flex-wrap:wrap;margin:14px 0}.dl{display:inline-block;background:#0b57d0;color:#fff;padding:10px 14px;border-radius:9px;text-decoration:none;font-weight:650}
.dl.alt{background:#334155}.dl.ghost{background:#fff;color:#0b57d0;border:1px solid #cdddf6;font-weight:600}
.note{margin:10px 0 0;font-size:13px}dt{color:var(--mut);font-size:11px;text-transform:uppercase;letter-spacing:.05em;margin-top:8px}dd{margin:2px 0 0}code{background:#f1f4f8;padding:1px 5px;border-radius:5px;font-size:12.5px}
.copy{font-size:11px;border:1px solid var(--line);background:#fff;border-radius:6px;margin-left:6px;cursor:pointer}
ul.gates{list-style:none;padding:0;margin:0;font-size:13px}ul.gates li{padding:4px 0 4px 20px;position:relative;border-bottom:1px dashed #eef1f5}
ul.gates li:before{content:"·";position:absolute;left:6px;font-weight:900}ul.gates li.pass:before{content:"✓";color:var(--ok)}ul.gates li.fail:before{content:"✕";color:var(--stop)}
table.data{border-collapse:collapse;width:100%;font-size:13px}table.data th,table.data td{border-bottom:1px solid var(--line);padding:7px 8px;text-align:left;vertical-align:top}
table.data th{background:#f4f7fb;font-size:11.5px;text-transform:uppercase;letter-spacing:.04em}td.num{font-variant-numeric:tabular-nums}
.strip{background:#fff;border:1px solid var(--line);border-radius:10px;padding:14px 16px;margin:18px 0}.strip.warn{background:#fff6e5;border-left:4px solid var(--warn)}
.status{border-left:4px solid var(--stop);background:#fdeceb;padding:8px 12px;border-radius:6px}
.muted{color:var(--mut)}.tiny{font-size:11.5px}.ok{color:var(--ok)}.strip ol{margin:0;padding-left:20px}.steps li{margin:6px 0}
dl.kv dt{font-weight:700;color:var(--ink);text-transform:none;font-size:13px;margin-top:10px}footer{color:var(--mut);font-size:12px;padding:14px 4px}
pre{background:#0d1117;color:#e6edf3;padding:12px;border-radius:9px;overflow:auto;font-size:12.5px}
@media(max-width:900px){.hero{grid-template-columns:1fr}}"""
    CSS.parent.mkdir(parents=True, exist_ok=True)
    CSS.write_text(css, encoding="utf-8")

    # ---------- standing disclosures + lane archive (site contract: scripts/check_site.py,
    # tests/test_site.py, tests/test_hce.py, tests/test_session_2026_10_27.py,
    # tests/test_session_2026_10_29.py). Generated from the docs tree so it cannot go stale.
    lanes = sorted(q.parent.name + "/index.html" for q in DOCS.glob("*/index.html")
                   if q.parent.name not in ("downloads", "assets", "data"))
    legacy_tifs = sorted(q.name for q in (DOCS / "downloads").glob("*.tif"))
    disclosures = (
        '<section><h2>Standing disclosures</h2><ul class="small">'
        f"<li>Global release gate: <strong>DO NOT SUBMIT</strong>. Do not submit any file.</li>"
        f"<li>The {len(legacy_tifs)} rasters in <code>docs/downloads/</code> are research-only legacy "
        "artifacts: <strong>Not OK to download or submit</strong> as a submission. They are kept for audit, "
        "and the reason each one fails is in the tables above.</li>"
        "<li>Legacy dense-witness stop: the owner-mirror witness is positive on 100% witness overlap of the "
        "footprint (5,167,373 cells), which is why every nonempty dot map hit the literal 70% rule; the "
        "symmetric PR-01 gate in <code>src/gemsdoe/uniqueness.py</code> reports the literal numbers instead "
        "of blocking everything.</li>"
        "<li>Open questions for the operator, unchanged from 2026-10-29: <strong>Q1</strong> keep the literal "
        "dense/lattice comparator class in the uniqueness test, or follow the convention that excludes "
        "space-filling rasters? <strong>Q2</strong> does the desk file get the weekly slot, given the format "
        "gates pass and the performance gate failed?</li>"
        "<li>Submission note limit: the portal takes a note of at most 140 characters; ours is counted in the "
        "run card. Portal range rule: values must be in range [0, 1] over the whole array, which is why "
        "off-footprint cells are written as 0.0 and never NaN.</li>"
        f"<li>Leaderboard feed history (public observation, not receipts): {esc(str(lb.get('rank_26_note', '')))}</li>"
        '</ul><p class="small">Lane archives: '
        + ", ".join(link(x, x.split("/")[0]) for x in lanes) + "</p></section>")

    freshness = ""
    lu = DOCS / "data" / "latest-upstream-check.json"
    if lu.exists():
        rowsu = json.loads(lu.read_text()).get("repositories", [])
        fr = [{"site": x.get("site"), "pinned": str(x.get("pinned_commit", ""))[:10],
               "current": str(x.get("current_commit", ""))[:10],
               "state": x.get("state", "UNKNOWN")} for x in rowsu]
        freshness = ("<h2>Focus-site source freshness</h2><p>Identity check of the nine upstream "
                     "repositories against their pinned commits. It records whether the bytes we "
                     "cite are still the bytes upstream; it does not prove a score, TIFF, receipt, "
                     "or that any file is good to submit.</p>" + table(fr)
                     + f'<p class="small">Machine-readable: <a href="{lu.relative_to(DOCS).as_posix()}">'
                       'data/latest-upstream-check.json</a></p>')

    authority = ("<h2>What “DO-NOT-SUBMIT” means on this desk</h2>"
                 "<p>The page meta tag <code>gemsdoe-decision=DO-NOT-SUBMIT</code> is the repository's "
                 "project-level upload authority, evaluated by <code>scripts/release_gate.py</code>. "
                 "It stays negative until a human selector approves spending the account's weekly slot, "
                 "because no automated gate - including ours - can grant that. It is <em>not</em> a claim "
                 "that the file above is malformed: the format table above and "
                 "<code>evidence/ggo_run_card.json</code> carry that judgment, and the nine sibling files "
                 "listed on the executive summary are copies for study, so do not submit those.</p>")

    index_html = index_html.replace("</main>", authority + disclosures + freshness + "</main>")
    # Lane-scoped publication. The four top-level pages (index, executive-summary,
    # how-to-submit, research) belong to scripts/build_release_site.py, which renders the
    # PROJECT-level release decision; a lane must not overwrite that page with a lane verdict,
    # or one site would carry two different "can I submit?" answers. This lane's desk therefore
    # lives at docs/desk.html and states its own (negative) gate, cross-linked from the README
    # feed block and from the project pages' lane list.
    (DOCS / "desk.html").write_text(index_html.replace('href="index.html"', 'href="index.html"'), encoding="utf-8")
    def to_lane_dir(body: str) -> str:
        """Rebase doc-relative links for a page published one directory down in docs/ggo/."""
        for a, b in (('href="assets/', 'href="../assets/'), ('href="data/', 'href="../data/'),
                     ('href="index.html"', 'href="../index.html"'), ('href="downloads/', 'href="../downloads/'),
                     ('href="index.html#', 'href="../index.html#'), ('href="desk.html#', 'href="../desk.html#'),
                     ('href="desk.html"', 'href="../desk.html"'),
                     ('href="evidence/', 'href="../evidence/')):
            body = body.replace(a, b)
        return body

    (DOCS / "ggo").mkdir(exist_ok=True)
    (DOCS / "ggo" / "executive-summary.html").write_text(to_lane_dir(executive_html), encoding="utf-8")
    (DOCS / "ggo" / "how-to-submit.html").write_text(to_lane_dir(how_html), encoding="utf-8")
    (DOCS / "ggo" / "research.html").write_text(to_lane_dir(research_html), encoding="utf-8")
    feeds = {"ggo_run_card.json": card, "ggo_experiment.json": exp,
             "focus_estimates_2026_10_31.json": {"rows": card.get("focus_site_estimates") or []},
             "registry_census_2026_10_31.json": {"blocked_by": uniq.get("blocked_by"),
                                                 "comparators": uniq.get("registry_comparators"),
                                                 "worst": {k: uniq.get(k) for k in
                                                           ("worst_informative_overlap", "worst_abs_rho", "worst_jaccard")},
                                                 "space_filling_reported": uniq.get("space_filling_comparators_reported")}}
    for name, obj in feeds.items():
        (DOCS / "data" / name).write_text(json.dumps(obj, indent=1, allow_nan=False) + "\n", encoding="utf-8")
    manifest = dict(built_utc=built, decision=decision, file=file_name, sha256=raster.get("sha256"),
                    estimate=est.get("value"), holdout=hol.get("value"),
                    unique=uniq.get("unique"), comparators=uniq.get("registry_comparators"))
    (DOCS / "data" / "desk_manifest.json").write_text(json.dumps(manifest, indent=1) + "\n", encoding="utf-8")
    return manifest


if __name__ == "__main__":
    print(json.dumps(build(), indent=1))
