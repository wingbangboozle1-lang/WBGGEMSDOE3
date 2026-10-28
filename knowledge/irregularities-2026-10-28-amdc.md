# Irregularities and open risks — 2026-10-28 AMDC audit addendum

Companion to `knowledge/irregularities-2026-10-27.md` (left untouched; its IR-28-xx
series belongs to the parallel 9b794637 review, so this lane uses IR-AMDC-xx to avoid
colliding). Every item below was measured this session; the file that holds each
measurement is named. Nothing here is resolved by assertion. None of it overrides the
repository's governing DO-NOT-SUBMIT decision.

| id | issue | evidence | effect on the published claims | status |
|---|---|---|---|---|
| IR-AMDC-01 | The session-2 headline 0.1675 was measured on per-cell k6 **rebuild** files with asymmetric per-domain dot budgets, not on the shipped bytes. The shipped bytes score **0.0191** [0.0169, 0.0211] on the identical evaluator and folds (22,232 withheld); a budget-repaired pooled rebuild scores 0.0026 | `evidence/amdc/sgce_bytes_audit.json`, `evidence/session2_run_card.json` | 0.1675 is retired as a bytes claim and retained only as a labelled per-cell-rebuild method measurement; the bytes correction is recorded in the AMDC dossier | **corrected in the record, disclosed** |
| IR-AMDC-02 | Owner-reported scores and matched-holdout scores are **inverted** on the 9 focus sites: Spearman −0.849, Pearson −0.886. The dotted near-catalogue family (B2 0.2778 owner) scores worst on the holdout (0.0039); off-catalogue files score best on the holdout and worst with owners | `evidence/amdc/ranking.json`, `evidence/amdc_run_card.json` | any owner↔holdout mapping (including the 0.2726 OLS projection) is sign-unstable across families; projections are published with their cross-method disagreement (0.05–0.27) as the uncertainty statement | **open, structural** |
| IR-AMDC-03 | The AMDC-E3 build (60,000 dots) has max **gated** registry overlap **0.936** vs `ledger/GEMSDOE67__gemsdoe67-ovtr-ml-cover-tau3p0-20261012-nan.tif` plus 9 further gated overlaps > 0.81 and 25 literal duplicates on the 134-row registry. No TIF was written | `evidence/amdc/uniqueness_remeasured.json`, `evidence/amdc_run_card.json` | AMDC verdict is **negative** by duplicate-stop; the 3-experiment budget is exhausted (3/3) so no 4th experiment is permitted | **closed, fail-closed** |
| IR-AMDC-04 | The dipole/corridor mechanism tested **negative**: E1 (no corridors) 0.0466 beats E2 (corridors) 0.0441 on the matched holdout. E3's win (0.0552) comes from coverage/placement, not from the preregistered dipole-gating mechanism | `evidence/amdc/exps.json`, `evidence/amdc/paired.json` | the AMDC hypothesis is not supported even before the uniqueness stop; a rerun would need a new mechanism, not a new threshold | **closed, negative result** |
| IR-AMDC-05 | Four other repository candidates are format-SUBMITTABLE yet fail even the content-aware registry reading: TDE-30k 0.723, skarpline 0.772, CSPES 0.703, HCE1 0.741 (max gated overlap, limit 0.70). SGCE passes the content-aware reading (0.690) but remains blocked by the governing literal reading (100% dense-witness overlap) | `evidence/amdc/sgce_reaudit.json` + repo sweep logged in `evidence/amdc_run_card.json` | TDE-30k is revoked as a candidate under every reading; nothing in this item challenges the repository DO-NOT-SUBMIT | **recorded, disclosed** |
| IR-AMDC-06 | Focus sites GEMSDOE25 and GEMSDOE30 are byte-comparable on the holdout (identical 0.100926 over 44,090 dots) while carrying separate owner reports (both 0.2600); GEMSDOE24/27 are near-identical on the holdout (0.0967/0.0964) with different reports (0.2477/0.2449). The 9-point owner↔holdout fit inherits this aliasing | `evidence/amdc/ranking.json` | the OLS R² = 0.786 / LOOCV 0.0051 fit is in-family and partly aliased; out-of-family projections (SGCE) are weak | **open, disclosed** |
| IR-AMDC-07 | Cells k6/k7 bowls contributed 0 withheld positives on evaluator-A folds (empty bowls); the v3.0 pooled figure rests on the remaining folds. Identical for every file scored, so comparisons are fair, but absolute levels depend on fold composition | `evidence/amdc/sgce_bytes_audit.json` | absolute HOLDOUT-DTI levels are evaluator-relative; only same-fold comparisons are cited | **open, minor** |
| IR-AMDC-08 | The format reading differs by policy: this lane's all-finite re-check passes the zeros encoding and rejects the NaN variant, while the parallel independent audit reads the outside-footprint wording the other way. No organizer receipt exists; weekly quota, account state and private labels remain unobservable. No slot was spent | `evidence/amdc/sgce_bytes_audit.json`, `evidence/format_independent_sgce_*_2026-10-27.json` | neither encoding is cleared either way; the repository decision stays DO-NOT-SUBMIT | **open, structural** |

## What this addendum changed in the record

* The SGCE bytes correction (0.0191 native / 0.0190 matched, vs 0.0045 / 0.0039 for the
  B2 reference bytes) is recorded with its constructional explanation; 0.1675 survives
  only as a labelled per-cell-rebuild method figure.
* The 134-row registry re-audit, the matched 14-file ranking with paired CIs, and the
  owner↔holdout inversion are published as `docs/data/amdc_*.json` with the negative
  AMDC dossier at `docs/amdc/index.html`.
* The repository decision is unchanged: DO-NOT-SUBMIT under the governing literal
  registry reading. This lane's content-aware numbers are published for transparency,
  not as an override.
