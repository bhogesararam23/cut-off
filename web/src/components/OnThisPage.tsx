import { useEffect, useState } from 'react';
import { C } from '../lib/content.ts';

const link = 'block rounded px-2 py-1 text-sm hover:bg-ink/5';

/** Which section is nearest the top of the screen, for the sticky list. */
function useActiveId(): string {
  const [active, setActive] = useState('top');
  useEffect(() => {
    const els = C.toc.items.map((i) => document.getElementById(i.id)).filter((e): e is HTMLElement => e !== null);
    if (!('IntersectionObserver' in window) || els.length === 0) return;
    const io = new IntersectionObserver(
      (entries) => {
        const hit = entries.filter((e) => e.isIntersecting).sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top)[0];
        if (hit) setActive(hit.target.id);
      },
      { rootMargin: '-72px 0px -60% 0px' },
    );
    els.forEach((el) => io.observe(el));
    return () => io.disconnect();
  }, []);
  return active;
}

/** The sticky "On this page" list in the left margin of wide screens. */
export function OnThisPage() {
  const active = useActiveId();
  return (
    <nav aria-label={C.toc.heading} className="no-print sticky top-16 self-start px-3 py-6">
      <p className="px-2 text-xs font-semibold uppercase tracking-wide text-ink/70">{C.toc.heading}</p>
      <ul className="mt-2 space-y-0.5">
        {C.toc.items.map((i) => (
          <li key={i.id}>
            <a href={`#${i.id}`} aria-current={active === i.id ? 'location' : undefined} className={`${link} ${active === i.id ? 'bg-ink/10 font-semibold' : ''}`}>
              {i.label}
            </a>
          </li>
        ))}
      </ul>
    </nav>
  );
}

/** The same list as a compact row of links, for screens too narrow for the margin. */
export function OnThisPageInline() {
  return (
    <nav aria-label={C.toc.heading} className="no-print mt-5 xl:hidden">
      <p className="text-xs font-semibold uppercase tracking-wide text-ink/70">{C.toc.heading}</p>
      <ul className="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-sm">
        {C.toc.items.map((i) => (
          <li key={i.id}>
            <a className="underline decoration-brand decoration-2 underline-offset-2" href={`#${i.id}`}>{i.label}</a>
          </li>
        ))}
      </ul>
    </nav>
  );
}
