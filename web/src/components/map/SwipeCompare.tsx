import type { Map as MapLibreMap } from 'maplibre-gl';
import { useCallback, useEffect, useRef, useState, type KeyboardEvent, type PointerEvent } from 'react';
import { useApp } from '../../lib/AppState.tsx';
import { C, fill } from '../../lib/content.ts';
import { ready, useData } from '../../lib/DataContext.tsx';
import { fmtDayYear, hoursBetween } from '../../lib/format.ts';
import { FIT_PADDING_PX, FLY_MIN_ZOOM, FLY_MS } from '../../lib/mapStyle.ts';
import { FeaturePopup } from './FeaturePopup.tsx';
import { MapCanvas } from './MapCanvas.tsx';

const START_PCT = 50;
const KEY_STEP_PCT = 5;
const FULL_PCT = 100;
const SAME_DAY_HOURS = 24; // "N hours after the quake" is only said for a pass within a day of the quake

/** Keep two maps looking at the same place. Returns a function that stops the syncing. */
function syncCameras(a: MapLibreMap, b: MapLibreMap): () => void {
  let busy = false;
  const follow = (from: MapLibreMap, to: MapLibreMap) => () => {
    if (busy) return;
    busy = true; // jumpTo fires 'move' on the other map straight away: this flag stops it echoing back
    to.jumpTo({ center: from.getCenter(), zoom: from.getZoom(), bearing: from.getBearing(), pitch: from.getPitch() });
    busy = false;
  };
  const ab = follow(a, b);
  const ba = follow(b, a);
  a.on('move', ab);
  b.on('move', ba);
  return () => {
    a.off('move', ab);
    b.off('move', ba);
  };
}

