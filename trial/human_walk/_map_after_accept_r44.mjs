import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";

const DIR = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261026_gozero";
const OUT = `${DIR}/map-after-accept-390.txt`;
const NL = String.fromCharCode(10);
const lines = [];
const note = (v) => { lines.push(v); fs.writeFileSync(OUT, lines.join(NL) + NL, "utf8"); };
const injected = JSON.parse(fs.readFileSync("D:/moodle/_cmdr_v3_live_1022/.demo_ticket_map.json", "utf8"));

const ctx = await chromium.launchPersistentContext("D:/moodle/_cmdr_v3_live_1022/_chrome_classroom_map", {
  channel: "chrome", headless: false, viewport: { width: 390, height: 844 }, deviceScaleFactor: 1,
});
const page = ctx.pages()[0] ?? await ctx.newPage();
let cdp = null;
async function shot(name) {
  try {
    cdp ??= await page.context().newCDPSession(page);
    const { data } = await cdp.send("Page.captureScreenshot", { format: "png" });
    fs.writeFileSync(`${DIR}/${name}.png`, Buffer.from(data, "base64"));
    note("SHOT " + name);
  } catch (e) { note("SHOT_ERR " + String(e).slice(0, 60)); }
}
async function press(loc, label, timeout = 12000) {
  const t = loc.first();
  try { await t.waitFor({ state: "visible", timeout }); } catch { note("MISS " + label); return false; }
  await t.evaluate((n) => n.scrollIntoView({ block: "center" })).catch(() => {});
  await page.waitForTimeout(250);
  const ok = await t.evaluate((node) => {
    const b = node.getBoundingClientRect();
    if (!b.width || !b.height) return false;
    const top = document.elementFromPoint(b.left + b.width / 2, b.top + b.height / 2);
    return Boolean(top) && (node === top || node.contains(top)) && !node.disabled;
  });
  note(`HIT ${label} ${ok}`);
  if (!ok) return false;
  await t.click({ timeout: 15000 }).catch(() => {});
  await page.waitForTimeout(1200);
  return true;
}

await page.goto(`http://127.0.0.1:14492/revolution#pair=${injected.ticket}`, { waitUntil: "domcontentloaded", timeout: 60000 });
await page.waitForTimeout(9000);
await press(page.getByRole("button", { name: /^地图$/ }), "map-tab");
await page.waitForTimeout(2500);
const pane = page.locator('[data-testid="rev-mission-layer-map"]');
note("MAP_PANE " + await pane.count());
const text = await page.evaluate(() => document.body.innerText || "");
const mapText = (await pane.first().innerText().catch(() => "")) || text;
note("HAS_GUGONG " + /故宫/.test(mapText));
note("HAS_TIANTAN " + /天坛/.test(mapText));
note("MAP_TEXT " + JSON.stringify(mapText.replace(/\s+/g, " ").slice(0, 700)));
await shot("map-after-accept-390");
await ctx.close();
