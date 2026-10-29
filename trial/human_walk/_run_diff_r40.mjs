import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";

const DIR = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261026_gozero";
const OUT = `${DIR}/run-diff-390.txt`;
const NL = String.fromCharCode(10);
const lines = [];
const note = (v) => { lines.push(v); fs.writeFileSync(OUT, lines.join(NL) + NL, "utf8"); };
const t0 = Date.now();
const el = () => ((Date.now() - t0) / 1000).toFixed(1);
const injected = JSON.parse(fs.readFileSync("D:/moodle/_cmdr_v3_live_1022/.demo_ticket_run.json", "utf8"));

const ctx = await chromium.launchPersistentContext("D:/moodle/_cmdr_v3_live_1022/_chrome_classroom_run2", {
  channel: "chrome", headless: false, viewport: { width: 390, height: 844 }, deviceScaleFactor: 1,
});
const page = ctx.pages()[0] ?? await ctx.newPage();
const errors = [];
page.on("pageerror", (e) => errors.push(String(e).slice(0, 160)));
page.on("response", (r) => {
  const u = r.url();
  if (!/simulation|replans/.test(u)) return;
  if (!["POST", "PUT"].includes(r.request().method())) return;
  note(`HTTP ${r.status()} ${u.replace(/^http:\/\/[^/]+/, "").slice(0, 100)}`);
});
let cdp = null;
async function shot(name) {
  try {
    cdp ??= await page.context().newCDPSession(page);
    const { data } = await cdp.send("Page.captureScreenshot", { format: "png" });
    fs.writeFileSync(`${DIR}/${name}.png`, Buffer.from(data, "base64"));
    note(`SHOT ${name} t=${el()}`);
  } catch (e) { note("SHOT_ERR " + String(e).slice(0, 60)); }
}
async function press(loc, label, timeout = 12000) {
  const t = loc.first();
  try { await t.waitFor({ state: "visible", timeout }); } catch { note(`MISS ${label} t=${el()}`); return false; }
  await t.evaluate((n) => n.scrollIntoView({ block: "center" })).catch(() => {});
  await page.waitForTimeout(250);
  const ok = await t.evaluate((node) => {
    const b = node.getBoundingClientRect();
    if (!b.width || !b.height) return false;
    const top = document.elementFromPoint(b.left + b.width / 2, b.top + b.height / 2);
    return Boolean(top) && (node === top || node.contains(top)) && !node.disabled;
  });
  note(`HIT ${label} ${ok} t=${el()}`);
  if (!ok) return false;
  await t.click({ timeout: 15000 }).catch(() => {});
  await page.waitForTimeout(900);
  return true;
}
const runLine = async () => {
  const n = page.locator('[data-testid="rev-presenter-run"]');
  return (await n.first().isVisible().catch(() => false)) ? (await n.first().innerText().catch(() => "")) : "";
};

await page.goto(`http://127.0.0.1:14492/revolution#pair=${injected.ticket}`, { waitUntil: "domcontentloaded", timeout: 60000 });
await page.waitForTimeout(9000);
await shot("run-diff-390-enter");
await press(page.getByRole("button", { name: /去课堂控制台/ }), "to-console");
await page.waitForTimeout(1500);
note("RUN0 " + JSON.stringify(await runLine()));

const start = page.getByRole("button", { name: /开演（模拟两日）/ });
if (await start.first().isVisible().catch(() => false)) {
  await press(start, "start-run", 20000);
  for (let i = 0; i < 10; i += 1) {
    await page.waitForTimeout(3000);
    if (/模拟进行中/.test(await runLine())) break;
  }
}
note("RUN1 " + JSON.stringify(await runLine()));

const scenes = page.locator('[data-testid="rev-presenter-scenes"]');
note("SCENES " + await scenes.count());
if (await scenes.first().isVisible().catch(() => false)) {
  await press(scenes.getByRole("button", { name: /闭馆/ }), "inject-closure", 20000);
  for (let i = 0; i < 12; i += 1) {
    await page.waitForTimeout(2500);
    const line = await runLine();
    if (/等待守护|守护|暂停|接受/i.test(line)) { note("RUN2 " + JSON.stringify(line)); break; }
  }
}
note("RUN2B " + JSON.stringify(await runLine()));
await shot("run-diff-390-injected");

const toGuardian = page.getByRole("button", { name: /交给守护助手/ });
if (await press(toGuardian, "to-guardian", 20000)) {
  note("GUARDIAN_SENT t=" + el());
}

const diff = page.locator('[data-testid="rev-presenter-diff"]');
let seen = false;
for (let i = 0; i < 36; i += 1) {
  await page.waitForTimeout(15000);
  if (await diff.first().isVisible().catch(() => false)) { seen = true; break; }
  const refresh = page.getByRole("button", { name: /刷新读数/ });
  if (i % 2 === 1) await press(refresh, `refresh-${i}`, 8000);
  note(`WAIT ${i} run=${JSON.stringify(await runLine())} t=${el()}`);
}
note("DIFF " + seen);
if (seen) {
  note("DIFF_TEXT " + JSON.stringify((await diff.first().innerText().catch(() => "")).slice(0, 600)));
  await diff.first().scrollIntoViewIfNeeded().catch(() => {});
  await page.waitForTimeout(400);
  await shot("run-diff-390-block");
  const accept = page.getByRole("button", { name: /接受这次事件的调整/ });
  if (await press(accept, "accept", 20000)) {
    await page.waitForTimeout(12000);
    note("AFTER_ACCEPT " + JSON.stringify((await page.evaluate(() => document.body.innerText || "")).slice(-500)));
    await shot("run-diff-390-after");
  }
}
note("ERRORS " + JSON.stringify(errors.slice(0, 3)));
await ctx.close();
