import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";
const BASE = process.env.SIM_BASE || "http://127.0.0.1:14494";
const OUT = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome";
const NL = String.fromCharCode(10);
const lines = [];
const note = (v) => { lines.push(v); fs.writeFileSync(OUT + "/classroom-entry-banner-33.txt", lines.join(NL) + NL, "utf8"); };

const clean = (s) => String(s || "").replace(/\s+/g, " ").trim();

const browser = await chromium.launch({ headless: true });

async function arm(label, url, shot, press = "") {
  const ctx = await browser.newContext({ viewport: { width: 430, height: 932 }, deviceScaleFactor: 1 });
  await ctx.addInitScript(() => {
    if (!sessionStorage.getItem("__probe_booted")) { localStorage.clear(); sessionStorage.clear(); sessionStorage.setItem("__probe_booted", "1"); }
  });
  const page = await ctx.newPage();
  const errors = [];
  page.on("pageerror", (e) => errors.push(String(e).slice(0, 140)));
  await page.goto(url, { waitUntil: "networkidle", timeout: 60000 });
  await page.waitForTimeout(4200);

  const banner = page.locator('[data-testid="rev-demo-error-banner"]');
  const oldSpot = page.locator('[data-testid="rev-demo-error"]');
  const bannerCount = await banner.count();
  const box = bannerCount ? await banner.first().boundingBox() : null;
  const visible = bannerCount ? await banner.first().isVisible() : false;
  const text = bannerCount ? clean(await banner.first().innerText()) : "";
  const tab = await page.locator('[data-testid="revolution-first-look"]').count();
  // What a teacher sees without scrolling: banner box must sit inside the first viewport.
  const inViewport = !!(box && box.y >= 0 && box.y + box.height <= 932 && box.width > 0);
  note(`${label} banner_count=${bannerCount} visible=${visible} in_viewport=${inViewport} box=${JSON.stringify(box)} root=${tab}`);
  note(`${label}_TEXT ${JSON.stringify(text)}`);
  note(`${label}_OLD_SPOT ${await oldSpot.count()}`);
  await page.screenshot({ path: OUT + "/" + shot, fullPage: false });

  if (press) {
    const clicked = [];
    for (const id of press.split(",")) {
      const button = page.locator(`[data-testid="${id}"]`);
      const pressed = await button.count();
      if (pressed) await button.first().click().catch(() => {});
      clicked.push(`${id}:${pressed}`);
      await page.waitForTimeout(900);
    }
    await page.waitForTimeout(4200);
    const afterPress = page.locator('[data-testid="rev-demo-error-banner"]');
    const afterCount = await afterPress.count();
    const afterBox = afterCount ? await afterPress.first().boundingBox() : null;
    note(`${label}_PRESS ${clicked.join(" ")} banner_count=${afterCount} box=${JSON.stringify(afterBox)}`);
    note(`${label}_PRESS_TEXT ${JSON.stringify(afterCount ? clean(await afterPress.first().innerText()) : "")}`);
    await page.screenshot({ path: OUT + "/" + shot.replace(".png", "-press.png"), fullPage: false });
  }

  await page.reload({ waitUntil: "networkidle", timeout: 60000 });
  await page.waitForTimeout(3800);
  const afterReload = await page.locator('[data-testid="rev-demo-error-banner"]').count();
  note(`${label}_AFTER_RELOAD banner_count=${afterReload}`);
  await ctx.close();
  return { errors };
}

const noTicket = await arm("NO_TICKET", `${BASE}/revolution`, "classroom-entry-banner-33-no-ticket.png", "rev-mobile-tab-trips,rev-demo-session");
const badTicket = await arm("BAD_TICKET", `${BASE}/revolution#pair=${"A".repeat(43)}`, "classroom-entry-banner-33-bad-ticket.png");
const tickets = [badTicket];
const valid = process.env.PAIR_TICKET || "";
if (valid) {
  tickets.push(await arm("SEALED_TRIP", `${BASE}/revolution#pair=${encodeURIComponent(valid)}`, "classroom-entry-banner-33-sealed-trip.png"));
} else {
  note("SEALED_TRIP SKIPPED no PAIR_TICKET");
}
note(`ERRORS ${JSON.stringify([...noTicket.errors, ...tickets.flatMap((t) => t.errors)].slice(0, 4))}`);
await browser.close();
