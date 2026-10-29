# Repository review — Arena session 3b056688 — 2026-10-29

## Executive decision

**DO NOT SUBMIT.** The current literal registry-witness stop remains binding. No GeoTIFF was generated or approved; no geological experiment, feature canary, new HOLDOUT-DTI, score estimate, candidate validator, or selector action was run. The current machine-readable decision is [`evidence/session_3b056688_run_card.json`](../evidence/session_3b056688_run_card.json). The only current candidate decision is **none**; there is no safe-to-download-and-submit file.

The review was limited to repository evidence, an official public-page refresh, software/site maintenance, and the requested three-pass review. It did not select a weekly submission slot. **Maximize P(Win)** and **Own the Outcome** are served here by refusing to promote an unsupported artifact or score.

## Pass 1 — synthesize the evidence and explain GEMSDOE32

### Nine pinned focus sites

The nine historical files and their highest pinned owner/user-reported values are summarized in [`README.md`](../README.md) and the generated [executive summary](../docs/executive-summary.html). Values are **OWNER-REPORTED / UNVERIFIED**, not organizer receipts. No reliable estimate for a new file is available. The site comparison's historical rasters are research references; none is authorized for download-and-submit.

| Site | Owner/user report | Estimate for a new file | Unique / disposition |
|---|---:|---|---|
| GEMSDOE24 | 0.2477 | Not estimable | No — research only |
| GEMSDOE25 | 0.2600 | Not estimable | No — research only |
| GEMSDOE27 | 0.2449 | Not estimable | No — research only |
| GEMSDOE28 | 0.2710 | Not estimable | No — research only |
| GEMSDOE30 | 0.2600 | Not estimable | No — research only |
| GEMSDOE31 | 0.2708 | Not estimable | No — research only |
| GEMSDOE32 | 0.2778 | Not estimable | No — research only |
| GEMSDOE33 | 0.2632 | Not estimable | No — research only |
| GEMSDOE36 | 0.2750 | Not estimable | No — research only |

The byte audit measures the candidate-to-focus directed overlap within three pixels; each historical entry fails the repository's nine-site uniqueness criterion. That focus-only audit is not a complete registry clearance. Separately, the active literal witness is positive on all 5,167,373 cells of the mirrored sample footprint. Under the recorded finite-positive support rule, every nonempty in-footprint map has conditional 100% directed overlap with it. This is a stop under the user's current written rule, while its dependence on owner-mirrored bytes and incomplete portal-registry provenance remains explicit.

### GEMSDOE32's reported 0.2778

The pinned GEMSDOE32 B2 raster contains 37,654 positive cells. Its support is an exact subset of the pinned 40,199-cell GEMSDOE28 H27-4 base: 2,545 cells were removed and none added. The removed cells are reported 1.414–2 pixels from the mirrored fault catalogue. The owner-reported score rises from 0.2708 on the base to 0.2778 on B2, a claimed +0.0070; the score-to-byte link and hidden labels are not independently verified.

A plausible mechanism is metric-based pruning: the official distance-weighted Tversky score penalizes false-positive prediction mass, while its 300 m triangular kernel gives nearby predictions some credit. Deleting redundant or low-credit pixels close to the catalogue could reduce false-positive contribution while retaining much of the distance-tolerant coverage. That is **not a causal finding**. The evidence cannot distinguish false-positive reduction from lost true-positive credit, identify a numeric break-even density, or prove that pruning produced the reported score. Staff clarification that known-fault pixels are excluded does not imply that all nearby pixels are excluded. Full caveats and the historical holdout caveat are in [`content/why-0.2778.md`](../content/why-0.2778.md) and [`evidence/pair_identification.json`](../evidence/pair_identification.json).

### Prior method-lane evidence is not a release decision

These entries are carried forward from their individual cards; none is an organizer score and none overrides the current global stop:

