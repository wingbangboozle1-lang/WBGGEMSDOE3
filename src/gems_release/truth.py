"""Truth construction: spatial folds, hide-and-recover segments, off-catalogue proxies.

Three truth concepts are kept strictly separate, because conflating them is how
holdout numbers get inflated:

``catalogue``
    The 60,988 mapped fault cells of ``existing_faults.tif`` (byte-identical to
    ``labels.tif``; verified SHA-256 ``7ba308cc…``). These are the *training*
    labels and, at scoring time, the official *mask*.
``fold truth``
    Whole catalogue segments withheld in one spatial quadrant. Truth pixels that
    lie within ``BUFFER_PX`` of a visible catalogue pixel are dropped, so the
    model cannot score by predicting next to a visible fault.
``off-catalogue proxy``
    State Geologic Map Compilation faults (``sgmc_faults_100m.tif``) that lie
    more than ``SGMC_MIN_PX`` from every catalogue pixel. This is an independent
    mapping lineage, not hidden truth: it is used only as a second, harder
    generalisation axis.
"""
from __future__ import annotations

import csv
from pathlib import Path

import numpy as np
from scipy.ndimage import distance_transform_edt

from . import shared

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / "data" / "work"

BUFFER_PX = 5.0        # 500 m buffer around visible faults when selecting fold truth
SGMC_MIN_PX = 3.0      # off-catalogue proxy must be > 300 m from the catalogue
QUADRANTS = ("NW", "NE", "SW", "SE")


def _grid_shape() -> tuple[int, int]:
    footprint, _ = shared.load_masks()
    return footprint.shape


def quadrant_masks(shape: tuple[int, int] | None = None) -> dict:
    """Four hard spatial blocks: NW, NE, SW, SE quadrants of the AOI."""
    h, w = shape or _grid_shape()
    yy = np.arange(h)[:, None] < h // 2
    xx = np.arange(w)[None, :] < w // 2
    return {
        "NW": yy & xx,
        "NE": yy & ~xx,
        "SW": ~yy & xx,
        "SE": ~yy & ~xx,
    }


def load_segments() -> np.ndarray:
    """Parse ``trace_segments_utm11.csv`` into an (n, 5) float array (id, x0,y0,x1,y1)."""
    path = shared.data_path("external/trace_segments_utm11.csv")
    rows = []
    with open(path, newline="") as fh:
        for rec in csv.DictReader(fh):
            try:
                rows.append((int(float(rec["record_id"])),
                             float(rec["x0"]), float(rec["y0"]),
                             float(rec["x1"]), float(rec["y1"])))
            except (KeyError, TypeError, ValueError):
                continue
    return np.asarray(rows, dtype=np.float64)


