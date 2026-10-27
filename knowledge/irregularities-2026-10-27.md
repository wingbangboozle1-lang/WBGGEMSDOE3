# Irregularities and open risks — 2026-10-27 session

Each item is something a reviewer should look at before trusting a number on the site. Nothing here is
resolved by assertion; where a measurement exists, the file that holds it is named.

| id | issue | evidence | effect on the published claims | status |
|---|---|---|---|---|
| IR-27-01 | Two registered rasters have 3-px dilated support covering 99.87 % and 100 % of the footprint, which makes the literal 70 % overlap rule vacuous for *any* candidate | `evidence/uniqueness.json`, `knowledge/pr-01-uniqueness-protocol.md` | uniqueness verdict depends on PR-01; the exclusion list is published in full | **protocol revised, disclosed** |
| IR-27-02 | The public leaderboard has been quoted to us as 0.4437 (timestamped snapshot), 0.4413 and 0.3195 (informal) | `registry/leaderboard.json` (`last_success_utc` 2026-10-26T21:49:35Z) | the site prints only the timestamped snapshot and labels the others unverified | **open** |
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
