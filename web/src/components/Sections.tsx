import { lazy, Suspense } from 'react';
import { baselineFails, confusion, sizeRows } from '../lib/answer.ts';
import { C, fill } from '../lib/content.ts';
import { ready, useData } from '../lib/DataContext.tsx';
import { fmtNumber, fmtPercent } from '../lib/format.ts';
import { FileError } from './FileError.tsx';
import { REPO } from './Header.tsx';
import { WhyRadar } from './panel/WhyRadar.tsx';
import { Skeleton } from './Skeleton.tsx';

// the charting library is large: fetched only when this section is on the page
const EvidenceCharts = lazy(() => import('./charts/EvidenceCharts.tsx'));

const section = 'mx-auto max-w-6xl scroll-mt-16 px-4 py-10';
const prose = 'max-w-[68ch] text-[15px] leading-relaxed';
const ext = 'underline decoration-brand decoration-2 underline-offset-2';

function Row({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="flex items-baseline justify-between gap-4 border-b border-ink/10 py-2">
      <dt className="text-sm">{label}</dt>
      <dd className="num shrink-0 text-right font-medium">
        {value}
        {sub && <span className="ml-2 text-xs font-normal text-ink/70">{sub}</span>}
      </dd>
    </div>
  );
}

/** Section D: the accuracy check, with counts next to every rate. */
export function SureSection() {
  const { stats } = useData();
  const s = ready(stats);
  const v = s?.validation ?? null;
  const cm = v ? confusion(v) : null;
  return (
    <section id="sure" aria-labelledby="sure-h" className={section}>
      <h2 id="sure-h" className="text-2xl font-semibold tracking-tight">{C.sure.heading}</h2>
      <div className={`${prose} mt-3 space-y-2`}>
        <p>{C.sure.p1}</p>
        <p>{C.sure.p2}</p>
      </div>
      {stats.status === 'error' && <FileError file={stats.file} />}
      {stats.status === 'loading' && <Skeleton className="mt-4 h-40" />}
      {s && !v && <p className="mt-4 font-medium">{C.evidence.noValidation}</p>}
      {s && v && cm && (
        <div className="mt-6 grid gap-8 lg:grid-cols-2">
          <div>
            <dl>
              <Row label={C.sure.detection} value={`${fmtPercent(v.detection_rate, 1)}%`} sub={fill(C.sure.of, { k: cm.found, n: v.n_test_landslide })} />
              <Row label={C.sure.falseAlarm} value={`${fmtPercent(v.false_alarm_rate, 1)}%`} sub={fill(C.sure.of, { k: cm.falseAlarms, n: v.n_test_forest })} />
              <Row label={C.sure.auc} value={fmtNumber(v.auc, 2)} />
              <Row label={C.sure.threshold} value={`${fmtNumber(v.threshold_db, 1)} dB`} />
              <Row label={C.sure.baseline} value={`${fmtPercent(s.baseline_no_change_flag_rate, 1)}%`} />
              <Row label={C.sure.post} value={`${fmtPercent(s.post_event_flag_rate, 1)}%`} />
            </dl>
            {baselineFails(s) && <p className="mt-3 rounded-card border border-brand bg-white p-3 text-sm">{C.evidence.baselineWarning}</p>}

            <table className="mt-6 w-full border-collapse text-sm">
              <caption className="mb-1 text-left font-semibold">{C.sure.table.title}</caption>
              <thead>
                <tr className="border-b border-ink/20 text-left">
                  <td />
                  <th scope="col" className="py-1 font-medium">{C.sure.table.flagged}</th>
                  <th scope="col" className="py-1 font-medium">{C.sure.table.notFlagged}</th>
                </tr>
              </thead>
              <tbody className="num">
                <tr className="border-b border-ink/10">
                  <th scope="row" className="py-1 text-left font-sans font-normal">{C.sure.table.landslide}</th>
                  <td>{cm.found}</td>
                  <td>{cm.missed}</td>
                </tr>
                <tr>
                  <th scope="row" className="py-1 text-left font-sans font-normal">{C.sure.table.forest}</th>
                  <td>{cm.falseAlarms}</td>
                  <td>{cm.correctForest}</td>
                </tr>
              </tbody>
            </table>

            <h3 className="mt-6 font-semibold">{C.sure.bySize}</h3>
            <ul className="mt-1 text-sm">
              {sizeRows(v.by_size).map((r) => (
                <li key={r.size} className={`flex justify-between border-b border-ink/10 py-1 ${r.scored ? '' : 'text-ink/55'}`}>
                  <span>{r.size}</span>
                  <span className="num">{r.scored ? `${fmtPercent(r.detection_rate, 1)}% (n = ${r.n})` : `n = ${r.n}, ${C.sure.tooFew}`}</span>
                </li>
              ))}
            </ul>
          </div>
          <div className="text-[15px]">
            <Suspense fallback={<Skeleton className="h-64" />}>
              <EvidenceCharts />
            </Suspense>
            <p className="mt-4 text-sm text-ink/75">{C.evidence.context}</p>
          </div>
        </div>
      )}
    </section>
  );
}

