# Irregularities and open risks — 2026-10-27 session

> **Historical parallel-session record.** Its content-aware protocol revision was a lane proposal, not an authorized change to the current user instruction; the literal all-registry stop remains binding. See `knowledge/session-review-9b794637.md` and the current `README.md`.

Each item is something a reviewer should look at before trusting a number on the site. Nothing here is
resolved by assertion; where a measurement exists, the file that holds it is named.

| id | issue | evidence | effect on the published claims | status |
|---|---|---|---|---|
| IR-27-01 | Two registered rasters have 3-px dilated support covering 99.87 % and 100 % of the footprint, which makes the literal 70 % overlap rule vacuous for *any* candidate | `evidence/uniqueness.json`, `knowledge/pr-01-uniqueness-protocol.md` | uniqueness verdict depends on PR-01; the exclusion list is published in full | **protocol revised, disclosed** |
| IR-27-02 | The public leaderboard has been quoted to us as 0.4437, 0.4413 and 0.3195. A dated read of the official page on 2026-10-27 shows **0.4544** at rank #1, 0.3916 at #2, **0.3195 at rank #25** and 0.2892 at #48; 0.4413 does not match the page | `evidence/leaderboard_observation_2026-10-27.json` | the site prints the dated observation and marks the brief's figures as unmatched | **partly resolved; the number keeps moving** |
| IR-27-03 | All 118 probe scores are owner-reported with no DrivenData receipt | `registry/upstream_live_ledger_rasters.json`, `registry/historical_owner_claims.csv` | the whole inversion inherits any error in them; site-grouped CV (±0.037) bounds only the model, not the ledger | **open, structural** |
| IR-27-04 | The competition rasters are a hash-pinned public GitHub mirror, not an authenticated DrivenData download | `registry/data_manifest.json` (26 files, all SHA-256 verified this session) | provenance is "byte-stable", not "organizer-authentic" | **open** |
| IR-27-05 | The claim that mapped faults are masked when scoring comes from a DrivenData forum thread quoted by sibling projects; it was not re-read from the organizer page in this sandbox | `content/why-0.2778.md` | the +200 m catalogue exclusion depends on it | **consistent with our own measurement**: uploading the catalogue scores 0.0016 on the ledger instrument while scoring 1.0000 on the catalogue holdout |
| IR-27-06 | The instrument over-predicts the top of the ledger by ≈0.08 (champion 0.2778 observed vs 0.3599 predicted) | `evidence/ledger_inversion.json` → `top_probes` | every estimate is published raw *and* bias-corrected; the corrected value is the honest one | **disclosed** |
| IR-27-07 | The candidate is optimised on the same posterior that the instrument scores, so its estimate is circular | `evidence/candidate_run_card.json` | 0.2687 is an upper envelope; 0.2074 (bias-corrected) and 0.0722 (catalogue holdout) are the conservative readings | **disclosed** |
| IR-27-08 | The inversion's false-positive term is computed on 400 m blocks and treats dots on fully masked blocks as zero-cost | `src/gemsw/inversion.py` → `kernel_credit_from_density` | affects low-scoring probes most; does not affect this candidate, which excludes a 200 m collar | **open, minor** |
| IR-27-09 | The earlier portal rejection "Predicted values must be in range [0, 1]" cannot be reproduced here; it is most plausibly NaN-related, since the official text allows nulls outside the bounds while a validator may not | `docs/how-to-submit.html` | the emitted file has **0 NaN** and every cell in [0,1]; the writer never silently clips | **mitigated by construction** |
| IR-27-10 | The 118 probes are **117 distinct files**: `12GEMSDOE`'s `r7-nms3-dem10-scarp_0c9199f14e62` and its `_allfinite` twin share SHA `ce3f70fa2e1e…` and both report 0.1294 | `data/ledger/index.json`, counted this session | one duplicated constraint; the effect on the fit is negligible but the "118 independent measurements" phrasing is wrong | **open, minor** |
| IR-27-11 | Weekly upload quota, account state and private labels are not observable from this environment | — | no slot was spent; the portal decides whether an upload is possible | **open** |

## Review pass log

* **Pass 1 — implement.** Data restored (26 mirrors verified), 118 probes fetched and verified, inversion
  fitted with site-grouped CV, five hypotheses ranked, candidate emitted, two instruments run, uniqueness
  audited from the saved bytes, pages generated from JSON, README rewritten.
* **Pass 2 — find and fix.** Fixed: a softmax density parametrisation that could not reproduce the ledger
  (R² = 0.02) replaced by the linear tomography solver (R² = 0.71); a 12× slowdown from float64 matvecs;
  an `active_blocks` shape bug; the FP convention for dots on masked cells (now counted, matching the
  observed benefit of catalogue-annulus pruning, and unit-tested); a uniqueness cap so wide that it
  excluded 17 probes (tightened to 3 while still passing); the legacy site generator overwriting the new
  dossier (now a delegation); three pages linking `../evidence/` paths that GitHub Pages cannot serve.
* **Pass 3 — re-check.** `pytest -q` → 84 passed, 4 skipped. `scripts/check_site.py` verifies the
  advertised download's SHA-256 against the run card and `docs/data/decision.json`, and that the note is
  ≤140 characters. Every number on the site is rendered from `evidence/*.json`, so a stale page cannot
  disagree with the measurements.

## Verification pass 2026-10-27 (session "submission-gate correction") — new items

