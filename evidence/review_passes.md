# Three-pass record

**Pass 1 – implement.** Registry (522 TIFs / 296 masks), ledger (118 verified live-scored rasters), design matrices, nested leave-site-out fit, allocator, candidate builder with uniqueness repair, writer + validator, hold-out runner, run card, site, README.

**Pass 2 – review / bug fixes found.**
* `build_submission` first build failed uniqueness (0.859 vs GEMSDOE22 h23-b) → avoid-zone + lower on-network share; build #2 passes (excess 0.047 ≤ 0.05).
* Independent verifier (`scripts/verify_submission.py`, separate code path: rasterio + exact EDT) initially failed because it lacked the lattice-excess rule; rule added; now PASS and reproduces main-audit overlaps (H19-5 0.6200).
* `assess_sites.py` was ~100× slow (NpzFile re-decompression) → loaded once. It applied the literal 0.70 rule to lattice references (trivially ≈1.0) → now uses the same excess-over-null rule as our own file.
* Allocator marginal-gain formula verified against brute force (tests/test_alloc.py).
* Site front page initially headlined a 0.317 projection and an unconditional green "SAFE" banner → projection withheld, two-axis banner (integrity PASS, performance NEGATIVE).
* Earlier +0.0079 hold-out result belonged to a non-unique build → kept separately, labelled.

**Pass 3 – re-check against the request.** Unique TIF ✔ (gates G1–G6 + independent verifier); no human inspection ✔; [0,1]/NaN handling ✔; name + note ≤140 (118) ✔; exec summary per-site table ✔; how-to-submit page ✔; ≥3 hypotheses ranked before implementation ✔; top hypothesis validated on hold-out ✔ (**NEGATIVE**, reported as such); external-data sources named, obtainability checked (not reachable from sandbox) ✔; labels HOLDOUT-DTI / ORGANIZER-CONFIRMED ✔; no slot selected ✔; budget exceeded (disclosed) ⚠; original prompt only reconstructed (README says so) ⚠.
