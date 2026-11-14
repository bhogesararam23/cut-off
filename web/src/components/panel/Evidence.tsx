import { C, fill } from '../../lib/content.ts';
import { ready, useData } from '../../lib/DataContext.tsx';
import { fmtNumber, fmtPercent } from '../../lib/format.ts';
import { FileError } from '../FileError.tsx';
import { Skeleton } from '../Skeleton.tsx';

const REPO = import.meta.env.VITE_REPO_URL?.replace(/\/$/, '');

export function Evidence() {
  const { stats } = useData();
  const s = ready(stats);
  const v = s?.validation ?? null;

  return (
    <section aria-labelledby="evidence-h" className="space-y-4 text-[15px]">
      <h2 id="evidence-h" className="text-lg font-semibold">{C.evidence.heading}</h2>
      {stats.status === 'loading' && <Skeleton className="h-40" />}
      {stats.status === 'error' && <FileError file={stats.file} />}
      {s && (
        <>
          {v ? (
            <div className="space-y-2">
              <p>{C.evidence.method}</p>
              <p className="font-medium">
                {fill(C.evidence.results, {
                  n_test_landslide: fmtNumber(v.n_test_landslide), n_test_forest: fmtNumber(v.n_test_forest),
                  detection_rate: fmtPercent(v.detection_rate), false_alarm_rate: fmtPercent(v.false_alarm_rate), auc: fmtNumber(v.auc, 2),
                })}
              </p>
            </div>
          ) : (
            <p>{C.evidence.noValidation}</p>
          )}

          <div>
            <h3 className="font-semibold">{C.evidence.baselineHeading}</h3>
            <p>
              {fill(C.evidence.baselineText, {
                baseline: fmtPercent(s.baseline_no_change_flag_rate, 1), post: fmtPercent(s.post_event_flag_rate, 1),
              })}
            </p>
          </div>

          <p className="text-sm text-slate-700">{C.evidence.context}</p>
          {REPO && (
            <p>
              <a
                href={`${REPO}/blob/main/docs/method.md`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sky-800 underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-500"
              >
                {C.evidence.link}
              </a>
            </p>
          )}
        </>
      )}
    </section>
  );
}
