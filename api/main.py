"""Read-only API that serves the pipeline's output files (see models.py for the exact shapes).

No database, no accounts, no writes. Only GET requests are answered. Everything read from disk goes through
store.DataStore, which only allows names from an allowlist and paths that stay inside the data folder.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Literal, TypeVar

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import TypeAdapter, ValidationError

import models as m
from store import FEATURE_ID_RE, DataStore

VERSION = "0.1.0"
CACHE_CONTROL = "public, max-age=300"
DEFAULT_CORS_ORIGINS = ["http://localhost:5173"]
CONFIDENCE_RANK = {"low": 1, "medium": 2, "high": 3}
MEDIA_TYPES = {".png": "image/png", ".json": "application/json", ".geojson": "application/geo+json"}
MAX_AREA_M2 = 1e9

log = logging.getLogger("cutoff.api")
T = TypeVar("T")


def parse_origins(raw: str | None) -> list[str]:
    """Allowed browser origins from a comma separated list. A wildcard or a malformed entry is a setup error."""
    if raw is None or not raw.strip():
        return list(DEFAULT_CORS_ORIGINS)
    origins = [o.strip().rstrip("/") for o in raw.split(",") if o.strip()]
    for o in origins:
        if o == "*" or not (o.startswith("https://") or o.startswith("http://")) or "*" in o:
            raise ValueError(f"CORS_ORIGINS must list full origins like https://example.com, not {o!r}")
    return origins


def parse_choices(raw: str | None, allowed: tuple[str, ...]) -> set[str] | None:
    """A comma separated query value such as 'blocked,at_risk'. Anything outside the allowed values is a 422."""
    if raw is None:
        return None
    parts = [p.strip() for p in raw.split(",")]
    if not parts or any(p not in allowed for p in parts):
        raise HTTPException(status_code=422, detail="invalid query value")
    return set(parts)


def create_app(data_dir: str | Path | None = None, cors_origins: list[str] | None = None,
               public_url: str | None = None) -> FastAPI:
    base = Path(data_dir) if data_dir else Path(os.environ.get("DATA_DIR") or Path(__file__).resolve().parent.parent / "web" / "public" / "data")
    origins = cors_origins if cors_origins is not None else parse_origins(os.environ.get("CORS_ORIGINS"))
    public = (public_url if public_url is not None else os.environ.get("PUBLIC_URL") or "").rstrip("/")
    store = DataStore(base)

    app = FastAPI(title="Cut Off API", version=VERSION, redoc_url=None, description="Read-only access to the Cut Off output files.")

    # ---- errors: short generic messages to the client, details only in the server log ----
    @app.exception_handler(RequestValidationError)
    async def bad_request(_: Request, __: RequestValidationError):
        return JSONResponse({"detail": "invalid query value"}, status_code=422)

    @app.exception_handler(Exception)
    async def unexpected(request: Request, exc: Exception):
        log.error("unhandled error on %s: %s", request.url.path, type(exc).__name__)
        return JSONResponse({"detail": "internal error"}, status_code=500)

    # ---- headers on every response ----
    @app.middleware("http")
    async def common_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cross-Origin-Resource-Policy"] = "cross-origin"
        response.headers["Cache-Control"] = CACHE_CONTROL if response.status_code == 200 and request.method == "GET" else "no-store"
        return response

    # added last, so it is the outermost layer: error responses carry the CORS headers too
    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["GET"], allow_headers=[],
                       allow_credentials=False, max_age=600)

    # ---- helpers ----
    def read(event_id: str, name: str, model: Any) -> Any:
        """Load a file and check it against its model. Unknown event -> 404; damaged file -> generic 500."""
        if store.event_dir(event_id) is None:
            raise HTTPException(status_code=404, detail="event not found")
        try:
            raw = store.load_json(event_id, name)
        except (ValueError, OSError) as e:
            log.error("cannot read %s/%s: %s", event_id, name, type(e).__name__)
            raise HTTPException(status_code=500, detail="internal error") from None
        if raw is None:
            raise HTTPException(status_code=404, detail="data not found")
        try:
            return TypeAdapter(model).validate_python(raw)
        except ValidationError:
            log.error("%s/%s does not match the expected format", event_id, name)
            raise HTTPException(status_code=500, detail="internal error") from None

    def collection(c: Any, features: list[Any]) -> Any:
        return type(c)(type="FeatureCollection", features=features)

    # ---- endpoints ----
    @app.get("/api/health", response_model=m.Health)
    def health():
        return m.Health(status="ok", version=VERSION)

    @app.get("/api/events", response_model=list[m.EventSummary])
    def events():
        out = []
        for event_id in store.event_ids():
            try:
                e = TypeAdapter(m.EventInfo).validate_python(store.load_json(event_id, "event.json"))
            except (ValidationError, ValueError, OSError):
                log.error("skipping %s: event.json is not usable", event_id)
                continue
            out.append(m.EventSummary(event_id=e.event_id, name=e.name, time_utc=e.time_utc, bbox=e.bbox, mock=e.mock))
        return out

    @app.get("/api/events/{event_id}", response_model=m.EventInfo, responses={404: {"model": m.ErrorBody}})
    def event(event_id: str):
        return read(event_id, "event.json", m.EventInfo)

    @app.get("/api/events/{event_id}/pairs", response_model=list[m.Pair], responses={404: {"model": m.ErrorBody}})
    def pairs(event_id: str, request: Request):
        items: list[m.Pair] = read(event_id, "pairs.json", list[m.Pair])
        root = public or str(request.base_url).rstrip("/")
        return [p.model_copy(update={k: f"{root}/static/{event_id}/{getattr(p, k)}" for k in ("before_png", "after_png", "change_png")})
                for p in items]

    @app.get("/api/events/{event_id}/landslides", response_model=m.Landslides, responses={404: {"model": m.ErrorBody}})
    def landslides(event_id: str, min_confidence: Literal["low", "medium", "high"] | None = None,
                   min_area_m2: float | None = Query(default=None, ge=0, le=MAX_AREA_M2)):
        fc: m.Landslides = read(event_id, "landslides.geojson", m.Landslides)
        keep = fc.features
        if min_confidence is not None:
            keep = [f for f in keep if CONFIDENCE_RANK[f.properties.confidence] >= CONFIDENCE_RANK[min_confidence]]
        if min_area_m2 is not None:
            keep = [f for f in keep if f.properties.area_m2 >= min_area_m2]
        return collection(fc, keep)

    @app.get("/api/events/{event_id}/landslides/{landslide_id}", response_model=m.Landslide,
             responses={404: {"model": m.ErrorBody}})
    def landslide(event_id: str, landslide_id: str):
        fc: m.Landslides = read(event_id, "landslides.geojson", m.Landslides)
        if FEATURE_ID_RE.fullmatch(landslide_id):
            for f in fc.features:
                if f.properties.id == landslide_id:
                    return f
        raise HTTPException(status_code=404, detail="feature not found")

    @app.get("/api/events/{event_id}/unknown", response_model=m.UnknownAreas, responses={404: {"model": m.ErrorBody}})
    def unknown(event_id: str):
        return read(event_id, "unknown.geojson", m.UnknownAreas)

    @app.get("/api/events/{event_id}/roads", response_model=m.Roads, responses={404: {"model": m.ErrorBody}})
    def roads(event_id: str, status: str | None = Query(default=None, max_length=64, description="comma separated: blocked,at_risk,clear,unknown")):
        fc: m.Roads = read(event_id, "roads.geojson", m.Roads)
        wanted = parse_choices(status, ("blocked", "at_risk", "clear", "unknown"))
        return fc if wanted is None else collection(fc, [f for f in fc.features if f.properties.status in wanted])

    @app.get("/api/events/{event_id}/communities", response_model=m.Communities, responses={404: {"model": m.ErrorBody}})
    def communities(event_id: str, status: str | None = Query(default=None, max_length=64, description="comma separated: cut_off,reachable,unknown")):
        fc: m.Communities = read(event_id, "communities.geojson", m.Communities)
        wanted = parse_choices(status, ("cut_off", "reachable", "unknown"))
        return fc if wanted is None else collection(fc, [f for f in fc.features if f.properties.status in wanted])

    @app.get("/api/events/{event_id}/communities/{osm_id}/route", response_model=m.RouteInfo,
             responses={404: {"model": m.ErrorBody}})
    def community_route(event_id: str, osm_id: str):
        fc: m.Communities = read(event_id, "communities.geojson", m.Communities)
        if FEATURE_ID_RE.fullmatch(osm_id):
            for f in fc.features:
                if f.properties.osm_id == osm_id:
                    return m.RouteInfo(status=f.properties.status, reason=f.properties.reason, nearest_hub=f.properties.nearest_hub)
        raise HTTPException(status_code=404, detail="feature not found")

    @app.get("/api/events/{event_id}/stats", response_model=m.Stats, responses={404: {"model": m.ErrorBody}})
    def stats(event_id: str):
        return read(event_id, "stats.json", m.Stats)

    @app.get("/api/events/{event_id}/timeseries", response_model=list[m.TimeseriesPoint], responses={404: {"model": m.ErrorBody}})
    def timeseries(event_id: str):
        return read(event_id, "timeseries.json", list[m.TimeseriesPoint])

    @app.get("/api/events/{event_id}/timeline", response_model=list[m.TimelineItem], responses={404: {"model": m.ErrorBody}})
    def timeline(event_id: str):
        return read(event_id, "timeline.json", list[m.TimelineItem])

    @app.get("/static/{event_id}/{file_name}", responses={200: {"content": {"image/png": {}}}, 404: {"model": m.ErrorBody}})
    def static_file(event_id: str, file_name: str):
        path = store.file(event_id, file_name)
        if path is None:
            raise HTTPException(status_code=404, detail="feature not found" if store.event_dir(event_id) else "event not found")
        return FileResponse(path, media_type=MEDIA_TYPES[path.suffix])

    return app


app = create_app()
