import { useMemo, useState } from 'react';
import { useApp } from '../../lib/AppState.tsx';
import { C, fill } from '../../lib/content.ts';
import { ready, useData } from '../../lib/DataContext.tsx';
import { fmtArea, fmtNumber } from '../../lib/format.ts';
import { representativePoint } from '../../lib/geo.ts';
import { filterLandslides, sortLandslides, type ConfidenceFilter, type SortKey } from '../../lib/lists.ts';
import { FileError } from '../FileError.tsx';
import { Skeleton } from '../Skeleton.tsx';

const MAX_ROWS = 200; // a long list slows phones down; the filters and sort narrow it

const selectClass =
  'rounded border border-slate-300 bg-white px-2 py-1 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-500';

export function Landslides() {
  const { landslides } = useData();
  const { focusFeature, selected } = useApp();
  const [filter, setFilter] = useState<ConfidenceFilter>('all');
  const [sort, setSort] = useState<SortKey>('size');
  const fc = ready(landslides);

  const rows = useMemo(() => (fc ? sortLandslides(filterLandslides(fc.features, filter), sort) : []), [fc, filter, sort]);
  const shown = rows.slice(0, MAX_ROWS);

  return (
    <section aria-labelledby="landslides-h" className="space-y-3">
      <h2 id="landslides-h" className="text-lg font-semibold">{C.landslides.heading}</h2>
      {landslides.status === 'loading' && <Skeleton className="h-32" />}
      {landslides.status === 'error' && <FileError file={landslides.file} />}
      {fc && (
        <>
          <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm">
            <label className="flex items-center gap-2">
              {C.landslides.filterLabel}
              <select value={filter} onChange={(e) => setFilter(e.target.value as ConfidenceFilter)} className={selectClass}>
                {(Object.keys(C.landslides.filters) as ConfidenceFilter[]).map((k) => (
                  <option key={k} value={k}>{C.landslides.filters[k]}</option>
                ))}
              </select>
            </label>
            <label className="flex items-center gap-2">
              {C.landslides.sortLabel}
              <select value={sort} onChange={(e) => setSort(e.target.value as SortKey)} className={selectClass}>
                {(Object.keys(C.landslides.sorts) as SortKey[]).map((k) => (
                  <option key={k} value={k}>{C.landslides.sorts[k]}</option>
                ))}
              </select>
            </label>
          </div>
          <p className="text-xs text-slate-600">{C.landslides.confidenceHelp}</p>

          {rows.length === 0 ? (
            <p className="text-[15px] text-slate-700">{C.landslides.empty}</p>
          ) : (
            <ul className="divide-y divide-slate-200 rounded border border-slate-200 bg-white">
              {shown.map((f) => {
                const p = f.properties;
                const isSelected = selected?.kind === 'landslide' && selected.props.id === p.id;
                return (
                  <li key={p.id}>
                    <button
                      type="button"
                      aria-pressed={isSelected}
                      onClick={() => focusFeature({ kind: 'landslide', props: p, lngLat: representativePoint(f.geometry) })}
                      className={`flex w-full items-center justify-between gap-2 px-3 py-2 text-left text-sm hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-sky-500 ${isSelected ? 'bg-sky-50' : ''}`}
                    >
                      <span>
                        {fill(C.landslides.row, { id: p.id, area: fmtArea(p.area_m2), pairs_seen: p.pairs_seen, pairs_visible: p.pairs_visible })}
                      </span>
                      <span className="shrink-0 rounded border border-slate-300 px-1.5 text-xs">{C.landslides.confidenceLabels[p.confidence]}</span>
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
          {rows.length > shown.length && (
            <p className="text-xs text-slate-600">{fill(C.landslides.showing, { shown: fmtNumber(shown.length), total: fmtNumber(rows.length) })}</p>
          )}
        </>
      )}
    </section>
  );
}
