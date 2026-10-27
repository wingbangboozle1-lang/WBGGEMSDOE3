#!/usr/bin/env python3
"""Render a down-sampled quick-look PNG of the submission against the two catalogues.

Pure numpy + zlib (no matplotlib/PIL in the sandbox). Output: docs/assets/submission-map.png
"""
from __future__ import annotations

import struct
import sys
import zlib
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.gemsdoe import config as C   # noqa: E402
from src.gemsdoe import io as gio     # noqa: E402
from src.gemsdoe import validation as V  # noqa: E402

STEP = 4


def write_png(path: Path, rgb: np.ndarray) -> None:
    H, W, _ = rgb.shape
    raw = b"".join(b"\x00" + rgb[y].tobytes() for y in range(H))

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(raw, 9))
           + chunk(b"IEND", b""))
    path.write_bytes(png)


def pool(mask: np.ndarray) -> np.ndarray:
    H, W = mask.shape
    H2, W2 = H // STEP, W // STEP
    return mask[:H2 * STEP, :W2 * STEP].reshape(H2, STEP, W2, STEP).max(axis=(1, 3))


def main() -> int:
    sub = sorted((ROOT / "submission").glob("*skarpline*.tif"))
    if not sub:
        print("no submission tif found")
        return 1
    with __import__("rasterio").open(sub[-1]) as src:
        ours = src.read(1) > 0
    cat = gio.read_labels()
    gt = V.sgmc_only_gt(gio.read_footprint())
    de = gio.read_band(C.FEATURES_TIF, 12)
    de = np.where(np.isfinite(de), de, np.nan)
    # hillshade from a smoothed detrended elevation
    from scipy import ndimage as ndi
    z = ndi.gaussian_filter(np.nan_to_num(de, nan=np.nanmedian(de)), 2.0)
    gy, gx = np.gradient(z)
    shade = np.clip(128 + 40 * (-gx - gy), 0, 255)

    H2, W2 = C.HEIGHT // STEP, C.WIDTH // STEP
    img = np.zeros((H2, W2, 3), dtype=np.uint8)
    base = shade[:H2 * STEP, :W2 * STEP].reshape(H2, STEP, W2, STEP).mean(axis=(1, 3))
    img[..., 0] = np.clip(base * 0.62, 0, 255).astype(np.uint8)
    img[..., 1] = np.clip(base * 0.66, 0, 255).astype(np.uint8)
    img[..., 2] = np.clip(base * 0.72, 0, 255).astype(np.uint8)
    img[pool(gt)] = (40, 170, 255)      # external catalogue proxy (SGMC-only)
    img[pool(cat)] = (120, 200, 120)    # public catalogue
    img[pool(ours)] = (255, 70, 60)     # our submission
    out = ROOT / "docs" / "assets" / "submission-map.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    write_png(out, img)
    print(f"wrote {out} {out.stat().st_size} bytes  ({H2}x{W2})  "
          f"ours={int(pool(ours).sum())} cat={int(pool(cat).sum())} proxy={int(pool(gt).sum())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
