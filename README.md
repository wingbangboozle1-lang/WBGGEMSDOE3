# GEMS Field Notes — GEMS fault-mapping review

<!-- FEED:BEGIN -->
## Current desk state — regenerated 2026-10-31 01:45 UTC by `scripts/build_readme_feed.py`

**Decision: NOT CLEARED — do not upload.**
Do not read any number below as an organizer-confirmed score: no submission was uploaded from this
environment, so no receipt exists.

| | |
|---|---|
| File | [`docs/downloads/wbggems3-ggo-covergate-60000d-20261031T012630Z-e7c02e69-zeros.tif`](docs/downloads/wbggems3-ggo-covergate-60000d-20261031T012630Z-e7c02e69-zeros.tif) · sha256 `348605467b0c868925a0d6bb…` |
| Format gates | 4/6 true · all-pass True |
| Estimate | **0.0774** LEDGER-INVERSION ESTIMATE (60000 dots), CV MAE 0.06476, estimator Spearman 0.3376 on 118 public probes — an estimate, never a score |
| HOLDOUT-DTI | 0.019485 (60988 withheld positives, CI [0.0, 0.047918]); arm A3_ggo_plus_morphology beats incumbent on the holdout: True |
| Uniqueness | 138 sibling rasters censused, 2 blockers, worst informative 3-px overlap 0.748683, worst |ρ| 0.859966 |
| Leakage canary | max single-feature AUC 0.8261 (bar 0.90) |
| Live public leaderboard | rank 1 = **0.4544** (2026-10-31T01:05:00Z); the brief's 0.4413 / 0.3195 are stale (IR-31-01) |

Holdout arms (pooled, best first): `A3_ggo_plus_morphology` 0.0319, `A1_morphology_incumbent` 0.0273, `A3_ggo_plus_morphology` 0.0195, `A3_ggo_plus_morphology` 0.0119.

Read next: [docs/index.html](docs/index.html) (one-click download desk),
[docs/executive-summary.html](docs/executive-summary.html) (nine-site table with estimates and
uniqueness), [docs/how-to-submit.html](docs/how-to-submit.html) (exact portal steps and the root
cause of `Predicted values must be in range [0, 1]`),
[docs/research.html](docs/research.html) (instruments, sources, census),
`evidence/ggo_run_card.json` (machine-readable run card).
<!-- FEED:END -->


## Start here — 2026-10-29 executive summary

**Read first: [knowledge/executive-summary-2026-10-29.md](knowledge/executive-summary-2026-10-29.md)**
(nine-site table with file, owner-reported score, projection, uniqueness, and decision).

- **Decision: DO NOT DOWNLOAD OR SUBMIT.** No file is cleared. No TIFF was generated on
  2026-10-29, and no holdout score or slot selection exists.
- **Best owner-reported file:** GEMSDOE32, 0.2778 (owner report, not a receipt). It is **not
  unique**: every nine-site file overlaps another at ≥97.6% within 3 px.
- **Why no new file yet:** the competition labels cannot be reached from this sandbox
  (DrivenData and Dropbox are unreachable); the repo's dense-witness stop is open; and the
  portal's `Predicted values must be in range [0, 1]` error is unexplained.
- **Reproduce the summary and verification record:**
  `python scripts/build_executive_summary_2026_10_29.py --archive <pinned 57GEMSDOE tar.gz>`
  writes `evidence/verification_2026_10_29.json` and the summary above.

### Requirements from the 2026-10-29 request (condensed, not verbatim)

1. Review GEMSDOE24, 25, 27, 28, 30, 31, 32, 33, 36 and give each an executive summary with the
   best submission file, an estimated score, and a uniqueness verdict.
2. Explain why GEMSDOE32 (0.2778) scored highest, and generate a unique, validated TIFF only if
   it passes the holdout and uniqueness gates. Do not spend a slot without a holdout win.
3. Generate 3–5 geological hypotheses ranked by expected gain and cost, each with a named
   non-fault mimic and a holdout test on the spatially blocked set.
4. Label every number as `HOLDOUT-DTI` (evaluator, withheld count, 95% CI) or
   `ORGANIZER-CONFIRMED` (from a receipt). A projection is never a score.
5. Cite official sources with links; flag irregularities; no manual input; no hallucinations.
6. Keep *Maximize P(Win)* and *Own the Outcome* as the decision rule.

