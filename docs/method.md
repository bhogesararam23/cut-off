# Method

Results, parameters and granule IDs are added here as they become final.

## Question
## Data
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
## Validation
The accuracy check uses points marked by hand on Sentinel-2 photos from before and after the quake: landslide scars and untouched forest. The points file is committed to the repository before anything is scored.
1. The points are split 50/50 within each label (landslide, forest) with a fixed random seed (2026): a tuning half and a sealed test half.
2. The detection threshold is chosen on the tuning half only. Thresholds from -1.5 to -6.0 dB in steps of 0.5 dB are tried, and the one with the best detection rate minus false-alarm rate is kept (ties go to the value nearest -3 dB).
3. Detection is rerun with that threshold. The test half is then scored once: a landslide point counts as found if a candidate landslide polygon lies within 20 m of it, and a forest point counts as a false alarm if one does.
4. The area under the ROC curve (AUC) uses the radar change at each test point (a bigger drop means more landslide-like). Detection is also reported by landslide size.
5. The code refuses to score the test half a second time unless it is forced, and every run is logged.
The threshold is never changed after the test result has been seen. A poor result is reported as it is.
## Results
## Comparison with reports from the ground
## Limits
