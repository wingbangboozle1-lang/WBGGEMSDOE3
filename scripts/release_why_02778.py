#!/usr/bin/env python3
"""Why did GEMSDOE32's file score 0.2778, and how do the other eight compare?

Every number here is measured from the pinned bytes (``focus_sites.json``) or
derived from the official metric algebra. The decomposition used is exact for a
binary dot field:

    DTI = TP_w / (0.2*TP_w + 0.8*|G| + 0.2*FP_w)
    R   = TP_w / |G|                       (kernel-weighted recall)
    n   = number of dots
    h   = (dots within 3 px of truth) / n   (hit rate, kernel-weighted approximation)

    => DTI = h * (n/|G|) / (0.8 + 0.2 * n/|G|)

so the published score of one file pins *joint* constraints on its recall and on
the hidden fault-pixel count |G| -- it does not identify either alone.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems_release import shared  # noqa: E402

EVID = ROOT / "evidence" / "release"


def spearman(x, y) -> float:
    from scipy.stats import spearmanr
    return float(spearmanr(x, y).statistic)


def main() -> int:
    focus = json.loads((EVID / "focus_sites.json").read_text())
    rows = [r for r in focus["sites"] if r.get("dots")]
    scores = [r["owner_reported_score"] for r in rows]
    near = [r["frac_within_3px"] for r in rows]
    dots = [r["dots"] for r in rows]
    rho_near = spearman(near, scores)
    rho_dots = spearman(dots, scores)

    # invert the exact binary algebra for a range of assumed hit rates
    inversion = {}
    for h in (0.10, 0.15, 0.20, 0.25):
        per = {}
        for r in rows:
            s, n = r["owner_reported_score"], r["dots"]
            # s = h*(n/G)/(0.8+0.2n/G)  =>  n/G = 0.8s / (h - 0.2s)
            denom = h - 0.2 * s
            if denom <= 0:
                continue
            ratio = 0.8 * s / denom
            per[r["site"]] = dict(n_over_G=round(ratio, 3),
                                  implied_G=round(n / ratio),
                                  implied_recall=round(h * ratio, 3))
        inversion[f"h={h}"] = per

    out = {
        "generated_by": "scripts/release_why_02778.py",
        "question": "why did GEMSDOE32's h33-2-b2 file score 0.2778 and can a "
                    "different emission beat it?",
        "measured_table": [
            {k: r[k] for k in ("site", "dots", "owner_reported_score", "frac_on_catalogue",
                               "frac_within_1px", "frac_within_2px", "frac_within_3px",
                               "frac_beyond_3px", "median_distance_px",
                               "max_overlap_within_3px", "unique_vs_focus_set")}
            for r in rows],
        "rank_correlations": {
            "spearman_score_vs_near_catalogue_fraction": rho_near,
            "spearman_score_vs_dot_count": rho_dots,
            "n_sites": len(rows),
            "reading": "a negative value means fewer near-catalogue dots go with a "
                       "higher published score; n=9, observational, owner-reported "
                       "scores, so this is supporting evidence and not a controlled "
                       "experiment",
        },
        "mechanism": [
            "Known USGS/INGENIOUS fault pixels are excluded from the score entirely "
            "(staff post, topic 11516), so a dot on the mask is wasted budget.",
            "A dot 1-3 px from the mask is NOT masked: it is an active cell whose "
            "nearest hidden truth is a *new* fault, so it contributes p(x)=1 to FP_w "
            "unless a new fault happens to be within 300 m. The collar is therefore "
            "pure false-positive mass in the initial round.",
            "The 0.2778 file is the only focus file whose near-catalogue fraction was "
            "pruned twice (its own audit records '0 within 100 m and 0 within 200 m'), "
            "and it has the lowest measured near-catalogue fraction of the nine.",
            "The score is pooled over the public subset (staff post, topic 11550), so "
            "dot count enters only through the ratio n/|G|.",
        ],
        "score_inversion": inversion,
        "answer": {
            "why_it_scored_best_of_the_nine": "it placed the same structural dots as "
                "the family but removed the near-catalogue subset that the official "
                "masking rule turns into false positives",
            "can_a_different_emission_beat_it": "yes if the new emission raises the "
                "hit rate h or the coverage ratio n/|G| without lowering h faster; "
                "the fold sweep and the off-catalogue axis in this release both test "
                "that directly",
        },
        "constraint_on_the_hidden_truth": "for any file, DTI <= 1.25*R at n->0 and "
            "DTI -> 5*h as n/|G| grows, so 0.2778 requires h >= 0.0556 or, "
            "equivalently, R >= 0.2222 in the limit of negligible false positives",
    }
    (EVID / "why_02778.json").write_text(json.dumps(out, indent=2) + "\n")
    print("spearman(score, near-catalogue fraction) = %.3f" % rho_near)
    print("spearman(score, dot count)               = %.3f" % rho_dots)
    for r in rows:
        print(f"  {r['site']} score={r['owner_reported_score']:.4f} dots={r['dots']:6d} "
              f"<=3px={r['frac_within_3px']:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
