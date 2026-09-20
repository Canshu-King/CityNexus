/* Vite's development service worker, registered from src/main.tsx.
 *
 * Two defects lived here, both of which turned one network blip into a page that looked
 * broken rather than a page that failed to load:
 *
 *  1. the catch-all fallback answered *any* failed GET with the HTML shell, including a
 *     `.js` module or a stylesheet.  The browser then parsed HTML as a script, the app
 *     half-booted, and that half-booted document got written back into the cache -- which
 *     is how "white screen that survives a reload" happened.
 *  2. activate deleted every cache whose name was not this worker's own, so a dev session
 *     wiped the same origin's Workbox production caches (`workbox-precache-*`,
 *     `citynexus-pages`, `citynexus-static`).  That is the other half of "I rebuilt and a
 *     refresh still gave me the old shell".
 *
 * Production uses the versioned Workbox worker instead; this file stays registered so the
 * gates that require a controlling service worker keep working under `vite dev`.
 */

const CACHE = "citynexus-trip-operations-v1";
const CACHE_PREFIX = "citynexus-trip-operations-";
const APP_SHELL = ["/v8/live", "/manifest.webmanifest", "/favicon.svg"];

self.addEventListener("install", (event) => {
  // allSettled, not all: if one shell URL is unreachable the worker must still install.
  // A rejected install leaves the *previous* worker in control, which is exactly the
  // stale-shell state this file is meant to clear.
  event.waitUntil(
    caches
      .open(CACHE)
      .then((cache) => Promise.allSettled(APP_SHELL.map((url) => cache.add(url)))),
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then(async (keys) => {
        // Only caches this worker owns.  Anything else on the origin belongs to
        // another strategy and is not ours to destroy.
        const doomed = keys.filter((key) => key.startsWith(CACHE_PREFIX) && key !== CACHE);
        await Promise.all(doomed.map((key) => caches.delete(key)));
        /* Record what this activation deleted.  Without it, "the cleanup is scoped" is not
           observable from outside the worker: a test that only lists caches afterwards
           cannot tell a scoped cleanup from one that never ran. */
        const own = await caches.open(CACHE);
        await own.put(
          "/__sw_activate_report__",
          new Response(
            JSON.stringify({
              /* Which script this activation belongs to.  Without it a reader cannot tell
                 this activation from the previous worker's, and a poll for "a report"
                 always finds the stale one. */
              script: self.location.href,
              deleted: doomed,
              kept: keys.filter((key) => !doomed.includes(key)),
            }),
            { headers: { "content-type": "application/json" } },
          ),
        );
      })
      .then(() => self.clients.claim()),
  );
});

self.addEventListener("fetch", (event) => {
  const request = event.request;
  if (request.method !== "GET") return;

  const url = new URL(request.url);
  // Vite's dev client and source modules are live compiler resources: a dev worker must
  // keep them network-first so a normal reload observes the current module graph.
  if (
    url.origin !== self.location.origin ||
    url.pathname.startsWith("/api/") ||
    url.pathname.includes("hot-update")
  )
    return;

  /* Code and styles are network-only, and an HTML body is never a valid answer for them.

     Checking `request.destination` alone was not enough: a measured gate run showed the
     dev server answering an unknown `.js` path with a 200 `text/html` document, and a
     module pulled in through fetch() carries destination "empty", so the HTML still
     reached a code request.  The extension check closes that hole, and the content-type
     check closes the one where the network itself is the thing handing back HTML --
     whoever produced it, HTML parsed as a script is how a hiccup became a white screen. */
  const CODE_PATH = /\.(js|mjs|cjs|css)$/i;
  const isCode =
    ["script", "style", "worker"].includes(request.destination) || CODE_PATH.test(url.pathname);

  if (isCode) {
    event.respondWith(
      fetch(request).then((response) => {
        if (/text\/html/i.test(response.headers.get("content-type") ?? "")) {
          // Fail the request honestly instead of serving a document where code belongs.
          return Response.error();
        }
        const copy = response.clone();
        event.waitUntil(
          caches.open(CACHE).then((cache) => cache.put(request, copy)).catch(() => undefined),
        );
        return response;
      }),
    );
    return;
  }

  event.respondWith(
    fetch(request)
      .then((response) => {
        const copy = response.clone();
        event.waitUntil(
          caches.open(CACHE).then((cache) => cache.put(request, copy)).catch(() => undefined),
        );
        return response;
      })
      .catch(() =>
        caches.match(request).then((cached) => {
          if (cached) return cached;
          // Offline may still show the shell, but only for a real navigation.  Anything
          // else keeps its original failure instead of receiving HTML.
          if (request.mode === "navigate") {
            return caches.match("/v8/live").then((shell) => shell ?? Response.error());
          }
          return Response.error();
        }),
      ),
  );
});
