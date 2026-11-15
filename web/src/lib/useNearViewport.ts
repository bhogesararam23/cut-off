import { useEffect, useState, type RefObject } from 'react';

/** True once the element is within `margin` of the screen (and stays true). Used so heavy parts load only when needed. */
export function useNearViewport(ref: RefObject<Element | null>, margin = '600px'): boolean {
  const [near, setNear] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (!('IntersectionObserver' in window)) {
      setNear(true);
      return;
    }
    const io = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) {
          setNear(true);
          io.disconnect();
        }
      },
      { rootMargin: margin },
    );
    io.observe(el);
    return () => io.disconnect();
  }, [ref, margin]);
  return near;
}
