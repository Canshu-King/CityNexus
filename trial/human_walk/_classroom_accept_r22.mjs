import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";

const URL = process.env.PAIR_URL || "";
const DIR = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261026_gozero";
const OUT = `${DIR}/classroom-accept-390.txt`;
const NL = String.fromCharCode(10);
const lines = [];
const note = (v) => { lines.push(v); fs.writeFileSync(OUT, lines.join(NL) + NL, "utf8"); };
const started = Date.now();
const el = () => ((Date.now() - started) / 1000).toFixed(1);

const ctx = await chromium.launchPersistentContext("D:/moodle/_cmdr_v3_live_1022/_chrome_classroom_accept", {
  channel: "chrome", headless: false, viewport: { width: 390, height: 844 },
});
const page = ctx.pages()[0] ?? await ctx.newPage();
page.on("response", (resp) => {
  const u = resp.url();
  if (/replans\/.+\/(accept|reject)/.test(u)) note(`HTTP ${resp.request().method()} ${resp.status()} ${u.split("/api/v1")[1]} t=${el()}`);
});
async function shot(n) {
  await page.screenshot({ path: `${DIR}/${n}.png`, fullPage: false }).catch(() => {});
  note(`SHOT ${n} t=${el()}`);
}
async function visible(l) { try { return await l.first().isVisible(); } catch { return false; } }
async function press(l, label, timeout = 12000) {
  const t = l.first();
  try { await t.waitFor({ state: "visible", timeout }); } catch { note(`MISS ${label}`); return false; }
  await t.evaluate((n) => n.scrollIntoView({ block: "center" })).catch(() => {});
  await page.waitForTimeout(300);
  const ok = await t.evaluate((node) => {
    const b = node.getBoundingClientRect();
    const top = document.elementFromPoint(b.left + b.width / 2, b.top + b.height / 2);
    return Boolean(top) && (node === top || node.contains(top)) && !node.disabled;
  });
  note(`HIT ${label} ${ok} t=${el()}`);
  if (!ok) return false;
  await t.click({ timeout: 15000 }).catch(() => {});
  await page.waitForTimeout(600);
  return true;
}
const firstStop = async () => {
  const body = await page.evaluate(() => document.body.innerText || "");
  return {
    first: (body.match(/第一站[：:][^\n]+/) || [null])[0],
    now: (body.match(/现在[：:][^\n]+/) || [null])[0],
    body: body.slice(0, 300),
  };
};

await page.goto(URL, { waitUntil: "domcontentloaded", timeout: 60000 });
await page.waitForTimeout(10000);
for (let tries = 0; tries < 2; tries += 1) {
  const cold = (await page.evaluate(() => (document.body.innerText || ""))).includes("从一句话开始");
  if (!cold) break;
  note(`COLD_SCREEN_RELOAD ${tries + 1}`);
  await page.reload({ waitUntil: "domcontentloaded" }).catch(() => {});
  await page.waitForTimeout(12000);
}
const before = await firstStop();
note(`BEFORE ${JSON.stringify(before)}`);
await shot("classroom-accept-390-before");

const accept = page.getByRole("button", { name: /接受这份调整/ });
const has = await visible(accept);
note(`ACCEPT_VISIBLE ${has}`);
if (!has) {
  note(`BODY_BEFORE ${JSON.stringify((await page.evaluate(() => document.body.innerText || "")).slice(0, 1200))}`);
} else {
  await press(accept, "accept-proposal");
  // settleProposal reloads the page 1.2 s after a 200; wait past that and let the new plan render.
  await page.waitForTimeout(9000);
  const after = await firstStop();
  note(`AFTER ${JSON.stringify(after)}`);
  await shot("classroom-accept-390-after");
}
note(`URL_AFTER ${page.url().slice(0, 80)}`);
await ctx.close();
