# Cut Off

NISAR L-band radar finds the roads Panama's 2026 landslides likely blocked.

Live app: {url} · Video: {url} · NASA Space Apps 2026, "Dancing with the SARs"

## What it does

Clouds and forest hid Panama's landslides from normal satellites. NISAR's radar sees through both. We compared radar images from before and after the magnitude 7.7 earthquake of 9 October 2026 and looked for forest that suddenly lost its radar signal. Those candidate landslides are then joined to the open road map to show which roads were likely blocked and which communities were possibly cut off, with how sure we are and what the radar cannot see.

This is a research demo for the first days after a disaster. It is not an official warning, and nobody saw the blockages: "likely blocked" is inferred from a landslide lying next to a road.

## Results

<!-- results:start -->
Results will appear here once the real data has been processed.
<!-- results:end -->

## How it works

1. **Radar change.** NISAR's cross-polarised signal (HV) is strong over forest and weak over bare soil. We compare it before and after the quake and flag drops on steep, forested slopes.
2. **Several passes.** Candidates are confirmed across up to four before/after pairs from two look directions. Slopes the radar cannot see (shadow and layover) are marked unknown.
3. **Roads.** Landslides are joined to the OpenStreetMap road network: a road is "likely blocked" if a landslide touches it, "at risk" within 100 m.
4. **Communities.** A community is "possibly cut off" if every mapped road from it to a nearby town crosses a likely-blocked road.

The full method, with every parameter and granule ID, is in [docs/method.md](docs/method.md).

## Accuracy

We hand-marked points on Sentinel-2 photos from before and after the quake: real landslide scars and untouched forest. We split them in half at random, tuned the detection threshold on one half, and tested once on the other half, which we never looked at while tuning. We also ran the same method on two passes from before the quake, to see how much it flags when nothing happened. The numbers are in the Results section above and in the app's Evidence tab. A poor result is reported as it is.

## Limits

1. It misses landslides narrower than about 3 pixels (roughly 30–60 m).
2. Slopes facing away from the radar, or hidden behind ridges, are unknown (grey).
3. "Likely blocked" is inferred from a landslide touching the road. Nobody saw the blockage. Collapsed bridges and sinking roads are not detected.
4. The road map comes from OpenStreetMap volunteers. Missing roads mean missing routes.
5. The radar data is PROVISIONAL: NISAR's science team has not finished calibrating it.
6. Other things can lower the signal: logging, fields being cleared, very wet ground, radio interference. Using several passes cuts these down but not to zero.
7. Most roads reopened within a week. This shows the first days, not today.
8. This is a research demo built in 48 hours, not an official product or warning.

## Run it

The processing runs offline on a laptop and writes small files that the website and the API only read. Python 3.11 and Node 24 are used.

```bash
# processing pipeline (made-up demo data; real data needs downloads, see docs/method.md)
cd pipeline && pip install -r requirements.txt && pip install -e . --no-deps && python -m cutoff mock

# read-only API
cd api && pip install -r requirements-dev.txt && uvicorn main:app --reload

# website
cd web && npm ci && npm run dev
```

Tests: `pytest -q` in `pipeline/` and in `api/`, and `npm test && npm run build` in `web/`. Deployment (Cloudflare Pages for the website, Azure App Service for the API) is described in [docs/deploy.md](docs/deploy.md).

## Data and credits

Radar: NASA-ISRO NISAR L2 GCOV (PROVISIONAL), via NASA ASF DAAC. Basemap: NASA GIBS. Roads and places: © OpenStreetMap contributors (ODbL); our road-status file derived from them is also released under ODbL. Check images: contains modified Copernicus Sentinel data 2026. Elevation: Copernicus DEM GLO-30, © DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018 provided under COPERNICUS by the European Union and ESA.

Software: MapLibre GL JS (BSD-3-Clause); React, Vite, Tailwind CSS and Recharts (MIT); FastAPI, Pydantic and Uvicorn (MIT/BSD); NumPy, SciPy, scikit-image, NetworkX, rasterio, Shapely and GeoPandas (BSD); Pillow (MIT-CMU); asf_search (BSD-3-Clause) and earthaccess (MIT). Every source is listed in [docs/citations.md](docs/citations.md).

NASA does not endorse this project.

## Use of AI

We used AI tools (listed in [docs/si-log.md](docs/si-log.md)) to help with planning and technical specifications, code, documentation and text drafts. All results come from our own processing of NISAR data; no AI-generated images, video or data are presented as real.

## Licence

Apache 2.0. See [LICENSE](LICENSE).
