import { lazy, Suspense } from 'react';
import { Answer } from './components/Answer.tsx';
import { BottomSheet } from './components/BottomSheet.tsx';
import { ErrorBoundary } from './components/ErrorBoundary.tsx';
import { Header } from './components/Header.tsx';
import { MockBanner } from './components/MockBanner.tsx';
import { MethodSection, SiteFooter, SureSection } from './components/Sections.tsx';
import { TabbedPanel } from './components/SidePanel.tsx';
import { AppStateProvider } from './lib/AppState.tsx';
import { C } from './lib/content.ts';
import { DataProvider } from './lib/DataContext.tsx';
import { DESKTOP_QUERY, useMedia } from './lib/useMedia.ts';

// the map library is large: the answer screen paints first, the map follows
const MapView = lazy(() => import('./components/map/MapView.tsx').then((m) => ({ default: m.MapView })));

function MapSlot() {
  return (
    <ErrorBoundary>
      <Suspense fallback={<div role="status" aria-label="Loading map" className="absolute inset-0 bg-ink" />}>
        <MapView />
      </Suspense>
    </ErrorBoundary>
  );
}

/** Section C: guided rail on the left and the map on the right; on a phone the rail is a bottom sheet over the map. */
function Explorer() {
  const desktop = useMedia(DESKTOP_QUERY);
  return (
    <section id="map" aria-label={C.explorer.heading} className="relative flex h-[calc(100dvh-56px)] min-h-[520px] scroll-mt-14 border-y border-ink/20">
      {desktop ? (
        <>
          <aside className="w-[35%] max-w-[460px] min-w-[340px] shrink-0 border-r border-ink/20">
            <TabbedPanel />
          </aside>
          <div className="relative min-w-0 flex-1">
            <MapSlot />
          </div>
        </>
      ) : (
        <>
          <div className="absolute inset-x-0 top-0 bottom-[35%]">
            <MapSlot />
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
        <MockBanner />
        <Header />
        <main>
          <Answer />
          <Explorer />
          <SureSection />
          <MethodSection />
        </main>
        <SiteFooter />
      </AppStateProvider>
    </DataProvider>
  );
}
