#!/usr/bin/env python3
"""Build the public dashboard from committed, machine-readable evidence.

A lane card is not an upload authorization.  This renderer reads the global
release gate first and will only show a competition-submission action when that
gate passes for the exact candidate SHA-256.
"""
from __future__ import annotations

import hashlib
import html
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
DATA = DOCS / "data"
SUBMISSION = ROOT / "submission"
sys.path.insert(0, str(ROOT / "src"))
from gems_project.release_gate import evaluate_release_gate  # noqa: E402
from hce_banner import HCE_BANNER  # noqa: E402

CSS = """
:root{--bg:#0d1117;--panel:#161b22;--line:#30363d;--fg:#e6edf3;--mut:#9aa7b4;--ok:#2ea043;--warn:#d29922;--bad:#da3633;--accent:#58a6ff}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
header{background:#010409;border-bottom:1px solid var(--line);padding:14px 20px;display:flex;gap:18px;flex-wrap:wrap;align-items:center}header b{font-size:17px}header a{color:var(--mut);text-decoration:none;font-size:14px}header a:hover,header a.on{color:var(--fg)}
main{max-width:1080px;margin:0 auto;padding:26px 20px 80px}h1{font-size:30px;line-height:1.25;margin:8px 0 10px}h2{font-size:22px;margin:34px 0 10px;border-bottom:1px solid var(--line);padding-bottom:6px}h3{font-size:17px;margin:22px 0 8px}p,li{color:#d7dee6}
code{background:#1f2630;padding:1px 5px;border-radius:4px;font-size:13px;overflow-wrap:anywhere}.small{font-size:13.5px;color:var(--mut)}.hero{border:1px solid var(--bad);background:linear-gradient(180deg,#2a1214,#0d1117);border-radius:12px;padding:22px;margin:14px 0 8px}.tag{display:inline-block;font-size:12px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;padding:3px 9px;border-radius:99px;background:var(--bad);color:#fff}.btn{display:inline-block;background:#21262d;border:1px solid var(--line);color:var(--fg);font-weight:600;padding:13px 22px;border-radius:9px;text-decoration:none;margin:12px 10px 4px 0;font-size:16px}.btn.warn{background:var(--warn);color:#1a1200;border-color:var(--warn)}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin:16px 0}.kpi{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:12px 14px}.kpi .v{font-size:21px;font-weight:700}.kpi .k{font-size:12.5px;color:var(--mut);text-transform:uppercase;letter-spacing:.05em}
table{width:100%;border-collapse:collapse;margin:14px 0;font-size:14px}th,td{text-align:left;padding:8px 9px;border-bottom:1px solid var(--line);vertical-align:top}th{color:var(--mut);font-weight:600;font-size:13px;text-transform:uppercase;letter-spacing:.04em}tr.me td{background:#28191b;font-weight:600}.yes{color:var(--ok);font-weight:700}.no{color:#ff8b8b;font-weight:700}.note{background:var(--panel);border-left:3px solid var(--accent);padding:12px 14px;border-radius:0 8px 8px 0;margin:14px 0}.warnbox{background:var(--panel);border-left:3px solid var(--warn);padding:12px 14px;border-radius:0 8px 8px 0;margin:14px 0}.danger{background:#2a1214;border-left:3px solid var(--bad);padding:12px 14px;border-radius:0 8px 8px 0;margin:14px 0}footer{border-top:1px solid var(--line);color:var(--mut);font-size:13px;padding:18px 20px;margin-top:40px}a{color:var(--accent)}ul{padding-left:22px}.scroll{overflow-x:auto}
"""
NAV = (("index.html", "Start"), ("executive-summary.html", "Executive summary"),
       ("research.html", "Science"), ("evidence.html", "Evidence"))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def page(title: str, body: str, current: str) -> str:
    nav = "".join(
        f'<a href="{href}" class="{"on" if href == current else ""}">{name}</a>'
        for href, name in NAV
    )
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="gemsdoe-decision" content="DO-NOT-SUBMIT">
<title>{esc(title)} · WBGGEMSDOE3</title><style>{CSS}</style></head>
<body><header><b>WBGGEMSDOE3</b>{nav}<a href="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/" target="_blank" rel="noopener">Official leaderboard ↗</a></header>
<main>{HCE_BANNER}{body}</main>
<footer>Evidence-first research for the <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">DOE GEMS Prize</a>. Historical owner claims, local proxies, and format checks are not organizer receipts.</footer>
</body></html>"""


def focus_rows(audit: dict) -> str:
    records = sorted(audit["focus_sites"], key=lambda x: -float(x["claimed_by_owner_not_receipt"]))
    rows: list[str] = []
    for r in records:
        worst = max((float(c["my_dots_within_3px"]) for c in r.get("comparisons", [])), default=float("nan"))
        rows.append(f"""<tr><td><b>{esc(r['site'])}</b></td>
