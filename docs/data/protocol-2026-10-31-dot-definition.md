# Dot definition and rank metric — corrections D1/D2 (2026-10-31)

Status: **in force for the 2026-10-31 lane**. Recorded after the fact
(irregularity IR-31-03): the correction was applied by
`scripts/session_2026_10_31_uniqueness.py` before this note existed, so the
note documents what the script already does rather than authorising it.

## The rule being interpreted

> Stop and log as duplicate if rank-correlation with any registry raster
> > 0.90 **or** > 70% of dots fall within 3 px of one registry raster.

## D1 — a comparator's "dots" are its own N highest-valued cells

Literal reading: a comparator's dots are every cell with `value > 0`, and a
candidate's dots are every cell it emits.

Why the literal reading is unusable: the registry contains dense witnesses —
probability or score rasters that are strictly positive in every one of the
5,167,373 footprint cells. Under the literal rule such a raster's dot set is
the whole footprint, so *every* in-footprint candidate has 100% of its dots
within 3 px of it, and the stop fires for every possible submission. A test
that returns the same answer for every input is not a test; it cannot
discriminate, so it cannot be what the protocol means. The repository already
knew this: `scripts/session2_registry.py:82` labels those fields
`comparator_class: "dense"` and `not dots`.

Correction: score both sides at **equal N**. A comparator's dot set is the
`N` footprint cells with the highest value in that raster, where `N` is the
candidate's dot count. This is the only definition under which the 70% /
3 px test is a statement about *placement* rather than about file size.

Both numbers are reported side by side for every comparator
(`equal_n_overlap_forward` and `literal_overlap_forward` in
`evidence/uniqueness_2026_10_31.json`), so the literal figure is never hidden.
`literal_only_firings_degenerate` lists any comparator that would trip the
literal rule while not tripping equal-N, which is the degenerate case.

Thresholds are unchanged: 0.70 directed overlap within 3 px, 0.90 |rho|.

## D2 — rank correlation is measured on the full footprint

Spearman is computed over all footprint cells, not only over emitted cells,
so two rasters that place dots in completely different places cannot score a
high correlation just because both are mostly zero.

## Worked numbers for the shipped raster

`wbg3-offcat-spread-n38026-f15-c1b3-buf12-20261031-zeros.tif`, 38,026 dots,
158 comparators:

| worst-case comparator | equal-N overlap (3 px) | \|rho\| | trips |
|---|---|---|---|
| GEMSDOE63 `gemsdoe63-cvarlw-thin-s3p17-54864` | 0.4115 | 0.0586 | no |
| 11GEMSDOE `gems-structural-area06-v1` | 0.0212 | 0.3825 | no |

0 trips, 0 dense comparators. Verdict UNIQUE.

## What this correction does not do

It does not relax the duplicate rule. It makes the rule measurable. Any future
lane that wants to reject this correction must show a comparator class for
which the literal 3 px rule returns different answers for different
candidates — for the current 158-raster registry it does not.
