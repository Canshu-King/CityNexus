import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

/* Serves only `harness/tooltip-harness.html`, with the real components and the real token layer.
   It is its own config rather than `vite.config.ts` for two reasons: the product config installs
   the PWA service worker, and a second controller on a reused port is how a stale shell gets
   mistaken for a dead component; and `cacheDir` is moved off `node_modules/.vite`, because this
   lane's `node_modules` is a junction into a tree other lanes are using, and optimized deps
   written there are a write into somebody else's checkout. */
export default defineConfig({
  plugins: [react()],
  cacheDir: "node_modules/.vite_tooltip_1008",
  server: { port: 6111, host: "127.0.0.1", strictPort: true },
});
