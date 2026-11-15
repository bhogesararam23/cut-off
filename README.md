# Cut Off

Candidate landslides, roads likely blocked and communities possibly cut off after the magnitude 7.7 earthquake in Panama on 9 October 2026, from NISAR L-band radar change detection, with the accuracy check and its limits.

Live app: https://cut-off.bhogesara-ram23.workers.dev · API (optional): https://cutoff-api-26-ram26.azurewebsites.net/docs · NASA Space Apps 2026, "Dancing with the SARs"

## What it does

Clouds and dense forest make landslides hard to see from optical satellites. We compared NISAR radar images from before and after the earthquake and looked for forested slopes where the radar signal dropped. Radar can collect images through cloud and at night. This analysis looks for changes in the radar signal over forested slopes. Vegetation, soil moisture, viewing geometry and other factors also change the signal, so a change is a lead, not a confirmed landslide.

The candidate landslides are joined to the OpenStreetMap road network to show which roads are likely blocked and which communities are possibly cut off. Nobody saw the blockages: "likely blocked" is inferred from a candidate landslide lying next to a road. The website shows this on a map with a before/after swipe of radar and optical (Sentinel-2) images, lists the communities by status, and puts the accuracy check next to the headline numbers. A small read-only API serves the same result files. The radar data are PROVISIONAL. This is a research demo, not an official warning.

## Results

<!-- results:start -->
- **8,442** candidate landslides (connected patches of flagged radar pixels) covering **19.13 km²** of forested slopes. A candidate is a lead, not a confirmed landslide.
- **92.2 km** of road likely blocked and **102** communities possibly cut off (of 460 mapped places: 337 reachable, 21 unknown); inferred from candidate landslides next to roads, nobody saw the blockages.
- Held-out point split, second scoring, revised method (57 landslide points, 34 forest points): found **33%**, false alarms **0%**, AUC **0.86** (0.5 = guessing, 1.0 = perfect). Found by landslide size: small 20% (n = 30), medium 48% (n = 27).
- Held-out point split, first scoring, original method (57 landslide points, 34 forest points): found **21%**, false alarms **3%**, AUC **0.55** (0.5 = guessing, 1.0 = perfect). Found by landslide size: small 13% (n = 30), medium 30% (n = 27).
- The held-out half was scored twice: first on the original method, then after the method was revised using the tuning half only. Both results are shown.
- The two AUC values use different scoring rules: the first reads one pass at the point; the revised one averages four passes, each taking the strongest drop within one pixel (20 m) of the point.
- This is a random split of points within one study area, labelled from optical imagery and checked by eye. It is not independent geographic validation and not field validation; nearby points may share conditions.
- Pre-event baseline (ordinary change between two passes before the quake, 20 Sep to 2 Oct 2026; rain, soil moisture, farming and vegetation can change over 12 days): the same method flagged 3.3% of forested slopes, against 4.8% in a pair spanning the quake from the same track.
- Settings: drop threshold -1 dB below the local mean, local-mean window 11 pixels (220 m), minimum slope 10°, forest test: HV before at least -16 dB, minimum patch 3 pixels, pixel size 20 m.

All results come from radar processed in advance. This is a research demo, not an official warning.
<!-- results:end -->

## How it works

1. **Radar change.** The cross-polarised signal (HV) is compared before and after the quake, in dB, on a 20 m grid.
2. **Local reference.** Each pair's own local mean change (a 220 m window) is subtracted, so region-wide shifts such as wetter soil are not counted.
3. **Several passes.** Pixels must be flagged by two of up to four before/after pairs where two can see them. Patches under 3 pixels are dropped; each remaining connected patch is one candidate landslide. Slopes the radar cannot see (shadow and layover) are marked unknown.
4. **Roads.** Candidates are joined to the OpenStreetMap road network: a road is "likely blocked" if a candidate touches it, "at risk" within 100 m.
5. **Communities.** A community is "possibly cut off" if every mapped road from it to a nearby town crosses a likely-blocked road.

All processing runs offline and writes small files; the website and the API only read them. The full method, with every parameter, the nine granule IDs and every setting that was tried, is in [docs/method.md](docs/method.md).

## Accuracy

183 check points were marked on Sentinel-2 images from before and after the quake: fresh landslide scars and untouched forest. An AI tool suggested candidates from the change in vegetation greenness, and every point was checked by eye; the radar was never used to pick them. The points file was committed before anything was scored. The points were split in half at random; the method settings were chosen on one half only, and the other half was held out.

This is a random split of points within one study area, labelled from optical imagery and checked by eye. It is not independent geographic validation and not field validation; nearby points may share conditions.

The held-out half was scored twice: first on the original method, then after the method was revised using the tuning half only. Both results are shown in the Results section and in `data/validation/`. The two AUC values use different scoring rules; on the primary pair alone the revised method gives 0.71 (`auc_primary_pair_only` in `data/validation/scoring_2_revised_method.json`). We also ran the same method on two passes from before the quake (the pre-event baseline: ordinary change between two passes before the quake, 20 Sep to 2 Oct 2026; rain, soil moisture, farming and vegetation can change over 12 days). A poor result is reported as it is.

