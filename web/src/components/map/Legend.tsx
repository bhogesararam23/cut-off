import { useState, type ReactNode } from 'react';
import { C } from '../../lib/content.ts';
import { COLORS } from '../../lib/mapStyle.ts';
import { DESKTOP_QUERY } from '../../lib/useMedia.ts';
import { StatusSymbol } from '../panel/Access.tsx';

function Row({ symbol, children }: { symbol: ReactNode; children: ReactNode }) {
  return (
    <li className="flex items-start gap-2">
      <span aria-hidden="true" className="mt-0.5 flex h-4 w-8 shrink-0 items-center justify-center">{symbol}</span>
      <span>{children}</span>
    </li>
  );
}

const line = (color: string, dash?: string, cased = false) => (
  <svg width="32" height="10" viewBox="0 0 32 10">
    {cased && <line x1="1" y1="5" x2="31" y2="5" stroke={COLORS.ink} strokeWidth="6" />}
    <line x1="1" y1="5" x2="31" y2="5" stroke={color} strokeWidth="3" strokeDasharray={dash} strokeLinecap={dash === '0.1 5' ? 'round' : undefined} />
  </svg>
);
const hatch = (
  <svg width="24" height="12" viewBox="0 0 24 12">
    <rect width="24" height="12" fill="#fff" stroke={COLORS.unknown} />
    <path d="M-2 12 L10 0 M6 12 L18 0 M14 12 L26 0" stroke={COLORS.unknown} strokeWidth="2" />
  </svg>
);

/** Explains the patterns and colours on the map. Open on larger screens, closed on phones; a button toggles it. */
export function Legend() {
  const [open, setOpen] = useState(() => window.matchMedia(DESKTOP_QUERY).matches);
  return (
    <div className="absolute bottom-6 left-2 z-10 max-w-[18rem] rounded-card border border-ink/20 bg-white/95 text-xs">
      <button
        type="button"
        aria-expanded={open}
        aria-controls="legend-list"
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between gap-3 rounded-card px-3 py-1.5 text-sm font-semibold"
      >
        {C.legend.title}
        <span aria-hidden="true">{open ? '▾' : '▸'}</span>
      </button>
      {open && (
        <ul id="legend-list" className="space-y-1 px-2 pb-2">
          <Row symbol={<span className="block h-3 w-6 rounded-sm border" style={{ backgroundColor: COLORS.landslide, borderColor: COLORS.landslideOutline }} />}>{C.legend.landslide}</Row>
          <Row symbol={line(COLORS.roads.blocked, '7 4', true)}>{C.legend.roads.blocked} (dashed)</Row>
          <Row symbol={line(COLORS.roads.at_risk, '0.1 5', true)}>{C.legend.roads.at_risk} (dotted)</Row>
          <Row symbol={line(COLORS.roads.clear)}>{C.legend.roads.clear} (solid grey)</Row>
          <Row symbol={<StatusSymbol status="cut_off" />}>{C.legend.communities.cut_off} (triangle)</Row>
          <Row symbol={<StatusSymbol status="reachable" />}>{C.legend.communities.reachable} (hollow circle)</Row>
          <Row symbol={<StatusSymbol status="unknown" />}>{C.legend.communities.unknown} (grey dot)</Row>
          <Row symbol={hatch}>{C.legend.grey}</Row>
          <Row symbol={<span className="block h-3 w-6 bg-gradient-to-r from-black to-white ring-1 ring-slate-400" />}>{C.legend.radar}</Row>
          <Row symbol={<span className="block h-3 w-6 bg-gradient-to-r from-red-600 to-blue-600" />}>{C.legend.change}</Row>
        </ul>
      )}
    </div>
  );
}
