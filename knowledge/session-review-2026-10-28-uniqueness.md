# Session review — 2026-10-28 · full-registry uniqueness audit (merged onto main)

Branch `arena/0d17f7d5-wbggemsdoe3`. Originally based on `main` at `0549e93`; merged with `main` at `1bcb89a` (PR #56), which already set the governing decision to DO-NOT-SUBMIT.

## Lane method paragraph

This session did not build a new design. It re-measured the single candidate and two alternatives
against the full registry of real sibling submissions, using the shared 3-px kernel
(`gemsw.exact.kernel_credit_field`, `RADIUS_PX = 3.0`) and the repo's existing audit tooling
(`scripts/check_uniqueness.py`, extended to take a candidate path and to classify
`submission` vs `input_feature` rows). Every number was measured from bytes pinned by sha256.
The 3-px test is the directed overlap: the share of a candidate's dots within 3 px of any dot of a comparator.

## Decision

**Governing decision (unchanged by this branch): DO-NOT-SUBMIT.** `main` (commits d7bd382 and 4a059be) fails
closed on a literal dense-witness stop. The owner-mirror witness `17GEMSDOE_E-proba-multiscale.tif` is positive on
the whole footprint, so any nonempty candidate has 100% directed overlap with it. Do not upload any historical TIFF.

This branch adds an independent second finding. The 13GEMSDOE r13 lattice blocks every candidate in the repo under
the literal per-raster 70% rule, even if the witness is set aside:
- invdesign candidate 0.9944, KHD 0.9991, FCHD 0.9996, TDE30k 0.9895.
- The lanes passed earlier only because they excluded "lattice" masks from the 3-px test.

Open question for the user (not decided here): whether the dense-witness stop and the lattice class should stay
literal (current `main` protocol) or follow the earlier convention that excludes them.

## Measurements (all from `evidence/`)

| Artifact | Comparators | Max directed 3-px overlap | Binding comparator | Max abs Spearman | Literal unique |
|---|---|---|---|---|---|
| invdesign candidate (`uniqueness_gate_full_2026-10-28.json`) | 457 submissions | **0.9944** | 13GEMSDOE r13 lattice | 0.0507 | no |
| KHD (`uniqueness_khd_full_2026-10-28.json`) | 457 | **0.9991** | 13GEMSDOE r13 lattice | 0.2019 | no |
| FCHD-NCM (`uniqueness_fchd_full_2026-10-28.json`) | 458 | **0.9996** | 13GEMSDOE r13 lattice | 0.6232 | no |
| TDE30k (`uniqueness_tde30k_full_2026-10-28.json`) | 457 | **0.9895** | 13GEMSDOE r13 lattice | 0.0400 | no |

Earlier 58-raster pass (`evidence/uniqueness_gate.json`, max 0.6874): superseded. It was a subset of the registry.

Structural measurements (`scripts/uniqueness_coverage.py` → `evidence/uniqueness_coverage_2026-10-28.json`):
- Union of all 457 submissions' dots (3,964,929 cells): the 3-px footprint covers **100%** of the 5,167,373-cell footprint. No design can have zero overlap with every submission.
- The 13GEMSDOE lattice leaves **7,103 footprint cells (0.14%)** at ≥ 3 px. Under the literal rule, ≥ 30% of any design's dots must sit there.
- Input and witness rasters are excluded from the sibling count: `acquisition_block_id_100m` (1.0), `tiger_road_distance_m` (0.9998), `blm_closed_claim_distance_m`, and the dense witness `17GEMSDOE_E-proba-multiscale` (100% footprint).

## Changes on this branch

- `scripts/check_uniqueness.py`: takes an optional candidate path; classifies `submission` vs `input_feature`; keeps every row; drops the candidate's own bytes.
- `scripts/uniqueness_coverage.py` (new): union coverage and free-cell measurement.
- `scripts/fetch_registry_rasters.py`, `scripts/fetch_focus_tifs.py`, `scripts/verify_focus_and_candidate.py`, `scripts/verify_0_2778_chain.py` (new): fail-closed fetch and verification of pinned bytes.
- Evidence: the four full audits, the coverage file, `evidence/focus_candidate_verify_2026-10-28.json`, `evidence/chain_0_2778_verify_2026-10-28.json`, `evidence/registry_fetch_2026-10-28.json`, and `evidence/session_2026-10-28_uniqueness_run_card.json`.

Edits made to gate, site, and test files before the merge were discarded in favour of `main`'s governing versions. `main` had already fixed the same defects:
the 0.000 KPIs (its builder no longer reads the git-ignored `inversion98b.json`), the "ORGANIZER-CONFIRMED" wording, and the stale 0.687 / ≤ 0.174 / 98-probe figures.
Verified on the merged tree: `scripts/check_site.py` PASS and 236 tests passed, 4 skipped.

## Still open after this branch (for the user)

- Choose the uniqueness reading (literal, as on `main`, or lattice-excluded). Under the literal reading, a registry-aware constrained allocator is required and is blocked: it needs `data/external/*_u8.tif` (GEMSDOE24 mirror), `data/work/rho_blocks.npy` (`scripts/invert_ledger.py`), and `data/work/champion_ref.tif`. None are in the checkout.
- Locate the upstream repo and ref for `pindrop-v4-discovery` / `pindrop-v4-nodes` (155,021 dots each).
- Decide the outside-footprint encoding (zeros vs NaN). The candidate uses zeros; the official text says "null or nan".
- `evidence/run_card_v3.json` still reads "promote"; `main`'s gate is authoritative. Left unedited because the gate binds its sha.
- The 0.2778 chain: the 2,545 removed dots lie at √2 px (1,201) and 2.0 px (1,344), and the 3,891 dots removed earlier sit at 1.0 px. The zero-credit and pure-FP premises are assumptions (see `docs/executive-summary.html` on `main`).
- `knowledge/preregistration-2026-10-28-khd.md` says "1.01–2.01 px"; frozen, not edited.
- Dangling README link to `evidence/review-2026-10-28.json` (pre-existing on `main`; not created here).

## Limitations

- No new design was built or run on this branch. Zero design experiments; four audits and one coverage pass.
- No organizer receipt, portal result, or holdout result exists in this sandbox for any file. Owner-reported scores are not organizer-confirmed.
- The DrivenData portal and data pages are login-walled from this sandbox.
