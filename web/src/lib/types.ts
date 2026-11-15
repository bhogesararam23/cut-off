// Types for every output file the pipeline writes to public/data/<event>/.
// They mirror the file format exactly: same keys, same types, missing values are null.
// Each *_KEYS record lists the keys of one object; the compiler forces it to match the interface,
// and tests/contract.test.ts compares it with the real files.

export type PairId = 't141d' | 't4a' | 't40d' | 't76a';
export type Direction = 'ascending' | 'descending';
export type Confidence = 'high' | 'medium' | 'low';
export type RoadStatus = 'blocked' | 'at_risk' | 'clear' | 'unknown';
export type CommunityStatus = 'cut_off' | 'reachable' | 'unknown';

/** [longitude, latitude] in WGS84 (EPSG:4326). */
export type LonLat = [number, number];
/** [west, south, east, north] */
export type BBox = [number, number, number, number];

// event.json
export interface EventReference {
  label: string;
  url: string;
}
/** Optional optical (Sentinel-2) comparison images, same corner order as the radar images. */
export interface Optical {
  before_webp: string;
  after_webp: string;
  bounds: [LonLat, LonLat, LonLat, LonLat];
  before_caption: string;
  after_caption: string;
  attribution: string;
}
export interface EventInfo {
  event_id: string;
  name: string;
  time_utc: string;
  epicentre: LonLat;
  bbox: BBox;
  maturity: string;
  mock: boolean;
  optical: Optical | null;
  references: EventReference[];
}
export const EVENT_KEYS: Record<keyof EventInfo, true> = {
  event_id: true, name: true, time_utc: true, epicentre: true, bbox: true, maturity: true, mock: true, optical: true, references: true,
};

// pairs.json (array)
export interface Pair {
  id: PairId;
  track: number;
  direction: Direction;
  before: string;
  after: string;
  before_png: string;
  after_png: string;
  change_png: string;
  /** top-left, top-right, bottom-right, bottom-left (MapLibre image source order) */
  bounds: [LonLat, LonLat, LonLat, LonLat];
  granules: string[];
  flagged_pixels: number;
}
export const PAIR_KEYS: Record<keyof Pair, true> = {
  id: true, track: true, direction: true, before: true, after: true, before_png: true, after_png: true,
  change_png: true, bounds: true, granules: true, flagged_pixels: true,
};

// GeoJSON
export interface Feature<G, P> {
  type: 'Feature';
  geometry: G;
  properties: P;
}
export interface FeatureCollection<G, P> {
  type: 'FeatureCollection';
  features: Feature<G, P>[];
}
export interface PolygonGeometry {
  type: 'Polygon';
  coordinates: number[][][];
}
export interface MultiPolygonGeometry {
  type: 'MultiPolygon';
  coordinates: number[][][][];
}
export interface LineStringGeometry {
  type: 'LineString';
  coordinates: number[][];
}
export interface MultiLineStringGeometry {
  type: 'MultiLineString';
  coordinates: number[][][];
}
export interface PointGeometry {
  type: 'Point';
  coordinates: LonLat;
}
export type AreaGeometry = PolygonGeometry | MultiPolygonGeometry;
export type LineGeometry = LineStringGeometry | MultiLineStringGeometry;

// landslides.geojson
export interface LandslideProps {
  id: string;
  area_m2: number;
  hv_before_db: number;
  hv_after_db: number;
  /** mean change in dB, negative = drop */
  dhv_db: number;
  slope_deg: number;
  /** 0-4 */
  pairs_seen: number;
  /** 0-4 */
  pairs_visible: number;
  confidence: Confidence;
}
export const LANDSLIDE_KEYS: Record<keyof LandslideProps, true> = {
  id: true, area_m2: true, hv_before_db: true, hv_after_db: true, dhv_db: true, slope_deg: true,
  pairs_seen: true, pairs_visible: true, confidence: true,
};
export type Landslides = FeatureCollection<AreaGeometry, LandslideProps>;

// unknown.geojson: areas no pair can see (shadow, layover or no data). No required properties.
export type UnknownAreas = FeatureCollection<AreaGeometry, Record<string, never>>;

// roads.geojson
export interface RoadProps {
  osm_id: string | null;
  name: string | null;
  highway: string | null;
  status: RoadStatus;
  /** distance to the nearest landslide, metres */
  min_distance_m: number | null;
  /** comma-separated ids within 100 m */
  landslide_ids: string;
}
export const ROAD_KEYS: Record<keyof RoadProps, true> = {
  osm_id: true, name: true, highway: true, status: true, min_distance_m: true, landslide_ids: true,
};
export type Roads = FeatureCollection<LineGeometry, RoadProps>;

// communities.geojson
export interface CommunityProps {
  osm_id: string | null;
  name: string;
  /** OSM class: town, village, hamlet, ... */
  place: string;
  population: number | null;
  status: CommunityStatus;
  nearest_hub: string | null;
  reason: string;
}
export const COMMUNITY_KEYS: Record<keyof CommunityProps, true> = {
  osm_id: true, name: true, place: true, population: true, status: true, nearest_hub: true, reason: true,
};
export type Communities = FeatureCollection<PointGeometry, CommunityProps>;

// stats.json
export interface StatsParams {
  threshold_db: number;
  min_slope_deg: number;
  min_forest_hv_db: number;
  min_pixels: number;
}
export const STATS_PARAMS_KEYS: Record<keyof StatsParams, true> = {
  threshold_db: true, min_slope_deg: true, min_forest_hv_db: true, min_pixels: true,
};
export interface SizeDetection {
  size: 'small' | 'medium' | 'large';
  n: number;
  /** 0-1 */
  detection_rate: number;
}
export const SIZE_DETECTION_KEYS: Record<keyof SizeDetection, true> = { size: true, n: true, detection_rate: true };
export interface ValidationStats {
  split: 'test';
  n_test_landslide: number;
  n_test_forest: number;
  /** 0-1 */
  detection_rate: number;
  /** 0-1 */
  false_alarm_rate: number;
  auc: number;
  threshold_db: number;
  by_size: SizeDetection[];
}
export const VALIDATION_KEYS: Record<keyof ValidationStats, true> = {
  split: true, n_test_landslide: true, n_test_forest: true, detection_rate: true, false_alarm_rate: true,
  auc: true, threshold_db: true, by_size: true,
};
export interface Stats {
  mock: boolean;
  landslides: number;
  area_km2: number;
  roads_blocked_km: number | null;
  communities_cut_off: number | null;
  /** null until validation has run */
  validation: ValidationStats | null;
  /** 0-1 */
  baseline_no_change_flag_rate: number;
  /** 0-1 */
  post_event_flag_rate: number;
  params: StatsParams;
  pixel_m: number;
}
export const STATS_KEYS: Record<keyof Stats, true> = {
  mock: true, landslides: true, area_km2: true, roads_blocked_km: true, communities_cut_off: true, validation: true,
  baseline_no_change_flag_rate: true, post_event_flag_rate: true, params: true, pixel_m: true,
};

// timeseries.json (array)
export interface TimeseriesPoint {
  date: string;
  track: number;
  direction: Direction;
  hv_landslide_db: number;
  hv_forest_db: number;
}
export const TIMESERIES_KEYS: Record<keyof TimeseriesPoint, true> = {
  date: true, track: true, direction: true, hv_landslide_db: true, hv_forest_db: true,
};

// timeline.json (array)
export interface TimelineItem {
  time_utc: string;
  label: string;
  source: string;
}
export const TIMELINE_KEYS: Record<keyof TimelineItem, true> = { time_utc: true, label: true, source: true };
