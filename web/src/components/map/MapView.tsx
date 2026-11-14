import type { Map as MapLibreMap } from 'maplibre-gl';
import { useEffect, useRef } from 'react';
import { useApp } from '../../lib/AppState.tsx';
import { FLY_MIN_ZOOM } from '../../lib/mapStyle.ts';
import { Legend } from './Legend.tsx';
import { LayerToggles } from './LayerToggles.tsx';
import { MapCanvas } from './MapCanvas.tsx';

/** The map with its legend and layer toggles. */
export function MapView() {
  const { flyNonce, selected } = useApp();
  const map = useRef<MapLibreMap | null>(null);

  // picking a feature in a list: fly the map to it
  useEffect(() => {
    const m = map.current;
    if (!flyNonce || !selected || !m) return;
    m.flyTo({ center: selected.lngLat, zoom: Math.max(m.getZoom(), FLY_MIN_ZOOM) });
    // only a new request moves the camera, not later selection changes
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [flyNonce]);

  return (
    <div className="absolute inset-0 overflow-hidden bg-slate-800">
      <MapCanvas side="after" onMap={(m) => { map.current = m; }} />
      <LayerToggles />
      <Legend />
    </div>
  );
}
