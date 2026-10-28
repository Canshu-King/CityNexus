import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";

// #332, measured instead of worked around.  Twice this shift a measurement needed a journey that already
// existed, and twice the answer was "start a fresh stack and a fresh journey", because reopening the
// browser appears to lose the traveller.  The question this arm answers on the live screen, with no
// seeded storage and no direct API call:
//
//   phase A -- create a journey the way a traveller does, note the journey id the app itself posts, and
//              print WHICH storage keys hold something (names only; the values are credentials and are
//              never printed), then close the browser the way a traveller closes a laptop;
//   phase B -- reopen the SAME profile directory and observe what the product does by itself: does it
//              land back on that journey, does it ask, or does it show an empty world?
//
// Three outcomes are all readings: RECOVERED / NEEDS_REAUTH_PROMPT / LOST.  Nothing here decides the
// auth design; it reports what a first-time traveller who came back would actually face.
// Isolated canary stack: vite :14464 / backend :60364 from E:/_cmdr_tip_113 (detached dea0328e0b, zero
// dirty, no file carried forward this round), empty database, Amap key inherited from the process
// environment and never printed.
const DIR = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261026_gozero";
const OUT = `${DIR}/bp136-session-recovery-390.txt`;
const PROFILE = "D:/moodle/_cmdr_v3_live_1022/_chrome_gozero_bp136";
const NL = String.fromCharCode(10);
const lines = [];
const note = (v) => { lines.push(v); fs.writeFileSync(OUT, lines.join(NL) + NL, "utf8"); };
const started = Date.now();
const elapsed = () => ((Date.now() - started) / 1000).toFixed(1);
const UUID = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i;

// Key names only.  A value is reported as "set" or "absent" -- the arm never prints a token, a bearer, or
// a body, so this receipt can be pasted into a report without leaking anything.
const storageMap = (label) => page.evaluate((tag) => {
  const grab = (store) => {
    const out = [];
    for (let i = 0; i < store.length; i += 1) {
      const key = store.key(i);
      const raw = store.getItem(key) || "";
      // The shape test has to live inside the page function: an outer constant is not in scope once the
      // body runs in the browser, and the first run of this arm died with "UUID is not defined".
      const shapeUuid = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i;
      out.push({ key, len: raw.length, shape: /^[0-9a-f-]{30,}$/i.test(raw) ? "id-like"
        : raw.startsWith("{") ? "json" : "short-text", hasUuid: shapeUuid.test(raw) });
    }
    return out;
  };
  return { tag, local: grab(window.localStorage), session: grab(window.sessionStorage) };
}, label);

async function boot(candidates) {
  const tried = [];
  for (const dir of candidates) {
    try {
      const box = await chromium.launchPersistentContext(dir, {
        channel: "chrome", headless: false, viewport: { width: 390, height: 844 }, deviceScaleFactor: 1,
      });
      note(`PROFILE_USED ${dir.split("/").pop()} after ${tried.length} failed t=${elapsed()}`);
      return box;
    } catch (error) {
      tried.push(String(error).replace(/\s+/g, " ").slice(0, 120));
      note(`PROFILE_LOCKED ${dir.split("/").pop()} ${tried[tried.length - 1]}`);
    }
  }
  note("ABORT no launchable profile " + JSON.stringify(tried));
  process.exit(9);
}
let page = null;
let ctx = null;
let journeyId = "";
function watch(box) {
  box.on("response", async (resp) => {
    const url = resp.url(); const method = resp.request().method();
    if (!url.includes("/api/v1/")) return;
    if (method !== "POST" && resp.status() < 400) return;
    if (!/journeys|traveler|auth|token|restore|goal-tasks/.test(url)) return;
    note(`HTTP ${method} ${resp.status()} ${url.replace(/^http:\/\/[^/]+/, "")}`);
  });
  box.on("pageerror", (e) => note("PAGEERROR " + String(e).replace(/\s+/g, " ").slice(0, 160)));
}

// ---- phase A: a traveller's very first journey, then a closed laptop -------------------------------
ctx = await boot([PROFILE + "b", PROFILE]);
page = ctx.pages()[0] ?? await ctx.newPage();
watch(ctx);
await page.goto("http://127.0.0.1:14464/revolution", { waitUntil: "domcontentloaded", timeout: 60000 });
await page.waitForTimeout(7000);
const firstScreen = await page.evaluate(() => (document.body.innerText || "").replace(/\s+/g, " ").slice(0, 160));
note(`A_FIRST_SCREEN ${JSON.stringify(firstScreen)} t=${elapsed()}`);
const beforeKeys = await storageMap("A_before");
note(`A_STORAGE_BEFORE ${JSON.stringify(beforeKeys.local.map((k) => k.key))} session=${JSON.stringify(beforeKeys.session.map((k) => k.key))}`);

