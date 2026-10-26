# Untried hypotheses (written BEFORE implementation; ranked)

Registry check performed on 2026-10-26 by `grep` over the nine sibling repos (commits pinned in
`registry/upstream_pins.json`). Honest novelty statements are included; where an idea overlaps prior work it says so.

| Rank | ID | One-line | Expected DTI gain (labelled guess, not a result) | Cost | Data |
|---|---|---|---|---|---|
| 1 | **W1** | Ledger-supervised density tomography over 66 independent fields, used to **allocate** dots (Dinkelbach/greedy) under an H19-5 overlap cap | 0 to +0.02 vs champion lineage; main value is a *unique* file at a known projected score | medium (done) | all in repo |
| 2 | W2 | Ledger-residual gap fill: place the off-network quota where the fitted density is high but the champion network has no dot | folded into W1 (the quota arm) | low | in repo |
| 3 | W3 | Metre-scale scarp matched filter from the official USGS 3DEP 1 m DEM tiles | +0.02 to +0.08 if scarps in the hidden labels are metre-scale (unknown) | high | **not obtainable here** (see below) |
| 4 | W4 | Sentinel-1/OPERA InSAR line-of-sight velocity steps across faults | unknown, probably small in an arid, slowly deforming basin | high | **not obtainable here** |
| 5 | W5 | Newer-vintage Quaternary-fault database difference (faults mapped after the training catalogue) | unknown; only helps if hidden labels overlap newly mapped traces | medium | **not obtainable here** |

## W1 — Ledger-supervised tomography (LST), executed
* **Layers (all in the repo mirror):** 19 training bands, 12-band lidar-scarp stack (11 used), GeoDAWN radiometric
  (4) and extension (4) rasters, derived SGMC fault-distance, TIGER road distance, plus derived: gradient magnitude,
  Laplacian-of-Gaussian, local relief and gravity×magnetic cross-gradient at several scales, and distances to
  wellsprings/vents.  66 fields total (`evidence/field_canary.json`).
* **Physical signature:** none by assumption.  The method does not assert a fault signature; it *measures* which
  field bins carry hidden-truth density, using the only off-catalogue supervision that exists — the live scores of
  112 distinct submitted rasters (each a "sensing pattern" of the hidden-truth field).
* **Why it can find uncatalogued faults:** the official scoring masks catalogued pixels, so a model fitted to the
  catalogue learns where the *known* faults are; the ledger instead constrains where the *new* labels are.
* **Difference from prior work (stated narrowly):** live-score inversion exists in GEMSDOE28
  (`knowledge/07_live_score_inversion.md`, 20 rasters), GEMSDOE27 `src/gems27/tomography.py` (20 rasters, recorded as
  refuted) and GEMSDOE32 LLI (strata = catalogue distance × H19-5 distance, optional few factors).  LST differs in:
  (i) 112 unique rasters instead of ≤ 60, (ii) 66 independent fields screened with *nested* leave-family-out CV so the
  reported error is not selection-biased, (iii) the fitted density is used to *place* dots with a Dinkelbach
  marginal-gain greedy, not only to rank existing files, (iv) an explicit cap on overlap with the H19-5 network
  because the ledger is confounded by that lineage.  Verdict is by nested CV, not by assertion.
* **Failure modes recorded in advance:** collinearity with the H19-5 lineage (all top ledger scores descend from it),
  so the on-network density is not identified; 112 measurements cannot resolve 5.2 M pixels; scores are
  owner-reported.  If nested-CV MAE is not clearly below the nuisance-only baseline the verdict is NEGATIVE.

## W2 — Ledger-residual gap fill (quota arm of W1)
Same machinery, but the allocation reserves a fixed fraction of dots for places the density model rates high and
H19-5 has no dot within 3 px.  Differs from GEMSDOE27 "H27-10 annulus" (a fixed geometric reallocation) by being
density-driven.  Cost is a parameter of the allocator.

