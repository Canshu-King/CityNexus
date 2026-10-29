import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";

const URL = process.env.PAIR_URL || "";
const DIR = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261026_gozero";
const OUT = `${DIR}/presenter-diff-390.txt`;
const NL = String.fromCharCode(10);
const lines = [];
const note = (value) => { lines.push(value); fs.writeFileSync(OUT, lines.join(NL) + NL, "utf8"); };
const started = Date.now();
const elapsed = () => ((Date.now() - started) / 1000).toFixed(1);

const ctx = await chromium.launchPersistentContext("D:/moodle/_cmdr_v3_live_1022/_chrome_classroom_diff", {
  channel: "chrome", headless: false, viewport: { width: 390, height: 844 }, deviceScaleFactor: 1,
});
const page = ctx.pages()[0] ?? await ctx.newPage();
const errors = [];
page.on("pageerror", (e) => errors.push(String(e).slice(0, 160)));

async function shot(name) {
  await page.screenshot({ path: `${DIR}/${name}.png`, fullPage: false }).catch(() => {});
  note(`SHOT ${name} t=${elapsed()}`);
}
async function visible(locator) { try { return await locator.first().isVisible(); } catch { return false; } }
async function press(locator, label, timeout = 8000) {
  const target = locator.first();
  try { await target.waitFor({ state: "visible", timeout }); } catch { note(`MISS ${label}`); return false; }
  await target.evaluate((n) => n.scrollIntoView({ block: "center" })).catch(() => {});
  await page.waitForTimeout(250);
  const ok = await target.evaluate((node) => {
    const box = node.getBoundingClientRect();
    const top = document.elementFromPoint(box.left + box.width / 2, box.top + box.height / 2);
    return Boolean(top) && (node === top || node.contains(top)) && !node.disabled;
  });
  note(`HIT ${label} ${ok} t=${elapsed()}`);
  if (!ok) return false;
  await target.click({ timeout: 15000 }).catch(() => {});
  await page.waitForTimeout(700);
  return true;
}

note(`URL_HAS_TICKET ${URL.includes("#pair=")}`);
await page.goto(URL || "http://127.0.0.1:14492/revolution", { waitUntil: "domcontentloaded", timeout: 60000 });
await page.waitForTimeout(6000);
note(`AFTER_PAIR ${JSON.stringify((await page.evaluate(() => document.body.innerText || "")).slice(0, 240))}`);
await shot("classroom-390-after-pair");

// The console sits below the first screen; the green bar's own button is the product's own door.
const toConsole = page.getByRole("button", { name: /去课堂控制台/ });
if (await visible(toConsole)) { await press(toConsole, "to-console", 10000); await page.waitForTimeout(1500); }
const consolePanel = page.locator('[aria-label="演示者控制台"]');
note(`CONSOLE ${await consolePanel.count()} visible=${await visible(consolePanel)}`);
if (await visible(consolePanel)) {
  await consolePanel.scrollIntoViewIfNeeded().catch(() => {});
  await page.waitForTimeout(500);
}
await shot("classroom-390-console");

// The proposal diff is fetched on the panel's own refresh tick.
const diff = page.locator('[data-testid="rev-presenter-diff"]');
let seen = false;
for (let i = 0; i < 12; i += 1) {
  if (await visible(diff)) { seen = true; break; }
  const refresh = page.getByRole("button", { name: /刷新读数/ });
  if (i % 3 === 2 && await visible(refresh)) await press(refresh, `refresh-${i}`, 8000);
  await page.waitForTimeout(3000);
}
note(`DIFF ${seen}`);
if (seen) {
  const text = await diff.innerText().catch(() => "");
  note(`DIFF_TEXT ${JSON.stringify(text)}`);
  await diff.scrollIntoViewIfNeeded().catch(() => {});
  await page.waitForTimeout(400);
  await shot("classroom-390-diff");
  const box = await diff.boundingBox().catch(() => null);
  if (box) note(`DIFF_BOX ${JSON.stringify({ x: Math.round(box.x), y: Math.round(box.y), w: Math.round(box.width), h: Math.round(box.height) })}`);
}

const accept = page.getByRole("button", { name: /接受这次事件的调整/ });
if (await visible(accept)) {
  note("ACCEPT_VISIBLE");
  if (await press(accept, "accept", 20000)) {
    const key = "classroom-diff-check-" + Date.now();
    note(`ACCEPT_PRESSED ${key}`);
    for (let i = 0; i < 20; i += 1) {
      await page.waitForTimeout(3000);
      const body = await page.evaluate(() => document.body.innerText || "");
      const m = body.match(/这次事件已经落定|可以继续模拟|事件处理完了/);
      if (m) { note(`ACCEPT_STATE ${JSON.stringify(m[0])} t=${elapsed()}`); break; }
    }
    await shot("classroom-390-after-accept");
  }
} else {
  note("ACCEPT_NOT_VISIBLE");
}

const body = await page.evaluate(() => (document.body.innerText || "").slice(0, 1200)).catch(() => "");
note(`BODY ${JSON.stringify(body)}`);
note(`ERRORS ${JSON.stringify(errors.slice(0, 3))}`);
await ctx.close();
