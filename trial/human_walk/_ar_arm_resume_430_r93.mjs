import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";

// Continuation arm.  The r92 run left a real journey behind -- read out of the canary database with
// query_only on: 737b3a6c is status DRAFT with active_plan_version_id NONE, i.e. the draft was saved
// but "保存为正式候选方案" has never been pressed on this generation.  So this arm does no research at
// all: it reopens that journey through the traveller's own tabs and presses the save key twice.  Same
// throwaway profile as r92 (that is where the client keeps its journey pointer), same isolated stack.
const W = 430;
const H = 932;
const PROFILE = "D:/moodle/_cmdr_v3_live_1022/_chrome_gozero_aq92";
const BASE = "http://127.0.0.1:14462";
const DIR = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261026_gozero";
const OUT = `${DIR}/ar-resume-430-r93.txt`;
const NL = String.fromCharCode(10);
const lines = [];
const note = (value) => { lines.push(value); fs.writeFileSync(OUT, lines.join(NL) + NL, "utf8"); };
const started = Date.now();
const elapsed = () => ((Date.now() - started) / 1000).toFixed(1);
const UUID = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i;

const ctx = await chromium.launchPersistentContext(PROFILE, {
  channel: "chrome", headless: false, viewport: { width: W, height: H }, deviceScaleFactor: 1,
});
const page = ctx.pages()[0] ?? await ctx.newPage();
page.on("response", async (resp) => {
  const url = resp.url();
  const method = resp.request().method();
  if (!url.includes("/api/v1/") || (method !== "POST" && method !== "PUT")) return;
  if (!/goal-tasks|plans|journeys|departure/.test(url)) return;
  const line = `HTTP ${method} ${resp.status()} ${url.replace(/^http:\/\/[^/]+/, "")}`;
  if (resp.status() >= 400) {
    let detail = "";
    try { detail = JSON.stringify(await resp.json()).slice(0, 900); } catch { detail = "(unreadable body)"; }
    note(line + " BODY " + detail);
  } else { note(line); }
});

async function shot(name) {
  await page.screenshot({ path: `${DIR}/${name}.png`, fullPage: false }).catch(() => {});
  note(`SHOT ${name} t=${elapsed()}`);
}
async function visible(locator) { try { return await locator.first().isVisible(); } catch { return false; } }
async function press(locator, label, timeout = 8000) {
  const target = locator.first();
  try { await target.waitFor({ state: "visible", timeout }); } catch { note(`MISS ${label}`); return false; }
  await target.evaluate((node) => node.scrollIntoView({ block: "center" })).catch(() => {});
  await page.waitForTimeout(300);
  const ok = await target.evaluate((node) => {
    const box = node.getBoundingClientRect();
    if (box.width === 0 || box.height === 0) return false;
    const top = document.elementFromPoint(box.left + box.width / 2, box.top + box.height / 2);
    return Boolean(top) && (node === top || node.contains(top)) && !node.disabled;
  });
  note(`HIT ${label} ${ok} t=${elapsed()}`);
  if (!ok) return false;
  await target.click({ timeout: 15000 }).catch(() => {});
  await page.waitForTimeout(900);
  return true;
}
const bodyText = () => page.evaluate(() => document.body.innerText || "").catch(() => "");
const flat = (t) => t.replace(/\s+/g, " ").slice(0, 260);
const saveButton = page.getByRole("button", { name: /保存为正式候选方案/ });

async function leakReading(label) {
  const band = await page.locator(".rev-plan-message, [role='alert'], [role='status']").allInnerTexts().catch(() => []);
  const joined = band.join(" | ");
  const body = await bodyText();
  note(`${label} TEXTS ${JSON.stringify(band.slice(0, 4))}`);
  note(`${label} LEAK citynexus_api_in_body=${body.includes("CityNexus API")} api_in_band=${joined.includes("CityNexus API")} uuid_in_band=${UUID.test(joined)}`);
}

await page.goto(`${BASE}/revolution`, { waitUntil: "domcontentloaded", timeout: 60000 });
await page.waitForTimeout(5000);
const opener = await bodyText();
note(`COLD_BODY ${JSON.stringify(flat(opener))}`);
note(`COLD_HAS_JOURNEY_POINTER ${/我的旅程|行程|草案/.test(opener)} save_key=${await saveButton.count().catch(() => 0)}`);
await shot("430-ar-cold");

