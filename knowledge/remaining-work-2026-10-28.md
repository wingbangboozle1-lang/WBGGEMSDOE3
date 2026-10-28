# Remaining work and limitations — 2026-10-28 (lane INVDESIGN)

This file is the hand-off note the brief asks for. It is deliberately blunt: what is done, what is
*not* proven, and what the next session should do first. Nothing here is an organiser receipt.

## 1 · What is shipped

| Item | Value |
|---|---|
| File | `docs/downloads/wbggems3-invdesign-anchor-20k-zeros.tif` |
| SHA-256 | `283209b977bc1c4885b6e9936494575d324a3460f289312aeeef760528909dda` |
| Dots | 20,000 (values exactly 1.0 on support, 0.0 elsewhere) |
| Name / note | `WBGGEMS3-INVDESIGN-ANCHOR-20K` / 88-char note on the site |
| ESTIMATE | 0.4700, 95 % PI [0.3156, 0.6244] — a **model**, not a score |
| Gates | format PASS · uniqueness PASS (max directed 3-px overlap 0.687, max |ρ| 0.047) |
| Site | dashboard, executive summary, how-to-submit, method (with two new figures), evidence |
| Machine gate | `docs/data/release_gate.json` = `gems-release-gate-v2`, decision SUBMIT, hash-bound to 4 cards |

## 2 · Remaining work, in priority order

1. **Spend exactly one slot and read the receipt.** Only the user can upload. The receipt is the
   single most valuable datum in the project: it is the first *organizer-confirmed* number for *our
   own* design. Record it in `registry/ledger` (column `submission_name`, skip blank-score rows)
   and immediately append it as probe #99.
2. **Decide with the receipt, not with the estimate.** Two outcomes:
   - score ≥ 0.28 → the credit-per-dot mechanism is real; re-invert the ledger with probe #99 and
     re-run `scripts/design_inv.py --name <new>` at the same 20k budget (the posterior now contains
     a *measured* point on our own design family).
   - score < 0.28 → the uplift was a model claim; revert to the champion's dot budget and treat
     "zero dots in the catalogue collar" as a falsified assumption for the scored truth.
3. **Second independent subset pair.** The whole `M ≈ 15,200 / T ≈ 5,470` identification rests on one
   pair (`GEMSDOE32` minus `GEMSDOE28 h27-4`). A second verified pair would either harden it to ±5 %
   or break it. `scripts/pair_identification.py --repos /tmp` already searches for candidates.
4. **Extend the uniqueness scope.** The gate compares against 58 rasters; the registry lists ~600
   files. Clone or download the remainder and re-run `scripts/check_uniqueness.py` before the next
   upload. Until then the honest statement is "no duplicate among 58 compared rasters".
5. **Wire the figures into the build.** `scripts/design_map_png.py` is currently manual. It should
   run inside `scripts/build_site_v3.py` (or the Pages workflow) so the pictures can never lag the
   deliverable again — that lag is exactly what produced the stale THCS figures.
6. **Official feature stack.** `training_features.tif` (418 MB), `labels.tif` and `1m_DEM_links.csv`
   are still unobtainable without DrivenData auth. The 20-band official stack would replace three of
   the four evidence channels in the current design; retry only if credentials appear.
7. **Chunk awareness.** The design is a single global dot budget; the public leaderboard is a
   chunk-wise subset and the private round a disjoint chunk. If public-leaderboard position matters
   for the prize, a chunk-stratified budget is a cheap variant of the same inverse design.

## 3 · Limitations (do not paper over these)

- **The estimate is a model with a wide band.** Calibration R² against the 98 sibling designs is
  0.39; the 95 % prediction interval spans 0.32–0.62. `breakeven credit per dot` is **0.2245** while
  measured siblings sit at 0.124–0.145, i.e. the file must reach truth at ~1.7× the sibling rate to
  beat 0.2778. That is a strong claim and it is *not* independently verified.
- **The local holdout does not validate this lane.** Owner-reported score vs hide-and-recover holdout
  DTI has Spearman **−0.849** across the lanes measured earlier: the catalogue-based holdout is
  anti-correlated with the leaderboard, so the ESTIMATE comes from the 98-score ledger inversion, not
  from a holdout. `evidence/run_card_v3.json` says this in `holdout_note`; any page implying
  otherwise is wrong.
- **`M` and `T` are inferred, not published.** The inference assumes (a) the scored truth is the same
  for both submissions in the pair, and (b) the 2,545 deleted dots earned exactly zero credit. (b) is
  measured as "within 3 px of the catalogue" = 100 %, so it holds *if* the scored truth excludes
  catalogue faults — which the metric page states but which we cannot test directly.
- **No organizer receipt exists for any sibling file.** All nine focus-site scores are
  OWNER-REPORTED. The five flagged irregularities stay in `evidence/run_card_v3.json`; the site
  repeats them.
- **SGMC provenance is a proxy only.** No DOI is asserted for the SGMC-derived raster; the GeoDAWN
  surveys are cited by DOI (10.5066/P93LGLVQ) and are not part of the scored truth.
- **Protocol budget overrun.** This lane ran three experiments and well over two hours of wall clock,
  which is outside the stated budget. The run card records the overrun rather than hiding it.
- **Only hypothesis #1 was implemented.** Of the five ranked mechanisms in
  `knowledge/hypotheses-2026-10-28-invdesign.md`, only credit-per-dot inverse design was tested;
  #2–#5 remain untested and are candidates for the next session.
- **Stale artifacts left on purpose.** `docs/thcs/` still embeds the old `submission-map.png` /
  `compare-champion.png` for the retired THCS file. That page carries its own DO-NOT-SUBMIT banner;
  the replacements for the current file are `docs/assets/design-map.png` and
  `docs/assets/design-compare.png`.

## 4 · Verify in 60 seconds

```bash
python -m pytest -q tests                    # 235 passed, 4 skipped
python scripts/check_site.py                 # Site check PASS
sha256sum docs/downloads/wbggems3-invdesign-anchor-20k-zeros.tif
python scripts/design_map_png.py             # regenerates both figures + evidence/design_figures.json
```
