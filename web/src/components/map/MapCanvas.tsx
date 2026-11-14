import {
  Map as MapLibreMap, Marker, NavigationControl, type GeoJSONSource, type ImageSource, type PointLike,
} from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { useEffect, useRef, useState } from 'react';
import { useApp, type LayerKey } from '../../lib/AppState.tsx';
import { C } from '../../lib/content.ts';
import { assetUrl } from '../../lib/data.ts';
import { ready, useData } from '../../lib/DataContext.tsx';
import { expandBBox } from '../../lib/geo.ts';
import { BASE_STYLE, BOUNDS_MARGIN_DEG, CLICKABLE, COLORS, FIT_PADDING_PX, LAYER_IDS, SOURCE_IDS } from '../../lib/mapStyle.ts';
import '../../lib/mapWorker.ts';
import { toPicked } from '../../lib/pick.ts';
import type { Pair } from '../../lib/types.ts';

export type Side = 'before' | 'after';

const HIT_RADIUS_PX = 6;
const EMPTY = { type: 'FeatureCollection', features: [] } as const;

/** Which style layers each toggle switches. */
const LAYER_GROUPS: Record<LayerKey, string[]> = {
  radar: [LAYER_IDS.hv],
  change: [LAYER_IDS.change],
  landslides: [LAYER_IDS.landslides, LAYER_IDS.landslidesOutline],
  roads: [LAYER_IDS.roads, LAYER_IDS.roadsBlocked],
  communities: [LAYER_IDS.communities, LAYER_IDS.communitiesRing],
  unknown: [LAYER_IDS.unknown],
};

function addVectorLayers(map: MapLibreMap) {
  for (const id of [SOURCE_IDS.unknown, SOURCE_IDS.landslides, SOURCE_IDS.roads, SOURCE_IDS.communities]) {
    map.addSource(id, { type: 'geojson', data: EMPTY as never });
  }
  map.addLayer({
    id: LAYER_IDS.unknown, type: 'fill', source: SOURCE_IDS.unknown,
    paint: { 'fill-color': COLORS.unknown, 'fill-opacity': 0.35 },
  });
  map.addLayer({
    id: LAYER_IDS.landslides, type: 'fill', source: SOURCE_IDS.landslides,
    paint: { 'fill-color': COLORS.landslide, 'fill-opacity': ['match', ['get', 'confidence'], 'high', 0.75, 'medium', 0.55, 0.3] },
  });
  map.addLayer({
    id: LAYER_IDS.landslidesOutline, type: 'line', source: SOURCE_IDS.landslides,
    paint: { 'line-color': COLORS.landslideOutline, 'line-width': 1 },
  });
  const roadColor = [
    'match', ['get', 'status'],
    'blocked', COLORS.roads.blocked, 'at_risk', COLORS.roads.at_risk, 'clear', COLORS.roads.clear, COLORS.roads.unknown,
  ] as never;
  const roadWidth = ['case', ['==', ['get', 'highway'], 'primary'], 3, 2] as never;
  map.addLayer({
    id: LAYER_IDS.roads, type: 'line', source: SOURCE_IDS.roads, filter: ['!=', ['get', 'status'], 'blocked'],
    paint: { 'line-color': roadColor, 'line-width': roadWidth },
  });
  map.addLayer({
    id: LAYER_IDS.roadsBlocked, type: 'line', source: SOURCE_IDS.roads, filter: ['==', ['get', 'status'], 'blocked'],
    paint: { 'line-color': COLORS.roads.blocked, 'line-width': ['case', ['==', ['get', 'highway'], 'primary'], 4, 3] as never, 'line-dasharray': [2, 1.5] },
  });
  map.addLayer({
    id: LAYER_IDS.communitiesRing, type: 'circle', source: SOURCE_IDS.communities, filter: ['==', ['get', 'status'], 'cut_off'],
    paint: { 'circle-radius': 11, 'circle-color': '#ffffff', 'circle-opacity': 0, 'circle-stroke-color': COLORS.communities.cut_off, 'circle-stroke-width': 2 },
  });
  map.addLayer({
    id: LAYER_IDS.communities, type: 'circle', source: SOURCE_IDS.communities,
    paint: {
      'circle-radius': 6,
      'circle-color': ['match', ['get', 'status'], 'cut_off', COLORS.communities.cut_off, 'reachable', COLORS.communities.reachable, COLORS.communities.unknown] as never,
      'circle-stroke-color': '#ffffff',
      'circle-stroke-width': ['case', ['==', ['get', 'status'], 'cut_off'], 3, 1.5] as never,
    },
  });
}

function setImage(map: MapLibreMap, id: string, url: string, coordinates: Pair['bounds'], opacity: number) {
  const source = map.getSource(id) as ImageSource | undefined;
  if (source) {
    source.updateImage({ url, coordinates });
    return;
  }
  map.addSource(id, { type: 'image', url, coordinates });
  map.addLayer({ id, type: 'raster', source: id, paint: { 'raster-opacity': opacity, 'raster-fade-duration': 0 } }, LAYER_IDS.unknown);
}

