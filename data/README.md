# Local data directory

Competition rasters and generated feature caches are intentionally ignored by Git. Obtain the official data through the authenticated DrivenData competition page, then place only the required local inputs here or point the shared template to their existing paths. Never put credentials or private data in this repository.

Required for the shared pipeline (filenames may be set by that template):

- `training_features.tif`
- `labels.tif`
- `existing_faults.tif`
- `sample_submission.tif`
- the template's prepared/cache feature stack

This checkout currently contains none of those inputs or the complete canonical registry. The validator can be exercised with synthetic files in tests, but synthetic fixtures are not competition data and cannot produce a scientific holdout result or a submission candidate. See `data/registry/README.md` for the required registry manifest contract. Restore/hash-check genuine inputs and the registry before running `evaluate_holdout.py`, `submission_writer.py`, or uniqueness checks in the shared template.
