// Turns the properties MapLibre returns for a clicked feature into the typed objects the app uses.
// MapLibre may drop null properties, so missing values are read as null.
import type { Picked } from './AppState.tsx';
import type { CommunityProps, LandslideProps, RoadProps } from './types.ts';

type Raw = Record<string, unknown>;
const str = (v: unknown): string | null => (typeof v === 'string' ? v : null);
const num = (v: unknown): number | null => (typeof v === 'number' && Number.isFinite(v) ? v : null);

export const LAYER_KIND: Record<string, Picked['kind']> = {
  landslides: 'landslide',
  roads: 'road',
  'roads-blocked': 'road',
  'roads-risk': 'road',
  communities: 'community',
};

export function toPicked(layerId: string, p: Raw, lngLat: [number, number]): Picked | null {
  switch (LAYER_KIND[layerId]) {
    case 'landslide':
      return {
        kind: 'landslide', lngLat,
        props: {
          id: String(p.id ?? ''), area_m2: Number(p.area_m2), hv_before_db: Number(p.hv_before_db), hv_after_db: Number(p.hv_after_db),
          dhv_db: Number(p.dhv_db), slope_deg: Number(p.slope_deg), pairs_seen: Number(p.pairs_seen), pairs_visible: Number(p.pairs_visible),
          confidence: p.confidence as LandslideProps['confidence'],
        },
      };
    case 'road':
      return {
        kind: 'road', lngLat,
        props: {
          osm_id: str(p.osm_id), name: str(p.name), highway: str(p.highway), status: p.status as RoadProps['status'],
          min_distance_m: num(p.min_distance_m), landslide_ids: str(p.landslide_ids) ?? '',
        },
      };
    case 'community':
      return {
        kind: 'community', lngLat,
        props: {
          osm_id: str(p.osm_id), name: String(p.name ?? ''), place: String(p.place ?? ''), population: num(p.population),
          status: p.status as CommunityProps['status'], nearest_hub: str(p.nearest_hub), reason: String(p.reason ?? ''),
        },
      };
    default:
      return null;
  }
}
