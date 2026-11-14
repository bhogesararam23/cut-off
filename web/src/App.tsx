import { AboutModal } from './components/AboutModal.tsx';
import { BottomSheet } from './components/BottomSheet.tsx';
import { Footer } from './components/Footer.tsx';
import { MockBanner } from './components/MockBanner.tsx';
import { TabbedPanel } from './components/SidePanel.tsx';
import { TopBar } from './components/TopBar.tsx';
import { AppStateProvider } from './lib/AppState.tsx';
import { MapView } from './components/map/MapView.tsx';
import { DataProvider } from './lib/DataContext.tsx';
import { DESKTOP_QUERY, useMedia } from './lib/useMedia.ts';

function Layout() {
  const desktop = useMedia(DESKTOP_QUERY);
  // Only one panel is mounted at a time, so ids and tab order are never duplicated.
  return (
    <div className="flex h-dvh flex-col bg-slate-50 text-slate-900">
      <MockBanner />
      <TopBar />
      <main className="relative flex min-h-0 flex-1">
        {desktop ? (
          <>
            <div className="relative min-w-0 flex-1">
              <MapView />
            </div>
            <aside className="w-[400px] shrink-0 border-l border-slate-200 bg-white">
              <TabbedPanel />
            </aside>
          </>
        ) : (
          <>
            <div className="absolute inset-x-0 top-0 bottom-[35%]">
              <MapView />
            </div>
            <BottomSheet>
              <TabbedPanel />
            </BottomSheet>
          </>
        )}
      </main>
      <Footer />
      <AboutModal />
    </div>
  );
}

export default function App() {
  return (
    <DataProvider>
      <AppStateProvider>
        <Layout />
      </AppStateProvider>
    </DataProvider>
  );
}
