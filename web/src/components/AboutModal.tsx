import { useEffect, useRef } from 'react';
import { useApp } from '../lib/AppState.tsx';
import { C } from '../lib/content.ts';

const REPO = import.meta.env.VITE_REPO_URL?.replace(/\/$/, '');

function ExternalLink({ href, children }: { href: string; children: string }) {
  return (
    <a href={href} target="_blank" rel="noopener noreferrer" className="text-sky-800 underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-500">
      {children}
    </a>
  );
}

export function AboutModal() {
  const { aboutOpen, setAboutOpen } = useApp();
  const closeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!aboutOpen) return;
    const previous = document.activeElement as HTMLElement | null;
    closeRef.current?.focus();
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setAboutOpen(false);
    window.addEventListener('keydown', onKey);
    return () => {
      window.removeEventListener('keydown', onKey);
      previous?.focus();
    };
  }, [aboutOpen, setAboutOpen]);

  if (!aboutOpen) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 p-4" onClick={() => setAboutOpen(false)}>
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="about-title"
        onClick={(e) => e.stopPropagation()}
        className="max-h-full w-full max-w-md overflow-y-auto rounded-lg bg-white p-5 shadow-xl"
      >
        <h2 id="about-title" className="text-lg font-semibold">
          {C.about.heading}
        </h2>
        <p className="mt-2 text-[15px]">{C.about.body}</p>
        {REPO && (
          <p className="mt-2 text-[15px]">
            {C.about.code}: <ExternalLink href={REPO}>{REPO}</ExternalLink> · {C.about.method}:{' '}
            <ExternalLink href={`${REPO}/blob/main/docs/method.md`}>{`${REPO}/blob/main/docs/method.md`}</ExternalLink>
          </p>
        )}
        <p className="mt-2 text-[15px] font-medium">{C.about.disclaimer}</p>
        <p className="mt-2 text-[15px]">
          {C.about.si}
          {REPO ? (
            <>
              : <ExternalLink href={`${REPO}/blob/main/docs/si-log.md`}>{`${REPO}/blob/main/docs/si-log.md`}</ExternalLink>
            </>
          ) : (
            '.'
          )}
        </p>
        <button
          ref={closeRef}
          type="button"
          aria-label={C.about.close}
          onClick={() => setAboutOpen(false)}
          className="mt-4 rounded bg-slate-800 px-4 py-1.5 text-sm text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-500 focus-visible:ring-offset-2"
        >
          {C.about.close}
        </button>
      </div>
    </div>
  );
}
