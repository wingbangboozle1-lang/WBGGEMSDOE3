#!/usr/bin/env python3
"""LBCAL lane summary: nine-site table, candidate re-estimates, lane decision (2026-10-27).

Lane-scoped: it never rewrites the repository-wide decision owned by the main
site (docs/data/decision.json + docs/data/release_gate.json); it adds the LBCAL
lane's own evidence and an independent ESTIMATE for every candidate, including
the files other lanes merged to main the same day.  Needs the ignored caches.
Writes:

  evidence/focus_sites_2026-10-27.json   nine-site table (best file, owner score, LBCAL
                                         estimate, pairwise 3 px overlap, uniqueness)
  evidence/candidates_2026-10-27.json    every candidate this repo ever produced, re-estimated
  evidence/lbcal_lane_decision.json      the LBCAL lane's decision card (lane scope only)
  evidence/lbcal/registry_delta_main.json  uniqueness of the LBCAL TIF vs rasters merged to main later
  evidence/leaderboard_snapshot_2026-10-27T1905Z.json
  docs/lbcal/data/*.json                 copies for the lane pages (scripts/build_site_lbcal.py)
  docs/lbcal/downloads/<LBCAL tif/zip>   research-only artefact (DO-NOT-SUBMIT in the name)
"""
from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import binary_dilation

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from lbcal import coverage as COV, data as D, features as F, model as Mdl  # noqa: E402

FOCUS = ["GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE30", "GEMSDOE31", "GEMSDOE32",
         "GEMSDOE33", "GEMSDOE36"]
OWNER = "buffedlizard55-lab"
DISK = (lambda r: (np.add.outer(np.arange(-r, r + 1) ** 2, np.arange(-r, r + 1) ** 2) <= r * r))(3)
EV = ROOT / "evidence"
DOCS = ROOT / "docs"
LANE = DOCS / "lbcal"
MAIN_NEW = [  # candidate rasters other lanes merged to main on 2026-10-27 (after this lane's registry scan)
    ("score-tomography lane (main decision: SUBMIT-WITH-CAVEAT)", "submission/wbggems3-tde30k-tomography-emission-20261027T1853Z-e756a162-zeros.tif"),
    ("session-1f0b051d lidar dipole lane (negative)", "submission/wbg3-dipolehybrid-40000d-20261027-e8535621-zeros.tif"),
]


def jload(p):
    return json.loads(Path(p).read_text())