// The census read the DOM directly and saw the tab; this arm's locator saw zero.  Those two readings
// cannot both be about the same thing, so take both in one run: what is really in the document, and
// what each locator answers about it.
const diag = await page.evaluate(() => {
  const nav = document.querySelector('[data-testid="rev-mobile-bottom-nav"]');
  return {
    nav_present: Boolean(nav),
    nav_html: nav ? nav.outerHTML.replace(/\s+/g, " ").slice(0, 300) : null,
    testids: Array.from(document.querySelectorAll('[data-testid]')).map((n) => n.getAttribute("data-testid")).slice(0, 24),
    buttons: Array.from(document.querySelectorAll("button")).length,
    frames: window.frames.length,
  };
});
note(`DIAG ${JSON.stringify(diag)}`);
note(`DIAG_LOCATOR testid=${await page.locator('[data-testid="rev-mobile-bottom-nav"]').count().catch((e) => "ERR" + String(e).slice(0, 60))}`
  + ` by_text=${await page.getByText("我的旅程", { exact: true }).count().catch(() => -1)}`);

// Every hand the product might use to take the traveller back to their own trip, tried in order and
// written down -- r91 leg 2 already proved the journey screen, not the explore screen, carries the door.
// The role-name hands all returned zero on a screen whose body text plainly says 我的旅程, so the
// census (as-role-census-r94.txt) was consulted: the entry is button[data-testid=
// rev-mobile-tab-trips] inside nav[data-testid=rev-mobile-bottom-nav], visible at top 866.  Trust the
// product's own testid, keep the role name only as a fallback, and say which hand actually moved.
for (const [i, hand] of [[0, '[data-testid="rev-mobile-tab-trips"]'], [1, /我的旅程/], [2, /探索/]].entries()) {
  const tab = i === 0 ? page.locator(hand) : page.getByRole("button", { name: hand });
  const found = await tab.count().catch(() => 0);
  note(`HAND ${i} found=${found}`);
  if (!found) continue;
  if (await press(tab, `hand-${i}`, 8000)) {
    await page.waitForTimeout(3500);
    const after = await bodyText();
    note(`AFTER_HAND ${i} save_key=${await saveButton.count().catch(() => 0)} body=${JSON.stringify(flat(after))}`);
    if (await saveButton.count().catch(() => 0)) { note(`HAND_WON ${i}`); break; }
    // A trip list: open the newest card, whatever it is called.
    const cards = page.locator("article, [data-testid*='journey'], li");
    const cardCount = await cards.count().catch(() => 0);
    note(`LIST_CARDS ${cardCount}`);
    for (let k = 0; k < Math.min(cardCount, 4); k += 1) {
      if (await press(cards.nth(k), `card-${k}`, 6000)) {
        await page.waitForTimeout(3500);
        note(`AFTER_CARD ${k} save_key=${await saveButton.count().catch(() => 0)} body=${JSON.stringify(flat(await bodyText()))}`);
        if (await saveButton.count().catch(() => 0)) { note(`CARD_WON ${k}`); break; }
      }
    }
    if (await saveButton.count().catch(() => 0)) { note(`HAND_WON ${i}`); break; }
  }
}

await shot("430-ar-before-key");
if (!(await visible(saveButton))) {
  await leakReading("NO_KEY");
  note("ABORT the save key never became reachable through the traveller's own tabs");
  await ctx.close();
  process.exit(5);
}

for (const round of [1, 2]) {
  const pressed = await press(saveButton, `save-round-${round}`, 30000);
  note(`R${round}_PRESSED ${pressed} t=${elapsed()}`);
  await page.waitForTimeout(round === 1 ? 14000 : 7000);
  await leakReading(`R${round}`);
  await shot(`430-ar-after-save-${round}`);
}
const finalBody = await bodyText();
note("FINAL_HAS_SAVED " + /已保存\s*\d+\s*项正式安排/.test(finalBody));
note("FINAL_MAPS_SENTENCE " + (/这一版已经排好|不再改草案|刷新一下再继续/.test(finalBody)));
note("DONE t=" + elapsed());
await ctx.close();