- **HCE-1:** the fold-local E4 method result was `HOLDOUT-DTI = 0.129213` (evaluator `GEMSDOE32-HIDE-RECOVER-v3.0`, 22,232 withheld positives, 95% CI [0.116024, 0.142575]). The actual saved/repaired raster's separate static read-back was `HOLDOUT-DTI = 0.093134` (same evaluator/count, 95% CI [0.082389, 0.103673]). These are distinct measurements; the higher method-level result must not be attributed to the released bytes. HCE's own card reports content-aware uniqueness but literal-witness failure.
- **CSPES:** `HOLDOUT-DTI = 0.025652` (evaluator `GEMSDOE32-HIDE-RECOVER-v3.0`, 22,232 withheld positives, 95% CI [0.019366, 0.031916]); paired delta versus the saved 0.099202 incumbent proxy is −0.073550 (95% CI [−0.088320, −0.058663]). Negative lane result.
- **LBCAL:** `HOLDOUT-DTI = 0.0631` (evaluator `GEMSDOE32-HIDE-RECOVER-v3.0`, 22,232 withheld positives, card CI [0.0513, 0.0765]); negative. Its reported cross-fit 0.5012 is an **ESTIMATE**, not a score. Its saved analysis shows the hide-and-recover/public-score relation is weak (ρ=0.089), despite much stronger family-CV/public-score relation (ρ=0.914); do not use its leaderboard inversion as a calibrated projection. The separate lane/decision cards differ in some precision and overlap fields, so retain their individual scopes rather than combining them.
- **FCHD-NCM:** selected E2 `HOLDOUT-DTI = 0.097024` (evaluator `GEMSDOE32-HIDE-RECOVER-v3.0`, 22,232 withheld positives, 95% CI [0.087257, 0.106516]); paired delta versus its GEMSDOE32 hide-and-recover baseline is −0.002179 (95% CI [−0.012192, 0.008389]), so the superiority gate fails. The lane reports 72 leakage canaries with max AUC 0.74318 and max non-lattice 3-px overlap 0.635, but neither clears the project-wide literal witness. Its LBCAL-Physics 0.0927 and SGMC-Cal 0.05024 are **ESTIMATES**, not scores.

The five preregistered geological hypotheses remain qualitative, untested priorities—not score projections. No new hypothesis test was run because the uniqueness stop binds, and the checkout contains only `data/template_grid.tif`: no shared `.cache`, authenticated labels, or restored shared feature stack.

## Pass 2 — refresh the public feed and maintain the submission guide

The official DrivenData public leaderboard page was fetched in chunks on 2026-10-29. The new date-only observation records rank 1 = 0.4544, rank 2 = 0.3916, rank 25 = 0.3330, rank 26 = 0.3328, rank 47 = 0.3195, and rank 48 = 0.3180. The retrieval interface exposes no exact fetch timestamp. The previous 2026-10-28 rows at ranks 25/26 are now historical; the user-supplied 0.3195 is not the leader. These are public leaderboard observations, not repository-file scores, private-test results, or receipts.

The new snapshot is [`evidence/leaderboard_observation_2026-10-29.json`](../evidence/leaderboard_observation_2026-10-29.json); the local feed is [`registry/leaderboard.json`](../registry/leaderboard.json). The automated six-hour feed workflow was inspected but not invoked in this environment. The feed JavaScript now handles date-only observations without incorrectly treating midnight on the capture date as the exact fetch time; a future automatic refresh records its UTC request-start timestamp and separately retains the dated manual snapshot.

The README, generated site, and submission guide continue to state **DO NOT SUBMIT** and give no direct TIFF download. The guide documents the format and receipt steps for a future eligible submission, but no filename or upload note is assigned to a candidate. The official metric/format/rules/geology-source review remains the 2026-10-28 audit; only the public leaderboard was re-observed on 2026-10-29. Written format requirements do not prove portal acceptance. Login-gated account quota, official input access, accepted uploads, and receipts remain unknown. The deadline discrepancy between the competition home page and September 2026 rules remains unresolved.

## Pass 3 — adversarial code, gate, and evidence verification

