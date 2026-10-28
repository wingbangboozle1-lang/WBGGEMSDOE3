# Irregularities log — session `arena/08f7423a-wbggemsdoe3` (LBCAL-K, 2026-10-28 UTC)

Extends `IR-01`..`IR-28` from earlier lanes.

## `IR-29` — GEMSDOE92 pinned commit no longer exists upstream (fetch layer)

- **Discovery:** `scripts/fetch_peer_prompt_rasters.py` pins
  `buffedlizard55-lab/GEMSDOE92@0fd35bc0ef0654bf511b40d15eb19c53fc229a08`
  for both of its rasters; the GitHub contents API returns
  `404 No commit found for the ref` (verified twice, 2026-10-28).
- **Handling:** fail-soft refetch (inline, recorded in
  `registry/peer_prompt_2026-10-27.json`): both GEMSDOE92 rasters were
  retrieved from the repository default-branch HEAD and their on-disk SHA-256
  recorded; `pin_status` for both rows reads
  `PINNED_REF_404_used_HEAD; original_pin=0fd35bc0...`. All 17/17 peer rasters
  are present. The two GEMSDOE92 rows are disclosed as **not byte-pinned to the
  original ref**; every other row keeps its original pin.

## `IR-30` — E1 placement: knapsack cap destroyed by post-hoc prune + repair index-space bug

- **Discovery (E1, `evidence/lbcal_k/run_card_e1.json`, verdict `negative`):**
  1. The CELF allocator enforced `max_empirical_overlap = 0.60` across all 149
     sparse masks at the 120,000-dot selection stage, but the subsequent exact
     Dinkelbach leave-one-out prune (120,000 → 60,214) preferentially removed
     low-π dots *outside* dense comparator halos and kept high-π dots inside
     them, inflating post-prune overlaps to `0.9989` (own archived LBCAL 71k
     file), `0.9417` (GEMSDOE22 h23-b), `0.9360` (GEMSDOE23 h30), `0.8576`
     (h23-a), `0.8525` (GEMSDOE67 ovtr). **The cap held only at selection
     time; the gate correctly failed the near-copy of our own prior artefact.**
  2. The removal-only repair routine indexed the dot array in
     *footprint-flat* space but wrote to `dots.ravel()` in *global raster*
     space, so it cleared up to 503 unrelated dots in the raster's top rows
     instead of the violating dots, then stalled at `removed=0` for 11
     iterations (log lines in the E1 record).
- **Fix (E1-repair, same preregistered hypothesis, not a new experiment):**
  global index mapping `flat_idx[cand_idx[drop]]`; two-pass adaptive cap
  recalibration (`cap_abs ≈ 0.635 × N_final × 0.97`) so the cap is expressed
  against the *post-prune* dot count rather than the placement ceiling; a
  fail-closed guard that aborts to `negative` if a repair would remove more
  than 25 % of the dots. E1's corrupted artefact was renamed
  `…-DO-NOT-SUBMIT` and moved to `evidence/lbcal_k/` (outside every registry
  discovery root); its card is preserved at `evidence/lbcal_k/run_card_e1.json`.

## `IR-31` — registry scope difference vs the FCHD-era build (disclosure, not a failure)

- This session's full-registry build indexes **182 files / 152 unique dot masks
  / 149 sparse masks**; the FCHD-era build indexed 195 / 153 / **149**. The 13
  missing files are `.cache/sites` focus-repo extras whose masks were
  duplicates or dense controls in the FCHD build; the sparse non-lattice mask
  set that drives the `≤ 0.70` gate is identical in size (149) and the dense
  witness (IR-01) and r13 lattice are present. Scope disclosed in the run card.

## Standing caveat unchanged — `IR-01`

The registered 17GEMSDOE dense witness remains positive on 100 % of the
footprint, so the *literal* all-registry `≤ 0.70` reading is unpassable for any
nonempty candidate. The content-aware gates (U1 exact identity, U3 non-lattice
`≤ 0.70`, lattice excess `≤ +0.05`, surface `|ρ| ≤ 0.90`) are the decision rule
per this session's brief and the preregistration — disclosed, not silent.
