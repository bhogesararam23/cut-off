import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react';
import type { TabId } from './content.ts';
import type { CommunityProps, LandslideProps, PairId, RoadProps } from './types.ts';

export type LayerKey = 'radar' | 'change' | 'landslides' | 'roads' | 'communities' | 'unknown';

export const DEFAULT_LAYERS: Record<LayerKey, boolean> = {
  radar: true, change: false, landslides: true, roads: true, communities: true, unknown: true,
};

/** A feature chosen in a list or on the map: the map flies to it and opens its popup. */
export type Picked =
  | { kind: 'landslide'; props: LandslideProps; lngLat: [number, number] }
  | { kind: 'road'; props: RoadProps; lngLat: [number, number] }
  | { kind: 'community'; props: CommunityProps; lngLat: [number, number] };

export interface FocusRequest {
  picked: Picked;
  /** changes on every request so the same feature can be picked twice */
  nonce: number;
}

interface AppState {
  pairId: PairId | null;
  setPairId: (id: PairId) => void;
  tab: TabId;
  setTab: (t: TabId) => void;
  layers: Record<LayerKey, boolean>;
  toggleLayer: (k: LayerKey) => void;
  focus: FocusRequest | null;
  focusFeature: (p: Picked) => void;
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
  const [focus, setFocus] = useState<FocusRequest | null>(null);
  const [aboutOpen, setAboutOpen] = useState(false);
  const [sheetOpen, setSheetOpen] = useState(false);

  const toggleLayer = useCallback((k: LayerKey) => setLayers((l) => ({ ...l, [k]: !l[k] })), []);
  const focusFeature = useCallback((picked: Picked) => {
    setFocus((f) => ({ picked, nonce: (f?.nonce ?? 0) + 1 }));
    setSheetOpen(false); // on a phone, reveal the map
  }, []);

  const value = useMemo(
    () => ({ pairId, setPairId, tab, setTab, layers, toggleLayer, focus, focusFeature, aboutOpen, setAboutOpen, sheetOpen, setSheetOpen }),
    [pairId, tab, layers, toggleLayer, focus, focusFeature, aboutOpen, sheetOpen],
  );
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useApp(): AppState {
  const v = useContext(Ctx);
  if (!v) throw new Error('useApp must be used inside AppStateProvider');
  return v;
}
