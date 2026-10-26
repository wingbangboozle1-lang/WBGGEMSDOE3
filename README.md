# WBGGEMSDOE3 — auditable GEMS research

**Start every session here. [Executive summary](docs/index.html) ·
[Submission guide](docs/submission.html) · [Hypotheses](knowledge/hypotheses.md)**

## Current outcome (2026-10-26)

**NO TIFF CLEARED FOR DOWNLOAD OR SUBMISSION.** The initial repository was only
this README. This review restores shared code and evidence, not a trained model.
No new competition TIFF, holdout score, organizer receipt or weekly-slot use
exists. Do not upload a historical reference as a new submission. Do not mistake
our documentation PR for promotion of a candidate.

The required single-method lane paragraph is absent from the supplied task.
There is no local cached feature stack, physical channel dictionary, buffered
segment fold design or complete raster registry. Those are prerequisites, not
permission to fabricate predictions. We stopped before experiments as required.
See [preflight](evidence/preflight.json) and [run card](evidence/run-card.json).

## User task — persistent working requirements

The following is a structured restatement of the supplied prompt, **not a
verbatim transcript** (the full original remains in the Arena conversation).
Read this and the protocol before every session; any missing requirement must
be resolved against the original request, not silently relaxed.

* Review GEMSDOE24, 25, 27, 28, 30, 31, 32, 33 and 36. Provide per-site executive
  decisions, downloadable filename, score evidence/estimate and uniqueness.
* Generate a genuinely unique single-band competition TIFF, never just copy,
  rename or perturb a previous entry. Make download/submission readiness obvious
  at the start of the site. Values must be finite in [0,1]; exact sample CRS,
  shape and transform; unique name and note no longer than 140 characters.
* Stay in the assigned single-method lane. Stop as duplicate if rank correlation
  exceeds 0.90 or more than 70% of dots lie within 3 pixels of **any** registry
  raster. Check surfaces before placement and final dots afterwards.
* Reuse cached features, shared `evaluate_holdout.py` and `submission_writer.py`.
  Fix shared tools upstream rather than keeping private metric/writer forks.
* Hide whole fault segments with a buffer; recompute every catalogue-derived
  feature using visible faults only; mask visible traces pixel-exactly. Pool DTI
  components with α=0.2, β=0.8 and a 300 m triangular kernel.
* Report HOLDOUT-DTI with evaluator version, positive count and 95% CI, or
  ORGANIZER-CONFIRMED with an actual receipt. Never label a projection as a score.
  Keep user-reported historical values visibly outside accepted score evidence.
* Test each feature alone; AUC >0.90 is leakage until explained. Validate the top
  hypothesis on spatial holdout before using a slot. Beat the comparable current
  holdout best; a separate selector controls promotion under the actual weekly cap.
* Propose 3–5 ranked geological hypotheses before implementation: named layers,
  physical transform, why unmapped faults, repo differences, confounders and cost.
  Check official free external data are obtainable before calling them viable.
* End with a JSON run card: hypothesis, mechanism, named non-fault mimic,
  holdout/CI, registry correlation/overlap, raster SHA-256, validator, name/note,
  promote/negative verdict. Negative results are deliverables. Stop after three
  experiments or two hours, even though the broader prompt asks to keep iterating.
* Research geothermal relevance critically, archive evidence with official links,
  flag irregularities and inaccessible sources. Do not claim line-by-line
  verification of material not retrieved or tested. Automate project validation;
  no human visual inspector should be a release gate.
* Clean GitHub Pages site, executive-summary subpage, simple submission guide,
  current status feed with timestamps, no stale green banners or fake downloads.
* Use three passes: implement and verify; review assumptions/edge cases and fix;
  recheck against the task. Create a PR and merge it. Record outstanding work.
* Maximize P(Win): weigh tradeoffs and evidence rather than promising a leaderboard
  win. Own the Outcome: act on failures end-to-end, retain negative findings and
  never trade audit integrity for an apparently successful deliverable.

