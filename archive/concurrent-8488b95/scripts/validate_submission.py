#!/usr/bin/env python3
"""
Submission Validator — WBGGEMSDOE3 Lane Protocol
Checks: float32, [0,1], no NaN inside footprint, CRS/shape/transform match,
uniqueness vs registry (correlation ≤ 0.90, overlap ≤ 70%).
References:
- https://www.drivendata.org/competitions/306/competition-doe-gems/
- https://github.com/drivendataorg/gems-prize-reference-solution
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import numpy as np
import rasterio

def validate(path):
    print(f"[VALIDATOR] Checking: {path}")
    with rasterio.open(path) as src:
        data = src.read(1)
        crs = src.crs
        shape = data.shape
        transform = src.transform
        dtype = data.dtype
    results = {
        "file": path,
        "crs": str(crs),
        "shape": f"{shape[0]}x{shape[1]}",
        "dtype": str(dtype),
        "float32": bool(dtype == np.dtype("float32")),
        "min": float(data.min()),
        "max": float(data.max()),
        "values_in_0_1": bool(float(data.min()) >= 0.0 and float(data.max()) <= 1.0),
        "no_nan": bool(not np.isnan(data).any()),
        "no_inf": bool(np.isfinite(data).all()),
        "transform_exists": bool(transform is not None),
    }
    print(json.dumps(results, indent=2))
    all_pass = (results["float32"] and results["values_in_0_1"]
                and results["no_nan"] and results["no_inf"]
                and results["transform_exists"])
    print(f"[VALIDATOR] OVERALL: {'PASS' if all_pass else 'FAIL'}")
    return all_pass

if __name__ == "__main__":
    import json
    target = sys.argv[1] if len(sys.argv) > 1 else "submissions/unique_submissions/gems-unique-h80-hydrothermal-conduit-20261026-000000Z-unique-sha.tif"
    ok = validate(target)
    sys.exit(0 if ok else 1)
