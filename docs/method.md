# Method

Results, parameters and granule IDs are added here as they become final.

## Question
Can NISAR L-band radar find the landslides of the 9 October 2026 Panama earthquake (magnitude 7.7) under cloud and forest, and can that be turned into a list of roads likely blocked and communities possibly cut off? This page describes exactly what was done and how well it worked. The short answer: with this simple method and 20 m pixels, only weakly.

## Data
- **Radar:** NASA-ISRO NISAR Level-2 GCOV, PROVISIONAL release, HV polarisation (the `HVHV` layer, linear power on a 10 m UTM grid), from the Alaska Satellite Facility DAAC through NASA Earthdata Search and the Harmony service, trimmed to the study box (west -81.0, south 7.3, east -80.3, north 8.0).
- **Elevation:** Copernicus DEM GLO-30 (tile N07 W081).
- **Roads and places:** OpenStreetMap, Geofabrik Panama extract of 13 November 2026: roads tagged trunk, primary, secondary, tertiary, unclassified, residential or track, and places tagged town, village or hamlet, in the box widened by 0.15 degrees.
- **Check points:** Copernicus Sentinel-2 L2A images (see Validation).

| Pair | Track | Before | After | Before granule | After granule | Pixels flagged |
|---|---|---|---|---|---|---|
| t141d | 141 descending | 2026-09-27 | 2026-10-09 | `NISAR_L2_PR_GCOV_031_141_D_085_4005_DHDH_A_20260927T235335_20260927T235344_P05023_N_P_J_001` | `NISAR_L2_PR_GCOV_032_141_D_085_4005_DHDH_A_20261009T235335_20261009T235345_P05023_N_P_J_001` | 64,291 |
| t4a | 4 ascending | 2026-09-30 | 2026-10-12 | `NISAR_L2_PR_GCOV_032_004_A_005_4005_DHDH_A_20260930T110420_20260930T110435_P05023_N_P_J_001` | `NISAR_L2_PR_GCOV_033_004_A_005_4005_DHDH_A_20261012T110420_20261012T110436_P05023_N_P_J_001` | 8,624 |
| t40d | 40 descending | 2026-10-02 | 2026-10-14 | `NISAR_L2_PR_GCOV_032_040_D_085_4005_DHDH_A_20261002T234516_20261002T234533_P05023_N_P_J_001` | `NISAR_L2_PR_GCOV_033_040_D_085_4005_DHDH_A_20261014T234516_20261014T234533_P05023_N_P_J_001` | 144,943 |
| t76a | 76 ascending | 2026-10-05 | 2026-10-17 | `NISAR_L2_PR_GCOV_032_076_A_005_4005_DHDH_A_20261005T105604_20261005T105616_P05023_N_P_J_001` | `NISAR_L2_PR_GCOV_033_076_A_005_4005_DHDH_A_20261017T105604_20261017T105616_P05023_N_P_J_001` | 50,861 |

The no-quake baseline is track 40, 20 September against 2 October 2026 (`NISAR_L2_PR_GCOV_031_040_D_085_4005_DHDH_A_20260920T234516_20260920T234532_P05023_N_P_J_001` and the track 40 "before" granule above). Granule names follow the ASF archive listing; the files were ordered by hand. The radar images cover only part of the box: about 40% for track 141, 24% for track 4, 77% for track 40 and 61-65% for track 76.

## Processing steps
1. Build one grid (20 m pixels) from the first pair's "before" image. All images are averaged as linear power onto it, then converted to dB and smoothed with a 5 x 5 median filter. Only images from the same track are ever compared.
2. Slope and aspect come from the Copernicus DEM resampled onto the same grid.
3. Slopes that face the radar steeply (layover) or face away steeply (shadow) are marked unknown for that pair, using the radar's look direction and incidence angle.
4. Change = HV after minus HV before. A pixel is a candidate landslide in a pair if the change is at or below the threshold, the slope is steep enough, the ground was bright forest in the "before" image, and the radar could see it. Patches smaller than 3 connected pixels are removed.
5. Pairs are combined by voting: a pixel is kept if enough pairs flag it, where "enough" is two when at least two pairs could see it, and one otherwise. Each kept patch becomes a polygon with its area, mean HV before and after, mean slope, how many pairs flagged it and how many could see it.
6. The same detection runs on two passes from before the quake. The share of forested slope it flags is the no-change rate, reported next to the rate after the quake.
7. For every pass, the mean HV at the detected landslides is compared with the mean HV on intact forested slopes.
8. Roads are cut into pieces of at most 500 m and each piece gets a status: "likely blocked" if a landslide lies within 10 m (it touches the road), "at risk" within 100 m, "unknown" if at least half of the piece lies where the radar could not see, otherwise "clear". Nobody saw a blockage: this is inferred from the landslide being next to the road. Collapsed bridges and sinking roads cannot be seen by this method.
9. A road graph is built from the OpenStreetMap lines (road points within 1 m are joined). A community is "possibly cut off" if it could reach a main town on the full map, but every route crosses a likely-blocked piece. It is "reachable" if a route without such a piece remains. It is "unknown" if no mapped road lies within 2 km, or its roads do not reach any main town even on the full map (a gap in the map is not reported as a blockage).
## Parameters used
| Setting | Value |
|---|---|
| Grid | 20 m pixels, UTM zone 17N (EPSG:32617), taken from the track 141 "before" image |
| Speckle filter | 5 x 5 median on dB |
| Drop threshold | **-1.5 dB** (chosen on the tuning half of the check points; the starting value was -3 dB) |
| Minimum slope | 10 degrees |
| Forest test | HV before at least -16 dB |
| Smallest patch | 3 connected pixels |
| Incidence angle for shadow/layover | 37 degrees; headings 350 (ascending) and 190 (descending) degrees, not read from the files |
| Voting | kept if flagged by at least two pairs, or by one pair when only one pair could see the pixel |
| Road status | likely blocked within 10 m of a candidate landslide, at risk within 100 m, pieces of at most 500 m |
| Community status | unknown if no mapped road within 2 km |
| Main towns | Chitré, Las Tablas, Tonosí, Macaracas, Santiago |

