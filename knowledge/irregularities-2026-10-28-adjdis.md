# Irregularities log — ADJDIS lane, session `arena/6984642c-wbggemsdoe3` (2026-10-28)

This document extends `IR-01`..`IR-28` (`irregularities-2026-10-27.md`,
`irregularities-2026-10-28-fchd.md`) with two newly audited irregularities
(`IR-29`, `IR-30`) found while executing the frozen preregistration
[`knowledge/preregistration-2026-10-28-adjdis.md`](preregistration-2026-10-28-adjdis.md).
Neither is a competition score; all numbers are local HOLDOUT-DTI or allocator
diagnostics.

## `IR-29` — Feature-stack OOM kill inside `build_or_load_static_features`

- **Detected:** 2026-10-28 16:47 UTC. The first ADJDIS lane process (pid 3297)
  was killed by the 3.8 GiB cgroup OOM killer (`anon-rss: 3867020 kB`) during the
  62-feature build, even though `src/fchd/features.py` documents a "< 500 MB peak"
  design. The failure was masked once by a `python | tee` pipeline that returned
  `tee`'s exit status 0; relaunches use `set -o pipefail`.
- **Cause:** `build_or_load_static_features` holds roughly thirty full-grid
  float32 intermediates (~49.5 MB each at 3730×3292) as frame locals until
  function return, and every `_fill_outside` call runs a full-grid
  `distance_transform_edt(..., return_indices=True)` (~300 MB scratch). glibc
  arenas retain freed pages as RSS, so the unreleased intermediates plus churn
  pushed resident memory past the cgroup limit before the meta file was written.
- **Fix (shared code, one place):** added `_memory_sweep()`
  (`gc.collect()` + `ctypes.CDLL(None).malloc_trim(0)`) and explicit `del` of
  each group's locals immediately after its last `_put(...)` in
  [`src/fchd/features.py`](../src/fchd/features.py). Numerics are unchanged —
  the operations and their order are identical; only release timing differs.
  The cache was rebuilt at 16:53 UTC and the full gate battery below re-passed
  afterwards (baseline reproduction `0.099202`, band canary, surface gates).
- **Status:** fixed in the shared module (no private fork); disclosed here and
  in the session review. The docstring's "< 500 MB" claim remains aspirational —
  measured peak after the fix is ~2.5 GiB.

## `IR-30` — Phase-A adjacency starvation under the shared allocator's strict final cap

- **Detected:** attempt-1 of the preregistered E1/E2/E3 (executed 16:43–17:16
  UTC, verdict `negative` in [`evidence/adjdis_run_card.json`](../evidence/adjdis_run_card.json))
  emitted only **27 Phase-A cells out of an 18,900-cell adjacency quota**
  (E3 full emission: 23,127 dots = 27 A + 23,100 B; E1: 35 A of a 15,235-dot
  emission). All nine E2 grid probes returned HOLDOUT-DTI `0.0402–0.0563`,
  decreasing monotonically with the adjacency quota `s` — the signature of a
  quota that is reserved but never spendable.
- **Measured attribution (no scoring involved):**
  - [`evidence/adjdis_ir28_04_diagnostic.json`](../evidence/adjdis_ir28_04_diagnostic.json)
    — eligibility is healthy (159k–270k Phase-A cells per holdout cell;
    draw-level quota ≈ 19k) but a replay of `celf_knapsack_allocate` on one
    holdout cell returns `selected=13` of `budget_k=3,582`
    (`comparators_capped=7`, `blocked_by_knapsack=1,386`).
  - [`evidence/adjdis_ir28_05_fullphase_replay.json`](../evidence/adjdis_ir28_05_fullphase_replay.json)
    — footprint-wide replay with the exact E3 parameters returns `selected=27`
    of `18,900` and `32` of `22,800`, reproducing the real emission bit-counts;
    `max_empirical_overlap ≈ 0.630` (the cap is enforced *over the call's own
    selected set*, so the reported ratio stays just under 0.635 while almost
    every dot is removed).
- **Cause:** `celf_knapsack_allocate` (shared FCHD tool,
  [`src/fchd/registry_full.py`](../src/fchd/registry_full.py)) runs greedy NMS
  rounds (~15.9k candidates admitted) and then a strict violation-repair pass
  enforcing `|S ∩ dilate3(B_j)| / |S| ≤ 0.635` **per comparator over that call's
  own selected set `S`**. Phase-A cells live almost entirely inside the 3-px
  dilation corridors of the 7–8 whole-catalogue registry comparators, so their
  in-corridor ratio starts at ≈1.0 and the repair pass deletes all but a few
  dozen corridor-diverse cells. Because the preregistered implementation calls
  the allocator once per phase, the Phase-B set that would have provided
  denominator headroom is never visible to the Phase-A repair.
- **Consequence for the gates:** Gate 1 (`0.059897 < 0.099202`, paired
  Δ CI `[−0.0498, −0.0291]`) fails for a mechanical reason: the adjacency
  hypothesis `H2` was never actually exercised by attempt-1. Content-aware
  uniqueness still passed (U3 `0.63497 ≤ 0.70`, pre-placement
  `max |Spearman| = 0.52995 ≤ 0.90`); Gate 3 failed via the FCHD-direct overlap
  `0.9964` and the literal dense witness (`1.0`), both reported, not waived.
- **Status:** not fixed inside the attempt-1 budget (3 experiments executed,
  16:43–17:16; diagnostics 17:33–17:52 are attribution only and scored nothing).
  The planned correction for the next session — to be preregistered before any
  run — is a joint allocation (single call over the Phase-A∪Phase-B eligible set
  with the split expressed as weights), or an explicitly reported one-place
  extension of the shared allocator accepting an external cap denominator so
  the repair pass judges the union set. The separate per-phase call semantics
  must not be retried unchanged.
