import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";

const FILE = "D:/moodle/_cmdr_v3_live_1022/.demo_pairing_ticket";
const DIR = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261026_gozero";
const OUT = `${DIR}/classroom-accept-tickets-390.txt`;
const NL = String.fromCharCode(10);
const lines = [];
const note = (v) => { lines.push(v); fs.writeFileSync(OUT, lines.join(NL) + NL, "utf8"); };
const started = Date.now();
const el = () => ((Date.now() - started) / 1000).toFixed(1);

const data = JSON.parse(fs.readFileSync(FILE, "utf8"));
const tickets = Array.isArray(data.tickets) ? data.tickets.slice(0, 3) : [];
note(`TICKETS ${tickets.length} expires_at ${data.expires_at} journey ${data.journey_id}`);

async function shot(page, n) {
  await page.screenshot({ path: `${DIR}/${n}.png`, fullPage: false }).catch(() => {});
  note(`SHOT ${n} t=${el()}`);
}

let page = null, ctx = null, used = 0;
for (let i = 0; i < tickets.length && !page; i += 1) {
  ctx = await chromium.launchPersistentContext(`D:/moodle/_cmdr_v3_live_1022/_chrome_caccept_${i}`, {
    channel: "chrome", headless: false, viewport: { width: 390, height: 844 },
  });
  const candidate = ctx.pages()[0] ?? await ctx.newPage();
  const responses = [];
  candidate.on("response", (resp) => {
    if (/demo\/pairing\/redeem/.test(resp.url())) responses.push(resp.status());
  });
  await candidate.goto(`http://127.0.0.1:14492/revolution#pair=${tickets[i]}`, { waitUntil: "domcontentloaded", timeout: 60000 });
  await candidate.waitForTimeout(10000);
  const body = await candidate.evaluate(() => document.body.innerText || "");
  note(`TRY ${i} redeem=${JSON.stringify(responses)} body=${JSON.stringify(body.slice(0, 90))}`);
  if (body.includes("北京 · 2日行程") || body.includes("北京 · 2 日行程")) { page = candidate; used = i; }
  else { await ctx.close(); ctx = null; }
}
note(`ENTRY_TICKET_INDEX ${used} entered=${Boolean(page)}`);

if (page) {
  const firstStop = async () => {
    const body = await page.evaluate(() => document.body.innerText || "");
    return {
      first: (body.match(/第一站[：:][^\n]+/) || [null])[0],
      now: (body.match(/现在[：:][^\n]+/) || [null])[0],
      accepted: /行程已按这份调整更新|行程已经启动/.test(body),
      head: body.slice(0, 200),
    };
  };
  const before = await firstStop();
  note(`BEFORE ${JSON.stringify(before)}`);
  await shot(page, "classroom-accept-tickets-before");

  // The proposal card lives in the 行程守护 drawer, not on the execution screen itself.
  const guardian = page.getByRole("button", { name: /行程守护/ });
  if (await guardian.count()) {
    await guardian.first().evaluate((n) => n.scrollIntoView({ block: "center" })).catch(() => {});
    await page.waitForTimeout(300);
    await guardian.first().click({ timeout: 10000 }).catch(() => {});
    await page.waitForTimeout(3000);
    note(`GUARDIAN_OPENED t=${el()}`);
    await shot(page, "classroom-accept-tickets-guardian");
  } else {
    note("NO_GUARDIAN_BUTTON");
  }
  const accept = page.getByRole("button", { name: /接受这份调整/ });
  let visible = false;
  try { visible = await accept.first().isVisible(); } catch { visible = false; }
  note(`ACCEPT_VISIBLE ${visible}`);
  if (visible) {
    await accept.first().evaluate((n) => n.scrollIntoView({ block: "center" })).catch(() => {});
    await page.waitForTimeout(400);
    const ok = await accept.first().evaluate((node) => {
      const b = node.getBoundingClientRect();
      const top = document.elementFromPoint(b.left + b.width / 2, b.top + b.height / 2);
      return Boolean(top) && (node === top || node.contains(top)) && !node.disabled;
    });
    note(`ACCEPT_HIT ${ok}`);
    if (ok) {
      await accept.first().click({ timeout: 15000 }).catch(() => {});
      await page.waitForTimeout(9000);
      const after = await firstStop();
      note(`AFTER ${JSON.stringify(after)}`);
      await shot(page, "classroom-accept-tickets-after");
    }
  } else {
    note(`BODY_NO_ACCEPT ${JSON.stringify((await page.evaluate(() => document.body.innerText || "")).slice(0, 1000))}`);
  }
}
if (ctx) await ctx.close();
