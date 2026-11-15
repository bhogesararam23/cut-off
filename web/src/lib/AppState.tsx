import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react';
import type { TabId } from './content.ts';
import type { CommunityProps, LandslideProps, PairId, RoadProps } from './types.ts';

export type LayerKey = 'radar' | 'change' | 'landslides' | 'roads' | 'communities' | 'unknown';
export type Layers = Record<LayerKey, boolean>;
/** What the two sides of the compare slider show. */
export type CompareMode = 'radar' | 'optical' | 'mixed';

export const DEFAULT_LAYERS: Layers = {
  radar: true, change: false, landslides: true, roads: true, communities: true, unknown: true,
};
export const DEFAULT_RADAR_OPACITY = 0.9;

/** Layers shown by each guided step. Clicking a step applies these; nothing advances by itself. */
export const STEP_LAYERS: Record<TabId, Layers> = {
  happened: { radar: true, change: false, landslides: false, roads: false, communities: false, unknown: false },
  slopes: { radar: true, change: true, landslides: true, roads: false, communities: false, unknown: true },
  roads: { radar: true, change: false, landslides: true, roads: true, communities: false, unknown: false },
  access: { radar: true, change: false, landslides: true, roads: true, communities: true, unknown: false },
  sure: DEFAULT_LAYERS,
  limits: DEFAULT_LAYERS,
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
  /** go to a guided step: sets its layers and resets the camera to the whole area */
  setTab: (t: TabId) => void;
  layers: Layers;
  toggleLayer: (k: LayerKey) => void;
  compareMode: CompareMode;
  setCompareMode: (m: CompareMode) => void;
  radarOpacity: number;
  setRadarOpacity: (v: number) => void;
  /** the feature whose popup is open */
  selected: Picked | null;
  select: (p: Picked | null) => void;
  /** picking from a list: select it and ask the map to go there. `flyNonce` changes on every request. */
  focusFeature: (p: Picked) => void;
  flyNonce: number;
  /** changes when the map should show the whole area again */
  fitNonce: number;
  aboutOpen: boolean;
  setAboutOpen: (open: boolean) => void;
  sheetOpen: boolean;
  setSheetOpen: (open: boolean) => void;
}

const Ctx = createContext<AppState | null>(null);

export function AppStateProvider({ children }: { children: ReactNode }) {
  const [pairId, setPairId] = useState<PairId | null>(null);
  const [tab, setTabState] = useState<TabId>('happened');
  const [layers, setLayers] = useState(STEP_LAYERS.happened);
  const [compareMode, setCompareMode] = useState<CompareMode>('radar');
  const [radarOpacity, setRadarOpacity] = useState(DEFAULT_RADAR_OPACITY);
  const [selected, select] = useState<Picked | null>(null);
  const [flyNonce, setFlyNonce] = useState(0);
  const [fitNonce, setFitNonce] = useState(0);
  const [aboutOpen, setAboutOpen] = useState(false);
  const [sheetOpen, setSheetOpen] = useState(false);

  const toggleLayer = useCallback((k: LayerKey) => setLayers((l) => ({ ...l, [k]: !l[k] })), []);
  const setTab = useCallback((t: TabId) => {
    setTabState(t);
    setLayers(STEP_LAYERS[t]);
    select(null);
    setFitNonce((n) => n + 1);
  }, []);
  const focusFeature = useCallback((p: Picked) => {
    select(p);
    setFlyNonce((n) => n + 1);
    setSheetOpen(false); // on a phone, reveal the map
  }, []);

  const value = useMemo(
    () => ({
      pairId, setPairId, tab, setTab, layers, toggleLayer, compareMode, setCompareMode, radarOpacity, setRadarOpacity,
      selected, select, focusFeature, flyNonce, fitNonce, aboutOpen, setAboutOpen, sheetOpen, setSheetOpen,
    }),
    [pairId, tab, setTab, layers, toggleLayer, compareMode, radarOpacity, selected, focusFeature, flyNonce, fitNonce, aboutOpen, sheetOpen],
  );
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useApp(): AppState {
  const v = useContext(Ctx);
  if (!v) throw new Error('useApp must be used inside AppStateProvider');
  return v;
}
