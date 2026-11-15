// The first-screen numbers, the "too few to score" rule, the footer rules and forbidden strings.
import assert from 'node:assert/strict';
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';
import test from 'node:test';
import { answerTiles, baselineFails, confusion, MIN_N_TO_SCORE, sizeRows } from '../src/lib/answer.ts';
import { C } from '../src/lib/content.ts';
import type { Stats } from '../src/lib/types.ts';

const ROOT = new URL('..', import.meta.url);
const read = (rel: string) => readFileSync(new URL(rel, ROOT), 'utf-8');
const stats: Stats = JSON.parse(read('public/data/panama-2026/stats.json'));

test('the key facts show exactly the values in stats.json', () => {
  const tiles = Object.fromEntries(answerTiles(stats).map((t) => [t.key, t]));
  assert.equal(tiles.landslides.value, stats.landslides);
  assert.equal(tiles.roads.value, stats.roads_blocked_km);
  assert.equal(tiles.communities.value, stats.communities_cut_off);
  assert.equal(tiles.landslides.source, 'stats.json');
});

test('missing values stay missing: never a guess', () => {
  const tiles = answerTiles({ ...stats, roads_blocked_km: null, communities_cut_off: null });
  assert.equal(tiles.find((t) => t.key === 'roads')?.value, null);
  assert.equal(tiles.find((t) => t.key === 'communities')?.value, null);
});

test('size groups with too few points get no score', () => {
  const rows = sizeRows([{ size: 'small', n: 30, detection_rate: 0.13 }, { size: 'large', n: 2, detection_rate: 1 }]);
  assert.deepEqual(rows.map((r) => [r.size, r.n, r.scored]), [['small', 30, true], ['medium', 0, false], ['large', 2, false]]);
  assert.equal(MIN_N_TO_SCORE, 5);
  assert.match(C.sure.chart1TooFew, /too few to score/);
});

test('counts behind the rates add up to the number of test points', () => {
  const v = stats.validation;
  assert.ok(v, 'validation is present in the real data');
  const cm = confusion(v);
  assert.equal(cm.found + cm.missed, v.n_test_landslide);
  assert.equal(cm.falseAlarms + cm.correctForest, v.n_test_forest);
  assert.ok(Math.abs(cm.found / v.n_test_landslide - v.detection_rate) < 0.01);
});

test('a failing pre-event baseline is detected', () => {
  assert.equal(baselineFails({ ...stats, baseline_no_change_flag_rate: 0.03, post_event_flag_rate: 0.02 }), true);
  assert.equal(baselineFails({ ...stats, baseline_no_change_flag_rate: 0.001, post_event_flag_rate: 0.02 }), false);
});

test('the footer carries the disclaimer, credits, licence and AI line', () => {
  assert.equal(C.footer.disclaimer, 'Built for the NASA International Space Apps Challenge 2026. Not affiliated with or endorsed by NASA or ISRO.');
  const credits = C.footer.credits.join(' | ');
  for (const must of ['NISAR', 'Alaska Satellite Facility', 'Copernicus DEM GLO-30', 'Contains modified Copernicus Sentinel data 2026', 'OpenStreetMap contributors (ODbL)', 'NASA GIBS', 'EMSR934']) {
    assert.ok(credits.includes(must), must);
  }
  assert.match(C.footer.licence, /project code is licensed under Apache 2\.0/);
  assert.match(C.footer.ai, /AI tools assisted/);
  assert.match(read('src/components/Sections.tsx'), /C\.footer\.disclaimer/);
  assert.match(C.footer.licence, /Datasets and third-party material keep their own terms/);
});

test('wording: the product name has no agency name and claims are qualified', () => {
  assert.equal(C.topBar.title, 'Cut Off');
  assert.match(C.page.title, /Candidate landslides/);
  assert.match(C.page.title, /possibly cut off/);
  assert.match(C.page.title, /likely blocked/);
});

function walk(dir: string): string[] {
  return readdirSync(dir).flatMap((n) => {
    const p = join(dir, n);
    return statSync(p).isDirectory() ? walk(p) : [p];
  });
}

test('no forbidden strings, logos or trackers in the site sources and data', () => {
  const base = new URL('.', ROOT).pathname.replace(/^\/([A-Za-z]:)/, '$1');
  const files = [...walk(join(base, 'src')), ...walk(join(base, 'public')), join(base, 'index.html')].filter((f) => /\.(tsx?|css|html|json|geojson)$/.test(f) || f.endsWith('_headers'));
  const forbidden = ['meatball', 'logo-nasa', 'Mock Road', 'Mock Village', 'googletagmanager', 'google-analytics', 'fonts.googleapis', 'gtag('];
  for (const f of files) {
    const text = readFileSync(f, 'utf-8');
    for (const bad of forbidden) assert.ok(!text.includes(bad), `${bad} found in ${f}`);
  }
  assert.ok(files.length > 20);
});

test('audit wording: no overclaims anywhere in the visible text', () => {
  const all = JSON.stringify(C);
  for (const bad of [/sealed/i, /through both/i, /through leaves/i, /nothing happened/i, /every claim is cited/i, /everything is open source/i, /Open source under/i,
    /independent test/i, /found \d[\d,]* landslides/i, /real-time/i, /confirmed landslides? (were|are) found/i]) {
    assert.doesNotMatch(all, bad);
  }
  assert.match(C.page.splitNote, /not independent geographic validation and not field validation/);
  assert.match(C.sure.splitNote, /random split of points within one study area/);
  assert.match(C.method.radarNote, /a change is a lead, not a confirmed landslide/);
  assert.match(C.landslides.supportHelp, /not the probability that a landslide happened/);
  assert.deepEqual(Object.values(C.landslides.supportLabels), ['Seen in many passes', 'Seen in 2 passes', 'Seen in 1 pass']);
  assert.match(C.sure.baselineText, /20 Sep to 2 Oct 2026/);
  assert.match(C.sure.p2, /scored twice/);
});

test('the two source links the audit asked for are on the page', () => {
  assert.match(C.page.quakeUrl, /us6000u18k/);
  assert.match(read('src/components/Overview.tsx'), /EMSR934|referenceLabel/);
});