<td><a href="{esc(r['download_research_only'])}" rel="noopener"><code>{esc(r['filename'])}</code></a><div class="small">research only · SHA-256 {esc(r['sha256'][:16])}…</div></td>
<td>{esc(r['claimed_by_owner_not_receipt'])}<div class="small">OWNER-REPORTED; no receipt tied to these bytes</div></td>
<td>NOT ESTIMABLE<div class="small">no compliant common HOLDOUT-DTI or receipt-linked calibration</div></td>
<td class="no">NO — worst measured focus overlap {worst:.1%}</td>
<td class="no">DO NOT SUBMIT — already scored / not unique</td></tr>""")
    return "\n".join(rows)


def main() -> int:
    authority_path = ROOT / "evidence" / "run_card.json"
    candidate_path = ROOT / "evidence" / "gemsdoe_run_card.json"
    authority = json.loads(authority_path.read_text())
    candidate = json.loads(candidate_path.read_text())
    gate = evaluate_release_gate(authority, candidate)
    if gate["okay_to_submit"]:
        raise RuntimeError("This renderer is intentionally scoped to the current negative release decision.")

    audit = json.loads((ROOT / "evidence" / "focus_audit.json").read_text())
    leaderboard = json.loads((ROOT / "registry" / "leaderboard.json").read_text())
    tif_rel = candidate["download"]["tif"]
    zip_rel = candidate["download"]["zip"]
    tif_name, zip_name = Path(tif_rel).name, Path(zip_rel).name
    tif = ROOT / tif_rel
    zipfile = ROOT / zip_rel
    if not tif.exists() or sha256(tif) != candidate["sha256"]:
        raise RuntimeError("candidate bytes are missing or do not match their lane card")

    DOCS.mkdir(exist_ok=True)
    DATA.mkdir(exist_ok=True)
    (DOCS / "downloads").mkdir(exist_ok=True)
    shutil.copy2(tif, DOCS / "downloads" / tif_name)
    shutil.copy2(zipfile, DOCS / "downloads" / zip_name)

    gate["source_cards"] = {
        "authority": "evidence/run_card.json", "authority_sha256": sha256(authority_path),
        "candidate": "evidence/gemsdoe_run_card.json", "candidate_sha256": sha256(candidate_path),
    }
    (ROOT / "evidence" / "release_gate.json").write_text(json.dumps(gate, indent=2, sort_keys=True) + "\n")
    focus = focus_rows(audit)
    reasons = "".join(f"<li>{esc(reason)}</li>" for reason in gate["blocking_reasons"])
    n_positive = candidate["validator"].get("n_positive", "not recorded")
    local_ok = bool(candidate["validator"].get("pass"))
    reported_top = audit["focus_sites"][0]["claimed_by_owner_not_receipt"]

    release_box = f"""
<div class="hero"><span class="tag">DO NOT SUBMIT</span><h1>No competition file is cleared</h1>
<p><b>{esc(tif_name)}</b> is a format-valid <em>research artifact</em>, not an approved competition submission.
The global release gate is fail-closed and requires a correct holdout, literal uniqueness clearance, and a separate selector approval for the exact SHA-256. Those requirements are not met.</p>
<a class="btn warn" href="downloads/{esc(tif_name)}" download>Download research GeoTIFF — NOT for upload</a>
<a class="btn" href="downloads/{esc(zip_name)}" download>Research ZIP — NOT for upload</a>
<p class="small">SHA-256 <code>{esc(candidate['sha256'])}</code> · suggested future note (not authorized now): <code>{esc(candidate['download']['note'])}</code></p></div>
<div class="danger"><b>Blocking release checks:</b><ul>{reasons}</ul><p>Local byte validation is {"PASS" if local_ok else "not passing"}; that is necessary but never sufficient for portal acceptance, uniqueness, or a leaderboard result.</p></div>"""

    index_body = release_box + f"""
