// Turning values from the data files into text. No result is ever typed by hand: these only format.

import type { TimeseriesPoint } from './types.ts';

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const MONTHS_LONG = [
  'January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December',
];
const PERCENT = 100; // unit conversion: the data files store rates as fractions
const MS_PER_HOUR = 3_600_000;
const MS_PER_DAY = 86_400_000;
const HECTARE_M2 = 10_000;

const nf = (digits: number) => new Intl.NumberFormat('en', { maximumFractionDigits: digits, minimumFractionDigits: digits });

/** "27 Sep" (UTC) */
export function fmtDay(iso: string): string {
  const d = new Date(iso);
  return `${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]}`;
}
/** "27 Sep 2026" (UTC) */
export function fmtDayYear(iso: string): string {
  return `${fmtDay(iso)} ${new Date(iso).getUTCFullYear()}`;
}
/** "9 October 2026" (UTC) */
export function fmtDayLong(iso: string): string {
  const d = new Date(iso);
  return `${d.getUTCDate()} ${MONTHS_LONG[d.getUTCMonth()]} ${d.getUTCFullYear()}`;
}
/** "9 Oct 2026, 17:56 UTC" */
export function fmtDateTime(iso: string): string {
  const d = new Date(iso);
  const hh = String(d.getUTCHours()).padStart(2, '0');
  const mm = String(d.getUTCMinutes()).padStart(2, '0');
  return `${fmtDayYear(iso)}, ${hh}:${mm} UTC`;
}

export function fmtNumber(n: number | null | undefined, digits = 0): string {
  return n === null || n === undefined || !Number.isFinite(n) ? '–' : nf(digits).format(n);
}
/** A 0-1 rate as a whole-number percent, without the % sign. */
export function fmtPercent(rate: number | null | undefined): string {
  return rate === null || rate === undefined || !Number.isFinite(rate) ? '–' : nf(0).format(rate * PERCENT);
}
/** Square metres, or hectares above one hectare's worth of 10,000 m². */
export function fmtArea(m2: number): string {
  return m2 > HECTARE_M2 ? `${fmtNumber(m2 / HECTARE_M2, 1)} ha` : `${fmtNumber(m2, 0)} m²`;
}
export function fmtDb(db: number): string {
  return fmtNumber(db, 1);
}

/** Whole hours from the quake to a later time. */
export function hoursBetween(fromIso: string, toIso: string): number {
  return Math.round((new Date(toIso).getTime() - new Date(fromIso).getTime()) / MS_PER_HOUR);
}
export function daysBetween(fromIso: string, toIso: string): number {
  return Math.round((new Date(toIso).getTime() - new Date(fromIso).getTime()) / MS_PER_DAY);
}

/** Average drop in landslide HV after the quake compared with before (positive number of dB), or null. */
export function landslideDrop(series: TimeseriesPoint[], quakeIso: string): number | null {
  const q = new Date(quakeIso).getTime();
  const before = series.filter((s) => new Date(s.date).getTime() < q).map((s) => s.hv_landslide_db);
  const after = series.filter((s) => new Date(s.date).getTime() > q).map((s) => s.hv_landslide_db);
  if (!before.length || !after.length) return null;
  const mean = (a: number[]) => a.reduce((x, y) => x + y, 0) / a.length;
  return mean(before) - mean(after);
}
