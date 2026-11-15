import { useApp } from '../lib/AppState.tsx';
import { C, fill, TAB_ORDER, type TabId } from '../lib/content.ts';
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
export function TabbedPanel() {
  const { tab, setTab } = useApp();
  const index = TAB_ORDER.indexOf(tab);
  return (
    <div className="flex h-full min-h-0 flex-col bg-paper">
      <nav aria-label="Guided steps" className="shrink-0 border-b border-ink/15 bg-white p-2">
        <ol className="grid grid-cols-6 gap-1 lg:grid-cols-3">
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
                <span className="hidden leading-tight lg:inline">{C.tabs[id]}</span>
              </button>
            </li>
          ))}
        </ol>
        <p className="num mt-1 text-[11px] text-ink/70 lg:hidden">{fill(C.explorer.stepLabel, { n: index + 1, total: TAB_ORDER.length })}: {C.tabs[tab]}</p>
      </nav>
      <div className="min-h-0 flex-1 overflow-y-auto p-4" tabIndex={0} role="region" aria-label={C.tabs[tab]}>
        <StepBody tab={tab} />
      </div>
    </div>
  );
}