<div class="kpis"><div class="kpi"><div class="k">Competition-score estimate</div><div class="v">NOT ESTIMABLE</div><div class="small">No compliant common holdout or organizer receipt</div></div>
<div class="kpi"><div class="k">Candidate metric</div><div class="v">PROXY ONLY</div><div class="small">Not a required HOLDOUT-DTI</div></div>
<div class="kpi"><div class="k">Literal all-registry gate</div><div class="v no">FAIL</div><div class="small">Dense registered control makes the current rule a stop</div></div>
<div class="kpi"><div class="k">Saved-byte preflight</div><div class="v {'yes' if local_ok else 'no'}">{'PASS' if local_ok else 'FAIL'}</div><div class="small">single-band float32, [0,1], exact grid — local check</div></div>
<div class="kpi"><div class="k">Weekly slots used</div><div class="v">0</div><div class="small">No portal action taken</div></div>
<div class="kpi"><div class="k">Public leaderboard observation</div><div class="v">{esc(leaderboard.get('best_public_dti', 'unknown'))}</div><div class="small">observed {esc(str(leaderboard.get('last_success_utc', 'unknown'))[:10])}; not this project</div></div></div>
<h2>Decision in plain language</h2>
<p>There is <b>no file to upload today</b>. The downloadable TIFF is retained so that the automated format checks can be reproduced; downloading it is not permission to submit it. The nine historical leaders are also research references only. The global gate is based on the binding literal protocol, not an optional lane-level reinterpretation.</p>
<h2>The nine focus sites</h2><div class="scroll"><table><thead><tr><th>Site</th><th>Best pinned historical file</th><th>Claim</th><th>New-file estimate</th><th>Unique vs focus set?</th><th>Decision</th></tr></thead><tbody>{focus}</tbody></table></div>
<p class="small">The values in the claim column are copied from owner materials and are not organizer scores or ORGANIZER-CONFIRMED receipts. The score-estimate column deliberately says NOT ESTIMABLE rather than converting a proxy or owner claim into a predicted leaderboard result.</p>
<h2>Automated next steps before any submission</h2><ol><li>Resolve the literal registry-support definition with the protocol owner; do not silently exempt a dense control.</li><li>Use one assigned lane and the shared hide-and-recover evaluator to produce HOLDOUT-DTI with whole-segment buffering, positive count and 95% CI.</li><li>Run per-feature leakage canaries, then rerun the full literal registry check on the surface and final dots.</li><li>Re-read saved bytes against an organizer-authenticated template and obtain a separate selector approval for the exact SHA-256.</li><li>Only then use the submission-page quota and preserve the organizer receipt.</li></ol>"""

    exec_body = f"""