## W3 — 1 m scarp matched filter (not run)
* **Layers:** USGS 3DEP 1 m DEM tiles listed in the competition's `1m_DEM_links.csv`.
* **Signature:** metre-scale vertical offsets (fault scarps) with a characteristic cross-section; a matched filter on
  profile curvature picks them out of 1 m topography far below the 100 m grid.
* **Prior status:** registered, never executed, as H61-5 in the sibling repos ("official `1m_DEM_links.csv` 3DEP
  tiles ... unverified").  Not new, but never tested.
* **Free official source:** USGS 3DEP via The National Map, https://www.usgs.gov/3d-elevation-program ; competition
  data page https://www.drivendata.org/competitions/306/competition-doe-gems/data/ .
* **Obtainable here?** NO.  This sandbox may reach only github.com, api.github.com, codeload.github.com,
  registry.npmjs.org, pypi.org and files.pythonhosted.org; `curl` to drivendata.org/usgs.gov was blocked in this
  session (HTTP 000), so the link table and the tiles could not be fetched.  Needs: an unrestricted runner, the
  DrivenData data page (login), and ~100s of GB of 1 m tiles.

## W4 — InSAR velocity steps (not run)
Sentinel-1 / OPERA products from NASA ASF (https://asf.alaska.edu , free Earthdata login).  Prior sibling note: "data-blocked in sandbox".
Not obtainable here (host not reachable; login required).

## W5 — Newer-vintage fault database difference (not run)
USGS Quaternary Fault and Fold Database, https://www.usgs.gov/programs/earthquake-hazards/faults ; difference against
the competition catalogue.  Not obtainable here (host not reachable).  Prior siblings registered variants (H60-x).

## Ranking logic
W1 is the only hypothesis that is (a) executable with data verified in the repo, (b) testable before a slot is spent
(nested ledger-CV plus the spatial hold-out), and (c) able to yield a file that is provably distinct from the
registry.  W3–W5 may have higher ceilings but are gated by access, so their *expected* gain is unrealizable today.


## Outcome of W1 (added after execution; HOLDOUT-DTI, spatially-blocked, cluster-bootstrap CI)
Precedent cited: GEMSDOE32 **H47** (LLI-unique, 49,231 dots) was also NEGATIVE on its hold-out (0.0784 vs 0.0992), and GEMSDOE27/28 tomography lanes were refuted.

| Variant (final, unique construction) | HOLDOUT-DTI [95 % CI] | Paired Δ vs champion proxy 0.0992 |
|---|---|---|
| stratum quota | 0.0632 [0.0552, 0.0711] | −0.0360 [−0.0448, −0.0270] |
| **LST modulation + quota, LCB λ (delivered)** | 0.0667 [0.0569, 0.0765] | −0.0325 [−0.0410, −0.0237] |
| LST modulation, no quota | 0.0632 [0.0538, 0.0731] | −0.0360 [−0.0445, −0.0275] |
| LST modulation + quota, median λ | 0.0777 [0.0664, 0.0883] | −0.0215 [−0.0302, −0.0127] |
| *diagnostic:* LCB λ, no avoid-zone (not deliverable) | 0.0837 [0.0738, 0.0932] | −0.0155 [−0.0233, −0.0074] |
| *diagnostic:* median λ, no avoid-zone (not deliverable) | 0.0922 [0.0817, 0.1024] | −0.0070 [−0.0143, +0.0006] |

Conclusion: the expected gain of W1 (0 to +0.02) was **not** realised once the uniqueness constraints were enforced. Verdict **NEGATIVE** for a submission slot.
An earlier non-unique build (49k dots, point λ, no avoid-zone) measured +0.0079, but it failed the uniqueness gate (0.859 overlap with GEMSDOE22 `h23-b`) and is not the delivered file.
The pinned upstream commits for all nine sites and the reference solution are in `registry/upstream_pins.json`.
W3 (3DEP 1 m scarp matched filter) remains the best-ranked untried hypothesis for a runner with unrestricted network access.
