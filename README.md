# Cut Off

Candidate landslides, roads likely blocked and communities possibly cut off after the magnitude 7.7 earthquake in Panama on 9 October 2026, found by NISAR L-band radar change detection, with an honest accuracy check and its limits.

Live app: https://cut-off.bhogesara-ram23.workers.dev · API: https://cutoff-api-26-ram26.azurewebsites.net/docs · NASA Space Apps 2026, "Dancing with the SARs"

| | |
|---|---|
| **Live app** | https://cut-off.bhogesara-ram23.workers.dev |
| **Read-only API** (interactive docs) | https://cutoff-api-26-ram26.azurewebsites.net/docs |
| **Source code** | https://github.com/bhogesararam23/cut-off |
| **Method, parameters and every setting tried** | [docs/method.md](docs/method.md) |
| **Sources and licences** | [docs/citations.md](docs/citations.md) |
| **Use of AI tools** | [docs/si-log.md](docs/si-log.md) |

**Contents:** [Summary](#summary) · [Results](#results) · [How it works](#how-it-works) · [Accuracy](#accuracy) · [Limits](#limits) · [NASA data and other resources](#nasa-data-and-other-resources) · [Technology](#technology) · [Use of AI](#use-of-ai) · [Repository layout](#repository-layout) · [Run it](#run-it) · [Deployment](#deployment) · [Licence](#licence)

## Summary

**The challenge.** After a large earthquake, landslides can block roads and cut off communities, but clouds and dense forest make them hard to see from optical satellites. This project responds to the NASA Space Apps Challenge 2026 challenge "Dancing with the SARs".

**What we built.** We compared NISAR L-band radar images from before and after the earthquake and looked for forested slopes where the radar signal dropped. Radar can collect images through cloud and at night. This analysis looks for changes in the radar signal over forested slopes. Vegetation, soil moisture, viewing geometry and other factors also change the signal, so a change is a lead, not a confirmed landslide.

The candidate landslides are joined to the OpenStreetMap road network to show which roads are likely blocked and which communities are possibly cut off. Nobody saw the blockages: "likely blocked" is inferred from a candidate landslide lying next to a road. The radar data are PROVISIONAL. This is a research demo, not an official warning.

**Why it matters.** Knowing which roads and communities to check first is useful in the first days after an earthquake. What is just as important is knowing how much to trust a radar-derived map. We therefore measured the method against hand-marked points, tested it on a pre-event baseline, and report the weak results next to the numbers on the website, in this README and in the method document.

**What it does.**
- Shows candidate landslides, roads likely blocked and communities possibly cut off on a map, with a before/after swipe of radar and optical (Sentinel-2) images.
- Lists the communities by status, with search, and shows a popup with the reason for each status.
- Shows the accuracy check (both scorings of the held-out points, the pre-event baseline and detection by landslide size) next to the headline numbers.
- Serves the same result files through a small read-only API.
- Works on a phone (checked at 390 px) and prints as a briefing.

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

All processing runs offline and writes small files; the website and the API only read them. The full method, with every parameter, granule ID and the settings that were tried, is in [docs/method.md](docs/method.md).

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

## NASA data and other resources

NASA data used (the core of the analysis):

| Resource | Provider | Used for |
|---|---|---|
| NISAR L2 GCOV, PROVISIONAL release, HV polarisation (four before/after pairs and a pre-event baseline, nine granules) | NASA-ISRO NISAR mission, distributed by the Alaska Satellite Facility DAAC (ASF DAAC) | The radar change detection |
| NASA GIBS imagery tiles (Blue Marble) | NASA Global Imagery Browse Services | The map basemap |

Other data and resources:

| Resource | Provider and licence | Used for |
|---|---|---|
| Copernicus DEM GLO-30 | Copernicus / ESA (free with attribution) | Slope, aspect, radar shadow and layover |
| Sentinel-2 L2A images (8 and 22 Sep, 18 and 28 Oct 2026) | Copernicus / ESA (free and open) | Marking the 183 check points; the optical before/after images |
| OpenStreetMap, Panama extract of 13 Nov 2026 | © OpenStreetMap contributors (ODbL) | Roads, places and the road graph |
| Copernicus EMS EMSR934; USGS event us6000u18k | Copernicus EMS; U.S. Geological Survey | Event reference; earthquake time, size and place |
| News reports on cut-off towns and reopened roads | Newsroom Panama, Wikipedia (cited, not copied) | Comparison with reports from the ground |

Every source, licence and the date it was added is in [docs/citations.md](docs/citations.md). Credits: Radar data are NASA-ISRO NISAR L2 GCOV (PROVISIONAL), distributed by the Alaska Satellite Facility DAAC. Basemap: NASA GIBS. Roads and places: © OpenStreetMap contributors (ODbL); our road-status file derived from them is also released under ODbL. Check images: contains modified Copernicus Sentinel data 2026. Elevation: Copernicus DEM GLO-30, © DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018 provided under COPERNICUS by the European Union and ESA.

## Technology

- **Processing pipeline (Python 3.11):** NumPy, SciPy, scikit-image, NetworkX, rasterio, Shapely, GeoPandas, pyproj and Pillow (BSD or MIT-style licences); asf_search and earthaccess for data access.
- **API (FastAPI):** read-only, GET only, CORS allowlist, safe file paths, generic error messages. Packaged as a non-root Docker image and run on Azure App Service.
- **Website (React, TypeScript, Vite, Tailwind CSS):** MapLibre GL JS for the map and Recharts for one chart (both loaded only when near the screen), self-hosted Inter and IBM Plex Mono fonts. No analytics, trackers or third-party embeds; a strict content security policy. Hosted on Cloudflare.
- **Quality checks:** 149 pipeline tests, 440 API tests and 38 web tests run in GitHub Actions on every push; a Lighthouse mobile run of the built site scored 100 for performance, accessibility, best practices and SEO.

Libraries and their licences are listed in [docs/citations.md](docs/citations.md).

## Use of AI

We used AI tools (listed in [docs/si-log.md](docs/si-log.md)) to help with planning and technical specifications, code, documentation, text drafts and suggesting candidate check points. Where it was used:

- **Code and data:** the pipeline, API and website code were written with an AI coding assistant and reviewed and tested by the team; each step is logged in [docs/si-log.md](docs/si-log.md). The check points were suggested by an AI tool from the change in vegetation greenness and every point was checked by eye.
- **Text:** README, method and website wording were drafted with AI help and checked against the data files.
- **Not used for:** results, images or video presented as real. All results come from our own processing of NISAR data; no AI-generated images, video or data are presented as real, and nothing here uses NASA or ISRO branding.

Sources and AI use are documented in the linked logs.

## Repository layout

| Folder | Contents |
|---|---|
| `pipeline/` | Offline radar processing, tuning, validation, road and community access, report writer (`python -m cutoff ...`) and its tests |
| `api/` | Read-only FastAPI service, its tests and `Dockerfile` |
| `web/` | The website (React + Vite), its tests, and the result files it ships with in `web/public/data/` |
| `data/validation/` | The hand-marked check points and both scorings of the held-out half |
| `docs/` | Method, deployment guide, sources and licences, AI-use log |
| `.github/` | CI, deploy workflow and dependency updates |

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

Tests: `pytest -q` in `pipeline/` and in `api/`, and `npm test && npm run build` in `web/`. The result files in `web/public/data/` are committed, so the website and API run without any radar download.

## Deployment

The API runs as a container on Azure App Service (image built from `api/Dockerfile`, tagged with the commit hash, deployed by `.github/workflows/deploy.yml` with passwordless GitHub-to-Azure login). The website is hosted on Cloudflare. Steps, settings and the secret and variable names (never values) are in [docs/deploy.md](docs/deploy.md). The website works on its own from the files it ships with; if the API is down, nothing on the page breaks.

## Data and credits

Software: MapLibre GL JS (BSD-3-Clause); React, Vite, Tailwind CSS and Recharts (MIT); FastAPI, Pydantic and Uvicorn (MIT/BSD); NumPy, SciPy, scikit-image, NetworkX, rasterio, Shapely and GeoPandas (BSD); Pillow (MIT-CMU); asf_search (BSD-3-Clause) and earthaccess (MIT); Inter and IBM Plex Mono fonts (SIL Open Font License 1.1).

Built for the NASA International Space Apps Challenge 2026. Not affiliated with or endorsed by NASA or ISRO.

## Licence

The project code is licensed under Apache 2.0 (see [LICENSE](LICENSE)). Datasets and third-party material keep their own terms (OpenStreetMap is ODbL; Copernicus data has its own terms).

Security issues: see [SECURITY.md](SECURITY.md).
