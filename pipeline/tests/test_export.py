import json

import numpy as np
import pytest
from affine import Affine
from pyproj import Transformer
from rasterio.crs import CRS
from shapely.geometry import Polygon, box

from cutoff.contract import _check_geometry
from cutoff.detect import Landslide
from cutoff.export import (MAX_PNG_SIDE, bounds_from_bbox, default_timeline, geometry_dict, landslide_features,
                           overlay_size, pair_entry, png_change, png_hv, png_names, to_lonlat, to_wgs84,
                           unknown_features, write_json)

UTM = CRS.from_epsg(32617)
BBOX = [-81.0, 7.3, -80.3, 8.0]


def utm_origin(lon, lat):
    return Transformer.from_crs(4326, UTM, always_xy=True).transform(lon, lat)


def test_hv_encoding():
    px = np.array(png_hv(np.array([[-25.0, -15.0, -5.0, np.nan, -40.0, 0.0]], dtype="float32")))
    assert px.shape == (1, 6, 2)
    assert px[0, 0, 0] == 0 and px[0, 2, 0] == 255          # -25 dB black, -5 dB white
    assert abs(int(px[0, 1, 0]) - 127) <= 1
    assert px[0, 3, 1] == 0 and (px[0, [0, 1, 2, 4, 5], 1] == 255).all()      # alpha 0 only where no data
    assert px[0, 4, 0] == 0 and px[0, 5, 0] == 255                              # clipped


def test_change_encoding():
    px = np.array(png_change(np.array([[-6.0, -0.5, 0.0, 6.0, np.nan, -10.0]], dtype="float32")))
    assert tuple(px[0, 0]) == (220, 38, 38, 255)             # red, full colour at -6 dB
    assert px[0, 1, 3] == 0 and px[0, 2, 3] == 0              # transparent near 0
    assert tuple(px[0, 3]) == (37, 99, 235, 255)              # blue for a rise
    assert px[0, 4, 3] == 0                                    # no data
    assert px[0, 5, 3] == 255


def test_overlay_never_exceeds_2048_and_keeps_aspect():
    w, h = overlay_size(BBOX, 20)
    assert max(w, h) == MAX_PNG_SIDE and abs(w - h) <= 1
    w, h = overlay_size([-80.9, 7.4, -80.8, 7.5], 20)          # small box: native detail, no upscaling
    assert max(w, h) < MAX_PNG_SIDE and w == pytest.approx(h, abs=1)


def test_to_wgs84_places_pixels_correctly():
    x0, y0 = utm_origin(-80.95, 7.95)
    data = np.full((300, 300), -12.0, dtype="float32")
    data[:150, :150] = -20.0                                   # top-left quarter darker
    t = Affine(20, 0, x0, 0, -20, y0)
    small = [-80.95, 7.90, -80.90, 7.95]                       # about 5.5 km box starting at the raster's corner
    out = to_wgs84(data, t, UTM, small, 20)
    assert out.shape == overlay_size(small, 20)[::-1]
    assert out[5, 5] == pytest.approx(-20.0, abs=0.01)          # near top-left: dark
    assert out[-5, -5] == pytest.approx(-12.0, abs=0.01) or np.isnan(out[-5, -5])


def test_to_wgs84_outside_coverage_is_nan():
    x0, y0 = utm_origin(-80.5, 7.5)
    out = to_wgs84(np.ones((50, 50), "float32"), Affine(20, 0, x0, 0, -20, y0), UTM, [-81.0, 7.3, -80.9, 7.4], 20)
    assert np.isnan(out).all()


def test_bounds_order():
    assert bounds_from_bbox(BBOX) == [[-81.0, 8.0], [-80.3, 8.0], [-80.3, 7.3], [-81.0, 7.3]]


