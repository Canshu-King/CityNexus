import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";

const INJ = "D:/moodle/_cmdr_v3_live_1022/.demo_ticket_injected.json";
const DIR = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261026_gozero";
const OUT = `${DIR}/classroom-run-diff-390.txt`;
const NL = String.fromCharCode(10);
const lines = [];
const note = (v) => { lines.push(v); fs.writeFileSync(OUT, lines.join(NL) + NL, "utf8"); };
const t0 = Date.now();
const el = () => ((Date.now() - t0) / 1000).toFixed(1);

const injected = JSON.parse(fs.readFileSync(INJ, "utf8"));
const URL = `http://127.0.0.1:14492/revolution#pair=${injected.ticket}`;
note(`JOURNEY ${injected.journey_id}`);

const ctx = await chromium.launchPersistentContext("D:/moodle/_cmdr_v3_live_1022/_chrome_classroom_diff2", {
  channel: "chrome", headless: false, viewport: { width: 390, height: 844 }, deviceScaleFactor: 1,
});
const page = ctx.pages()[0] ?? await ctx.newPage();
const errors = [];
page.on("pageerror", (e) => errors.push(String(e).slice(0, 160)));
let cdp = null;
async function shot(name) {
  try {
    cdp ??= await page.context().newCDPSession(page);
    const { data } = await cdp.send("Page.captureScreenshot", { format: "png" });
    fs.writeFileSync(`${DIR}/${name}.png`, Buffer.from(data, "base64"));
    note(`SHOT_CDP ${name} t=${el()}`);
  } catch (e) { note(`SHOT_ERR ${name} ${String(e).slice(0, 80)}`); }
}
async function visible(loc) { try { return await loc.first().isVisible(); } catch { return false; } }
async function press(loc, label, timeout = 8000) {
  const target = loc.first();
  try { await target.waitFor({ state: "visible", timeout }); } catch { note(`MISS ${label}`); return false; }
  await target.evaluate((n) => n.scrollIntoView({ block: "center" })).catch(() => {});
  await page.waitForTimeout(250);
  const ok = await target.evaluate((node) => {
    const b = node.getBoundingClientRect();
    if (!b.width || !b.height) return false;
    const top = document.elementFromPoint(b.left + b.width / 2, b.top + b.height / 2);
    return Boolean(top) && (node === top || node.contains(top)) && !node.disabled;
  });
  note(`HIT ${label} ${ok} t=${el()}`);
  if (!ok) return false;
  await target.click({ timeout: 15000 }).catch(() => {});
  await page.waitForTimeout(800);
  return true;
}
const body = () => page.evaluate(() => document.body.innerText || "").catch(() => "");
const runLine = async () => {
  const node = page.locator('[data-testid="rev-presenter-run"]');
  return (await visible(node)) ? (await node.first().innerText().catch(() => "")) : "";
};
const nextAction = async () => {
  const text = await body();
  if (/接受这次事件的调整/.test(text)) return "ACCEPT";
  if (/交给守护助手/.test(text)) return "TO_GUARDIAN";
  if (/继续模拟/.test(text)) return "RESUME";
  if (/开演（模拟两日）/.test(text)) return "START";
  return "UNKNOWN";
};

await page.goto(URL, { waitUntil: "domcontentloaded", timeout: 60000 });
await page.waitForTimeout(9000);
note(`PAIR_BODY ${JSON.stringify((await body()).slice(0, 200))}`);
await shot("classroom-r29-enter");

const toConsole = page.getByRole("button", { name: /去课堂控制台/ });
if (await visible(toConsole)) { await press(toConsole, "to-console", 10000); await page.waitForTimeout(1500); }
note(`CONSOLE ${await page.locator('[aria-label="演示者控制台"]').count()}`);
note(`RUN_BEFORE ${JSON.stringify(await runLine())}`);
note(`ACTION_BEFORE ${await nextAction()}`);
await shot("classroom-r29-console-before");

const start = page.getByRole("button", { name: /开演（模拟两日）/ });
if (await visible(start)) {
  await press(start, "start-run", 15000);
  for (let i = 0; i < 10; i += 1) {
    await page.waitForTimeout(3000);
    const action = await nextAction();
    if (action !== "START") { note(`AFTER_START action=${action} run=${JSON.stringify(await runLine())}`); break; }
  }
  await shot("classroom-r29-started");
} else {
  note("START_NOT_VISIBLE");
}

const clockNext = page.locator('[data-testid="rev-clock-next"]');
note(`CLOCK_VISIBLE ${await visible(clockNext)}`);
for (let i = 0; i < 6; i += 1) {
  const action = await nextAction();
  note(`STEP ${i} action=${action} run=${JSON.stringify(await runLine())}`);
  if (action === "TO_GUARDIAN" || action === "ACCEPT") break;
  if (!(await press(clockNext, `clock-next-${i}`, 15000))) break;
  await page.waitForTimeout(6000);
}
note(`AFTER_STEPS action=${await nextAction()} run=${JSON.stringify(await runLine())}`);
await shot("classroom-r29-after-steps");
note(`BODY_TAIL ${JSON.stringify((await body()).slice(-700))}`);
note(`ERRORS ${JSON.stringify(errors.slice(0, 4))}`);
await ctx.close();
