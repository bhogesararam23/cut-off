// Filtering, sorting and summing for the Landslides and Access tabs. Pure functions, so they can be tested.
import type {
  Communities, CommunityStatus, Confidence, LandslideProps, Landslides, LineGeometry, RoadStatus, Roads,
} from './types.ts';

export type ConfidenceFilter = 'all' | 'medium' | 'high';
export type SortKey = 'size' | 'confidence' | 'passes';
type LandslideFeature = Landslides['features'][number];

const RANK: Record<Confidence, number> = { high: 3, medium: 2, low: 1 };
const MIN_RANK: Record<ConfidenceFilter, number> = { all: 1, medium: 2, high: 3 };

export function filterLandslides(features: LandslideFeature[], filter: ConfidenceFilter): LandslideFeature[] {
  return features.filter((f) => RANK[f.properties.confidence] >= MIN_RANK[filter]);
}

const byId = (a: LandslideProps, b: LandslideProps) => a.id.localeCompare(b.id);

/** A new array, sorted largest/most-confident/most-seen first. Ties keep a stable order by id. */
export function sortLandslides(features: LandslideFeature[], key: SortKey): LandslideFeature[] {
  const cmp: Record<SortKey, (a: LandslideProps, b: LandslideProps) => number> = {
    size: (a, b) => b.area_m2 - a.area_m2,
    confidence: (a, b) => RANK[b.confidence] - RANK[a.confidence] || b.area_m2 - a.area_m2,
    passes: (a, b) => b.pairs_seen - a.pairs_seen || b.area_m2 - a.area_m2,
  };
  return [...features].sort((a, b) => cmp[key](a.properties, b.properties) || byId(a.properties, b.properties));
}

const EARTH_RADIUS_KM = 6371.0088;
const rad = (d: number) => (d * Math.PI) / 180;

/** Great-circle distance between two [lon, lat] points, in kilometres. */
export function haversineKm(a: number[], b: number[]): number {
  const dLat = rad(b[1] - a[1]);
  const dLon = rad(b[0] - a[0]);
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(rad(a[1])) * Math.cos(rad(b[1])) * Math.sin(dLon / 2) ** 2;
  return 2 * EARTH_RADIUS_KM * Math.asin(Math.sqrt(h));
}

function lineLengthKm(coords: number[][]): number {
  let km = 0;
  for (let i = 1; i < coords.length; i++) km += haversineKm(coords[i - 1], coords[i]);
  return km;
}

export function geometryLengthKm(g: LineGeometry): number {
  return g.type === 'LineString' ? lineLengthKm(g.coordinates) : g.coordinates.reduce((s, l) => s + lineLengthKm(l), 0);
}

/** Kilometres of road in each status, summed from the road geometry. */
export function roadKmByStatus(roads: Roads): Record<RoadStatus, number> {
  const km: Record<RoadStatus, number> = { blocked: 0, at_risk: 0, clear: 0, unknown: 0 };
  for (const f of roads.features) km[f.properties.status] += geometryLengthKm(f.geometry);
  return km;
}

type CommunityFeature = Communities['features'][number];

/** Communities by status, each group sorted by name. */
export function groupCommunities(c: Communities): Record<CommunityStatus, CommunityFeature[]> {
  const out: Record<CommunityStatus, CommunityFeature[]> = { cut_off: [], unknown: [], reachable: [] };
  for (const f of c.features) out[f.properties.status].push(f);
  for (const k of Object.keys(out) as CommunityStatus[]) out[k].sort((a, b) => a.properties.name.localeCompare(b.properties.name));
  return out;
}
