// Reach probe: what is actually on the two routes whose controls the ruler missed?
import { createRequire } from "node:module";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
const require = createRequire(import.meta.url);
const HERE = dirname(fileURLToPath(import.meta.url));
const { chromium } = require(resolve(join(HERE, "..", "..", "frontend", "node_modules", "playwright"), "."));

const BASE = process.env.BASE_URL || "http://127.0.0.1:5399";
const JOURNEY = process.env.CITYNEXUS_JOURNEY_ID || "";
const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 390, height: 844 } });
const page = await ctx.newPage();
await page.goto(`${BASE}/hub`);
await page.evaluate((id) => localStorage.setItem("citynexus.v8.journey_id", id), JOURNEY);

for (const route of ["/v8/bookings", "/legacy"]) {
  const res = await page.goto(`${BASE}${route}`, { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(1400);
  const dump = await page.evaluate(() => ({
    status_selects: Array.from(document.querySelectorAll("select")).map((s) => ({
      testid: s.getAttribute("data-testid"),
      h: Math.round(s.getBoundingClientRect().height),
      opts: s.options.length,
    })),
    testids: Array.from(document.querySelectorAll("[data-testid]")).map((n) => n.getAttribute("data-testid")).slice(0, 60),
    body_chars: document.body.innerText.trim().length,
    heading: (document.querySelector("h1,h2") || {}).textContent || null,
  }));
  console.log(JSON.stringify({ route, http: res ? res.status() : 0, ...dump }, null, 1));
}
await browser.close();
