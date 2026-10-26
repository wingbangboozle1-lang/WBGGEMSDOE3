#!/usr/bin/env python3
"""Assemble the current static site without overwriting authored source pages.

The former concurrent builder wrote into docs/ and could replace the active
summary with an older snapshot. Its original is archived. This assembler copies
only the active site and non-submission evidence; it does not publish old TIFFs.
"""
from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE_FILES = (
    "index.html",
    "assets/style.css", "assets/app.js",
    "docs/index.html", "docs/executive-summary.html", "docs/research.html",
    "docs/submission.html", "docs/data/public-feed.json",
    "evidence/run-card.json", "evidence/preflight.json", "evidence/priority-audit.json",
    "evidence/data-readiness.json", "evidence/format-27candidate.json",
    "evidence/concurrent-candidate-audit.json", "evidence/review-passes.md",
    "research/hypotheses.md",
)


def build(output: Path | None = None) -> Path:
    target = (output or (ROOT / "_site")).resolve()
    source_dirs = tuple((ROOT / name).resolve() for name in ("docs", "assets", "evidence", "research"))
    if target == ROOT or any(target == source or source in target.parents for source in source_dirs):
        raise ValueError("output must not overwrite the repository or source directories")
    if target.exists():
        if target != (ROOT / "_site").resolve() and any(target.iterdir()):
            raise ValueError("custom output directory must be empty")
        # _site is an ignored generated directory. Clear stale prior builds so
        # an old candidate TIFF cannot accidentally enter a deployment artifact.
        for child in target.iterdir():
            if child.is_dir() and not child.is_symlink():
                shutil.rmtree(child)
            else:
                child.unlink()
    for rel in SITE_FILES:
        source, destination = ROOT / rel, target / rel
        if not source.is_file():
            raise FileNotFoundError(f"missing site input: {rel}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    return target


if __name__ == "__main__":
    print("Assembled static site in", build())
