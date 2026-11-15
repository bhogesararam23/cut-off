import { useApp, type CompareMode } from '../../lib/AppState.tsx';
import { C } from '../../lib/content.ts';
import { ready, useData } from '../../lib/DataContext.tsx';
import { PairSelector } from '../PairSelector.tsx';
import { Legend } from './Legend.tsx';
import { LayerToggles } from './LayerToggles.tsx';
import { SwipeCompare } from './SwipeCompare.tsx';

const MODES: CompareMode[] = ['radar', 'optical', 'mixed'];
const OPACITY_STEP = 0.05;

/** Compare mode, radar pair and opacity. Plain form controls, so they work with a keyboard. */
function Controls() {
  const { compareMode, setCompareMode, radarOpacity, setRadarOpacity } = useApp();
  const { event } = useData();
  const hasOptical = !!ready(event)?.optical;
  const field = 'rounded-card border border-ink/30 bg-white px-2 py-1 text-sm';
  return (
    <div className="flex shrink-0 flex-wrap items-center gap-x-4 gap-y-2 border-b border-ink/15 bg-white px-3 py-2 text-sm">
      <label className="flex items-center gap-2">
        <span className="font-medium">{C.explorer.compare}</span>
        <select value={hasOptical ? compareMode : 'radar'} onChange={(e) => setCompareMode(e.target.value as CompareMode)} className={field}>
          {MODES.filter((m) => hasOptical || m === 'radar').map((m) => (
            <option key={m} value={m}>{C.explorer.modes[m]}</option>
          ))}
        </select>
      </label>
      <PairSelector />
      <label className="flex items-center gap-2">
        <span>{C.explorer.opacity}</span>
        <input type="range" min={0} max={1} step={OPACITY_STEP} value={radarOpacity} onChange={(e) => setRadarOpacity(Number(e.target.value))} className="w-24 accent-[#0B1E3A]" />
      </label>
    </div>
  );
}

/** The swipe map with its controls, legend and layer toggles. */
export function MapView() {
  return (
    <div className="absolute inset-0 flex flex-col bg-ink">
      <Controls />
      <div className="relative min-h-0 flex-1 overflow-hidden">
        <SwipeCompare />
        <LayerToggles />
        <Legend />
      </div>
    </div>
  );
}
