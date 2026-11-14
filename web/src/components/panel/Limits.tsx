import { C } from '../../lib/content.ts';

export function Limits() {
  return (
    <section aria-labelledby="limits-h" className="space-y-3">
      <h2 id="limits-h" className="text-lg font-semibold">{C.limits.heading}</h2>
      <ol className="list-decimal space-y-2 pl-5 text-[15px]">
        {C.limits.items.map((t) => (
          <li key={t}>{t}</li>
        ))}
      </ol>
    </section>
  );
}
