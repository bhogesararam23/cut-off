import numpy as np
import pytest

from cutoff.terrain import look_azimuth, shadow_layover, slope_aspect


def ramp(rise_per_col=0.0, rise_per_row=0.0, n=20):
    rows, cols = np.mgrid[0:n, 0:n]
    return rise_per_col * cols + rise_per_row * rows


def test_slope_of_known_ramps():
    s, _ = slope_aspect(ramp(rise_per_col=1.0), 10.0, 10.0)      # 1 m rise per 10 m = 5.71 deg
    assert s[10, 10] == pytest.approx(np.degrees(np.arctan(0.1)), abs=0.01)
    s, _ = slope_aspect(np.zeros((10, 10)), 20.0, 20.0)
    assert (s == 0).all()


def test_aspect_is_the_downhill_compass_direction():
    # higher to the east -> faces west (270); higher to the south (rows increase south) -> faces north (0)
    _, a = slope_aspect(ramp(rise_per_col=1.0), 10, 10)
    assert a[10, 10] == pytest.approx(270.0, abs=0.01)
    _, a = slope_aspect(ramp(rise_per_row=1.0), 10, 10)
    assert min(a[10, 10], 360 - a[10, 10]) == pytest.approx(0.0, abs=0.01)
    _, a = slope_aspect(ramp(rise_per_col=-1.0), 10, 10)          # higher to the west -> faces east
    assert a[10, 10] == pytest.approx(90.0, abs=0.01)


def test_look_azimuth_is_right_of_heading():
    assert look_azimuth("ascending") == pytest.approx(80.0)      # roughly east
    assert look_azimuth("descending") == pytest.approx(280.0)    # roughly west
    assert look_azimuth("descending", heading_deg=180.0) == pytest.approx(270.0)
    with pytest.raises(ValueError):
        look_azimuth("sideways")


def test_steep_slope_facing_away_is_shadow_and_flat_is_not():
    look = 280.0
    slope = np.array([60.0, 60.0, 0.0])
    aspect = np.array([look, (look + 180) % 360, 0.0])           # away from radar, towards radar, flat
    unknown = shadow_layover(slope, aspect, look, incidence_deg=37.0)
    assert unknown.tolist() == [True, True, False]               # shadow, layover, fine


def test_gentle_slopes_are_visible_from_both_sides():
    look = 80.0
    slope = np.full(4, 15.0)
    aspect = np.array([look, look + 180, look + 90, look + 270])
    assert not shadow_layover(slope, aspect, look, 37.0).any()


def test_missing_dem_is_unknown():
    unknown = shadow_layover(np.array([np.nan, 10.0]), np.array([0.0, np.nan]), 80.0, 37.0)
    assert unknown.all()
