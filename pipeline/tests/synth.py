"""Build a small synthetic scene on disk: radar GeoTIFFs, a DEM and a matching config. No real data."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import rasterio
from affine import Affine
from pyproj import Transformer
from rasterio.crs import CRS
from rasterio.transform import from_origin

UTM = CRS.from_epsg(32617)
LON0, LAT0 = -80.90, 7.52            # north-west corner of the scene
N = 400                               # 400 x 400 pixels of 10 m = 4 km
SLOPE_GRADIENT = 0.27                 # about 15 degrees, rising to the south (slope faces north: visible to the radar)

PATCH_A = (slice(100, 116), slice(100, 116))     # real landslide: dark in both pairs
PATCH_B = (slice(250, 266), slice(250, 266))     # only the first pair sees it: must be dropped
QUAKE = "2026-10-09T17:56:00Z"


def _write(path: Path, data: np.ndarray, transform: Affine, crs: CRS) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(path, "w", driver="GTiff", height=data.shape[0], width=data.shape[1], count=1,
                       dtype="float32", crs=crs, transform=transform, nodata=0.0) as dst:
        dst.write(data.astype("float32"), 1)


def _power(rng, db_map: np.ndarray) -> np.ndarray:
    return 10 ** ((db_map + rng.normal(0, 0.6, db_map.shape)) / 10.0)


def build(root: Path) -> dict:
    """Write rasters under root/data/raw and return a config that points at them (paths relative to root)."""
    rng = np.random.default_rng(7)
    x0, y0 = Transformer.from_crs(4326, UTM, always_xy=True).transform(LON0, LAT0)
    transform = Affine(10, 0, x0, 0, -10, y0)
    raw = root / "data" / "raw"

    flat = np.full((N, N), -12.0)

    def with_drop(*patches, drop=-6.0):
        m = flat.copy()
        for p in patches:
            m[p] = flat[p] + drop
        return m

    files = {
        "t141_before": flat, "t141_after": with_drop(PATCH_A, PATCH_B),
        "t4_before": flat, "t4_after": with_drop(PATCH_A),
        "t40_before_0920": flat, "t40_after_1002": flat,
    }
    for name, db_map in files.items():
        _write(raw / f"{name}.tif", _power(rng, db_map), transform, UTM)

    # DEM in lon/lat, 1 arc-second, covering the scene with a margin; elevation rises towards the south
    px = 1 / 3600
    width = int(0.06 / px)
    lat_top = LAT0 + 0.01
    rows = np.arange(width)[:, None]
    lat = lat_top - rows * px
    z = (LAT0 - lat) * 110_574.0 * SLOPE_GRADIENT + 500.0
    dem = np.repeat(z, width, axis=1)
    _write(raw / "dem.tif", dem, from_origin(LON0 - 0.01, lat_top, px, px), CRS.from_epsg(4326))

    west, south = LON0 - 0.001, LAT0 - 0.04
    bbox = [west, south, LON0 + 0.04, LAT0 + 0.001]
    return {
        "event_id": "synthetic", "name": "Synthetic scene", "time_utc": QUAKE, "epicentre": [LON0, LAT0],
        "bbox": bbox, "maturity": "PROVISIONAL", "references": [], "target_res_m": 20, "filter_size": 5,
        "incidence_deg": 37, "detect": {"threshold_db": -3.0, "min_slope_deg": 10, "min_forest_hv_db": -16, "min_pixels": 3},
        "dem": "data/raw/dem.tif", "primary_pair": "t141d",
        "pairs": [
            {"id": "t141d", "track": 141, "direction": "descending", "before": "2026-09-27T23:53:35Z",
             "after": "2026-10-09T23:53:35Z", "before_hv": "data/raw/t141_before.tif", "after_hv": "data/raw/t141_after.tif", "granules": []},
            {"id": "t4a", "track": 4, "direction": "ascending", "before": "2026-09-30T11:04:20Z",
             "after": "2026-10-12T11:04:20Z", "before_hv": "data/raw/t4_before.tif", "after_hv": "data/raw/t4_after.tif", "granules": []},
        ],
        "baseline": {"track": 40, "direction": "descending", "before": "2026-09-20T23:45:16Z", "after": "2026-10-02T23:45:16Z",
                     "before_hv": "data/raw/t40_before_0920.tif", "after_hv": "data/raw/t40_after_1002.tif"},
        "series": [], "timeline": [], "work": "work", "out": "out",
    }


def write_config(root: Path, cfg: dict) -> Path:
    p = root / "pipeline" / "config.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(cfg), encoding="utf-8")
    return p
