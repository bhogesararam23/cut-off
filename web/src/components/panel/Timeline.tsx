import { C } from '../../lib/content.ts';
import { ready, useData } from '../../lib/DataContext.tsx';
import { fmtDateTime } from '../../lib/format.ts';
import { FileError } from '../FileError.tsx';
import { Skeleton } from '../Skeleton.tsx';

export function Timeline() {
  const { timeline } = useData();
  const items = ready(timeline);
  return (
    <section aria-labelledby="timeline-h" className="space-y-3">
      <h2 id="timeline-h" className="text-lg font-semibold">{C.timeline.heading}</h2>
      {timeline.status === 'loading' && <Skeleton className="h-24" />}
      {timeline.status === 'error' && <FileError file={timeline.file} />}
      {items && items.length === 0 && <p className="text-[15px] text-slate-600">{C.timeline.empty}</p>}
      {items && items.length > 0 && (
        <ol className="space-y-3 border-l-2 border-slate-300 pl-4">
          {[...items]
            .sort((a, b) => a.time_utc.localeCompare(b.time_utc))
            .map((t) => (
              <li key={`${t.time_utc}${t.label}`} className="relative text-[15px]">
                <span aria-hidden="true" className="absolute -left-[1.4rem] top-1.5 h-2.5 w-2.5 rounded-full bg-slate-600" />
                <time dateTime={t.time_utc} className="block text-xs text-slate-600">{fmtDateTime(t.time_utc)}</time>
                {t.label} <span className="text-xs text-slate-600">({t.source})</span>
              </li>
            ))}
        </ol>
      )}
      <p className="text-xs text-slate-600">{C.timeline.footer}</p>
    </section>
  );
}
