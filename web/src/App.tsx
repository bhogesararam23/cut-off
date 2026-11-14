import { useEffect, useState } from 'react';
import type { EventInfo } from './lib/types.ts';

const DATA = '/data/panama-2026';

export default function App() {
  const [event, setEvent] = useState<EventInfo | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    fetch(`${DATA}/event.json`)
      .then((r) => (r.ok ? (r.json() as Promise<EventInfo>) : Promise.reject(new Error('missing'))))
      .then(setEvent)
      .catch(() => setFailed(true));
  }, []);

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      {event?.mock && (
        <div role="alert" className="bg-red-700 px-4 py-2 text-center text-sm font-semibold text-white">
          MOCK DATA: not real results. This screen uses made-up data while the real radar processing finishes.
        </div>
      )}
      <header className="border-b border-slate-200 bg-white px-4 py-3">
        <h1 className="text-lg font-semibold">Cut Off</h1>
        <p className="text-sm text-slate-600">{event ? event.name : 'Loading…'}</p>
      </header>
      <main className="p-4">
        {failed && <p className="text-sm text-red-700">Could not load event.json. The rest of the app still works.</p>}
      </main>
    </div>
  );
}
