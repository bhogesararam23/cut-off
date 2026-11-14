import { useState } from 'react';
import { useApp, type LayerKey } from '../../lib/AppState.tsx';
import { C } from '../../lib/content.ts';
import { DESKTOP_QUERY } from '../../lib/useMedia.ts';

const KEYS: LayerKey[] = ['radar', 'change', 'landslides', 'roads', 'communities', 'unknown'];

/** Checkboxes that switch map layers on and off. Open on larger screens, closed on phones. */
export function LayerToggles() {
  const { layers, toggleLayer } = useApp();
  const [open, setOpen] = useState(() => window.matchMedia(DESKTOP_QUERY).matches);

  return (
    <div className="absolute left-2 top-2 z-10 max-w-[15rem] rounded-md bg-white/95 text-sm shadow">
      <button
        type="button"
        aria-expanded={open}
        aria-controls="layer-list"
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between gap-3 rounded-md px-3 py-1.5 font-semibold focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-500"
      >
        Layers
        <span aria-hidden="true">{open ? '▾' : '▸'}</span>
      </button>
      {open && (
        <fieldset id="layer-list" className="space-y-1 px-2 pb-2">
          <legend className="sr-only">Layers</legend>
          {KEYS.map((k) => (
            <label key={k} className="flex cursor-pointer items-center gap-2">
              <input
                type="checkbox"
                checked={layers[k]}
                onChange={() => toggleLayer(k)}
                className="h-4 w-4 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-500"
              />
              {C.layers[k]}
            </label>
          ))}
        </fieldset>
      )}
    </div>
  );
}
