import { answerTiles, baselineFails } from '../lib/answer.ts';
import { C, fill } from '../lib/content.ts';
import { assetUrl } from '../lib/data.ts';
import { ready, useData } from '../lib/DataContext.tsx';
import { fmtDayYear, fmtNumber, fmtPercent } from '../lib/format.ts';
import { FileError } from './FileError.tsx';
import { OnThisPageInline } from './OnThisPage.tsx';
import { Skeleton } from './Skeleton.tsx';

const IMG_PX = 2048; // the comparison images are square; the size is set so the page does not jump while they load
const ext = 'underline decoration-brand decoration-2 underline-offset-2';

/** The top band: title, one-sentence summary, key facts with unit and source, and how to read them. */
export function Overview() {
  const { stats } = useData();
  const s = ready(stats);
  const v = s?.validation ?? null;

  return (
    <section id="top" aria-labelledby="page-h" className="border-b border-ink/10 bg-white">
      <div className="mx-auto max-w-3xl xl:ml-14 xl:mr-0 px-4 py-8 sm:py-10">
        <p className="inline-block rounded-card border border-ink px-2 py-0.5 text-xs font-semibold uppercase tracking-wide">{C.page.provisional}</p>
        <h1 id="page-h" className="mt-3 text-[1.7rem] font-semibold leading-tight tracking-tight sm:text-4xl">{C.page.title}</h1>
        <p className="mt-4 text-lg leading-relaxed">{C.page.summary}</p>
        <p className="mt-2 text-sm text-ink/80">
          {C.page.notWarning} {C.page.quakeSource} (<a className={ext} href={C.page.quakeUrl} target="_blank" rel="noopener noreferrer">USGS</a>
          ; <a className={ext} href="https://mapping.emergency.copernicus.eu/news/earthquake-in-los-santos-panama-emsr934/" target="_blank" rel="noopener noreferrer">{C.page.referenceLabel}</a>).
        </p>

        <OnThisPageInline />

        <h2 className="mt-8 text-xl font-semibold">{C.page.factsHeading}</h2>
        {stats.status === 'error' && <div className="mt-3"><FileError file={stats.file} /></div>}
        <dl className="mt-3 grid grid-cols-2 gap-3">
          {s ? (
            <>
              {answerTiles(s).map((t) => (
                <div key={t.key} className="rounded-card border border-ink/15 bg-paper p-4">
                  <dd className="num text-3xl font-medium">
                    {t.value === null ? <span className="text-base">{C.page.notAvailable}</span> : fmtNumber(t.value, t.digits)}
                    {t.value !== null && t.unit && <span className="ml-1 text-base">{t.unit}</span>}
                  </dd>
                  <dt className="mt-1 text-sm font-semibold">{C.page.facts[t.key].label}</dt>
                  <p className="mt-1 text-xs text-ink/75">{C.page.facts[t.key].meaning}</p>
                  <p className="num mt-2 text-[10px] uppercase tracking-wide text-ink/60">{fill(C.page.source, { file: t.source })}</p>
                </div>
              ))}
              <div className="rounded-card border border-ink/15 bg-paper p-4">
                <dd className="num text-3xl font-medium">
                  {v ? <>{fmtPercent(v.detection_rate, 0)}<span className="ml-1 text-base">%</span></> : <span className="text-base">{C.page.notAvailable}</span>}
                </dd>
                <dt className="mt-1 text-sm font-semibold">{C.page.facts.detection.label}</dt>
                <p className="mt-1 text-xs text-ink/75">
                  {v ? fill(C.page.facts.detection.meaning, { n: v.n_test_landslide, false_alarm: fmtPercent(v.false_alarm_rate, 0), n_forest: v.n_test_forest }) : ''}
                </p>
                <p className="num mt-2 text-[10px] uppercase tracking-wide text-ink/60">{fill(C.page.source, { file: 'stats.json' })}</p>
              </div>
            </>
          ) : (
            [0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-36" />)
          )}
        </dl>

        {s && v && (
          <div role="note" className="mt-4 space-y-2 rounded-card border border-brand bg-paper p-3 text-[15px]">
            <p>{fill(C.page.readFirst, { detection: fmtPercent(v.detection_rate, 0), auc: fmtNumber(v.auc, 2) })}</p>
            <p>{C.page.splitNote}</p>
            {baselineFails(s) && <p className="font-semibold">{C.page.baselineFails}</p>}
          </div>
        )}

        <p className="no-print mt-6 flex flex-wrap gap-3">
          <a href="#map" className="rounded-card bg-ink px-5 py-2.5 font-semibold text-white transition-opacity duration-150 hover:opacity-90">{C.page.openMap}</a>
          <a href="#sure" className="rounded-card border border-ink px-5 py-2.5 font-semibold transition-colors duration-150 hover:bg-ink/5">{C.page.jumpAccuracy}</a>
        </p>
      </div>
    </section>
  );
}

/** Figure 1: optical and radar, side by side, with what you are seeing and the credit. */
export function Figure1() {
  const { event, pairs } = useData();
  const e = ready(event);
  const first = ready(pairs)?.[0];
  if (!e?.optical || !first) return null;
  const date = fmtDayYear(first.after);
  const items = [
    { src: assetUrl(e.optical.after_webp), alt: C.figure1.altOptical, cap: C.figure1.capOptical },
    { src: assetUrl(first.after_png), alt: fill(C.figure1.altRadar, { date }), cap: fill(C.figure1.capRadar, { date }) },
  ];
  return (
    <section id="figure-1" aria-labelledby="fig1-h" className="mx-auto max-w-3xl xl:ml-14 xl:mr-0 scroll-mt-16 px-4 py-8">
      <figure>
        <h2 id="fig1-h" className="text-lg font-semibold">{C.figure1.title}</h2>
        <div className="mt-3 grid grid-cols-2 gap-2">
          {items.map((im) => (
            <div key={im.src}>
              <img src={im.src} alt={im.alt} width={IMG_PX} height={IMG_PX} loading="lazy" decoding="async" className="aspect-square w-full rounded-card border border-ink/15 bg-ink object-cover" />
              <p className="mt-1 text-xs font-medium text-ink/80">{im.cap}</p>
            </div>
          ))}
        </div>
        <figcaption className="mt-3 space-y-1 text-[15px]">
          <p>{fill(C.figure1.seeing, { date })}</p>
          <p className="text-xs text-ink/70">{C.figure1.credit}</p>
        </figcaption>
      </figure>
    </section>
  );
}

/** A small box of plain-English terms. */
export function Terms() {
  return (
    <section id="terms" aria-labelledby="terms-h" className="mx-auto max-w-3xl xl:ml-14 xl:mr-0 scroll-mt-16 px-4 pb-10">
      <div className="rounded-card border border-ink/20 bg-white p-4">
        <h2 id="terms-h" className="text-lg font-semibold">{C.terms.heading}</h2>
        <dl className="mt-2 grid gap-x-6 gap-y-2 text-[15px] sm:grid-cols-2">
          {C.terms.items.map((t) => (
            <div key={t.term}>
              <dt className="font-semibold">{t.term}</dt>
              <dd className="text-ink/85">{t.text}</dd>
            </div>
          ))}
        </dl>
      </div>
    </section>
  );
}
