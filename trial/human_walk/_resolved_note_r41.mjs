import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";

const DIR = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261026_gozero";
const OUT = `${DIR}/resolved-note-390.txt`;
const NL = String.fromCharCode(10);
const lines = [];
const note = (v) => { lines.push(v); fs.writeFileSync(OUT, lines.join(NL) + NL, "utf8"); };
const injected = JSON.parse(fs.readFileSync("D:/moodle/_cmdr_v3_live_1022/.demo_ticket_run2.json", "utf8"));

const ctx = await chromium.launchPersistentContext("D:/moodle/_cmdr_v3_live_1022/_chrome_classroom_run3", {
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
  await page.waitForTimeout(900);
  return true;
}

await page.goto(`http://127.0.0.1:14492/revolution#pair=${injected.ticket}`, { waitUntil: "domcontentloaded", timeout: 60000 });
await page.waitForTimeout(9000);
await press(page.getByRole("button", { name: /去课堂控制台/ }), "to-console");
await page.waitForTimeout(2000);
const runLine = await page.locator('[data-testid="rev-presenter-run"]').first().innerText().catch(() => "");
note("RUN " + JSON.stringify(runLine));
const resolved = page.locator('[data-testid="rev-presenter-resolved-note"]');
const mismatch = page.locator('[data-testid="rev-presenter-proposal-mismatch"]');
note("RESOLVED_VISIBLE " + await resolved.first().isVisible().catch(() => false));
note("RESOLVED_TEXT " + JSON.stringify(await resolved.first().innerText().catch(() => "")));
note("MISMATCH_COUNT " + await mismatch.count());
note("MISMATCH_VISIBLE " + (await mismatch.count() ? await mismatch.first().isVisible().catch(() => false) : false));
const body = await page.evaluate(() => document.body.innerText || "");
note("HAS_RESTART_ADVICE " + /看不到可接受的内容/.test(body));
await page.locator('[data-testid="rev-presenter-run"]').first().scrollIntoViewIfNeeded().catch(() => {});
await shot("resolved-note-390");
await ctx.close();
