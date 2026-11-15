# Method

This page describes exactly what was done and how well it worked. Numbers that appear in the README and on the website come from `stats.json`; the tables below come from the files in `data/validation/`.

## Question
Can NISAR L-band radar change detection find leads to the landslides of the 9 October 2026 Panama earthquake (magnitude 7.7, USGS event [us6000u18k](https://earthquake.usgs.gov/earthquakes/eventpage/us6000u18k)) over forested slopes, and can those leads be turned into a list of roads likely blocked and communities possibly cut off? Short answer: only weakly. The revised method finds about a third of the hand-marked landslide points, mostly the larger ones, and almost everything it flags is unconfirmed.

Radar can collect images through cloud and at night. This analysis looks for changes in the radar signal over forested slopes. Vegetation, soil moisture, viewing geometry and other factors also change the signal, so a change is a lead, not a confirmed landslide.

## Data
- **Radar:** NASA-ISRO NISAR Level-2 GCOV, PROVISIONAL release, HV polarisation (the `HVHV` layer, linear power on a 10 m UTM grid), from the Alaska Satellite Facility DAAC through NASA Earthdata Search and the Harmony service, trimmed to the study box (west -81.0, south 7.3, east -80.3, north 8.0).
- **Elevation:** Copernicus DEM GLO-30 (tile N07 W081).
- **Roads and places:** OpenStreetMap, Geofabrik Panama extract of 13 November 2026: roads tagged trunk, primary, secondary, tertiary, unclassified, residential or track, and places tagged town, village or hamlet, in the box widened by 0.15 degrees.
- **Check points:** Copernicus Sentinel-2 L2A images (see Validation).
- **Event reference:** Copernicus EMS [EMSR934](https://mapping.emergency.copernicus.eu/news/earthquake-in-los-santos-panama-emsr934/).

| Pair | Track | Before | After | Before granule | After granule |
|---|---|---|---|---|---|
| t141d | 141 descending | 2026-09-27 | 2026-10-09 | `NISAR_L2_PR_GCOV_031_141_D_085_4005_DHDH_A_20260927T235335_20260927T235344_P05023_N_P_J_001` | `NISAR_L2_PR_GCOV_032_141_D_085_4005_DHDH_A_20261009T235335_20261009T235345_P05023_N_P_J_001` |
| t4a | 4 ascending | 2026-09-30 | 2026-10-12 | `NISAR_L2_PR_GCOV_032_004_A_005_4005_DHDH_A_20260930T110420_20260930T110435_P05023_N_P_J_001` | `NISAR_L2_PR_GCOV_033_004_A_005_4005_DHDH_A_20261012T110420_20261012T110436_P05023_N_P_J_001` |
| t40d | 40 descending | 2026-10-02 | 2026-10-14 | `NISAR_L2_PR_GCOV_032_040_D_085_4005_DHDH_A_20261002T234516_20261002T234533_P05023_N_P_J_001` | `NISAR_L2_PR_GCOV_033_040_D_085_4005_DHDH_A_20261014T234516_20261014T234533_P05023_N_P_J_001` |
| t76a | 76 ascending | 2026-10-05 | 2026-10-17 | `NISAR_L2_PR_GCOV_032_076_A_005_4005_DHDH_A_20261005T105604_20261005T105616_P05023_N_P_J_001` | `NISAR_L2_PR_GCOV_033_076_A_005_4005_DHDH_A_20261017T105604_20261017T105616_P05023_N_P_J_001` |

The **pre-event baseline** is track 40, 20 September against 2 October 2026 (`NISAR_L2_PR_GCOV_031_040_D_085_4005_DHDH_A_20260920T234516_20260920T234532_P05023_N_P_J_001` and the track 40 "before" granule above): ordinary change between two passes before the quake. Rain, soil moisture, farming and vegetation can change over 12 days. Granule names follow the ASF archive listing; the files were ordered by hand. The radar images cover only part of the box: about 40% for track 141, 23% for track 4, 75% for track 40 and 61% for track 76 (the share of the grid each pair can see).

## Processing steps
1. Build one grid (20 m pixels) from the first pair's "before" image. All images are averaged as linear power onto it, then converted to dB and smoothed with a 5 x 5 median filter. Only images from the same track are ever compared.
2. Slope and aspect come from the Copernicus DEM resampled onto the same grid.
3. Slopes that face the radar steeply (layover) or face away steeply (shadow) are marked unknown for that pair, using the radar's look direction and incidence angle.
4. Change = HV after minus HV before, in dB.
5. **Local reference (new in the revised method).** The pair's own mean change in a 11 x 11 pixel window (220 m) is subtracted from every pixel. Reason: a slow, region-wide shift (wetter soil, calibration drift, a different viewing geometry) moves every pixel together and says nothing about a landslide; what matters is a pixel that drops more than its surroundings. The correction is applied the same way to every pair and to the baseline pair, so before-and-after flag rates can be compared fairly.
6. A pixel is a candidate in a pair if the corrected change is at or below the threshold, the slope is steep enough, the ground was bright forest in the "before" image, and the radar could see it. Patches smaller than 3 connected pixels are removed.
7. Pairs are combined by voting: a pixel is kept if enough pairs flag it, where "enough" is two when at least two pairs could see it, and one otherwise. After voting, patches smaller than 3 connected pixels are removed again. **Each remaining connected patch is one candidate landslide object** (an 8-connected group of flagged 20 m pixels, so at least 0.12 ha). It gets its area, mean HV before and after, mean slope, how many pairs flagged it and how many could see it.
8. The same detection runs on the baseline pair. The share of forested slope it flags is compared with the share flagged in the post-quake pair from the same track (track 40, 2 to 14 October), which has the same viewing geometry.
9. Roads are cut into pieces of at most 500 m and each piece gets a status: "likely blocked" if a candidate landslide lies within 10 m (it touches the road), "at risk" within 100 m, "unknown" if at least half of the piece lies where the radar could not see, otherwise "clear". Nobody saw a blockage: this is inferred from the candidate being next to the road. Collapsed bridges and sinking roads cannot be seen by this method.
10. A road graph is built from the OpenStreetMap lines (road points within 1 m are joined). A community is "possibly cut off" if it could reach a main town on the full map, but every route crosses a likely-blocked piece. It is "reachable" if a route without such a piece remains. It is "unknown" if no mapped road lies within 2 km, or its roads do not reach any main town even on the full map (a gap in the map is not reported as a blockage).

## Parameters used (revised method)
| Setting | Value | How it was set |
|---|---|---|
| Grid | 20 m pixels, UTM zone 17N (EPSG:32617), taken from the track 141 "before" image | fixed in advance |
| Speckle filter | 5 x 5 median on dB | fixed in advance |
| Local-mean window | **11 pixels (220 m)** | chosen on the tuning half (table below) |
| Drop threshold | **-1.0 dB** below the local mean | chosen on the tuning half |
| Minimum slope | 10 degrees | fixed in advance |
| Forest test | HV before at least -16 dB | fixed in advance |
| Smallest patch | 3 connected pixels | fixed in advance |
| Incidence angle for shadow/layover | 37 degrees; headings 350 (ascending) and 190 (descending) degrees, not read from the files | fixed in advance |
| Voting | kept if flagged by at least two pairs, or by one pair when only one pair could see the pixel | fixed in advance |
| Road status | likely blocked within 10 m of a candidate, at risk within 100 m, pieces of at most 500 m | fixed in advance |
| Community status | unknown if no mapped road within 2 km | fixed in advance |
| Main towns | Chitré, Las Tablas, Tonosí, Macaracas, Santiago | fixed in advance |

The original method used a threshold of -1.5 dB and no local-mean correction.

## Validation
The validation set is 183 check points from Sentinel-2 L2A NDVI change (8/22 Sep vs 18/28 Oct 2026): 114 landslide points (63 small, 49 medium, 2 large) and 69 forest points. An AI tool suggested candidate points from the change in vegetation greenness and every point was checked by eye. NISAR values were never used to pick them. The file `data/validation/points.csv` was committed before anything was scored.

**What this is and is not.** This is a random split of points within one study area, labelled from optical imagery and checked by eye. It is not independent geographic validation and not field validation; nearby points may share conditions. The forest points were picked as clearly intact forest, so the false-alarm rate is probably lower than it would be across all forest.

1. The points are split 50/50 within each label (landslide, forest) with a fixed random seed (2026): a tuning half (57 landslide, 35 forest points) and a held-out half (57 landslide, 34 forest points).
2. The method settings (local-mean window and drop threshold) are chosen on the tuning half only. The rule, written before the second scoring: a setting must flag less forested slope before the quake than after it (same track, same method) and no more than 5% of forested slope after it (an assumption: a landslide map that flags a larger share of all forested slope is not credible); among those settings, the best AUC on the tuning points wins, then the best detection rate minus false-alarm rate (Youden's J), then the threshold nearest -3 dB.
3. Detection is rerun with those settings. The held-out half is then scored: a landslide point counts as found if a candidate landslide polygon lies within 20 m of it, and a forest point counts as a false alarm if one does.
4. AUC: the chance that a landslide point gets a higher score than a forest point (0.5 = guessing, 1.0 = perfect). In the first scoring the score was the radar change of the primary pair (track 141) at the point. In the revised scoring the score is the mean over the four pairs of the strongest corrected drop within one pixel (20 m) of the point. The two AUC values therefore use different scoring rules. Using the primary pair alone with the revised rule, the held-out AUC is 0.71 (`auc_primary_pair_only` in `data/validation/scoring_2_revised_method.json`).
5. The code refuses to score the held-out half again unless it is forced, and every scoring is logged.

**The held-out half was scored twice: first on the original method, then after the method was revised using the tuning half only. Both results are shown.** The revision was made after seeing that the first result was poor, so the second result is better than a single pre-registered scoring would be; the numbers have not been tuned on the held-out half, but the decision to try a revised method was prompted by the first result.

## Results
| Held-out half (57 landslide, 34 forest points) | First scoring: original method | Second scoring: revised method |
|---|---|---|
| Landslide points found | 12 of 57 (21%) | 19 of 57 (33%) |
| Forest points flagged | 1 of 34 (3%) | 0 of 34 (0%) |
| AUC | 0.55 | 0.86 |
| Found, small landslides | 13% (n = 30) | 20% (n = 30) |
| Found, medium landslides | 30% (n = 27) | 48% (n = 27) |
| Found, large landslides | n = 0 (both large points fell in the tuning half) | n = 0 |
| Drop threshold | -1.5 dB | -1.0 dB below the local mean (11 pixel window) |

**Candidate landslides (revised method):** 8,442 objects covering 19.13 km² of forested slope. Their median area is 1,600 m² (4 pixels); 90% are under 4,000 m²; only 43 are larger than 1 ha. About 64% (5,393) were flagged by one pass only, 2,296 by two, 732 by three and 21 by all four. These are leads: the share of forested slope flagged after the quake is 4.8%, and the check points are too few and too easy to say how many objects are real.

**Pre-event baseline:** with the revised method, 3.30% of forested slope was flagged between the two passes before the quake, against 4.80% in the pair spanning the quake from the same track. The ratio is about 1.5, not large. With the original method and the same-track comparison the numbers were 3.4% and 2.8% (baseline higher than after the quake): the detector flagged as much change without an earthquake as with one, so single detections are weak evidence. The first run compared the baseline (track 40) with a pair from a different track (track 141) and gave 3.4% and 1.8%.

**Roads and communities (revised method):** 92.2 km of road likely blocked and 102 of 460 mapped places possibly cut off (337 reachable, 21 unknown). With the original method the figures were 46.1 km and 7 communities. These counts rise and fall with how many candidates are flagged, so they say more about the threshold than about the roads.

## What was tried
Every setting below was scored on the **tuning half only**. The held-out half was not read while any of these were tried. The tables show the ones that did not help as well as the one that was kept.

**Final search** (run by the code, `python -m cutoff tune`; saved in `data/validation/tuning_2_revised_method.json`). The selection rule is applied to this table: the chosen row is window 11, threshold -1 dB.

| Local-mean window (px) | Threshold (dB) | Tuning AUC | Found | False alarms | Found minus false alarms | Flagged before quake | Flagged after quake | Passes the before/after rule |
|---|---|---|---|---|---|---|---|---|
| off | -0.5 | 0.774 | 50.9% | 20.0% | +0.309 | 25.86% | 25.41% | no |
| off | -0.75 | 0.774 | 38.6% | 5.7% | +0.329 | 16.28% | 15.77% | no |
| off | -1 | 0.774 | 24.6% | 0.0% | +0.246 | 9.80% | 9.21% | no |
| off | -1.25 | 0.774 | 17.5% | 0.0% | +0.175 | 5.76% | 5.17% | no |
| off | -1.5 | 0.774 | 12.3% | 0.0% | +0.123 | 3.36% | 2.82% | no |
| off | -2 | 0.774 | 7.0% | 0.0% | +0.070 | 1.17% | 0.82% | no |
| off | -2.5 | 0.774 | 5.3% | 0.0% | +0.053 | 0.41% | 0.25% | no |
| off | -3 | 0.774 | 3.5% | 0.0% | +0.035 | 0.15% | 0.09% | no |
| off | -4 | 0.774 | 0.0% | 0.0% | +0.000 | 0.02% | 0.02% | no |
| off | -5 | 0.774 | 0.0% | 0.0% | +0.000 | 0.00% | 0.01% | yes |
| off | -6 | 0.774 | 0.0% | 0.0% | +0.000 | 0.00% | 0.00% | yes |
| 11 | -0.5 | 0.855 | 52.6% | 17.1% | +0.355 | 16.14% | 19.10% | no |
| 11 | -0.75 | 0.855 | 35.1% | 2.9% | +0.322 | 7.51% | 9.90% | no |
| 11 | -1 | 0.855 | 19.3% | 0.0% | +0.193 | 3.30% | 4.80% | yes |
| 11 | -1.25 | 0.855 | 14.0% | 0.0% | +0.140 | 1.45% | 2.27% | yes |
| 11 | -1.5 | 0.855 | 7.0% | 0.0% | +0.070 | 0.67% | 1.08% | yes |
| 11 | -2 | 0.855 | 3.5% | 0.0% | +0.035 | 0.17% | 0.27% | yes |
| 11 | -2.5 | 0.855 | 3.5% | 0.0% | +0.035 | 0.05% | 0.07% | yes |
| 11 | -3 | 0.855 | 0.0% | 0.0% | +0.000 | 0.01% | 0.03% | yes |
| 11 | -4 | 0.855 | 0.0% | 0.0% | +0.000 | 0.00% | 0.00% | yes |
| 11 | -5 | 0.855 | 0.0% | 0.0% | +0.000 | 0.00% | 0.00% | yes |
| 11 | -6 | 0.855 | 0.0% | 0.0% | +0.000 | 0.00% | 0.00% | no |
| 21 | -0.5 | 0.838 | 56.1% | 14.3% | +0.418 | 18.73% | 21.82% | no |
| 21 | -0.75 | 0.838 | 42.1% | 2.9% | +0.393 | 9.87% | 12.47% | no |
| 21 | -1 | 0.838 | 28.1% | 0.0% | +0.281 | 4.90% | 6.69% | no |
| 21 | -1.25 | 0.838 | 17.5% | 0.0% | +0.175 | 2.41% | 3.46% | yes |
| 21 | -1.5 | 0.838 | 12.3% | 0.0% | +0.123 | 1.22% | 1.78% | yes |
| 21 | -2 | 0.838 | 5.3% | 0.0% | +0.053 | 0.35% | 0.50% | yes |
| 21 | -2.5 | 0.838 | 3.5% | 0.0% | +0.035 | 0.12% | 0.16% | yes |
| 21 | -3 | 0.838 | 3.5% | 0.0% | +0.035 | 0.04% | 0.06% | yes |
| 21 | -4 | 0.838 | 0.0% | 0.0% | +0.000 | 0.01% | 0.01% | yes |
| 21 | -5 | 0.838 | 0.0% | 0.0% | +0.000 | 0.00% | 0.00% | yes |
| 21 | -6 | 0.838 | 0.0% | 0.0% | +0.000 | 0.00% | 0.00% | yes |
| 31 | -0.5 | 0.833 | 56.1% | 14.3% | +0.418 | 19.23% | 22.33% | no |
| 31 | -0.75 | 0.833 | 43.9% | 5.7% | +0.382 | 10.40% | 12.98% | no |
| 31 | -1 | 0.833 | 31.6% | 0.0% | +0.316 | 5.31% | 7.07% | no |
| 31 | -1.25 | 0.833 | 19.3% | 0.0% | +0.193 | 2.68% | 3.70% | yes |
| 31 | -1.5 | 0.833 | 14.0% | 0.0% | +0.140 | 1.39% | 1.93% | yes |
| 31 | -2 | 0.833 | 7.0% | 0.0% | +0.070 | 0.42% | 0.55% | yes |
| 31 | -2.5 | 0.833 | 5.3% | 0.0% | +0.053 | 0.15% | 0.18% | yes |
| 31 | -3 | 0.833 | 3.5% | 0.0% | +0.035 | 0.05% | 0.07% | yes |
| 31 | -4 | 0.833 | 0.0% | 0.0% | +0.000 | 0.01% | 0.01% | yes |
| 31 | -5 | 0.833 | 0.0% | 0.0% | +0.000 | 0.00% | 0.00% | yes |
| 31 | -6 | 0.833 | 0.0% | 0.0% | +0.000 | 0.00% | 0.00% | yes |
| 51 | -0.5 | 0.828 | 52.6% | 17.1% | +0.355 | 19.58% | 22.64% | no |
| 51 | -0.75 | 0.828 | 42.1% | 5.7% | +0.364 | 10.76% | 13.27% | no |
| 51 | -1 | 0.828 | 33.3% | 0.0% | +0.333 | 5.60% | 7.29% | no |
| 51 | -1.25 | 0.828 | 19.3% | 0.0% | +0.193 | 2.90% | 3.86% | yes |
| 51 | -1.5 | 0.828 | 14.0% | 0.0% | +0.140 | 1.53% | 2.02% | yes |
| 51 | -2 | 0.828 | 8.8% | 0.0% | +0.088 | 0.47% | 0.58% | yes |
| 51 | -2.5 | 0.828 | 5.3% | 0.0% | +0.053 | 0.17% | 0.19% | yes |
| 51 | -3 | 0.828 | 3.5% | 0.0% | +0.035 | 0.06% | 0.08% | yes |
| 51 | -4 | 0.828 | 0.0% | 0.0% | +0.000 | 0.01% | 0.02% | yes |
| 51 | -5 | 0.828 | 0.0% | 0.0% | +0.000 | 0.00% | 0.01% | yes |
| 51 | -6 | 0.828 | 0.0% | 0.0% | +0.000 | 0.00% | 0.00% | yes |
| 101 | -0.5 | 0.826 | 52.6% | 17.1% | +0.355 | 19.78% | 22.81% | no |
| 101 | -0.75 | 0.826 | 43.9% | 5.7% | +0.382 | 11.02% | 13.48% | no |
| 101 | -1 | 0.826 | 35.1% | 2.9% | +0.322 | 5.85% | 7.44% | no |
| 101 | -1.25 | 0.826 | 21.1% | 0.0% | +0.210 | 3.06% | 3.96% | yes |
| 101 | -1.5 | 0.826 | 15.8% | 0.0% | +0.158 | 1.64% | 2.08% | yes |
| 101 | -2 | 0.826 | 8.8% | 0.0% | +0.088 | 0.51% | 0.60% | yes |
| 101 | -2.5 | 0.826 | 5.3% | 0.0% | +0.053 | 0.18% | 0.20% | yes |
| 101 | -3 | 0.826 | 3.5% | 0.0% | +0.035 | 0.07% | 0.08% | yes |
| 101 | -4 | 0.826 | 0.0% | 0.0% | +0.000 | 0.01% | 0.02% | yes |
| 101 | -5 | 0.826 | 0.0% | 0.0% | +0.000 | 0.00% | 0.01% | yes |
| 101 | -6 | 0.826 | 0.0% | 0.0% | +0.000 | 0.00% | 0.00% | yes |

The last column applies the rule's two conditions. Tuning AUC depends on the window only; it rises as the window shrinks from 101 to 11 pixels. Note that the chosen row finds 19% of the tuning landslide points: the AUC is high because landslide points rank above forest points, not because many landslides are flagged.

**First exploration** (an ad hoc script that is not kept in the repository, run before the code above existed; tuning half only). It tried smoothing, a division by local noise, subtracting the baseline change, and larger minimum patches. Thresholds from 1.5 upward were tried for these (more sensitive ones only for the settings that looked promising). "Tuning AUC (4 passes)" scores each point as in the revised method.

| Smoothing (px) | Change measure | Natural-change correction | Min patch (px) | Tuning AUC (4 passes) | Tuning AUC (primary pair only) | Best Youden J (at threshold) | Found / false alarms there | Flagged before vs after the quake there |
|---|---|---|---|---|---|---|---|---|
| 1 | dB change | none | 3 | 0.775 | 0.575 | 0.123 (drop of 1.5 dB) | 12% / 0% | 3.4% vs 2.9% |
| 1 | dB change | none | 8 | 0.775 | 0.575 | 0.088 (drop of 1.5 dB) | 9% / 0% | 2.6% vs 2.0% |
| 1 | dB change | subtract the 1 km mean of the baseline change | 3 | 0.762 | 0.532 | 0.105 (drop of 1.5 dB) | 11% / 0% | 1.5% vs 4.5% |
| 1 | dB change | subtract the 1 km mean of the baseline change | 8 | 0.762 | 0.532 | 0.053 (drop of 1.5 dB) | 5% / 0% | 1.0% vs 3.6% |
| 1 | dB change | subtract the baseline change pixel by pixel | 3 | 0.753 | 0.615 | 0.200 (drop of 1.5 dB) | 23% / 3% | not testable (built from the baseline) |
| 1 | dB change | subtract the baseline change pixel by pixel | 8 | 0.753 | 0.615 | 0.158 (drop of 1.5 dB) | 16% / 0% | not testable (built from the baseline) |
| 1 | dB change divided by local texture of the before image | none | 3 | 0.607 | 0.441 | 0.129 (drop of 1.5 σ) | 16% / 3% | 7.2% vs 5.8% |
| 1 | dB change divided by local texture of the before image | none | 8 | 0.607 | 0.441 | 0.140 (drop of 1.5 σ) | 14% / 0% | 6.0% vs 4.6% |
| 1 | dB change divided by local texture of the before image | subtract the 1 km mean of the baseline change | 3 | 0.671 | 0.487 | 0.094 (drop of 1.5 σ) | 12% / 3% | 3.8% vs 7.6% |
| 1 | dB change divided by local texture of the before image | subtract the 1 km mean of the baseline change | 8 | 0.671 | 0.487 | 0.088 (drop of 1.5 σ) | 9% / 0% | 2.7% vs 6.6% |
| 1 | dB change divided by local texture of the before image | subtract the baseline change pixel by pixel | 3 | 0.651 | 0.516 | 0.127 (drop of 1.5 σ) | 30% / 17% | not testable (built from the baseline) |
| 1 | dB change divided by local texture of the before image | subtract the baseline change pixel by pixel | 8 | 0.651 | 0.516 | 0.090 (drop of 1.5 σ) | 18% / 9% | not testable (built from the baseline) |
| 1 | dB change divided by local noise of the baseline | none | 3 | 0.736 | 0.549 | 0.182 (drop of 1.5 σ) | 21% / 3% | 11.4% vs 12.4% |
| 1 | dB change divided by local noise of the baseline | none | 8 | 0.736 | 0.549 | 0.193 (drop of 1.5 σ) | 19% / 0% | 9.3% vs 10.3% |
| 1 | dB change divided by local noise of the baseline | subtract the 1 km mean of the baseline change | 3 | 0.706 | 0.501 | 0.158 (drop of 2 σ) | 16% / 0% | 2.0% vs 9.1% |
| 1 | dB change divided by local noise of the baseline | subtract the 1 km mean of the baseline change | 8 | 0.706 | 0.501 | 0.105 (drop of 2 σ) | 11% / 0% | 0.8% vs 7.8% |
| 1 | dB change divided by local noise of the baseline | subtract the baseline change pixel by pixel | 3 | 0.709 | 0.578 | 0.256 (drop of 1.5 σ) | 46% / 20% | not testable (built from the baseline) |
| 1 | dB change divided by local noise of the baseline | subtract the baseline change pixel by pixel | 8 | 0.709 | 0.578 | 0.259 (drop of 1.5 σ) | 32% / 6% | not testable (built from the baseline) |
| 3 | dB change | none | 3 | 0.739 | 0.513 | 0.105 (drop of 1.5 dB) | 11% / 0% | 2.2% vs 1.5% |
| 3 | dB change | none | 8 | 0.739 | 0.513 | 0.070 (drop of 1.5 dB) | 7% / 0% | 1.9% vs 1.2% |
| 3 | dB change | subtract the 1 km mean of the baseline change | 3 | 0.719 | 0.475 | 0.088 (drop of 1.5 dB) | 9% / 0% | 0.7% vs 3.2% |
| 3 | dB change | subtract the 1 km mean of the baseline change | 8 | 0.719 | 0.475 | 0.070 (drop of 1.5 dB) | 7% / 0% | 0.6% vs 2.9% |
| 3 | dB change | subtract the baseline change pixel by pixel | 3 | 0.702 | 0.542 | 0.140 (drop of 1.5 dB) | 14% / 0% | not testable (built from the baseline) |
| 3 | dB change | subtract the baseline change pixel by pixel | 8 | 0.702 | 0.542 | 0.105 (drop of 1.5 dB) | 11% / 0% | not testable (built from the baseline) |
| 3 | dB change divided by local texture of the before image | none | 3 | 0.596 | 0.431 | 0.077 (drop of 1.5 σ) | 11% / 3% | 5.4% vs 4.0% |
| 3 | dB change divided by local texture of the before image | none | 8 | 0.596 | 0.431 | 0.105 (drop of 1.5 σ) | 11% / 0% | 4.9% vs 3.5% |
| 3 | dB change divided by local texture of the before image | subtract the 1 km mean of the baseline change | 3 | 0.659 | 0.463 | 0.088 (drop of 1.5 σ) | 9% / 0% | 2.2% vs 6.1% |
| 3 | dB change divided by local texture of the before image | subtract the 1 km mean of the baseline change | 8 | 0.659 | 0.463 | 0.053 (drop of 1.5 σ) | 5% / 0% | 1.8% vs 5.6% |
| 3 | dB change divided by local texture of the before image | subtract the baseline change pixel by pixel | 3 | 0.637 | 0.480 | 0.070 (drop of 2.5 σ) | 7% / 0% | not testable (built from the baseline) |
| 3 | dB change divided by local texture of the before image | subtract the baseline change pixel by pixel | 8 | 0.637 | 0.480 | 0.066 (drop of 1.5 σ) | 12% / 6% | not testable (built from the baseline) |
| 3 | dB change divided by local noise of the baseline | none | 3 | 0.751 | 0.503 | 0.193 (drop of 1.5 σ) | 19% / 0% | 8.1% vs 9.1% |
| 3 | dB change divided by local noise of the baseline | none | 8 | 0.751 | 0.503 | 0.158 (drop of 1.5 σ) | 16% / 0% | 7.2% vs 8.2% |
| 3 | dB change divided by local noise of the baseline | subtract the 1 km mean of the baseline change | 3 | 0.694 | 0.476 | 0.147 (drop of 1.5 σ) | 18% / 3% | 3.2% vs 12.9% |
| 3 | dB change divided by local noise of the baseline | subtract the 1 km mean of the baseline change | 8 | 0.694 | 0.476 | 0.094 (drop of 1.5 σ) | 12% / 3% | 2.3% vs 12.1% |
| 3 | dB change divided by local noise of the baseline | subtract the baseline change pixel by pixel | 3 | 0.663 | 0.508 | 0.166 (drop of 1.5 σ) | 28% / 11% | not testable (built from the baseline) |
| 3 | dB change divided by local noise of the baseline | subtract the baseline change pixel by pixel | 8 | 0.663 | 0.508 | 0.153 (drop of 1.5 σ) | 21% / 6% | not testable (built from the baseline) |
| 3 | dB change | subtract the 1 km mean of the baseline change (slope 20°, forest HV -14 dB) | 8 | 0.719 | 0.475 | 0.053 (drop of 1.5 dB) | 5% / 0% | 0.8% vs 1.6% |
| 3 | dB change | none (slope 20°, forest HV -14 dB) | 8 | 0.739 | 0.513 | 0.053 (drop of 1.5 dB) | 5% / 0% | 2.1% vs 1.1% |

What this showed, in plain words:
- **Smoothing over 3 x 3 pixels hurt** the AUC (0.775 to 0.739): landslides at the check points are only about 1 to 3 pixels wide, so smoothing blurs them away.
- **Dividing by local noise** (the texture of the before image, or the local noise of the baseline change) gave no better AUC, and the baseline-noise version made the before and after flag rates almost equal.
- **Subtracting the baseline change** pixel by pixel raises the share flagged after the quake but cannot be tested: the baseline pair minus itself is zero, so its flag rate says nothing. Subtracting only its 1 km mean lowered the baseline flag rate, but partly by construction (the baseline is used to build the correction it is then tested on), and it did not raise the AUC.
- **Larger minimum patches** (8 pixels) lowered the share found without changing the AUC.
- **A steeper slope and brighter forest mask** (20 degrees, -14 dB) found fewer points and did not help.
- **The local-mean correction applied to each pair's own change** (the revised method) raised the tuning AUC from 0.775 to 0.855 for an 11 pixel window and made the flag rate before the quake lower than after it at every threshold tried except -6 dB, where both rates are close to zero. It treats the baseline and the post-quake pairs identically, so the comparison is fair.

## Comparison with reports from the ground
News reports said the towns of Arenas, El Cacao and Quebro (Veraguas) were cut off after roads collapsed ([Newsroom Panama](https://newsroompanama.com/2026/10/17/2351-landslides-at-least-were-caused-by-the-earthquake-in-panama/), 17 Oct 2026). With the revised method, the mapped places named Arenas, El Cacao and La Loma de Quebro come out as "possibly cut off", while Los Arenas and a second place called El Cacao come out as "reachable". With the original method all of them were "reachable". Because 102 of 460 mapped places are now "possibly cut off", agreement with the reports could be chance: the method cannot see collapsed roads or bridges, and the reports describe road collapses. These communities are leads, not confirmed.

## Limitations
- **Weak accuracy.** The revised method found about a third of the held-out landslide points, and only a fifth of the small ones. Every detection is a lead to verify, not a finding.
- **The before/after separation is small.** The pre-event baseline flags 3.3% of forested slope; the quake pair flags 4.8%. Natural change over 12 days (rain and soil moisture, farming, vegetation) is a large part of the signal.
- **A random split in one area is not independent validation.** The tuning and held-out points come from the same images and the same area; nearby points may share conditions. The held-out half was scored twice (see above).
- **Forest points are easy cases.** They were picked as clearly intact forest, so the false-alarm rate is probably optimistic.
- **Small landslides are missed.** Most check-point landslides are narrower than 60 m; at 20 m pixels they barely change the signal. Only 2 large landslides exist in the check points.
- **12-day gap between passes.** Anything else that changed in those days looks the same as a landslide.
- **Provisional data.** NISAR's science team has not finished calibrating this release; residual interference and banding are possible. Coverage of the box is partial for every track.
- **Shadow and layover** are estimated from the DEM with assumed headings, not from the files' own metadata.
- **OpenStreetMap completeness.** Missing roads mean missing routes; few places carry a population.
- **"Likely" is not confirmed.** A road is "likely blocked" only because a candidate landslide lies within 10 m of the mapped line. Nobody saw a blockage. Collapsed bridges and road subsidence are invisible to this method.
- **Check points.** They come from optical change checked by eye, not from field work, and they are concentrated in the west of the box.
- **The 5% cap in the selection rule is an assumption**, not a measured value.
