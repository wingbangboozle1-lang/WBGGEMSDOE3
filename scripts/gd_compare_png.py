#!/usr/bin/env python3
"""Render the champion-vs-ours comparison figure.

Left half is not a separate panel: one map, three colours, so overlap is visible
without any interpretation.
  orange = GEMSDOE32's 0.2778 file (37,654 dots)
  red    = this repo's submission (97,608 dots)
  white  = dots present in both (the honest measure of "same idea")
  green  = public catalogue
Output: docs/assets/compare-champion.png
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.gd_map_png import STEP, pool, write_png   # noqa: E402
from src.gemsdoe import config as C                   # noqa: E402
from src.gemsdoe import io as gio                     # noqa: E402


def main() -> int:
    champ_path = sorted((ROOT / ".cache" / "focus").glob("GEMSDOE32__*.tif"))[0]
    ours_path = sorted((ROOT / "submission").glob("*skarpline*.tif"))[-1]
    with rasterio.open(champ_path) as src:
        champ = np.nan_to_num(src.read(1)) > 0
    with rasterio.open(ours_path) as src:
        ours = np.nan_to_num(src.read(1)) > 0
    cat = gio.read_labels()

    de = gio.read_band(C.FEATURES_TIF, 12)
    de = np.where(np.isfinite(de), de, np.nan)
    from scipy import ndimage as ndi
    z = ndi.gaussian_filter(np.nan_to_num(de, nan=np.nanmedian(de)), 2.0)
    gy, gx = np.gradient(z)
    shade = np.clip(122 + 38 * (-gx - gy), 0, 255)

    H2, W2 = C.HEIGHT // STEP, C.WIDTH // STEP
    img = np.zeros((H2, W2, 3), dtype=np.uint8)
    base = shade[:H2 * STEP, :W2 * STEP].reshape(H2, STEP, W2, STEP).mean(axis=(1, 3))
    for i, k in enumerate((0.62, 0.66, 0.72)):
        img[..., i] = np.clip(base * k, 0, 255).astype(np.uint8)

    img[pool(cat)] = (96, 160, 96)
    img[pool(champ)] = (255, 138, 40)
    img[pool(ours)] = (222, 48, 44)
    img[pool(ours & champ)] = (255, 255, 255)

    out = ROOT / "docs" / "assets" / "compare-champion.png"
    write_png(out, img)
    inter = int((ours & champ).sum())
    print(f"wrote {out} {out.stat().st_size} bytes ({H2}x{W2}); "
          f"champ={int(champ.sum())} ours={int(ours.sum())} shared={inter} "
          f"jaccard={inter / int((ours | champ).sum()):.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
