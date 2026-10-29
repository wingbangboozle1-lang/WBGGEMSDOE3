# GEMS Field Notes — GEMS fault-mapping review

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
