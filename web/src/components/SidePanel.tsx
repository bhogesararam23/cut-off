import { useApp } from '../lib/AppState.tsx';
import { C, TAB_ORDER, type TabId } from '../lib/content.ts';
import { Access } from './panel/Access.tsx';
import { Landslides } from './panel/Landslides.tsx';
import { Limits } from './panel/Limits.tsx';
import { Happened, RoadsStep, SureStep } from './panel/Steps.tsx';

function StepBody({ tab }: { tab: TabId }) {
  switch (tab) {
    case 'happened':
      return <Happened />;
    case 'slopes':
      return (
        <>
          <p className="mb-3 text-sm">{C.explorer.slopes}</p>
          <Landslides />
        </>
      );
    case 'roads':
      return <RoadsStep />;
    case 'access':
      return <Access />;
    case 'sure':
      return <SureStep />;
    case 'limits':
      return <Limits />;
  }
}

/** The guided rail: six numbered steps. Choosing a step sets the map layers; nothing advances by itself. */
export function TabbedPanel({ flow = false }: { flow?: boolean }) {
  const { tab, setTab } = useApp();
  return (
    <div className={`flex min-h-0 flex-col bg-paper ${flow ? '' : 'h-full'}`}>
      <nav aria-label="Guided steps" className="shrink-0 border-b border-ink/15 bg-white p-2">
        <ol className="grid grid-cols-2 gap-1 sm:grid-cols-3">
          {TAB_ORDER.map((id, i) => (
            <li key={id}>
              <button
                type="button"
                aria-current={tab === id ? 'step' : undefined}
                title={C.tabs[id]}
                onClick={() => setTab(id)}
                className={`flex w-full items-center gap-1.5 rounded-card border px-1.5 py-1.5 text-left text-xs transition-colors duration-150 ${
                  tab === id ? 'border-ink bg-ink text-white' : 'border-ink/20 bg-white hover:bg-ink/5'
                }`}
              >
                <span className="num flex h-5 w-5 shrink-0 items-center justify-center rounded-full border border-current text-[11px]">{i + 1}</span>
                <span className="leading-tight">{C.tabs[id]}</span>
              </button>
            </li>
          ))}
        </ol>
      </nav>
      <div className={`min-h-0 flex-1 p-4 ${flow ? '' : 'overflow-y-auto'}`} tabIndex={0} role="region" aria-label={C.tabs[tab]}>
        <StepBody tab={tab} />
      </div>
    </div>
  );
}
