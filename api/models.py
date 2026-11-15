"""Response models. They mirror the output files exactly: same keys and types, no extra keys.

Files are checked against these models before they are served, so a damaged file can never reach a client.
"""

from __future__ import annotations

from typing import Annotated, Any, Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field

LonLat = tuple[float, float]
PairId = Literal["t141d", "t4a", "t40d", "t76a"]
Direction = Literal["ascending", "descending"]
Confidence = Literal["high", "medium", "low"]
RoadStatus = Literal["blocked", "at_risk", "clear", "unknown"]
CommunityStatus = Literal["cut_off", "reachable", "unknown"]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


# event.json
class Reference(Strict):
    label: str
    url: str


class Optical(Strict):
    before_webp: str
    after_webp: str
    bounds: tuple[LonLat, LonLat, LonLat, LonLat]
    before_caption: str
    after_caption: str
    attribution: str


class EventInfo(Strict):
    event_id: str
    name: str
    time_utc: str
    epicentre: LonLat
    bbox: tuple[float, float, float, float]
    maturity: str
    mock: bool
    optical: Optical | None
    references: list[Reference]


class EventSummary(Strict):
    event_id: str
    name: str
    time_utc: str
    bbox: tuple[float, float, float, float]
    mock: bool


# pairs.json
class Pair(Strict):
    id: PairId
    track: int
    direction: Direction
    before: str
    after: str
    before_png: str
    after_png: str
    change_png: str
    bounds: tuple[LonLat, LonLat, LonLat, LonLat]
    granules: list[str]
    flagged_pixels: int


# GeoJSON
class PolygonGeometry(Strict):
    type: Literal["Polygon"]
    coordinates: list[list[list[float]]]


class MultiPolygonGeometry(Strict):
    type: Literal["MultiPolygon"]
    coordinates: list[list[list[list[float]]]]


class LineStringGeometry(Strict):
    type: Literal["LineString"]
    coordinates: list[list[float]]


class MultiLineStringGeometry(Strict):
    type: Literal["MultiLineString"]
    coordinates: list[list[list[float]]]


class PointGeometry(Strict):
    type: Literal["Point"]
    coordinates: LonLat


AreaGeometry = Annotated[PolygonGeometry | MultiPolygonGeometry, Field(discriminator="type")]
LineGeometry = Annotated[LineStringGeometry | MultiLineStringGeometry, Field(discriminator="type")]

G = TypeVar("G")
P = TypeVar("P")


class Feature(Strict, Generic[G, P]):
    type: Literal["Feature"]
    geometry: G
    properties: P


class FeatureCollection(Strict, Generic[G, P]):
    type: Literal["FeatureCollection"]
    features: list[Feature[G, P]]


class LandslideProps(Strict):
    id: str
    area_m2: float
    hv_before_db: float
    hv_after_db: float
    dhv_db: float
    slope_deg: float
    pairs_seen: int = Field(ge=0, le=4)
    pairs_visible: int = Field(ge=0, le=4)
    confidence: Confidence


class RoadProps(Strict):
    osm_id: str | None
    name: str | None
    highway: str | None
    status: RoadStatus
    min_distance_m: float | None
    landslide_ids: str


class CommunityProps(Strict):
    osm_id: str | None
    name: str
    place: str
    population: int | None
    status: CommunityStatus
    nearest_hub: str | None
    reason: str


Landslides = FeatureCollection[AreaGeometry, LandslideProps]
Landslide = Feature[AreaGeometry, LandslideProps]
UnknownAreas = FeatureCollection[AreaGeometry, dict[str, Any]]
Roads = FeatureCollection[LineGeometry, RoadProps]
Communities = FeatureCollection[PointGeometry, CommunityProps]


# stats.json
class SizeDetection(Strict):
    size: Literal["small", "medium", "large"]
    n: int
    detection_rate: float


class Validation(Strict):
    split: Literal["test"]
    n_test_landslide: int
    n_test_forest: int
    detection_rate: float
    false_alarm_rate: float
    auc: float
    threshold_db: float
    by_size: list[SizeDetection]


class StatsParams(Strict):
    threshold_db: float
    min_slope_deg: float
    min_forest_hv_db: float
    min_pixels: int


class Stats(Strict):
    mock: bool
    landslides: int
    area_km2: float
    roads_blocked_km: float | None
    communities_cut_off: int | None
    validation: Validation | None
    baseline_no_change_flag_rate: float
    post_event_flag_rate: float
    params: StatsParams
    pixel_m: float


# timeseries.json, timeline.json
class TimeseriesPoint(Strict):
    date: str
    track: int
    direction: Direction
    hv_landslide_db: float
    hv_forest_db: float


class TimelineItem(Strict):
    time_utc: str
    label: str
    source: str


# /communities/{osm_id}/route
class RouteInfo(Strict):
    status: CommunityStatus
    reason: str
    nearest_hub: str | None


class Health(Strict):
    status: Literal["ok"]
    version: str


class ErrorBody(Strict):
    detail: str
