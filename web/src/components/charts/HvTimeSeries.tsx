import { CartesianGrid, Legend, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { C, fill } from '../../lib/content.ts';
import { fmtDay, fmtNumber, forestStaysFlat, hvDrop } from '../../lib/format.ts';
import type { TimeseriesPoint } from '../../lib/types.ts';

const LANDSLIDE_COLOR = '#DC2626';
const FOREST_COLOR = '#16A34A';
const FOREST_DASH = '5 4'; // forest is dashed so the two lines differ by more than colour

/** Mean HV at landslides vs intact forest on every pass. A vertical line marks the quake. */
export function HvTimeSeries({ series, quakeIso }: { series: TimeseriesPoint[]; quakeIso: string }) {
  const data = [...series]
    .sort((a, b) => a.date.localeCompare(b.date))
    .map((s) => ({ ...s, t: new Date(s.date).getTime() }));

  const drop = hvDrop(series, quakeIso, 'hv_landslide_db');
  const forestDrop = hvDrop(series, quakeIso, 'hv_forest_db');
  const summary =
    drop === null
      ? C.evidence.chartEmpty
      : forestStaysFlat(series, quakeIso)
        ? fill(C.evidence.chart2Summary, { drop: fmtNumber(drop, 1) })
        : fill(C.evidence.chart2SummaryNeutral, { drop: fmtNumber(drop, 1), forest_drop: fmtNumber(forestDrop, 1) });

  return (
    <figure className="space-y-1">
      <figcaption className="font-semibold">{C.evidence.chart2Title}</figcaption>
      {data.length === 0 ? (
        <p className="text-sm text-slate-600">{C.evidence.chartEmpty}</p>
      ) : (
        <>
          <div role="img" aria-label={summary} className="h-56 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={data} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="t" type="number" scale="time" domain={['dataMin', 'dataMax']} tickFormatter={(t: number) => fmtDay(new Date(t).toISOString())} tick={{ fontSize: 11 }} />
                <YAxis unit=" dB" width={56} domain={['auto', 'auto']} tick={{ fontSize: 11 }} />
                <Tooltip
                  labelFormatter={(t) => fmtDay(new Date(Number(t)).toISOString())}
                  formatter={(v, name, item) => [`${fmtNumber(Number(v), 1)} dB`, `${name} (track ${item.payload.track}, ${item.payload.direction})`]}
                />
                <Legend />
                <ReferenceLine x={new Date(quakeIso).getTime()} stroke="#111827" strokeDasharray="2 2" label={{ value: C.evidence.quakeLabel, position: 'insideTopRight', fontSize: 11 }} />
                <Line dataKey="hv_landslide_db" name={C.evidence.atLandslides} stroke={LANDSLIDE_COLOR} strokeWidth={2} dot={{ r: 4 }} isAnimationActive={false} />
                <Line dataKey="hv_forest_db" name={C.evidence.atForest} stroke={FOREST_COLOR} strokeWidth={2} strokeDasharray={FOREST_DASH} dot={{ r: 3, strokeWidth: 1 }} isAnimationActive={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <p className="text-sm text-slate-700">{summary}</p>
        </>
      )}
    </figure>
  );
}
