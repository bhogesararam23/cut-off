// The numbers of the first screen and of the "How sure" section, worked out only from the data files.
// A missing value is reported as null and shown as "not available": never a guess.
import type { SizeDetection, Stats, ValidationStats } from './types.ts';

export const MIN_N_TO_SCORE = 5; // with fewer test points than this, a rate would be meaningless

export interface Tile {
  key: 'landslides' | 'roads' | 'communities';
  value: number | null;
  unit?: string;
  digits: number;
  source: string;
}

/** The three counts of the key facts. A missing value is null: shown as "not available", never a guess. */
export function answerTiles(stats: Stats): Tile[] {
  return [
    { key: 'landslides', value: stats.landslides, digits: 0, source: 'stats.json' },
    { key: 'roads', value: stats.roads_blocked_km, unit: 'km', digits: 1, source: 'stats.json' },
    { key: 'communities', value: stats.communities_cut_off, digits: 0, source: 'stats.json' },
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

/** True when the pre-event baseline check fails: as much (or more) is flagged before the quake as after it. */
export function baselineFails(stats: Stats): boolean {
  return stats.baseline_no_change_flag_rate >= stats.post_event_flag_rate;
}
