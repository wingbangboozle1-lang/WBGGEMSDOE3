#!/usr/bin/env python3
"""Render quick-look PNGs of the *current* (20k-dot inverse-design) submission.

The older ``docs/assets/submission-map.png`` / ``compare-champion.png`` were drawn for the
retired THCS-OOF lane and therefore show a file that must not be submitted; leaving them as
the only figures was a real source of confusion.  This script writes two replacements that
are bound to the published deliverable's bytes:

    docs/assets/design-map.png      <- 20,000 design dots vs the public catalogue and the
                                       extended (SGMC) proxy catalogue, on a flat base
    docs/assets/design-compare.png  <- design dots vs the GEMSDOE32 0.2778 champion dots,
                                       white where the two are within the 3-px kernel

Pure numpy + zlib (no matplotlib/PIL).  Everything it draws is re-read from disk; nothing is
hand-drawn, so the figures cannot drift from the file they claim to describe.
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

DELIVERABLE = ROOT / "docs" / "downloads" / "wbggems3-invdesign-anchor-20k-zeros.tif"
CATALOGUE = ROOT / "data" / "bridge" / "existing_faults.tif"
EXTENDED = ROOT / "data" / "external" / "derived_sgmc_faults_100m_u8.tif"
CHAMPION = ROOT / "data" / "work" / "champion_ref.tif"

STEP = 4          # pool 4x4 -> 932 x 823
RADIUS_PX = 3     # 300 m kernel


def write_png(path: Path, rgb: np.ndarray) -> None:
    h, w, _ = rgb.shape
    raw = b"".join(b"\x00" + rgb[y].tobytes() for y in range(h))

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(raw, 9))
           + chunk(b"IEND", b""))
    path.write_bytes(png)


def pool(mask: np.ndarray, step: int = STEP) -> np.ndarray:
    h, w = mask.shape
    h2, w2 = h // step, w // step
    return mask[:h2 * step, :w2 * step].reshape(h2, step, w2, step).max(axis=(1, 3))


def read_mask(path: Path) -> np.ndarray:
    with rasterio.open(path) as src:
        return src.read(1) > 0


def canvas(shape: tuple[int, int], rgb: tuple[int, int, int]) -> np.ndarray:
    img = np.zeros((shape[0], shape[1], 3), np.uint8)
    img[...] = rgb
    return img


def paint(img: np.ndarray, mask: np.ndarray, rgb: tuple[int, int, int]) -> None:
    img[pool(mask)] = rgb


def main() -> int:
    design = read_mask(DELIVERABLE)
    catalogue = read_mask(CATALOGUE)
    extended = read_mask(EXTENDED)
    champion = read_mask(CHAMPION)
    out_dir = ROOT / "docs" / "assets"
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. Where the dots are, and what they are (not) sitting on.
    h2, w2 = design.shape[0] // STEP, design.shape[1] // STEP
    img = canvas((h2, w2), (26, 30, 36))
    paint(img, extended, (38, 122, 168))     # extended SGMC proxy catalogue - blue
    paint(img, catalogue, (74, 168, 96))     # public catalogue - green
    paint(img, design, (238, 74, 60))        # the 20,000 submitted dots - red
    p1 = out_dir / "design-map.png"
    write_png(p1, img)

    # 2. Design vs the 0.2778 champion, with the shared 3-px corridors in white.
    near_champion = ndi.binary_dilation(champion, ndi.generate_binary_structure(2, 2),
                                        iterations=RADIUS_PX)
    shared = design & near_champion
    img2 = canvas((h2, w2), (24, 26, 30))
    paint(img2, champion, (214, 158, 44))    # champion dots - amber
    paint(img2, shared, (245, 245, 245))     # within 3 px of a champion dot - white
    paint(img2, design & ~near_champion, (238, 74, 60))   # design-only dots - red
    p2 = out_dir / "design-compare.png"
    write_png(p2, img2)

    n_design = int(design.sum())
    stats = {
        "schema": "gems-design-figures-v1",
        "generated_utc": __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
                          .strftime("%Y-%m-%dT%H:%M:%SZ"),
        "deliverable": str(DELIVERABLE.relative_to(ROOT)),
        "design_dots": n_design,
        "champion_file": str(CHAMPION.relative_to(ROOT)),
        "champion_dots": int(champion.sum()),
        "catalogue_file": str(CATALOGUE.relative_to(ROOT)),
        "extended_catalogue_file": str(EXTENDED.relative_to(ROOT)),
        "kernel_radius_px": RADIUS_PX,
        "pool_step": STEP,
        "figures": ["docs/assets/design-map.png", "docs/assets/design-compare.png"],
    }
    frac_near = float((design & near_champion).sum()) / max(n_design, 1)
    stats["frac_design_within_3px_of_champion"] = frac_near
    stats["frac_design_on_public_catalogue"] = float((design & catalogue).sum()) / max(n_design, 1)
    stats["frac_design_on_extended_catalogue"] = float((design & extended).sum()) / max(n_design, 1)
    js = ROOT / "evidence" / "design_figures.json"
    js.write_text(json.dumps(stats, indent=2) + "\n")
    print(f"design dots                 {n_design}")
    print(f"within 3 px of champion     {frac_near:.4f}  (gate: <= 0.70 directed)")
    print(f"on public catalogue         {float((design & catalogue).sum()) / max(n_design, 1):.4f}")
    print(f"on extended proxy catalogue {float((design & extended).sum()) / max(n_design, 1):.4f}")
    print(f"wrote {p1.relative_to(ROOT)} ({p1.stat().st_size} bytes, {w2}x{h2})")
    print(f"wrote {p2.relative_to(ROOT)} ({p2.stat().st_size} bytes, {w2}x{h2})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