const ICONS = [
  <path key="a" d="M4 30 L14 12 L22 24 L30 8 L44 30 Z M30 8 L34 16" />,
  <path key="b" d="M4 34 L24 8 L44 34 Z M14 34 L24 20 L34 34" />,
  <path key="c" d="M10 12 h12 v10 h-12 Z M26 22 h12 v12 h-12 Z M22 17 L26 24" />,
  <path key="d" d="M6 34 C14 20 20 30 28 18 S40 12 42 8 M28 18 l-4 -6 M10 30 a3 3 0 1 0 0.1 0" />,
];

/** Section E: the method in four steps with simple line drawings, and the limits. */
export function MethodSection() {
  return (
    <section id="method" aria-labelledby="method-h" className={`${section} border-t border-ink/10`}>
      <h2 id="method-h" className="text-2xl font-semibold tracking-tight">{C.method.heading}</h2>
      <ol className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {C.method.steps.map((st, i) => (
          <li key={st.title} className="rounded-card border border-ink/15 bg-white p-4">
            <svg viewBox="0 0 48 40" width="48" height="40" aria-hidden="true" fill="none" stroke="#0b1e3a" strokeWidth="2" strokeLinejoin="round" strokeLinecap="round">{ICONS[i]}</svg>
            <p className="num mt-2 text-xs text-ink/60">{i + 1}</p>
            <h3 className="font-semibold">{st.title}</h3>
            <p className="mt-1 text-sm text-ink/80">{st.text}</p>
          </li>
        ))}
      </ol>
      <div className="mt-8 grid gap-8 lg:grid-cols-2">
        <div className="max-w-[68ch]"><WhyRadar /></div>
        <div>
          <h3 className="text-lg font-semibold">{C.method.limitsHeading}</h3>
          <ol className="mt-2 max-w-[68ch] list-decimal space-y-2 pl-5 text-[15px]">
            {C.limits.items.map((t) => <li key={t}>{t}</li>)}
          </ol>
          <p className="mt-3"><a className={ext} href={`${REPO}/blob/main/docs/method.md`} target="_blank" rel="noopener noreferrer">{C.method.full}</a></p>
        </div>
      </div>
    </section>
  );
}

/** Section F and footer: disclaimer, data credits, licence, AI use. */
export function SiteFooter() {
  return (
    <footer id="data" className="scroll-mt-16 bg-ink px-4 py-10 text-sm text-white/90">
      <div className="mx-auto max-w-6xl">
        <h2 className="text-lg font-semibold text-white">{C.footer.dataHeading}</h2>
        <ul className="mt-2 max-w-[80ch] list-disc space-y-1 pl-5">
          {C.footer.credits.map((c) => <li key={c}>{c}</li>)}
        </ul>
        <p className="mt-4 max-w-[80ch] font-semibold text-white">{C.footer.disclaimer}</p>
        <p className="mt-2">
          {C.footer.licence}{' '}
          <a className="underline" href={REPO} target="_blank" rel="noopener noreferrer">{C.footer.repo}</a>
        </p>
        <p className="mt-2">
          {C.footer.ai}{' '}
          <a className="underline" href={`${REPO}/blob/main/docs/si-log.md`} target="_blank" rel="noopener noreferrer">{C.footer.aiLink}</a>
        </p>
      </div>
    </footer>
  );
}
