import { Bar, BarChart, CartesianGrid, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { C, fill } from '../../lib/content.ts';
import { fmtPercent } from '../../lib/format.ts';
import type { SizeDetection } from '../../lib/types.ts';

const ORDER: SizeDetection['size'][] = ['small', 'medium', 'large'];
const BAR_COLOR = '#334155';
const RATE_MAX = 1; // rates are stored as fractions of 1
export const MIN_N_TO_SCORE = 5; // with fewer test points than this, a rate would be meaningless

/** Detection rate by landslide size, with the number of test points (n) on each bar. */
export function DetectionBySize({ bySize }: { bySize: SizeDetection[] }) {
  const present = ORDER.map((size) => bySize.find((b) => b.size === size)).filter((b): b is SizeDetection => b !== undefined);
  // groups with too few points get no bar and no rate, only their count
  const data = present.map((b) => ({ ...b, detection_rate: b.n >= MIN_N_TO_SCORE ? b.detection_rate : null }));
  const summary = present
    .map((b) =>
      b.n >= MIN_N_TO_SCORE
        ? fill(C.evidence.chart1Scored, { size: b.size, rate: fmtPercent(b.detection_rate), n: b.n })
        : fill(C.evidence.chart1TooFew, { size: b.size, n: b.n }),
    )
    .join('. ') + '.';

  return (
    <figure className="space-y-1">
      <figcaption className="font-semibold">{C.evidence.chart1Title}</figcaption>
      {present.length === 0 ? (
        <p className="text-sm text-slate-600">{C.evidence.chartEmpty}</p>
      ) : (
        <>
          <div role="img" aria-label={summary} className="h-52 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data} margin={{ top: 18, right: 8, bottom: 0, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="size" />
                <YAxis domain={[0, RATE_MAX]} tickFormatter={(v: number) => `${fmtPercent(v)}%`} width={44} />
                <Tooltip formatter={(v) => (v === null || v === undefined ? '–' : `${fmtPercent(Number(v))}%`)} labelFormatter={(l) => String(l)} />
                <Bar dataKey="detection_rate" name="Detection rate" fill={BAR_COLOR} isAnimationActive={false}>
                  <LabelList dataKey="n" position="top" formatter={(v) => `n = ${v}`} className="text-xs" />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <p className="text-sm text-slate-700">{summary}</p>
        </>
      )}
    </figure>
  );
}
