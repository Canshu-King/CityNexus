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
              /* Document-navigation latency, measured against the live public entry the user
                 is actually on (`review/tunnel-latency-n20.txt`, 20 unauthenticated GETs of
                 /v8/live, so the whole DNS + TLS + tunnel + auth-proxy path is traversed and
                 only the tiny 401 body comes back):
                   min 0.84s  p50 1.59s  p90 3.88s  p95 10.47s  max 20.93s
                   4 of 20 above 3s, 2 of 20 above 8s
                 Loopback floor for the same document is p50 0.9ms / p95 21ms, so the server
                 is never the constraint -- the tail is the tunnel leg.  A 3s budget is below
                 a fifth of real navigations, and even a body as small as this one understates
                 a real shell, so the percentiles here are a lower bound.
                 Kept out of this number on purpose: API/provider operation latency.  The
                 backend lane measured a stay search at 120.86s on the provider chain, and a
                 slow API call is no reason to let an HTML navigation hang.
                 What 10s does not fix: roughly one navigation in ten still falls back to the
                 cached shell. That fallback is the designed answer (a stale page beats a
                 spinner), and the remaining tail belongs to the shared tunnel, not here. */
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
