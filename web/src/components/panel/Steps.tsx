import { useMemo } from 'react';
import { C, fill } from '../../lib/content.ts';
import { STATIC_BASE } from '../../lib/data.ts';
import { ready, useData } from '../../lib/DataContext.tsx';
import { fmtDateTime, fmtNumber, fmtPercent } from '../../lib/format.ts';
import { roadKmByStatus } from '../../lib/lists.ts';
import { FileError } from '../FileError.tsx';
import { Skeleton } from '../Skeleton.tsx';
import { Timeline } from './Timeline.tsx';

/** Step 1: what happened. */
export function Happened() {
  const { event } = useData();
  const e = ready(event);
  return (
    <section aria-labelledby="happened-h" className="space-y-3">
      <h2 id="happened-h" className="text-lg font-semibold">{C.tabs.happened}</h2>
      {event.status === 'error' && <FileError file={event.file} />}
      {e ? (
        <>
          <p className="text-sm">{C.explorer.happened}</p>
          <p className="num text-sm">{e.name} · {fmtDateTime(e.time_utc)}</p>
          <p className="num text-sm">{fill(C.explorer.epicentre, { lat: fmtNumber(e.epicentre[1], 3), lon: fmtNumber(Math.abs(e.epicentre[0]), 3) })}</p>
        </>
      ) : (
        <Skeleton className="h-16" />
      )}
      <Timeline />
    </section>
  );
}

const FILES = ['landslides.geojson', 'roads.geojson', 'communities.geojson'];

/** Step 3: which roads, with the road totals and the downloads. */
export function RoadsStep() {
  const { roads } = useData();
  const data = ready(roads);
  const km = useMemo(() => (data && data.features.length ? roadKmByStatus(data) : null), [data]);
  return (
    <section aria-labelledby="roads-h" className="space-y-3">
      <h2 id="roads-h" className="text-lg font-semibold">{C.tabs.roads}</h2>
      <p className="text-sm">{C.explorer.roadsIntro}</p>
      {roads.status === 'loading' && <Skeleton className="h-24" />}
      {roads.status === 'error' && <FileError file={roads.file} />}
      {km && (
        <dl className="text-sm">
          {(['blocked', 'at_risk', 'clear', 'unknown'] as const).map((s) => (
            <div key={s} className="flex justify-between border-b border-ink/10 py-1.5">
              <dt>{C.legend.roads[s]}</dt>
              <dd className="num">{fmtNumber(km[s], 1)} km</dd>
            </div>
          ))}
        </dl>
      )}
      <h3 className="pt-2 text-sm font-semibold">{C.explorer.downloads}</h3>
      <ul className="text-sm">
        {FILES.map((f) => (
          <li key={f}><a className="num underline decoration-brand decoration-2 underline-offset-2" href={`${STATIC_BASE}/${f}`} download>{f}</a></li>
        ))}
      </ul>
      <p className="text-xs text-ink/75">{C.explorer.odbl}</p>
      <button type="button" onClick={() => window.print()} className="rounded-card border border-ink px-3 py-1.5 text-sm font-medium hover:bg-ink/5">Print briefing</button>
    </section>
  );
}

/** Step 5: the short version of the accuracy check, with a link to the full section. */
export function SureStep() {
  const { stats } = useData();
  const s = ready(stats);
  const v = s?.validation ?? null;
  return (
    <section aria-labelledby="surestep-h" className="space-y-3">
      <h2 id="surestep-h" className="text-lg font-semibold">{C.tabs.sure}</h2>
      {stats.status === 'error' && <FileError file={stats.file} />}
      {s && !v && <p className="text-sm">{C.evidence.noValidation}</p>}
      {v && (
        <p className="text-sm">
          {fill(C.explorer.sureShort, {
            detection: fmtPercent(v.detection_rate, 1), n_land: v.n_test_landslide, false_alarm: fmtPercent(v.false_alarm_rate, 1),
            n_forest: v.n_test_forest, auc: fmtNumber(v.auc, 2),
          })}
        </p>
      )}
      {s && s.baseline_no_change_flag_rate >= s.post_event_flag_rate && <p className="rounded-card border border-brand bg-white p-2 text-sm">{C.evidence.baselineWarning}</p>}
      <p><a href="#sure" className="text-sm font-semibold underline decoration-brand decoration-2 underline-offset-2">{C.explorer.sureLink}</a></p>
    </section>
  );
}