The active site builder now consumes the 2026-10-29 run card and immutable leaderboard observation, binds both the current run card and feed/review hashes into the negative release gate, and renders the latest successfully captured tracked ranks. The site checker and tests were updated to verify the new paths, date, feed copy, no-candidate invariants, evidence labels, local links, and absence of TIFF download links. Historical site data and lane cards remain dated research records; they are not substituted for current authority.

The current stop was not weakened. The 5,167,373/5,167,373 witness count is conditional on a SHA-pinned owner mirror and the repository's positive-support convention; it is not proof that the mirror is organizer-authenticated or that the portal registry is fully inventoried. No correlation was computed without a surface. No final-dot overlap or new format validation was run without a candidate.

### Experiment, validator, and slot accounting

- New geological experiments: **0 / 3**; experiment time: **0 / 2 hours**.
- New HOLDOUT-DTI runs: **0**; no evaluator version, count, value, or CI is claimed for this review.
- New candidate GeoTIFFs / candidate SHA-256 values: **0 / none**.
- Candidate validator runs: **0**; no file is cleared for submission.
- Selector actions / weekly slots used: **0 / 0**; organizer receipts: **none**.
- Current project decision: **DO NOT SUBMIT**; do not download any historical artifact for submission.

### Verification results

- `python scripts/build_site.py && python scripts/check_site.py`: **PASS**. The negative site and scoped archives were regenerated; the release decision is hash-bound, no candidate download link is published, and all local site links resolve.
- `.venv/bin/python -m pytest -q`: **237 passed, 4 skipped**; 72 Rasterio pending-deprecation warnings. Pytest was installed in the ignored local virtual environment from the repository's existing `requirements.txt`; no dependency manifest was changed.
- `python -m py_compile` for the modified builder/checker/feed/test modules: **PASS**.
- `git diff --check`: **PASS** (run after the final edits).
- The automated network feed refresh and portal workflows were **not invoked**. The leaderboard snapshot is the recorded date-only page retrieval, not a live scheduled refresh.

These are software/site checks only; they are not a geology result, score, registry-provenance finding, portal-acceptance result, or submission authorization.

## Remaining work and limitations

1. Resolve the literal dense-witness issue only through a documented, evidence-based correction to the protocol or authenticated registry evidence; do not silently exempt the witness or waive the threshold.
2. Once and only if the stop is resolved, recover organizer-authorized data and the shared cache/runtime, confirm the assigned single method lane, then execute the pre-registered protocol with the shared evaluator/writer, buffered whole-fault-segment holdouts, visible-fault-only catalogue features, pixel-exact visible-fault masking, per-feature leakage tests, registry correlation/overlap, and a candidate-specific validator.
3. Keep `HOLDOUT-DTI` separate from projections and organizer-confirmed values; the latter requires a verifiable receipt linking exact uploaded bytes to the score.
4. Ask the organizer to resolve the homepage-versus-rules deadline conflict and verify the authenticated account's actual quota. Neither login-gated page was available here.
5. Do not select a weekly submission slot in the research lane. A separate selector is required only after all scientific, uniqueness, format, provenance, and receipt safeguards can be satisfied.

## Official-source references

- [DrivenData public leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/) — fetched 2026-10-29; date precision only.
- [DrivenData metric and submission format](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/) — official public page; α=0.2, β=0.8, 300 m triangular support and written GeoTIFF constraints.
- [DrivenData competition homepage](https://www.drivendata.org/competitions/306/competition-doe-gems/) and [September 2026 official rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf) — source of the unresolved deadline conflict and submission rules.
- [Official reference solution](https://github.com/drivendataorg/gems-prize-reference-solution) — repository reference; no code/data downloaded in this review.
- Source-by-source checks for [GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and), [DOE GDR #1391](https://gdr.openei.org/submissions/1391), [USGS 3DEP](https://www.usgs.gov/3d-elevation-program), and [Landsat Collection 2](https://www.usgs.gov/landsat-missions/landsat-collection-2) are retained in [`evidence/official_source_check_2026-10-28.json`](../evidence/official_source_check_2026-10-28.json). These pages do not authenticate local mirrored files or prove AOI coverage.