await page.getByRole("textbox", { name: /想怎么玩/ }).first()
  .fill("2026 年 12 月 3 日到 4 日在北京玩两天，两个人，每段步行不超过 1 公里，太远坐地铁");
await page.waitForTimeout(600);
await page.getByRole("button", { name: /继续规划/ }).first().click().catch(() => note("A_CONTINUE_MISS"));
await page.waitForTimeout(3000);
const posted = lines.filter((l) => l.includes("POST 201 /api/v1/journeys"));
journeyId = ((posted[0] || "").match(UUID) || [""])[0];
note(`A_JOURNEY_ID ${journeyId || "not_seen_in_receipt"}`);
const afterKeys = await storageMap("A_after");
note(`A_STORAGE_AFTER local=${JSON.stringify(afterKeys.local.map((k) => ({ key: k.key, len: k.len, shape: k.shape })))}`);
note(`A_STORAGE_AFTER session=${JSON.stringify(afterKeys.session.map((k) => ({ key: k.key, len: k.len, shape: k.shape })))}`);
await page.screenshot({ path: `${DIR}/390-bp136-phaseA-created.png` }).catch(() => {});
await ctx.close();
note(`A_CLOSED t=${elapsed()}`);

// ---- phase B: reopen the same profile, let the product answer on its own --------------------------
await new Promise((done) => setTimeout(done, 2500));
ctx = await boot([PROFILE + "b", PROFILE]);
page = ctx.pages()[0] ?? await ctx.newPage();
watch(ctx);
await page.goto("http://127.0.0.1:14464/revolution", { waitUntil: "domcontentloaded", timeout: 60000 });
await page.waitForTimeout(9000);
const bScreen = await page.evaluate(() => (document.body.innerText || "").replace(/\s+/g, " ").slice(0, 220));
note(`B_FIRST_SCREEN ${JSON.stringify(bScreen)} t=${elapsed()}`);
const bKeys = await storageMap("B_after_reopen");
note(`B_STORAGE_LOCAL ${JSON.stringify(bKeys.local.map((k) => ({ key: k.key, len: k.len, shape: k.shape })))}`);
note(`B_STORAGE_SESSION ${JSON.stringify(bKeys.session.map((k) => ({ key: k.key, len: k.len, shape: k.shape })))}`);
const stillThere = journeyId ? await page.evaluate((id) => (document.body.innerText || "").includes(id.slice(0, 8)), journeyId) : false;
const asksToSignIn = await page.getByRole("button", { name: /登录|重新认证|继续上次|找回/ }).count().catch(() => 0);
const tripsTab = page.locator('[data-testid="rev-mobile-tab-trips"]');
const tabHit = await tripsTab.count() ? await tripsTab.first().evaluate((n) => {
  const b = n.getBoundingClientRect();
  return b.width > 0 && b.height > 0;
}).catch(() => false) : false;
note(`B_JOURNEY_ID_ON_SCREEN ${stillThere} B_SIGNIN_ASKS ${asksToSignIn} B_TRIPS_TAB_VISIBLE ${tabHit}`);
if (tabHit) {
  await tripsTab.first().click().catch((e) => note("B_TRIPS_CLICK_FAIL " + String(e).replace(/\s+/g, " ").slice(0, 160)));
  await page.waitForTimeout(2500);
  const tripsText = await page.evaluate(() => (document.body.innerText || "").replace(/\s+/g, " ").slice(0, 240));
  note(`B_TRIPS_SCREEN ${JSON.stringify(tripsText)} t=${elapsed()}`);
  const cards = await page.evaluate(() => Array.from(document.querySelectorAll("article, [data-testid*='trip-card']")).length);
  note(`B_TRIPS_CARDS ${cards}`);
}
await page.screenshot({ path: `${DIR}/390-bp136-phaseB-reopened.png` }).catch(() => {});
let verdict = "LOST";
if (stillThere) verdict = "RECOVERED";
else if (asksToSignIn > 0) verdict = "NEEDS_REAUTH_PROMPT";
else if (tabHit) verdict = "TRIPS_TAB_PRESENT_content_unconfirmed";
note(`VERDICT ${verdict} journey_id=${journeyId.slice(0, 8)}… t=${elapsed()}`);
note("DONE t=" + elapsed());
await ctx.close();