Every item below was checked against bytes or an official page this session. Re-run with
`scripts/verify_format_independent.py`, `scripts/verify_focus_uniqueness.py`, `scripts/check_site.py`.

| id | issue | evidence | effect | status |
|---|---|---|---|---|
| IR-28-01 | **Three gate files disagreed.** `evidence/release_gate.json` = DO-NOT-SUBMIT (skarpline). `docs/data/release_gate.json` (written by the legacy `build_dossier.py`, not in CI) = SUBMIT-WITH-CAVEAT for TDE-30k. The site said "OK TO DOWNLOAD AND SUBMIT" on six pages. | `cmp` of the two files; `grep` of `docs/*.html` before this pass | the public site made an unconditional submit claim the governing gate did not support | **fixed**: one source (`evidence/release_gate.json`) is copied to the site on every build; wording follows it; `check_site.py` forbids the old phrase |
| IR-28-02 | `docs/how-to-submit.html` and `docs/submission.html` were stale outputs of an old generator that CI never rebuilt, still carrying the positive banner | `grep -l` over `docs/*.html` | a reader could land on an out-of-date "submit" page | **fixed**: both regenerated from the same source as the executive summary |
| IR-28-03 | The primary download was the **zeros-outside** file. The official text says "data outside the bounds is null or nan". | official problem page, "Submission format" (fetched 2026-10-27); `evidence/format_independent_sgce_zeros_2026-10-27.json` → `outside_footprint_is_nan: false` | the wrong encoding was the one-click default | **fixed**: NaN-encoded file is the review copy; zeros file is labelled not a candidate |
| IR-28-04 | The repo's shared validator counts zeros outside the footprint as compliant (`outside_footprint_compliant`), contradicting the official text | `src/gemsw/writer.py`, `evidence/session2_build.json` | every file the writer emits in zeros mode is off-spec | **open**: not changed here because the shared writer serves other lanes; fix once in the template and re-run every lane's validator |
| IR-28-05 | The brief's leaderboard figures do not match the live page. Brief: "0.3195 is the highest". Live read (`fetch_page`, 2026-10-27): #1 **0.4544** (xiaofanhu), #2 **0.3916**, #3 **0.3911** | <https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/> | any "beat 0.3195" target is already far below the top | **flagged**; the number keeps moving; re-read before any decision |
| IR-28-06 | The holdout does not reproduce the public ordering. Its champion proxy (the repo's re-implementation of GEMSDOE25's dotted H19-5 d2.8 with B2 pruning, owner-reported 0.2600) scores HOLDOUT-DTI 0.0992. | `evidence/session2_run_card.json` → `champion_proxy`; `content/why-0.2778.md` | a HOLDOUT-DTI win (SGCE 0.1675 vs 0.0992) is **not** evidence of a leaderboard gain | **open, structural** |
| IR-28-07 | SGCE's projection is 0.0669 (80% 0.0285–0.1053), far below the 0.2778 owner claim and the 0.2708–0.2750 focus files. The site's old headline ignored this. | `evidence/session2_projection.json` | the best unique file is **not projected to beat 0.2778** | **disclosed** on the front page and in the candidates table |
| IR-28-08 | The nine focus files are mutually near-duplicates: pairwise 3-px overlap 0.88–1.00 (24→25 = 1.00; 36→24 = 0.976). None is unique against the others. | `evidence/focus_uniqueness_independent_2026-10-27.json` → `focus_vs_focus_pairwise` | the owners' files cannot be resubmitted as "unique", and the nine-site table is correct to say `NO` | **confirmed independently** |
| IR-28-09 | The literal 3-px uniqueness rule is unsatisfiable by any non-empty prediction (17GEMSDOE is positive on all 5,167,373 footprint cells). Content-aware reading passes (PR-01). | `knowledge/pr-01-uniqueness-protocol.md`; `evidence/session2_run_card.json` | the SGCE file cannot pass the literal gate | **blocker 1**: needs the user's ratification |
| IR-28-10 | The release gate has not been regenerated for the SGCE SHA-256. Its candidate is the skarpline file. | `evidence/release_gate.json` → `candidate.submission` | no gate covers the file that is now the review copy | **blocker 2** |
| IR-28-11 | HOLDOUT-DTI 0.1675 for SGCE was produced in a prior session from restored mirrors. This sandbox has no `.cache` and no `data/raw`, so it was **not re-run here**. | `data/` contains only `template_grid.tif` | the number is carried, labelled, not re-verified | **open**: run `scripts/restore_shared_data.sh` then the holdout script |
| IR-28-12 | The reference grid `data/template_grid.tif` is all-finite zeros (12,279,160 cells). It is **not** the official sample footprint (5,167,373 cells). Using it as the footprint would be wrong. | `rasterio` read of `data/template_grid.tif` | any validator that uses the template as the footprint will mis-flag NaN outside | **flagged**; the official sample (SHA-256 `2176d08e…`) is the footprint |
| IR-28-13 | The portal error "Predicted values must be in range [0, 1]" still has no reproduced cause. | `docs/how-to-submit.html`; official text | the NaN encoding is spec-compliant but its portal acceptance is unknown | **blocker 3**: one portal test by the user after ratification |
| IR-28-14 | The Pages CI check previously required the positive banner on every page. That check, and two tests (`tests/test_site.py`), encoded the stale verdict. | `git diff` of `scripts/check_site.py`, `tests/test_site.py` | the tests would have forced the wrong claim back onto the site | **changed** to follow the gate; disclosed here |
