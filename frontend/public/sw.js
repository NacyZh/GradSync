const CACHE_PREFIX = 'gradsync-shell-';
const BUILD_REVISION = '__GRADSYNC_BUILD_REVISION__';
const CACHE_NAME = `${CACHE_PREFIX}${BUILD_REVISION}`;
const APP_SHELL = ['/', '/index.html', '/manifest.webmanifest', '/asset-manifest.json'];

async function precacheApplication() {
  const manifestResponse = await fetch('/asset-manifest.json', { cache: 'no-store' });
  const manifest = await manifestResponse.json();
  const builtAssets = Object.values(manifest).flatMap((entry) => [
    entry.file,
    ...(entry.css || []),
    ...(entry.assets || []),
  ]).filter(Boolean).map((file) => `/${file}`);
  const cache = await caches.open(CACHE_NAME);
  await cache.addAll([...new Set([...APP_SHELL, ...builtAssets])]);
}

self.addEventListener('install', (event) => {
  event.waitUntil(precacheApplication());
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((key) => key.startsWith(CACHE_PREFIX) && key !== CACHE_NAME).map((key) => caches.delete(key))))
      .then(() => self.clients.claim()),
  );
});

self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);
  if (
    request.method !== 'GET'
    || url.origin !== self.location.origin
    || url.pathname.startsWith('/api/')
    || url.pathname.startsWith('/media/')
    || request.headers.has('Authorization')
  ) return;

  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request).catch(async () => (
        (await caches.match('/index.html')) || (await caches.match('/')) || Response.error()
      )),
    );
    return;
  }

  if (url.pathname.startsWith('/assets/') || ['script', 'style', 'font', 'image'].includes(request.destination)) {
    event.respondWith(
      caches.match(request).then(async (cached) => {
        if (cached) return cached;
        const response = await fetch(request);
        if (response.ok && response.type === 'basic') {
          const cache = await caches.open(CACHE_NAME);
          await cache.put(request, response.clone());
        }
        return response;
      }),
    );
  }
});
