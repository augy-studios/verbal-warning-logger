const CACHE = "vigila-v1";
const SHELL = [
  "/",
  "/css/style.css",
  "/js/app.js",
  "/js/api.js",
  "/js/auth.js",
  "/js/theme.js",
  "/js/router.js",
  "/js/pages/home.js",
  "/js/pages/warnings.js",
  "/js/pages/polls.js",
  "/js/pages/templates.js",
  "/js/pages/auttaja.js",
  "/js/pages/utility.js",
  "/icons/icon.svg",
  "/manifest.json",
];

self.addEventListener("install", (e) => {
  e.waitUntil(
    caches.open(CACHE).then((cache) => cache.addAll(SHELL)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  // Network-first for API calls
  if (url.pathname.startsWith("/api/")) {
    e.respondWith(
      fetch(e.request).catch(() =>
        new Response(JSON.stringify({ error: "Offline" }), {
          status: 503,
          headers: { "Content-Type": "application/json" },
        })
      )
    );
    return;
  }
  // Cache-first for shell assets
  e.respondWith(
    caches.match(e.request).then(
      (cached) => cached || fetch(e.request).then((resp) => {
        if (resp.ok && e.request.method === "GET") {
          const clone = resp.clone();
          caches.open(CACHE).then((cache) => cache.put(e.request, clone));
        }
        return resp;
      })
    )
  );
});
