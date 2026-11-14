import { C } from '../lib/content.ts';
import { ready, useData } from '../lib/DataContext.tsx';

/** Shown on every screen while the event or stats file says the data is made up. */
export function MockBanner() {
  const { event, stats } = useData();
  const mock = ready(event)?.mock === true || ready(stats)?.mock === true;
  if (!mock) return null;
  return (
    <div role="alert" className="bg-red-700 px-4 py-2 text-center text-sm font-semibold text-white">
      {C.mockBanner}
    </div>
  );
}