function epicentreMarker(): HTMLElement {
  const el = document.createElement('div');
  el.className = 'pointer-events-none flex flex-col items-center text-[11px] font-semibold text-slate-900';
  el.setAttribute('role', 'img');
  el.setAttribute('aria-label', C.legend.epicentre);
  const star = document.createElement('span');
  star.className = 'text-xl leading-none drop-shadow-[0_0_2px_#fff]';
  star.textContent = '★';
  const label = document.createElement('span');
  label.className = 'rounded bg-white/85 px-1';
  label.textContent = C.legend.epicentre;
  el.append(star, label);
  return el;
}

interface Props {
  side: Side;
  onMap: (map: MapLibreMap | null) => void;
}

/** One MapLibre map: basemap, the radar image for its side, and all vector layers. */
export function MapCanvas({ side, onMap }: Props) {
  const data = useData();
  const { layers, pairId, select } = useApp();
  const container = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const selectRef = useRef(select);
  selectRef.current = select;
  const [loaded, setLoaded] = useState(false);
  const [failed, setFailed] = useState(false);

  const event = ready(data.event);
  const pairs = ready(data.pairs);
  const pair = pairs?.find((p) => p.id === pairId) ?? pairs?.[0];

  // create the map once the event (and so the data box) is known
  useEffect(() => {
    if (!event || !container.current || mapRef.current) return;
    let map: MapLibreMap;
    try {
      const [w, s, e, n] = event.bbox;
      const [mw, ms, me, mn] = expandBBox(event.bbox, BOUNDS_MARGIN_DEG);
      map = new MapLibreMap({
        container: container.current,
        style: BASE_STYLE,
        bounds: [[w, s], [e, n]],
        fitBoundsOptions: { padding: FIT_PADDING_PX },
        maxBounds: [[mw, ms], [me, mn]],
        dragRotate: false,
        pitchWithRotate: false,
        touchPitch: false,
        attributionControl: { compact: true },
      });
    } catch {
      setFailed(true);
      return;
    }
    mapRef.current = map;
    map.touchZoomRotate.disableRotation();
    map.keyboard.disableRotation();
    map.addControl(new NavigationControl({ showCompass: false }), 'top-right');
    map.on('load', () => {
      addVectorLayers(map);
      new Marker({ element: epicentreMarker() }).setLngLat(event.epicentre).addTo(map);
      setLoaded(true);
    });

    const hit = (point: { x: number; y: number }) => {
      const box: [PointLike, PointLike] = [[point.x - HIT_RADIUS_PX, point.y - HIT_RADIUS_PX], [point.x + HIT_RADIUS_PX, point.y + HIT_RADIUS_PX]];
      const present = CLICKABLE.filter((id) => map.getLayer(id));
      return present.length ? map.queryRenderedFeatures(box, { layers: [...present] })[0] : undefined;
    };
    map.on('click', (e) => {
      const f = hit(e.point);
      const picked = f ? toPicked(f.layer.id, f.properties, [e.lngLat.lng, e.lngLat.lat]) : null;
      selectRef.current(picked);
    });
    map.on('mousemove', (e) => {
      map.getCanvas().style.cursor = hit(e.point) ? 'pointer' : '';
    });
    const resize = new ResizeObserver(() => map.resize());
    resize.observe(container.current);
    onMap(map);

    return () => {
      resize.disconnect();
      onMap(null);
      map.remove();
      mapRef.current = null;
      setLoaded(false);
    };
    // the map is created once per event; later changes are applied by the effects below
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [event?.event_id]);

  // vector data
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !loaded) return;
    const files = {
      [SOURCE_IDS.unknown]: ready(data.unknown), [SOURCE_IDS.landslides]: ready(data.landslides),
      [SOURCE_IDS.roads]: ready(data.roads), [SOURCE_IDS.communities]: ready(data.communities),
    };
    for (const [id, fc] of Object.entries(files)) if (fc) (map.getSource(id) as GeoJSONSource).setData(fc as never);
  }, [loaded, data.unknown, data.landslides, data.roads, data.communities]);

  // radar images for the selected pair
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !loaded || !pair) return;
    setImage(map, SOURCE_IDS.hv, assetUrl(side === 'before' ? pair.before_png : pair.after_png), pair.bounds, 0.9);
    if (side === 'after') setImage(map, SOURCE_IDS.change, assetUrl(pair.change_png), pair.bounds, 0.8);
  }, [loaded, pair, side]);

  // layer toggles (also re-applied after images are added)
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !loaded) return;
    for (const [key, ids] of Object.entries(LAYER_GROUPS) as [LayerKey, string[]][]) {
      for (const id of ids) if (map.getLayer(id)) map.setLayoutProperty(id, 'visibility', layers[key] ? 'visible' : 'none');
    }
  }, [loaded, layers, pair]);

  if (failed) {
    return (
      <p role="alert" className="absolute inset-0 flex items-center justify-center bg-slate-800 p-4 text-center text-sm text-white">
        {C.errors.map}
      </p>
    );
  }
  // MapLibre's own stylesheet makes its container position: relative, so the sizing lives on this wrapper
  return (
    <div className="absolute inset-0">
      <div ref={container} className="h-full w-full" />
    </div>
  );
}
