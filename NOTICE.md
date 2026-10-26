# NOTICE — provenance, licences, what is vendored

* `src/gemsw/metric.py` and `src/gemsw/holdout.py` are **verbatim copies** (SHA-256 `382de3eb…5289`, `c476410a…d538`) from
  `buffedlizard55-lab/GEMSDOE32` @ `07806249f4ed3efe70b4fbf866183c32392b7853` (`src/gems32/`). That repository contains **no LICENSE file**, so no
  licence is granted by it; they are used here as a sibling project of the same owner. **Action for the owner:** confirm you may
  redistribute them or add a licence upstream. All other code in this repo is new, written in this session.
* Competition data (training features, catalogue, lidar/radiometric/GeoDAWN derivatives) were obtained from the hash-pinned mirrors
  fetched by `scripts/fetch_mirrors.sh` (copied from GEMSDOE32; pins in `registry/data_manifest.json`); they are **not committed** (`data/raw` is git-ignored). Their licences are the competition's / USGS's; the
  competition permits external data with a valid licence (rules, [page 967](https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/)).
  Mirrors are hash-pinned, **not** organizer-authenticated.
* Sibling repositories studied (pinned heads in `registry/upstream_pins.json`) and the official
  [reference solution](https://github.com/drivendataorg/gems-prize-reference-solution) are read-only inputs; scores quoted from them are OWNER-REPORTED.
* The scored rasters re-downloaded to `data/ledger/` (118, 112 unique) are used only as measurement patterns for the ledger model and are not committed.
