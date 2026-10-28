# GEMS Field Notes — fault discovery and submission audit

> **CURRENT DECISION: DO NOT SUBMIT. No new GeoTIFF is cleared.**
> The registered 17GEMSDOE probability raster is positive on all 5,167,373
> cells of the hash-pinned mirrored sample footprint. Under the shared
> positive-support definition, every nonempty in-footprint candidate overlaps it
> by 100% at zero distance—above the user's 70% / 3-pixel duplicate stop.
> This is one conclusive witness, **not** a complete registry audit or proof
> that the mirror is an authenticated organizer download. No experiment or
> competition slot was used in this session.
>
> [Executive dashboard](docs/index.html) · [Nine-site comparison](docs/executive-summary.html) ·
> [How to submit *after* clearance](docs/how-to-submit.html) ·
> [Evidence and limitations](docs/evidence.html) ·
> [Existing TIFF — research only, DO NOT SUBMIT](docs/downloads/wbggems3-sgce-20261027-f52d35d8-zeros.tif)

## Start every session here

Read this README, [`AGENTS.md`](AGENTS.md), the [current negative run card](evidence/session_9b794637_run_card.json),
the [independent witness recheck](evidence/registry_witness_recheck_2026-10-27.json),
[preregistration](knowledge/preregistration-2026-10-27-9b794637.md), and
[release protocol](knowledge/protocol.md). Keep **Maximize P(Win)** and **Own the
Outcome** central: weigh risk and evidence, act autonomously when safe, and treat
a negative result as a deliverable. The reconstructed standing brief is included
at the end of this README. It is **not verbatim**: the full original prompt was
not available to this session, and the previous verbatim claim was incorrect.

## Executive summary: nine requested sites

The figures below are user/owner-reported historical claims, not
organizer-confirmed receipts. They are not current leaderboard estimates.
Each link is a pinned historical research file, not an approved download.
“Unique: No” means it fails the directed 3-pixel overlap rule against at least
one of the other eight; it does **not** assert byte-identical files. A full
current registry comparison was not completed. No reliable score for a new
submission can be estimated from these unverified, dependent data.

