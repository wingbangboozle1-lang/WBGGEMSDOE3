# Irregularities and open risks — 2026-10-28 AMDC audit addendum

Companion to `knowledge/irregularities-2026-10-27.md` (left untouched). Every item below was
measured this session; the file that holds each measurement is named. Nothing here is resolved
by assertion.

| id | issue | evidence | effect on the published claims | status |
|---|---|---|---|---|
| IR-28-01 | The published SGCE figure 0.1675 was measured on per-cell k6 **rebuild** files with asymmetric per-domain dot budgets, not on the shipped bytes. The shipped bytes score **0.0191** [0.0169, 0.0211] on the identical evaluator and folds (22,232 withheld); a budget-repaired pooled rebuild scores 0.0026 | `evidence/amdc/sgce_bytes_audit.json`, `evidence/session2_run_card.json` | the site headline is corrected to the shipped-bytes figure; 0.1675 is retained only as a labelled per-cell-rebuild method measurement | **corrected on site, disclosed** |
| IR-28-02 | Owner-reported scores and matched-holdout scores are **inverted** on the 9 focus sites: Spearman −0.849, Pearson −0.886. The dotted near-catalogue family (B2 0.2778 owner) scores worst on the holdout (0.0039); off-catalogue files score best on the holdout and worst with owners | `evidence/amdc/ranking.json`, `evidence/amdc_run_card.json` | any owner↔holdout mapping (including the 0.2726 OLS projection) is sign-unstable across families; projections are published with their cross-method disagreement (0.05–0.27) as the uncertainty statement | **open, structural** |
| IR-28-03 | The AMDC-E3 build (60,000 dots) has max **gated** registry overlap **0.936** vs `ledger/GEMSDOE67__gemsdoe67-ovtr-ml-cover-tau3p0-20261012-nan.tif` plus 9 further gated overlaps > 0.81 and 25 literal duplicates on the 134-row registry. No TIF was written | `evidence/amdc/uniqueness_remeasured.json`, `evidence/amdc_run_card.json` | AMDC verdict is **negative** by duplicate-stop; the 3-experiment budget is exhausted (3/3) so no 4th experiment is permitted | **closed, fail-closed** |
| IR-28-04 | The dipole/corridor mechanism tested **negative**: E1 (no corridors) 0.0466 beats E2 (corridors) 0.0441 on the matched holdout. E3's win (0.0552) comes from coverage/placement, not from the preregistered dipole-gating mechanism | `evidence/amdc/exps.json`, `evidence/amdc/paired.json` | the AMDC hypothesis is not supported even before the uniqueness stop; a rerun would need a new mechanism, not a new threshold | **closed, negative result** |
| IR-28-05 | Four other repository candidates are format-SUBMITTABLE yet fail full-registry uniqueness: TDE-30k 0.723, skarpline 0.772, CSPES 0.703, HCE1 0.741 (max gated overlap, limit 0.70). Only SGCE passes (0.690) | `evidence/amdc/sgce_reaudit.json` + repo sweep logged in `evidence/amdc_run_card.json` | TDE-30k is revoked as the release-gate candidate and reconciled to SGCE; the other three stay research-only | **corrected on site, disclosed** |
| IR-28-06 | Focus sites GEMSDOE25 and GEMSDOE30 are byte-comparable on the holdout (identical 0.100926 over 44,090 dots) while carrying separate owner reports (both 0.2600); GEMSDOE24/27 are near-identical on the holdout (0.0967/0.0964) with different reports (0.2477/0.2449). The 9-point owner↔holdout fit inherits this aliasing | `evidence/amdc/ranking.json` | the OLS R² = 0.786 / LOOCV 0.0051 fit is in-family and partly aliased; out-of-family projections (SGCE) are weak | **open, disclosed** |
| IR-28-07 | Cells k6/k7 bowls contributed 0 withheld positives on evaluator-A folds (empty bowls); the v3.0 pooled figure rests on the remaining folds. Identical for every file scored, so comparisons are fair, but absolute levels depend on fold composition | `evidence/amdc/sgce_bytes_audit.json` | absolute HOLDOUT-DTI levels are evaluator-relative; only same-fold comparisons are cited | **open, minor** |
| IR-28-08 | No organizer receipt exists for any file here; weekly quota, account state and private labels remain unobservable. No slot was spent | — | the decision stays SUBMIT-WITH-CAVEAT with the slot check as a blocking human action | **open, structural** |

## What changed on the site because of this addendum

* The SGCE headline figure is the shipped-bytes HOLDOUT-DTI 0.0191 (native evaluator) / 0.0190
  (matched evaluator), with the 0.1675 method figure labelled as a per-cell rebuild.
* The 9-site table gained audited matched-holdout, projection, and uniqueness-decision columns.
* `docs/data/release_gate.json` authority moved from the revoked TDE-30k bytes to the SGCE bytes;
  the decision stays SUBMIT-WITH-CAVEAT and the blocking reasons still name the slot check.
* The AMDC lane keeps a negative verdict with its own dossier at `docs/amdc/index.html`.
