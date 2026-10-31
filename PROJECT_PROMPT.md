# Reconstructed operational project brief (maintained 2026-10-27)

This is a **condensed reconstruction**, not a verbatim transcript: the original
full chat prompt was not available to the current session, and an earlier heading
incorrectly called this file verbatim. Do not invent missing wording. The current
session's instructions and the standing requirements below govern; the complete
exact original can only be restored from the source conversation. The historical
site/score ledger is linked below. The README contains this reconstruction for
session-start reading together with the current decision.

**Current status (2026-10-31):** the project has one cleared file. The clearance
sentence, the one-click download, the SHA-256 and the 140-character portal note are on
[`docs/index.html`](docs/index.html); they are generated from
[`evidence/release/candidate_run_card.json`](evidence/release/candidate_run_card.json).
The 2026-10-27 → 2026-10-30 verdicts were **DO NOT SUBMIT** and are preserved as dated
archives under [`docs/archive/`](docs/archive/) and in the README's historical sections.

---

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


---

## Session reading order (maintained by every lane)

1. `README.md` and this reconstructed brief — the standing requirements and provenance caveat.
2. `README.md` — current repository-wide decision and each lane's status.
3. `AGENTS.md`, `knowledge/preregistration-2026-10-27-hce.md` (HCE-1 lane +
   four ranked hypotheses), `knowledge/preregistration-2026-10-26.md` and
   `knowledge/review-and-irregularities-2026-10-26.md` (IR-01…IR-08).
4. `evidence/hce_run_card.json` — the HCE-1 run card; also read
   `evidence/gemsdoe_run_card.json` and `evidence/cspes_run_card.json` for the
   other parallel lanes. Never merge their verdicts without checking the bytes.
5. `docs/index.html` — current negative repository-wide executive summary;
   historical lane pages (including HCE-1) are archived and do not authorize upload.
6. LBCAL lane (`arena/88400903`): `knowledge/preregistration-2026-10-27-lbcal.md` (five ranked
   hypotheses), `knowledge/lbcal-findings-2026-10-27.md` (science, gate audit, irregularities),
   `evidence/lbcal_lane_decision.json`, `evidence/lbcal_run_card.json`, `docs/lbcal/index.html`.
7. FCHD-NCM lane (`arena/6ea84033-wbggemsdoe3`): `knowledge/preregistration-2026-10-27-fchd.md`,
   `knowledge/irregularities-2026-10-28-fchd.md` (`IR-24`..`IR-28`), `evidence/fchd_run_card.json`,
   `evidence/master_audit_2026-10-27.json`, `docs/fchd/index.html`.

## Feed (newest first)

- **2026-10-28 ~01:45 UTC, arena/6ea84033-wbggemsdoe3 (`FCHD-NCM` lane, negative).** 62-ch 10 m 3DEP $\chi$ +
  facet + Lahontan/BLM deconfounder + 0→150 m basin worms + GDR #1391 + 4-fold NCM OOF HGB + 149-comparator
  knapsack CELF (`38,000` dots, SHA-256 `35b37288b8b1ac2a...`). Gate 0: `72/72 <= 0.7432`. Solves the `ovtr`
  overlap problem (`max non-lattice 3-px overlap = 0.6350 <= 0.70` across 195 TIFs; `0.4191` across 17 Oct 27
  peer TIFs), reaches #1 ~38k-dot spatially-blocked `HOLDOUT-DTI = 0.09702` (Draw-20 `0.10220`, ahead of
  `THCS-OOF 0.09573`, saved `HCE-1 0.09313`, and `AMDC E3 0.0552`) and #1 valid `LBCAL-Physics ESTIMATE = 0.0927`.
  Consistent with governing `DO-NOT-SUBMIT` (`release_gate.json`). 0 slots used.

- **2026-10-27 ~20:15 UTC, arena/88400903 (LBCAL lane, negative; PR #32).** A hidden-fault density fitted to
  119 owner-reported scores (family-grouped CV Spearman 0.91, RMSE 0.036 vs 0.086 constant). The design
  (71,416 dots) has a cross-fit ESTIMATE of 0.50 but fails the holdout gate (0.0631 < 0.1292) and like-for-like
  uniqueness. Holdout gate vs leaderboard: Spearman 0.09 (n=119). Independent LBCAL ESTIMATEs: skarpline 0.073,
  TDE-30k 0.051 (that lane's estimate is 0.207-0.269), dipole hybrid 0.062. Public LB at 19:05 UTC: #1 0.4544, #5 0.3566.
  The repository decision (main dashboard) is unchanged by this lane. 0 slots used.