| Site | Highest reported historical file (research only) | Owner/user report | Estimated score | Unique vs other eight? | Decision |
|---|---|---:|---|---|---|
| GEMSDOE24 | [gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif](https://github.com/buffedlizard55-lab/GEMSDOE24/raw/5cfab74597cd1d0a271e4640b4cc34511e56ca59/docs/downloads/gems24-h25-1-dotted-h19-5-d1-5-20261002-989f59505db1-nan.tif) | 0.2477 | Not estimable | No (100.0% vs GEMSDOE25) | **Do not submit** |
| GEMSDOE25 | [gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif](https://github.com/buffedlizard55-lab/GEMSDOE25/raw/bfb2dfdbdf1b87d67afc6facd422180f56ebc455/docs/downloads/gems25-dotted-h19-5-d2-8-20261002-e56ea318af89-nan.tif) | 0.2600 | Not estimable | No (100.0% vs GEMSDOE30) | **Do not submit** |
| GEMSDOE27 | [gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan.tif](https://github.com/buffedlizard55-lab/GEMSDOE27/raw/f1e32af867d9cf0081af20866c8241ec8678a432/docs/downloads/gems27-topo-gap-closure-t-v2-on-d1-5-20261002-5512495c6bd1-nan.tif) | 0.2449 | Not estimable | No (98.0% vs GEMSDOE24) | **Do not submit** |
| GEMSDOE28 | [gems28-h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan.tif](https://github.com/buffedlizard55-lab/GEMSDOE28/raw/9c1be21e8f1be707347f737e42abf62ea669c819/docs/downloads/gems28-h36-1-rung30-blind-r1-20261003-b531dae0a36f-nan.tif) | 0.2710 | Not estimable | No (100.0% vs GEMSDOE25) | **Do not submit** |
| GEMSDOE30 | [gemsdoe30-d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca.tif](https://github.com/buffedlizard55-lab/GEMSDOE30/raw/35ce8911e2c3287eed973eacd12c252e8cb3f34c/docs/downloads/gemsdoe30-d28-poisson300m-offcat-44090-20261003T233156Z-91eae1ca.tif) | 0.2600 | Not estimable | No (100.0% vs GEMSDOE25) | **Do not submit** |
| GEMSDOE31 | [gemsdoe31-h27-4-solo-d28-20261004-8acb75e1-nan.tif](https://github.com/buffedlizard55-lab/GEMSDOE31/raw/78f9bf3ae82e5c78ca348aa37c0660c339e72f0e/docs/downloads/gemsdoe31-h27-4-solo-d28-20261004-8acb75e1-nan.tif) | 0.2708 | Not estimable | No (100.0% vs GEMSDOE25) | **Do not submit** |
| GEMSDOE32 | [gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif](https://github.com/buffedlizard55-lab/GEMSDOE32/raw/8953b986b2ce6eb5ee8b7eda23fe3ad529720986/docs/downloads/gemsdoe32-h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros.tif) | 0.2778 | Not estimable | No (100.0% vs GEMSDOE36) | **Do not submit** |
| GEMSDOE33 | [GEMSDOE33-h33d-analog-tip-stepover-r30-20261004-cb490425926e.tif](https://github.com/buffedlizard55-lab/GEMSDOE33/raw/a24fb7c5031ee08b12440af4593057858fecef8e/docs/downloads/GEMSDOE33-h33d-analog-tip-stepover-r30-20261004-cb490425926e.tif) | 0.2632 | Not estimable | No (99.7% vs GEMSDOE27) | **Do not submit** |
| GEMSDOE36 | [gemsdoe36-anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros.tif](https://github.com/buffedlizard55-lab/GEMSDOE36/raw/b90418f852615aa0974cf9a53b92fa569ed133fc/docs/downloads/gemsdoe36-anderson-geothermal-pinn-38854-20261004T230000Z-9b9ea4e6-zeros.tif) | 0.2750 | Not estimable | No (97.6% vs GEMSDOE27) | **Do not submit** |

For GEMSDOE32 B2, the decoded support is an exact subset of the GEMSDOE28 H27-4
base: 2,545 of 40,199 dots were removed near the mirrored fault catalogue.
Pruning could change the precision/recall balance, but hidden labels and a
receipt are missing, so the cause of the reported **0.2778** is unproved. A
physically distinct method might score higher; no such result has been demonstrated
here. The separate [focus audit](evidence/focus_audit.json) and
[explanation](content/why-0.2778.md) retain the measurements and caveats.

## What has and has not been validated

- The independently rechecked SGCE research TIFF has 102,208 positive cells,
  all overlapping the dense witness; its literal uniqueness gate fails. The
  mirrored grid is 3730 × 3292, EPSG:32611, 100 m. A local range/grid diagnostic
  for its zeros-outside variant passes, but a parallel independent audit of the
  outside-footprint wording fails that variant and passes its NaN-outside twin.
  This session could not re-read the official wording or test portal acceptance;
  **neither file is cleared**. The earlier `[0, 1]` upload error has no known
  cause because the rejected bytes and receipt are unavailable.
- A parallel focus-only review, independently rerun here, found a maximum 16.68%
  SGCE overlap among the nine selected files. It does not cover the full registry
  and cannot override the 100% witness. See
  [`evidence/focus_uniqueness_independent_2026-10-27.json`](evidence/focus_uniqueness_independent_2026-10-27.json).
- No new surface, raster, leak-canary, whole-fault buffered holdout, score or
  complete registry audit was produced. The original “single method paragraph”
  was not identifiable in the available brief. Four unexecuted, ranked
  [geological hypotheses](knowledge/preregistration-2026-10-27-9b794637.md)
  include named non-fault mimics, layer needs, comparisons and cost caveats.
- A dated public leaderboard observation of 0.4544 in
  [`registry/leaderboard.json`](registry/leaderboard.json) was not refreshed in
  this session and is not a score for any project file. The portal, live quota,
  authenticated official data and official USGS/GDR sites were inaccessible
  from this sandbox; pinning a public mirror only proves byte identity.

## Reproduce the checks

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
# Restore the two hash-pinned mirrored rasters to the ignored cache, and remeasure.
.venv/bin/python scripts/recheck_registry_witness.py --fetch
# Restore the exact pinned shared template for its smoke tests, without competition data.
PYTHONPATH=src .venv/bin/python -c 'from gems_project.template import ensure_template; print(ensure_template())'
.venv/bin/python scripts/build_site.py
.venv/bin/python scripts/check_site.py
.venv/bin/python -m pytest -q
```

The site builder deliberately publishes only the negative decision. The
release-gate function checks a documented prospective schema, but its caller
must independently verify actual bytes and evidence. Historical generators and
the flawed local holdout wrapper are blocked rather than used as private forks.
Full reviews and next steps are in
[`knowledge/session-review-9b794637.md`](knowledge/session-review-9b794637.md).
Historical lane records, including [LBCAL](docs/lbcal/index.html),
[HCE](docs/hce/index.html) and [THCS](docs/thcs/index.html), remain research-only
and do not authorize a submission.

## Standing project brief — reconstructed, not a verbatim transcript

The complete exact source prompt is not present in the current context. This
working reconstruction was inherited from the repository; preserve the actual
conversation as the authority if its wording differs. The long historical
claim list is in [`registry/historical_owner_claims.csv`](registry/historical_owner_claims.csv).

<details>
<summary>Expand reconstructed standing brief and parallel-run protocol</summary>

Review the repo.

I want to focus on the highest scoring submissions from the following sites,
GEMSDOE24, GEMSDOE25, GEMSDOE27, GEMSDOE28, GEMSDOE30, GEMSDOE31, GEMSDOE32,
GEMSDOE33, GEMSDOE36. I want an executive summary on every site that is clear
and obvious which is the best submission to submit to obtain a high score on
the leaderboard. It should also be unique and not an exact duplicate of any
previous submission that is the same as below. Keep iterating and testing
until we have the highest scoring submission to download and submit.

We should be able to estimate the score for a submission. I want a table in
the executive summary that clearly lists what file to download, what the
estimate score is, and whether it is a unique submission unlike any of the
other GEMDOE sites listed below.

THE FOLLOWING IS THE HIGHEST URGENCY AND MUST BE FOLLOWED!

MUST GENERATE A UNIQUE TIF SUBMISSION FOR THE COMPETITION. DO NOT COPY A
PREVIOUS SUBMISSION UNLESS IT'S FOR LEARNING AND EDUCATION. BUT WE MUST
GENERATE A UNIQUE TIF SUBMISSION. IT MUST BE OBVIOUS WHETHER IT IS OK TO
DOWNLOAD AND SUBMIT THE GENERATED TIF SUBMISSION.

There should be an easy to download submission tif file as described by the
prompt. Read the entire prompt. A lot of sites mention inspection only and a
human inspector, but the inspection needs to be done through the project and
needs to be validated for submission without human intervention.

PARALLEL-RUN PROTOCOL — read first. This session is one of several running
from this same prompt.

1. LANE. Your lane is the single method paragraph below. Stay inside it. If
   your raster's rank-correlation with any registry raster exceeds [0.90], or
   more than [70%] of your dots fall within 3 px of one registry raster's
   dots, you have drifted into another lane: log it as a duplicate and stop.
   Check this on the surface before placement AND on the final dots.
2. REUSE, DON'T REBUILD. Use the template's cached feature stack,
   evaluate_holdout.py and submission_writer.py. Holdout = hide-and-recover:
   withhold whole fault segments with a buffer, derive every catalogue-based
   feature only from the visible faults, mask visible faults pixel-exactly,
   score pooled DTI (alpha 0.2, beta 0.8, 300 m triangular kernel). If a
   shared tool is wrong, fix it once in the template and report it; never
   keep a private fork.
3. LABEL EVERY NUMBER as HOLDOUT-DTI (evaluator version, number of withheld
   positives, 95% CI) or ORGANIZER-CONFIRMED (copied from a submission-page
   receipt). A projection is never written as a score.
4. LEAKAGE CANARY. Test each feature alone on the holdout before trusting
   any result. AUC above [0.90] means leakage until proven otherwise.
5. RUN CARD. End with one JSON card: hypothesis; mechanism; the named
   non-fault process that could mimic it; holdout DTI + CI;
   correlation/overlap vs registry; raster sha256; validator output (no NaN
   inside the footprint, values in [0,1], CRS/shape/transform match);
   submission name + note of at most 140 characters; verdict promote /
   negative. Negative results are deliverables.
6. BUDGET. Stop after [3] experiments or [2] hours. Do not pick submissions:
   promotion to a real slot is a separate selector step, within the weekly
   cap shown on the submission page.

The following sites should serve as a starting point for understanding how
to generate TIF submissions. These websites are researched, and tested and
have generated TIF submissions. But we need to generate high scoring
submissions. [The full historical site/score ledger is retained in
`registry/historical_owner_claims.csv`; the 2026-10-27 focus set and their
owner-reported best scores are GEMSDOE32 0.2778, GEMSDOE36 0.2750, GEMSDOE28
0.2710, GEMSDOE31 0.2708, GEMSDOE33 0.2632, GEMSDOE25 0.2600, GEMSDOE30
0.2600, GEMSDOE24 0.2477, GEMSDOE27 0.2449. Later owner-reported rows (10-25/10-26) are in the
same CSV and in `registry/ledger_addendum_2026-10-27.json`: GEMSDOE24 gvc1 0.0859, GEMSDOE25 h66 0.0742,
GEMSDOE27 h29 0.2190 and h31 0.2250, GEMSDOE28 s18 0.0217 and s21 0.0206, GEMSDOE30 MSDB1 0.1462,
GEMSDOE33 s33 0.0963, GEMSDOE36 kpl36 0.1647, GEMSDOE64 h64 0.0383, GEMSDOE79 tilt-ring 0.0005.]

We need to study, analyze, and understand the highest score from the GEMDOE
site where the submission TIF is downloaded from, GEMSDOE32
(h33-h33-2-b2-20261004T220000Z-e5eb6e7e-zeros: 0.2778). Why and how did this
get the highest score and are we able to generate a submission that scores
higher? Answer using PhD-level experience, knowledge and judgement, then use
the answer to generate a unique TIF submission. Must be unique unlike any
within the GEMSDOE sites. Verify working line by line, no hallucinations.
Current competition leaderboard high score references supplied: 0.4413 and
0.3195 (time-dependent observations, not receipts).

Before implementing, generate 3–5 candidate geological hypotheses we haven't
tried yet, each naming: the specific layer(s) involved, the physical
signature being targeted (e.g., an edge-detection or curvature transform),
why it should catch a fault missing from the USGS/INGENIOUS catalogue rather
than one already in it, and how it differs from anything already implemented
in this repo. Rank them by expected DTI improvement and implementation cost.
Validate the top candidate on our spatially-blocked holdout set before
touching a weekly submission slot — do not spend a submission slot on an
idea that hasn't beaten the current holdout best. If a candidate can't be
validated without new external data, name the specific free, official source
needed and check it's obtainable before proposing the idea as viable.

Work line by line verifying from official verified trusted sources, provide
links for manual review. There should be no manual input, work on your own
to complete tasks. Flag any irregularities for review. No hallucinations.
Verify no hallucinations.

We need deep research into the part of the project that matters most, the
scientific discovery of geothermal vents. Store all information and knowledge
gathered from official verified sources. Think outside the box but stay
grounded in proper scientific research; be contrarian but smart; find data
sources others overlook. Design a new strategy, research, testing, analyzing
and generating submission system unique from the current websites.

Put this prompt into the repo readme and read it every time we work on the
project as a starting point. It should solve the problem of having to
manually check everything ourselves and having an up to date current feed.

Review the repo. Keep the Core Values and Own the Outcome as a focal point:
Maximize P(Win) — weigh tradeoffs, assess risk, choose the path that
maximizes the probability of winning, set emotions aside. Own the Outcome —
own results end to end; when problems arise and we have the means to act, do
so without waiting for permission; treat failure and success as signals.

The site should be able to generate a TIF file required for submission, as
easy as downloading a file to click and submit. This needs to be in the
executive summary or the very beginning of the site, obvious when you visit.

A prior downloaded document returned the portal error:
"Predicted values must be in range [0, 1]". Also give it a unique name and a
short comment to help tell submissions apart (e.g. clustering with k=25).
Create an executive summary subpage that explains exactly how to make a
submission into the contest.

Competition references:
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

Known access limitation: no DrivenData auth → cannot auto-download
training_features.tif, labels.tif, sample_submission.tif or 1m_DEM_links.csv
(verified redirect to login). The project restores a hash-pinned public
GitHub mirror instead; mirror bytes establish byte identity, not organizer
provenance.

Run the task through multiple passes. Pass 1: implement completely and
verify. Pass 2: review for bugs, missing requirements, incorrect assumptions,
edge cases; fix. Pass 3: re-check against the original request; improve
accuracy, reliability, completeness, code quality. Then create a pull
request and merge it onto main, and suggest remaining work and limitations
for the next session.

</details>
