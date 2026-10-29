import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";
const BASE = "http://127.0.0.1:14492";
const OUT = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome";
const NL = String.fromCharCode(10);
const lines = [];
const note = (v) => { lines.push(v); fs.writeFileSync(OUT + "/classroom-desktop-dump-21.txt", lines.join(NL) + NL, "utf8"); };
const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 }, deviceScaleFactor: 1 });
await ctx.addInitScript(() => {
  if (!sessionStorage.getItem("__probe_booted")) { localStorage.clear(); sessionStorage.clear(); sessionStorage.setItem("__probe_booted", "1"); }
});
const page = await ctx.newPage();
const errors = [];
page.on("pageerror", (e) => errors.push(String(e).slice(0, 160)));
await page.goto(BASE + "/revolution", { waitUntil: "networkidle", timeout: 45000 }).catch(() => {});
await page.waitForTimeout(1500);
await page.locator('[data-testid="rev-mobile-tab-trips"]').click(); await page.waitForTimeout(1200);
await page.locator('[data-testid="rev-demo-session"]').click(); await page.waitForTimeout(3600);
note("SCROLL_AFTER_ENTRY " + JSON.stringify(await page.evaluate(() => Math.round(window.scrollY))));
await page.getByRole("button", { name: /行程守护/ }).first().click(); await page.waitForTimeout(2600);
note("SCROLL_AFTER_GUARDIAN " + JSON.stringify(await page.evaluate(() => Math.round(window.scrollY))));
const dump = await page.evaluate(() => {
  const out = [];
  document.querySelectorAll("[data-testid]").forEach((el) => {
    const rect = el.getBoundingClientRect();
    if (rect.width > 120 && rect.height > 80) {
      out.push({
        id: el.getAttribute("data-testid"),
        x: Math.round(rect.x), y: Math.round(rect.y),
        w: Math.round(rect.width), h: Math.round(rect.height),
        text: (el.innerText || "").replace(/\s+/g, " ").slice(0, 50),
      });
    }
  });
  return out;
});
note("BLOCKS " + JSON.stringify(dump));
const left = await page.evaluate(() => {
  const el = document.elementFromPoint(300, 300);
  return el ? { tag: el.tagName, cls: String(el.className).slice(0, 80), text: (el.innerText || "").slice(0, 80) } : null;
});
note("LEFT_AT_300x300 " + JSON.stringify(left));
note("ERRORS " + JSON.stringify(errors.slice(0, 4)));
await browser.close();