def main() -> int:
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    meta = jload(D.CACHE / "dataset_meta.json")
    ds = np.load(D.CACHE / "dataset.npz")
    var = jload(EV / "lbcal_variants.json")
    sel = var["selected"]
    beta, pi_max = np.array(var["variants"][sel]["beta"]), var["variants"][sel]["pi_max"]
    M, _ = Mdl.design_matrix()
    N = np.array([m["N"] for m in meta])
    est_all = Mdl.predict(beta, M, ds["C"].astype(float), ds["P"].astype(float), N, ds["n_px"], pi_max=pi_max)[0]
    cv = jload(EV / "lbcal_cv.json")
    cvb = var["variants"][sel]["cv_pred"]
    cv_by = {(r["site"], r["submission"]): (r["family_cv_estimate"], cvb[j]) for j, r in enumerate(cv["observations"])}
    # identical decoded arrays were de-duplicated before fitting; reuse the estimate of the first copy
    arr = {m["array_sha256"]: cv_by[(m["site"], m["submission"])] for m in meta if (m["site"], m["submission"]) in cv_by}
    for m in meta:
        if m["score"] is not None and (m["site"], m["submission"]) not in cv_by and m["array_sha256"] in arr:
            cv_by[(m["site"], m["submission"])] = arr[m["array_sha256"]]
    live = {r.get("sha256"): r for r in jload(ROOT / "registry" / "upstream_live_ledger_rasters.json")["rows"] if r.get("sha256")}
    grid = D.load_grid()
    foot = grid.foot

    # ---------------- nine focus sites ----------------
    best = []
    for site in FOCUS:
        rows = [(i, m) for i, m in enumerate(meta) if m["site"] == site and m["score"] is not None]
        i, m = max(rows, key=lambda t: t[1]["score"])
        lv = live.get(m["sha256"], {})
        url = (f"https://github.com/{OWNER}/{lv['repo']}/raw/{lv['ref']}/{lv['path']}" if lv.get("ref") else None)
        unb, bnd = cv_by.get((site, m["submission"]), (None, None))
        best.append(dict(site=site, submission=m["submission"], file=Path(lv.get("path", m["local"])).name,
                         download_url=url, sha256=m["sha256"], owner_reported=m["score"], dots=m["n_pos"],
                         lbcal_family_cv_estimate=bnd, lbcal_unbounded_cv_estimate=unb, local=m["local"],
                         identical_array_of=(meta[m["duplicate_of"]]["site"] + "/" + meta[m["duplicate_of"]]["submission"]
                                             if m.get("duplicate_of") is not None else None),
                         other_scored_files=len(rows) - 1))
    dots = []
    for b in best:
        with rasterio.open(ROOT / b["local"]) as src:
            a = src.read(1)
        dots.append(np.isfinite(a) & (a > 0) & foot)
    halos = [binary_dilation(d, structure=DISK) for d in dots]
    n = len(best)
    ov = [[None] * n for _ in range(n)]
    for i in range(n):
        for j in range(n):
            if i != j:
                ov[i][j] = round(float(halos[j][dots[i]].mean()), 4)
    for i, b in enumerate(best):
        worst = max((ov[i][j], best[j]["site"]) for j in range(n) if j != i)
        b["max_forward_overlap_vs_other_focus"] = worst[0]
        b["max_overlap_with"] = worst[1]
        b["unique_vs_other_focus_sites"] = bool(worst[0] <= 0.70)
        b["ok_to_resubmit"] = False
        b["why_not"] = "already scored (owner-reported); a byte copy earns no new information and is not unique"
        b.pop("local")
    focus = dict(evidence_class="REGISTRY-MEASUREMENT on hash-pinned bytes; scores OWNER-REPORTED; estimates ESTIMATE",
                 generated_utc=now, overlap_rule="forward overlap = share of row-file dots within 3 px of column-file dots; >0.70 = duplicate",
                 sites=best, pairwise_forward_overlap=dict(order=[b["site"] for b in best], matrix=ov),
                 best_overall=max(best, key=lambda b: b["owner_reported"])["site"])
    (EV / "focus_sites_2026-10-27.json").write_text(json.dumps(focus, indent=1) + "\n")

    # ---------------- this repo's candidates, re-estimated ----------------
    lb = jload(EV / "lbcal_run_card.json")
    hce = jload(EV / "hce_run_card.json") if (EV / "hce_run_card.json").exists() else {}
    cands = []
    labels = {
        "wbggemsdoe3-skarpline-union": ("skarpline lane (its 0.428 ESTIMATE came from an 11-file fit)", "WITHDRAWN (all lanes agree)"),
        "wbggems3-hce1-congruence": ("HCE-1 lane (ledger projection 0.082)", "research file; not the file cleared on main"),
        "wbggems3-cspes-edgestab": ("CSPES lane", "negative"),
        "wbggems3-lst1-hybrid": ("LST1 lane", "negative"),
        "wb-gems-doe-3-stepover-damagezone": ("legacy", "legacy, DO NOT SUBMIT"),
        "wb-gems-doe-3-latest-submission": ("legacy alias of stepover-damagezone", "legacy, DO NOT SUBMIT"),
    }
    for i, m in enumerate(meta):
        if m["source"] != "this-repo":
            continue
        lab = next((v for k, v in labels.items() if m["submission"].startswith(k)), ("", ""))
        cands.append(dict(file=m["local"], sha256=m["sha256"], dots=m["n_pos"], lbcal_estimate=round(float(est_all[i]), 4),
                          lane=lab[0], status=lab[1]))
    cands.append(dict(file=lb["file"]["path"], sha256=lb["file"]["sha256"], dots=lb["file"]["dots"],
                      lbcal_estimate=lb["estimate"]["cross_fit_mean"], lane="LBCAL (this session)",
                      status="negative (failed holdout + like-for-like uniqueness)"))
    feats = np.load(D.CACHE / "features.npz")
    for lane_name, rel in MAIN_NEW:
        pth = ROOT / rel
        if not pth.is_file():
            continue
        p, _ = D.read_prediction(pth)
        st = COV.stats(p, foot, feats["cell"], F.n_cells(), feats["d_cat_px"])
        y = float(Mdl.predict(beta, M, st["C"][None], st["P"][None], np.array([st["N"]]), ds["n_px"], pi_max=pi_max)[0][0])
        cands.append(dict(file=rel, sha256=D.sha256_file(pth), dots=st["n_pos"], lbcal_estimate=round(y, 4),
                          lane=lane_name, status="see that lane's card (not this lane's decision)"))
    others = []
    for i, m in enumerate(meta):
        if m["score"] is None and m["source"] != "this-repo":
            others.append(dict(site=m["site"], submission=m["submission"], sha256=m["sha256"],
                               lbcal_estimate=round(float(est_all[i]), 4)))
    (EV / "candidates_2026-10-27.json").write_text(json.dumps(dict(
        evidence_class="ESTIMATE (bounded LBCAL model, in-sample for training rasters; never a score)",
        model=sel, generated_utc=now, this_repo=cands, unscored_peer_rasters=others), indent=1) + "\n")

    # ---------------- leaderboard snapshot ----------------
    snap = dict(evidence_class="PUBLIC-LEADERBOARD OBSERVATION (agent read of the official page); not a receipt",
                source="https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/",
                observed_utc="2026-10-27T19:05Z",
                rows=[dict(rank=1, team="xiaofanhu", public_dti=0.4544), dict(rank=2, team="cfld__", public_dti=0.3916),
                      dict(rank=3, team="Batik Shirt Brothers", public_dti=0.3911),
                      dict(rank=4, team="BrandenKMurray", public_dti=0.3724),
                      dict(rank=5, team="No Fault of Our Own", public_dti=0.3566),
                      dict(rank=10, team=None, public_dti=0.3379), dict(rank=22, team=None, public_dti=0.3261)],
                repo_observations=dict(rank_25=0.3195, rank_48=0.2892,
                                       source="evidence/leaderboard_observation_2026-10-27.json"),
                user_brief_figures=dict(earlier_high=0.4413, called_highest_now=0.3195,
                                        status="both stale: 0.4544 leads; 0.3195 was rank #25"),
                implication="Top-5 public currently needs >= 0.3566; the best owner-reported file (0.2778) is below rank #48.")
    (EV / "leaderboard_snapshot_2026-10-27T1905Z.json").write_text(json.dumps(snap, indent=1) + "\n")

    # ---------------- uniqueness of the LBCAL TIF vs rasters merged to main later ----------------
    lb_tif = ROOT / lb["file"]["path"]
    with rasterio.open(lb_tif) as src:
        mine = (src.read(1) > 0) & foot
    allowed = foot & ~grid.cat
    delta = []
    for lane_name, rel in MAIN_NEW:
        pth = ROOT / rel
        if not pth.is_file():
            continue
        with rasterio.open(pth) as src:
            a_ = src.read(1)
        t = np.isfinite(a_) & (a_ > 0) & foot
        halo = binary_dilation(t, structure=DISK)
        fo = float(halo[mine].mean())
        rev = float(binary_dilation(mine, structure=DISK)[t].mean()) if t.any() else 0.0
        delta.append(dict(file=rel, lane=lane_name, their_dots=int(t.sum()), my_dots_within_3px_of_theirs=round(fo, 4),
                          their_dots_within_3px_of_mine=round(rev, 4), halo_share_of_allowed=round(float(halo[allowed].mean()), 4),
                          jaccard=round(float((mine & t).sum() / max(1, (mine | t).sum())), 4), duplicate_by_overlap=bool(fo > 0.70)))
    (EV / "lbcal" / "registry_delta_main.json").write_text(json.dumps(dict(
        evidence_class="REGISTRY-MEASUREMENT on the saved LBCAL bytes vs rasters merged to main after the lane's scan",
        rule="forward overlap > 0.70 = duplicate", rows=delta), indent=1) + "\n")

    # ---------------- LBCAL lane decision card (lane scope) ----------------
    conc = jload(EV / "lbcal_gate_concordance.json")
    post = jload(EV / "lbcal" / "postcheck.json")["summary"]
    tif = Path(lb["file"]["path"])
    (LANE / "downloads").mkdir(parents=True, exist_ok=True)
    for suf in (".tif", ".zip"):
        shutil.copy2(ROOT / tif.with_suffix(suf), LANE / "downloads" / tif.with_suffix(suf).name)
    tde = next((c for c in cands if "tde30k" in c["file"]), None)
    card = dict(
        schema="LBCAL lane decision card v1 (lane scope; the repository decision lives in docs/data/decision.json)",
        generated_utc=now, session_branch="arena/88400903-wbggemsdoe3",
        evidence_class="Aggregates REGISTRY-MEASUREMENT, HOLDOUT-DTI and ESTIMATE labels from the linked cards; no ORGANIZER-CONFIRMED score",
        verdict="negative", lane_decision="DO NOT SUBMIT the LBCAL file", ok_to_submit=False,
        decision_reason=("The LBCAL design fails two pre-registered gates: HOLDOUT-DTI 0.0631 < 0.1292 (owner rule) and "
                         "like-for-like uniqueness (4 informative dense-raster firings)."),
        hypothesis=lb["hypothesis"], mechanism=lb["mechanism"], named_non_fault_mimic=lb["non_fault_mimic"],
        holdout_dti=lb["holdout"], estimate=lb["estimate"], registry=dict(
            pre_placement_worst_rho=lb["registry"]["pre_placement_surface"]["worst_rho"],
            final_like_for_like=lb["registry"]["final_dots_like_for_like"], post_hoc=post, delta_vs_main=delta),
        leakage_canary=lb["leakage_canary"], raster_sha256=lb["file"]["sha256"], sha256=lb["file"]["sha256"],
        validator_output=lb["validator"], submission_name=lb["submission_name"], submission_note=lb["note"],
        download=dict(tif=str(tif), zip=str(tif.with_suffix(".zip")), cleared=False, label="RESEARCH ONLY — DO NOT SUBMIT"),
        gate_concordance=dict(n=conc["n"], spearman_holdout_vs_public=round(conc["spearman_holdout_vs_score"], 3),
                              spearman_lbcal_cv_vs_public=round(conc["spearman_lbcal_cv_vs_score"], 3),
                              source="evidence/lbcal_gate_concordance.json"),
        independent_estimate_of_main_cleared_file=(dict(file=tde["file"], lbcal_estimate=tde["lbcal_estimate"],
                                                        note="ESTIMATE from the bounded LBCAL model (in-sample density; file not in training)")
                                                   if tde else None),
        candidates="evidence/candidates_2026-10-27.json", focus_sites="evidence/focus_sites_2026-10-27.json",
        experiments=3, slots_spent=0, selector_approval=None,
    )
    (EV / "lbcal_lane_decision.json").write_text(json.dumps(card, indent=1) + "\n")
    (LANE / "data").mkdir(parents=True, exist_ok=True)
    shutil.copy2(EV / "lbcal_lane_decision.json", LANE / "data" / "lbcal_lane_decision.json")
    for src in ("lbcal_run_card.json", "focus_sites_2026-10-27.json", "candidates_2026-10-27.json",
                "leaderboard_snapshot_2026-10-27T1905Z.json", "lbcal_gate_concordance.json", "lbcal_variants.json"):
        shutil.copy2(EV / src, LANE / "data" / src)
    shutil.copy2(EV / "lbcal" / "registry_delta_main.json", LANE / "data" / "registry_delta_main.json")
    cvs = {k: v for k, v in cv.items() if k not in ("estimates", "observations")}
    (LANE / "data" / "lbcal_cv_summary.json").write_text(json.dumps(cvs, indent=1) + "\n")
    print(json.dumps(dict(focus=[(b["site"], b["owner_reported"], b["lbcal_family_cv_estimate"],
                                  b["max_forward_overlap_vs_other_focus"]) for b in best],
                          candidates=[(Path(c["file"]).name[:40], c["lbcal_estimate"], c["status"]) for c in cands]),
                     indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
