def submission_page() -> str:
    if MODE != "submit":
        return page_top("Submission status", "No file is currently cleared.", "See the executive summary and future submission guide; no upload is authorized.") + '<div class="wrap"><p><a href="executive-summary.html">Open executive summary →</a></p></div>'
    r = CAND["raster"]
    g = {x["name"]: x for x in CAND["gates"]}
    g2 = g["G2_final_dot_uniqueness"]["detail"]
    est = g["G4_leaderboard_estimate_gt_0p2778"]["detail"]
    hold = CAND["holdout"]
    tif_name = r["path"].split("/")[-1]
    indep = g["G3_format_portal_range"]["detail"].get("independent", {})
    gate_rows = "".join(
        f'<tr><td>{esc(x["name"].split("_")[0])}</td><td>{esc(x["name"])}</td>'
        f'<td>{"PASS" if x["passed"] else "FAIL"}</td></tr>' for x in CAND["gates"])
    return page_top("Submission status", "Gate-cleared candidate, ready to download.",
                    "Everything below is hash-bound to the saved bytes; every score-like number is labelled for what it is.") + f"""<div class="wrap">
<section class="card"><h2>⬇ The file</h2>
<p><a class="btn" href="downloads/{esc(tif_name)}" download>DOWNLOAD {esc(tif_name)}</a>
<a class="btn secondary" href="downloads/{esc(tif_name.replace('.tif', '.zip'))}" download>DOWNLOAD ZIP</a>
<a class="btn secondary" href="data/{esc(CAND['submission_name'])}.receipt.json" download>Receipt JSON</a></p>
<p>SHA-256 <code>{esc(r['sha256'])}</code> · {r['dots']:,} dots<br>
Name <code>{esc(CAND['submission_name'])}</code> · Note <code>{esc(CAND['note'])}</code> ({CAND['note_chars']} chars)</p>
<p class="small">Independent byte re-read: shape {indep.get('shape_match')} · crs {indep.get('crs_match')} · transform {indep.get('transform_match')} · dtype {esc(str(indep.get('dtype')))} · NaN {indep.get('n_nan')} · Inf {indep.get('n_inf')} · in [0,1] everywhere {indep.get('in_0_1_everywhere')} · zeros outside footprint {indep.get('no_positive_outside_footprint')} · no positives within 2 px of catalogue {indep.get('no_positive_within_collar_2px')} · saved bytes == audited dots {indep.get('saved_dots_equal_design')}</p></section>
<section><div class="section-head"><div class="eyebrow">Preregistered gates</div><h2>G0–G4 passed before any result</h2></div>
<div class="tablewrap" role="region" aria-label="Gate table"><table><thead><tr><th>#</th><th>Gate</th><th>Result</th></tr></thead><tbody>{gate_rows}</tbody></table></div>
<p class="small">G2 details: U1 exact duplicate {g2['U1_exact_duplicate']} · max non-lattice overlap {g2['U3_max_nonlattice_overlap_3px']:.3f} ≤ 0.70 vs {g2['sparse_masks_compared']} sparse masks ({g2['unique_masks_compared']} unique, {g2['total_files_indexed']} files indexed) · lattice excess +{g2['U3_lattice_excess']:.5f} ≤ 0.05 (null {g2['U3_lattice_null_rate']:.5f}) · each focus site ≤ 0.425 · repair gutting {g2['repair_gutted_over_25pct']}.<br>
G4: ESTIMATE {est['cross_fit_mean']:.4f}, bootstrap95 {est['family_bootstrap_95'][0]:.4f}–{est['family_bootstrap_95'][1]:.4f}, instrument family-CV Spearman {est['instrument_family_cv_spearman']:.3f} (RMSE {est['instrument_family_cv_rmse']:.4f}) — an estimate, NOT a score; beats owner-reported 0.2778 (GEMSDOE32) and the 0.3195 reference.<br>
G5 context: {esc(hold['label'])} = {hold['pooled_dti']:.5f}, 95% CI {hold['ci95'][0]:.5f}–{hold['ci95'][1]:.5f}, {hold['n_withheld']:,} withheld, evaluator {esc(hold['evaluator'])} — context only per IR-11 (ρ=0.089 with owner scores); promotion rides on G0–G4.</p></section>
<section class="card"><h3>Disclosures that travel with this file</h3><ul>
<li>The literal “every registry file ≤70%” reading is unpassable for any candidate (IR-01: the registered dense witness covers 100% of the footprint). The preregistered content-aware gates (U1 identity, U3 non-lattice, lattice excess, surface ρ) are the decision rule — disclosed, never silent.</li>
<li>Historical negative record: the 2026-10-27 decision (9b794637) still governs all historical research TIFFs; lane pages remain DO NOT SUBMIT.</li>
<li>Estimates are ESTIMATES; the holdout is a HOLDOUT-DTI measurement; neither is an organizer-confirmed score. Only a DrivenData receipt confirms a score.</li>
<li>Nothing was uploaded; weekly slots used: 0. Spending the slot is a separate, human-owned decision.</li>
<li>Mechanism note: fixed-budget capped CELF, no post-hoc prune (IR-30); E1's prune-based design failed G2 at 0.999 and is archived DO-NOT-SUBMIT in evidence/lbcal_k/.</li>
</ul>
<p class="small"><a href="data/lbcal_k_run_card.json">Run card ↓</a> · <a href="data/preregistration-2026-10-28-lbcalk.md">Preregistration ↓</a> · <a href="data/irregularities-2026-10-28-lbcalk.md">IR-29..31 ↓</a> · <a href="data/adaptive_passes_log.txt">E1 adaptive-pass collapse log ↓</a> · <a href="data/focus_overlap.json">Nine-site overlaps ↓</a> · <a href="data/registry_audit_final.json">Final registry audit ↓</a></p></section>
<section class="card"><h3>How to submit</h3><p>Follow the <a href="how-to-submit.html">submission guide</a>: verify the checksum, use the exact name and note, upload via <a href="https://www.drivendata.org/competitions/306/competition-doe-gems/submissions/">DrivenData</a>, and save the receipt.</p></section>
</div>'''


def render() -> None:
    global MODE, CAND, FOCUS_OVL_DATA
    authority, candidate, recheck, audit, feed = map(read, (AUTHORITY, SGCE_CARD, RECHECK, FOCUS, FEED))
    focus_only, nan_format, zero_format = map(read, (INDEPENDENT_FOCUS, INDEPENDENT_NAN, INDEPENDENT_ZERO))
    historical_gate = evaluate_release_gate(authority, candidate)
    w, c = recheck.get("witness", {}), recheck.get("candidate", {})
    if (historical_gate["okay_to_submit"] or authority.get("verdict") != "negative"
            or authority.get("selector_approval") is not False
            or recheck.get("verdict") != "negative" or recheck.get("approved_for_submission") is not False
            or w.get("universal_blocker") is not True or not w.get("footprint_cells")
            or w.get("witness_positive_inside") != w.get("footprint_cells")
            or c.get("sha256") != SHA_CANDIDATE or c.get("literal_duplicate") is not True
            or c.get("directed_overlap_within_3px_all_positive") != 1.0
            or digest(ROOT / w["registry"]) != w.get("registry_sha256")
            or digest(DOCS / "downloads" / CANDIDATE_FILE) != SHA_CANDIDATE
            or digest(ROOT / "submission" / CANDIDATE_FILE) != SHA_CANDIDATE):
        raise ValueError("Evidence no longer supports the historical negative record; fail closed and review")
    wanted = {"GEMSDOE24", "GEMSDOE25", "GEMSDOE27", "GEMSDOE28", "GEMSDOE30", "GEMSDOE31", "GEMSDOE32", "GEMSDOE33", "GEMSDOE36"}
    independent_rows = focus_only.get("per_file", [])
    nan_file = DOCS / "downloads/wbggems3-sgce-20261027-f52d35d8-nan.tif"
    if (len(independent_rows) != 9 or {r.get("site") for r in independent_rows} != wanted
            or any(r.get("same_grid_as_candidate") is not True for r in independent_rows)
            or focus_only.get("errors") or focus_only.get("n_focus_files_checked") != 9
            or focus_only.get("max_candidate_overlap_with_focus") != max(r["candidate_dots_within_3px_of_focus"] for r in independent_rows)
            or focus_only.get("candidate_sha256") != digest(nan_file)
            or nan_format.get("sha256") != digest(nan_file) or nan_format.get("passed") is not True
            or zero_format.get("sha256") != SHA_CANDIDATE or zero_format.get("passed") is not False):
        raise ValueError("independent focus or format evidence does not match the recorded research bytes")
    rows = audit.get("focus_sites", [])
    if len(rows) != 9 or {r.get("site") for r in rows} != wanted or any(r.get("focus_literal_unique") is not False for r in rows):
        raise ValueError("focus-site audit is incomplete or inconsistent")

    # ---------------- candidate decision (v2, gate-based) -------------------
    card = read(LBCAL_K_CARD)
    v2 = evaluate_release_gate_v2(card, ROOT, prereg_path=PREREG_LBCALK)
    if v2["decision"] == "SUBMIT":
        tif_src = ROOT / card["raster"]["path"]
        zip_src = tif_src.with_suffix(".zip")
        rec_src = tif_src.with_suffix(".json")
        if not (tif_src.is_file() and zip_src.is_file() and rec_src.is_file()
                and digest(tif_src) == card["raster"]["sha256"]):
            raise ValueError("candidate bytes are missing or drifted at publication; fail closed")
        if not FOCUS_OVL.is_file() or read(FOCUS_OVL).get("candidate_sha256") != card["raster"]["sha256"]:
            raise ValueError("focus overlap evidence missing or bound to other bytes; fail closed")
        for site, entry in read(FOCUS_OVL).get("sites", {}).items():
            if entry.get("unique_under_0p70") is not True:
                raise ValueError(f"focus-site uniqueness failed for {site}; fail closed")
        MODE, CAND, FOCUS_OVL_DATA = "submit", card, read(FOCUS_OVL)
        gate = v2
        gate["source_cards"] = {
            "authority": str(LBCAL_K_CARD.relative_to(ROOT)), "authority_sha256": digest(LBCAL_K_CARD),
            "preregistration": str(PREREG_LBCALK.relative_to(ROOT)), "preregistration_sha256": digest(PREREG_LBCALK),
            "focus_overlap": str(FOCUS_OVL.relative_to(ROOT)), "focus_overlap_sha256": digest(FOCUS_OVL),
            "irregularities": str(IRREGULARITIES.relative_to(ROOT)), "irregularities_sha256": digest(IRREGULARITIES),
            "witness_audit": str(RECHECK.relative_to(ROOT)), "witness_audit_sha256": digest(RECHECK),
            "historical_negative_authority": str(AUTHORITY.relative_to(ROOT)),
            "historical_negative_authority_sha256": digest(AUTHORITY),
        }
        gate["historical_record"] = (
            "The 2026-10-27 negative decision (session_9b794637) remains valid under the literal "
            "all-registry reading (IR-01) and still governs every historical research TIFF; the "
            "preregistered content-aware gates of 2026-10-28 govern the NEW candidate only.")
        decision_json = {"decision": "SUBMIT", "okay_to_download_and_submit": True, "okay_to_submit": True,
                         "candidate": gate["candidate"], "selector_slot_spend": gate["selector_slot_spend"],
                         "source": "release_gate.json"}
        publish_mode_note = "Built gate-cleared candidate pages; historical lane pages quarantined DO NOT SUBMIT."
    else:
        gate = historical_gate
        gate["source_cards"] = {"authority": str(AUTHORITY.relative_to(ROOT)), "authority_sha256": digest(AUTHORITY),
                                "candidate": str(SGCE_CARD.relative_to(ROOT)), "candidate_sha256": digest(SGCE_CARD),
                                "witness_audit": str(RECHECK.relative_to(ROOT)), "witness_audit_sha256": digest(RECHECK)}
        gate["blocking_reasons"].insert(0, "The registered dense witness overlaps every in-footprint candidate; SGCE's measured overlap is 100%.")
        decision_json = {"decision": "DO-NOT-SUBMIT", "okay_to_submit": False,
                         "candidate": None, "source": "release_gate.json"}
        publish_mode_note = "Built negative evidence-first pages and quarantined historical lane pages."

    data = DOCS / "data"
    data.mkdir(parents=True, exist_ok=True)
    (data / "release_gate.json").write_text(json.dumps(gate, indent=2, allow_nan=False) + "\n")
    (data / "decision.json").write_text(json.dumps(decision_json, indent=2, allow_nan=False) + "\n")
    for path in (AUTHORITY, RECHECK, FOCUS, FEED, INDEPENDENT_FOCUS, INDEPENDENT_NAN, INDEPENDENT_ZERO):
        shutil.copyfile(path, data / path.name)
    shutil.copyfile(AUTHORITY, data / "run_card.json")
    if MODE == "submit":
        shutil.copyfile(LBCAL_K_CARD, data / "lbcal_k_run_card.json")
        shutil.copyfile(PREREG_LBCALK, data / "preregistration-2026-10-28-lbcalk.md")
        shutil.copyfile(IRREGULARITIES, data / "irregularities-2026-10-28-lbcalk.md")
        for extra in ("canary.json", "preplacement_surface.json", "registry_audit_final.json",
                      "focus_overlap.json", "run_card_e1.json", "adaptive_passes_log.txt"):
            src_path = ROOT / "evidence" / "lbcal_k" / extra
            if not src_path.is_file():
                raise ValueError(f"missing candidate evidence artefact: {src_path}")
            shutil.copyfile(src_path, data / extra)
        for suffix in (".tif", ".zip", ".json"):
            shutil.copyfile((ROOT / card["raster"]["path"]).with_suffix(suffix),
                            DOCS / "downloads" / Path(card["raster"]["path"]).with_suffix(suffix).name)
    for _, (_, _, card_name) in LANES.items():
        path = ROOT / "evidence" / card_name
        if not path.is_file():
            raise ValueError(f"missing historical lane card: {path}")
        historical = read(path)
        notice = "SUPERSEDED historical lane record; its claims were not replayed in this review and do not authorize an upload. See release_gate.json."
        prior_notice = historical.pop("_archive_notice", None)
        historical = {"_archive_notice": notice + (" " + prior_notice if prior_notice else ""), **historical}
        (data / card_name).write_text(json.dumps(historical, indent=2, allow_nan=False) + "\n")
    old = {"_archive_notice": "SUPERSEDED historical lane claims; no repository-wide upload approval. See release_gate.json.", **candidate}
    (data / "session2_run_card.json").write_text(json.dumps(old, indent=2, allow_nan=False) + "\n")
    pages = {"index.html": ("Overview", home(audit, feed)), "executive-summary.html": ("Executive summary", executive(audit)),
             "how-to-submit.html": ("Submission guide", howto()), "research.html": ("Research", research()),
             "evidence.html": ("Evidence", evidence_page(recheck, focus_only)),
             "submission.html": ("Submission", submission_page())}
    decision_meta = "SUBMIT" if MODE == "submit" else "DO-NOT-SUBMIT"
    for name, (title, body) in pages.items():
        (DOCS / name).write_text(layout(title, name, body, decision=decision_meta), encoding="utf-8")
    (DOCS / "downloads/index.html").write_text(downloads_index(), encoding="utf-8")
    for directory, (names, title, card_name) in LANES.items():
        for name in names:
            (DOCS / directory / name).write_text(lane_stub(directory, title, card_name), encoding="utf-8")
    for directory in ("lbcal", "thcs"):
        path = DOCS / directory / "downloads" / "index.html"
        path.write_text('<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Research archive</title></head><body><h1>DO NOT SUBMIT</h1><p>Historical research files only; no candidate is cleared. <a href="../../executive-summary.html">Current executive summary</a>.</p></body></html>', encoding="utf-8")
    print(publish_mode_note)
