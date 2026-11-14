// Loads the output files. By default they are static files; if VITE_API_URL is set the API is tried first
// and the static files are the fallback, so a sleeping or broken API never breaks the app.

import type {
  Communities, EventInfo, Landslides, Pair, Roads, Stats, TimelineItem, TimeseriesPoint, UnknownAreas,
} from './types.ts';

const API = import.meta.env.VITE_API_URL;
export const STATIC_BASE = (import.meta.env.VITE_DATA_URL || '/data/panama-2026').replace(/\/$/, '');
export const EVENT_ID = 'panama-2026';

export async function getJson<T>(name: string, apiPath: string): Promise<T> {
  if (API) {
    try {
      const r = await fetch(`${API.replace(/\/$/, '')}${apiPath}`);
      if (r.ok) return (await r.json()) as T;
    } catch {
      /* fall through to the static file */
    }
  }
  const r = await fetch(`${STATIC_BASE}/${name}`);
  if (!r.ok) throw new Error(`missing ${name}`);
  return (await r.json()) as T;
}

/** URL of an image named in pairs.json: absolute URLs (from the API) are kept, names are looked up in the data folder. */
export function assetUrl(name: string): string {
  return /^https?:\/\//.test(name) ? name : `${STATIC_BASE}/${name}`;
}

export interface FileSpec<T> {
  name: string;
  api: string;
  _type?: T;
}
const spec = <T,>(name: string, api: string): FileSpec<T> => ({ name, api });

export const FILES = {
  event: spec<EventInfo>('event.json', `/api/events/${EVENT_ID}`),
  pairs: spec<Pair[]>('pairs.json', `/api/events/${EVENT_ID}/pairs`),
  stats: spec<Stats>('stats.json', `/api/events/${EVENT_ID}/stats`),
  landslides: spec<Landslides>('landslides.geojson', `/api/events/${EVENT_ID}/landslides`),
  unknown: spec<UnknownAreas>('unknown.geojson', `/api/events/${EVENT_ID}/unknown`),
  roads: spec<Roads>('roads.geojson', `/api/events/${EVENT_ID}/roads`),
  communities: spec<Communities>('communities.geojson', `/api/events/${EVENT_ID}/communities`),
  timeseries: spec<TimeseriesPoint[]>('timeseries.json', `/api/events/${EVENT_ID}/timeseries`),
  timeline: spec<TimelineItem[]>('timeline.json', `/api/events/${EVENT_ID}/timeline`),
} as const;

export type FileKey = keyof typeof FILES;
export type Loadable<T> = { status: 'loading' } | { status: 'ready'; data: T } | { status: 'error'; file: string };