### Irregularities flagged for review (2026-10-29)

- **IR-29-01 Template footprint.** `data/template_grid.tif` is all-zero across 12,279,160
  finite cells; the writer's claimed official footprint is 5,167,373. CRS, shape, origin, and
  resolution match. (Extends IR-28-12.)
- **IR-29-02 Leaderboard figures.** The request gives 0.4413 as the high and 0.3195 as the
  current top. The repo's 2026-10-28 capture has rank 1 = 0.4544 and 0.3195 at rank 26.
- **IR-29-03 Third-party label mirror.** A public owner archive (57GEMSDOE, pinned commit
  `822a0ce5`) holds `data/official/labels.tif`, whose SHA-256 is identical to
  `existing_faults.tif`. Its license and organizer origin are unverified, so it is not used.
- **IR-29-04 Portal error.** `Predicted values must be in range [0, 1]` has no local
  reproduction; the archived writer's cause is unproven.
- **IR-29-05 Deadline.** The homepage and the rules' Appendix A disagree (unresolved).

Sources: [competition](https://www.drivendata.org/competitions/306/competition-doe-gems/),
[problem and metric](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/),
[leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/),
[rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf).

---

> ## STATUS — 2026-10-29: still **DO NOT SUBMIT**; the blocker is a definition, and it needs your decision
>
> **No downloadable TIFF is cleared.** This session re-measured the registered dense witness
> (`17GEMSDOE_E-proba-multiscale`, sha256 `ab0a0a62…3872be`, verified against its pinned commit). It is a
> soft-probability map (0.0005–0.984). The literal "dots = value > 0" rule therefore puts 100% of the footprint
> into the witness, which causes the universal stop. Top-37,654-cell or ≥0.5 definitions are sparse.
> The code comment already calls this surface "not dots", so the gate and the code disagree.
> A second, independent blocker remains: the 13GEMSDOE lattice (0.99 overlap) and two other rasters (0.82, 0.72)
> exceed 70% for the invdesign candidate.
>
> **Decision needed (options A/B/C):** [knowledge/session-review-2026-10-29-witness.md](knowledge/session-review-2026-10-29-witness.md).
> Measurements: [evidence/witness_definition_check_2026-10-29.json](evidence/witness_definition_check_2026-10-29.json) ·
> run card: [evidence/session_2026-10-29_run_card.json](evidence/session_2026-10-29_run_card.json) ·
> reproducible script: `scripts/check_witness_definition.py`.
>
> **Leaderboard conflict:** the brief's 0.4413 / 0.3195 figures do not match the saved 2026-10-28 observation
> (rank 1 = 0.4544). Re-check failed: `drivendata.org` was unreachable from this sandbox (HTTP 000).

> ## CURRENT PROJECT DECISION — 2026-10-28: **DO NOT SUBMIT**
>
> **No file is cleared. This review generated no candidate TIFF.** While this branch was in
> progress, GitHub `main` advanced with PR #53, which added a 15,000-dot blind-basin TIFF under
> `docs/downloads/`. It was not generated or used as a candidate in this review, and its
> science/format eligibility was not assessed; its bytes were only matched to the upstream
> reported SHA-256 for quarantine identity. It is not cleared and is treated as a legacy research
> file. This review ran no geological experiment, ran no holdout, and selected no slot.
> The saved owner-mirror witness is positive on all **5,167,373** cells of the mirrored
> sample footprint. Under the committed finite-and-positive support rule, any nonempty
> in-footprint dot map would have 100% directed overlap at distance zero, above the user's
> 70%/3-pixel stop. The finding is conditional on hash-pinned owner mirrors; it is not
> authenticated organizer provenance or a full portal-registry census. The stop is still
> binding under the current literal protocol. **Do not upload any historical TIFF.**
>
> Current machine-readable decision: [`docs/data/release_gate.json`](docs/data/release_gate.json) ·
> current negative run card: [`evidence/session_7393d521_run_card.json`](evidence/session_7393d521_run_card.json) ·
> current site: [`docs/index.html`](docs/index.html) ·
> full evidence: [`docs/evidence.html`](docs/evidence.html).

> ## Uniqueness audit on branch `arena/0d17f7d5-wbggemsdoe3` (2026-10-28, evidence only)
>
> Re-measured every candidate against the **457 real sibling submissions** with the shared 3-px kernel. All four fail the literal 70% rule, and all four fail on the same comparator, the 13GEMSDOE r13 lattice: invdesign **0.9944**, KHD **0.9991**, FCHD **0.9996**, TDE30k **0.9895**. The 3-px footprint of all 457 submissions covers **100%** of the footprint, and the lattice leaves **0.14%** free. No file is cleared; the governing decision above is unchanged.
> Open question for you: keep the literal lattice class in the test, or follow the earlier convention that excludes dense/lattice rasters.
> Details: [knowledge/session-review-2026-10-28-uniqueness.md](knowledge/session-review-2026-10-28-uniqueness.md) · [evidence/session_2026-10-28_uniqueness_run_card.json](evidence/session_2026-10-28_uniqueness_run_card.json) · [evidence/uniqueness_coverage_2026-10-28.json](evidence/uniqueness_coverage_2026-10-28.json)

## Start every session here

Read this README (including the full prompt brief below), [`PROJECT_PROMPT.md`](PROJECT_PROMPT.md),
[`AGENTS.md`](AGENTS.md), the latest
[review](knowledge/review-2026-10-28-session.md) and
[negative run card](evidence/session_7393d521_run_card.json), the
[preregistration](knowledge/preregistration-2026-10-28.md) and its
[machine-readable copy](evidence/preregistration_2026-10-28.json), the
[official-source check](evidence/official_source_check_2026-10-28.json), the
[registry witness recheck](evidence/registry_witness_recheck_2026-10-27.json), and
[`knowledge/protocol.md`](knowledge/protocol.md). Preserve **Maximize P(Win)** and
**Own the Outcome**: weigh tradeoffs, stay evidence-led, act autonomously where safe, and
treat negative findings as deliverables. Never let urgency override the duplicate stop,
provenance limits, or the experiment/selector safeguards.

## Executive summary — requested focus sites

All score values below are **OWNER-REPORTED / UNVERIFIED**, not organizer receipts. No
validated leaderboard estimate is available for these files. Each raster is a historical
research reference only; no file is cleared for download-and-submit. The nine-site byte
audit and direct research links are in [`evidence/focus_audit.json`](evidence/focus_audit.json)
and the generated [executive summary](docs/executive-summary.html).

| Site | Highest pinned historical file (research only) | Owner/user report | Estimate | Unique / decision |
|---|---|---:|---|---|
| GEMSDOE24 | [gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif](https://github.com/buffedlizard55-lab/GEMSDOE24/raw/5cfab74597cd1d0a271e4640b4cc34511e56ca59/docs/downloads/gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif) | 0.2477 | Not estimable | **No; DO NOT SUBMIT** |
| GEMSDOE25 | [gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif](https://github.com/buffedlizard55-lab/GEMSDOE25/raw/bfb2dfdbdf1b87d67afc6facd422180f56ebc455/docs/downloads/gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif) | 0.2600 | Not estimable | **No; DO NOT SUBMIT** |
| GEMSDOE27 | [gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan.tif](https://github.com/buffedlizard55-lab/GEMSDOE27/raw/f1e32af867d9cf0081af20866c8241ec8678a432/docs/downloads/gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan.tif) | 0.2449 | Not estimable | **No; DO NOT SUBMIT** |
| GEMSDOE28 | [gems28-h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan.tif](https://github.com/buffedlizard55-lab/GEMSDOE28/raw/9c1be21e8f1be707347f737e42abf62ea669c819/docs/downloads/gems28-h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan.tif) | 0.2710 | Not estimable | **No; DO NOT SUBMIT** |
| GEMSDOE30 | [gemsdoe30-d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca.tif](https://github.com/buffedlizard55-lab/GEMSDOE30/raw/35ce8911e2c3287eed973eacd12c252e8cb3f34c/docs/downloads/gemsdoe30-d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca.tif) | 0.2600 | Not estimable | **No; DO NOT SUBMIT** |
| GEMSDOE31 | [gemsdoe31-h27-4-solo-d28-20261004-8acb75e1-nan.tif](https://github.com/buffedlizard55-lab/GEMSDOE31/raw/78f9bf3ae82e5c78ca348aa37c0660c339e72f0e/docs/downloads/gemsdoe31-h27-4-solo-d28-20261004-8acb75e1-nan.tif) | 0.2708 | Not estimable | **No; DO NOT SUBMIT** |
| GEMSDOE32 | [gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif](https://github.com/buffedlizard55-lab/GEMSDOE32/raw/8953b986b2ce6eb5ee8b7eda23fe3ad529720986/docs/downloads/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif) | 0.2778 | Not estimable | **No; DO NOT SUBMIT** |
| GEMSDOE33 | [GEMSDOE33-h33d-analog-tip-stepover-r30-20261004-cb490425926e.tif](https://github.com/buffedlizard55-lab/GEMSDOE33/raw/a24fb7c5031ee08b12440af4593057858fecef8e/docs/downloads/GEMSDOE33-h33d-analog-tip-stepover-r30-20261004-cb490425926e.tif) | 0.2632 | Not estimable | **No; DO NOT SUBMIT** |
| GEMSDOE36 | [gemsdoe36-anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros.tif](https://github.com/buffedlizard55-lab/GEMSDOE36/raw/b90418f852615aa0974cf9a53b92fa569ed133fc/docs/downloads/gemsdoe36-anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros.tif) | 0.2750 | Not estimable | **No; DO NOT SUBMIT** |

“Unique: No” reflects the saved nine-site audit and the current literal witness stop. The
links are direct access to historical upstream bytes for reproducibility only, not an upload
recommendation. A local format check or published owner score is not a receipt.

### Why GEMSDOE32's reported 0.2778 is plausible—but unproved

The saved byte-level analysis reports the GEMSDOE32 B2 positive support as an exact subset of
the GEMSDOE28 H27-4 base, with 2,545 cells removed near a mirrored catalogue. Under the
competition's false-positive penalty, pruning low-credit dots could improve a distance-weighted
Tversky score if useful coverage remains. That is a plausible metric mechanism, **not a proven
causal explanation**: the 0.2778 remains an owner report, the hidden labels are unavailable,
and no verified portal receipt ties the number to those bytes. See
[`content/why-0.2778.md`](content/why-0.2778.md),
[`evidence/pair_identification.json`](evidence/pair_identification.json), and the
[official metric page](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/).

## Current public leaderboard feed (2026-10-28)

The official public leaderboard page displayed rank 1 **0.4544**, rank 25 **0.3217**,
rank 26 **0.3195**, and rank 48 **0.2895** in the 2026-10-28 observation. Thus 0.3195 is
not the current top value in that capture. These are public-test scores for other entries,
not a score for any file in this repository, not private-test results, and not receipts.
The [snapshot](evidence/leaderboard_observation_2026-10-28.json) records the date and
precision; [`registry/leaderboard.json`](registry/leaderboard.json) is the scheduled feed
snapshot. The Pages workflow refreshes the public leaderboard feed every six hours and
retains the last successful observation marked stale if a refresh fails.

## Official-source checks and access limits

The public competition description and official rules, public leaderboard, USGS GeoDAWN,
DOE GDR #1391, USGS 3DEP, and USGS Landsat Collection 2 pages were checked on 2026-10-28.
Source-by-source facts, scope, and caveats are stored in
[`evidence/official_source_check_2026-10-28.json`](evidence/official_source_check_2026-10-28.json).

- Official DTI: α=0.2, β=0.8, 300 m triangular kernel. Required raster: single-band float32,
  EPSG:32611, 100 m, [0,1], and null/NaN outside the bounds. The text requirement is not
  proof of portal acceptance.
- The September 2026 official rules state three submissions per week per entity, one final
  submission across both prize rounds, and disclosure of generative-AI use in the narrative.
- **Deadline conflict:** the competition home page lists 2026-12-03 at 23:59 UTC; Appendix
  A.1 of the rules states 5:00 p.m. ET on the deadline date. The effective cutoff is
  unresolved; use the earlier time unless the organizer confirms otherwise.
- The submission and data pages redirected to login. The account quota, data download access,
  and any upload receipt could not be checked. The local feature stack is an owner mirror,
  not an authenticated organizer download.
- USGS identifies GeoDAWN's magnetics/radiometrics and line products, with terrain-clearance
  caveats; GDR #1391 lists geothermal/geochemical layers under CC BY 4.0; 3DEP describes
  public products; Landsat Collection 2 documents reflectance/temperature products. These
  page checks do not establish exact AOI coverage or suitability of local files.

## Research hypotheses (preregistered; **none tested**)

Ranks are qualitative research priority, not score projections. Full mechanisms, layers,
repository-difference checks, named non-fault mimics, costs, and data-access status are in
[`knowledge/preregistration-2026-10-28.md`](knowledge/preregistration-2026-10-28.md) and
[`evidence/preregistration_2026-10-28.json`](evidence/preregistration_2026-10-28.json).

1. **H1-RMIX — Local radiometric mixing-manifold residual.** K–Th–U–total-count local
   compositional closure residual at independently supported concealed structures. Mimic:
   non-fault lithologic/weathering contacts or survey leveling/clearance.
2. **H2-XCATCH — Cross-catchment channel-profile discontinuity.** Area/lithology-conditioned
   paired channel-profile breaks with independent geophysical orientation. Mimic: resistant
   bedrock or nontectonic base-level change, plus human drainage edits.
3. **H3-ANISO-THERM — Sampling-corrected anisotropic shallow thermal evidence.** Compare a
   density-normalized anisotropic kernel to a matched isotropic baseline. Mimic: sparse
   sampling near known springs/wells or basin/lithologic heat effects.
4. **H4-XOVER — Airborne acquisition-crossing repeatability.** Require independent crossing
   GeoDAWN lines to repeat anomalies after line-level corrections. Mimic: real non-fault
   lithologic contacts, tie-line leveling, flight-line striping, terrain clearance.
5. **H5-LANDSAT — Landsat surface-alteration texture conditioned on structure.** Test
   season-matched, cloud-screened surface alteration textures only with independent structural
   corroboration. Mimic: host lithology/soil, moisture, vegetation, mine disturbance, playa.

## Locked safeguards and release status

- Remain in one assigned method lane. Surface rank-correlation is checked before placement;
  stop if absolute Spearman exceeds 0.90. Stop/log a duplicate if more than 70% of final dots
  fall within 3 px of any registry raster.
- Use the shared cached feature stack, `evaluate_holdout.py`, and `submission_writer.py`;
  do not fork. Hold out whole fault segments with a buffer, derive catalogue features only
  from visible faults, and pixel-exactly mask visible faults. Use pooled DTI with the official
  α=0.2, β=0.8, 300 m triangular kernel.
- Test each feature alone for leakage. AUC >0.90 is leakage until proven otherwise.
- Label every score `HOLDOUT-DTI` with evaluator version, withheld-positive count, and 95% CI,
  or `ORGANIZER-CONFIRMED` only from a verifiable receipt. A projection is never a score.
- Maximum three geological experiments or two hours, whichever comes first. No slot selection
  in this research lane; the separate selector must check the portal's weekly cap.
- End an eligible run with one JSON run card including hypothesis, mechanism, mimic, holdout
  and CI, registry correlation/overlap, raster SHA-256, validator results, submission name and
  ≤140-character note, and a `promote` or `negative` verdict. Negative results are deliverables.
- This review's card is negative: **0 experiments, 0 holdout runs, 0 candidate rasters,
  0 selector actions, 0 weekly slots used**. The shared cache/tool runtime was not restored.

## Build and test

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/build_site.py
.venv/bin/python scripts/check_site.py
.venv/bin/python -m pytest -q
```

The site builder renders only the current fail-closed decision. `scripts/build_site_v3.py`,
`scripts/build_release_gate_v2.py`, and `scripts/build_evidence_page.py` are blocked retired
positive paths. The scoped FCHD and AMDC archives remain negative. Do not generate a TIFF or
run a holdout while the literal witness stop remains unresolved.

## Three review passes and remaining work

The current review performed three passes: (1) preregistered five hypotheses and rendered a
negative, source-bound executive/site summary; (2) removed positive build/check/test paths and
checked lane safeguards; (3) fetched official sources, refreshed the dated public leaderboard
observation, and rechecked the task against the prompt and exact release contract. Details and
limitations are in [`knowledge/review-2026-10-28-session.md`](knowledge/review-2026-10-28-session.md).

Next: resolve the dense-witness protocol interpretation through documented evidence, verify
organizer access/provenance and current portal deadline/quota, restore the shared cache and
runtime, then run the existing preregistered protocol only if eligible. Do not spend a slot or
claim a score before that separate selector step.

## Standing task prompt and project brief (preserved for future sessions)

The original chat prompt in full is not independently recoverable from the repository history;
this section preserves the complete task brief available in the current session and the stored
operational requirements. Do not relabel this reconstruction as an authenticated verbatim
transcript. The current decision and explicit safeguards above govern when requirements conflict.

<details>
<summary>Full task brief and standing requirements</summary>

> Review the repository and continue the GEMS competition project, focusing on GEMSDOE24, 25,
> 27, 28, 30, 31, 32, 33, and 36. Explain the reported GEMSDOE32 result, maintain an auditable
> executive summary and submission guide, develop and rank 3–5 distinct geological hypotheses,
> and test the best eligible candidate using the shared holdout tooling before any separate
> submission-slot selection. Provide official-source references, an up-to-date feed, three
> implementation/review passes, preserve this prompt in README, and prepare a PR merged to main.
>
> Focus-site owner/user reports (not verified receipts): GEMSDOE24 0.2477; GEMSDOE25 0.2600;
> GEMSDOE27 0.2449; GEMSDOE28 0.2710; GEMSDOE30 0.2600; GEMSDOE31 0.2708;
> GEMSDOE32 0.2778; GEMSDOE33 0.2632; GEMSDOE36 0.2750. Existing estimates and “best”
> selections must be rechecked for evidence and status.
>
> **Parallel-run protocol:** remain in the assigned single method lane; test surface rank-
> correlation before placement and final-dot overlap; stop and log a duplicate if correlation
> exceeds 0.90 or more than 70% of dots are within 3 px of a registry raster.
>
> Reuse the shared cached feature stack, `evaluate_holdout.py`, and `submission_writer.py`; do
> not fork shared tools. Hold out whole fault segments with a buffer, derive catalogue-based
> features only from visible faults, pixel-exactly mask visible faults, and use pooled DTI
> (α=0.2, β=0.8, 300 m triangular kernel). Test each feature alone for leakage; AUC >0.90 is
> leakage until proven otherwise. Label every score as HOLDOUT-DTI with evaluator version,
> withheld-positive count, and 95% CI, or ORGANIZER-CONFIRMED from a receipt. A projection is
> never a score.
>
> End research with one JSON run card containing hypothesis, mechanism, named non-fault mimic,
> holdout DTI/CI, registry correlation/overlap, raster SHA-256, validator checks, submission
> name/note (≤140 characters), and promote/negative verdict. Negative findings are deliverables.
> Maximum three experiments or two hours; do not select a real slot. Promotion is a separate
> selector step subject to the portal's weekly cap.
>
> Requirements also include a unique format-valid GeoTIFF, [0,1] predictions, matching CRS/
> shape/transform, easy download, clear filename/note, automated validation, three review
> passes, verified official sources, current feed, PR plus merge, and the full prompt preserved
> in README. These requirements do not override the lane's duplicate stop or experiment/
> selector safeguards. Keep **Maximize P(Win)** and **Own the Outcome** central.

</details>

## Historical lane records

Older work is retained for audit, not clearance: [FCHD-NCM](docs/fchd/index.html),
[AMDC](docs/amdc/index.html), [ADJDIS](evidence/adjdis_run_card.json), [KHD](evidence/khd_run_card.json),
[SGCE/Session 2](evidence/session2_run_card.json), [LBCAL research-only dossier](docs/lbcal/index.html)
([findings](knowledge/lbcal-findings-2026-10-27.md)), and earlier repository reviews are all scoped research records. None overrides the current
project-wide `DO-NOT-SUBMIT` gate. Historical TIFFs are inventoried in
[`docs/downloads/LEGACY-DO-NOT-SUBMIT.txt`](docs/downloads/LEGACY-DO-NOT-SUBMIT.txt).

---

# Standing task prompt (preserved for every session)

Read this section at the start of every work session. It is the authoritative statement of what
we are building and why. Core values: **Maximize P(Win)** and **Own the Outcome**.

## Focus

I want to focus on the highest scoring submissions from the following sites:
GEMSDOE24, GEMSDOE25, GEMSDOE27, GEMSDOE28, GEMSDOE30, GEMSDOE31, GEMSDOE32,
GEMSDOE33, GEMSDOE36.

I want an executive summary on every site that is clear and obvious which is the best submission
to submit to obtain a high score on the leaderboard. It should also be unique and not an exact
duplicate of any previous submission that is the same as below. Keep iterating and testing until
we have the highest scoring submission to download and submit.

We should be able to estimate the score for a submission. I want a table in the executive summary
that clearly lists what file to download, what the estimate score is, and whether it is a unique
submission unlike any of the other GEMSDOE sites listed below.

## Highest urgency — MUST FOLLOW

MUST GENERATE A UNIQUE TIF SUBMISSION FOR THE COMPETITION. DO NOT COPY A PREVIOUS SUBMISSION
UNLESS IT'S FOR LEARNING AND EDUCATION. BUT WE MUST GENERATE A UNIQUE TIF SUBMISSION. IT MUST
BE OBVIOUS WHETHER IT IS OK TO DOWNLOAD AND SUBMIT THE GENERATED TIF SUBMISSION.

There should be an easy to download submission tif file as described by the prompt. Read the
entire prompt. A lot of sites mention inspection only and a human inspector, but the inspection
needs to be done through the project and needs to be validated for submission without human
intervention.

## Parallel-run protocol

1. LANE. Your lane is the single method paragraph below. Stay inside it. If your raster's
   rank-correlation with any registry raster exceeds [0.90], or more than [70%] of your dots fall
   within 3 px of one registry raster's dots, you have drifted into another lane: log it as a
   duplicate and stop. Check this on the surface before placement AND on the final dots.
2. REUSE, DON'T REBUILD. Use the template's cached feature stack, evaluate_holdout.py and
   submission_writer.py. Holdout = hide-and-recover: withhold whole fault segments with a buffer,
   derive every catalogue-based feature only from the visible faults, mask visible faults
   pixel-exactly, score pooled DTI (alpha 0.2, beta 0.8, 300 m triangular kernel). If a shared
   tool is wrong, fix it once in the template and report it; never keep a private fork.
3. LABEL EVERY NUMBER as HOLDOUT-DTI (evaluator version, number of withheld positives, 95% CI)
   or ORGANIZER-CONFIRMED (copied from a submission-page receipt). A projection is never written
   as a score.
4. LEAKAGE CANARY. Test each feature alone on the holdout before trusting any result. AUC above
   [0.90] means leakage until proven otherwise.
5. RUN CARD. End with one JSON card: hypothesis; mechanism; the named non-fault process that
   could mimic it; holdout DTI + CI; correlation/overlap vs registry; raster sha256; validator
   output (no NaN inside the footprint, values in [0,1], CRS/shape/transform match); submission
   name + note of at most 140 characters; verdict promote / negative. Negative results are
   deliverables.
6. BUDGET. Stop after [3] experiments or [2] hours. Do not pick submissions: promotion to a real
   slot is a separate selector step, within the weekly cap shown on the submission page.

## Sites to study (starting point for understanding TIF generation)

GEMSDOE32: h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros: 0.2778
GEMSDOE: gems-submission-20260925T001403Z-7f00890a: 0.1563
6GEMSDOE: gems6_hgb88-topk03_33cec71ff0: 0.0286
GEMSDOE3: pindrop-v4-nodes-...: 0.1193 / pindrop-v4-discovery-...: 0.0830 / pindrop-v4-ridge-...: 0.1152
GEMSDOE2: gemsdoe2-dual-family-union-...: 0.1560
GEMSDOE4: gems-submission-20260926T163915Z-237f0063: 0.0343
5GEMSDOE: gems-submission-20260926T175114Z-7f00890a: 0.1563
7GEMSDOE: lidarscarp-ridge-top2pct-36c3a3f341c8: 0.1461
8GEMSDOE: Hedge-v2_submission: 0.1563
GEMSDOE9: 2314b599: 0.0107
11GEMSDOE: gems-structural-area06-v1: 0.0202
12GEMSDOE: r7-nms3-dem10-scarp_0c9199f14e62: 0.1294
15GEMSDOE: gems-tso1-20260929T005627Z-conj_alteration_mag: 0.0782
14GEMSDOE: GEMS_r5-geom-horse-ensemble_...: 0.0020
17GEMSDOE: 17GEMSDOE_F-ensemble-2pct_20260930T050626Z: 0.0187
18GEMSDOE: H19-C_20260930T212401Z_c11e495e: 0.0297
19GEMSDOE: h19-4-multiline-corroborated-openness-thermal-pop-...: 0.1894 / h19-5-powerlaw-budget-multiline-corroborated-...: 0.1922
GEMSDOE10: h16-continuation-...: 0.0461 / h20-dem10-scarp-thin-...: 0.0921 / H25-ctx-ridge-...: 0.1280 / h28-dotted-ridge-...: 0.1839
13GEMSDOE: 20261001_r13-lattice-s5_v2_nan-outside: 0.0904
16GEMSDOE: h16-1-topo-geophys-baseline-ridges-...: 0.1855 / h18-3a-topo-geophys-x-complexity-prior-...: 0.0976 / h18-4-usgs-geologic-map-faults-gap-...: 0.0360
GEMSDOE21: h19-4-reference-20260930-691e4dfa: 0.1894
20GEMSDOE: h20-1-sarnnpu-powerlaw-pi0363-tilt-wingcrack-...: 0.1890 / h20-5-continuous-pu-proxy-unverified-...: 0.1859
GEMSDOE22: h23-a-dti-optimal-emission-6pct-...: 0.1002 / h23-b-dti-optimal-emission-10pct-...: 0.0748
GEMSDOE23: h30-arrangement-matched-habitat-...: 0.1352
GEMSDOE24: h25-1-dotted-h19-5-d1-5-...: 0.2477
GEMSDOE25: dotted-h19-5-d2-8-...: 0.2600
GEMSDOE26: dilcond-oof-v1-...: 0.1223
GEMSDOE27: topo-gap-closure-t-v2-on-d1-5-...: 0.2449
GEMSDOE30: d28-poisson300m-offcat-44090-...: 0.2600
GEMSDOE31: h27-4-solo-d28-...: 0.2708
GEMSDOE32: h33-h33-2-b2-...: 0.2778
GEMSDOE33: h33d-analog-tip-stepover-r30-...: 0.2632
GEMSDOE36: anderson-geothermal-pinn-38854-...: 0.2750

Current competition leaderboard GEMSDOE high score: 0.4413 (also cited: 0.3195).

## Key question

Why and how did GEMSDOE32 (h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros: 0.2778) get the highest
score, and are we able to generate a submission that scores higher than 0.2778?

Answer using PhD-level experience, knowledge, and judgement. Then use the answer to generate a
unique TIF submission into the competition. Must be unique submission unlike any within the
GEMSDOE sites above. Verify working line by line, no hallucinations.

## Required outputs

1. Executive summary subpage explaining exactly how to make a submission into the contest.
   Table listing: file to download, estimate score, unique submission verdict.
2. Unique TIF submission — easy to download, clear whether OK to download and submit.
   Values must be in [0,1] (fixes "Predicted values must be in range [0, 1]" portal error).
   Unique name and short comment (≤140 chars, e.g. clustering with k=25).
3. 3–5 candidate geological hypotheses not yet tried, each naming: specific layer(s), physical
   signature, why it catches a fault missing from USGS/INGENIOUS catalogue, how it differs from
   repo code. Rank by expected DTI improvement and implementation cost. Validate top candidate on
   spatially-blocked holdout before touching a weekly submission slot.
4. Work line by line verifying from official verified trusted sources; provide links for manual
   review; no manual input; no hallucinations; flag irregularities.
5. Store all information from official verified sources; contrarian but smart approaches;
   find overlooked data sources for geothermal vent discovery.
6. Put this prompt into the repo README and read it every time we work on the project.
7. Generate submission system that can score higher than 0.3195 (current cited high).
8. Create a PR and merge onto main; suggest remaining work and limitations.

## Competition references

- https://www.drivendata.org/competitions/306/competition-doe-gems/
- https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/
- https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/
- https://www.drivendata.org/competitions/306/competition-doe-gems/data/
- https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/
- https://github.com/drivendataorg/gems-prize-reference-solution
- https://docs.nlr.gov/docs/fy26osti/96647.pdf
- https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and
- https://gbcge.org/current-projects/ingenious/
- https://gdr.openei.org/submissions/1391
- https://epsg.io/32611
- https://en.wikipedia.org/wiki/Tversky_index

## Known access limitation

No DrivenData auth → cannot auto-download training_features.tif, labels.tif,
sample_submission.tif, 1m_DEM_links.csv from the data tab (verified redirect to login).
The project restores a hash-pinned public GitHub mirror instead; mirror bytes establish byte
identity, not organizer provenance.

## Core values

- Maximize P(Win): weigh tradeoffs, assess risk, choose the path that maximizes the probability
  of winning. Set emotions aside.
- Own the Outcome: own results end to end. When problems arise and we have the means to act, do
  so without waiting for permission. Treat failure and success as signals.
