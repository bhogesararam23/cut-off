import { useState, type ReactNode } from 'react';
import { C } from '../../lib/content.ts';
import { COLORS } from '../../lib/mapStyle.ts';
import { DESKTOP_QUERY } from '../../lib/useMedia.ts';

function Row({ symbol, children }: { symbol: ReactNode; children: ReactNode }) {
  return (
    <li className="flex items-start gap-2">
      <span aria-hidden="true" className="mt-0.5 flex h-4 w-8 shrink-0 items-center justify-center">{symbol}</span>
      <span>{children}</span>
    </li>
  );
}

const line = (color: string, dashed = false) => (
  <svg width="32" height="10" viewBox="0 0 32 10"><line x1="1" y1="5" x2="31" y2="5" stroke={color} strokeWidth="3" strokeDasharray={dashed ? '6 4' : undefined} /></svg>
);
const dot = (color: string, ringed = false) => (
  <svg width="20" height="20" viewBox="0 0 20 20">
    {ringed && <circle cx="10" cy="10" r="8.5" fill="none" stroke={COLORS.communities.cut_off} strokeWidth="2" />}
    <circle cx="10" cy="10" r="5" fill={color} stroke="#fff" strokeWidth={ringed ? 2 : 1} />
  </svg>
);
const swatch = (color: string, opacity: number) => <span className="block h-3 w-6 rounded-sm" style={{ backgroundColor: color, opacity }} />;

/** Explains the colours and symbols on the map. Open on larger screens, closed on phones; a button toggles it. */
export function Legend() {
  const [open, setOpen] = useState(() => window.matchMedia(DESKTOP_QUERY).matches);

  return (
    <div className="absolute bottom-6 left-2 z-10 max-w-[19rem] rounded-md bg-white/95 text-xs shadow">
      <button
        type="button"
        aria-expanded={open}
        aria-controls="legend-list"
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between gap-3 rounded-md px-3 py-1.5 text-sm font-semibold focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-500"
      >
        {C.legend.title}
        <span aria-hidden="true">{open ? '▾' : '▸'}</span>
      </button>
      {open && (
        <div id="legend-list" className="px-2 pb-2">
          <ul className="space-y-1">
            <Row symbol={<span className="block h-3 w-6 bg-gradient-to-r from-black to-white ring-1 ring-slate-400" />}>{C.legend.radar}</Row>
            <Row symbol={<span className="block h-3 w-6 bg-gradient-to-r from-red-600 to-blue-600" />}>{C.legend.change}</Row>
            <Row symbol={swatch(COLORS.landslide, 0.75)}>{C.legend.landslide}</Row>
            <Row symbol={line(COLORS.roads.blocked, true)}>{C.legend.roads.blocked}</Row>
            <Row symbol={line(COLORS.roads.at_risk)}>{C.legend.roads.at_risk}</Row>
            <Row symbol={line(COLORS.roads.clear)}>{C.legend.roads.clear}</Row>
            <Row symbol={line(COLORS.roads.unknown)}>{C.legend.roads.unknown}</Row>
            <Row symbol={dot(COLORS.communities.cut_off, true)}>{C.legend.communities.cut_off}</Row>
            <Row symbol={dot(COLORS.communities.reachable)}>{C.legend.communities.reachable}</Row>
            <Row symbol={dot(COLORS.communities.unknown)}>{C.legend.communities.unknown}</Row>
            <Row symbol={swatch(COLORS.unknown, 0.5)}>{C.legend.grey}</Row>
          </ul>
        </div>
      )}
    </div>
  );
}
