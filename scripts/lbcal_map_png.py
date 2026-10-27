#!/usr/bin/env python3
"""Quick-look PNG of the LBCAL research candidate (pure numpy + zlib).

Red = LBCAL dots, green = public catalogue, grey = hillshade of det_elev inside the
scored footprint. Output: docs/lbcal/assets/lbcal-map.png
"""
from __future__ import annotations

import json
import struct
import sys
import zlib
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from lbcal import data as D  # noqa: E402

STEP = 4


def write_png(path: Path, rgb: np.ndarray) -> None:
    H, W, _ = rgb.shape
    raw = b"".join(b"\x00" + rgb[y].tobytes() for y in range(H))

    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0))
                     + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def pool(mask: np.ndarray) -> np.ndarray:
    H, W = mask.shape
    H2, W2 = H // STEP, W // STEP
    return mask[:H2 * STEP, :W2 * STEP].reshape(H2, STEP, W2, STEP).max(axis=(1, 3))


def main() -> int:
    card = json.loads((ROOT / "evidence" / "lbcal_run_card.json").read_text())
    with rasterio.open(ROOT / card["file"]["path"]) as src:
        dots = src.read(1) > 0
    grid = D.load_grid()
    z = D.band("det_elev")
    z = ndi.gaussian_filter(np.nan_to_num(z, nan=float(np.nanmedian(z))), 2.0)
    gy, gx = np.gradient(z)
    shade = np.clip(128 + 40 * (-gx - gy), 0, 255)
    H2, W2 = D.SHAPE[0] // STEP, D.SHAPE[1] // STEP
    base = shade[:H2 * STEP, :W2 * STEP].reshape(H2, STEP, W2, STEP).mean(axis=(1, 3))
    foot = pool(grid.foot)
    img = np.zeros((H2, W2, 3), np.uint8)
    for k, f in enumerate((0.62, 0.66, 0.72)):
        img[..., k] = np.where(foot, np.clip(base * f, 0, 255), 12).astype(np.uint8)
    img[pool(grid.cat)] = (120, 200, 120)
    img[pool(dots)] = (255, 70, 60)
    out = ROOT / "docs" / "lbcal" / "assets" / "lbcal-map.png"
    write_png(out, img)
    print(f"wrote {out.relative_to(ROOT)} {out.stat().st_size} bytes ({H2}x{W2})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
