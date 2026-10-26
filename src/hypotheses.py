"""
Candidate geological hypotheses for GEMS geothermal discovery.

Each hypothesis names: the layer(s) involved, the physical signature targeted,
why it should catch a fault missing from the USGS / INGENIOUS catalogue, and how
it differs from anything already implemented. They are ranked by expected DTI
improvement versus implementation cost.

These are untested on the real competition grid because the labelled training
data (labels.tif / training_features.tif) requires DrivenData login, which is
not available in this environment. Each must be validated on the spatially
blocked holdout before a weekly submission slot is spent.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Hypothesis:
    id: str
    name: str
    layers: str
    signature: str
    why_misses_catalogue: str
    difference_from_repo: str
    expected_dti_improvement: str
    implementation_cost: str
    external_data_needed: str
    obtainable: str
    status: str


HYPOTHESES = [
    {
        "id": "H-NEW-01",
        "name": "Blind stepover / relay-ramp pull-apart density",
        "layers": "Upper crust (1-5 km): Quaternary alluvium over Tertiary volcanic & sedimentary basin-fill; basement faults.",
        "signature": "High density of short, sub-seismic fault segments and stepover bends (30-200 m scale) extracted from DEM curvature + shaded relief; concentrated where catalogue faults offset or terminate.",
        "why_misses_catalogue": "USGS/INGENIOUS catalogue maps mapped, through-going scarps. Blind stepovers and relay ramps below mapping resolution host permeability but are absent from the catalogue; their surface expression is subtle curvature/texture, not a continuous lineament.",
        "difference_from_repo": "Repo features focus on distance-to-catalogue-fault and coarse lineament density. This targets sub-catalogue stepover clusters via high-resolution curvature texture, a transform not yet implemented.",
        "expected_dti_improvement": "Moderate (+0.03 to +0.08 DTI) if blind structures drive undiscovered geothermal cells.",
        "implementation_cost": "Low (curvature + local density, raster-only).",
        "external_data_needed": "30 m DEM (USGS 3DEP / SRTM) — already referenced in repo (epsg.io/32611, DEM links).",
        "obtainable": "Yes — USGS 3DEP is free and official.",
        "status": "proposed",
    },
    {
        "id": "H-NEW-02",
        "name": "Radiometric potassium-thorium (K/Th) hydrothermal alteration halo",
        "layers": "Near-surface (<1 m effective sensing): airborne radiometric survey (GEODAWN K, Th, eU).",
        "signature": "Elevated K and Th with suppressed eU (low K/Th or K/(Th+U) anomaly) over clay-rich hydrothermal alteration; expressed as a radiometric ratio raster rather than absolute count.",
        "why_misses_catalogue": "Catalogue faults are structural; alteration halos can extend beyond mapped faults and mark blind, buried geothermal systems with little surface faulting. Radiometry sees chemistry the structural catalogue misses.",
        "difference_from_repo": "Existing submissions use topography, lidar scarps, and structural faults. No submission in GEMSDOE 24-36 uses the GEODAWN airborne radiometric K/Th ratio as a primary feature.",
        "expected_dti_improvement": "Moderate-to-high (+0.05 to +0.12 DTI) where alteration is the dominant blind indicator.",
        "implementation_cost": "Low-medium (ratio raster + smoothing; needs the geodawn features raster).",
        "external_data_needed": "GEODAWN airborne magnetic & radiometric survey (USGS GDR submission 1391 / gems-geodawn-numerical-features.tif).",
        "obtainable": "Partly — data pack file is reference-only; needs DrivenData login to download. Confirm obtainable before promoting.",
        "status": "blocked-pending-data",
    },
    {
        "id": "H-NEW-03",
        "name": "Magnetic lineament gradient + Curie-point depth proxy",
        "layers": "Mid-to-upper crust: magnetic basement and its shallow termination.",
        "signature": "High horizontal-gradient magnitude of aeromagnetic data (magnetic lineament edges) combined with a shallow Curie-point-depth proxy (broad, low-amplitude magnetic field = deep thermal source).",
        "why_misses_catalogue": "Magnetic gradients trace fault-bound lithologic contacts and buried faults with no surface expression. A shallow Curie point indicates elevated heat flow. Neither is in the structural fault catalogue.",
        "difference_from_repo": "Repo uses topography and structure. Magnetic gradient magnitude as the dominant feature is not among GEMSDOE 24-36 submissions, which lean on dotted-ridge / DTI / topo.",
        "expected_dti_improvement": "Moderate (+0.04 to +0.10 DTI) in basins with magnetic basement.",
        "implementation_cost": "Low-medium (derivative of aeromagnetic raster; needs geodawn magnetic raster).",
        "external_data_needed": "GEODAWN airborne magnetic survey (same USGS GDR source as H-NEW-02).",
        "obtainable": "Partly — same data-access block as H-NEW-02.",
        "status": "blocked-pending-data",
    },
    {
        "id": "H-NEW-04",
        "name": "Thermal-inertia / nighttime LST anomaly over piedmont",
        "layers": "Land surface: satellite-derived land-surface temperature and thermal inertia.",
        "signature": "Nighttime LST warm anomaly + low thermal inertia (rapid cooling) over piedmont/alluvial fans, indicating shallow groundwater upflow and convective heat transport.",
        "why_misses_catalogue": "Thermal anomalies can be blind to structure; a warm, low-inertia piedmont patch may mark concealed upflow with no mapped fault at the surface.",
        "difference_from_repo": "No GEMSDOE submission uses satellite thermal inertia or nighttime LST as a primary feature; existing thermal references are generic.",
        "expected_dti_improvement": "Low-to-moderate (+0.02 to +0.06 DTI), highly sensitive to atmospheric correction and seasonality.",
        "implementation_cost": "Low-medium (needs Landsat/Sentinel-3 LST + DEM-derived inertia proxy).",
        "external_data_needed": "Landsat 8/9 TIRS or Sentinel-3 SLSTR LST (USGS EarthExplorer / ESA, free).",
        "obtainable": "Yes — free official satellite data.",
        "status": "proposed",
    },
    {
        "id": "H-NEW-05",
        "name": "Dilation / stepover stress proxy from catalogue fault geometry",
        "layers": "Fault catalogue geometry (USGS/INGENIOUS mapped faults).",
        "signature": "Dilational quadrants and stepover zones computed from fault strike/rake/dip and regional stress orientation; high where faults step over or terminate in extension.",
        "why_misses_catalogue": "Uses the same catalogue but derives a new process (dilation) not directly mapped; catches the specific segments that are permeability conduits even though the fault itself is catalogued.",
        "difference_from_repo": "Existing submissions use distance-to-fault and density; none computes a dilation/stress quadrature field from fault geometry. Complements, rather than duplicates, catalogue-distance features.",
        "expected_dti_improvement": "Low (+0.01 to +0.04 DTI) because it reuses catalogue faults (may miss truly blind systems).",
        "implementation_cost": "Low (raster catalogue + orientation field).",
        "external_data_needed": "None — uses existing_faults.tif from the data pack.",
        "obtainable": "Yes (requires DrivenData login for the data pack).",
        "status": "proposed",
    },
]

RANK_ORDER = {"high": 3, "moderate-to-high": 2.5, "moderate": 2,
              "low-to-moderate": 1.5, "low": 1}
COST_ORDER = {"low": 2, "low-medium": 1.5, "medium": 1, "moderate": 0.5}


def rank_key(h):
    imp = h["expected_dti_improvement"].split(" ")[0].strip("+").rstrip("DTI").strip()
    cost = h["implementation_cost"].split(" ")[0]
    return (RANK_ORDER.get(imp, 1), COST_ORDER.get(cost, 1))


RANKED = sorted(HYPOTHESES, key=rank_key, reverse=True)


def list_hypotheses():
    for h in RANKED:
        print(f"{h['id']} | {h['name']} | {h['expected_dti_improvement']} | "
              f"cost={h['implementation_cost']} | {h['status']}")


if __name__ == "__main__":
    list_hypotheses()
