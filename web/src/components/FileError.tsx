import { C, fill } from '../lib/content.ts';

export function FileError({ file }: { file: string }) {
  return (
    <p role="status" className="rounded border border-amber-300 bg-amber-50 p-2 text-sm text-amber-900">
      {fill(C.errors.file, { file })}
    </p>
  );
}