/** Before and after radar images side by side: drag the divider (mouse, touch or arrow keys) to compare. */
export function SwipeCompare({ onAfterMap }: { onAfterMap?: (map: MapLibreMap | null) => void }) {
  const { event, pairs } = useData();
  const { pairId, flyNonce, fitNonce, selected, compareMode } = useApp();
  const [pct, setPct] = useState(START_PCT);
  const [before, setBefore] = useState<MapLibreMap | null>(null);
  const [after, setAfter] = useState<MapLibreMap | null>(null);
  const box = useRef<HTMLDivElement>(null);
  const dragging = useRef(false);

  const list = ready(pairs);
  const pair = list?.find((p) => p.id === pairId) ?? list?.[0];
  const e = ready(event);

  useEffect(() => {
    if (!before || !after) return;
    return syncCameras(before, after);
  }, [before, after]);

  const setAfterMap = useCallback((m: MapLibreMap | null) => {
    setAfter(m);
    onAfterMap?.(m);
  }, [onAfterMap]);

  // picking a feature in a list: fly there (the other map follows)
  useEffect(() => {
    if (!flyNonce || !selected || !after) return;
    const target = { center: selected.lngLat, zoom: Math.max(after.getZoom(), FLY_MIN_ZOOM) };
    // people who ask for less motion get an instant jump instead of a flight
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) after.jumpTo(target);
    else after.flyTo({ ...target, duration: FLY_MS });
    // only a new request moves the camera, not later selection changes
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [flyNonce]);

  // a guided step asks for the whole area again
  useEffect(() => {
    if (!fitNonce || !after || !e) return;
    const [w, s, ea, n] = e.bbox;
    after.fitBounds([[w, s], [ea, n]], { padding: FIT_PADDING_PX, duration: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 0 : FLY_MS });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fitNonce]);

  const clamp = (v: number) => Math.min(FULL_PCT, Math.max(0, v));
  const moveTo = (clientX: number) => {
    const r = box.current?.getBoundingClientRect();
    if (!r || r.width === 0) return;
    setPct(clamp(((clientX - r.left) / r.width) * FULL_PCT));
  };
  // Pointer events cover mouse, touch and pen. A ref (not capture state) says whether a drag is under way.
  const onPointerDown = (ev: PointerEvent<HTMLDivElement>) => {
    dragging.current = true;
    try {
      ev.currentTarget.setPointerCapture(ev.pointerId); // keeps events coming when the finger leaves the handle
    } catch {
      /* not an active pointer: the drag still works while it stays over the handle */
    }
    moveTo(ev.clientX);
  };
  const onPointerMove = (ev: PointerEvent<HTMLDivElement>) => {
    if (dragging.current) moveTo(ev.clientX);
  };
  const endDrag = () => {
    dragging.current = false;
  };
  const onKeyDown = (ev: KeyboardEvent<HTMLDivElement>) => {
    const step = ev.key === 'ArrowLeft' ? -KEY_STEP_PCT : ev.key === 'ArrowRight' ? KEY_STEP_PCT : null;
    if (step !== null) setPct((p) => clamp(p + step));
    else if (ev.key === 'Home') setPct(0);
    else if (ev.key === 'End') setPct(FULL_PCT);
    else return;
    ev.preventDefault();
  };

  const hours = e && pair ? hoursBetween(e.time_utc, pair.after) : null;
  const mode = e?.optical ? compareMode : 'radar';
  const radarAfter = pair
    ? hours !== null && hours >= 0 && hours < SAME_DAY_HOURS
      ? fill(C.swipe.afterHours, { date: fmtDayYear(pair.after), hours })
      : fill(C.swipe.after, { date: fmtDayYear(pair.after) })
    : null;
  const beforeLabel = !pair ? null : mode === 'radar' ? fill(C.swipe.before, { date: fmtDayYear(pair.before) }) : mode === 'optical' ? C.explorer.opticalBefore : C.explorer.opticalAfter;
  const afterLabel = mode === 'optical' ? C.explorer.opticalAfter : radarAfter;

  return (
    <div ref={box} className="absolute inset-0 overflow-hidden">
      <MapCanvas side="before" onMap={setBefore} />
      {/* the "after" map sits on top, clipped from the divider to the right edge */}
      <div className="absolute inset-0" style={{ clipPath: `inset(0 0 0 ${pct}%)` }}>
        <MapCanvas side="after" onMap={setAfterMap} />
      </div>

      <FeaturePopup map={after} />

      {pair && (
        <>
          <p className="pointer-events-none absolute left-2 top-2 z-10 rounded bg-slate-900/75 px-2 py-0.5 text-xs font-medium text-white">
            {beforeLabel}
          </p>
          <p className="pointer-events-none absolute right-12 top-2 z-10 max-w-[55%] rounded bg-slate-900/75 px-2 py-0.5 text-right text-xs font-medium text-white">
            {afterLabel}
          </p>
        </>
      )}

      {/* wide transparent grab area (easy to hit with a finger) around a thin white bar and a round handle */}
      <div
        role="slider"
        tabIndex={0}
        aria-label={C.swipe.handle}
        aria-orientation="horizontal"
        aria-valuemin={0}
        aria-valuemax={FULL_PCT}
        aria-valuenow={Math.round(pct)}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={endDrag}
        onPointerCancel={endDrag}
        onLostPointerCapture={endDrag}
        onKeyDown={onKeyDown}
        className="group absolute inset-y-0 z-10 flex w-11 -translate-x-1/2 cursor-ew-resize touch-none justify-center focus-visible:outline-none"
        style={{ left: `${pct}%` }}
      >
        <span aria-hidden="true" className="h-full w-1 bg-white shadow-[0_0_3px_rgba(0,0,0,0.6)]" />
        <span
          aria-hidden="true"
          className="absolute top-1/2 flex h-9 w-9 -translate-y-1/2 items-center justify-center rounded-full border-2 border-slate-700 bg-white text-sm text-slate-800 shadow group-focus-visible:ring-4 group-focus-visible:ring-sky-500"
        >
          ◀▶
        </span>
      </div>
    </div>
  );
}
