import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react';
import type { TabId } from './content.ts';
import type { CommunityProps, LandslideProps, PairId, RoadProps } from './types.ts';

export type LayerKey = 'radar' | 'change' | 'landslides' | 'roads' | 'communities' | 'unknown';

export const DEFAULT_LAYERS: Record<LayerKey, boolean> = {
  radar: true, change: false, landslides: true, roads: true, communities: true, unknown: true,
};

/** A feature chosen on the map or in a list. Its popup is shown at `lngLat`. */
export type Picked =
  | { kind: 'landslide'; props: LandslideProps; lngLat: [number, number] }
  | { kind: 'road'; props: RoadProps; lngLat: [number, number] }
  | { kind: 'community'; props: CommunityProps; lngLat: [number, number] };

interface AppState {
  pairId: PairId | null;
  setPairId: (id: PairId) => void;
  tab: TabId;
  setTab: (t: TabId) => void;
  layers: Record<LayerKey, boolean>;
  toggleLayer: (k: LayerKey) => void;
  /** the feature whose popup is open */
  selected: Picked | null;
  select: (p: Picked | null) => void;
  /** picking from a list: select it and ask the map to fly there. `flyNonce` changes on every request. */
  focusFeature: (p: Picked) => void;
  flyNonce: number;
  aboutOpen: boolean;
  setAboutOpen: (open: boolean) => void;
  sheetOpen: boolean;
  setSheetOpen: (open: boolean) => void;
}

const Ctx = createContext<AppState | null>(null);

export function AppStateProvider({ children }: { children: ReactNode }) {
  const [pairId, setPairId] = useState<PairId | null>(null);
  const [tab, setTab] = useState<TabId>('overview');
  const [layers, setLayers] = useState(DEFAULT_LAYERS);
  const [selected, select] = useState<Picked | null>(null);
  const [flyNonce, setFlyNonce] = useState(0);
  const [aboutOpen, setAboutOpen] = useState(false);
  const [sheetOpen, setSheetOpen] = useState(false);

  const toggleLayer = useCallback((k: LayerKey) => setLayers((l) => ({ ...l, [k]: !l[k] })), []);
  const focusFeature = useCallback((p: Picked) => {
    select(p);
    setFlyNonce((n) => n + 1);
    setSheetOpen(false); // on a phone, reveal the map
  }, []);

  const value = useMemo(
    () => ({ pairId, setPairId, tab, setTab, layers, toggleLayer, selected, select, focusFeature, flyNonce, aboutOpen, setAboutOpen, sheetOpen, setSheetOpen }),
    [pairId, tab, layers, toggleLayer, selected, focusFeature, flyNonce, aboutOpen, sheetOpen],
  );
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useApp(): AppState {
  const v = useContext(Ctx);
  if (!v) throw new Error('useApp must be used inside AppStateProvider');
  return v;
}