<span class="tag">DO NOT SUBMIT</span><h1>Executive summary and submission gate</h1>
<p><b>Best historical focus-site claim:</b> GEMSDOE32 B2 at <b>{esc(reported_top)}</b>, labelled OWNER-REPORTED — not a receipt. <b>Best file to submit:</b> none. The table below makes the decision explicit for every listed site and the locally generated artifact.</p>
<h2>1. Required table</h2><div class="scroll"><table><thead><tr><th>Site / candidate</th><th>File</th><th>Claim or estimate</th><th>Unique?</th><th>Safe decision</th></tr></thead><tbody>{focus}
<tr class="me"><td><b>This repository candidate</b></td><td><code>{esc(tif_name)}</code><div class="small">{n_positive:,} positive cells · SHA-256 {esc(candidate['sha256'][:16])}…</div></td><td>NOT ESTIMABLE<div class="small">PROXY-DTI exists, but no compliant release HOLDOUT-DTI</div></td><td class="no">NO under literal all-registry rule</td><td class="no"><b>DO NOT SUBMIT</b><br>Download only to reproduce checks</td></tr></tbody></table></div>
<h2>2. Why GEMSDOE32 B2 may have performed well — bounded conclusion</h2>
<p>The pinned byte audit shows B2 has 37,654 positive cells and is a subset of a 40,199-cell base; 2,545 cells were removed near the mirrored mapped-fault mask. Under the stated 300 m, α=0.2/β=0.8 distance-weighted metric, sparse placement and removal of catalogue-adjacent mass are a plausible mechanism for improving a new-fault target. This is a byte-level observation, <b>not</b> proof of an organizer score or a causal explanation: the hidden labels and upload receipt are unavailable.</p>
<h2>3. Format/range check for the generated research TIFF</h2><table><thead><tr><th>Check</th><th>Recorded result</th><th>Meaning</th></tr></thead><tbody>
<tr><td>Single band / float32 / EPSG:32611 / shape / transform</td><td class="yes">local PASS</td><td>Saved bytes match the pinned mirror template in the lane card.</td></tr>
<tr><td>Finite values in [0,1]</td><td class="yes">local PASS</td><td>It locally avoids the historic “Predicted values must be in range [0, 1]” error class; portal acceptance remains unverified.</td></tr>
<tr><td>Submission release</td><td class="no">FAIL</td><td>{esc('; '.join(gate['blocking_reasons']))}</td></tr></tbody></table>
<h2>4. When the gate is green</h2><p>Only after the release gate says SUBMIT: download the exact TIFF; use DrivenData → New submission; paste the stored note (≤140 characters); verify the current weekly cap; and keep the receipt beside the SHA-256. At present, stop before the upload step.</p>
<h2>5. Sources for manual review</h2><ul><li><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/">Official problem and metric</a></li><li><a href="https://www.drivendata.org/competitions/306/competition-doe-gems/">Competition overview and rules</a></li><li><a href="https://github.com/drivendataorg/gems-prize-reference-solution">Organizer reference solution</a></li><li><a href="https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and">USGS GeoDAWN</a> and <a href="https://www.usgs.gov/3d-elevation-program">USGS 3DEP</a></li></ul>"""

    research_body = """
<span class="tag">RESEARCH ONLY</span><h1>Hypotheses and scientific constraints</h1>
<p>The target is unmapped surface-fault probability, not direct detection of geothermal vents. Potential-field, radiometric, topographic and geothermal observations can support hypotheses but are not ground truth. The ranked hypotheses and source-availability decisions were written before execution in <code>knowledge/preregistration-2026-10-27.md</code> and <code>knowledge/preregistration-2026-10-27-hce.md</code>.</p>
<h2>Candidate hypotheses currently documented</h2><table><thead><tr><th>Hypothesis</th><th>Layers / signature</th><th>Why it might detect an uncatalogued fault</th><th>Named mimic / status</th></tr></thead><tbody>
<tr><td>Cross-scale potential-field edge stability</td><td>Isostatic gravity, RTP magnetics, detrended elevation; persistent, collinear multi-scale gradients</td><td>Buried density and magnetization discontinuities may outlast a subdued scarp.</td><td>Lithologic contact, volcanic margin, survey stripe. Tested CSPES result is negative; do not promote.</td></tr>
<tr><td>Strain-aligned magnetic discontinuity</td><td>Geodetic strain gradients plus RTP magnetic edges</td><td>Active strain localization could reveal a trace missing from surface mapping.</td><td>Interseismic deformation / groundwater-pumping artefact. Not run.</td></tr>
<tr><td>Basement-cover step-over</td><td>Depth to basement, conductivity, gravity high gradient</td><td>Concordant subsurface changes could mark a covered basin-margin fault.</td><td>Stratigraphic onlap / interpolated-surface artefact. Not run.</td></tr>
<tr><td>Phase-based tilt crest with gravity confirmation</td><td>Tilt-angle phase crossings, gravity and magnetic horizontal gradients</td><td>May locate amplitude-robust discontinuities where direct scarps are weak.</td><td>Dike or dipping contact. Not run; adjacent prior art exists.</td></tr>
<tr><td>Thermal-plume contrast</td><td>INGENIOUS temperatures, sampling effort and structural gradient</td><td>Advection across a hidden permeable structure is physically plausible.</td><td>Groundwater/climate/sampling bias. Requires official external bytes not accessible here.</td></tr></tbody></table>
<h2>Validated negative result</h2><p>CSPES used the cached potential-field stack and recorded HOLDOUT-DTI 0.0257 (95% CI 0.0194–0.0319; 22,232 withheld positives; evaluator GEMSDOE32-HIDE-RECOVER-v3.0), below its matched incumbent 0.0992. Its run card is a negative deliverable: <a href="data/cspes_run_card.json">CSPES JSON</a>.</p>
<div class="warnbox"><b>External-data limit.</b> This sandbox can reach GitHub and package registries but not the cited official USGS/GDR/DrivenData download hosts. Public links are provided for review; availability and coverage are not asserted without an authenticated source download.</div>"""

    evidence_body = f"""
<span class="tag">GLOBAL RELEASE GATE: DO NOT SUBMIT</span><h1>Evidence, conflicts, and reproducibility</h1>
<h2>1. Which record governs?</h2><p><code>evidence/run_card.json</code> is the repository-level governing card and has verdict <code>{esc(authority.get('verdict'))}</code>. <code>evidence/gemsdoe_run_card.json</code> is a lane card that reports a proxy and a restricted uniqueness audit. The latter cannot override the former. The generated <a href="data/release_gate.json">release gate JSON</a> records the reconciliation and hashes both source cards.</p>
<pre class="small">{esc(json.dumps(gate, indent=2, sort_keys=True))}</pre>
<h2>2. Available audit records</h2><ul><li><a href="data/run_card.json">Governing run card</a></li><li><a href="data/gemsdoe_run_card.json">Candidate lane card (research record)</a></li><li><a href="data/focus_audit.json">Nine-site byte/overlap audit</a></li><li><a href="data/verification_2026-10-27.json">Independent verification record</a></li><li><a href="data/uniqueness.json">Restricted comparator diagnostics</a></li><li><a href="data/cspes_run_card.json">CSPES negative run card</a></li></ul>
<h2>3. Irregularities to resolve before another experiment</h2><ol><li>The literal duplicate rule is made vacuous by a registered dense positive raster. A content-aware reading is a protocol change, not an automatic waiver.</li><li>The skarpline candidate records PROXY-DTI rather than the requested whole-segment hide-and-recover HOLDOUT-DTI.</li><li>Historical values are owner-reported claims without organizer receipts bound to exact file bytes.</li><li>The data mirror proves pinned byte identity but not organizer provenance; the official data tab is login-walled in this environment.</li><li>The official outside-footprint convention and the historic portal range rejection have not been confirmed by a portal receipt.</li></ol>
<h2>4. Reproduce the non-destructive checks</h2><pre class="small">python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
PYTHONPATH=src .venv/bin/python scripts/generate_release_gate.py || test $? -eq 2
PYTHONPATH=src .venv/bin/python scripts/build_executive.py
PYTHONPATH=src .venv/bin/python scripts/check_site.py
PYTHONPATH=src .venv/bin/python -m pytest -q</pre>"""

    (DOCS / "index.html").write_text(page("Start", index_body, "index.html"))
    (DOCS / "executive-summary.html").write_text(page("Executive summary", exec_body, "executive-summary.html"))
    (DOCS / "research.html").write_text(page("Science", research_body, "research.html"))
    (DOCS / "evidence.html").write_text(page("Evidence", evidence_body, "evidence.html"))

    for source, target in ((authority_path, "run_card.json"), (candidate_path, "gemsdoe_run_card.json"),
                           (ROOT / "evidence" / "release_gate.json", "release_gate.json"),
                           (ROOT / "evidence" / "focus_audit.json", "focus_audit.json"),
                           (ROOT / "evidence" / "verification_2026-10-27.json", "verification_2026-10-27.json"),
                           (ROOT / "evidence" / "cspes_run_card.json", "cspes_run_card.json"),
                           (DOCS / "data" / "uniqueness.json", "uniqueness.json")):
        if source.resolve() != (DATA / target).resolve():
            shutil.copy2(source, DATA / target)

    (DOCS / "downloads" / "LEGACY-DO-NOT-SUBMIT.txt").write_text(
        "RESEARCH ARTIFACTS — DO NOT SUBMIT.\n"
        "No file in this directory is cleared by the repository-wide release gate.\n"
        f"{tif_name} is locally format-valid but blocked by the literal registry, holdout, and selector gates.\n"
    )
    (DOCS / "downloads" / "index.html").write_text(f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Research downloads</title><style>body{{font:16px/1.6 system-ui;max-width:52rem;margin:3rem auto;padding:1rem;color:#ddd;background:#0d1117}}a{{color:#58a6ff}}code{{background:#1f2630;padding:1px 5px;border-radius:4px}}</style></head><body><h1>Research downloads — DO NOT SUBMIT</h1><p>These bytes are kept for reproducibility. The global release gate has not approved a competition upload.</p><p><a href="{esc(tif_name)}" download>{esc(tif_name)}</a> · <a href="{esc(zip_name)}" download>ZIP</a><br><small>SHA-256 <code>{esc(candidate['sha256'])}</code></small></p><p><a href="../executive-summary.html">Read the executive gate decision</a></p></body></html>""")
    print("wrote negative-gate dashboard and evidence copies")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
