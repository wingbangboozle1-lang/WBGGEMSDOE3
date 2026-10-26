# WBGGEMSDOE3 · GEMS Evidence Lab

## DO NOT SUBMIT — no eligible new TIFF

[Decision & nine-site table](https://wingbangboozle1-lang.github.io/WBGGEMSDOE3/docs/) · [Executive summary / submission guide](docs/executive-summary.html) · [Scientific review](research/REVIEW.md) · [Negative run card](docs/run-card.json) · [Independent measurements](docs/audit.json)

**Read this README and the standing brief below at the start of every session.**

This checkout began with only a 13-byte README. We independently restored and SHA-256 checked nine historical TIFFs, the sample grid, existing faults, and a registered lattice from owner mirrors. **All nine historical leaders fail the literal final-dot uniqueness rule.** No candidate was generated, no holdout score was invented, and no submission slot was used. This is a negative preflight deliverable, not completion of the requested winning-TIFF goal.

### Verified findings

* GEMSDOE32 B2 equals GEMSDOE25 D2.8 after removing exactly 6,436 dots within two pixels of the catalogue. No dots were added.
* GEMSDOE25 and GEMSDOE30 have identical positive-pixel support despite different file hashes.
* A registered lattice leaves only 6,649 footprint pixels more than three pixels from its dots. Any 37,654 distinct dots must overlap it by at least 82.34%, above the 70% stop. Smaller budgets are not automatically eligible.
* Claimed leaderboard values lack organizer receipts in the reviewed evidence. They are quarantined in [unverified_user_claims.json](research/unverified_user_claims.json), never relabelled ORGANIZER-CONFIRMED.
* The prompt's single-method paragraph is absent. No geological lane was invented. There is no authenticated feature cache or matched out-of-fold baseline here.

See the [nine-site table](docs/index.html) for pinned historical downloads, unavailable estimates, measured duplication and clear DO NOT SUBMIT labels. Historical TIFFs remain comparison-only in ignored `data/`; they are never presented as new submissions.

## Reproduce

Python 3.11+, GitHub CLI, and GitHub access are required. No GPU is needed for this audit.

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/restore_comparators.py
.venv/bin/python scripts/audit.py
.venv/bin/python scripts/check_freshness.py
.venv/bin/python scripts/build_site.py
.venv/bin/pytest -q
# Optional: checks format only, NEVER authorizes submission
.venv/bin/python scripts/check_candidate.py path/to/candidate.tif --template data/sample_submission.tif
```

The audit verifies stored bytes before computation, uses pixel-exact Euclidean three-pixel neighbourhoods, measures directed overlap, and computes exact Spearman correlations of binary outputs including ties. It does not substitute binary-output correlations for pre-placement surface checks. The source inventory is pinned and historical, not the entire live registry.

The seven shared GEMSDOE24 instrument files are preserved **byte-for-byte** under `vendor/template24/`, with checksums and attribution. No private evaluator is implemented. The upstream `evaluate_holdout.py` is a method-specific runner; this project does not pretend it is a generic training command. Peer sources disagree about the shared-template identity (GEMSDOE24 versus 57GEMSDOE); resolve that before a geological experiment.

CI verifies the site, source pins and tests. The optional/manual source-freshness workflow reports changed GitHub HEADs without silently substituting new science. It does not monitor the DrivenData leaderboard or update main automatically. GitHub Pages was already enabled for main's root; root `index.html` routes to the static `docs/` site.

## Standing project prompt — normalized operational copy

This section records the current request's operative requirements, without presenting its repeated historical claims as verified facts. The long prior score lists and historical wording in peer READMEs remain archived under `research/sources/`; those are **peer source snapshots**, not a verbatim transcript of this session. The quarantined focus-site claims are linked above.

### Outcome and priorities

Review this repository and continue genuine previous work first. Focus on GEMSDOE24, 25, 27, 28, 30, 31, 32, 33 and 36. Deliver an executive summary for every site with a clearly identified file, defensible estimate if available, uniqueness determination and submission eligibility. Study the claimed GEMSDOE32 historical leader, explaining why its construction might improve performance without inventing causality or a score. Aim for the top leaderboard; do not claim that the conflicting leaderboard highs supplied in the prompt are current.

**MUST GENERATE A UNIQUE TIF SUBMISSION**, not a copied, renamed or cosmetically perturbed previous submission. Reuse old files only for education, auditing and comparison. A new submission must be clearly distinguished from research downloads. If mandatory gates fail, publish a negative run card rather than a misleading eligible download. The current unique-TIFF goal remains unmet.

Use an accessible, clean GitHub Pages site. Put the submission decision and file download at the beginning when a file actually qualifies. Provide a separate executive-summary subpage explaining the contest submission process. A valid upload is a single-band GeoTIFF or ZIP containing one TIFF, matching sample CRS, shape and transform. Prediction values must be in [0,1]; fix the previously reported range-error class through automatic validation. Include a unique name and a note of at most 140 characters. Do not ask a human inspector to bypass project validation.

### Parallel-run protocol (hard constraints)

1. Stay within the assigned single geological method. The method paragraph is missing from this request; do not silently invent an assignment. If rank correlation exceeds 0.90 or more than 70% of dots lie within three pixels of any registry raster, log duplicate and stop. Check before placement and on final dots. Do not exempt controls without explicit protocol revision.
2. Reuse the template's cached feature stack, `evaluate_holdout.py` and `submission_writer.py`, not private forks. Hide and recover entire fault segments with a buffer; derive all catalogue-based features only from visible faults. Mask visible faults pixel-exactly. Score pooled DTI with alpha 0.2, beta 0.8 and a 300 m triangular kernel. Fix a faulty shared instrument upstream once and report it.
3. Performance numbers must be HOLDOUT-DTI with evaluator version, withheld-positive count and 95% CI, or ORGANIZER-CONFIRMED with a submission-page receipt. A projection is not a score. Historical user reports without receipts stay quarantined, not promoted to either category.
4. Test each feature alone on holdout. AUC above 0.90 is leakage until disproved.
5. End with a JSON run card: hypothesis, mechanism, named non-fault mimic, holdout/CI, registry correlations/overlap, raster SHA-256, validator result, submission name/note and promote/negative verdict. Missing values remain null, not invented. Negative results are deliverables.
6. Stop after three experiments or two hours, whichever comes first. Do not select or spend a real submission slot: a separate selector must check the live weekly cap.

### Research and validation

Before implementation, propose three to five geological hypotheses with specific layers, physical signatures, reasons they could detect faults absent from USGS/INGENIOUS and differences from existing implementations. Rank qualitatively by plausible gain and cost. Validate the top eligible hypothesis using spatially blocked holdout and a matched current-best comparator before a weekly slot. New external data must be free, official and obtainable; check access before calling an idea viable. Research the physical processes relevant to geothermal systems, but recognize the competition target is fault detection, not directly geothermal vents.

Use official sources where reachable, retain provenance and source links, verify code and evidence, and flag irregularities. Do not invent successful downloads, authentication, data availability, live leaderboard values, score forecasts or scientific discoveries. Automate checks and expose freshness without false claims of a live feed. Work autonomously within available access and state limitations.

Primary source links from the brief:

* [Competition](https://www.drivendata.org/competitions/306/competition-doe-gems/)
* [Problem](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/), [resources](https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/), [data](https://www.drivendata.org/competitions/306/competition-doe-gems/data/), [leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)
* [Official reference solution](https://github.com/drivendataorg/gems-prize-reference-solution)
* [GeoDAWN USGS release](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and)
* [INGENIOUS](https://gbcge.org/current-projects/ingenious/), [GDR 1391](https://gdr.openei.org/submissions/1391)
* [Submission guidance PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf)
* [EPSG 32611 reference](https://epsg.io/32611), [Tversky background](https://en.wikipedia.org/wiki/Tversky_index)

Only GitHub/npm/PyPI hosts are available to this session. The other links above are provided for reference, **not claimed as independently fetched or verified**. Dropbox links from the brief cannot be fetched under that allowlist. Owner mirrors are reachable and pinned but are not organizer-authenticated. CPU operation is supported by the official reference README; a GPU is beneficial, not universally mandatory.

### Three passes and delivery

Pass 1: implement and verify. Pass 2: review bugs, omissions, assumptions and edge cases; repair them. Pass 3: recheck original requirements, code quality and evidence; record remaining limitations. Open a pull request from the session branch and merge it into main after successful checks, without making a competition submission. Preserve next-session actions.

**Maximize P(Win):** weigh trade-offs, protect scarce slots, prefer verified incremental value to optimistic claims. **Own the Outcome:** own the work end to end, fix what can be fixed, treat failure as evidence and clearly disclose what remains blocked.

## Next session, in order

1. Resolve the missing geological lane, shared-template identity and literal registry/budget feasibility without weakening the owner's thresholds.
2. Authenticate and restore the feature cache, metadata and labels; the mirror `labels.tif` is byte-identical to `existing_faults.tif`, not an independent evaluation set.
3. Verify external-source access before selecting a data-dependent hypothesis; see the four ranked candidates in the scientific review.
4. Reconstruct the best baseline out-of-fold and execute the feature canaries and at most three preregistered experiments. Do not use historical full-catalogue predictions as a leakage-free baseline.
5. Only after all gates pass, generate, validate and offer a genuinely new TIFF. A separate selector checks slots and receipts. Until then the current negative decision remains authoritative.

## Concurrent-session integration

While PR #4 was being prepared, main advanced through PR #3. That session's
`vendor/gems57` package, hash pins, evidence, hypothesis notes and evaluator/writer
adapters are preserved. Its read-only audit now lives at
`scripts/audit_preflight.py` (commands `preflight` and `raster`); its 18 tests remain
active in `tests/test_preflight.py`. Use our `scripts/audit.py` for the new measured
historical raster audit. The two template families must not be treated as
interchangeable until reconciled. The old conflicting site/build files are retained
as historical evidence in `archive/concurrent-main-35d7ccf/`, not active entry points.
Previously quarantined synthetic artifacts remain research-only and are not
submission files. The current authoritative decision is `docs/run-card.json`.
