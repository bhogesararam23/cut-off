import { useMemo } from 'react';
import { useApp } from '../../lib/AppState.tsx';
import { C, fill } from '../../lib/content.ts';
import { ready, useData } from '../../lib/DataContext.tsx';
import { fmtNumber } from '../../lib/format.ts';
import { groupCommunities, roadKmByStatus } from '../../lib/lists.ts';
import { COLORS } from '../../lib/mapStyle.ts';
import type { CommunityStatus } from '../../lib/types.ts';
import { FileError } from '../FileError.tsx';
import { Skeleton } from '../Skeleton.tsx';

const GROUPS: CommunityStatus[] = ['cut_off', 'unknown', 'reachable'];

/** Same symbols as the map: a ringed red dot for possibly cut off, so colour is never the only signal. */
function StatusDot({ status }: { status: CommunityStatus }) {
  const ringed = status === 'cut_off';
  return (
    <svg aria-hidden="true" width="18" height="18" viewBox="0 0 20 20" className="shrink-0">
      {ringed && <circle cx="10" cy="10" r="8.5" fill="none" stroke={COLORS.communities.cut_off} strokeWidth="2" />}
      <circle cx="10" cy="10" r="5" fill={COLORS.communities[status]} stroke="#fff" strokeWidth={ringed ? 2 : 1} />
    </svg>
  );
}

export function Access() {
  const { communities, roads } = useData();
  const { focusFeature, selected } = useApp();
  const comms = ready(communities);
  const roadData = ready(roads);

  const groups = useMemo(() => (comms ? groupCommunities(comms) : null), [comms]);
  const km = useMemo(() => (roadData && roadData.features.length ? roadKmByStatus(roadData) : null), [roadData]);

  return (
    <section aria-labelledby="access-h" className="space-y-3">
      <h2 id="access-h" className="text-lg font-semibold">{C.access.heading}</h2>
      <p className="text-[15px]">{fill(C.access.intro, { hubs: C.access.hubs.join(', ') })}</p>

      {communities.status === 'loading' && <Skeleton className="h-32" />}
      {communities.status === 'error' && <FileError file={communities.file} />}
      {comms && comms.features.length === 0 && <p className="text-[15px] text-slate-700">{C.access.empty}</p>}
      {groups &&
        GROUPS.map((status) =>
          groups[status].length === 0 ? null : (
            <div key={status}>
              <h3 className="mb-1 text-[15px] font-semibold">{fill(C.access.groups[status], { n: fmtNumber(groups[status].length) })}</h3>
              <ul className="divide-y divide-slate-200 rounded border border-slate-200 bg-white">
                {groups[status].map((f, i) => {
                  const p = f.properties;
                  const isSelected = selected?.kind === 'community' && selected.props.name === p.name && selected.props.osm_id === p.osm_id;
                  return (
                    <li key={`${p.osm_id ?? p.name}-${i}`}>
                      <button
                        type="button"
                        aria-pressed={isSelected}
                        onClick={() => focusFeature({ kind: 'community', props: p, lngLat: f.geometry.coordinates })}
                        className={`flex w-full items-start gap-2 px-3 py-2 text-left text-sm hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-sky-500 ${isSelected ? 'bg-sky-50' : ''}`}
                      >
                        <StatusDot status={status} />
                        <span>{fill(C.access.row, { name: p.name, place: p.place, reason: p.reason })}</span>
                      </button>
                    </li>
                  );
                })}
              </ul>
            </div>
          ),
        )}

      {roads.status === 'error' && <FileError file={roads.file} />}
      {km && (
        <p className="text-[15px]">
          {fill(C.access.roadsSummary, {
            blocked_km: fmtNumber(km.blocked, 1), at_risk_km: fmtNumber(km.at_risk, 1),
            clear_km: fmtNumber(km.clear, 1), unknown_km: fmtNumber(km.unknown, 1),
          })}
        </p>
      )}

      <h3 className="pt-2 text-[15px] font-semibold">{C.access.realityHeading}</h3>
      <p className="text-[15px]">{C.access.realityText}</p>
    </section>
  );
}
