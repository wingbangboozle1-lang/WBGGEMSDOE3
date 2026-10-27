# GEMS Field Notes — fault discovery & submission audit

> **CURRENT DECISION: DO NOT SUBMIT.** No competition GeoTIFF is cleared.
> The literal registry uniqueness rule is blocked by a registered raster that is
> positive across the entire mirrored footprint. This lane ran no experiment and used
> no slot. A separately generated parallel TIFF fails the registry and footprint checks;
> it is retained for research only. [Executive dashboard](docs/index.html) ·
> [Submission guide](docs/executive-summary.html) · [Run card](evidence/run_card.json)

This is an evidence-first research system for the [DOE GEMS Prize](https://www.drivendata.org/competitions/306/competition-doe-gems/).
The actual target is **surface fault probability**, which can inform geothermal
exploration; a predicted fault is not proof of a geothermal vent or resource. See the
[official problem and metric](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/).

## Project prompt and standing instructions — read at the start of every session

The following is the operational project brief, preserving the user's mandatory
requirements and the historical-claim ledger; it is a condensed working record, **not
a verbatim transcript** of the conversation. The prior submissions and all their
owner-reported figures have been retained in [the historical ledger](registry/historical_owner_claims.csv)
(copied from [GEMSDOE33's pinned user-report ledger](https://github.com/buffedlizard55-lab/GEMSDOE33/blob/a24fb7c5031ee08b12440af4593057858fecef8e/registry/user_reported_scores_20261026.csv));
the ledger itself is not independently receipt-verified or guaranteed exhaustive.

### Mission and values

- Review the repo and focus on GEMSDOE24, 25, 27, 28, 30, 31, 32, 33 and 36. Make an
  executive summary with the best known historical file for each site, a defensible
  estimate or an explicit **not estimable**, uniqueness versus the other listed sites,
  and an obvious download/submission decision. Investigate the reported GEMSDOE32
  H33 B2 result and whether a scientifically distinct method can improve on it.
- **Maximize P(Win)** by prioritizing reproducible improvements rather than spending
  scarce uploads on unvalidated guesses. **Own the Outcome** by investigating defects,
  surfacing negative results and maintaining an accurate handoff.
- “MUST GENERATE A UNIQUE TIF SUBMISSION FOR THE COMPETITION. DO NOT COPY A PREVIOUS
  SUBMISSION UNLESS IT'S FOR LEARNING AND EDUCATION.” A technical file, a different
  filename, a different nodata encoding or a perturbation does not establish novelty.
  If mandatory stop rules make the request impossible, say so rather than fabricate a
  result or present an old file as new.
- Produce an easy, one-click download **only for a genuinely new artifact that is
  clearly labeled**; clearly distinguish research-only files from files approved by the
  separate slot selector. No manual geological inspection should be needed for the
  checks. A local format pass is not organizer acceptance or proof of performance.
- Before implementation, document and rank 3–5 new geological hypotheses, specifying
  inputs, transforms, off-catalogue rationale, confounders, novelty and cost. Confirm
  availability and licensing of needed official external data. The top single lane and
  future alternatives are [preregistered here](knowledge/preregistration-2026-10-26.md).
- Use official, trusted sources; maintain citations, a clean, auditable table, and a
  current public feed that reports staleness. Clearly mark limitations and irregularities.
  Work through implementation, review/fixes and a final re-check. No hallucinations.
- Learn from the listed sites but do not assume any unreceipted historical claim is
  organizer-confirmed. Do not label a projection or a local proxy as an actual score.
  Holdout values must include evaluator version, withheld positives and spatial 95% CI;
  organizer-confirmed candidate results require a submission-page receipt tied to bytes.

### Parallel-run protocol — binding unless explicitly revised

1. **LANE:** stay within one assigned method. If surface or final-dot rank correlation
   exceeds 0.90 against any registry raster, or more than 70% of dots are within 3 px
   of one registry raster, log duplicate and stop. Check before placement and on final dots.
2. **REUSE, DON'T REBUILD:** use the template's cached feature stack, `evaluate_holdout.py`
   and `submission_writer.py`. Holdout must hide whole fault segments with a buffer;
   derive catalogue features only from visible faults; mask visible faults pixel-exactly;
   score pooled DTI with α=0.2, β=0.8 and the 300 m triangular kernel. If a shared tool
   is wrong, fix it once upstream, not in a private fork.
3. **LABEL:** every performance number must be HOLDOUT-DTI (version, positive count and
   95% CI) or ORGANIZER-CONFIRMED (actual submission receipt). A projection is not a
   score; unverified owner claims must never be relabeled as either.
4. **LEAKAGE CANARY:** test each feature alone on the holdout. AUC > 0.90 is leakage
   until proven otherwise.
5. **RUN CARD:** output one JSON card with hypothesis, mechanism, named non-fault mimic,
   holdout DTI and CI, registry correlation/overlap, raster SHA-256, validator output,
   submission name and note ≤140 characters, and verdict `promote` or `negative`.
   Negative results are deliverables.
6. **BUDGET:** stop after 3 experiments or 2 hours. Do not select a real submission slot;
   that requires a separate selector step and the current weekly cap on the portal.

The supplied request refers to a “single method paragraph below” but does not identify
one. The [preregistration](knowledge/preregistration-2026-10-26.md) therefore records
one **proposed**, not externally assigned, lane. The universal preflight stop occurs
before that lane is run.

### Competition and submission requirements

- Predict all faults in the GeoDAWN region in one 100 m, single-band float32 GeoTIFF,
  on the sample's CRS, shape and transform; valid predictions are probabilities in
  `[0,1]`. [Official format and DTI](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/).
  The user encountered “Predicted values must be in range [0, 1]”; its cause is not
  proven. The shared writer rejects invalid or nonfinite input rather than silently
  clipping. **Unresolved format risk:** the official text says null/NaN outside bounds,
  while the owner-mirrored sample has NaNs outside its finite footprint and the shared
  writer emits unmasked zeros there. The meaning of “bounds” and portal acceptance are
  not established; reconcile with organizers and fix the shared writer upstream before
  any future upload. See [IR-04](knowledge/review-and-irregularities-2026-10-26.md).
- [Official rules](https://docs.nlr.gov/docs/fy26osti/96647.pdf) state up to three
  submissions per week and require one final choice across both prize rounds, complete
  reproducible solution assets, license compliance, and generative-AI-use disclosure.
  Check the current account's actual quota before any upload. No account or private labels
  are accessible here.
- Focus-site links: [24](https://buffedlizard55-lab.github.io/GEMSDOE24/),
  [25](https://buffedlizard55-lab.github.io/GEMSDOE25/), [27](https://buffedlizard55-lab.github.io/GEMSDOE27/),
  [28](https://buffedlizard55-lab.github.io/GEMSDOE28/), [30](https://buffedlizard55-lab.github.io/GEMSDOE30/),
  [31](https://buffedlizard55-lab.github.io/GEMSDOE31/docs/), [32](https://buffedlizard55-lab.github.io/GEMSDOE32/docs/index.html),
  [33](https://buffedlizard55-lab.github.io/GEMSDOE33/), [36](https://buffedlizard55-lab.github.io/GEMSDOE36/docs/).
  Exact pinned research file links and independently computed overlaps are in the
  [dashboard](docs/index.html) and [audit](evidence/focus_audit.json).
- The user supplied multiple historical leaderboard figures; they are time-dependent and
  not a receipt. The public leaderboard is monitored separately and always timestamped.
  Never infer a current private score or an uploaded-file identity from it.

### Sources and required access

- [DrivenData overview](https://www.drivendata.org/competitions/306/competition-doe-gems/),
  [problem](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/),
  [about](https://www.drivendata.org/competitions/306/competition-doe-gems/page/968/),
  [data](https://www.drivendata.org/competitions/306/competition-doe-gems/data/) (login),
  [public leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/),
  [reference solution](https://github.com/drivendataorg/gems-prize-reference-solution).
- [USGS GeoDAWN](https://www.usgs.gov/data/geodawn-airborne-magnetic-and-radiometric-surveys-northwestern-great-basin-nevada-and),
  [USGS 3DEP](https://www.usgs.gov/3d-elevation-program),
  [INGENIOUS GDR 1391](https://gdr.openei.org/submissions/1391),
  [INGENIOUS project](https://gbcge.org/current-projects/ingenious/),
  [EPSG:32611](https://epsg.io/32611), [Tversky index](https://en.wikipedia.org/wiki/Tversky_index).
- The user also supplied Dropbox links to the rules, example TIFF, fault TIFF, numerical
  features and DEM link list. Direct Dropbox/DrivenData access is not available from
  this sandbox. The shared template restores a public owner mirror through allowed
  GitHub hosts; SHA pins prove mirror consistency, **not** independent official origin.
  An authenticated organizer download and hidden test labels remain unavailable.

## Results and limitations of this session

- Independently re-read nine pinned historical GeoTIFFs: all fail the requested
  uniqueness rule against at least one other focus-site raster. GEMSDOE25 and GEMSDOE30
  are identical inside the footprint despite different file encodings. See the full
  directional overlap matrix in [focus_audit.json](evidence/focus_audit.json).
- The H33 B2 raster is an exact support subset of an H27-4 base (37,654 vs 40,199
  positive pixels); 2,545 were removed close to mapped faults. This establishes a
  mechanism in the files, **not** a causal reason for the unverified historical claim.
- A registered 17GEMSDOE probability raster is positive on all 5,167,373 mirrored
  footprint cells. Under the template's finite-positive support rule, any nonempty
  in-footprint candidate has 100% forward overlap with that witness. This makes the
  literal rule impossible; no density exemption or undocumented change was applied.
- A parallel branch merged a 35,000-dot step-over TIFF (`5d451566…`). Independent
  rereading shows **98.55%** of all its dots within 3 px of the registered witness,
  **747** dots outside the mirrored footprint, and **463** on the mirrored fault
  catalogue. It is **not unique or cleared** under this protocol. Its 58-file audit
  omitted the witness and its all-valid synthetic grid cannot establish the footprint.
  Two other stand-ins do not match the sample's grid. Their files and original history
  are preserved; see [concurrent artifact audit](evidence/concurrent_audit.json).
- The shared template and 19 feature-band caches were restored with pinned SHA-256s.
  They are in ignored `.cache/`, not Git. The shared uniqueness tool tests positive
  correlation only, while the requested threshold is `|rho| > 0.90`; the independent
  audit uses the two-sided rule, and an upstream fix is still needed. No new AUC canary,
  valid holdout, raster or local new-file validator result exists because the stop came
  first. See the [scientific review](knowledge/scientific-review-2026-10-26.md) and
  [irregularities and next steps](knowledge/review-and-irregularities-2026-10-26.md).

## Reproduce the autonomous audit

Requires Python 3.11+, internet to GitHub/PyPI, `gh` or unauthenticated GitHub API
access, and disk space for the cached 19-band mirror. The script creates `.venv` if
needed and calls the pinned shared template without forking its evaluator/writer:

```bash
bash scripts/restore_shared_data.sh   # restore template + public mirror + 19 cached bands
.venv/bin/python scripts/audit_focus.py      # proof, nine-site comparison, negative run card
.venv/bin/python scripts/audit_concurrent.py # recheck parallel artifacts and rebind card
.venv/bin/python -m pytest -q               # synthetic and evidence checks
python scripts/build_site.py && python scripts/check_site.py
python -m http.server 8000 --bind 0.0.0.0 --directory docs
```

The static [GitHub Pages dashboard](https://wingbangboozle1-lang.github.io/WBGGEMSDOE3/)
is built from the evidence. Its scheduled workflow refreshes the public leaderboard
observation using the official public HTMX table fragment; failed refreshes retain a visibly stale snapshot. A feed
cannot reveal account quota, private labels, actual uploaded bytes or selector approval.
The repository currently also has legacy branch-based Pages enabled; the scheduled
workflow stages the same `/docs/` URL layout to avoid broken links when both publish.
The integration could not change the Pages source setting (GitHub returned 403); both
publishers were observed to deploy successfully. The source and checks are in
`.github/workflows/` and `scripts/refresh_feed.py`.

**Next session:** resolve the registry-support contradiction through an explicit
protocol revision; then verify official data provenance and band semantics, freeze the
single lane and comparator inventory, run feature canaries and buffered whole-segment
holdout against a matched same-evaluator incumbent, and only then use the unchanged
shared writer and separate selector. The current instruction makes producing an
eligible unique TIFF impossible, so the project must not imply otherwise.

## Parallel lane LST1 — Ledger-Supervised Tomography (research-only, **NEGATIVE**)

A second lane ran on branch `arena/7d6b3b9f-wbggemsdoe3` and is merged under its own namespace so nothing above is overwritten:
[lane README](LST1_README.md) · [lane site](docs/lst1/index.html) · [lane run card](evidence/lst1_run_card.json) · code in `src/gemsw/` and `scripts/*lst*|build_submission|run_holdout|…`.
It produced `submission/wbggems3-lst1-hybrid-20261026-0a0229da-zeros.tif` (32,810 dots; format validator PASS; independent verifier PASS). Its HOLDOUT-DTI is **0.0667 vs 0.0992** for the champion proxy
(paired Δ −0.0325, 95 % CI −0.041 to −0.024) — verdict **negative**, consistent with this README's **DO NOT SUBMIT** decision. It is **not** a cleared file: its uniqueness holds only under two
documented deviations from the literal registry rule (whole-footprint feature layers excluded; excess-over-null for lattice-like references), and the project's stricter reading above declines such exemptions.
It has no organizer-confirmed score and no slot was selected. Use it for learning (e.g. the ledger-model calibration, the uniqueness-price decomposition in the lane site's Evidence page), not for upload.

## Session 2026-10-27 — verification and blocked request

- Status: **DO NOT SUBMIT.** No GeoTIFF was generated or cleared the gate; experiments 0 of 3; slots 0.
- Start here: [verification record](knowledge/verification-2026-10-27.md) (line-by-line, with official
  links), [irregularities IR-09 to IR-19](knowledge/review-and-irregularities-2026-10-27.md),
  [requirements status](knowledge/requirements-status-2026-10-27.md), and the
  [session run card](evidence/session_run_card_2026-10-27.json).
- Re-run the checks locally with `.venv/bin/python scripts/verify_2026_10_27.py`
  (needs the restored shared-data cache from `scripts/restore_shared_data.sh`).
- Live leaderboard observation (public split, not a receipt): [evidence/leaderboard_observation_2026-10-27.json](evidence/leaderboard_observation_2026-10-27.json).
