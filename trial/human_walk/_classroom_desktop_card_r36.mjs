import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";
const BASE = "http://127.0.0.1:14492";
const TICKET_FILE = "D:/moodle/_cmdr_v3_live_1022/.demo_pairing_ticket";
let pairing = "";
try {
  const raw = JSON.parse(fs.readFileSync(TICKET_FILE, "utf8"));
  if (raw.ticket && Number(raw.expires_at) * 1000 > Date.now()) pairing = String(raw.ticket);
} catch { /* old backend: the entry signs a session locally */ }
const OUT = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome";
const NL = String.fromCharCode(10);
const lines = [];
const note = (v) => { lines.push(v); fs.writeFileSync(OUT + "/classroom-desktop-card-36.txt", lines.join(NL) + NL, "utf8"); };
const clean = (s) => String(s || "").replace(/\s+/g, " ").trim();

const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 }, deviceScaleFactor: 1 });
await ctx.addInitScript(() => {
  if (!sessionStorage.getItem("__probe_booted")) { localStorage.clear(); sessionStorage.clear(); sessionStorage.setItem("__probe_booted", "1"); }
});
const page = await ctx.newPage();
const errors = [];
page.on("pageerror", (e) => errors.push(String(e).slice(0, 160)));
await page.goto(BASE + "/revolution" + (pairing ? "#pair=" + encodeURIComponent(pairing) : ""), { waitUntil: "networkidle", timeout: 60000 });
await page.waitForTimeout(1200);
if (pairing) {
  await page.waitForTimeout(4200);
} else {
  await page.locator('[data-testid="rev-mobile-tab-trips"]').click();
  await page.waitForTimeout(1000);
  await page.locator('[data-testid="rev-demo-session"]').click();
  await page.waitForTimeout(3600);
}
await page.getByRole("button", { name: /行程守护/ }).first().click();
await page.waitForTimeout(2400);

const card = page.locator('[data-testid="rev-guardian-proposal"]');
const before = await card.boundingBox().catch(() => null);
const viewportFirst = await page.evaluate(() => window.innerHeight);
note(`CARD_BOX ${JSON.stringify(before)}`);
note(`IN_FIRST_VIEW ${JSON.stringify(!!before && before.y >= 0 && before.y + before.height <= viewportFirst)}`);
note(`VALUE_TEXT ${JSON.stringify(clean(await page.locator('[data-testid="rev-guardian-proposal-diff"]').innerText().catch(() => "")))}`);
note(`SCROLL_Y ${await page.evaluate(() => window.scrollY)}`);
const accept = page.locator('[data-testid="rev-guardian-accept-replan"]');
const acceptBox = await accept.boundingBox().catch(() => null);
const hit = acceptBox
  ? await page.evaluate(({ x, y }) => {
      const el = document.elementFromPoint(x, y);
      if (!el) return "none";
      return el.closest('[data-testid="rev-guardian-accept-replan"]') ? "self" : (el.className || el.tagName);
    }, { x: acceptBox.x + acceptBox.width / 2, y: acceptBox.y + acceptBox.height / 2 })
  : "no-button";
note(`ACCEPT_BOX ${JSON.stringify(acceptBox)}`);
note(`ACCEPT_HIT ${JSON.stringify(hit)}`);
await page.screenshot({ path: OUT + "/classroom-desktop-card-36-before.png", fullPage: false });

await card.scrollIntoViewIfNeeded().catch(() => {});
await page.waitForTimeout(700);
const after = await card.boundingBox().catch(() => null);
note(`AFTER_SCROLL_BOX ${JSON.stringify(after)}`);
note(`AFTER_SCROLL_Y ${await page.evaluate(() => Math.round(window.scrollY))}`);
note(`ACCEPT_IN_VIEW ${JSON.stringify(!!after && after.y >= 0 && after.y + after.height <= viewportFirst)}`);
await page.screenshot({ path: OUT + "/classroom-desktop-card-36-after.png", fullPage: false });
note(`ERRORS ${JSON.stringify(errors.slice(0, 3))}`);
await ctx.close();
await browser.close();
