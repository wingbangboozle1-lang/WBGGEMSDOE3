#!/usr/bin/env python3
"""H66-SPRP variant emission: keep the lane, drop the shared dot support.

WHY.  The first H66 candidate (80,000 dots, spacing 2 px, top of the model's
probability field) is byte- and pixel-distinct from every sibling and has a
max |Spearman| of 0.138 against all 473 hash-verified sibling rasters, but the
project's parallel-run rule is a *dot* rule: more than 70 % of this lane's dots
must not fall within 3 px of one registry raster's dots.  Six informative
comparators fire that rule (0.74 - 0.87).

WHAT THIS DOES.  It applies the repository's existing remedy (the one the
FCHD lane used): the emission may not place a dot within 3 px of the dots of a
registry raster that this lane's own candidate already duplicated.  The
forbidden list is written out in full, with SHA-256s, so the rule is
reproducible and auditable; it is a *position* rule, it removes no catalogue
information, and the emission is re-validated on the shared holdout instrument
afterwards.

The probability field, the classifier, the feature bank, the allocator and the
writer are the same shared-template objects as the first candidate.

Usage:
    python scripts/h66_variant.py --stage forbidden --threshold 0.60
    python scripts/h66_variant.py --stage holdout --arm sp2_b80000
    python scripts/h66_variant.py --stage emit --arm sp2_b80000 --name <name>
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_COMMIT = "822a0ce5546c7b6749cdd82eb145b6b3e616603d"
TPL = ROOT / ".cache" / f"57GEMSDOE-{TEMPLATE_COMMIT}"
sys.path.insert(0, str(TPL / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from gems57 import grid as G                       # noqa: E402
from gems57 import holdout as H                    # noqa: E402
from gems57 import metric as M                     # noqa: E402
from gems57 import evaluate_holdout as EH          # noqa: E402
from gems57 import submission_writer as W          # noqa: E402
from gems57 import validate as V                   # noqa: E402
from gems57 import gates as GT                     # noqa: E402
from gems57 import uniqueness as U                 # noqa: E402

import h66_sprp_lane as LANE                       # noqa: E402

OUT = ROOT / "evidence" / "h66_sprp"
WORK = ROOT / "data" / "work" / "h66_sprp"
SAMPLE = TPL / "data" / "bridge" / "sample_submission.tif"
FORBIDDEN_JSON = OUT / "forbidden_halos.json"


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def build_forbidden(threshold: float) -> dict:
    """Registry comparators whose 3-px support this lane's candidate duplicated."""
    uni = json.loads((OUT / "uniqueness.json").read_text())
    rows = uni["rows"]
    picked = []
    for r in rows:
        if "error" in r:
            continue
        ov = r.get("my_dots_within_3px_of_theirs")
        if ov is None or ov <= threshold:
            continue
        if not r.get("informative_probe"):
            continue      # space-filling comparators carry no positional information
        picked.append(dict(submission=r.get("submission"), file=r.get("file"),
                           sha256=r.get("sha256"), forward_overlap=float(ov),
                           their_dots=r.get("their_dots"),
                           support_coverage_3px=r.get("their_support_coverage_3px")))
    picked.sort(key=lambda d: -d["forward_overlap"])
    doc = dict(
        evidence_class="REGISTRY-MEASUREMENT",
        rule=("A registry raster is forbidden when this lane's first candidate placed more "
              f"than {threshold:.0%} of its dots within 3 px of that raster's dots AND the "
              "raster is an informative comparator (3-px dilated support covering <= 60 % of "
              "the scored footprint). The emission may not place a dot inside the 3-px halo "
              "of a forbidden raster."),
        threshold=threshold,
        source_audit="evidence/h66_sprp/uniqueness.json",
        n_forbidden=len(picked),
        forbidden=picked,
        note=("This is a position rule on the emission, applied to published sibling rasters. "
              "It removes no catalogue information and no official data."),
    )
    FORBIDDEN_JSON.write_text(json.dumps(doc, indent=1) + "\n")
    log(f"forbidden list: {len(picked)} comparators (threshold {threshold})")
    for p in picked:
        log(f"  {p['forward_overlap']:.4f}  {p['submission']}")
    return doc


