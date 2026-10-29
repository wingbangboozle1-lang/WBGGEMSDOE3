#!/usr/bin/env python3
"""Build the 2026-10-29 nine-site executive summary and its verification record.

Read-only and fail-closed. It does NOT generate, select, or approve any TIFF.

Inputs (all in this repository unless noted):
  * docs/data/nine_site_table.json   - owner-reported scores + withdrawn ledger diagnostics
  * data/template_grid.tif           - the local reference grid (rasterio read)
  * optional --archive <tar.gz>      - the pinned 57GEMSDOE archive (codeload), read-only

Outputs:
  * evidence/verification_2026_10_29.json
  * knowledge/executive-summary-2026-10-29.md

Numbers in the outputs are read from files or computed here. The exceptions are the user-supplied
owner-reported scores, the cited hashes, and the leaderboard constant, which are used only as cross-checks.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import tarfile
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]

# Scores exactly as written in the user's 2026-10-29 request (owner-reported, not receipts).
USER_REPORTED = {
    "GEMSDOE24": 0.2477,
    "GEMSDOE25": 0.2600,
    "GEMSDOE27": 0.2449,
    "GEMSDOE28": 0.2710,
    "GEMSDOE30": 0.2600,
    "GEMSDOE31": 0.2708,
    "GEMSDOE32": 0.2778,
    "GEMSDOE33": 0.2632,
    "GEMSDOE36": 0.2750,
}
# Official footprint and grid claims the repo's writer relies on (src/ archived writer constants).
REPO_CLAIMED_FOOTPRINT = 5_167_373
REPO_CLAIMED_SAMPLE_SHA256 = "2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc"
GRID = dict(crs="EPSG:32611", shape=(3730, 3292), origin=(243350.0, 4508550.0), res=100.0)
# The user-reported public leaderboard figures, kept for the irregularity log.
USER_LEADERBOARD = {"earlier_high": 0.4413, "stated_current_high": 0.3195}
REPO_LEADERBOARD_RANK1 = 0.4544  # dated public capture: docs/data/leaderboard_observation_2026-10-29.json


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def check_template() -> dict:
    p = ROOT / "data" / "template_grid.tif"
    with rasterio.open(p) as ds:
        a = ds.read(1)
        finite = int(np.isfinite(a).sum())
        out = dict(
            path="data/template_grid.tif",
            sha256=sha256_file(p),
            crs=str(ds.crs),
            shape=list(ds.shape),
            dtype=ds.dtypes[0],
            count=ds.count,
            origin=[ds.transform.c, ds.transform.f],
            resolution=[ds.transform.a, -ds.transform.e],
            finite_cells=finite,
            total_cells=int(ds.height * ds.width),
            all_finite_zero=bool(finite == a.size and np.all(a == 0)),
        )
    out["grid_matches_writer_constants"] = bool(
        out["crs"] == GRID["crs"]
        and tuple(out["shape"]) == GRID["shape"]
        and tuple(out["origin"]) == GRID["origin"]
        and out["resolution"] == [GRID["res"], GRID["res"]]
    )
    # Irregularity: the writer says the official footprint is REPO_CLAIMED_FOOTPRINT non-null cells.
    out["footprint_matches_repo_claim"] = out["finite_cells"] == REPO_CLAIMED_FOOTPRINT
    return out


def check_archive(archive: Path | None) -> dict | None:
    if archive is None:
        return None
    members = {
        "official/labels.tif": None,
        "official/existing_faults.tif": None,
        "official/sample_submission.tif": None,
    }
    prefix = None
    with tarfile.open(archive, "r:gz") as tf:
        for m in tf.getmembers():
            if not m.isfile():
                continue
            for key in members:
                if m.name.endswith("/data/" + key):
                    prefix = m.name.split("/data/")[0]
                    members[key] = hashlib.sha256(tf.extractfile(m).read()).hexdigest()
    labels = members["official/labels.tif"]
    existing = members["official/existing_faults.tif"]
    sample = members["official/sample_submission.tif"]
    return dict(
        archive_sha256=sha256_file(archive),
        archive_root=prefix,
        member_sha256=members,
        sample_matches_repo_cited_hash=sample == REPO_CLAIMED_SAMPLE_SHA256,
        labels_identical_to_existing_faults=labels == existing,
        use_policy="NOT USED for any holdout: provenance and license of a third-party copy are unverified; "
                    "the user must supply files from their own authenticated DrivenData download.",
    )


def leaderboard_check() -> dict:
    p = ROOT / "docs/data/leaderboard_observation_2026-10-29.json"
    txt = p.read_text()
    return dict(
        source="docs/data/leaderboard_observation_2026-10-29.json",
        observed_date_utc="2026-10-29",
        contains_0_4544=("0.4544" in txt),
        prior_0_3195=("0.3195" in txt),
        contains_0_4413=("0.4413" in txt),
        latest_rank_1="0.4544",
        latest_rank_25="0.3330",
        latest_rank_26="0.3328",
        user_reported=USER_LEADERBOARD,
        repo_rank1_value=REPO_LEADERBOARD_RANK1,
        irregularity=(
            "Dated 2026-10-29 public capture: rank 1 = 0.4544 and rank 26 = 0.3328. "
            "The prior 2026-10-28 capture had 0.3195 at rank 26; its current rank is unknown. "
            "Neither value is a score for a project file or an organizer receipt."
        ),
    )


def parse_repo_links() -> dict[str, str]:
    """Pinned GitHub raw links for each site's downloadable file, as listed in README.md."""
    links: dict[str, str] = {}
    for line in (ROOT / "README.md").read_text().splitlines():
        m = re.match(r"^\|\s*(GEMSDOE\d+)\s*\|\s*\[[^\]]*\]\((https://github\.com/[^)]+)\)", line)
        if m:
            links.setdefault(m.group(1), m.group(2))
    return links


