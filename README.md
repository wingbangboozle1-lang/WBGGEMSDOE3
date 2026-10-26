# WBGGEMSDOE3 — DOE GEMS submission research

> **Session-start rule:** read this entire README and [`research/repo-review-2026-10-26.md`](research/repo-review-2026-10-26.md) before doing project work. The hard stop and evidence rules below are part of the project, not optional suggestions.

## Executive decision — no submission is cleared

**Do not download or submit a TIFF from this checkout. No new TIFF was generated.** The repository at the start of this review contained only this README: no competition rasters, cached features, sample submission, registry, evaluator, submission writer, validator, or tests. Without those inputs and the shared tools, a spatial holdout, leakage canary, uniqueness audit, and format validation cannot be run honestly.

The strongest *historical reference* among the nine focus sites is GEMSDOE32's `h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros` (`0.2778`, **OWNER-REPORTED; no submission-page receipt was present in the reviewed material**). It is an old H19-5-family derivative, not a new candidate, and the other project records report it as non-unique. **It is not approved for re-download or re-submission.** The present project has no score estimate for a new candidate.

Current status, the per-site table, the source/provenance notes, and the negative run card are on the [executive summary](executive-summary.html), [submission guide](submission.html), [research hypotheses](hypotheses.html), and [review report](research/repo-review-2026-10-26.md). Machine-readable records: [nine-site comparison](reports/focus-sites-2026-10-26.json) and [negative run card](reports/negative-run-card.json).

## Standing project brief

### Mission

Build an auditable research and submission workflow for DrivenData DOE GEMS fault prediction. Improve the probability of a strong leaderboard result through defensible geological hypotheses, official/free data, leakage-resistant spatial validation, reproducible output generation, and an obvious fail-closed decision about whether a TIFF may be submitted. Make the public project site simple to use and keep its evidence current.

The requested focus sites are **GEMSDOE24, GEMSDOE25, GEMSDOE27, GEMSDOE28, GEMSDOE30, GEMSDOE31, GEMSDOE32, GEMSDOE33, and GEMSDOE36**. The historic leaderboard records supplied in the request are a starting point only; they are not organizer receipts. The prompt itself gives conflicting global leaders (`0.3195` and `0.4413`). A GEMSDOE32 repository snapshot later records `0.4437` at `2026-10-26T21:20:39Z`; that is an owner-maintained observation, not independently fetched here. See the report for the discrepancy and its provenance.

### Non-negotiable working protocol

1. **Single lane only.** Use only an explicitly supplied, pre-registered method paragraph. If no method/lane is specified, do not infer one from another site and do not run an experiment. Stop and record the blocker. Before placement and again on final dots, compare against the registry. Stop and mark duplicate if absolute rank-correlation is above `0.90` or more than `70%` of the candidate's dots fall within `3 px` of a registry raster.
2. **Reuse, do not rebuild.** Use the shared cached feature stack, `evaluate_holdout.py`, and `submission_writer.py`. Do not copy another site's TIFF or maintain a private fork of shared tools. If a shared tool is defective, repair it in its canonical template and report the change. This checkout currently has no such template/tools.
3. **Holdout definition.** Hide whole fault segments with a buffer. Derive every catalogue-based feature from visible faults only, mask visible fault pixels exactly, then score pooled DTI with `alpha=0.2`, `beta=0.8`, and a `300 m` triangular kernel. A random pixel split is not an acceptable substitute.
4. **Leakage canary.** Test every feature alone on the same holdout first. An AUC above `0.90` is leakage until proven otherwise.
5. **Evidence labels.** Label a metric as `HOLDOUT-DTI` with evaluator version, number of withheld positives, and a `95% CI`, or as `ORGANIZER-CONFIRMED` only when copied from a submission-page receipt. A model projection is never a score. If a historic site score has no visible receipt, call it `OWNER-REPORTED (unverified)` and do not imply organizer confirmation.
6. **Run card.** Record hypothesis, mechanism, a named non-fault mimic, holdout DTI and CI, correlation/overlap against registry, raster SHA-256, validator output (footprint NaN check, range `[0,1]`, CRS/shape/transform), submission name/note (note at most `140` characters), and verdict `promote` or `negative`. A negative result is a deliverable.
7. **Budget and selector.** Stop after at most `3` experiments or `2` hours. Do not spend a weekly submission slot until the candidate beats the current holdout best. A separate selector handles promotion and the weekly cap; an experiment does not select itself.
8. **Submission safety.** Never label a file “OK to submit” unless all gates pass automatically. No manual visual inspection substitutes for validation. A portal upload/slot decision is not performed from this repository; organizer authentication and the current weekly quota are not available here.
9. **No fabrication.** Do not copy a previous submission as a competition entry, invent a score, call a projection a score, or create a “valid” TIFF without the actual sample grid and source data.

### Values

- **Maximize P(Win):** choose work by expected evidence-backed value, not enthusiasm or sunk cost.
- **Own the Outcome:** report negative results, provenance conflicts, missing inputs, and broken gates clearly; fix shared issues only in the shared template.

## What this repository actually contains

At the reviewed base commit (`891b84e8ed7771a98bffc2041bd291dfedf9e15e`), `git ls-files` contained only `README.md`. This project has no `data/` input files, cached feature stack, `scripts/download_competition_data.sh`, `scripts/prepare_data.py`, `scripts/evaluate_holdout.py`, `scripts/submission_writer.py`, registry rasters, validation suite, or prior project code. `rasterio` is also not installed in the current environment. As a result:

- no candidate TIF can be generated or validated against the competition sample;
- no candidate holdout DTI, leakage AUC, score estimate, or registry novelty measurement can be calculated;
- there is no basis to say that a new file is safe to download or submit.

This is a **negative, fail-closed decision**, not a claim that a better method is impossible. Do not work around it by copying a file or private tooling from a sibling site.

## Official sources and review links

These links were supplied in the project request. The GitHub reference repository was reachable and inspected; the non-GitHub sources were not fetched in this sandbox, so their current contents/accessibility are not independently verified here.

- [DrivenData competition](https://www.drivendata.org/competitions/306/competition-doe-gems/)
- [Problem description and submission task](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)
- [About page](https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/)
- [DrivenData data tab (login may be required)](https://www.drivendata.org/competitions/306/competition-doe-gems/data/)
- [Official DrivenData reference solution](https://github.com/drivendataorg/gems-prize-reference-solution) — inspected at commit `aebe92f7c8a990f0e3443451b7a825d9afd6336b`; its README says the competition data must be downloaded from the competition site.
- [GEMS prize/submission guidance PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf)
- [USGS GeoDAWN data](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
- [DOE Geothermal Data Repository (GDR) submission 1391](https://gdr.openei.org/submissions/1391)
- [INGENIOUS project](https://gbcge.org/current-projects/ingenious/)
- [EPSG:32611](https://epsg.io/32611)
- [Tversky index](https://en.wikipedia.org/wiki/Tversky_index)

## Review workflow

- Read the [repo review and research plan](research/repo-review-2026-10-26.md).
- Check the [executive summary](executive-summary.html) for site-by-site historic records and the single current decision.
- Read the [hypothesis register](hypotheses.html) before any proposal; ideas are not results.
- Use the [submission guide](submission.html) only after a future run card says `promote`. Current state is `negative`; no TIFF is offered.
