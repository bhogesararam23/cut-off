import { answerTiles, baselineFails, peopleInCutOff } from '../lib/answer.ts';
import { C, fill } from '../lib/content.ts';
import { assetUrl } from '../lib/data.ts';
import { ready, useData } from '../lib/DataContext.tsx';
import { fmtDayYear, fmtNumber, fmtPercent } from '../lib/format.ts';
import { FileError } from './FileError.tsx';
import { Skeleton } from './Skeleton.tsx';

const IMG_PX = 2048; // the comparison images are square; the size is set so the page does not jump while they load

/** First screen: the answer in numbers, how weak it is, and why radar was needed. Static: no animation. */
export function Answer() {
  const { stats, communities, event, pairs } = useData();
  const s = ready(stats);
  const c = ready(communities);
  const e = ready(event);
  const first = ready(pairs)?.[0];
  const people = peopleInCutOff(c);
  const v = s?.validation ?? null;

  return (
    <section id="top" aria-labelledby="answer-h" className="mx-auto max-w-6xl px-4 py-8 sm:py-12">
      <h1 id="answer-h" className="max-w-[26ch] text-3xl font-semibold leading-tight tracking-tight sm:max-w-[30ch] sm:text-4xl">
        {s && s.communities_cut_off !== null
          ? fill(C.answer.headline, { landslides: fmtNumber(s.landslides), communities: fmtNumber(s.communities_cut_off) })
          : C.answer.headlineLoading}
      </h1>

      {stats.status === 'error' && <div className="mt-4"><FileError file={stats.file} /></div>}
      {s && v && (baselineFails(s) || v.auc < 0.7) && (
        <p role="note" className="mt-4 max-w-[68ch] rounded-card border border-brand bg-white p-3 text-[15px]">
          {fill(C.answer.weak, { detection: fmtPercent(v.detection_rate, 1), auc: fmtNumber(v.auc, 2) })}
        </p>
      )}

      <dl className="mt-6 grid grid-cols-2 gap-3 lg:grid-cols-4">
        {s
          ? answerTiles(s, c).map((t) => (
              <div key={t.key} className="rounded-card border border-ink/15 bg-white p-4">
                <dd className="num text-3xl font-medium">
                  {t.value === null ? <span className="text-base">{C.answer.notAvailable}</span> : fmtNumber(t.value, t.digits)}
                  {t.value !== null && t.unit && <span className="ml-1 text-base">{t.unit}</span>}
                </dd>
                <dt className="mt-1 text-sm font-semibold">{C.answer.tiles[t.key].label}</dt>
                <p className="mt-1 text-xs text-ink/75">
                  {t.key === 'people' ? fill(C.answer.tiles.people.meaning, { known: people.known, total: people.total }) : C.answer.tiles[t.key].meaning}
                </p>
                <p className="num mt-2 text-[10px] uppercase tracking-wide text-ink/60">{fill(C.answer.source, { file: t.source })}</p>
              </div>
            ))
          : [0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-36" />)}
      </dl>

      {e?.optical && first && (
        <figure className="mt-8 max-w-3xl">
          <div className="grid grid-cols-2 gap-2">
            {[
              { src: assetUrl(e.optical.after_webp), cap: C.answer.compareOptical },
              { src: assetUrl(first.after_png), cap: fill(C.answer.compareRadar, { date: fmtDayYear(first.after) }) },
            ].map((im) => (
              <div key={im.src}>
                <img src={im.src} alt={im.cap} width={IMG_PX} height={IMG_PX} loading="lazy" decoding="async" className="aspect-square w-full rounded-card border border-ink/15 bg-ink object-cover" />
                <p className="mt-1 text-xs text-ink/75">{im.cap}</p>
              </div>
            ))}
          </div>
          <figcaption className="mt-2 text-lg font-semibold">{C.answer.compareCaption}</figcaption>
          <p className="text-xs text-ink/70">{e.optical.attribution}</p>
        </figure>
      )}

      <div className="no-print mt-6 flex flex-wrap gap-3">
        <a href="#map" className="rounded-card bg-brand px-5 py-2.5 font-semibold text-ink transition-opacity duration-150 hover:opacity-90">{C.answer.openMap}</a>
        <a href="#sure" className="rounded-card border border-ink px-5 py-2.5 font-semibold transition-colors duration-150 hover:bg-ink/5">{C.answer.howSure}</a>
      </div>
    </section>
  );
}
