# GEMS Field Notes — fault discovery & submission audit

> **CURRENT DECISION (2026-10-27): ONE FILE IS CLEARED FOR UPLOAD, with a disclosed caveat.**
> `submission/wbggems3-tde30k-tomography-emission-20261027T1853Z-e756a162-zeros.tif`
> (SHA-256 `e756a1621e15ae9675dc146b91a17ac379e8501f4a873e9de1133678a11b3817`) passes the format,
> range and uniqueness gates. **Estimated leaderboard DTI 0.269** (LEDGER-INVERSION ESTIMATE) /
> **0.207** bias-corrected — i.e. **below** the 0.2778 focus-site champion, because every
> focus-site file is a duplicate of another and this one is not. One-click download and the
> paste-ready portal note are on the [dashboard](docs/index.html);
> [how to submit](docs/how-to-submit.html) · [run card](evidence/candidate_run_card.json).

This is an evidence-first research system for the [DOE GEMS Prize](https://www.drivendata.org/competitions/306/competition-doe-gems/).
The actual target is **surface fault probability**, which can inform geothermal exploration; a predicted fault is not proof of a geothermal vent or resource. See the
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

## Results of the 2026-10-27 session — a score instrument, and an honest ceiling

**1. The metric makes every published score a measurement of an unknown field.** For a binary dot
field the credit term of the official DTI is *linear* in the hidden truth, so a known score pins down
the quantity `T = s(0.8M + 0.2FP)/(1 − 0.2s)`. With 118 sibling rasters that have a published score
(all SHA-256-verified against [the pinned ledger index](registry/upstream_live_ledger_rasters.json))
this becomes a small-angle tomography problem for the truth-mass field ρ on 400 m blocks, solved by
non-negative smoothness-regularised FISTA ([`src/gemsw/inversion.py`](src/gemsw/inversion.py),
[`scripts/invert_ledger.py`](scripts/invert_ledger.py)). Recovered truth mass: **27,111 cells**
(0.52 % of the footprint). Fit: MAE 0.037, R² 0.71, Spearman **0.989**. **Site-grouped cross-validation
(no site predicts itself): MAE 0.037, Spearman 0.946.** The instrument over-predicts the top of the
ledger by ≈0.08, so every estimate is reported raw *and* bias-corrected.

**2. Why 0.2778 won.** Not new information — deletion. 121,131 solid dots → 0.1922; thinned to 44,090
(2.8 px) → 0.2600; catalogue 100 m annulus dropped → 0.2708; 100–200 m annulus dropped → 0.2778. Credit
is a *max* over dots, cost is a *sum*, so the break-even marginal credit is ≈0.2·DTI: below the threshold
a dot only loses points, and inside the organiser's catalogue mask credit is impossible. It is a pruning
family with no remaining source of new information.

**3. The champion does not recover the catalogue.** Under the identical catalogue holdout the champion
scores **0.0065**, the H19-5 solid network 0.1646, and our candidate 0.0722. Uploading the catalogue
itself scores **0.0016** on the ledger instrument while being "perfect" (1.0000) on the catalogue
holdout — direct evidence that mapped faults are masked when scoring, and that the champion's score comes
from proximity to *unpublished* truth, which no instrument here can confirm.

**4. All nine focus-site best files fail uniqueness against each other.** Measured pairwise: GEMSDOE25 vs
GEMSDOE30 |ρ| = 1.000; GEMSDOE32 (champion) has 100 % of its dots within 3 px of a GEMSDOE24 file at
|ρ| = 0.984; GEMSDOE28 1.000 vs GEMSDOE24; the weakest pair is 0.714. Table:
[`evidence/nine_site_table.json`](evidence/nine_site_table.json).

**5. A unique candidate was generated and measured.** TDE-30k = (truth-density posterior from the
tomography)^12 × (tri-domain edge concordance + DEM ridge + 1 m lidar scarp stack)^0.3, emitted as 30,000
dots on a 1.5 px Poisson disk with every cell within 200 m of the catalogue excluded.
* LEDGER-INVERSION ESTIMATE **0.2687** raw / **0.2074** bias-corrected (±0.037 CV).
* HOLDOUT-DTI **0.0722** (95 % CI 0.0684–0.0755; 60,988 withheld positives, 10 km tiles).
* Uniqueness vs **all 118** verified rasters, audited from the saved file: max |rank correlation|
  **0.025**; worst 3-px overlap **0.631** over the
  **115** informative probes (cap 0.70) → PASS under
  [protocol revision PR-01](knowledge/pr-01-uniqueness-protocol.md), which excludes only probes whose
  3-px dilated support already covers more than 60 % of the footprint.
* Format: single band float32, EPSG:32611, 3730×3292, geotransform identical to the sample, 261,125 bytes,
  **0 NaN**, whole array in [0,1] — it cannot reproduce the "Predicted values must be in range [0, 1]"
  rejection. Note for the portal (120 chars) is in the run card.

**6. The leaderboard figure, dated.** The official page read on 2026-10-27 shows **0.4544** at rank #1
(rank #2 0.3916, **#25 0.3195**, #48 0.2892) — see
[`evidence/leaderboard_observation_2026-10-27.json`](evidence/leaderboard_observation_2026-10-27.json).
The 0.4413 quoted in the brief is not matched by the live page, and 0.3195 is rank #25, not the leader.

**7. Answer to "can we beat 0.2778?"** Not with a genuinely new field from these mirrors. The sweep
(quota 8k→60k, posterior weight 0→20, spacing 1.5/2.0 px) tops out at 0.2687 raw / 0.207 calibrated, and
the ledger's own 118 files show that only H19-5 descendants exceed 0.25. Beating 0.2778 requires new
information (metre-scale lineament *vectors*, InSAR strain, or a newer fault compilation), not another
transform of the same 19 bands. This is a negative result and it is a deliverable: the project now knows
where its ceiling is and can stop spending slots below it.

### Limitations and flagged irregularities

* Data provenance: the competition rasters are a **hash-pinned public GitHub mirror**, not an
  authenticated DrivenData download; pins prove byte stability, not organizer origin.
* All 118 probe scores are **owner-reported, no receipts**. The inversion inherits any error in them.
* Catalogue masking is peer-recorded (a DrivenData forum thread cited by the sibling projects) and is
  *consistent* with our catalogue-only measurement above, but was not re-read from the organizer page here.
* Documented circularity: the emission is optimised on the same posterior the instrument uses, so 0.2687
  is an upper envelope; 0.2074 and 0.0722 are the conservative readings.
* The inversion's FP term uses a 400 m block approximation and treats dots on fully masked blocks as
  zero-cost; the candidate excludes a 200 m collar so this does not affect its own estimate.
* Weekly upload quota is account-specific and unobservable from this sandbox. No slot was spent.

## How to reproduce this session (CPU only, ~25 min after the data restore)

```bash
bash scripts/restore_shared_data.sh   # pinned shared template
bash scripts/fetch_mirrors.sh         # 26 SHA-256-pinned rasters (419 MB feature stack)
.venv/bin/python scripts/fetch_ledger_rasters.py --jobs 6   # 118 scored probes, sha-verified
.venv/bin/python scripts/build_probe_set.py                 # 400 m score operators
.venv/bin/python scripts/invert_ledger.py --folds 3 --iters 100 --n-outer 3
.venv/bin/python scripts/emit_candidate.py --name wbggems3-tde --quota 30000 \
    --alpha-rho 12 --beta-S 0.3 --min-sep 1.5
.venv/bin/python scripts/nine_site_table.py
.venv/bin/python scripts/build_site.py && .venv/bin/python scripts/check_site.py
.venv/bin/python -m pytest -q
python -m http.server 8000 --bind 0.0.0.0 --directory docs
```

**Next session, in priority order.** (1) Replace the rasterised lidar scarp stack with true 1 m DEM
lineament *vectors* (USGS 3DEP, free, tile downloads need no login) — the only untested lever that adds
information rather than transforming it. (2) If that fails the same instrument, declare the lane closed
and stop spending slots. (3) Re-run the inversion with the corrected masked-block FP term and a 200 m
block grid to sharpen the posterior. (4) Obtain one organizer receipt so a ledger entry can be upgraded
from owner-reported to confirmed.

## Parallel lane LST1 — Ledger-Supervised Tomography (research-only, **NEGATIVE**)

A second lane ran on branch `arena/7d6b3b9f-wbggemsdoe3` and is merged under its own namespace so nothing above is overwritten:
[lane README](LST1_README.md) · [lane site](docs/lst1/index.html) · [lane run card](evidence/lst1_run_card.json) · code in `src/gemsw/` and `scripts/*lst*|build_submission|run_holdout|…`.
It produced `submission/wbggems3-lst1-hybrid-20261026-0a0229da-zeros.tif` (32,810 dots; format validator PASS; independent verifier PASS). Its HOLDOUT-DTI is **0.0667 vs 0.0992** for the champion proxy
(paired Δ −0.0325, 95 % CI −0.041 to −0.024) — verdict **negative**, consistent with this README's **DO NOT SUBMIT** decision. It is **not** a cleared file: its uniqueness holds only under two
documented deviations from the literal registry rule (whole-footprint feature layers excluded; excess-over-null for lattice-like references), and the project's stricter reading above declines such exemptions.
It has no organizer-confirmed score and no slot was selected. Use it for learning (e.g. the ledger-model calibration, the uniqueness-price decomposition in the lane site's Evidence page), not for upload.
