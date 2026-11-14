// Tests for the text and number helpers: every displayed value is formatted from data, never invented.
import assert from 'node:assert/strict';
import test from 'node:test';
import { C, fill } from '../src/lib/content.ts';
import {
  daysBetween, fmtArea, fmtDay, fmtDayLong, fmtDayYear, fmtDateTime, fmtNumber, fmtPercent, forestStaysFlat, hoursBetween, hvDrop, landslideDrop,
} from '../src/lib/format.ts';

test('fill replaces placeholders and never invents a number', () => {
  assert.equal(fill('{a} of {b}', { a: 2, b: 4 }), '2 of 4');
  assert.equal(fill('{a} of {b}', { a: 2 }), '2 of –');
  assert.equal(fill('{a}', { a: null }), '–');
  assert.equal(fill('no placeholders', {}), 'no placeholders');
});

test('dates are formatted in UTC', () => {
  assert.equal(fmtDay('2026-09-27T23:53:35Z'), '27 Sep');
  assert.equal(fmtDayYear('2026-10-09T00:00:01Z'), '9 Oct 2026');
  assert.equal(fmtDayLong('2026-10-09T17:56:00Z'), '9 October 2026');
  assert.equal(fmtDateTime('2026-10-09T17:56:00Z'), '9 Oct 2026, 17:56 UTC');
});

test('rates are fractions in the data and percents on screen', () => {
  assert.equal(fmtPercent(0.78), '78');
  assert.equal(fmtPercent(0.004), '0');
  assert.equal(fmtPercent(0.004, 1), '0.4');
  assert.equal(fmtPercent(null), '–');
  assert.equal(fmtPercent(Number.NaN), '–');
});

test('numbers and areas', () => {
  assert.equal(fmtNumber(1234.5), '1,235');
  assert.equal(fmtNumber(1.234, 2), '1.23');
  assert.equal(fmtNumber(null), '–');
  assert.equal(fmtArea(8000), '8,000 m²');
  assert.equal(fmtArea(25600), '2.6 ha');
});

test('durations come from the timestamps', () => {
  assert.equal(hoursBetween('2026-10-09T17:56:00Z', '2026-10-09T23:53:35Z'), 6);
  assert.equal(daysBetween('2026-09-27T23:53:35Z', '2026-10-09T23:53:35Z'), 12);
});

test('landslide drop is the mean before minus the mean after the quake', () => {
  const q = '2026-10-09T17:56:00Z';
  const row = (date: string, hv: number) => ({ date, track: 1, direction: 'descending' as const, hv_landslide_db: hv, hv_forest_db: -13 });
  const series = [row('2026-09-20T00:00:00Z', -13), row('2026-09-27T00:00:00Z', -13.2), row('2026-10-10T00:00:00Z', -18), row('2026-10-12T00:00:00Z', -18.4)];
  assert.ok(Math.abs((landslideDrop(series, q) as number) - 5.1) < 1e-9);
  assert.equal(landslideDrop(series.slice(0, 2), q), null);
  assert.equal(landslideDrop([], q), null);
});

test('required wording rules hold in the app text', () => {
  const all = JSON.stringify(C);
  assert.ok(!/confirmed|detected all/i.test(all));
  for (const key of ['blocked', 'cut_off'] as const) assert.ok(C.popups.status[key].length > 0);
  assert.equal(C.popups.status.blocked, 'Likely blocked');
  assert.equal(C.popups.status.cut_off, 'Possibly cut off');
  assert.equal(C.legend.communities.cut_off, 'Possibly cut off');
  assert.equal(C.limits.items.length, 8);
});

test('forest only counts as flat when it moved far less than the landslides', () => {
  const q = '2026-10-09T17:56:00Z';
  const row = (date: string, land: number, forest: number) => ({ date, track: 1, direction: 'descending' as const, hv_landslide_db: land, hv_forest_db: forest });
  const flat = [row('2026-09-20T00:00:00Z', -13, -13), row('2026-10-12T00:00:00Z', -18, -13.2)];
  const dropped = [row('2026-09-20T00:00:00Z', -13, -13), row('2026-10-12T00:00:00Z', -18, -16)];
  assert.equal(forestStaysFlat(flat, q), true);
  assert.equal(forestStaysFlat(dropped, q), false);
  assert.equal(forestStaysFlat([], q), false);
  assert.ok(Math.abs((hvDrop(dropped, q, 'hv_forest_db') as number) - 3) < 1e-9);
});
