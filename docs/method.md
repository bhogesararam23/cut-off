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
## Parameters used
## Validation
## Results
## Comparison with reports from the ground
## Limits
