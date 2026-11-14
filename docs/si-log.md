# AI (SI) use log

Which AI tools helped with this project, what they did, and how the output was checked.
Append-only. No AI-generated images or video are used.

| Date-time (IST) | Tool | What it helped with | Output | Checked by / how |
|---|---|---|---|---|
| 2026-11-14 | AI chat assistant | Planning and technical specification | Project plan, data format, task list (not part of the code) | Team read-through (to be confirmed by the team) |
| 2026-11-14 | AI coding assistant | Repository scaffold: licence, ignore rules, folder layout | Config and empty module files | Tests and build run |
| 2026-11-14 | AI coding assistant | Output-file types and a format checker | `web/src/lib/types.ts`, `pipeline/cutoff/contract.py`, tests | Checker tests and web test pass |
| 2026-11-14 | AI coding assistant | Mock data generator (made-up data, flagged `mock: true`) | `pipeline/cutoff/mock.py`, files in `web/public/data/panama-2026/` | Format checker, determinism test, viewed in the browser |
| 2026-11-14 | AI coding assistant | Minimal API health check, web page with mock banner, CI workflow | `api/main.py`, `web/src/App.tsx`, `.github/workflows/ci.yml` | API tests, web build, banner checked in the browser |
| 2026-11-14 | AI coding assistant | Radar image tools (dB, speckle filters, grid alignment) and terrain tools (slope, aspect, shadow/layover); pinned two older library builds that load on this machine | `pipeline/cutoff/radar.py`, `terrain.py`, tests | Synthetic-data unit tests pass |
| 2026-11-14 | AI coding assistant | Landslide detection: HV-drop candidates, threshold guess, small-patch removal, voting across pairs, polygons with statistics | `pipeline/cutoff/detect.py`, tests | Synthetic-data unit tests pass |
| 2026-11-14 | AI coding assistant | Output writers: HV and change PNG overlays in lon/lat, simplified GeoJSON, JSON helpers; shared with the mock generator | `pipeline/cutoff/export.py`, `mock.py`, tests | Unit tests pass; mock files unchanged byte for byte |
| 2026-11-14 | AI coding assistant | Processing run (all pairs, baseline, time series, every output file), granule listing, command line | `pipeline/cutoff/run.py`, `fetch.py`, `__main__.py`, tests | End-to-end test on a synthetic scene; listing checked against the live archive |
| 2026-11-14 | AI coding assistant | Web app shell: all app text, data loading with per-file errors, top bar, pair selector, About window, credits, side panel and phone bottom sheet with seven tabs, Overview, Why radar, Limits and Timeline tabs, security headers file | `web/src/**`, `web/public/_headers`, tests | Type check, build, unit tests; layout checked in the browser at laptop and phone widths |
| 2026-11-14 | AI coding assistant | Map: NASA GIBS basemap, radar image, landslide, road, community and shadow layers, epicentre marker, legend and layer toggles; MapLibre worker setup | `web/src/components/map/**`, `web/src/lib/map*.ts` | Type check, build, viewed in the browser at laptop and phone widths, layer toggle tried |
| 2026-11-14 | AI coding assistant | Before/after swipe: two synced maps, draggable divider with mouse, touch and keyboard control, date labels | `web/src/components/map/SwipeCompare.tsx` | Build; drag, keyboard, touch-style pointer events and zoom sync tried in the browser |
| 2026-11-14 | AI coding assistant | Landslides, Access and Evidence tabs: filter and sort, grouped communities, road kilometres by status, accuracy text; list/summing helpers | `web/src/components/panel/**`, `web/src/lib/lists.ts`, tests | Unit tests for filter, sort and distance sums; tabs checked in the browser against the mock files |

Summary for the submission form (update at the end):
- Tools: AI chat assistant, AI coding assistant.
- Used for: planning and specifications, code generation and review, documentation, text drafts.
- Not used for: data, results, images or video presented as real.
