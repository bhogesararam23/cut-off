import { Bar, BarChart, CartesianGrid, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { C, fill } from '../../lib/content.ts';
import { fmtPercent } from '../../lib/format.ts';
import type { SizeDetection } from '../../lib/types.ts';

const ORDER: SizeDetection['size'][] = ['small', 'medium', 'large'];
const BAR_COLOR = '#334155';
const RATE_MAX = 1; // rates are stored as fractions of 1

/** Detection rate by landslide size, with the number of test points (n) on each bar. */
export function DetectionBySize({ bySize }: { bySize: SizeDetection[] }) {
  const data = ORDER.map((size) => bySize.find((b) => b.size === size)).filter((b): b is SizeDetection => b !== undefined);
  const rate = (size: SizeDetection['size']) => fmtPercent(bySize.find((b) => b.size === size)?.detection_rate);
  const summary = fill(C.evidence.chart1Summary, { small: rate('small'), medium: rate('medium'), large: rate('large') });

  return (
    <figure className="space-y-1">
      <figcaption className="font-semibold">{C.evidence.chart1Title}</figcaption>
      {data.length === 0 ? (
        <p className="text-sm text-slate-600">{C.evidence.chartEmpty}</p>
      ) : (
        <>
          <div role="img" aria-label={summary} className="h-52 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data} margin={{ top: 18, right: 8, bottom: 0, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="size" />
                <YAxis domain={[0, RATE_MAX]} tickFormatter={(v: number) => `${fmtPercent(v)}%`} width={44} />
                <Tooltip formatter={(v) => `${fmtPercent(Number(v))}%`} labelFormatter={(l) => String(l)} />
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
