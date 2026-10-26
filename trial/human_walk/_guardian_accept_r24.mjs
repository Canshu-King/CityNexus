import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";

const FILE = "D:/moodle/_cmdr_v3_live_1022/.demo_pairing_ticket";
const DIR = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261026_gozero";
const OUT = `${DIR}/guardian-accept-390.txt`;
const NL = String.fromCharCode(10);
const lines = [];
const note = (v) => { lines.push(v); fs.writeFileSync(OUT, lines.join(NL) + NL, "utf8"); };
const started = Date.now();
const el = () => ((Date.now() - started) / 1000).toFixed(1);

const data = JSON.parse(fs.readFileSync(FILE, "utf8"));
const tickets = Array.isArray(data.tickets) ? data.tickets.slice(0, 3) : [];
note(`TICKETS ${tickets.length} journey ${data.journey_id}`);

let cdp = null;
async function shot(page, name) {
  try {
    cdp ??= await page.context().newCDPSession(page);
    const { data } = await cdp.send("Page.captureScreenshot", { format: "png" });
    fs.writeFileSync(`${DIR}/${name}.png`, Buffer.from(data, "base64"));
    note(`SHOT_CDP ${name} ok t=${el()}`);
    return;
  } catch (error) {
    note(`SHOT_CDP_ERR ${name} ${String(error).slice(0, 90)}`);
  }
  try { await page.screenshot({ path: `${DIR}/${name}.png`, fullPage: false }); note(`SHOT ${name} ok`); }
  catch (error) { note(`SHOT_ERR ${name} ${String(error).slice(0, 90)}`); }
}

let ctx = null, page = null, used = -1;
for (let i = 0; i < tickets.length && !page; i += 1) {
  const c = await chromium.launchPersistentContext(`D:/moodle/_cmdr_v3_live_1022/_chrome_ga_${i}`, {
    channel: "chrome", headless: false, viewport: { width: 390, height: 844 },
  });
  const p = c.pages()[0] ?? await c.newPage();
  const redeem = [];
  p.on("response", (r) => { if (/demo\/pairing\/redeem/.test(r.url())) redeem.push(r.status()); });
  await p.goto(`http://127.0.0.1:14492/revolution#pair=${tickets[i]}`, { waitUntil: "domcontentloaded", timeout: 60000 });
  await p.waitForTimeout(8000);
  const body = await p.evaluate(() => document.body.innerText || "");
  note(`TRY ${i} redeem=${JSON.stringify(redeem)}`);
  if (body.includes("北京 · 2日行程")) { ctx = c; page = p; used = i; }
  else await c.close();
}
note(`ENTERED ${Boolean(page)} ticket=${used}`);

if (page) {
  const toggle = page.locator('button[aria-expanded]', { hasText: "行程守护" }).first();
  note(`TOGGLE_COUNT ${await toggle.count()}`);
  if (await toggle.count()) {
    note(`ARIA_BEFORE ${await toggle.getAttribute("aria-expanded")}`);
    await toggle.scrollIntoViewIfNeeded().catch(() => {});
    await page.waitForTimeout(300);
    for (let attempt = 0; attempt < 3; attempt += 1) {
      try { await toggle.click({ timeout: 8000 }); break; }
      catch (error) { note(`TOGGLE_CLICK_ERR ${String(error).slice(0, 90)}`); await page.waitForTimeout(600); }
    }
    await page.waitForTimeout(3500);
    note(`ARIA_AFTER ${await toggle.getAttribute("aria-expanded")}`);
  }
  const panel = page.locator(".rev-guardian-panel");
  note(`PANEL ${await panel.count()} visible=${await panel.first().isVisible().catch(() => false)}`);
  const state = await page.locator(".rev-guardian-state").allInnerTexts().catch(() => []);
  note(`GUARDIAN_STATE ${JSON.stringify(state.slice(0, 3))}`);
  const proposal = page.locator('[data-testid="rev-guardian-proposal"]');
  const accept = page.locator('[data-testid="rev-guardian-accept-replan"]');
  note(`PROPOSAL ${await proposal.count()} ACCEPT ${await accept.count()} visible=${await accept.first().isVisible().catch(() => false)}`);
  const panelText = await panel.first().innerText().catch(() => "");
  note(`PANEL_TEXT ${JSON.stringify(panelText.slice(0, 700))}`);
  await shot(page, "guardian-accept-390-panel");

  if (await accept.count() && await accept.first().isVisible().catch(() => false)) {
    const statuses = [];
    page.on("response", (r) => { if (/replans\/.+\/accept/.test(r.url())) statuses.push(r.status()); });
    await accept.first().scrollIntoViewIfNeeded().catch(() => {});
    await page.waitForTimeout(300);
    const hit = await accept.first().evaluate((node) => {
      const b = node.getBoundingClientRect();
      const top = document.elementFromPoint(b.left + b.width / 2, b.top + b.height / 2);
      return Boolean(top) && (node === top || node.contains(top)) && !node.disabled;
    });
    note(`ACCEPT_HIT ${hit}`);
    if (hit) {
      await accept.first().click({ timeout: 15000 }).catch(() => {});
      await page.waitForTimeout(9000);
      note(`ACCEPT_HTTP ${JSON.stringify(statuses)}`);
      const body = await page.evaluate(() => document.body.innerText || "");
      note(`AFTER_FIRST ${JSON.stringify((body.match(/第一站[：:][^\n]+/) || [null])[0])}`);
      note(`AFTER_HEAD ${JSON.stringify(body.slice(0, 220))}`);
      await shot(page, "guardian-accept-390-after");
    }
  }
}
if (ctx) await ctx.close();
