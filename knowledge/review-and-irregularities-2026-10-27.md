# Review and irregularities — 2026-10-27

> **Merge recheck:** corrections below distinguish a prior independent session from the current negative run card. The H6-1 proxy cannot identify the near-catalogue live regime, and the mirrored data are not organizer-authenticated.

Continues `knowledge/review-and-irregularities-2026-10-26.md` (IR-01 to IR-08 stay in force).
Each item states what was observed, the evidence, the impact, and the proposed action.
Nothing here has been silently fixed. Decisions needing a user call are listed in the final report.

### IR-09 — Leaderboard figures conflict across sources
- **Observed.** Three public figures for the top score: the live official page (#1 xiaofanhu) reads
  0.4544 on 2026-10-27; the repository feed (`registry/leaderboard_snapshot_2026-10-26.json`) reads 0.4437;
  and the brief cites 0.4413. The brief's "highest" 0.3195 is rank #25, not the top.
- **Evidence.** `evidence/leaderboard_observation_2026-10-27.json`, source
  [official leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/).
- **Impact.** Any statement about "the leaderboard high" must name the snapshot date. The public split is not an organizer receipt.
- **Action.** Scheduled refresh replaces the feed. The live observation is shown next to it on the site. No hand-edit of the feed.

### IR-10 — The uniqueness gate is a project protocol, not an organizer rule
- **Observed.** The official rules (NLR PDF, all seven chunks read) have no clause that compares a submission with
  other competitors' rasters. The closest text is A.5.1, which requires "an original work by the competitor", and
  A.13, which names "technological or programmatic diversity" only as a policy factor.
- **Impact.** The 70% and 0.90 limits are a repository and user standing instruction. They must be labelled
  PROTOCOL, not organizer requirements, in any public text. The site says so.
- **Action.** A protocol owner should confirm whether the gate applies as written. See IR-11.

### IR-11 — The gate is unsatisfiable under the literal "dot" definition
- **Observed.** The registered witness (`17GEMSDOE` E-proba, SHA `ab0a0a62…`) is finite and positive on all
  5,167,373 footprint cells. Any nonempty in-footprint candidate therefore has 100% of its dots within 3 px of a
  witness dot. The gate's limit is 70%.
- **Evidence.** `evidence/verification_2026-10-27.json` (witness coverage and forward overlap); `evidence/focus_audit.json`
  (`universal_blocker: true`, reproduced by `scripts/audit_focus.py` today).
- **Impact.** The user's "MUST GENERATE A UNIQUE TIF" request cannot be satisfied under the literal gate. The stop is
  correct. Changing the gate's definition to make it pass would be gaming it, and was not done.
- **Action (decision for the user).** Options are listed in the final report. None is applied. The current
  instruction remains binding.

### IR-12 — Archived stand-in page was publicly downloadable
- **Observed.** The former `site/` page served `gems-hnew01-stepper-dblind-unique.tif` (1200 × 1600, wrong grid,
  labelled unique). Its grid does not match the sample, so it is not a valid submission for this competition.
- **Action taken.** Moved to `archive/site-legacy-2026-10-26/` with `ARCHIVE.md`.
  The Pages site no longer links to it. Confirm the public Pages URL no longer serves it after deploy.

### IR-13 — The owner's +0.0070 gap remains unexplained
- **Observed.** GEMSDOE32 (0.2778) is GEMSDOE31 (0.2708) minus 2,545 dots. Pruning on the holdout proxy (H6-1)
  moves DTI by +0.00005 (paired CI excludes zero but the magnitude is tiny). Against random equal-count pruning, the
  paired gain is +0.00011 and its CI includes zero.
- **Evidence.** `evidence/h6_1_proximity_pruning_holdout.json`; `evidence/verification_2026-10-27.json`.
- **Impact.** H6-1's buffered holdout has no withheld truth within 3 px of visible catalogue context, so it cannot determine the effect of pruning on live near-catalogue labels or attribute the unverified owner's gap. Other hidden-label effects remain unmeasured.
- **Action.** Keep as an open question. No new experiment run (budget rule: H6-1 is not re-run).

### IR-14 — The "Predicted values must be in range [0, 1]" error is not reproduced
- **Observed.** The eight TIFFs surveyed during the merged recheck (`docs/`, `submission/`, `archive/`, `data/`) have zero finite values
  outside [0,1]. The reported error text is not reproduced by any local file.
- **Evidence.** `evidence/verification_2026-10-27.json` → `local_tiff_survey`.
- **Impact.** Its cause is unexplained. Candidates: NaN outside the footprint without nodata; a sentinel value;
  float rounding above 1.0. Only the portal can distinguish these.
- **Action.** Needs a portal test with an authenticated account. This sandbox cannot perform it. Flagged as an open item.

### IR-15 — Zeros outside the footprint versus "null or nan"
- **Observed.** GEMSDOE32 (and the shared writer) store zeros, not NaN, outside the 3730 × 3292 footprint. The
  official page says data outside the bounds "is null or nan".
- **Evidence.** R6 in `knowledge/verification-2026-10-27.md`.
- **Impact.** Whether the portal accepts zeros outside bounds is not verified here. The owner claim implies the
  portal did accept GEMSDOE32, but that claim has no receipt.
- **Action.** Covered by the portal test in IR-14. No change to the shared writer without an explicit decision.

### IR-16 — The public feed was stale at the earlier observation
- **Observed.** The Pages feed showed 0.4437 (last checked 2026-10-26). The live page shows 0.4544.
- **Impact.** A stale feed must not look live. Direct bash access is restricted; public pages can be read through the research viewer.
- **Action.** The 0.4544 observation was recorded with its timestamp; the scheduled workflow attempts refresh and marks failures or age as stale.

### IR-17 — The nine-site table is a re-run of the repository audit, not nine independent measurements
- **Observed.** `scripts/audit_focus.py` was re-run today and reproduced the table. Only GEMSDOE32, GEMSDOE31
  and GEMSDOE36 were independently re-measured by hand-written checks in `scripts/verify_2026_10_27.py`.
- **Impact.** The other six rows depend on the audit script's code path. A bug there would affect them.
- **Action.** Recorded. Extend the independent checks to all nine sites before any future site-level decision.

### IR-18 — The requested unique GeoTIFF was not produced
- **Observed.** Under IR-11, no candidate can clear the gate. The user asked for a file that beats 0.2778.
  Beating it is not established: no holdout win has been demonstrated, and no receipt for 0.2778 exists.
- **Impact.** The request is blocked, not failed through error. No file was generated, uploaded, or presented as new.
- **Action.** Decision options are in the final report.

### IR-19 — Research-only and DO-NOT-SUBMIT TIFFs remain downloadable
- **Observed.** `docs/downloads/` and `submission/` contain research files that are labelled DO NOT SUBMIT.
  Their names and the site banner state this, but a direct file link is still usable.
- **Impact.** Low risk, but a user could submit one by mistake.
- **Action.** Each file carries the DO-NOT-SUBMIT label in the page that links it. Removal is a user decision.