def test_png_names_and_pair_entry():
    pair = {"id": "t141d", "track": 141, "direction": "descending", "before": "2026-09-27T23:53:35Z",
            "after": "2026-10-09T23:53:35Z", "granules": ["g"]}
    assert png_names(pair) == {"before_png": "hv_t141d_20260927.png", "after_png": "hv_t141d_20261009.png",
                               "change_png": "hv_change_t141d.png"}
    e = pair_entry(pair, BBOX, 1234)
    assert e["flagged_pixels"] == 1234 and e["granules"] == ["g"] and e["bounds"][0] == [-81.0, 8.0]


def test_geometry_dict_rounds_closes_and_orients():
    cw = Polygon([(0.12345678, 0.1), (0.12345678, 0.2), (0.22345678, 0.2), (0.22345678, 0.1)])   # clockwise
    g = geometry_dict(cw)
    ring = g["coordinates"][0]
    assert ring[0] == ring[-1] and ring[0][0] == 0.123457
    area2 = sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(ring, ring[1:]))
    assert area2 > 0                                           # counter-clockwise
    errors: list[str] = []
    _check_geometry(g, ("Polygon",), "test", errors)
    assert errors == []


def test_geometry_dict_drops_vanished_shapes():
    assert geometry_dict(Polygon([(0, 0), (1e-9, 0), (0, 1e-9)])) is None
    assert geometry_dict(Polygon()) is None


def test_landslide_features_are_simplified_reprojected_and_valid():
    x0, y0 = utm_origin(-80.87, 7.48)
    circle = Polygon([(x0 + 100 * np.cos(a), y0 + 100 * np.sin(a)) for a in np.linspace(0, 2 * np.pi, 200, endpoint=False)])
    props = {"id": "L0001", "area_m2": round(circle.area, 1)}
    feats = landslide_features([Landslide(circle, props)], UTM, 20.0)
    assert len(feats) == 1 and feats[0]["properties"] == props
    ring = feats[0]["geometry"]["coordinates"][0]
    assert len(ring) < 200                                      # simplified
    lon, lat = np.mean([p[0] for p in ring]), np.mean([p[1] for p in ring])
    assert lon == pytest.approx(-80.87, abs=0.001) and lat == pytest.approx(7.48, abs=0.001)
    assert all(round(v, 6) == v for p in ring for v in p)


def test_unknown_features_skip_tiny_patches():
    x0, y0 = utm_origin(-80.87, 7.48)
    mask = np.zeros((60, 60), dtype=bool)
    mask[10:30, 10:30] = True                                  # 400 px
    mask[50, 50] = True                                        # 1 px: dropped
    feats = unknown_features(mask, Affine(20, 0, x0, 0, -20, y0), UTM, 20.0)
    assert len(feats) == 1 and feats[0]["properties"] == {}


def test_to_lonlat_matches_pyproj():
    x0, y0 = utm_origin(-80.87, 7.48)
    p = to_lonlat(box(x0, y0, x0 + 1, y0 + 1), UTM)
    assert p.bounds[0] == pytest.approx(-80.87, abs=1e-5)


def test_default_timeline_uses_the_earliest_post_quake_pass():
    cfg = {"time_utc": "2026-10-09T17:56:00Z", "primary_pair": "t40d", "timeline": [],
           "pairs": [{"id": "t40d", "track": 40, "after": "2026-10-14T23:45:16Z"},
                     {"id": "t141d", "track": 141, "after": "2026-10-09T23:53:35Z"}]}
    t = default_timeline(cfg)
    assert t[0]["time_utc"] == cfg["time_utc"] and "track 141" in t[1]["label"] and t[1]["time_utc"] == "2026-10-09T23:53:35Z"
    cfg["timeline"] = [{"time_utc": "x", "label": "y", "source": "z"}]
    assert default_timeline(cfg) == cfg["timeline"]


def test_write_json_is_utf8_with_final_newline(tmp_path):
    write_json(tmp_path / "a.json", {"name": "Chitré"})
    raw = (tmp_path / "a.json").read_bytes()
    assert raw.endswith(b"\n") and "Chitré".encode("utf-8") in raw
    assert json.loads(raw)["name"] == "Chitré"
