import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
const BASE = "http://127.0.0.1:14492";
const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({ viewport: { width: 430, height: 932 } });
await context.addInitScript(() => { localStorage.clear(); sessionStorage.clear(); });
const page = await context.newPage();
const log = [];
page.on("response", async (r) => {
  const u = r.url();
  if (u.includes("/api/v1/")) {
    let body = "";
    try { body = (await r.text()).slice(0, 160); } catch {}
    log.push(`${r.status()} ${u.replace(BASE,'')} :: ${body}`);
  }
});
page.on("console", (m) => { if (m.type() === "error") log.push("CONSOLE " + m.text().slice(0, 200)); });
page.on("pageerror", (e) => log.push("PAGEERROR " + String(e).slice(0, 200)));
await page.goto(BASE + "/revolution", { waitUntil: "networkidle" });
await page.waitForTimeout(1500);
await page.locator('[data-testid="rev-mobile-tab-trips"]').click();
await page.waitForTimeout(1200);
await page.locator('[data-testid="rev-demo-session"]').click();
await page.waitForTimeout(5000);
console.log(log.join("\n"));
console.log("TEXT " + JSON.stringify((await page.evaluate(() => document.body.innerText)).slice(0, 500)));
await browser.close();
