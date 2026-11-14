import { useRef, type KeyboardEvent } from 'react';
import { useApp } from '../lib/AppState.tsx';
import { C, TAB_ORDER, type TabId } from '../lib/content.ts';
import { Limits } from './panel/Limits.tsx';
import { Overview } from './panel/Overview.tsx';
import { Placeholder } from './panel/Placeholder.tsx';
import { Timeline } from './panel/Timeline.tsx';
import { WhyRadar } from './panel/WhyRadar.tsx';

function TabBody({ tab }: { tab: TabId }) {
  switch (tab) {
    case 'overview':
      return <Overview />;
    case 'landslides':
      return <Placeholder title={C.landslides.heading} />;
    case 'access':
      return <Placeholder title={C.access.heading} />;
    case 'evidence':
      return <Placeholder title={C.evidence.heading} />;
    case 'why':
      return <WhyRadar />;
    case 'limits':
      return <Limits />;
    case 'timeline':
      return <Timeline />;
  }
}

/** The seven tabs. Used in the desktop side panel and inside the phone bottom sheet. */
export function TabbedPanel() {
  const { tab, setTab } = useApp();
  const refs = useRef<Partial<Record<TabId, HTMLButtonElement | null>>>({});

  const onKey = (e: KeyboardEvent) => {
    const i = TAB_ORDER.indexOf(tab);
    const next =
      e.key === 'ArrowRight' ? i + 1 : e.key === 'ArrowLeft' ? i - 1 : e.key === 'Home' ? 0 : e.key === 'End' ? TAB_ORDER.length - 1 : null;
    if (next === null) return;
    e.preventDefault();
    const id = TAB_ORDER[(next + TAB_ORDER.length) % TAB_ORDER.length];
    setTab(id);
    refs.current[id]?.focus();
  };

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div
        role="tablist"
        aria-label="Sections"
        onKeyDown={onKey}
        className="flex shrink-0 gap-1 overflow-x-auto border-b border-slate-200 bg-white px-2 pt-2"
      >
        {TAB_ORDER.map((id) => (
          <button
            key={id}
            ref={(el) => {
              refs.current[id] = el;
            }}
            role="tab"
            id={`tab-${id}`}
            type="button"
            aria-selected={tab === id}
            aria-controls="tabpanel"
            tabIndex={tab === id ? 0 : -1}
            onClick={() => setTab(id)}
            className={`shrink-0 whitespace-nowrap rounded-t px-1.5 py-1.5 text-[13px] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-500 ${
              tab === id ? 'border-b-2 border-slate-900 font-semibold' : 'text-slate-600 hover:bg-slate-100'
            }`}
          >
            {C.tabs[id]}
          </button>
        ))}
      </div>
      <div
        id="tabpanel"
        role="tabpanel"
        aria-labelledby={`tab-${tab}`}
        tabIndex={0}
        className="min-h-0 flex-1 overflow-y-auto p-4 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-sky-500"
      >
        <TabBody tab={tab} />
      </div>
    </div>
  );
}