def forbidden_mask(g) -> np.ndarray:
    doc = json.loads(FORBIDDEN_JSON.read_text())
    mask = np.zeros(g.shape, bool)
    for entry in doc["forbidden"]:
        with rasterio.open(entry["file"]) as src:
            a = src.read(1).astype(np.float32)
        a = np.where(np.isfinite(a), a, 0.0)
        support = (a > 0) & g.footprint
        if support.any():
            mask |= U._near(support)
    log(f"forbidden halo covers {mask.sum():,} cells "
        f"({100.0 * mask.sum() / g.footprint.sum():.1f}% of the footprint)")
    return mask


def parse_arm(arm: str) -> tuple[int, int]:
    sp = int(arm.split("_")[0][2:])
    budget = int(arm.split("_b")[1]) if "_b" in arm else 40000
    return sp, budget


def emit(g, p: np.ndarray, forbid: np.ndarray, catalogue: np.ndarray, arm: str) -> np.ndarray:
    sp, budget = parse_arm(arm)
    allow = LANE.allowed_mask(catalogue, g.footprint, LANE.EXCLUDE_PX) & ~forbid
    pool = LANE.nms_pool(p, allow, sp)
    field = LANE.top_budget_field(pool, p, budget)
    field[~g.footprint] = 0.0
    return field


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stage", required=True,
                    choices=["forbidden", "holdout", "emit", "scan"])
    ap.add_argument("--threshold", type=float, default=0.60)
    ap.add_argument("--arm", default="sp2_b80000")
    ap.add_argument("--name", default=None)
    ap.add_argument("--note", default=None)
    ap.add_argument("--candidate", default=None)
    args = ap.parse_args()
    t0 = time.time()

    g = LANE.load_grid()
    if args.stage == "forbidden":
        build_forbidden(args.threshold)
        return 0

    if args.stage == "scan":
        # Fast overlap-only scan against every local sibling raster (no
        # Spearman), used to iterate on the forbidden list.
        cand = Path(args.candidate)
        with rasterio.open(cand) as src:
            a = src.read(1).astype(np.float32)
        mine = (np.isfinite(a) & (a > 0) & g.footprint)
        rows = json.loads((OUT / "uniqueness.json").read_text())["rows"]
        worst = []
        for r in rows:
            if "error" in r:
                continue
            with rasterio.open(r["file"]) as src:
                b = src.read(1).astype(np.float32)
            b = np.where(np.isfinite(b), b, 0.0)
            support = (b > 0) & g.footprint
            if not support.any():
                continue
            ov = float(U._near(support)[mine].mean())
            cov = float(U._near(support)[g.footprint].sum() / g.footprint.sum())
            worst.append((ov, cov, r["file"], r.get("submission"),
                          bool(r.get("informative_probe"))))
        worst.sort(reverse=True)
        for ov, cov, f, name, inf in worst[:12]:
            log(f"  overlap {ov:.4f} cov {cov:.3f} informative={inf} {str(name)[:70]}")
        over = [w for w in worst if w[4] and w[0] > 0.70]
        log(f"informative comparators over 0.70: {len(over)}")
        json.dump([dict(overlap=w[0], coverage=w[1], file=w[2], submission=w[3])
                   for w in worst], open(OUT / "overlap_scan.json", "w"), indent=1)
        return 0

    forbid = forbidden_mask(g)

    if args.stage == "emit":
        p = np.load(WORK / "prob_full.npy")
        field = emit(g, p, forbid, g.catalogue, args.arm)
        n = int((field > 0).sum())
        name = args.name
        path = ROOT / "submission" / f"{name}.tif"
        receipt = W.write_submission(path, field, sample=SAMPLE, footprint=g.footprint,
                                     catalogue=g.catalogue, name=name, note=args.note,
                                     metadata=dict(lane="h66_sprp_variant", arm=args.arm,
                                                   n_forbidden_halos=json.loads(
                                                       FORBIDDEN_JSON.read_text())["n_forbidden"]))
        report = V.validate(path, g.footprint, g.catalogue)
        template_report = GT.format_report(path, SAMPLE, footprint=g.footprint)
        out = dict(receipt=receipt, validator=report, template_report=template_report,
                   emission=dict(n_dots=n, arm=args.arm,
                                 forbidden=list(json.loads(FORBIDDEN_JSON.read_text())["forbidden"])))
        (OUT / "variant_build.json").write_text(json.dumps(out, indent=1))
        log(f"variant emission: {n} dots -> {path}")
        return 0

    # ---- holdout: the same emission rule, fold-locally ------------------- #
    bank = LANE.load_bank()
    folds, _q = H.buffered_component_draw(LANE.GridNS(g.footprint, g.catalogue),
                                          seed=20, hide_frac=0.20, buffer_px=3,
                                          boundary_px=12)
    terms = {}
    rng = np.random.default_rng(LANE.RANDOM_STATE + 99)
    per_fold = []
    for f in folds:
        visible = np.asarray(f["visible"], bool)
        model, info = LANE.fit_fold(bank, g, visible, 20)
        p = LANE.predict_full(bank, model, g.shape)
        field = emit(g, p, forbid, visible, args.arm)
        n = int((field > 0).sum())
        allow = LANE.allowed_mask(visible, g.footprint, LANE.EXCLUDE_PX) & ~forbid
        ys, xs = np.nonzero(allow)
        take = rng.choice(ys.size, size=min(n, ys.size), replace=False)
        control = np.zeros(g.shape, np.float32)
        control[ys[take], xs[take]] = 1.0
        arm_dti = {}
        for nm, fld in (("candidate", field), ("random_control", control)):
            _res, t = EH.evaluate(fld, f, g.footprint, block_side=200, origin=(0, 0),
                                   global_shape=g.shape)
            terms[nm] = terms.get(nm, np.zeros_like(t)) + t
            arm_dti[nm] = float(_res["dti"])
        per_fold.append(dict(fold=f["name"], n_truth=int(_res["n_truth"]), n_dots=n,
                             arm_dti=arm_dti, train=info))
        log(f"  {f['name']}: candidate={arm_dti['candidate']:.4f} control={arm_dti['random_control']:.4f}")
        del p, model
    pooled = EH.pooled_summary(terms, candidate="candidate")
    out = dict(evidence_class="HOLDOUT-DTI", evaluator_version=EH.VERSION,
               evaluator_sha256=EH.implementation_hashes(), arm=args.arm,
               forbidden=list(json.loads(FORBIDDEN_JSON.read_text())["forbidden"]),
               n_forbidden=json.loads(FORBIDDEN_JSON.read_text())["n_forbidden"],
               pooled_summary=pooled,
               best_pooled_dti=pooled["scores"]["candidate"]["dti"],
               ci95=pooled["scores"]["candidate"]["ci95"],
               baseline_pooled_dti=pooled["scores"]["random_control"]["dti"],
               paired_delta_ci95=pooled["paired_differences"]["random_control"]["ci95"],
               n_withheld_positives=pooled["scores"]["candidate"]["withheld_positive_pixels"],
               per_fold=per_fold,
               note=("Same fold-local rule as the first candidate plus the published "
                     "forbidden-halo rule; catalogue band from the fold's visible faults "
                     "only; the matched control is a uniform random dot field with the "
                     "same dot count on the same folds."),
               elapsed_s=round(time.time() - t0, 1))
    (OUT / "variant_holdout.json").write_text(json.dumps(out, indent=1))
    log(f"variant HOLDOUT-DTI {out['best_pooled_dti']:.4f} CI {out['ci95']} "
        f"control {out['baseline_pooled_dti']:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
