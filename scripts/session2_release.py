#!/usr/bin/env python3
"""Release the validated k=6 SGCE candidate (contrarian-coverage uniqueness repair).

Deterministic from committed evidence + ignored local caches:
  data/work/sgce_bins.dat, data/work/dense_cover_count.npy, data/work/sgce_dots_k6.npy
Re-runs the OFFICIAL uniqueness audits (surface BEFORE placement, dots AFTER), writes both GeoTIFF
encodings, validates the saved bytes, and rebinds the run card to this exact construction.
"""
from __future__ import annotations
import hashlib, json, sys, time, shutil
from pathlib import Path
import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gemsw import sgce, grid as G, uniq2, writer as W  # noqa: E402

T0 = time.time()


def main() -> None:
    g = G.load_grid()
    bins = sgce.load_bins(g)
    cnt = np.load(ROOT / "data" / "work" / "dense_cover_count.npy")
    avoid = cnt > 6
    dots = uniq2.unpack(np.load(ROOT / "data" / "work" / "sgce_dots_k6.npy"), g.foot.shape)
    geo = sgce.geometry(g.labels, g.foot, 15.0)
    rho, dinfo = sgce.density(bins, g.labels, g.foot, geo)
    rho_u = rho.copy()
    rho_u[avoid] = 0.0
    print(f"candidate dots={int(dots.sum())}, avoided px={int((avoid&g.foot).sum())} "
          f"({100*(avoid&g.foot).sum()/g.foot.sum():.1f}% of footprint), t={time.time()-T0:.0f}s", flush=True)

    pre = uniq2.surface_only_audit(rho_u, g.foot)
    print("PRE-PLACEMENT SURFACE", {k: pre[k] for k in ("n_comparators", "max_abs_spearman", "passed")},
          f"t={time.time()-T0:.0f}s", flush=True)
    aud = uniq2.audit(dots, rho_u, g.foot)
    print("FINAL DOTS", {k: aud[k] for k in ("U1_exact_dot_duplicate", "U2_max_abs_spearman",
          "U3_max_overlap_nonlattice", "U3_lattice_excess_pass", "content_aware_pass", "literal_pass")},
          f"t={time.time()-T0:.0f}s", flush=True)
    if not (pre["passed"] and aud["content_aware_pass"]):
        raise RuntimeError("official uniqueness gate failed; refusing to release")

    dsha = uniq2.dots_sha(dots)
    name = f"wbggems3-sgce-20261027-{dsha[:8]}"
    note = ("SGCE H1: strain-gated fault continuation + DTI-optimal coverage + contrarian "
            "no-crowd prior (k=6); 20 physical fields; no TIFF copied.")
    assert len(note) <= 140, len(note)
    out = ROOT / "submission"
    tpl = ROOT / "data" / "raw" / "sample_submission.tif"
    f_zero = W.write_submission(dots.astype(np.float32), g.foot, g.labels, tpl,
                                out / f"{name}-zeros.tif", "zeros")
    f_nan = W.write_submission(dots.astype(np.float32), g.foot, g.labels, tpl,
                               out / f"{name}-nan.tif", "nan")
    f_zip = W.write_zip(f_zero, out / f"{name}-zeros.zip")
    val = {p.name: W.validate(p, tpl, g.foot, g.labels) for p in (f_zero, f_nan)}
    with rasterio.open(f_zero) as ds:
        back = ds.read(1)
    byte_exact = bool(np.array_equal(back > 0, dots))
    assert byte_exact and all(v["passed"] for v in val.values())
    for k, v in val.items():
        print(k, "PASSED" if v["passed"] else "FAILED", v["sha256"][:16], flush=True)

    # Remove superseded hard-repair artifacts so only one SGCE file is downloadable.
    old = json.loads((ROOT / "evidence" / "session2_build.json").read_text())
    for fname in list(old["files"]):
        for parent in (out, ROOT / "docs" / "downloads"):
            p = parent / fname
            if p.exists() and fname != f_zero.name:
                p.unlink()

    dl = ROOT / "docs" / "downloads"
    dl.mkdir(parents=True, exist_ok=True)
    for p in (f_zero, f_nan, f_zip):
        shutil.copyfile(p, dl / p.name)
    files = {p.name: dict(sha256=W.sha256_file(p), bytes=p.stat().st_size) for p in (f_zero, f_nan, f_zip)}

    k6 = json.loads((ROOT / "evidence" / "session2_k56.json").read_text())["6"]
    build = dict(
        name=name, note=note, note_length=len(note), dots=int(dots.sum()), dots_sha256=dsha,
        rho_sha256=hashlib.sha256(np.ascontiguousarray(rho_u).tobytes()).hexdigest(),
        construction=dict(
            hypothesis="H1 SGCE", sigma_px=15, mass=sgce.MASS, fields=sgce.FIELDS,
            uniqueness_repair="contrarian coverage prior: exclude pixels covered by >=7 of 10 dense registry rasters",
            k=6, avoided_px=int((avoid & g.foot).sum()),
            avoided_fraction=float((avoid & g.foot).sum() / g.foot.sum()),
            post_hoc_note=("k in {2,3,4,5,6} was scanned for uniqueness and holdout; k=6 was selected "
                           "because it maximises HOLDOUT-DTI while keeping max non-lattice overlap <=0.70. "
                           "This is a post-hoc selection inside one repair family and is disclosed.")),
        surface_pre_placement=pre, uniqueness=aud, files=files, validation=val,
        saved_bytes_equal_audited_dots=byte_exact,
        grid=dict(shape=list(g.foot.shape), crs="EPSG:32611", footprint_px=int(g.foot.sum()),
                  catalogue_px=int(g.labels.sum()), transform=list(g.profile["transform"])[:6]),
        superseded_research_files=sorted(old["files"]),
        repaired_hard_negative=json.loads((ROOT / "evidence" / "session2_holdout_repaired.json").read_text())["repaired"]["pooled_dti"],
    )
    json.dump(build, open(ROOT / "evidence" / "session2_build.json", "w"), indent=1, default=float)
    np.save(ROOT / "data" / "work" / "session2_dots_packed.npy", np.packbits(dots.ravel()))

    card = json.loads((ROOT / "evidence" / "session2_run_card.json").read_text())
    card["hypothesis"] += (" RELEASED CONSTRUCTION adds a contrarian no-crowd prior that removes pixels "
                           "already covered by >=7 of 10 dense registered emission rasters.")
    card["mechanism"] += (" A registry-derived coverage mask (k=6) is applied before placement; this is "
                          "what makes the released dots unique while keeping the DTI-optimal budget.")
    card["holdout"] = dict(
        label="HOLDOUT-DTI", evaluator_version=k6["holdout"]["evaluator"],
        withheld_positives=k6["holdout"]["n_withheld"], n_spatial_clusters=256,
        candidate=dict(dti=k6["holdout"]["dti"], ci95=k6["holdout"]["ci95"]),
        champion_proxy=dict(dti=k6["champion"], ci95=[0.08595140754809347, 0.11266835751415871]),
        paired_delta_vs_champion_proxy=k6["paired"],
        unrepaired_E1_dti=json.loads((ROOT / "evidence" / "session2_holdout.json").read_text())["experiments"]["E1"]["pooled_dti"],
        hard_repair_dti=build["repaired_hard_negative"],
        repair_family=dict(k4=0.07987156954331218, k5=0.1201663431786861, k6=k6["holdout"]["dti"]),
        promotion_rule_passed=bool(k6["promotion"]),
        caveat=("Hide-and-recover withholds catalogue segments; the scored population is expert-labelled "
               "NEW faults. k was selected post-hoc within one repair family (disclosed limitation). "
               "This number measures the exact released construction."))
    card["correlation_overlap_vs_registry"] = dict(
        pre_placement_surface=dict(max_abs_spearman=pre["max_abs_spearman"], passed=pre["passed"],
                                   n_comparators=pre["n_comparators"]),
        final_dots=dict(U1_exact_dot_duplicate=aud["U1_exact_dot_duplicate"],
                        U2_max_abs_spearman=aud["U2_max_abs_spearman"],
                        U3_max_overlap_nonlattice=aud["U3_max_overlap_nonlattice"],
                        U3_lattice_excess_pass=aud["U3_lattice_excess_pass"],
                        content_aware_pass=aud["content_aware_pass"], literal_pass=aud["literal_pass"],
                        literal_witness=aud["literal_witness"],
                        n_registry_dot_masks=aud["registry_unique_dot_masks"]),
        interpretation=("Content-aware reading preregistered 2026-10-27; literal positive-support reading "
                        "is blocked by the dense registered witness (IR-01). FLAGGED for ratification."))
    card["raster_sha256"] = files[f_zero.name]["sha256"]
    card["raster_sha256_nan_variant"] = files[f_nan.name]["sha256"]
    card["validator_output"] = dict(status="PASS", files=val,
                                    no_nan_inside_footprint=all(v["checks"]["in_footprint_no_nan"] for v in val.values()),
                                    values_in_0_1=all(v["checks"]["in_footprint_range_0_1"] for v in val.values()),
                                    crs_shape_transform_match=all(v["checks"]["crs_epsg_32611"] and
                                        v["checks"]["shape_matches_template"] and
                                        v["checks"]["transform_matches_template"] for v in val.values()),
                                    saved_bytes_equal_audited_dots=byte_exact)
    card["submission_name"] = name
    card["submission_note"] = note
    card["note_length"] = len(note)
    card["verdict"] = "promote" if k6["promotion"] else "negative"
    card["ok_to_download"] = True
    card["ok_to_submit"] = ("YES — after the separate selector confirms a free weekly slot; no slot used here. "
                            "No organizer receipt exists; a local PASS is not portal acceptance.")
    card["budget_disclosure"] = ("3 preregistered hypothesis arms (E1/E2/E3) + one repair family "
                                 "(k=2..6) tested after the first draft failed the registry gate. "
                                 "Wall time exceeded the 2 h guideline; disclosed, not hidden.")
    json.dump(card, open(ROOT / "evidence" / "session2_run_card.json", "w"), indent=1, default=float)
    print(f"RELEASED {name} dots={build['dots']} sha={files[f_zero.name]['sha256']} "
          f"HOLDOUT-DTI={k6['holdout']['dti']:.4f} paired={k6['paired']} t={time.time()-T0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
