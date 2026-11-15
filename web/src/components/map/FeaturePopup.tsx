import type { Map as MapLibreMap } from 'maplibre-gl';
import { useEffect, useState, type ReactNode } from 'react';
import { useApp, type Picked } from '../../lib/AppState.tsx';
import { C, fill } from '../../lib/content.ts';
import { fmtArea, fmtDb, fmtNumber } from '../../lib/format.ts';

const WIDTH_PX = 256;
const EDGE_PX = 8;
const GAP_PX = 12;
const FLIP_BELOW_PX = 200; // not enough room above the point: open below it

/** The text of a popup. Always rendered as React text: never as HTML, because feature names come from OpenStreetMap. */
export function popupContent(p: Picked): { title: string; lines: string[] } {
  const S = C.popups;
  switch (p.kind) {
    case 'landslide': {
      const l = p.props;
      return {
        title: fill(S.landslide.title, { id: l.id }),
        lines: [
          fill(S.landslide.area, { area: fmtArea(l.area_m2) }),
          fill(S.landslide.hv, { before: fmtDb(l.hv_before_db), after: fmtDb(l.hv_after_db), dhv: fmtDb(l.dhv_db) }),
          fill(S.landslide.slope, { slope: fmtNumber(l.slope_deg, 0) }),
          fill(S.landslide.seen, { pairs_seen: l.pairs_seen, pairs_visible: l.pairs_visible }),
          fill(S.landslide.confidence, { confidence: C.landslides.supportLabels[l.confidence] }),
        ],
      };
    }
    case 'road': {
      const r = p.props;
      const lines = [
        ...(r.highway ? [fill(S.road.type, { highway: r.highway })] : []),
        S.status[r.status],
        ...(r.min_distance_m !== null ? [fill(S.road.nearest, { distance: fmtNumber(r.min_distance_m, 0) })] : []),
        ...(r.landslide_ids ? [fill(S.road.ids, { ids: r.landslide_ids.split(',').join(', ') })] : []),
      ];
      return { title: r.name ?? S.road.unnamed, lines };
    }
    case 'community': {
      const c = p.props;
      return {
        title: c.name,
        lines: [
          `${c.place}${c.population !== null ? fill(S.community.population, { n: fmtNumber(c.population) }) : ''}`,
          S.status[c.status],
          c.reason,
          ...(c.nearest_hub ? [fill(S.community.hub, { hub: c.nearest_hub })] : []),
        ],
      };
    }
  }
}

function Box({ children }: { children: ReactNode }) {
  return <div className="space-y-0.5 text-[13px] leading-snug">{children}</div>;
}

/** A small card pinned to the selected feature. Follows the map as it moves; Escape or the close button dismisses it. */
export function FeaturePopup({ map }: { map: MapLibreMap | null }) {
  const { selected, select } = useApp();
  const [at, setAt] = useState<{ x: number; y: number; width: number } | null>(null);

  useEffect(() => {
    if (!map || !selected) {
      setAt(null);
      return;
    }
    const update = () => {
      const p = map.project(selected.lngLat);
      setAt({ x: p.x, y: p.y, width: map.getContainer().clientWidth });
    };
    update();
    map.on('move', update);
    map.on('resize', update);
    return () => {
      map.off('move', update);
      map.off('resize', update);
    };
  }, [map, selected]);

  useEffect(() => {
    if (!selected) return;
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && select(null);
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [selected, select]);

  if (!selected || !at) return null;
  const { title, lines } = popupContent(selected);
  const left = Math.min(Math.max(at.x, WIDTH_PX / 2 + EDGE_PX), Math.max(at.width - WIDTH_PX / 2 - EDGE_PX, WIDTH_PX / 2 + EDGE_PX));
  const below = at.y < FLIP_BELOW_PX;

  return (
    <div
      role="dialog"
      aria-label={title}
      className="absolute z-20 rounded-md border border-slate-300 bg-white p-3 pr-8 shadow-lg"
      style={{
        width: WIDTH_PX,
        left,
        top: at.y,
        transform: below ? `translate(-50%, ${GAP_PX}px)` : `translate(-50%, calc(-100% - ${GAP_PX}px))`,
      }}
    >
      <button
        type="button"
        aria-label={C.popups.close}
        onClick={() => select(null)}
        className="absolute right-1 top-1 h-6 w-6 rounded text-slate-600 hover:bg-slate-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-500"
      >
        <span aria-hidden="true">×</span>
      </button>
      <Box>
        <p className="text-sm font-semibold">{title}</p>
        {lines.map((l) => (
          <p key={l}>{l}</p>
        ))}
      </Box>
    </div>
  );
}
