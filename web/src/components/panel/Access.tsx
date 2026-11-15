import { useMemo, useState } from 'react';
import { useApp } from '../../lib/AppState.tsx';
import { C, fill } from '../../lib/content.ts';
import { ready, useData } from '../../lib/DataContext.tsx';
import { fmtNumber } from '../../lib/format.ts';
import { groupCommunities } from '../../lib/lists.ts';
import type { CommunityStatus } from '../../lib/types.ts';
import { FileError } from '../FileError.tsx';
import { Skeleton } from '../Skeleton.tsx';

const GROUPS: CommunityStatus[] = ['cut_off', 'unknown', 'reachable'];
const MAX_ROWS = 60; // per group; the search box narrows the list

/** Same symbols as the map: triangle in an amber ring = possibly cut off, hollow circle = reachable, grey dot = unknown. */
export function StatusSymbol({ status }: { status: CommunityStatus }) {
  return (
    <svg aria-hidden="true" width="20" height="20" viewBox="0 0 20 20" className="shrink-0">
      {status === 'cut_off' && (
        <>
          <circle cx="10" cy="10" r="8.5" fill="none" stroke="#E8A33D" strokeWidth="2.5" />
          <path d="M10 5 L15 14 L5 14 Z" fill="#0B1E3A" />
        </>
      )}
      {status === 'reachable' && <circle cx="10" cy="10" r="5" fill="#fff" stroke="#0B1E3A" strokeWidth="2" />}
      {status === 'unknown' && <circle cx="10" cy="10" r="4" fill="#8A8F98" />}
    </svg>
  );
}

/** The community list. It is also the text alternative to the map: everything on the map is listed here. */
export function Access() {
  const { communities } = useData();
  const { focusFeature, selected } = useApp();
  const [query, setQuery] = useState('');
  const comms = ready(communities);

  const groups = useMemo(() => {
    if (!comms) return null;
    const q = query.trim().toLowerCase();
    const g = groupCommunities({ ...comms, features: q ? comms.features.filter((f) => f.properties.name.toLowerCase().includes(q)) : comms.features });
    // largest known population first, then by name
    for (const k of GROUPS) g[k].sort((a, b) => (b.properties.population ?? -1) - (a.properties.population ?? -1) || a.properties.name.localeCompare(b.properties.name));
    return g;
  }, [comms, query]);

  return (
    <section aria-labelledby="access-h" className="space-y-3">
      <h2 id="access-h" className="text-lg font-semibold">{C.access.heading}</h2>
      <p className="text-sm">{fill(C.access.intro, { hubs: C.access.hubs.join(', ') })}</p>
      <label className="block text-sm">
        <span className="sr-only">{C.explorer.search}</span>
        <input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={C.explorer.search}
          className="w-full rounded-card border border-ink/30 bg-white px-3 py-1.5"
        />
      </label>

      {communities.status === 'loading' && <Skeleton className="h-32" />}
      {communities.status === 'error' && <FileError file={communities.file} />}
      {comms && comms.features.length === 0 && <p className="text-sm">{C.access.empty}</p>}
      {groups &&
        GROUPS.map((status) =>
          groups[status].length === 0 ? null : (
            <div key={status}>
              <h3 className="mb-1 text-sm font-semibold">{fill(C.access.groups[status], { n: fmtNumber(groups[status].length) })}</h3>
              <ul className="divide-y divide-ink/10 rounded-card border border-ink/15 bg-white">
                {groups[status].slice(0, MAX_ROWS).map((f, i) => {
                  const p = f.properties;
                  const isSelected = selected?.kind === 'community' && selected.props.name === p.name && selected.props.osm_id === p.osm_id;
                  return (
                    <li key={`${p.osm_id ?? p.name}-${i}`}>
                      <button
                        type="button"
                        aria-pressed={isSelected}
                        onClick={() => focusFeature({ kind: 'community', props: p, lngLat: f.geometry.coordinates })}
                        className={`flex w-full items-start gap-2 px-3 py-2 text-left text-sm hover:bg-ink/5 ${isSelected ? 'bg-brand/20' : ''}`}
                      >
                        <StatusSymbol status={status} />
                        <span>
                          <span className="font-medium">{p.name}</span> · {p.place}
                          {p.population !== null && <span className="num"> · {fmtNumber(p.population)}</span>}
                          {status !== 'reachable' && <span className="block text-xs text-ink/75">{p.reason}</span>}
                        </span>
                      </button>
                    </li>
                  );
                })}
              </ul>
              {groups[status].length > MAX_ROWS && (
                <p className="mt-1 text-xs text-ink/70">{fill(C.landslides.showing, { shown: MAX_ROWS, total: fmtNumber(groups[status].length) })}</p>
              )}
            </div>
          ),
        )}

      <h3 className="pt-2 text-sm font-semibold">{C.access.realityHeading}</h3>
      <p className="text-sm">{C.access.realityText}</p>
    </section>
  );
}
