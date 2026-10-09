import { chromium } from "playwright";
import { mkdirSync } from "node:fs";

const BASE = process.argv[2] ?? "http://localhost:5611";
const JID = process.argv[3] ?? "d13611bd-8c60-4c76-b1ef-200e2e2aff23";
const DIR = process.argv[4] ?? "_sidebar_shots";
mkdirSync(DIR, { recursive: true });

const b = await chromium.launch();
const shot = async (name, { w, h, act }) => {
  const ctx = await b.newContext({ viewport: { width: w, height: h }, deviceScaleFactor: 2 });
  await ctx.addInitScript((jid) => {
    localStorage.setItem("citynexus.v8.journey_id", jid);
    localStorage.removeItem("citynexus.v8.sidebar_collapsed");
  }, JID);
  const p = await ctx.newPage();
  await p.goto(`${BASE}/v8/hub`, { waitUntil: "domcontentloaded" });
  await p.waitForSelector(".v8-product-shell", { timeout: 20000 });
  await p.waitForTimeout(1200);
  if (act) await act(p);
  await p.screenshot({ path: `${DIR}/${name}.png` });
  await ctx.close();
  console.log("shot " + name);
};

await shot("a-desktop-open", { w: 1440, h: 900 });
await shot("b-desktop-collapsed", {
  w: 1440,
  h: 900,
  act: async (p) => {
    await p.click(".v8-sidebar-toggle");
    await p.waitForTimeout(500);
  },
});
await shot("c-desktop-short-viewport", { w: 1280, h: 560 });
await shot("d-mobile-drawer", {
  w: 390,
  h: 844,
  act: async (p) => {
    await p.click(".v8-mobile-menu");
    await p.waitForTimeout(500);
  },
});
await b.close();
console.log("SIDEBAR_SHOTS_DONE dir=" + DIR);
