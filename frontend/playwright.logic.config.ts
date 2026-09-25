/**
 * ORD-0326 -- a config for the pure-logic specs only.
 *
 * The repo's playwright.config.ts starts uvicorn on 127.0.0.1:8000 and `npm run dev` on 4173 with
 * reuseExistingServer:true. `:8000` is NOT AVAILABLE by standing ruling, and reusing whatever happens to
 * listen there would let another lane's backend answer for my assertions. These specs render through
 * react-dom/server and need neither, so this config starts nothing.
 */
import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  testMatch: "server-reason-ord0326.spec.ts",
  reporter: [["list"]],
});
