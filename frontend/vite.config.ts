import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";

const isStorybook = Boolean(process.env.STORYBOOK);

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      disable: isStorybook,
      filename: "v10-sw.js",
      registerType: "autoUpdate",
      // main.tsx owns the environment-specific registration: /sw.js in
      // development and /v10-sw.js in production.  Letting vite-plugin-pwa
      // auto-inject its dev-sw.js as well creates two competing controllers
      // and makes repeated navigation/reload nondeterministic.
      injectRegister: false,
      includeAssets: ["favicon.svg"],
      manifest: {
        name: "CityNexus Live Journey",
        short_name: "CityNexus",
        description: "Read-only offline journey execution companion",
        theme_color: "#092e34",
        background_color: "#f4f6f2",
        display: "standalone",
        start_url: "/v8/live",
        icons: [{ src: "/favicon.svg", sizes: "any", type: "image/svg+xml" }],
      },
      workbox: {
        // The product shell now includes the real mission timeline and MCP
        // disclosure UI. Keep the single application chunk precacheable while
        // retaining Workbox's safety ceiling.
        maximumFileSizeToCacheInBytes: 3 * 1024 * 1024,
        navigateFallback: "/index.html",
        additionalManifestEntries: [{ url: "/index.html", revision: "v10-shell" }],
        cleanupOutdatedCaches: true,
        runtimeCaching: [
          {
            urlPattern: ({ request, url }) =>
              request.destination === "document" && url.pathname.startsWith("/v8/"),
            handler: "NetworkFirst",
            options: {
              cacheName: "citynexus-pages",
              /* Measured from this machine against the live public tunnel path
                 (`review/tunnel-latency.txt`, 10 samples, unauthenticated so the response
                 is a 401 but the whole DNS + TLS + request path is traversed):
                   warm request  0.86s – 1.06s
                   cold request  2.96s  (DNS 0.03s + TLS 2.18s + request)
                   re-handshake  1.81s
                 Loopback floor for the same document is p50 0.9ms / p95 21ms, so the
                 server is never the constraint.  A 3s budget is therefore smaller than a
                 single cold connection on a *healthy* link: the timeout fires, the worker
                 answers with the cached shell, and the traveller reads "I can't get back to
                 the screen I was on".  10s is ~3.4x the cold sample and still bounds a
                 genuinely dead network.  Not measured here: the cellular leg itself. */
              networkTimeoutSeconds: 10,
              /* `0` used to be listed here.  An opaque/empty response is not a page worth
                 serving, and once cached under a NetworkFirst rule it becomes the answer
                 every time the network is even slightly slow. */
              cacheableResponse: { statuses: [200] },
            },
          },
          {
            urlPattern: ({ request, url }) =>
              !url.pathname.startsWith("/api/") &&
              ["script", "style", "worker", "image", "font"].includes(
                request.destination,
              ),
            /* Was CacheFirst, which never asks the network again: a rebuilt bundle kept
               serving its old bytes and "I rebuilt but the refresh shows the old shell"
               was the report.  StaleWhileRevalidate serves what it has and updates it. */
            handler: "StaleWhileRevalidate",
            options: {
              cacheName: "citynexus-static",
              cacheableResponse: { statuses: [200] },
            },
          },
        ],
      },
      devOptions: {
        enabled: false,
        navigateFallbackAllowlist: [/^\/(?:v8|index)/],
      },
    }),
  ],
  server: {
    proxy: {
      "/api/v1": {
        target: `http://127.0.0.1:${Number(process.env.CITYNEXUS_BACKEND_PORT ?? 8000)}`,
        changeOrigin: false,
      },
    },
  },
  /* `vite preview` deliberately does not inherit `server.proxy`.  Without this the
     production build cannot be walked end to end, and the user-facing gates would have to
     be evidenced against a dev server -- which is not the thing that ships. */
  preview: {
    proxy: {
      "/api/v1": {
        target: `http://127.0.0.1:${Number(process.env.CITYNEXUS_BACKEND_PORT ?? 8000)}`,
        changeOrigin: false,
      },
    },
  },
});
