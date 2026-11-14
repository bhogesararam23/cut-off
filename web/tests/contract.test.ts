// Checks that the key lists in src/lib/types.ts match the real output files exactly.
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import {
  COMMUNITY_KEYS, EVENT_KEYS, LANDSLIDE_KEYS, PAIR_KEYS, ROAD_KEYS, SIZE_DETECTION_KEYS, STATS_KEYS,
  STATS_PARAMS_KEYS, TIMELINE_KEYS, TIMESERIES_KEYS, VALIDATION_KEYS,
} from '../src/lib/types.ts';

const DIR = new URL('../public/data/panama-2026/', import.meta.url);
const read = (name: string) => JSON.parse(readFileSync(new URL(name, DIR), 'utf-8'));
const same = (obj: object, keys: object, where: string) =>
  assert.deepEqual(Object.keys(obj).sort(), Object.keys(keys).sort(), `${where}: keys differ from types.ts`);

test('event.json', () => same(read('event.json'), EVENT_KEYS, 'event.json'));

test('pairs.json', () => {
  const pairs = read('pairs.json');
  assert.ok(pairs.length > 0);
  pairs.forEach((p: object, i: number) => same(p, PAIR_KEYS, `pairs.json[${i}]`));
});

test('landslides.geojson', () => {
  const fc = read('landslides.geojson');
  assert.ok(fc.features.length > 0);
  fc.features.forEach((f: { properties: object }) => same(f.properties, LANDSLIDE_KEYS, 'landslide'));
});

test('roads.geojson', () => {
  read('roads.geojson').features.forEach((f: { properties: object }) => same(f.properties, ROAD_KEYS, 'road'));
});

test('communities.geojson', () => {
  read('communities.geojson').features.forEach((f: { properties: object }) => same(f.properties, COMMUNITY_KEYS, 'community'));
});

test('stats.json', () => {
  const s = read('stats.json');
  same(s, STATS_KEYS, 'stats.json');
  same(s.params, STATS_PARAMS_KEYS, 'stats.params');
  if (s.validation !== null) {
    same(s.validation, VALIDATION_KEYS, 'stats.validation');
    s.validation.by_size.forEach((b: object) => same(b, SIZE_DETECTION_KEYS, 'stats.validation.by_size'));
  }
});

test('timeseries.json and timeline.json', () => {
  read('timeseries.json').forEach((t: object) => same(t, TIMESERIES_KEYS, 'timeseries'));
  read('timeline.json').forEach((t: object) => same(t, TIMELINE_KEYS, 'timeline'));
});
