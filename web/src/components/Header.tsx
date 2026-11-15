import { C, fill } from '../lib/content.ts';
import { ready, useData } from '../lib/DataContext.tsx';
import { fmtDay, fmtDayYear } from '../lib/format.ts';

export const REPO = import.meta.env.VITE_REPO_URL?.replace(/\/$/, '') || 'https://github.com/bhogesararam23/cut-off';

const link = 'rounded px-2 py-1 text-sm text-white/90 hover:bg-white/10 hover:text-white';

/** Sticky header: plain-text wordmark, the data label (from the files) and section links. */
export function Header() {
  const { event, pairs } = useData();
  const e = ready(event);
  const first = ready(pairs)?.[0];
  const label = e && first ? fill(C.header.label, { maturity: e.maturity, before: fmtDay(first.before), after: fmtDayYear(first.after) }) : null;
  return (
    <header className="sticky top-0 z-40 flex h-14 items-center gap-4 bg-ink px-4 text-white">
      <a href="#top" className="shrink-0 text-lg font-semibold tracking-tight">{C.topBar.title}</a>
      <p className="num min-w-0 flex-1 truncate text-[11px] text-white/80 sm:text-xs" title={label ?? undefined}>{label ?? '…'}</p>
      <nav aria-label="Sections" className="hidden shrink-0 items-center gap-1 md:flex">
        <a className={link} href="#top">{C.header.nav.overview}</a>
        <a className={link} href="#map">{C.header.nav.map}</a>
        <a className={link} href="#sure">{C.header.nav.sure}</a>
        <a className={link} href="#method">{C.header.nav.method}</a>
        <a className={link} href="#data">{C.header.nav.data}</a>
        <a className={link} href={REPO} target="_blank" rel="noopener noreferrer">{C.header.nav.repo}</a>
      </nav>
    </header>
  );
}
