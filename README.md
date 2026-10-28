# GEMS Field Notes — evidence-first fault-discovery review

> ## Current repository decision: **DO NOT SUBMIT**
>
> **No new GeoTIFF was generated or cleared in this review.** There is no candidate
> `HOLDOUT-DTI`, no current candidate hash or validator result, no organizer receipt,
> and no selector approval. The repository's current release gate is
> [`docs/data/release_gate.json`](docs/data/release_gate.json) (`gems-release-gate-v1`);
> its fail-closed decision is `DO-NOT-SUBMIT`.
>
> Historical TIFFs in [`docs/downloads/`](docs/downloads/index.html) remain available
> **for research/inspection only**. None is approved for a competition upload. Do not
> infer approval from a local format check, a lane's old `promote` label, a filename,
> or a score written in a peer repository.
>
> **Why stopped:** the pinned public-mirror witness is positive on every cell of the
> mirrored sample footprint under the recorded finite-and-positive support rule.
> Under the user's literal directed-overlap rule, any nonempty in-footprint candidate
> would overlap that raster by 100%, above the 70% stop. This is a conditional
> measurement against one owner mirror, not proof of complete or organizer-authenticated
> registry coverage. Independently, the competition feature stack, labels, sample file,
> and saved holdout cache are absent here. The assigned “single method paragraph” is
> not identifiable in the available materials. Do not waive the literal stop, create a
> cosmetically unique TIFF, or claim a score to satisfy the request to generate a file.
>
> **Current review card:** [`evidence/session_c1e656ce_run_card.json`](evidence/session_c1e656ce_run_card.json) ·
> **Review log:** [`knowledge/review-c1e656ce.md`](knowledge/review-c1e656ce.md) ·
> **Research hypotheses:** [`knowledge/hypotheses.md`](knowledge/hypotheses.md) ·
> **Official-source links and limits:** [Research page](docs/research.html) ·
> **Nine-site table:** [Executive summary](docs/executive-summary.html).

## Start every session here

Read this README and its **Standing user brief and operating constraints** below at the
start of every session. Also read [`PROJECT_PROMPT.md`](PROJECT_PROMPT.md),
[`AGENTS.md`](AGENTS.md), [`knowledge/protocol.md`](knowledge/protocol.md), the current
release gate, and the current review card. Treat the repository and the current user's
instructions as the source of truth; historical site pages and run cards can be stale or
contradictory. Preserve the values **Maximize P(Win)** and **Own the Outcome**: weigh
risk and evidence, act autonomously when safe, and treat negative results as deliverables.

## Current findings

### Nine requested GEMSDOE sites

The table on the [executive-summary page](docs/executive-summary.html) links the pinned
historical TIFF for each requested site, labels reported values as **OWNER-REPORTED**,
uses **Not estimable** for an unvalidated leaderboard estimate, and marks the files
non-unique where the recorded 3-pixel comparison fails. Those old reports are not
organizer receipts or current score estimates. They are not recommended for submission.

The highest value in the available focus-site ledger is GEMSDOE32's **OWNER-REPORTED
0.2778**; no receipt connecting that value to the exact bytes is available here. The
recorded pair analysis says its 37,654-cell support is a subset of a GEMSDOE28
40,199-cell support, with 2,545 cells removed, all within 3 pixels of the mirrored
fault catalogue. This is consistent with catalogue-collar pruning reducing false-positive
mass under the stated distance-tolerant metric, but does **not** establish why the
reported result occurred: the hidden labels, score receipt, and authenticated data are
unavailable. See [`content/why-0.2778.md`](content/why-0.2778.md) and
[`evidence/pair_identification.json`](evidence/pair_identification.json). The arithmetic
in that file is an inference from owner reports, not a measured hidden-truth count or a
score projection for a new file.

### No new candidate result

- No geological experiment ran in this repository review (0 of the allowed 3); no
  competition slot was used.
- No new surface or dot set was placed. A candidate's pre-placement rank correlation
  and final-dot overlap are therefore **not measured**; the current card records them as
  null. The separate witness result is not a candidate result.
