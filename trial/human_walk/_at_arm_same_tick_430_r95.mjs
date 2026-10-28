import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";

// One run answers both questions in order.  First: does the trips tab exist on this screen, measured
// as three counts inside a single evaluate (the previous arm compared readings taken at different
// moments and that is exactly what made the timing explanation unfalsifiable).  Then it is re-read
// every few seconds, so "never rendered" and "rendered later" are different answers.  Only after
// that does the walk continue to the save key and press it twice -- the 409 screen proof.
const DIR = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261026_gozero";
const OUT = `${DIR}/at-same-tick-430-r95.txt`;
const NL = String.fromCharCode(10);
const lines = [];
const note = (v) => { lines.push(v); fs.writeFileSync(OUT, lines.join(NL) + NL, "utf8"); };
const started = Date.now();
const elapsed = () => ((Date.now() - started) / 1000).toFixed(1);
const UUID = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i;
const IDS = {
  nav: "[data-testid=\"rev-mobile-bottom-nav\"]",
  trips: "[data-testid=\"rev-mobile-tab-trips\"]",
  explore: "[data-testid=\"rev-mobile-tab-explore\"]",
  me: "[data-testid=\"rev-mobile-tab-me\"]",
};

const ctx = await chromium.launchPersistentContext("D:/moodle/_cmdr_v3_live_1022/_chrome_gozero_aq92", {
  channel: "chrome", headless: false, viewport: { width: 430, height: 932 }, deviceScaleFactor: 1,
});
const page = ctx.pages()[0] ?? await ctx.newPage();
page.on("response", async (resp) => {
  const url = resp.url(); const method = resp.request().method();
  if (!url.includes("/api/v1/") || (method !== "POST" && method !== "PUT")) return;
  if (!/goal-tasks|plans|journeys|departure/.test(url)) return;
  const line = `HTTP ${method} ${resp.status()} ${url.replace(/^http:\/\/[^/]+/, "")}`;
  if (resp.status() >= 400) {
    let d = ""; try { d = JSON.stringify(await resp.json()).slice(0, 800); } catch { d = "(unreadable)"; }
    note(line + " BODY " + d);
  } else note(line);
});
page.on("pageerror", (e) => note("PAGEERROR " + String(e).slice(0, 200)));

const sameTick = () => page.evaluate((ids) => {
  const c = (s) => document.querySelectorAll(s).length;
  const nav = document.querySelector(ids.nav);
  const labels = nav ? Array.from(nav.querySelectorAll("button")).map((b) => (b.getAttribute("aria-label") || b.innerText || "").replace(/\s+/g, " ").slice(0, 12)) : [];
  return { nav: c(ids.nav), trips: c(ids.trips), explore: c(ids.explore), me: c(ids.me), labels, href: location.pathname + location.search };
}, IDS);

async function pressLoc(locator, label, timeout = 8000) {
  const target = locator.first();
  try { await target.waitFor({ state: "visible", timeout }); } catch { note(`MISS ${label}`); return false; }
  await target.evaluate((n) => n.scrollIntoView({ block: "center" })).catch(() => {});
  await page.waitForTimeout(300);
  const ok = await target.evaluate((n) => {
    const b = n.getBoundingClientRect();
    if (!b.width || !b.height) return false;
    const top = document.elementFromPoint(b.left + b.width / 2, b.top + b.height / 2);
    return Boolean(top) && (n === top || n.contains(top)) && !n.disabled;
  });
  note(`HIT ${label} ${ok} t=${elapsed()}`);
  if (!ok) return false;
  await target.click({ timeout: 15000 }).catch(() => {});
  await page.waitForTimeout(1200);
  return true;
}
async function shot(name) {
  await page.screenshot({ path: `${DIR}/${name}.png` }).catch(() => {});
  note(`SHOT ${name} t=${elapsed()}`);
}
async function leakReading(label) {
  const band = await page.locator(".rev-plan-message, [role='alert'], [role='status']").allInnerTexts().catch(() => []);
  const body = await page.evaluate(() => document.body.innerText || "").catch(() => "");
  const joined = band.join(" | ");
  note(`${label} TEXTS ${JSON.stringify(band.slice(0, 4))}`);
  note(`${label} LEAK api_in_body=${body.includes("CityNexus API")} api_in_band=${joined.includes("CityNexus API")} uuid_in_band=${UUID.test(joined)}`);
  return joined;
}

await page.goto("http://127.0.0.1:14462/revolution", { waitUntil: "domcontentloaded", timeout: 60000 });
await page.waitForTimeout(6000);
for (let k = 0; k < 8; k += 1) {
  note(`TICK ${k} ${JSON.stringify(await sameTick())} t=${elapsed()}`);
  await page.waitForTimeout(4000);
}
await shot("430-at-first-screen");

const trips = page.locator(IDS.trips);
if (!(await pressLoc(trips, "trips-tab", 8000))) {
  note("ABORT trips tab still not pressable after the tick series -- recording the screen text instead");
  note("SCREEN_TEXT " + JSON.stringify((await page.evaluate(() => document.body.innerText || "")).replace(/\s+/g, " ").slice(0, 300)));
  await ctx.close();
  process.exit(5);
}
await page.waitForTimeout(4000);
note("AFTER_TRIPS " + JSON.stringify(await sameTick()));
await shot("430-at-trips-list");

// Newest trip card, whatever it is called.
const cards = page.locator("article, [data-testid*='trip'], [data-testid*='journey'], li");
const n = await cards.count().catch(() => 0);
note("CARDS " + n);
const saveKey = page.getByRole("button", { name: /保存为正式候选方案/ });
let reached = false;
for (let k = 0; k < Math.min(n, 5); k += 1) {
  if (await pressLoc(cards.nth(k), `card-${k}`, 6000)) {
    await page.waitForTimeout(5000);
    const count = await saveKey.count().catch(() => 0);
    note(`AFTER_CARD ${k} save_key=${count} text=${JSON.stringify((await page.evaluate(() => document.body.innerText || "")).replace(/\s+/g, " ").slice(0, 200))}`);
    if (count) { reached = true; break; }
  }
}
if (!reached) {
  await leakReading("NO_SAVE_KEY");
  await shot("430-at-no-save-key");
  note("ABORT no save key on any card this arm could open");
  await ctx.close();
  process.exit(6);
}

for (const round of [1, 2]) {
  const pressed = await pressLoc(saveKey, `save-${round}`, 30000);
  note(`R${round}_PRESSED ${pressed} t=${elapsed()}`);
  await page.waitForTimeout(round === 1 ? 14000 : 8000);
  await leakReading(`R${round}`);
  await shot(`430-at-after-save-${round}`);
}
const finalBody = await page.evaluate(() => document.body.innerText || "");
note("FINAL_HAS_SAVED " + /已保存\s*\d+\s*项正式安排/.test(finalBody));
note("FINAL_MAPS_SENTENCE " + (/这一版已经排好|不再改草案|刷新一下再继续/.test(finalBody)));
note("DONE t=" + elapsed());
await ctx.close();
