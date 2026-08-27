// Minimal service worker: makes the app installable and caches the static
// shell (icons, logo, this script) so the icon/theme survive a flaky
// connection. Everything else (pages, /api/*) is always fetched fresh from
// the network — flight prices and expenses must never be served stale.
const CACHE_NAME = "flight-finder-shell-v1";
const SHELL_ASSETS = [
  "/static/logo.png",
  "/static/icons/icon-192.png",
  "/static/icons/icon-512.png",
  "/static/icons/apple-touch-icon.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(SHELL_ASSETS))
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((names) =>
      Promise.all(
        names.filter((name) => name !== CACHE_NAME).map((name) => caches.delete(name))
      )
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;

  const url = new URL(request.url);
  if (!SHELL_ASSETS.includes(url.pathname)) return;

  event.respondWith(
    caches.match(request).then((cached) => cached || fetch(request))
  );
});