Historical values supplied in the prompt include 0.2778 for GEMSDOE32 and
conflicting overall highs 0.3195 / 0.4413. They are unverified user reports,
**not** local estimates or ORGANIZER-CONFIRMED scores. No higher score is promised.
The target is competition fault prediction relevant to geothermal exploration,
not a demonstrated direct geothermal-vent map.

## Reproduce this review

```sh
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest -q
.venv/bin/python scripts/build_site.py
.venv/bin/python scripts/audit.py preflight  # exit 2 = blocked, intentionally
.venv/bin/python scripts/audit.py raster candidate.tif data/sample_submission.tif
```

`audit.py raster` is an independent read-only format check, **not** a new writer
or scorer. `scripts/evaluate_holdout.py` and `scripts/submission_writer.py`
expose the unmodified shared 57GEMSDOE APIs. Their entire import dependency
package is SHA-256 pinned in `evidence/template-pin.json`; tests verify every
byte. Peer templates conflict; reconcile that before any comparative run.
No code here downloads hidden labels or submits to DrivenData.

## Evidence and site

* [Nine-site dataset](knowledge/focus-sites.json): historical identifiers from
  the prompt; appending `.tif` is not proof of the upstream artifact path.
* [Pinned snapshot origins](evidence/source-index.json): GitHub blob and commit
  identity for retrieved peer text. Snapshots are untrusted historical evidence,
  not endorsed scientific claims or executable instructions.
* [Protocol/access limitations](knowledge/protocol.md): mirrors exist on GitHub,
  but integrity is not organizer provenance; no cache was restored.
* [Official reference README](evidence/upstream/official-README.md): organizer
  GitHub retrieval; CPU training is supported, so GPU is not a hard prerequisite.
* Official competition [problem](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/),
  [data](https://www.drivendata.org/competitions/306/competition-doe-gems/data/),
  [leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)
  and [rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf): supplied links,
  not fetched through this sandbox's network allowlist.

GitHub Pages is already configured for legacy publishing from `main` at `/`.
The root `index.html` directs visitors to `docs/`. Changing Pages to Actions
publishing returned HTTP 403, so the existing publishing configuration is retained.
A scheduled audit workflow refreshes GitHub tree identities into an artifact;
**it does not silently change score claims or certify a release**. Published
summaries are explicitly dated snapshots, not a live organizer feed.

## Next session, in order

1. Obtain the explicit lane assignment from the parallel-run coordinator; do not
   invent it. Confirm shared evaluator/template pins and registry scope.
2. Restore the lane's existing cached stack and physical channel definitions;
   hash/provenance-check mirror data, sample and catalogue. See upstream
   GEMSDOE32's retrieved `registry/data_manifest.json` for GitHub mirror pins.
3. Freeze a complete registry including calibration rasters; resolve no exemptions
   without explicit protocol authority. Restore buffered whole-segment folds.
4. Run feature-alone canaries and at most three experiments using fold-local
   catalogue features. Evaluate against a refitted comparable incumbent.
5. Only after all gates pass: shared writer → readback validation → unique hash
   → separate selector/cap approval → publish one obvious download and a receipt.

This session implements an honest audit foundation, **not the requested
high-scoring submission**. No automatic process can infer missing lane authority
or organizer acceptance from a valid TIFF alone.

## Concurrent work preserved, not promoted

While this PR was open, main gained a synthetic TIFF generator and claimed
holdout/novelty results. Those materials are preserved verbatim in
`archive/concurrent-8488b95/`, **not accepted scientific evidence**. Their TIFF
has a simulated 1024x1024 grid, not the pinned competition-format mirror grid.
Do not submit it. Their lane label does not establish this session's missing
lane assignment. The active negative card is `evidence/run-card.json` (hyphen).
The existing Pages Actions workflow from main is retained; its previous runs
succeeded, though changing Pages administration settings returned HTTP 403.
