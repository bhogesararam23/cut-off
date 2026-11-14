import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import { FILES, getJson, type FileKey, type Loadable } from './data.ts';

type Spec = typeof FILES;
export type DataState = { [K in FileKey]: Loadable<NonNullable<Spec[K]['_type']>> };

const DataContext = createContext<DataState | null>(null);

const initial = Object.fromEntries(Object.keys(FILES).map((k) => [k, { status: 'loading' }])) as unknown as DataState;

/** Loads every file in parallel. Each file has its own loading/error state, so one bad file never blocks the rest. */
export function DataProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<DataState>(initial);

  useEffect(() => {
    let cancelled = false;
    (Object.keys(FILES) as FileKey[]).forEach((key) => {
      const { name, api } = FILES[key];
      getJson(name, api)
        .then((data) => !cancelled && setState((s) => ({ ...s, [key]: { status: 'ready', data } })))
        .catch(() => !cancelled && setState((s) => ({ ...s, [key]: { status: 'error', file: name } })));
    });
    return () => {
      cancelled = true;
    };
  }, []);

  return <DataContext.Provider value={state}>{children}</DataContext.Provider>;
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
