import { useApp } from '../lib/AppState.tsx';
import { C, fill } from '../lib/content.ts';
import { ready, useData } from '../lib/DataContext.tsx';
import { fmtDayLong } from '../lib/format.ts';
import { PairSelector } from './PairSelector.tsx';

export function TopBar() {
  const { event } = useData();
  const { setAboutOpen } = useApp();
  const e = ready(event);
  return (
    <header className="flex items-center justify-between gap-2 border-b border-slate-200 bg-white px-3 py-2">
      <div className="min-w-0">
        <h1 className="text-lg font-semibold leading-tight">{C.topBar.title}</h1>
        <p className="truncate text-xs text-slate-600">
          {e ? fill(C.topBar.subtitle, { name: e.name, date: fmtDayLong(e.time_utc) }) : '…'}
        </p>
      </div>
      <div className="flex shrink-0 items-center gap-2">
        <PairSelector />
        <button
          type="button"
          aria-label={C.topBar.about}
          onClick={() => setAboutOpen(true)}
          className="rounded border border-slate-300 px-3 py-1 text-sm hover:bg-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-500"
        >
          {C.topBar.about}
        </button>
      </div>
    </header>
  );
}
