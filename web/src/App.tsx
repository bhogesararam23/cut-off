import { lazy, Suspense, useEffect, useRef } from 'react';
import { BottomSheet } from './components/BottomSheet.tsx';
import { ErrorBoundary } from './components/ErrorBoundary.tsx';
import { Header } from './components/Header.tsx';
import { OnThisPage } from './components/OnThisPage.tsx';
import { Figure1, Overview, Terms } from './components/Overview.tsx';
import { LimitsSection, MethodSection, SiteFooter, SureSection } from './components/Sections.tsx';
import { TabbedPanel } from './components/SidePanel.tsx';
import { AppStateProvider } from './lib/AppState.tsx';
import { C } from './lib/content.ts';
import { DataProvider, useRequestMapData } from './lib/DataContext.tsx';
import { useNearViewport } from './lib/useNearViewport.ts';
import { DESKTOP_QUERY, useMedia } from './lib/useMedia.ts';

// the map library is large: the answer screen paints first, the map follows
const MapView = lazy(() => import('./components/map/MapView.tsx').then((m) => ({ default: m.MapView })));

const mapPlaceholder = <div role="status" aria-label="Loading map" className="absolute inset-0 bg-ink" />;

function MapSlot({ show }: { show: boolean }) {
  if (!show) return mapPlaceholder;
  return (
    <ErrorBoundary>
      <Suspense fallback={mapPlaceholder}>
        <MapView />
      </Suspense>
    </ErrorBoundary>
  );
}

/** The map: guided rail on the left and the map on the right; on a phone the rail is a bottom sheet over the map. */
function Explorer() {
  const desktop = useMedia(DESKTOP_QUERY);
  const ref = useRef<HTMLElement>(null);
  const near = useNearViewport(ref, '300px');
  const requestMapData = useRequestMapData();
  // the map code and its big data files are fetched only when this section is about to be seen
  useEffect(() => {
    if (near) requestMapData();
  }, [near, requestMapData]);
  return (
    <section ref={ref} id="map" aria-label={C.explorer.heading} className="relative flex h-[calc(100dvh-56px)] min-h-[520px] scroll-mt-14 border-y border-ink/20">
      {desktop ? (
        <>
          <aside className="w-[35%] max-w-[460px] min-w-[340px] shrink-0 border-r border-ink/20">
            <TabbedPanel />
          </aside>
          <div className="relative min-w-0 flex-1">
            <MapSlot show={near} />
          </div>
        </>
      ) : (
        <>
          <div className="absolute inset-x-0 top-0 bottom-[35%]">
            <MapSlot show={near} />
          </div>
          <BottomSheet>
            <TabbedPanel />
          </BottomSheet>
        </>
      )}
    </section>
  );
}

export default function App() {
  return (
    <DataProvider>
      <AppStateProvider>
        <Header />
        <div className="xl:grid xl:grid-cols-[13rem_minmax(0,1fr)]">
          <aside className="hidden border-r border-ink/10 xl:block"><OnThisPage /></aside>
          <main className="min-w-0">
            <Overview />
            <Figure1 />
            <Terms />
            <Explorer />
            <SureSection />
            <MethodSection />
            <LimitsSection />
          </main>
        </div>
        <SiteFooter />
      </AppStateProvider>
    </DataProvider>
  );
}
