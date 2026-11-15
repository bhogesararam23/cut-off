// The numbers of the first screen and of the "How sure" section, worked out only from the data files.
// A missing value is reported as null and shown as "not available": never a guess.
import type { Communities, SizeDetection, Stats, ValidationStats } from './types.ts';

export const MIN_N_TO_SCORE = 5; // with fewer test points than this, a rate would be meaningless

export interface Tile {
  key: 'landslides' | 'roads' | 'communities' | 'people';
  value: number | null;
  unit?: string;
  digits: number;
  source: string;
}

/** People living in the communities marked possibly cut off, counting only places with a known population. */
export function peopleInCutOff(c: Communities | undefined): { people: number | null; known: number; total: number } {
  if (!c) return { people: null, known: 0, total: 0 };
  const cut = c.features.filter((f) => f.properties.status === 'cut_off');
  const known = cut.filter((f) => f.properties.population !== null);
  return { people: known.length ? known.reduce((s, f) => s + (f.properties.population as number), 0) : null, known: known.length, total: cut.length };
}

export function answerTiles(stats: Stats, communities: Communities | undefined): Tile[] {
  return [
    { key: 'landslides', value: stats.landslides, digits: 0, source: 'stats.json' },
    { key: 'roads', value: stats.roads_blocked_km, unit: 'km', digits: 1, source: 'stats.json' },
    { key: 'communities', value: stats.communities_cut_off, digits: 0, source: 'stats.json' },
    { key: 'people', value: peopleInCutOff(communities).people, digits: 0, source: 'communities.geojson' },
  ];
}

export interface SizeRow extends SizeDetection {
  /** false when there are too few points for a rate to mean anything */
  scored: boolean;
}

/** One row per size group, always small / medium / large, with groups that have no test points shown as n = 0. */
export function sizeRows(bySize: SizeDetection[]): SizeRow[] {
  return (['small', 'medium', 'large'] as const).map((size) => {
    const b = bySize.find((x) => x.size === size) ?? { size, n: 0, detection_rate: 0 };
    return { ...b, scored: b.n >= MIN_N_TO_SCORE };
  });
}

/** Counts behind the rates: how many test points of each kind were flagged or not. */
export function confusion(v: ValidationStats) {
  const found = Math.round(v.detection_rate * v.n_test_landslide);
  const falseAlarms = Math.round(v.false_alarm_rate * v.n_test_forest);
  return { found, missed: v.n_test_landslide - found, falseAlarms, correctForest: v.n_test_forest - falseAlarms };
}

/** True when the no-quake check fails: as much (or more) is flagged before the quake as after it. */
export function baselineFails(stats: Stats): boolean {
  return stats.baseline_no_change_flag_rate >= stats.post_event_flag_rate;
}
