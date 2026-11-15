import { C, fill } from '../../lib/content.ts';
import { ready, useData } from '../../lib/DataContext.tsx';
import { daysBetween, fmtNumber, fmtPercent, hoursBetween } from '../../lib/format.ts';
import { FileError } from '../FileError.tsx';
import { Skeleton } from '../Skeleton.tsx';

function Card({ value, unit, label, mock }: { value: string; unit?: string; label: string; mock: boolean }) {
  return (
    <div className="relative rounded-lg border border-slate-200 bg-white p-3">
      {mock && <span className="absolute right-2 top-1 text-[10px] font-bold tracking-wide text-red-700">MOCK</span>}
      <p className="text-2xl font-semibold tabular-nums">
        {value}
        {unit && <span className="ml-1 text-base font-normal text-slate-600">{unit}</span>}
      </p>
      <p className="text-sm text-slate-700">{label}</p>
    </div>
  );
}

export function Overview() {
  const { stats, event, pairs } = useData();
  const s = ready(stats);
  const e = ready(event);
  // the story is about the earliest radar pass after the quake, whichever pair is listed first
  const first = [...(ready(pairs) ?? [])].sort((a, b) => a.after.localeCompare(b.after))[0];

  const story =
    e && first
      ? fill(C.overview.story, { hours: hoursBetween(e.time_utc, first.after), days: daysBetween(first.before, first.after) })
      : null;

  return (
    <section aria-labelledby="overview-h" className="space-y-3">
      <h2 id="overview-h" className="text-lg font-semibold">{C.overview.heading}</h2>
      {story ? (
        <p className="text-[15px]">{story}</p>
      ) : pairs.status === 'error' ? (
        <FileError file={pairs.file} />
      ) : event.status === 'error' ? (
        <FileError file={event.file} />
      ) : (
        <Skeleton className="h-16" />
      )}

      {stats.status === 'error' && <FileError file={stats.file} />}
      {stats.status === 'loading' && (
        <div className="grid grid-cols-2 gap-2">
          {[0, 1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-20" />
          ))}
        </div>
      )}
      {s && (
        <>
          <div className="grid grid-cols-2 gap-2">
            <Card mock={s.mock} value={fmtNumber(s.landslides)} label={C.overview.cards.landslides} />
            <Card mock={s.mock} value={fmtNumber(s.area_km2, 2)} unit="km²" label={C.overview.cards.area} />
            <Card
              mock={s.mock}
              value={s.roads_blocked_km === null ? C.overview.notAvailable : fmtNumber(s.roads_blocked_km, 1)}
              unit={s.roads_blocked_km === null ? undefined : 'km'}
              label={C.overview.cards.roads}
            />
            <Card
              mock={s.mock}
              value={s.communities_cut_off === null ? C.overview.notAvailable : fmtNumber(s.communities_cut_off)}
              label={C.overview.cards.communities}
            />
          </div>
          <p className="text-[15px]">
            {s.validation
              ? fill(C.overview.howSure, {
                  detection_rate: fmtPercent(s.validation.detection_rate),
                  false_alarm_rate: fmtPercent(s.validation.false_alarm_rate),
                })
              : C.overview.noValidation}
          </p>
        </>
      )}
      {s && s.baseline_no_change_flag_rate >= s.post_event_flag_rate && (
        <p role="note" className="rounded border border-amber-300 bg-amber-50 p-2 text-sm text-amber-900">{C.overview.weak}</p>
      )}
      <p className="text-sm text-slate-600">{C.overview.footnote}</p>
    </section>
  );
}
