import assert from 'node:assert/strict';
import test from 'node:test';
import {
  filterLandslides, geometryLengthKm, groupCommunities, haversineKm, roadKmByStatus, sortLandslides,
} from '../src/lib/lists.ts';
import type { Communities, Confidence, Landslides, Roads } from '../src/lib/types.ts';

const slide = (id: string, area: number, seen: number, confidence: Confidence) => ({
  type: 'Feature' as const,
  geometry: { type: 'Polygon' as const, coordinates: [[[0, 0], [0, 1], [1, 1], [0, 0]]] },
  properties: { id, area_m2: area, hv_before_db: -12, hv_after_db: -18, dhv_db: -6, slope_deg: 20, pairs_seen: seen, pairs_visible: 4, confidence },
});
const FEATURES: Landslides['features'] = [
  slide('L0001', 100, 2, 'medium'), slide('L0002', 500, 1, 'low'), slide('L0003', 300, 4, 'high'), slide('L0004', 300, 3, 'high'),
];

test('confidence filter keeps the chosen level and above', () => {
  assert.equal(filterLandslides(FEATURES, 'all').length, 4);
  assert.deepEqual(filterLandslides(FEATURES, 'medium').map((f) => f.properties.id), ['L0001', 'L0003', 'L0004']);
  assert.deepEqual(filterLandslides(FEATURES, 'high').map((f) => f.properties.id), ['L0003', 'L0004']);
});

test('sorting by size, confidence and passes', () => {
  const ids = (key: 'size' | 'confidence' | 'passes') => sortLandslides(FEATURES, key).map((f) => f.properties.id);
  assert.deepEqual(ids('size'), ['L0002', 'L0003', 'L0004', 'L0001']);          // ties broken by id
  assert.deepEqual(ids('confidence'), ['L0003', 'L0004', 'L0001', 'L0002']);
  assert.deepEqual(ids('passes'), ['L0003', 'L0004', 'L0001', 'L0002']);
});

test('sorting does not change the input', () => {
  const copy = JSON.stringify(FEATURES);
  sortLandslides(FEATURES, 'size');
  assert.equal(JSON.stringify(FEATURES), copy);
});

test('distance: one degree of latitude is about 111 km', () => {
  assert.ok(Math.abs(haversineKm([-80, 7], [-80, 8]) - 111.19) < 0.1);
  assert.equal(haversineKm([-80, 7], [-80, 7]), 0);
});

test('line lengths add up over segments and multi-lines', () => {
  const one = geometryLengthKm({ type: 'LineString', coordinates: [[-80, 7], [-80, 7.5], [-80, 8]] });
  assert.ok(Math.abs(one - 111.19) < 0.1);
  const multi = geometryLengthKm({ type: 'MultiLineString', coordinates: [[[-80, 7], [-80, 8]], [[-81, 7], [-81, 8]]] });
  assert.ok(Math.abs(multi - 2 * 111.19) < 0.2);
});

test('road kilometres are summed per status', () => {
  const road = (status: 'blocked' | 'at_risk' | 'clear' | 'unknown', lat: number) => ({
    type: 'Feature' as const,
    geometry: { type: 'LineString' as const, coordinates: [[-80, lat], [-80, lat + 1]] },
    properties: { osm_id: null, name: null, highway: null, status, min_distance_m: null, landslide_ids: '' },
  });
  const roads: Roads = { type: 'FeatureCollection', features: [road('blocked', 0), road('blocked', 2), road('clear', 4)] };
  const km = roadKmByStatus(roads);
  assert.ok(Math.abs(km.blocked - 2 * 111.19) < 0.3 && Math.abs(km.clear - 111.19) < 0.2);
  assert.equal(km.at_risk, 0);
  assert.deepEqual(roadKmByStatus({ type: 'FeatureCollection', features: [] }), { blocked: 0, at_risk: 0, clear: 0, unknown: 0 });
});

test('communities are grouped by status and sorted by name', () => {
  const c = (name: string, status: 'cut_off' | 'reachable' | 'unknown') => ({
    type: 'Feature' as const, geometry: { type: 'Point' as const, coordinates: [0, 0] as [number, number] },
    properties: { osm_id: null, name, place: 'village', population: null, status, nearest_hub: null, reason: '' },
  });
  const fc: Communities = { type: 'FeatureCollection', features: [c('B', 'cut_off'), c('A', 'cut_off'), c('C', 'reachable')] };
  const g = groupCommunities(fc);
  assert.deepEqual(g.cut_off.map((f) => f.properties.name), ['A', 'B']);
  assert.equal(g.reachable.length, 1);
  assert.equal(g.unknown.length, 0);
});