- No current-candidate `HOLDOUT-DTI` or confidence interval is reported. A valid result
  must name the shared evaluator version, withheld-positive count, and spatial 95% CI.
  Projections are never scores.
- No candidate TIFF exists from this review, so its SHA-256 and validator output are
  null/not run. A local format pass is not portal acceptance.
- The old `[0, 1]` portal rejection cannot be diagnosed without the exact rejected bytes
  and submission receipt. A future candidate must be checked on exact saved bytes for
  finite values, `[0,1]` range, CRS, shape, transform, and the official outside-footprint
  rule.
- This competition targets fault predictions, not geothermal vents. A fault prediction
  does not establish a vent, geothermal resource, or field discovery.

### Historical lane records

Historical lane pages, including the [LBCAL archive](docs/lbcal/index.html),
[FCHD-NCM dossier](docs/fchd/index.html), and [AMDC dossier](docs/amdc/index.html), are
research-only. Their lane cards and past `promote` labels do not override the repository
DO-NOT-SUBMIT gate.

### Prospective hypotheses—not a selected lane

[`knowledge/hypotheses.md`](knowledge/hypotheses.md) ranks four distinct, qualitative
hypotheses and identifies their conceptual input layers, geophysical signatures,
uncatalogued-fault rationale, code distinctions, mimics, cost, and source requirements.
Their expected DTI upside is a **relative research ranking only**, not a numeric forecast.
No “single method paragraph” or assigned lane was identified, and no hypothesis was run.
The official competition data page is the required source for authenticated features,
labels, and sample geometry; the competition requires authentication, which is not
available to this agent. GitHub mirrors are hash-pinned but do not authenticate organizer
provenance. Official USGS GeoDAWN, USGS 3DEP, DOE GDR, and competition links are retained
for manual review; their non-GitHub hosts were not accessible during this review.

## Reproduce the safe repository checks

The site builder is fail-closed and rewrites the current decision and download notice
from the checked-in negative authority/candidate cards. Retired positive publishers stop
before writing. With dependencies installed:

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/build_site.py
.venv/bin/python scripts/check_site.py
.venv/bin/python -m pytest -q
```

Optional, read-only refresh of the hash-pinned GitHub-mirror witness audit (does not run
an experiment or create a candidate):

```bash
.venv/bin/python scripts/recheck_registry_witness.py \
  --fetch --output evidence/session_c1e656ce_witness_recheck.json
