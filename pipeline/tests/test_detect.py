import numpy as np
import pytest
from affine import Affine

from cutoff.detect import (DetectParams, Landslide, candidate_mask, combine_votes, confidence, eligible_mask,
                           flag_rate, otsu_threshold, polygonise, remove_small_patches, visible_mask)

P = DetectParams()          # -3 dB, 10 deg, -16 dB, 3 px


def scene(n=30):
    before = np.full((n, n), -12.0, dtype="float32")
    dhv = np.zeros((n, n), dtype="float32")
    slope = np.full((n, n), 20.0, dtype="float32")
    unknown = np.zeros((n, n), dtype=bool)
    return before, dhv, slope, unknown


def test_six_by_six_drop_on_a_steep_slope_is_found():
    before, dhv, slope, unknown = scene()
    dhv[10:16, 10:16] = -5.0
    m = candidate_mask(dhv, before, slope, unknown, P)
    assert m.sum() == 36 and m[10:16, 10:16].all()


def test_same_drop_on_a_gentle_slope_is_not_found():
    before, dhv, slope, unknown = scene()
    slope[:] = 2.0
    dhv[10:16, 10:16] = -5.0
    assert not candidate_mask(dhv, before, slope, unknown, P).any()


def test_two_pixel_patch_is_removed_but_three_pixels_stay():
    before, dhv, slope, unknown = scene()
    dhv[5, 5:7] = -5.0
    dhv[20, 20:23] = -5.0
    m = candidate_mask(dhv, before, slope, unknown, P)
    assert not m[5, 5:7].any() and m[20, 20:23].all()


def test_diagonal_pixels_count_as_connected():
    m = np.zeros((6, 6), dtype=bool)
    m[1, 1] = m[2, 2] = m[3, 3] = True       # 8-connected diagonal of 3
    assert remove_small_patches(m, 3).sum() == 3


def test_not_forest_unknown_and_missing_pixels_are_excluded():
    before, dhv, slope, unknown = scene()
    dhv[:] = -5.0
    before[0:10, :] = -20.0                  # dark before: not forest (bare ground or water)
    unknown[10:20, :] = True                 # radar could not see
    dhv[20:25, :] = np.nan                   # no data
    m = candidate_mask(dhv, before, slope, unknown, P)
    assert not m[0:25].any() and m[25:].all()


def test_a_rise_is_not_a_landslide():
    before, dhv, slope, unknown = scene()
    dhv[10:16, 10:16] = +5.0
    assert not candidate_mask(dhv, before, slope, unknown, P).any()


def test_flag_rate_is_a_fraction_of_forested_slope():
    before, dhv, slope, unknown = scene(20)
    dhv[0:5, 0:20] = -5.0                    # 100 of 400 pixels
    vis = visible_mask(before, before, unknown)
    elig = eligible_mask(before, slope, vis, P)
    cand = candidate_mask(dhv, before, slope, unknown, P)
    assert flag_rate(cand, elig) == pytest.approx(0.25)
    assert flag_rate(cand, np.zeros_like(elig)) == 0.0


def test_otsu_separates_two_groups_and_is_clamped():
    rng = np.random.default_rng(3)
    dhv = np.concatenate([rng.normal(0, 0.5, 5000), rng.normal(-7, 0.5, 500)]).astype("float32")
    elig = np.ones(dhv.shape, dtype=bool)
    t = otsu_threshold(dhv, elig)
    assert -6.0 <= t <= -1.5
    assert otsu_threshold(dhv + 0, elig, lo=-2.0, hi=-1.5) >= -2.0          # clamp works
    assert otsu_threshold(np.zeros(100, "float32"), np.ones(100, bool)) == -3.0   # nothing to split


def test_votes_need_two_pairs_when_two_can_see():
    a, b, c = (np.zeros((4, 4), dtype=bool) for _ in range(3))
    a[0, 0] = b[0, 0] = True                 # seen by 2 -> kept
    a[1, 1] = True                           # seen by 1 of 3 visible -> dropped
    vis = [np.ones((4, 4), dtype=bool)] * 3
    keep, votes, visible = combine_votes([a, b, c], vis)
    assert keep[0, 0] and not keep[1, 1] and votes[0, 0] == 2 and visible[0, 0] == 3


def test_one_vote_is_enough_when_only_one_pair_can_see():
    a, b = np.zeros((3, 3), dtype=bool), np.zeros((3, 3), dtype=bool)
    a[1, 1] = True
    va, vb = np.ones((3, 3), dtype=bool), np.zeros((3, 3), dtype=bool)
    keep, _, _ = combine_votes([a, b], [va, vb])
    assert keep[1, 1]


