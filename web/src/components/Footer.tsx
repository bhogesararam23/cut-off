import { C } from '../lib/content.ts';

export function Footer() {
  return (
    <footer className="border-t border-slate-200 bg-white px-3 py-1 text-[11px] leading-snug text-slate-600">{C.credits}</footer>
  );
}
