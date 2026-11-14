import { useRef, type PointerEvent, type ReactNode } from 'react';
import { useApp } from '../lib/AppState.tsx';

const DRAG_PX = 40;

/** Phone layout: the panel sits in a sheet at the bottom. Tap or drag the handle to open and close it. */
export function BottomSheet({ children }: { children: ReactNode }) {
  const { sheetOpen, setSheetOpen } = useApp();
  const startY = useRef<number | null>(null);

  const down = (e: PointerEvent) => {
    startY.current = e.clientY;
  };
  const up = (e: PointerEvent) => {
    if (startY.current === null) return;
    const dy = e.clientY - startY.current;
    startY.current = null;
    if (dy < -DRAG_PX) setSheetOpen(true);
    else if (dy > DRAG_PX) setSheetOpen(false);
    else setSheetOpen(!sheetOpen);
  };

  return (
    <section
      aria-label="Details"
      className={`absolute inset-x-0 bottom-0 z-20 flex flex-col rounded-t-xl border-t border-slate-300 bg-white shadow-[0_-4px_12px_rgba(0,0,0,0.15)] transition-[height] duration-200 motion-reduce:transition-none ${
        sheetOpen ? 'h-[85%]' : 'h-[35%]'
      }`}
    >
      <button
        type="button"
        aria-label={sheetOpen ? 'Collapse details' : 'Expand details'}
        aria-expanded={sheetOpen}
        onPointerDown={down}
        onPointerUp={up}
        onPointerCancel={() => {
          startY.current = null;
        }}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            setSheetOpen(!sheetOpen);
          }
        }}
        className="flex w-full shrink-0 touch-none justify-center py-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-sky-500"
      >
        <span aria-hidden="true" className="h-1.5 w-10 rounded-full bg-slate-300" />
      </button>
      <div className="min-h-0 flex-1">{children}</div>
    </section>
  );
}
