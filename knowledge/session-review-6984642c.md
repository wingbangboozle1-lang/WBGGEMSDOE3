# Three-pass review — session `arena/6984642c-wbggemsdoe3` (2026-10-28)

**Verdict: negative; DO NOT SUBMIT.** One new GeoTIFF was generated and
validated locally, it is published for review/testing only, and it is **not
cleared** for upload. No portal upload, no slot selection, no organizer receipt.
Session run card:
[`evidence/session_6984642c_run_card.json`](../evidence/session_6984642c_run_card.json).
Experiments: 3 of 3 (frozen preregistration executed in full); slot usage: 0.

## Pass 1 — prerequisites, preregistration, execution

- Read `README.md`, `AGENTS.md`, `PROJECT_PROMPT.md`, the prior session review
  and run cards, `knowledge/protocol.md`, the full registry/witness evidence and
  the FCHD lane code before touching anything. Restored 26/26 hash-pinned
  mirrors (543,047,966 B), the 195-file comparator/ledger/peer registry, and the
  four FCHD externals; fetched the 17 peer prompt rasters with the resilient
  script after the original one 404'd on a rewritten commit (`IR` history).
- Froze [`knowledge/preregistration-2026-10-28-adjdis.md`](preregistration-2026-10-28-adjdis.md)
  **before execution**: five ranked hypotheses (H2 adjacency-band first), the
  E1/E2/E3 plan, gates G0–G4, baseline-reproduction requirement `0.099202`, the
  literal-vs-content-aware uniqueness double disclosure, and the 3-experiment /
  2-hour stop.
- Executed the plan with [`scripts/run_adjdis_lane.py`](../scripts/run_adjdis_lane.py)
  (shared FCHD surfaces, shared allocator, shared byte validator — no forks):
  - **Baseline reproduced exactly:** champion proxy HOLDOUT-DTI `0.099202`
    CI `[0.085951, 0.112668]`, 22,232 withheld positives, evaluator
    `GEMSDOE32-HIDE-RECOVER-v3.0`.
  - **Gate 0 passed:** 73 canary rows (62 static + 10 NCM + the new adjacency
    band), max directional AUC `0.77593 ≤ 0.90` (band itself `0.77593`);
    surface gates max |Spearman| `0.5300 ≤ 0.90`.
  - **E1** (`s=0.60, K=38,000`, physical OOF Phase-B): pooled `0.03492`
    `[0.02998, 0.03986]`, emission 15,235 dots (A=35).
  - **E2** grid `s∈{0.45,0.60,0.70}×d0∈{3.5,4.0,5.0}` on Draw-20 with the NCM
    surface: winner `s=0.45, d0=3.5` → `0.05607` (Draw-21 verify `0.05603`);
    all probes `0.0402–0.0563`, monotonically worse as `s` grows.
  - **E3** budgets `{35k,38k,42k}`: winner `K=42,000` → pooled **`0.059897`**
    `[0.052989, 0.066831]`, paired Δ vs champion `−0.039306`
    (CI `[−0.049786, −0.029076]`) → **Gate 1 FAIL (decisively negative)**.
- **Generated candidate (research/review only):**
  `wbggems3-adjdis-23127d-20261028T171558Z-07355e06-zeros.tif`
  (`submission/` + `docs/downloads/`), SHA-256
  `817901562c8708139a761269fd4976e1fd70edabff359142a18da64da8abf8f0`,
  23,127 dots, name `wbggems3-adjdis-23127d-20261028T171558Z-07355e06`,
  note (76 chars) `ADJDIS: fold-legal 3.5px adjacency-band quota s=0.45 + NCM
  physical discovery >10px, CELF cap 0.635 (23127d)`. Local byte validator
  PASS (float32 single band, EPSG:32611, 3730×3292, exact transform, all finite,
  [0,1], zeros outside footprint, zero on catalogue faults) — a format pass is
  not portal acceptance.
- **Uniqueness disclosed both ways:** content-aware passes (max non-lattice
  3-px overlap `0.63497 ≤ 0.70` over 153 unique registry masks,
  pre-placement max |Spearman| `0.52995 ≤ 0.90`, no exact duplicate) while the
  **literal** all-registry reading fails at `1.0` on the registered dense
  witness (IR-01/IR-09), and Gate 3 additionally fails on the direct
  FCHD-file overlap `0.9964`. None of this was waived.

