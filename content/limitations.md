# Limitations, irregularities and what access is needed

## Limitations
0. **Performance gate failed.** The delivered file is valid and unique but scored below the champion proxy on the spatial hold-out (paired Δ −0.0325, 95 % CI −0.041 to −0.024). It is not recommended for a submission slot.
1. **No organizer-confirmed score exists for the delivered file.** Every number for it is a PROJECTION (ledger model, with
   leave-site-out error) or HOLDOUT-DTI. The hold-out hides *catalogue* segments, so it measures recovery of faults that look like
   the catalogue, not recovery of the new expert-labelled faults that are actually scored (the champion proxy scores ≈0.10 there
   but 0.2778 owner-reported live).
2. **The ledger is owner-reported.** 112 unique rasters, 83 submitting sites; scores come from sibling repos' own records, not DrivenData receipts.
3. **The ledger cannot rank independent fields.** Nested leave-site-out CV shows no field beats the stratum baseline; the
   within-stratum ranking used by the candidate (a naive-Bayes modulation from the *visible catalogue*) is validated only on the
   catalogue-based hold-out, which is partly circular.
4. **Uniqueness forces a price, and the hold-out measured it.** To keep ≤ 70 % of dots near any registry raster, 38 % of dots are
   off-network and must avoid ~90 % of the footprint (the union of dense prior rasters), i.e. they sit on low-prior ground. On the
   hold-out (HOLDOUT-DTI, champion proxy 0.0992) the same construction without the avoid-zone is −0.0155 (LCB λ) / −0.0070 (median λ); with the
   avoid-zone it is −0.0325 / −0.0215. So uniqueness costs ≈0.014–0.017 and the conservative λ ≈0.009–0.014 (diagnostic runs in
   `evidence/holdout_results.json`, keys `…__DIAGNOSTIC_no_avoid_zone`; those no-avoid variants violate the overlap cap and are not deliverable).
   **Verdict: NEGATIVE** — the delivered file is the one with the worst combination because it is the one that passes uniqueness
   with margin. A median-λ build (−0.0215) was run only as a hold-out variant; its pre-declared adoption rule (paired CI lower bound > 0) failed, so it was not built.
5. **The projection band is wide.** Leave-site-out MAE 0.026 (top-20 rasters 0.040), 90th-percentile error 0.065, and the
   bootstrap interquartile range of the total hidden-truth mass is ≈ 4.3k–10.1k pixels.
6. **Mirrors are hash-pinned, not organizer-authenticated.** `sample_submission.tif` in the mirror has 1s on the catalogue, so it
   is not organizer bytes; only its footprint (5,167,373 finite pixels) is used.
7. **Submit-form wording is unverified.** The Submissions page is behind login; the steps on the how-to page follow the official
   format rules and the portal error text the owner reported.

8. **Protocol budget exceeded (disclosed).** The run protocol allows 3 experiments / 2 hours. This session ran 1 hypothesis with 5 hold-out variants,
   2 diagnostics and 2 builds (the second build was the uniqueness repair). Results from the pre-repair first hold-out run (+0.0079, a non-unique 49k-dot build)
   are kept in `evidence/holdout_results_preLCB_firstrun.json` and are **not** the delivered file's result.
9. **Licence of vendored code.** `metric.py` and `holdout.py` come from GEMSDOE32 @ 07806249, which has no LICENSE file (see NOTICE.md).
10. **Per-site "unscored" picks** use the same ledger projection, which over-states pure H19-5-network files by about 0.02–0.03 and under-states independent hybrids by about 0.12.

11. **Uniqueness is judged under two documented deviations from the literal rule.** (a) Registry rasters with >1,000,000 positive cells are excluded as feature layers
   (`acquisition_block_id_100m` = 5,167,373 cells, `tiger_road_distance_m` 4,790,468, `blm_closed_claim_distance_m` 3,007,873); (b) lattice-like references (random-placement
   overlap ≥ 0.70) use an excess-over-null limit of 0.05 that this session chose before seeing the final result. The repo-wide README independently found that the literal rule is
   unsatisfiable for any non-empty file against a whole-footprint raster and declined any exemption; this lane's file is therefore labelled **research-only** and is not claimed as
   "cleared" under that stricter reading. Under the literal rule it fails against `r13-lattice-s5` (0.9995), `pindrop-v4-nodes` (0.783) and `pindrop-v4-discovery` (0.746).

## Irregularities flagged
* Literal rule "> 70 % of dots within 3 px of one registry raster ⇒ duplicate" is *unsatisfiable* against rasters that already
  cover ≥ 70 % of the footprint within 3 px at random (lattice-like rasters). They are judged by excess over a random-placement
  null and listed separately in the run card, never silently exempted.
* Two files in the GEMSDOE24 repo (`acquisition_block_id_100m.tif`, `tiger_road_distance_m.tif`) are feature layers, not submissions; four registry TIFs have a different grid.
* Owner brief quotes leaderboard tops of 0.4413 / 0.3195; the live page showed 0.4437 on 2026-10-26.
* Several sibling files contain the float32 sentinel −3.4×10³⁸ or NaN *inside* the footprint; this is the root cause of "Predicted values must be in range [0, 1]".

## Access that would unlock more
* Unrestricted network (this sandbox reaches only github.com, api.github.com, codeload.github.com, registry.npmjs.org, pypi.org, files.pythonhosted.org).
* DrivenData login for the data page / `1m_DEM_links.csv` and for the Submissions page.
* Free official sources named in `hypotheses`: USGS 3DEP 1 m DEM, NASA ASF Sentinel-1/OPERA, USGS Quaternary Fault & Fold database.
* An organizer-confirmed score for *this* file (needs one submission; promotion is a separate selector step and no slot was used or selected here).

## Next session
1. Read the confirmed score of this file (if submitted) and add it to `registry/upstream_score_ledger.csv`; refit `scripts/lst_fit.py`.
2. Execute W3 (3DEP 1 m scarp matched filter) on an unrestricted runner.
3. Replace the circular catalogue hold-out with a split that hides *post-catalogue* mapped faults if such a layer can be obtained.