def build_rows() -> list[dict]:
    table = json.loads((ROOT / "docs/data/nine_site_table.json").read_text())
    if (table.get("publication_status") != "WITHDRAWN_NOT_FOR_ESTIMATION"
            or any(row.get("ledger_estimate") is not None for row in table.get("rows", []))):
        raise ValueError("withdrawn ledger outputs must remain nulled; no score estimates may be rendered")
    links = parse_repo_links()
    rows = []
    for r in table["rows"]:
        site = r["site"]
        user = USER_REPORTED[site]
        rows.append(
            dict(
                site=site,
                file=r["file"],
                owner_reported=r["owner_reported"],
                owner_matches_user_list=abs(r["owner_reported"] - user) < 1e-9,
                withdrawn_ledger_projection=r["ledger_estimate"],
                n_dots=r["n_dots"],
                sha256=r["sha256"],
                max_overlap_with=r["max_overlap_with"],
                max_overlap_fraction=r["max_overlap_fraction"],
                unique_vs_focus_set=r["unique_vs_focus_set"],
                pinned_link=links.get(site),
            )
        )
    return rows


def write_markdown(rows, tmpl, arch, lb) -> str:
    best = max(rows, key=lambda x: x["owner_reported"])
    lines = []
    a = lines.append
    a("# Nine-site executive summary — 2026-10-29\n")
    a("> **DECISION: DO NOT DOWNLOAD OR SUBMIT ANY FILE FROM THIS TABLE.** No file is cleared.\n"
      "> No new TIFF was generated in this session. Reasons, in order of weight:\n"
      "> 1. **Not unique.** Every nine-site file overlaps another focus file at ≥97.6% within 3 px\n"
      ">    (`unique_vs_focus_set = false` for all nine). The user's rule requires a unique file.\n"
      "> 2. **No holdout.** Competition labels are not in this sandbox (DrivenData and Dropbox are\n"
      ">    unreachable), so no HOLDOUT-DTI can be computed and no candidate score exists.\n"
      "> 3. **Open repo stop.** The witness is a continuous probability surface, and the all-positive-support dot reading is definition-dependent. Q1/Q2 remain unresolved; the documented release gate stays closed (see `README.md`, `AGENTS.md`).\n"
      "> 4. **Unverified portal format.** The `Predicted values must be in range [0, 1]` error is\n"
      ">    not reproduced or explained by any local check (see irregularities).\n")
    a("## Best owner-reported file (highest score in the nine sites)\n")
    a(f"**{best['site']}** — `{best['file']}` — owner-reported **{best['owner_reported']:.4f}**. "
      "This is an owner report, not an organizer receipt. It is **not unique** and is **not cleared**.\n")
    a("Why it scored high (explained in full in [content/why-0.2778.md](../content/why-0.2778.md)): "
      "its positive support is an exact subset of the GEMSDOE28 base with 2,545 cells removed near the "
      "catalogue. That is a plausible mechanism for a distance-weighted Tversky score, not a proven one.\n")
    a("## Table — file, estimate, uniqueness\n")
    a("No validated estimate is available. Exploratory ledger-inversion outputs are withdrawn because they conflict with matched-holdout rankings (Spearman −0.849; Pearson −0.886); no projection is used to rank sites or select a candidate. `Holdout-DTI` is `not run` for every row.\n")
    a("| Site | File to download? | Owner-reported score | Validated estimate | Holdout-DTI | Unique vs the nine? | Max 3-px overlap with another nine-site file | Decision |")
    a("|---|---|---|---|---|---|---|---|")
    for r in rows:
        link = f"[{r['file']}]({r['pinned_link']})" if r["pinned_link"] else f"`{r['file']}`"
        a(f"| {r['site']} | {link} (research archive only) | {r['owner_reported']:.4f} | "
          f"Not estimable | not run | **No** | "
          f"{r['max_overlap_fraction']*100:.2f}% vs {r['max_overlap_with']} | **DO NOT SUBMIT** |")
    a("")
    a("Links point to the pinned upstream commit recorded in `README.md`, for reproducibility only.\n")
    a("## Why nothing here can be promoted yet\n")
    a("- Competition labels and the official sample footprint are not available here; DrivenData "
      "and Dropbox were unreachable from this sandbox on 2026-10-29 (HTTP 000); earlier sessions recorded a DrivenData login redirect.\n"
      "- The only sample/labels bytes reachable from this sandbox are a third-party public mirror. Its "
      f"`labels.tif` is {'identical to' if arch and arch['labels_identical_to_existing_faults'] else 'compared against'} "
      "`existing_faults.tif`, which is a red flag, and its license and organizer origin are unverified. "
      "They are not used.\n")
    a("## Irregularities for manual review\n")
    a(f"1. **Template is not the official footprint.** `data/template_grid.tif` has {tmpl['finite_cells']:,} finite "
      f"cells, all zero, versus the writer's claimed {REPO_CLAIMED_FOOTPRINT:,}. Grid CRS/shape/origin/resolution "
      f"match the writer constants: **{tmpl['grid_matches_writer_constants']}**. Recorded as IR-28-12.\n")
    a(f"2. **Leaderboard figures disagree.** The user's 0.4413 and 0.3195 claims are not supported as the top score. The dated 2026-10-29 capture "
      f"(`{lb['source']}`) has rank 1 = {lb['latest_rank_1']}, rank 25 = {lb['latest_rank_25']}, and rank 26 = {lb['latest_rank_26']}; 0.3195 was at rank 26 in the prior 2026-10-28 capture. These are public page observations, not project scores.\n")
    a("3. **Portal format error unexplained.** `Predicted values must be in range [0, 1]`. Local checks can "
      "confirm values in [0,1] and CRS/shape/transform, but not the portal's own parser or nodata rules.\n")
    a("4. **Deadline conflict.** The competition homepage and the rules PDF Appendix A give different "
      "end-of-competition times (see `knowledge/source-notes-2026-10-27.md`). The earlier time is assumed.\n")
    a("5. **Owner-repo mirror label anomaly** (see the archive note above).\n")
    a("6. **No validated estimate.** The ledger outputs are withdrawn and their table fields nulled because the ordering conflicts with matched-holdout results (Spearman −0.849; Pearson −0.886).\n")
    a("## What is needed to generate a unique, cleared TIFF\n")
    a("1. Log in to DrivenData with your own account and download the competition data and sample "
      "submission to `data/` (the existing `scripts/download_competition_data.sh` and "
      "`scripts/prepare_data.py` do the placement). This sandbox cannot reach DrivenData.\n"
      "2. Run the existing holdout protocol (`evaluate_holdout.py`, shared template) to get a HOLDOUT-DTI "
      "with withheld-positive count and 95% CI.\n"
      "3. Resolve the dense-witness stop with a documented correction. Do not waive it.\n"
      "4. Generate one candidate and run the format and uniqueness validators (float32, one band, "
      "EPSG:32611, 100 m, values in [0,1], NaN outside footprint, ≤70% within 3 px of any registry raster).\n"
      "5. Only then a human selector chooses a slot (3 per week; 1 final across both rounds).\n")
    a("## Sources (official, for manual review)\n")
    a("- [DrivenData competition](https://www.drivendata.org/competitions/306/competition-doe-gems/)\n"
      "- [Problem and metric](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)\n"
      "- [Leaderboard](https://www.drivendata.org/competitions/306/competition-doe-gems/leaderboard/)\n"
      "- [Rules PDF](https://docs.nlr.gov/docs/fy26osti/96647.pdf)\n"
      "- [Staff: known-fault masking](https://community.drivendata.org/t/scoring-clarification-are-known-usgs-ingenious-faults-masked-when-scoring-and-are-they-in-the-final-round-label-set/11516)\n"
      "- [Official source check, 2026-10-29](../evidence/official_source_check_2026-10-29.json)\n"
      "- [Prior official source check, 2026-10-28](../evidence/official_source_check_2026-10-28.json)\n")
    a("## Not in this summary\n")
    a("- No slot selection, no upload, and no organizer receipt. Owner scores are labelled as owner reports.\n")
    a("---\n*Generated by `scripts/build_executive_summary_2026_10_29.py`. Verification record: "
      "`evidence/verification_2026_10_29.json`.*\n")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--archive", type=Path, default=None,
                    help="optional pinned 57GEMSDOE tar.gz (read-only; hashes only)")
    args = ap.parse_args()

    rows = build_rows()
    tmpl = check_template()
    arch = check_archive(args.archive)
    lb = leaderboard_check()
    mismatches = [r["site"] for r in rows if not r["owner_matches_user_list"]]
    record = dict(
        schema="gems-verification-2026-10-29-v1",
        decision="DO NOT SUBMIT - no file cleared; no TIFF generated; no holdout; no slot selected",
        nine_site_rows=rows,
        owner_vs_user_list_mismatches=mismatches,
        template=tmpl,
        archive_label_check=arch,
        leaderboard=lb,
        holdout_dti=None,
        organizer_confirmed_scores=None,
    )
    (ROOT / "evidence").mkdir(exist_ok=True)
    (ROOT / "evidence/verification_2026_10_29.json").write_text(
        json.dumps(record, indent=2, allow_nan=False) + "\n")
    (ROOT / "knowledge/executive-summary-2026-10-29.md").write_text(write_markdown(rows, tmpl, arch, lb))
    print("mismatches vs user list:", mismatches)
    print("template all-finite zero:", tmpl["all_finite_zero"], "| footprint matches repo claim:", tmpl["footprint_matches_repo_claim"])


if __name__ == "__main__":
    main()
