#!/usr/bin/env python3
"""Build the preregistered SGCE static field stack (ignored data/work cache)."""
from __future__ import annotations
import sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gemsw import sgce, grid as G  # noqa: E402

if __name__ == "__main__":
    t = time.time()
    g = G.load_grid()
    p = sgce.build_bins(g)
    print(f"done in {time.time()-t:.0f}s -> {p}", flush=True)
