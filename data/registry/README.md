# Registry inputs for literal uniqueness checks

The complete, refreshed registry rasters and manifest are **not present** in this checkout. The nine historical focus-site TIFFs in `docs/data/focus-site-audit.json` are only a subset; they are not a full-registry uniqueness clearance.

Before checking a future candidate:

1. Obtain the canonical shared-template registry export and its source/version from the shared project. Include every registered continuous pre-placement surface and final dot raster. The manifest must include all nine focus-site winners and the literal lattice raster; no lattice exception is permitted.
2. Preserve every registry raster byte-for-byte and record its SHA-256. Do not edit, resample, reproject, or drop inconvenient comparisons.
3. Create a local `manifest.json` following this schema:

```json
{
  "schema_version": 1,
  "registry_version": "canonical-version-or-commit",
  "source": "canonical shared-template registry location",
  "complete": true,
  "includes_literal_lattice": true,
  "includes_all_focus_site_winners": true,
  "entries": [
    {
      "id": "GEMSDOE24-surface-and-dots",
      "surface_file": "rasters/GEMSDOE24-surface.tif",
      "surface_sha256": "64-character SHA-256",
      "dots_file": "rasters/GEMSDOE24-dots.tif",
      "dots_sha256": "64-character SHA-256"
    }
  ]
}
```

The manifest must contain a distinct ID for every registry item; IDs for the nine focus-site files must include the respective `GEMSDOE24`, `GEMSDOE25`, `GEMSDOE27`, `GEMSDOE28`, `GEMSDOE30`, `GEMSDOE31`, `GEMSDOE32`, `GEMSDOE33`, and `GEMSDOE36` strings. At least one entry ID must include `lattice`. The booleans are assertions, not proof: keep the canonical source/version and completeness evidence alongside the manifest.

Run after the saved-byte preflight, using the official template footprint:

```bash
python scripts/validate_registry_uniqueness.py \
  --surface /path/to/candidate-surface.tif \
  --candidate /path/to/candidate-dots.tif \
  --template /path/to/sample_submission.tif \
  --registry-manifest /path/to/manifest.json \
  --out /path/to/registry-uniqueness.json
```

The script fails closed unless both the surface and dot comparisons pass against every manifest entry and the manifest asserts the required coverage. A passing report still does not independently prove manifest completeness or authorize a submission slot. All local registry rasters and manifests must remain out of Git; the repository ignore rules already exclude `data/registry/**` except this README.