def test_single_pair_keeps_its_candidates():
    a = np.zeros((3, 3), dtype=bool)
    a[1, 1] = True
    keep, _, _ = combine_votes([a], [np.ones((3, 3), dtype=bool)])
    assert keep[1, 1] and keep.sum() == 1


@pytest.mark.parametrize("seen,visible,expected", [
    (4, 4, "high"), (3, 4, "high"), (2, 4, "medium"), (2, 3, "high"), (2, 2, "high"), (1, 1, "low"), (1, 3, "low"),
])
def test_confidence_rule(seen, visible, expected):
    assert confidence(seen, visible) == expected


def test_polygonise_gives_one_polygon_per_patch_with_properties():
    n = 30
    transform = Affine(20, 0, 500000, 0, -20, 830000)
    before = np.full((n, n), -12.0, dtype="float32")
    after = before.copy()
    after[5:9, 5:9] = -18.0                  # patch A: 16 px
    after[20:23, 20:23] = -17.0              # patch B: 9 px
    slope = np.full((n, n), 25.0, dtype="float32")
    cand1 = (after - before) <= -3
    cand2 = np.zeros_like(cand1)
    cand2[5:9, 5:9] = True                   # second pair sees only patch A
    vis = [np.ones((n, n), dtype=bool)] * 2
    keep, _, _ = combine_votes([cand1, cand2], vis)
    slides = polygonise(keep, [cand1, cand2], vis, [before, before], [after, after], slope, transform)
    assert len(slides) == 1                  # patch B has one vote but two pairs could see it: dropped
    s: Landslide = slides[0]
    assert s.props["id"] == "L0001"
    assert s.props["area_m2"] == pytest.approx(16 * 400.0)
    assert s.props["hv_before_db"] == -12.0 and s.props["hv_after_db"] == -18.0 and s.props["dhv_db"] == -6.0
    assert s.props["slope_deg"] == 25.0
    assert s.props["pairs_seen"] == 2 and s.props["pairs_visible"] == 2 and s.props["confidence"] == "high"
    minx, miny, maxx, maxy = s.geometry.bounds
    assert (minx, maxx) == (500000 + 5 * 20, 500000 + 9 * 20) and (maxy, miny) == (830000 - 5 * 20, 830000 - 9 * 20)


def test_polygonise_falls_back_to_second_pair_for_statistics():
    n = 12
    transform = Affine(20, 0, 0, 0, -20, 0)
    nan = np.full((n, n), np.nan, dtype="float32")
    before = np.full((n, n), -12.0, dtype="float32")
    after = before.copy()
    after[3:6, 3:6] = -18.0
    cand = np.zeros((n, n), dtype=bool)
    cand[3:6, 3:6] = True
    vis = [np.zeros((n, n), dtype=bool), np.ones((n, n), dtype=bool)]       # primary cannot see it
    keep, _, _ = combine_votes([np.zeros_like(cand), cand], vis)
    slides = polygonise(keep, [np.zeros_like(cand), cand], vis, [nan, before], [nan, after],
                        np.full((n, n), 15.0, "float32"), transform)
    assert slides[0].props["dhv_db"] == -6.0 and slides[0].props["pairs_seen"] == 1 and slides[0].props["pairs_visible"] == 1


# ---- removing the region-wide shift ----

def test_local_mean_ignores_missing_pixels():
    from cutoff.detect import local_mean
    x = np.full((20, 20), -2.0, dtype="float32")
    x[5:8, 5:8] = np.nan
    m = local_mean(x, 5)
    assert np.allclose(m[np.isfinite(x)], -2.0) and np.isnan(m[6, 6])


def test_a_region_wide_drop_is_removed_but_a_local_one_stays():
    from cutoff.detect import adjusted_change
    dhv = np.full((60, 60), -2.0, dtype="float32")               # wet ground everywhere: 2 dB down
    dhv[30:33, 30:33] = -6.0                                        # a small patch 4 dB below its surroundings
    visible = np.ones((60, 60), bool)
    raw = adjusted_change(dhv, visible, 0)
    adj = adjusted_change(dhv, visible, 21)
    assert raw[10, 10] == -2.0 and abs(adj[10, 10]) < 0.1            # the shift is gone far from the patch
    assert adj[31, 31] < -3.0                                         # the patch is still clearly below its surroundings


def test_unseen_pixels_stay_missing_after_the_correction():
    from cutoff.detect import adjusted_change
    dhv = np.zeros((30, 30), dtype="float32")
    visible = np.ones((30, 30), bool)
    visible[:, :5] = False
    adj = adjusted_change(dhv, visible, 11)
    assert np.isnan(adj[:, :5]).all() and np.isfinite(adj[:, 5:]).all()
