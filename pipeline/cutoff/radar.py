"""Read radar rasters, convert power to dB, filter speckle, align grids.

A Raster is a 2-D float32 array plus its affine transform and coordinate system. Missing data is NaN.
Radar images are handled as linear power; they are averaged onto the common grid as power and only
then converted to dB.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import rasterio
from affine import Affine
from rasterio.crs import CRS
from rasterio.enums import Resampling
from rasterio.warp import reproject
from scipy.ndimage import median_filter, uniform_filter


@dataclass
class Raster:
    data: np.ndarray
    transform: Affine
    crs: CRS

    @property
    def shape(self) -> tuple[int, int]:
        return self.data.shape

    @property
    def pixel_size(self) -> tuple[float, float]:
        """(x size, y size) in CRS units, both positive."""
        return abs(self.transform.a), abs(self.transform.e)


def read_raster(path: str | Path, band: int = 1) -> Raster:
    """Read one band as float32; nodata becomes NaN."""
    with rasterio.open(path) as src:
        data = src.read(band, masked=True).astype("float32").filled(np.nan)
        return Raster(data, src.transform, src.crs)


def write_raster(path: str | Path, raster: Raster) -> None:
    """Write a single-band float32 GeoTIFF with NaN as nodata."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    h, w = raster.data.shape
    with rasterio.open(path, "w", driver="GTiff", height=h, width=w, count=1, dtype="float32",
                       crs=raster.crs, transform=raster.transform, nodata=np.nan, compress="deflate") as dst:
        dst.write(raster.data.astype("float32"), 1)


def power_to_db(power: np.ndarray) -> np.ndarray:
    """10 * log10(power) where power > 0, else NaN."""
    p = np.asarray(power, dtype="float64")
    out = np.full(p.shape, np.nan, dtype="float32")
    ok = np.isfinite(p) & (p > 0)
    out[ok] = 10.0 * np.log10(p[ok])
    return out


def median_speckle(db: np.ndarray, size: int = 5) -> np.ndarray:
    """size x size median filter on a dB image. NaN pixels stay NaN and do not leak into neighbours much."""
    nan = ~np.isfinite(db)
    if nan.all():
        return db.copy()
    filled = np.where(nan, np.nanmedian(db), db)
    out = median_filter(filled, size=size, mode="nearest").astype("float32")
    out[nan] = np.nan
    return out


def lee_speckle(power: np.ndarray, size: int = 5, looks: float = 1.0) -> np.ndarray:
    """Lee filter on linear power. `looks` is the equivalent number of looks (sets the noise variance)."""
    nan = ~np.isfinite(power)
    if nan.all():
        return power.copy()
    p = np.where(nan, np.nanmean(power), power).astype("float64")
    mean = uniform_filter(p, size, mode="nearest")
    sq_mean = uniform_filter(p * p, size, mode="nearest")
    var = np.maximum(sq_mean - mean * mean, 0.0)
    noise_var = (mean * mean) / max(looks, 1e-6)
    gain = np.where(var > 0, np.maximum(var - noise_var, 0.0) / np.where(var > 0, var, 1.0), 0.0)
    out = (mean + gain * (p - mean)).astype("float32")
    out[nan] = np.nan
    return out


def reference_grid(src: Raster, res_m: float) -> tuple[tuple[int, int], Affine, CRS]:
    """The common grid: same area and (metric) CRS as `src`, pixels of res_m metres."""
    if src.crs is None or src.crs.is_geographic:
        raise ValueError("the reference radar image must be in a projected (metric) coordinate system")
    left, top = src.transform.c, src.transform.f
    width_m = src.shape[1] * abs(src.transform.a)
    height_m = src.shape[0] * abs(src.transform.e)
    shape = (int(height_m // res_m), int(width_m // res_m))
    if min(shape) < 1:
        raise ValueError("reference image is smaller than one grid pixel")
    return shape, Affine(res_m, 0.0, left, 0.0, -res_m, top), src.crs


def align_to(src: Raster, shape: tuple[int, int], transform: Affine, crs: CRS,
             resampling: Resampling = Resampling.average) -> Raster:
    """Reproject `src` onto the given grid. Pixels with no source data become NaN."""
    dst = np.full(shape, np.nan, dtype="float32")
    reproject(
        source=src.data.astype("float32"), destination=dst,
        src_transform=src.transform, src_crs=src.crs, src_nodata=np.nan,
        dst_transform=transform, dst_crs=crs, dst_nodata=np.nan,
        resampling=resampling,
    )
    return Raster(dst, transform, crs)
