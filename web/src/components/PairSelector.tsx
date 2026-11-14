import { useEffect } from 'react';
import { useApp } from '../lib/AppState.tsx';
import { C, fill } from '../lib/content.ts';
import { ready, useData } from '../lib/DataContext.tsx';
import { fmtDay } from '../lib/format.ts';
import type { Pair, PairId } from '../lib/types.ts';

export function pairLabel(p: Pair): string {
  return fill(C.topBar.pairOption, { track: p.track, direction: p.direction, before: fmtDay(p.before), after: fmtDay(p.after) });
}

/** Which radar pair the before/after images come from. Detections stay combined across pairs. */
export function PairSelector() {
  const { pairs } = useData();
  const { pairId, setPairId } = useApp();
  const list = ready(pairs);

  // default to the first pair in the file (the pipeline writes the primary pair first)
  useEffect(() => {
    if (list?.length && !list.some((p) => p.id === pairId)) setPairId(list[0].id);
  }, [list, pairId, setPairId]);

  if (!list?.length) return null;
  return (
    <label className="flex items-center gap-2 text-sm">
      <span className="hidden text-slate-600 sm:inline">{C.topBar.pairLabel}</span>
      <select
        value={pairId ?? list[0].id}
        onChange={(e) => setPairId(e.target.value as PairId)}
        aria-label={C.topBar.pairLabel}
        className="max-w-[11rem] rounded border border-slate-300 bg-white px-2 py-1 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-500 sm:max-w-none"
      >
        {list.map((p) => (
          <option key={p.id} value={p.id}>
            {pairLabel(p)}
          </option>
        ))}
      </select>
    </label>
  );
}
