/* Increment the cache version when app code, bank, or Python runtime changes. */
const CACHE = 'cacm-python-pack-2026-10-04-v5';
const PREFIX = 'cacm-python-pack-';
const ASSETS = [
  '/coding/', '/coding/index.html', '/coding/app.css', '/coding/app.js',
  '/coding/core.js', '/coding/db.js', '/coding/runner.js', '/coding/revision.js', '/coding/worker.mjs',
  '/coding/harness.py', '/coding/data/questions.json', '/coding/data/solutions.json', '/coding/manifest.webmanifest', '/coding/icon.svg',
  '/coding/runtime/pyodide.mjs', '/coding/runtime/pyodide.asm.mjs',
  '/coding/runtime/pyodide.asm.wasm', '/coding/runtime/python_stdlib.zip', '/coding/runtime/pyodide-lock.json'
];
self.addEventListener('install', event => {
  event.waitUntil((async () => {
    const cache = await caches.open(CACHE);
    // A failed download never becomes an activated, supposedly complete pack.
    for (const url of ASSETS) await cache.add(new Request(url, { cache: 'reload' }));
    await self.skipWaiting();
  })());
});
self.addEventListener('activate', event => {
  event.waitUntil((async () => {
    for (const key of await caches.keys()) if (key.startsWith(PREFIX) && key !== CACHE) await caches.delete(key);
    await self.clients.claim();
  })());
});
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);
  if (event.request.method !== 'GET' || url.origin !== location.origin || !url.pathname.startsWith('/coding/')) return;
  // API calls are outside this scope and are never cached.
  event.respondWith((async () => {
    const cache = await caches.open(CACHE);
    const key = event.request.mode === 'navigate' ? '/coding/' : url.pathname;
    const cached = await cache.match(key);
    return cached || fetch(event.request);
  })());
});
self.addEventListener('message', event => {
  if (!['PACK_STATUS', 'REPAIR_PACK'].includes(event.data?.type)) return;
  event.waitUntil((async () => {
    const cache = await caches.open(CACHE);
    if (event.data.type === 'REPAIR_PACK') {
      try {
        for (const asset of ASSETS) if (!await cache.match(asset)) await cache.add(new Request(asset, { cache: 'reload' }));
      } catch (error) { event.ports[0]?.postMessage({ ready: false, error: error.message }); return; }
    }
    const missing = [];
    for (const asset of ASSETS) if (!await cache.match(asset)) missing.push(asset);
    event.ports[0]?.postMessage({ ready: missing.length === 0, version: CACHE, missing });
  })());
});
