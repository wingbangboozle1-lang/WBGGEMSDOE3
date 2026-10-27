# Session review — 2026-10-27, branch `arena/1f0b051d-wbggemsdoe3` (3 passes)

## Pass 1 — implement and verify
- Restored all pinned bytes SHA-closed (`scripts/restore_session_data.py`: core rasters,
  externals, calibration set, nine focus files — all PASS) and the full scored ledger
  (`scripts/fetch_ledger_rasters.py`: **118/118 verified**).
- Reproduced from bytes (`scripts/session_audit.py` → `evidence/session_1f0b051d_audit.json`):
  champion subset anatomy (2,545 dots removed vs GEMSDOE31, all at 1.414–2.0 px catalogue
  distance; retained min √5 px); focus-nine pairwise duplication (Jaccard 0.342–1.000,
  GEMSDOE25 ≡ GEMSDOE30); the skarpline estimator refit (R² −0.65, LOO RMS 0.096) and its two
  counterexamples (lattice 0.0904→“0.399”; SGMC self-prediction h=1.0→“1.66” vs reported
  0.049–0.051); density-matched proxy rankings; static hide-recover read-backs.
- Preregistered 5 hypotheses (H1 top: lidar scarp-dipole polarity) before any placement;
  leakage canary PASS (worst non-catalogue AUC₂ 0.659, lidar fields ≤0.578); refit LST
  (LOO MAE 0.0251, Spearman 0.907 — exact reproduction of the archived fit).
- E1 pure dipole: **failed** uniqueness (74.2% within 3 px of skarpline) and ledger strata
  (0.059). E2 + coherence/piedmont/suppressions: unique vs subset, still strata-empty (0.037).
  Frontier diagnostic: λ-optimal unique allocation projects 0.098, yet archived ~50%-unique
  files scored 0.219–0.2478 → λ off-network unidentified. E3 frontier hybrid → repaired final:
  40,000 dots, unique vs 122 comparators (max 67.0%), validator PASS, verdict **negative**
  on beating 0.2778 (analog-median estimate ≈0.16).

## Pass 2 — bugs, wrong assumptions, edge cases (all fixed or recorded)
1. **Uniqueness-repair v1 destroyed the design** (sequential per-offender drops removed
   20,575 dots; pool A collapsed 20,000→1,923). Rewrote as joint drop + cap-tracked streaming
   refill (4,125 drops); the bad TIF was deleted before any commit.
2. **Cap denominator bug**: caps computed at K=40,000 while refill stalled at 38,193 →
   fractions 0.7017 > 0.70. Fixed with streaming refill (reached 40,000) plus drop-only
   enforcement on final N.
3. **Pool ratio drift**: corridor refills were cap-blocked (broad cover rasters), final pools
   15,892/24,108 (39.7% corridor). Recorded in run card + note corrected to 40/60.
4. **My preregistered G3 gate (LST ≥ 0.26) was itself invalid**: λ is unidentified off-network
   (archive refutes λ=0 there). Withdrawn by recorded amendment, replaced by an archive-analog
   frontier gate; LST still reported with the caveat.
5. **Density-matched SGMC proxy ranks the 0.0904 lattice above the champion** — it cannot gate
   alone; G4 failure is recorded in the card/site rather than hidden.
6. Two `edit_file` patches silently failed to land during development (avoid-quota branch);
   detected by grep/import checks and by missing log lines. All shipped code paths were
   re-verified by execution, and `scripts/session_verify.py` re-audits the saved bytes with
   independent (EDT-based) code: all format checks PASS, overlaps match the KDTree results.
7. Edge cases checked: writer rejects non-finite/out-of-range (vendor template writer,
   unmodified); ZIP contains exactly the TIF; docs copy byte-identical; dots on catalogue = 0;
   dots outside footprint = 0; min spacing 3.0 px; note = 123 chars ≤ 140.

## Pass 3 — re-check against the original request
- Executive summary with the required table (file to download, estimated score, uniqueness vs
  the other GEMSDOE sites) for GEMSDOE24/25/27/28/30/31/32/33/36 + all previous lanes + this
  candidate: `docs/session-1f0b051d/index.html` (generated from evidence JSONs, no hand-typed
  numbers), with an obvious ✅ download / ⚠️ verdict banner at the top and a
  [how-to-submit](../docs/session-1f0b051d/how-to-submit.html) subpage (unique name, exact
  ≤140-char note, the [0,1] portal-error fix).
- “Why 0.2778?” answered from bytes (subset + √5 px trim; +0.0070 over base; no receipt exists).
- “Can we beat 0.2778?” — not demonstrably with a unique file and the available instruments;
  the archive frontier for unique files is 0.219–0.2478 and this candidate sits on it
  (estimate ≈0.16 median analog). Public leaderboard top observed 2026-10-27: 0.4544.
- 3–5 new hypotheses ranked pre-implementation; top candidate validated on the blocked
  holdout (with control) before any slot discussion; H5 blocked on named free official data
  (USGS 3DEP tiles unreachable from this sandbox).
- Protocol run card emitted (`evidence/session_1f0b051d_run_card.json`): hypothesis, mechanism,
  named mimic, HOLDOUT-DTI + CI + withheld count, registry correlation/overlap, raster SHA-256,
  validator output, submission name + 123-char note, verdict **negative**. 3 experiments run;
  0 slots used.
- Irregularities flagged on the site (§7, IR-S1…S6), including the still-unreconciled main-site
  “SUBMIT skarpline 0.428” banner (owned by the previous lane's card/tests; this lane records
  the correction and its evidence instead of silently rewriting another lane's decision).

## Limitations / what I need access to (unchanged blockers)
- No DrivenData login → no organizer-authenticated data, no upload, no receipt; every historical
  score remains owner-reported. Sandbox egress is allowlisted (GitHub/PyPI + page fetches);
  USGS 3DEP/NHD tile hosts are unreachable, blocking H5. 3.8 GB RAM / 2 CPU / no GPU in-sandbox.
- Next session should: get one organizer receipt to anchor estimators; reconcile the main-site
  decision with the withdrawn 0.428; consider H4 (radiometric gating) or H5 on an unrestricted
  machine; keep the 3-experiment preregistration discipline.
