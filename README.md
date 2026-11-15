# Cut Off

Candidate landslides, roads likely blocked and communities possibly cut off after the magnitude 7.7 earthquake in Panama on 9 October 2026, from NISAR L-band radar change detection, with the accuracy check and its limits.

Live app: {url} · NASA Space Apps 2026, "Dancing with the SARs"

The website reads the result files it ships with (`web/public/data/`). A small read-only API (`api/`) can serve the same files; the site does not need it.

## What it does

We compared NISAR radar images from before and after the earthquake and looked for forested slopes where the radar signal dropped. Radar can collect images through cloud and at night. This analysis looks for changes in the radar signal over forested slopes. Vegetation, soil moisture, viewing geometry and other factors also change the signal, so a change is a lead, not a confirmed landslide.

Those candidate landslides are joined to the OpenStreetMap road network to show which roads are likely blocked and which communities are possibly cut off. Nobody saw the blockages: "likely blocked" is inferred from a candidate landslide lying next to a road. The radar data are PROVISIONAL. This is a research demo, not an official warning.

## Results

<!-- results:start -->
- **8,442** candidate landslides (connected patches of flagged radar pixels) covering **19.13 km²** of forested slopes. A candidate is a lead, not a confirmed landslide.
- **92.2 km** of road likely blocked and **102** communities possibly cut off (inferred from candidate landslides next to roads; nobody saw the blockages).
- Held-out point split, second scoring, revised method (57 landslide points, 34 forest points): found **33%**, false alarms **0%**, AUC **0.86** (0.5 = guessing, 1.0 = perfect). Found by landslide size: small 20% (n = 30), medium 48% (n = 27).
- Held-out point split, first scoring, original method (57 landslide points, 34 forest points): found **21%**, false alarms **3%**, AUC **0.55** (0.5 = guessing, 1.0 = perfect). Found by landslide size: small 13% (n = 30), medium 30% (n = 27).
- The held-out half was scored twice: first on the original method, then after the method was revised using the tuning half only. Both results are shown.
- This is a random split of points within one study area, labelled from optical imagery and checked by eye. It is not independent geographic validation and not field validation; nearby points may share conditions.
- Pre-event baseline (ordinary change between two passes before the quake, 20 Sep to 2 Oct 2026; rain, soil moisture, farming and vegetation can change over 12 days): the same method flagged 3.3% of forested slopes, against 4.8% in a pair spanning the quake from the same track.
- Settings: drop threshold -1 dB below the local mean, local-mean window 11 pixels (220 m), minimum slope 10°, minimum patch 3 pixels, pixel size 20 m.

All results come from radar processed in advance. This is a research demo, not an official warning.
<!-- results:end -->

## How it works

1. **Radar change.** The cross-polarised signal (HV) is compared before and after the quake, in dB, on a 20 m grid.
2. **Local reference.** Each pair's own local mean change (a 220 m window) is subtracted, so region-wide shifts such as wetter soil are not counted.
3. **Several passes.** Pixels must be flagged by two of up to four before/after pairs where two can see them. Patches under 3 pixels are dropped; each remaining connected patch is one candidate landslide. Slopes the radar cannot see (shadow and layover) are marked unknown.
4. **Roads.** Candidates are joined to the OpenStreetMap road network: a road is "likely blocked" if a candidate touches it, "at risk" within 100 m.
5. **Communities.** A community is "possibly cut off" if every mapped road from it to a nearby town crosses a likely-blocked road.

The full method, with every parameter, granule ID and the settings that were tried, is in [docs/method.md](docs/method.md).

## Accuracy

183 check points were marked on Sentinel-2 images from before and after the quake: fresh landslide scars and untouched forest. An AI tool suggested candidates from the change in vegetation greenness, and every point was checked by eye; the radar was never used to pick them. The points file was committed before anything was scored. The points were split in half at random; the method settings were chosen on one half only, and the other half was held out.

This is a random split of points within one study area, labelled from optical imagery and checked by eye. It is not independent geographic validation and not field validation; nearby points may share conditions.

The held-out half was scored twice: first on the original method, then after the method was revised using the tuning half only. Both results are shown in the Results section. We also ran the same method on two passes from before the quake (the pre-event baseline: ordinary change over 12 days from rain, soil moisture, farming and vegetation). A poor result is reported as it is.

## Limits

1. Most check-point landslides are small (under 100 m wide), close to the 20 m radar pixel, and many are missed.
2. The revised method found well under half of the held-out landslide points. Treat every candidate as a lead to verify.
3. Forest check points were picked as clearly intact forest, so the false-alarm rate is probably lower than it would be across all forest.
4. Candidates flagged by only one radar pass are weaker leads. The counts of candidates, blocked road and cut-off communities rise and fall with the detection threshold.
5. Slopes facing away from the radar, or hidden behind ridges, are unknown (grey).
6. "Likely blocked" is inferred from a candidate landslide touching the road. Nobody saw the blockage. Collapsed bridges and sinking roads are not detected.
7. The road map comes from OpenStreetMap volunteers. Missing roads mean missing routes.
8. The radar data are PROVISIONAL: NISAR's science team has not finished calibrating them.
9. Other things can lower the signal: logging, fields being cleared, very wet ground, radio interference. Using several passes cuts these down but not to zero.
10. This shows the first days after the quake, not later road repairs.

## Run it

The processing runs offline on a laptop and writes small files that the website and the API only read. Python 3.11 and Node 24 are used.

```bash
# processing pipeline (real data needs downloads, see docs/method.md)
cd pipeline && pip install -r requirements.txt && pip install -e . --no-deps
python -m cutoff run --clean && python -m cutoff tune && python -m cutoff validate && python -m cutoff access && python -m cutoff report

# read-only API
cd api && pip install -r requirements-dev.txt && uvicorn main:app --reload

# website
cd web && npm ci && npm run dev
```

Tests: `pytest -q` in `pipeline/` and in `api/`, and `npm test && npm run build` in `web/`. Deployment (Cloudflare Pages for the website, an Azure container for the API) is described in [docs/deploy.md](docs/deploy.md).

## Data and credits

Radar: NASA-ISRO NISAR L2 GCOV (PROVISIONAL), distributed by the Alaska Satellite Facility DAAC (ASF DAAC). Basemap: NASA GIBS. Roads and places: © OpenStreetMap contributors (ODbL); our road-status file derived from them is also released under ODbL. Check images: contains modified Copernicus Sentinel data 2026. Elevation: Copernicus DEM GLO-30, © DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018 provided under COPERNICUS by the European Union and ESA. Event reference: Copernicus EMS EMSR934. Earthquake: USGS event us6000u18k.

Software: MapLibre GL JS (BSD-3-Clause); React, Vite, Tailwind CSS and Recharts (MIT); FastAPI, Pydantic and Uvicorn (MIT/BSD); NumPy, SciPy, scikit-image, NetworkX, rasterio, Shapely and GeoPandas (BSD); Pillow (MIT-CMU); asf_search (BSD-3-Clause) and earthaccess (MIT). Every source is listed in [docs/citations.md](docs/citations.md).

Not affiliated with or endorsed by NASA or ISRO.

## Use of AI

We used AI tools (listed in [docs/si-log.md](docs/si-log.md)) to help with planning and technical specifications, code, documentation, text drafts and suggesting candidate check points. All results come from our own processing of NISAR data; no AI-generated images, video or data are presented as real. Sources and AI use are documented in the linked logs.

## Licence

The project code is licensed under Apache 2.0 (see [LICENSE](LICENSE)). Datasets and third-party material keep their own terms (OpenStreetMap is ODbL; Copernicus data has its own terms).