## Pass 2 — irregularities found and fixed in shared code

- **IR-29:** the 62-feature build was OOM-killed at the 3.8 GiB cgroup limit
  (documented < 500 MB claim did not hold: ~thirty full-grid float32 locals plus
  EDT scratch, arenas retained). Fixed once in `src/fchd/features.py` with
  explicit group `del`s + `_memory_sweep()` (gc + malloc_trim); numerics
  unchanged, cache rebuilt, all gates re-passed afterwards. Also fixed a
  `python | tee` pipeline that masked the failure (relaunches use `pipefail`).
- **IR-30:** attempt-1 emitted only 27 Phase-A cells of an 18,900 quota.
  Attribution used two scored-free replays: per-cell replay
  `13/3,582` and footprint-wide replay `27/18,900` / `32/22,800` — both
  reproducing the real emission exactly. Cause: the shared allocator's strict
  final repair pass enforces `|S ∩ dilate3(B_j)|/|S| ≤ 0.635` **over each
  call's own selected set**, and per-phase Phase-A sets sit ≈100% inside the
  corridors of the 7–8 whole-catalogue comparators, so almost all of them are
  deleted. Evidence:
  [`adjdis_ir28_04_diagnostic.json`](../evidence/adjdis_ir28_04_diagnostic.json),
  [`adjdis_ir28_05_fullphase_replay.json`](../evidence/adjdis_ir28_05_fullphase_replay.json),
  full write-up
  [`knowledge/irregularities-2026-10-28-adjdis.md`](irregularities-2026-10-28-adjdis.md).
  **Consequence:** Gate 1's failure is mechanical — H2 was not actually
  exercised — and the correction (joint allocation or an externally reported
  cap denominator, preregistered first) is next-session work. The experiment
  budget and 2-hour window were respected; diagnostics after 17:16 scored
  nothing.
- The site builder gained an ADJDIS candidate section (file, HOLDOUT-DTI
  estimate with CI, uniqueness both readings, gate chips, NOT-CLEARED status)
  driven by `evidence/adjdis_run_card.json`; `scripts/check_site.py` and the
  full test suite (223 passed, 4 skipped) are green. `scripts/build_executive.py`
  remains blocked/superseded — all rendering goes through `scripts/build_site.py`.

## Pass 3 — release posture, limitations, next session

- **Governing decision unchanged: DO NOT SUBMIT.** Even a promote-level
  method result would still require (a) the user's ratification of the
  content-aware IR-01/IR-09 reading of the literal 70%/3-px rule, (b) a separate
  selector approving a real weekly slot, and (c) a receipt for any score to be
  ORGANIZER-CONFIRMED. Gate 3 and the literal witness independently block this
  file; Gate 1 fails on the merits/mechanics above.
- **Limitations:** holdout numbers are HOLDOUT-DTI proxies on hash-pinned
  mirrors (byte identity ≠ organizer provenance); owner-reported leaderboard
  claims (0.4413 / 0.3195 / 0.4544) are not receipts and their correlation with
  holdout estimates is negative (Spearman −0.849 in prior sessions); the SGMC-Cal
  ESTIMATE (`0.0382` for this emission) is an off-catalogue projection, not a
  score; attempt-1 never engaged the adjacency mechanism (IR-30); no external
  scientific sources were fetched this session (only GitHub-hosted mirrors).
- **Next session (in order):** (1) reread this review, IR-29/IR-30 and the
  frozen preregistration; (2) preregister the IR-30 joint-allocation correction
  with the same E1–E3 grid and gates — do not retry per-phase call semantics;
  (3) if Gate 1 then passes with paired CI lower > 0, re-audit uniqueness with
  the corrected emission (content-aware **and** literal), refresh the ADJDIS
  section through `scripts/build_site.py`, run `check_site.py` + `pytest`;
  (4) only after user ratification of IR-01 and an explicit selector decision
  consider a slot — never pick one autonomously.