## Limits

1. Most check-point landslides are small (under 100 m wide), close to the 20 m radar pixel, and many are missed.
2. The revised method found well under half of the held-out landslide points. Treat every candidate as a lead to verify.
3. Forest check points were picked as clearly intact forest, so the false-alarm rate is probably lower than it would be across all forest.
4. Candidates flagged by only one radar pass are weaker leads. The counts of candidates, likely blocked road and possibly cut off communities rise and fall with the detection threshold.
5. Slopes facing away from the radar, or hidden behind ridges, are unknown (grey).
6. "Likely blocked" is inferred from a candidate landslide touching the road. Nobody saw the blockage. Collapsed bridges and sinking roads are not detected.
7. The road map comes from OpenStreetMap volunteers. Missing roads mean missing routes.
8. The radar data are PROVISIONAL: NISAR's science team has not finished calibrating them.
9. Other things can lower the signal: logging, fields being cleared, very wet ground, radio interference. Using several passes cuts these down but not to zero.
10. This shows the first days after the quake, not later road repairs.

## Run it

The processing runs offline on a laptop and writes small files that the website and the API only read. Python 3.11 and Node 24 are used. The result files in `web/public/data/` are committed, so the website and API run without any radar download.

```bash
# processing pipeline (real data needs downloads, see docs/method.md)
cd pipeline && pip install -r requirements.txt && pip install -e . --no-deps
python -m cutoff run --clean && python -m cutoff tune && python -m cutoff validate && python -m cutoff access && python -m cutoff report

# read-only API
cd api && pip install -r requirements-dev.txt && uvicorn main:app --reload

# website
cd web && npm ci && npm run dev
```

Tests: `pytest -q` in `pipeline/` and in `api/`, and `npm test && npm run build` in `web/`. The website is built by Cloudflare from this repository; the API runs as a container on Azure App Service, deployed by GitHub Actions. Details are in [docs/deploy.md](docs/deploy.md).

## Team

Team: Ecliptic Nomads

| Member | Role | Responsibilities |
|---|---|---|
| Ram | Team lead and repository manager | Project scope and planning; NISAR radar data processing and the detection pipeline; validation and scoring; read-only API; web app structure and integration; repository management, reviews and releases; final submission |
| Hiren | Research and accuracy | Background research on the event and the method; checking the validation check points and the accuracy figures; fact-checking claims and sources; slide, video and submission form text |
| Mayank | Frontend and testing | Web app pages and map interface; testing on desktop and phone; README and documentation; video editing |
| Yash | DevOps | CI workflows; deployment of the website (Cloudflare) and the API (Azure); keeping the live site and checks green |
| Rudra | Charts and visuals | Chart components for the web app, such as detection by landslide size |

## Data and credits

NASA data (the core of the analysis):
- **NISAR L2 GCOV, PROVISIONAL release**, HV polarisation: four before/after pairs and a pre-event baseline (nine granules). NASA-ISRO NISAR mission, distributed by the NASA Alaska Satellite Facility DAAC (ASF DAAC).
- **NASA GIBS** imagery tiles (map basemap): NASA Global Imagery Browse Services.

Other data: Copernicus DEM GLO-30 (slope and radar shadow; © DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018, provided under COPERNICUS by the European Union and ESA); Sentinel-2 L2A images (check points and optical images; contains modified Copernicus Sentinel data 2026); © OpenStreetMap contributors (ODbL; our road-status file derived from them is also released under ODbL); Copernicus EMS EMSR934 and USGS event us6000u18k (event reference); news reports from Newsroom Panama and Wikipedia (cited, not copied).

Software: MapLibre GL JS (BSD-3-Clause); React, Vite, Tailwind CSS and Recharts (MIT); FastAPI, Pydantic and Uvicorn (MIT/BSD); NumPy, SciPy, scikit-image, NetworkX, rasterio, Shapely and GeoPandas (BSD); Pillow (MIT-CMU); asf_search (BSD-3-Clause) and earthaccess (MIT); Inter and IBM Plex Mono fonts (SIL Open Font License 1.1).

Every source, licence and date added is in [docs/citations.md](docs/citations.md). Not affiliated with or endorsed by NASA or ISRO.

## Use of AI

We used AI tools (listed in [docs/si-log.md](docs/si-log.md)) to help with planning and technical specifications, code, documentation, text drafts and suggesting candidate check points. The pipeline, API and website code were written with an AI coding assistant and reviewed and tested by the team; every suggested check point was checked by eye. All results come from our own processing of NISAR data; no AI-generated images, video or data are presented as real. Sources and AI use are documented in the linked logs.

## Licence

The project code is licensed under Apache 2.0 (see [LICENSE](LICENSE)). Datasets and third-party material keep their own terms (OpenStreetMap is ODbL; Copernicus data has its own terms).