## Validation
The validation set is 183 check points from Sentinel-2 L2A NDVI change (8/22 Sep vs 18/28 Oct 2026): 114 landslide points (63 small, 49 medium, 2 large) and 69 forest points. An AI tool suggested candidate points from the change in vegetation greenness and every point was checked by eye. NISAR values were never used to pick them. The file `data/validation/points.csv` was committed before anything was scored.
1. The points are split 50/50 within each label (landslide, forest) with a fixed random seed (2026): a tuning half and a sealed test half.
2. The detection threshold is chosen on the tuning half only. Thresholds from -1.5 to -6.0 dB in steps of 0.5 dB are tried, and the one with the best detection rate minus false-alarm rate is kept (ties go to the value nearest -3 dB).
3. Detection is rerun with that threshold. The test half is then scored once: a landslide point counts as found if a candidate landslide polygon lies within 20 m of it, and a forest point counts as a false alarm if one does.
4. The area under the ROC curve (AUC) uses the radar change at each test point (a bigger drop means more landslide-like). Detection is also reported by landslide size.
5. The code refuses to score the test half a second time unless it is forced, and every run is logged.
The threshold is never changed after the test result has been seen. A poor result is reported as it is.
## Results
- **4,672** candidate landslides covering **10.41 km²** of forested slopes.
- **46.1 km** of road likely blocked and **7** communities possibly cut off (inferred from landslides next to roads; nobody saw the blockages).
- Accuracy on a sealed test half of check points that was never used for tuning (57 landslide points, 34 forest points): found **21%**, false alarms **3%**, AUC **0.55** (0.5 = guessing, 1.0 = perfect). Found by landslide size: small 13% (n = 30), medium 30% (n = 27).
- On two passes before the quake the same method flagged 3.4% of forested slopes, against 1.8% after the quake.
- **Caution:** the method flagged more change before the quake than after it. Natural change between two passes is as large as the landslide signal at this setting, so single detections are weak evidence.
- Settings: drop threshold -1.5 dB, minimum slope 10°, pixel size 20 m.

All results come from radar processed in advance. This is a research demo, not an official warning.

**Tuning table** (tuning half only: 57 landslide and 35 forest points; main pair):

| Threshold (dB) | Found | False alarms | Found minus false alarms |
|---|---|---|---|
| -1.5 | 8.8% | 5.7% | +0.031 |
| -2 | 1.8% | 0.0% | +0.018 |
| -2.5 | 1.8% | 0.0% | +0.018 |
| -3 | 1.8% | 0.0% | +0.018 |
| -3.5 | 0.0% | 0.0% | +0.000 |
| -4 | 0.0% | 0.0% | +0.000 |
| -4.5 | 0.0% | 0.0% | +0.000 |
| -5 | 0.0% | 0.0% | +0.000 |
| -5.5 | 0.0% | 0.0% | +0.000 |
| -6 | 0.0% | 0.0% | +0.000 |

No threshold separated landslide points from forest points on the tuning half. The chosen value is the loosest one allowed, picked by a margin of a few points, so it should be read as "no usable threshold was found", not as an optimum. Both large check points fell in the tuning half, so there is no test score for large landslides (n = 0; with only 2 in total it could not have been meaningful anyway).

Of the candidate landslides, the ones seen by two or more passes are marked high or medium confidence in the app; the rest could be seen by one pair only.

## Comparison with reports from the ground
News reports said the towns of Arenas, El Cacao and Quebro (Veraguas) were cut off after roads collapsed. In this analysis the mapped places with those names (Arenas, Los Arenas, two places called El Cacao, and La Loma de Quebro) all come out as "reachable". So the method does **not** reproduce the reported cut-offs. That is consistent with its limits: it cannot see collapsed roads or bridges, and it missed most check-point landslides. The communities it lists as "possibly cut off" are not confirmed by any report we found.

## Limitations
- **Weak accuracy.** On the sealed test half the method found about a fifth of the landslide points and its AUC is close to guessing (see Results). Every detection is a lead to verify, not a finding.
- **The no-quake check fails.** The same method flags more forested slope between two passes before the quake than after it. Natural change over 12 days (rain and soil moisture, farming, vegetation) is as large as the landslide signal at this setting, so false alarms are expected.
- **Small landslides are missed.** Most check-point landslides are narrower than 60 m; after 20 m pixels and a 5 x 5 filter they barely change the signal. Only 2 large landslides exist in the check points.
- **12-day gap between passes.** Anything else that changed in those days looks the same as a landslide.
- **Provisional data.** NISAR's science team has not finished calibrating this release; residual interference and banding are possible. Coverage of the box is partial for every track.
- **Shadow and layover** are estimated from the DEM with assumed headings, not from the files' own metadata.
- **OpenStreetMap completeness.** Missing roads mean missing routes; few places carry a population.
- **"Likely" is not confirmed.** A road is "likely blocked" only because a candidate landslide lies within 10 m of the mapped line. Nobody saw a blockage. Collapsed bridges and road subsidence are invisible to this method.
- **The time-series chart is not independent evidence.** The "at landslides" line is measured at places that were selected because their signal dropped, so it shows the size of the selected drop, not proof of landslides.
- **Check points.** They come from optical change checked by eye, not from field work, and they are concentrated in the west of the box.
