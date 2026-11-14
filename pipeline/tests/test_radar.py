import numpy as np
import pytest
from affine import Affine
from rasterio.crs import CRS

from cutoff.radar import (Raster, align_to, lee_speckle, median_speckle, power_to_db, read_raster,
                          reference_grid, write_raster)

UTM = CRS.from_epsg(32617)


def test_power_to_db_values():
    out = power_to_db(np.array([1.0, 0.1, 0.0, np.nan, -1.0]))
    assert out[0] == pytest.approx(0.0)
    assert out[1] == pytest.approx(-10.0, abs=1e-5)
    assert np.isnan(out[2:]).all()          # 0, NaN and negative power are all NaN


def test_median_keeps_edges_and_removes_grain():
    rng = np.random.default_rng(1)
    img = np.zeros((40, 40), dtype="float32")
    img[:, 20:] = -10.0
    noisy = img + rng.normal(0, 1.5, img.shape).astype("float32")
    out = median_speckle(noisy, 5)
    assert out[5:-5, 5:15].std() < noisy[5:-5, 5:15].std() / 2          # grain reduced
    assert abs(out[20, 17] - 0.0) < 2 and abs(out[20, 23] - (-10.0)) < 2   # edge still there


def test_median_keeps_nan():
    img = np.full((10, 10), -12.0, dtype="float32")
    img[3, 3] = np.nan
    out = median_speckle(img, 3)
    assert np.isnan(out[3, 3]) and np.isfinite(out[0, 0])


def test_lee_reduces_variance_in_flat_area_and_keeps_nan():
    rng = np.random.default_rng(2)
    p = (rng.gamma(4.0, 0.25, (60, 60))).astype("float32")      # mean 1, 4 looks
    p[0, 0] = np.nan
    out = lee_speckle(p, 5, looks=4.0)
    assert np.isnan(out[0, 0])
    assert np.nanstd(out) < np.nanstd(p)


def test_write_read_roundtrip(tmp_path):
    data = np.arange(12, dtype="float32").reshape(3, 4)
    data[0, 0] = np.nan
    r = Raster(data, Affine(10, 0, 500000, 0, -10, 830000), UTM)
    write_raster(tmp_path / "a" / "x.tif", r)
    back = read_raster(tmp_path / "a" / "x.tif")
    assert np.array_equal(back.data, data, equal_nan=True)
    assert back.transform == r.transform and back.crs == UTM


def test_reference_grid_resolution():
    r = Raster(np.zeros((100, 120), "float32"), Affine(10, 0, 500000, 0, -10, 830000), UTM)
    shape, transform, crs = reference_grid(r, 20)
    assert shape == (50, 60)
    assert transform.a == 20 and transform.e == -20 and (transform.c, transform.f) == (500000, 830000)


def test_reference_grid_rejects_geographic():
    r = Raster(np.zeros((10, 10), "float32"), Affine(0.0001, 0, -81, 0, -0.0001, 8), CRS.from_epsg(4326))
    with pytest.raises(ValueError):
        reference_grid(r, 20)


def test_align_averages_power_onto_coarser_grid():
    data = np.ones((8, 8), "float32")
    data[:, 4:] = 3.0
    r = Raster(data, Affine(10, 0, 500000, 0, -10, 830000), UTM)
    shape, transform, crs = reference_grid(r, 20)
    out = align_to(r, shape, transform, crs)
    assert out.shape == (4, 4)
    assert np.allclose(out.data[:, :2], 1.0) and np.allclose(out.data[:, 2:], 3.0)


def test_align_outside_source_is_nan():
    r = Raster(np.ones((4, 4), "float32"), Affine(10, 0, 500000, 0, -10, 830000), UTM)
    out = align_to(r, (4, 4), Affine(10, 0, 600000, 0, -10, 830000), UTM)   # grid far to the east
    assert np.isnan(out.data).all()
