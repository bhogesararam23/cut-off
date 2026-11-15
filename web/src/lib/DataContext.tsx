import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from 'react';
import { FILES, getJson, type FileKey, type Loadable } from './data.ts';

type Spec = typeof FILES;
export type DataState = { [K in FileKey]: Loadable<NonNullable<Spec[K]['_type']>> };

const DataContext = createContext<DataState | null>(null);
const RequestMapData = createContext<() => void>(() => undefined);

// the four big map files are fetched only when the map is about to be seen; the key facts need none of them
const MAP_FILES: FileKey[] = ['landslides', 'unknown', 'roads', 'communities'];

const initial = Object.fromEntries(Object.keys(FILES).map((k) => [k, { status: 'loading' }])) as unknown as DataState;

/** Loads the files in parallel (the big map files once the map is near). Each file has its own loading/error state, so one bad file never blocks the rest. */
export function DataProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<DataState>(initial);
  const [mapWanted, setMapWanted] = useState(false);
  const loaded = useRef(new Set<FileKey>());
  const alive = useRef(true);

  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
    };
  }, []);

  useEffect(() => {
    (Object.keys(FILES) as FileKey[]).forEach((key) => {
      if (loaded.current.has(key) || (MAP_FILES.includes(key) && !mapWanted)) return;
      loaded.current.add(key);
      const { name, api } = FILES[key];
      getJson(name, api)
        .then((data) => alive.current && setState((s) => ({ ...s, [key]: { status: 'ready', data } })))
        .catch(() => alive.current && setState((s) => ({ ...s, [key]: { status: 'error', file: name } })));
    });
  }, [mapWanted]);

  const request = useCallback(() => setMapWanted(true), []);
  return (
    <DataContext.Provider value={state}>
      <RequestMapData.Provider value={request}>{children}</RequestMapData.Provider>
    </DataContext.Provider>
  );
}

/** Ask for the big map files. Safe to call more than once. */
export function useRequestMapData(): () => void {
  return useContext(RequestMapData);
}

export function useData(): DataState {
  const ctx = useContext(DataContext);
  if (!ctx) throw new Error('useData must be used inside DataProvider');
  return ctx;
}

/** The data of a loaded file, or undefined while loading or after an error. */
export function ready<T>(l: Loadable<T>): T | undefined {
  return l.status === 'ready' ? l.data : undefined;
}
