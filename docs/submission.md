# Project page text and submission checklist

Text for the NASA Space Apps project page, kept here so the page and the repository say the same thing. Numbers come from `web/public/data/panama-2026/stats.json`.

## Project name
Cut Off

## Team
Ram (team lead and repository manager), Hiren (research and accuracy), Mayank (frontend and testing), Yash (DevOps), Rudra (charts and visuals). Roles and responsibilities are in the README.

## High-level summary
Cut Off looks for candidate landslides after the magnitude 7.7 Panama earthquake of 9 October 2026 using changes in NISAR L-band radar images, joins them to the OpenStreetMap road network, and shows which roads are likely blocked and which communities are possibly cut off. It responds to the challenge "Dancing with the SARs". Optical satellites struggle under cloud and forest; radar can collect images through cloud and at night, so it can give first leads. What makes the project useful is that it also measures itself: the result is checked against hand-marked points and a pre-event baseline, and the weaknesses are shown next to the numbers.

## Final project link
https://cut-off.bhogesara-ram23.workers.dev (code: https://github.com/bhogesararam23/cut-off, read-only API: https://cutoff-api-26-ram26.azurewebsites.net/docs)

## Details
- **What it does:** a map with a before/after swipe of radar and optical images, candidate landslides, roads likely blocked, communities possibly cut off, and an accuracy section.
- **How it works:** HV radar change on a 20 m grid; each pair's own local mean change is subtracted; pixels flagged by two of up to four before/after pairs are kept; connected patches of at least 3 pixels are candidate landslides; candidates are joined to roads and communities. See `docs/method.md`.
- **Result, in plain words:** the revised method found 19 of 57 held-out landslide points (33%) and flagged 0 of 34 forest points. The held-out half was scored twice (original method first, revised method second) and both results are shown. It is a random split of points in one study area, not independent validation. The pre-event baseline flags 3.3% of forested slope against 4.8% after the quake. Candidates are leads, not confirmed landslides.
- **Benefits:** a quick, transparent first list of places to check, with every limit stated; open code, data files and API.
- **Tools:** Python (NumPy, SciPy, scikit-image, NetworkX, rasterio, Shapely, GeoPandas), FastAPI, React, TypeScript, Vite, Tailwind CSS, MapLibre GL JS, Recharts, Docker, GitHub Actions, Azure App Service, Cloudflare.

## Use of SI (AI) tools
Yes. AI tools helped with planning and technical specifications, code, documentation and text drafts, and suggested candidate check points from the change in vegetation greenness (every point was checked by eye). Results, images and video are not AI-generated. Each step is logged in `docs/si-log.md`; the README states where AI was used.

## NASA data and resources
NISAR L2 GCOV (PROVISIONAL), HV polarisation, nine granules (four before/after pairs and a pre-event baseline), from the ASF DAAC; NASA GIBS basemap tiles. Space Agency Partner data: NISAR is a joint NASA and ISRO mission. Also used: Copernicus DEM GLO-30, Sentinel-2 L2A, OpenStreetMap, Copernicus EMS EMSR934 and USGS event us6000u18k for reference.

## References
Every dataset, library, font, tool, text source and its licence is in `docs/citations.md`. The code, text and images in the repository were made by the team with the AI help described above; no copyrighted music, images or text are used.

## Checklist before pressing "Submit for Judging"
- [ ] Submission closes Sunday 15 November, 11:59 p.m. local time of your Local Event. Only the last saved submission is judged.
- [ ] Demo: a 7-slide deck or a video of 30 seconds or less, in English (a video in another language needs English subtitles), uploaded to a service such as YouTube, Google Drive or GitHub with public access and no login. Open the link in a private window to test it. Slides or video need the team name, member names and the challenge name. No images, video or audio of anyone under 18.
- [ ] Final project link works without login (open the live website in a private window; check the numbers at the top match `stats.json`).
- [ ] All required fields filled in, in English. Paste the sections above. Add the References from `docs/citations.md`.
- [ ] Every team member is registered for the same Local Event (or the Universal Event) and is on the Members tab.
- [ ] Tick the Terms and Conditions box and the "Confirm all work is original" box, then submit.
- [ ] Optional: request a FortiGuard web filter classification for the website so judges' networks do not block it.
- [ ] Keep every link live and unchanged through judging: do not force-push or delete anything after submitting.
