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
  roads: [LAYER_IDS.roads, LAYER_IDS.roadsCasing, LAYER_IDS.roadsRisk, LAYER_IDS.roadsBlocked],
  communities: [LAYER_IDS.communities, LAYER_IDS.communitiesTriangle],
  unknown: [LAYER_IDS.unknown],
};

const ICON_PX = 28;

/** Small pictures drawn here (no image files): a triangle for possibly-cut-off places and a hatch for unseen ground. */
function addIcons(map: MapLibreMap) {
  const canvas = document.createElement('canvas');
  canvas.width = canvas.height = ICON_PX;
  const ctx = canvas.getContext('2d');
  if (!ctx) return;
  ctx.beginPath();
  ctx.moveTo(ICON_PX / 2, 4);
  ctx.lineTo(ICON_PX - 4, ICON_PX - 5);
  ctx.lineTo(4, ICON_PX - 5);
  ctx.closePath();
  ctx.fillStyle = COLORS.ink;
  ctx.fill();
  ctx.lineWidth = 2;
  ctx.strokeStyle = '#ffffff';
  ctx.stroke();
  map.addImage('triangle', ctx.getImageData(0, 0, ICON_PX, ICON_PX), { pixelRatio: 2 });
  ctx.clearRect(0, 0, ICON_PX, ICON_PX);
  ctx.strokeStyle = COLORS.unknown;
  ctx.lineWidth = 2;
  for (const o of [-ICON_PX, 0, ICON_PX]) {
    ctx.beginPath();
    ctx.moveTo(o, ICON_PX);
    ctx.lineTo(o + ICON_PX, 0);
    ctx.stroke();
  }
  map.addImage('hatch', ctx.getImageData(0, 0, ICON_PX, ICON_PX), { pixelRatio: 2 });
}

function addVectorLayers(map: MapLibreMap) {
  addIcons(map);
  for (const id of [SOURCE_IDS.unknown, SOURCE_IDS.landslides, SOURCE_IDS.roads, SOURCE_IDS.communities]) {
    map.addSource(id, { type: 'geojson', data: EMPTY as never });
  }
  map.addLayer({ id: LAYER_IDS.unknown, type: 'fill', source: SOURCE_IDS.unknown, paint: { 'fill-pattern': 'hatch', 'fill-opacity': 0.7 } });
  map.addLayer({
    id: LAYER_IDS.landslides, type: 'fill', source: SOURCE_IDS.landslides,
    paint: { 'fill-color': COLORS.landslide, 'fill-opacity': ['match', ['get', 'confidence'], 'high', 0.85, 'medium', 0.65, 0.4] },
  });
  map.addLayer({
    id: LAYER_IDS.landslidesOutline, type: 'line', source: SOURCE_IDS.landslides,
    paint: { 'line-color': COLORS.landslideOutline, 'line-width': 1 },
  });
  const status = (s: string) => ['==', ['get', 'status'], s] as never;
  const width = ['case', ['==', ['get', 'highway'], 'primary'], 2.5, ['==', ['get', 'highway'], 'trunk'], 2.5, 1.2] as never;
  // open and unknown roads: grey, solid (unknown is lighter)
  map.addLayer({
    id: LAYER_IDS.roads, type: 'line', source: SOURCE_IDS.roads, filter: ['in', ['get', 'status'], ['literal', ['clear', 'unknown']]] as never,
    paint: { 'line-color': ['match', ['get', 'status'], 'unknown', COLORS.roads.unknown, COLORS.roads.clear] as never, 'line-width': width },
  });
  // a dark casing keeps the amber lines readable on bright radar images
  map.addLayer({
    id: LAYER_IDS.roadsCasing, type: 'line', source: SOURCE_IDS.roads, filter: ['in', ['get', 'status'], ['literal', ['blocked', 'at_risk']]] as never,
    paint: { 'line-color': COLORS.ink, 'line-width': 6 },
  });
  map.addLayer({
    id: LAYER_IDS.roadsRisk, type: 'line', source: SOURCE_IDS.roads, filter: status('at_risk'), layout: { 'line-cap': 'round' },
    paint: { 'line-color': COLORS.roads.at_risk, 'line-width': 3, 'line-dasharray': [0.1, 2] },
  });
  map.addLayer({
    id: LAYER_IDS.roadsBlocked, type: 'line', source: SOURCE_IDS.roads, filter: status('blocked'),
    paint: { 'line-color': COLORS.roads.blocked, 'line-width': 4, 'line-dasharray': [2, 1.2] },
  });
  // reachable: hollow circle; unknown: grey dot; possibly cut off: amber ring with a triangle on top
  map.addLayer({
    id: LAYER_IDS.communities, type: 'circle', source: SOURCE_IDS.communities,
    paint: {
      'circle-radius': ['match', ['get', 'status'], 'cut_off', 11, 'unknown', 3.5, 4.5] as never,
      'circle-color': ['match', ['get', 'status'], 'unknown', COLORS.communities.unknown, '#ffffff'] as never,
      'circle-opacity': ['match', ['get', 'status'], 'cut_off', 0.25, 'unknown', 1, 0.9] as never,
      'circle-stroke-color': ['match', ['get', 'status'], 'cut_off', COLORS.amber, 'unknown', '#ffffff', COLORS.ink] as never,
      'circle-stroke-width': ['match', ['get', 'status'], 'cut_off', 3, 'unknown', 1, 1.5] as never,
    },
  });
  map.addLayer({
    id: LAYER_IDS.communitiesTriangle, type: 'symbol', source: SOURCE_IDS.communities, filter: status('cut_off'),
    layout: { 'icon-image': 'triangle', 'icon-allow-overlap': true, 'icon-ignore-placement': true },
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
  el.className = 'pointer-events-none flex flex-col items-center text-[11px] font-semibold text-[#0B1E3A]';
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
  const { layers, pairId, select, compareMode, radarOpacity } = useApp();
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

  // the image for this side: radar or optical, depending on the compare mode
  const optical = event?.optical ?? null;
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !loaded || !pair) return;
    const mode = optical ? compareMode : 'radar';
    const useOptical = mode === 'optical' || (mode === 'mixed' && side === 'before');
    const url = useOptical && optical
      ? assetUrl(side === 'before' && mode === 'optical' ? optical.before_webp : optical.after_webp)
      : assetUrl(side === 'before' ? pair.before_png : pair.after_png);
    setImage(map, SOURCE_IDS.hv, url, useOptical && optical ? optical.bounds : pair.bounds, radarOpacity);
    if (side === 'after') setImage(map, SOURCE_IDS.change, assetUrl(pair.change_png), pair.bounds, 0.8);
    // opacity is applied by the next effect
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loaded, pair, side, compareMode, optical]);

  useEffect(() => {
    const map = mapRef.current;
    if (map && loaded && map.getLayer(LAYER_IDS.hv)) map.setPaintProperty(LAYER_IDS.hv, 'raster-opacity', radarOpacity);
  }, [loaded, radarOpacity, pair, compareMode]);

  // layer toggles (also re-applied after images are added)
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !loaded) return;
    for (const [key, ids] of Object.entries(LAYER_GROUPS) as [LayerKey, string[]][]) {
      for (const id of ids) if (map.getLayer(id)) map.setLayoutProperty(id, 'visibility', layers[key] ? 'visible' : 'none');
    }
  }, [loaded, layers, pair, compareMode]);

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