def segment_cell_index(cache: bool = True) -> dict:
    """Bresenham-rasterise every trace segment; return ``{record_id: (rows, cols)}``.

    Rasterisation is cell-centre based on the pinned grid transform
    (origin 243350 / 4508550, 100 m): ``col = floor((x - 243350)/100)``,
    ``row = floor((4508550 - y)/100)``. That is the same convention rasterio uses
    for the official rasters, so the segment index and the catalogue raster are
    directly comparable (checked by :func:`verify_segment_index`).
    """
    out_path = WORK / "segment_cells.npz"
    if cache and out_path.is_file():
        with np.load(out_path) as z:
            ids = z["ids"]
            return {int(i): (z["rows"][z["starts"][k]:z["starts"][k + 1]],
                             z["cols"][z["starts"][k]:z["starts"][k + 1]])
                    for k, i in enumerate(ids)}

    h, w = _grid_shape()
    ox, oy, res = 243350.0, 4508550.0, 100.0
    segs = load_segments()
    ids = np.unique(segs[:, 0].astype(np.int64))
    rows_l, cols_l, starts, kept = [], [], [0], []
    for rid in ids:
        rows, cols = [], []
        for x0, y0, x1, y1 in segs[segs[:, 0] == rid][:, 1:]:
            n = int(max(abs(x1 - x0), abs(y1 - y0)) // res) + 2
            xs = np.linspace(x0, x1, n)
            ys = np.linspace(y0, y1, n)
            c = np.floor((xs - ox) / res).astype(np.int64)
            r = np.floor((oy - ys) / res).astype(np.int64)
            ok = (r >= 0) & (r < h) & (c >= 0) & (c < w)
            rows.append(r[ok])
            cols.append(c[ok])
        if not rows:
            continue
        r = np.unique(np.concatenate(rows))
        c = np.unique(np.concatenate(cols))
        # keep the unique cells of the union of the segment's line pieces
        cells = np.unique(np.stack(np.concatenate(rows), np.concatenate(cols))) if False else None
        rr = np.concatenate(rows)
        cc = np.concatenate(cols)
        flat = np.unique(rr.astype(np.int64) * w + cc.astype(np.int64))
        rows_l.append(flat // w)
        cols_l.append(flat % w)
        starts.append(starts[-1] + flat.size)
        kept.append(int(rid))
    result = dict(ids=np.asarray(kept, np.int64),
                  rows=np.concatenate(rows_l), cols=np.concatenate(cols_l),
                  starts=np.asarray(starts, np.int64))
    if cache:
        WORK.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(out_path, **result)
    return {int(i): (result["rows"][result["starts"][k]:result["starts"][k + 1]],
                     result["cols"][result["starts"][k]:result["starts"][k + 1]])
            for k, i in enumerate(result["ids"])}


def verify_segment_index(tol: float = 0.9) -> dict:
    """How much of the catalogue raster the segment index reproduces.

    A high overlap is the check that the CSV and the official raster describe the
    same faults in the same grid; it is *not* assumed.
    """
    footprint, catalogue = shared.load_masks()
    idx = segment_cell_index()
    drawn = np.zeros(footprint.shape, bool)
    for rows, cols in idx.values():
        drawn[rows, cols] = True
    cat = catalogue
    inter = int((drawn & cat).sum())
    return dict(
        segments=len(idx), drawn_cells=int(drawn.sum()), catalogue_cells=int(cat.sum()),
        drawn_inside_catalogue_fraction=float(inter / max(1, int(drawn.sum()))),
        catalogue_covered_fraction=float(inter / max(1, int(cat.sum()))),
        buffer_px=BUFFER_PX, note="cell-centre rasterisation of the INGENIOUS/QFault trace export",
    )


def fold_truth(quadrant: str, catalogue: np.ndarray | None = None,
               buffer_px: float = BUFFER_PX) -> dict:
    """Withhold one quadrant's catalogue segments; buffer the recovery target."""
    footprint, cat = shared.load_masks() if catalogue is None else (None, catalogue)
    if footprint is None:
        footprint, _ = shared.load_masks()
    quad = quadrant_masks(footprint.shape)[quadrant]
    withheld = cat & quad
    visible = cat & ~quad
    d_vis = distance_transform_edt(~visible)
    truth = withheld & (d_vis >= buffer_px)
    active = footprint & ~visible          # official masking of known faults
    truth = truth & active
    return dict(quadrant=quadrant, truth=truth, visible=visible, active=active,
                footprint=footprint, region=quad,
                n_truth=int(truth.sum()), n_withheld_raw=int(withheld.sum()),
                n_dropped_by_buffer=int(withheld.sum() - truth.sum()))


def sgmc_offcatalogue(catalogue: np.ndarray | None = None,
                      min_px: float = SGMC_MIN_PX) -> dict:
    """SGMC faults that are absent from the competition catalogue."""
    import rasterio

    if catalogue is None:
        _fp, catalogue = shared.load_masks()
    with rasterio.open(shared.data_path("external/sgmc_faults_100m.tif")) as src:
        sgmc = src.read(1) == 1
    with rasterio.open(shared.data_path("external/derived_sgmc_faults_100m.tif")) as src:
        derived = src.read(1) == 1
    d_cat = distance_transform_edt(~catalogue)
    off = sgmc & (d_cat >= min_px)
    return dict(mask=off, sgmc=sgmc, derived=derived, distance_to_catalogue=d_cat,
                n_sgmc=int(sgmc.sum()), n_sgmc_on_catalogue=int((sgmc & catalogue).sum()),
                n_sgmc_off=int(off.sum()),
                derived_cells=int(derived.sum()),
                derived_on_catalogue=int((derived & catalogue).sum()),
                derived_minus_sgmc=int((derived & ~sgmc).sum()))


def background_mask(catalogue: np.ndarray, footprint: np.ndarray,
                    min_px: float = 10.0) -> np.ndarray:
    """Cells far from every known fault: used as supervised negatives."""
    d = distance_transform_edt(~catalogue)
    return footprint & (d >= min_px)