```

The mirror audit is conditional evidence; it is not an authenticated organizer download,
full registry audit, holdout, or score. Do not run a geological experiment or emit a
candidate until the literal stop and missing inputs are resolved and the method lane is
identified. The separate selector controls promotion and weekly submission caps. This
agent cannot access a DrivenData account, inspect private quota, or upload a file.

## Official and reference links

Links are provided for traceability and manual review; they are **not claims of a fresh
fetch, current leaderboard state, data availability, or score receipt**.

- [DrivenData competition](https://www.drivendata.org/competitions/306/competition-doe-gems/)
- [DrivenData problem and scoring description](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- [DrivenData competition details](https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/)
- [DrivenData data page (authentication required)](https://www.drivendata.org/competitions/306/competition-doe-gems/data/)
- [DrivenData public leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)
- [DrivenData submissions page](https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/)
- [Organizer reference solution on GitHub](https://github.com/drivendataorg/gems-prize-reference-solution)
- [NLR/DOE competition report](https://docs.nlr.gov/docs/fy26osti/96647.pdf)
- [USGS GeoDAWN airborne survey](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
- [Great Basin Center for Geothermal Energy — INGENIOUS](https://gbcge.org/current-projects/ingenious/)
- [DOE Geothermal Data Repository — INGENIOUS](https://gdr.openei.org/submissions/1391)
- [USGS 3D Elevation Program](https://www.usgs.gov/3d-elevation-program)
- [EPSG:32611](https://epsg.io/32611)
- [Tversky index](https://en.wikipedia.org/wiki/Tversky_index)

## Standing user brief and operating constraints

This is the complete retained working brief for this repository. The original source
conversation is not available as a verbatim transcript, so this block is a **faithful reconstruction** of the active requirements, not a verbatim quote. If the user supplies
newer exact wording, it supersedes this reconstruction. Read this section every session.

### Goal

Review prior repository work and investigate the nine named GEMSDOE sites
(GEMSDOE24, GEMSDOE25, GEMSDOE27, GEMSDOE28, GEMSDOE30, GEMSDOE31, GEMSDOE32,
GEMSDOE33, GEMSDOE36) and GEMSDOE32's reported 0.2778 result. Produce a clear executive
table with historical file links, properly classified evidence, and uniqueness findings.
Rank 3–5 distinct geological hypotheses, including conceptual layers, signature,
uncatalogued-fault rationale, differences from implemented methods, expected relative
DTI improvement, cost, and a named non-fault mimic. Validate a best candidate on the
prescribed holdout before considering any slot. If required external inputs are needed,
name the specific free official source and check whether it is obtainable before calling
a hypothesis viable. Do not hallucinate or treat a mirror as authenticated organizer data.

The long-term goal of producing a unique, valid, easy-to-download GeoTIFF remains active.
That goal **does not override the literal duplicate stop, missing holdout inputs, experiment
budget, or separate selector**. Make it obvious whether a file is safe to download and
whether it is authorized to submit. When no candidate clears, show `DO NOT SUBMIT`; do not
create a cosmetic/empty/renamed TIFF or fabricate a score, validation, receipt, or
uniqueness pass. Preserve the exact portal error `[0, 1]` and describe only what exact-byte
validation can establish. Include exact future submission steps and official source links.

### Parallel-run protocol (controlling)

1. **Method lane.** Stay in the single assigned method paragraph. The paragraph has not
   been identified in the available materials; do not infer or switch lanes. Before
   placement and again on final dots, compare with every registry raster. If surface rank
   correlation exceeds 0.90 or more than 70% of candidate dots lie within 3 pixels of one
   registry raster's dots, record a duplicate and stop. There is no dense-raster or
   content-aware exemption in the current protocol.
2. **Shared tools only.** Reuse the template's cached feature stack,
   `evaluate_holdout.py`, and `submission_writer.py`. Do not build a private evaluator or
   writer fork. Hide whole buffered fault segments; derive all catalogue-based features
   from visible faults only; mask visible faults pixel-exactly; score pooled DTI with
   α=0.2, β=0.8 and a 300 m triangular kernel. Fix a shared-tool defect upstream once
   and report it; do not silently substitute another evaluator.
3. **Leakage canary.** Test every feature alone on the holdout. AUC >0.90 is a leakage
   warning until resolved.
4. **Score labels.** Every reported score must be either `HOLDOUT-DTI` with evaluator
   version, withheld-positive count and 95% CI, or `ORGANIZER-CONFIRMED` with a submission
   receipt. Historical peer claims may be shown only as `OWNER-REPORTED`; projections and
   ledger inversions are never scores.
5. **Run card.** End each run with one JSON card recording the hypothesis, mechanism,
   named non-fault mimic, holdout and CI, pre-placement and final registry comparisons,
   raster SHA-256, validator output (NaN/range/CRS/shape/transform), submission name and
   note (≤140 characters), and `promote` or `negative` verdict. Record `null`/`NOT RUN`
   honestly when evidence does not exist. Negative results are valid deliverables.
6. **Budget and selector.** Stop after 3 experiments or 2 hours. Do not select or spend a
   real submission slot. A separate selector decides promotion and checks the live
   account's weekly cap.
7. **Review passes and delivery.** Complete multiple review passes for completeness,
   assumptions, edge cases, and accuracy. The requested workflow is a pull request and
   merge; stay on the assigned Arena branch and follow the repository's branch controls.
8. **Core values.** Maximize P(Win by weighing evidence and risk) and Own the Outcome
   without bypassing stated constraints. Work autonomously where safe; stop and disclose
   blockers instead of inventing a path around them.
