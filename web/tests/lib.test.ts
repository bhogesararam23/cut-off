// Tests for the text and number helpers: every displayed value is formatted from data, never invented.
import assert from 'node:assert/strict';
import test from 'node:test';
import { C, fill } from '../src/lib/content.ts';
import {
  daysBetween, fmtArea, fmtDay, fmtDayLong, fmtDayYear, fmtDateTime, fmtNumber, fmtPercent, hoursBetween,
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

test('required wording rules hold in the app text', () => {
  const all = JSON.stringify(C);
  assert.ok(!/detected all/i.test(all));
  assert.ok(!/(?<!not (a )?)confirmed/i.test(all.replace(/not a confirmed/gi, '').replace(/not confirmed/gi, '')), 'confirmed must only appear as "not (a) confirmed"');
  for (const key of ['blocked', 'cut_off'] as const) assert.ok(C.popups.status[key].length > 0);
  assert.equal(C.popups.status.blocked, 'Likely blocked');
  assert.equal(C.popups.status.cut_off, 'Possibly cut off');
  assert.equal(C.legend.communities.cut_off, 'Possibly cut off');
});
