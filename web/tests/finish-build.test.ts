import assert from 'node:assert/strict';
import { mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import test from 'node:test';
import { apiOrigin, applyHeaders, finish, mockFiles } from '../scripts/finish-build.ts';

const HEADERS = readFileSync(new URL('../public/_headers', import.meta.url), 'utf-8');

test('only plain https origins are accepted', () => {
  assert.equal(apiOrigin(undefined), '');
  assert.equal(apiOrigin('  '), '');
  assert.equal(apiOrigin('https://cut-off.azurewebsites.net'), 'https://cut-off.azurewebsites.net');
  assert.equal(apiOrigin('https://cut-off.azurewebsites.net/api/path?x=1'), 'https://cut-off.azurewebsites.net');
  assert.equal(apiOrigin('http://localhost:8000'), 'http://localhost:8000');
  for (const bad of [
    'http://example.com', 'ftp://example.com', 'javascript:alert(1)', 'not a url', 'https://user:pw@example.com',
    "https://example.com; script-src *", 'https://example.com, https://evil.example', "https://exa'mple.com", 'https://*.example.com',
    'data:text/html,hi',
  ]) {
    assert.throws(() => apiOrigin(bad), Error, bad);
  }
});

test('the headers file has the placeholder and a strict policy', () => {
  assert.match(HEADERS, /connect-src 'self' https:\/\/gibs\.earthdata\.nasa\.gov __API_ORIGIN__/);
  assert.match(HEADERS, /img-src 'self' data: blob: https:\/\/gibs\.earthdata\.nasa\.gov __API_ORIGIN__/);
  for (const must of ["default-src 'self'", "script-src 'self'", "object-src 'none'", "frame-ancestors 'self'", 'nosniff', 'strict-origin-when-cross-origin', 'Permissions-Policy']) {
    assert.ok(HEADERS.includes(must), must);
  }
  assert.ok(!/unsafe-inline|unsafe-eval/.test(HEADERS));
});

test('the API origin is added to connect-src and img-src, and only there', () => {
  const out = applyHeaders(HEADERS, 'https://api.example.com');
  assert.equal(out.split('https://api.example.com').length - 1, 2);
  assert.match(out, /connect-src [^;]*https:\/\/api\.example\.com/);
  assert.match(out, /img-src [^;]*https:\/\/api\.example\.com/);
  assert.ok(!out.includes('__API_ORIGIN__'));
  assert.ok(!/script-src [^;]*api\.example\.com/.test(out));
});

test('without an API address nothing is added', () => {
  const out = applyHeaders(HEADERS, '');
  assert.ok(!out.includes('__API_ORIGIN__') && !out.includes('azurewebsites'));
  assert.match(out, /connect-src 'self' https:\/\/gibs\.earthdata\.nasa\.gov;/);
});

test('a headers file without a policy is refused', () => {
  assert.throws(() => applyHeaders('/*\n  X-Frame-Options: DENY\n', ''));
});

function fakeDist(mock: boolean) {
  const dist = mkdtempSync(join(tmpdir(), 'dist-'));
  writeFileSync(join(dist, '_headers'), HEADERS, 'utf-8');
  mkdirSync(join(dist, 'data', 'panama-2026'), { recursive: true });
  writeFileSync(join(dist, 'data', 'panama-2026', 'event.json'), JSON.stringify({ mock }));
  writeFileSync(join(dist, 'data', 'panama-2026', 'stats.json'), JSON.stringify({ mock }));
  return dist;
}

test('mock data is only a warning unless real data is required', () => {
  const dist = fakeDist(true);
  try {
    assert.deepEqual(mockFiles(join(dist, 'data')), ['panama-2026/event.json', 'panama-2026/stats.json']);
    const r = finish(dist, { apiUrl: 'https://api.example.com' });
    assert.equal(r.origin, 'https://api.example.com');
    assert.equal(r.mock.length, 2);
    assert.throws(() => finish(fakeDist(true), { requireReal: '1' }), /still mock data/);
  } finally {
    rmSync(dist, { recursive: true, force: true });
  }
});

test('real data passes the strict build and the headers are written', () => {
  const dist = fakeDist(false);
  try {
    const r = finish(dist, { apiUrl: 'https://api.example.com', requireReal: '1' });
    assert.deepEqual(r.mock, []);
    assert.match(readFileSync(join(dist, '_headers'), 'utf-8'), /connect-src 'self' https:\/\/gibs\.earthdata\.nasa\.gov https:\/\/api\.example\.com;/);
  } finally {
    rmSync(dist, { recursive: true, force: true });
  }
});

test('a build without a headers file fails', () => {
  const dist = mkdtempSync(join(tmpdir(), 'dist-'));
  try {
    assert.throws(() => finish(dist, {}), /_headers is missing/);
  } finally {
    rmSync(dist, { recursive: true, force: true });
  }
});
