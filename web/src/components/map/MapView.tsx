import { Legend } from './Legend.tsx';
import { LayerToggles } from './LayerToggles.tsx';
import { SwipeCompare } from './SwipeCompare.tsx';

/** The swipe map with its legend and layer toggles. */
export function MapView() {
  return (
    <div className="absolute inset-0 overflow-hidden bg-slate-800">
      <SwipeCompare />
      <LayerToggles />
      <Legend />
    </div>
  );
}
