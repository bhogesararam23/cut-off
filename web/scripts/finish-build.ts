// Runs after `vite build`:
//  1. Puts the API address (VITE_API_URL) into the content security policy in dist/_headers, so the browser may
//     talk to it. Only a plain https origin is accepted (http only for localhost): nothing else can be injected.
//  2. With REQUIRE_REAL_DATA=1, fails the build if any data file in dist/data still says "mock": true.
// Node runs this file directly (type stripping), so keep it to plain syntax.
import { existsSync, readdirSync, readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';

const PLACEHOLDER = ' __API_ORIGIN__';

/** The origin of an API address, or '' if there is none. Throws for anything that is not a safe origin. */
export function apiOrigin(value: string | undefined): string {
  const v = (value ?? '').trim();
  if (!v) return '';
  let u: URL;
  try {
    u = new URL(v);
  } catch {
    throw new Error(`VITE_API_URL is not a valid address: ${JSON.stringify(v)}`);
  }
  const local = u.hostname === 'localhost' || u.hostname === '127.0.0.1';
  if (!(u.protocol === 'https:' || (u.protocol === 'http:' && local))) {
    throw new Error('VITE_API_URL must start with https:// (http:// is only allowed for localhost)');
  }
  if (u.username || u.password || /[\s;,'"*]/.test(v)) {
    throw new Error('VITE_API_URL must be a plain address without credentials or special characters');
  }
  return u.origin;
}

/** The headers file with the API origin added (or removed, when there is none). */
export function applyHeaders(text: string, origin: string): string {
  const out = text.split(PLACEHOLDER).join(origin ? ` ${origin}` : '');
  if (out.includes('__API_ORIGIN__')) throw new Error('an API placeholder was left in the headers file');
  if (!/Content-Security-Policy:.*default-src 'self'/.test(out)) throw new Error('the headers file has no content security policy');
  return out;
}

/** Names of data files that are marked as mock data. */
export function mockFiles(dataDir: string): string[] {
  const found: string[] = [];
  if (!existsSync(dataDir)) return found;
  for (const ev of readdirSync(dataDir, { withFileTypes: true })) {
    if (!ev.isDirectory()) continue;
    for (const name of ['event.json', 'stats.json']) {
      const p = join(dataDir, ev.name, name);
      if (existsSync(p) && JSON.parse(readFileSync(p, 'utf-8')).mock === true) found.push(`${ev.name}/${name}`);
    }
  }
  return found;
}

export interface Result {
  origin: string;
  mock: string[];
}

export function finish(dist: string, env: { apiUrl?: string; requireReal?: string }): Result {
  const origin = apiOrigin(env.apiUrl);
  const headers = join(dist, '_headers');
  if (!existsSync(headers)) throw new Error('dist/_headers is missing: the security headers would not be applied');
  writeFileSync(headers, applyHeaders(readFileSync(headers, 'utf-8'), origin), 'utf-8');
  const mock = mockFiles(join(dist, 'data'));
  if (mock.length && env.requireReal === '1') {
    throw new Error(`these data files are still mock data (mock: true): ${mock.join(', ')}. Process the real data first.`);
  }
  return { origin, mock };
}

// run as a script
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const { loadEnv } = await import('vite');
  const fileEnv = loadEnv(process.env.MODE ?? 'production', process.cwd(), 'VITE_');
  try {
    const r = finish(join(process.cwd(), 'dist'), {
      apiUrl: process.env.VITE_API_URL ?? fileEnv.VITE_API_URL,
      requireReal: process.env.REQUIRE_REAL_DATA,
    });
    console.log(r.origin ? `security headers: allowed the API at ${r.origin}` : 'security headers: no API address set (the site uses its own data files)');
    if (r.mock.length) console.warn(`warning: mock data in this build (${r.mock.join(', ')}). Set REQUIRE_REAL_DATA=1 for a production build.`);
  } catch (e) {
    console.error(`build check failed: ${(e as Error).message}`);
    process.exit(1);
  }
}
