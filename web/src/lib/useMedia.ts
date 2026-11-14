import { useSyncExternalStore } from 'react';

/** True while the CSS media query matches (updates when the window is resized). */
export function useMedia(query: string): boolean {
  return useSyncExternalStore(
    (notify) => {
      const m = window.matchMedia(query);
      m.addEventListener('change', notify);
      return () => m.removeEventListener('change', notify);
    },
    () => window.matchMedia(query).matches,
    () => false,
  );
}

/** Same breakpoint as Tailwind's `lg`. */
export const DESKTOP_QUERY = '(min-width: 1024px)';
