import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";

const FILE = "D:/moodle/_cmdr_v3_live_1022/.demo_pairing_ticket";
const DIR = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261026_gozero";
const OUT = `${DIR}/first-stop-date-390.txt`;
const NL = String.fromCharCode(10);
const lines = [];
const note = (v) => { lines.push(v); fs.writeFileSync(OUT, lines.join(NL) + NL, "utf8"); };
const data = JSON.parse(fs.readFileSync(FILE, "utf8"));
const tickets = Array.isArray(data.tickets) ? data.tickets.slice(0, 3) : [];

let cdp = null;
async function shot(page, name) {
  try {
    cdp ??= await page.context().newCDPSession(page);
    const { data } = await cdp.send("Page.captureScreenshot", { format: "png" });
    fs.writeFileSync(`${DIR}/${name}.png`, Buffer.from(data, "base64"));
    note(`SHOT_CDP ${name} ok`);
    return;
  } catch (e) { note(`SHOT_CDP_ERR ${String(e).slice(0, 90)}`); }
  for (let i = 0; i < 2; i += 1) {
    try { await page.bringToFront().catch(() => {}); await page.screenshot({ path: `${DIR}/${name}.png`, fullPage: false, animations: "disabled", caret: "hide", timeout: 10000 }); note(`SHOT ${name} ok`); return; }
    catch (e) { note(`SHOT_ERR ${String(e).slice(0, 80)}`); await page.waitForTimeout(800); }
  }
}

let ctx = null, page = null;
for (let i = 0; i < tickets.length && !page; i += 1) {
  const c = await chromium.launchPersistentContext(`D:/moodle/_cmdr_v3_live_1022/_chrome_fsd_${i}`, {
    channel: "chrome", headless: false, viewport: { width: 390, height: 844 },
  });
  const p = c.pages()[0] ?? await c.newPage();
  await p.goto(`http://127.0.0.1:14492/revolution#pair=${tickets[i]}`, { waitUntil: "domcontentloaded", timeout: 60000 });
  await p.waitForTimeout(9000);
  const body = await p.evaluate(() => document.body.innerText || "");
  note(`TRY ${i} entered=${body.includes("北京 · 2日行程")}`);
  if (body.includes("北京 · 2日行程")) { ctx = c; page = p; }
  else await c.close();
}
if (page) {
  const next = page.locator('[data-testid="live-next"]');
  note(`LIVE_NEXT_COUNT ${await next.count()}`);
  if (await next.count()) note(`LIVE_NEXT ${JSON.stringify(await next.first().innerText())}`);
  const body = await page.evaluate(() => document.body.innerText || "");
  note(`HEAD ${JSON.stringify(body.slice(0, 260))}`);
  await shot(page, "first-stop-date-390");
}
if (ctx) await ctx.close();
