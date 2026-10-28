import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";

// The trips screen says the device still holds the 北京 trip but this open is not logged into it.
// Before choosing any path, print every door that screen and the 我的 screen actually offer, with its
// testid and whether it is pressable -- so a claim of "no way in" comes with an inventory, not a grep.
const DIR = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261026_gozero";
const OUT = `${DIR}/au-trips-doors-r96.txt`;
const NL = String.fromCharCode(10);
const lines = [];
const note = (v) => { lines.push(v); fs.writeFileSync(OUT, lines.join(NL) + NL, "utf8"); };

const ctx = await chromium.launchPersistentContext("D:/moodle/_cmdr_v3_live_1022/_chrome_gozero_au96", {
  channel: "chrome", headless: false, viewport: { width: 430, height: 932 }, deviceScaleFactor: 1,
});
const page = ctx.pages()[0] ?? await ctx.newPage();
await page.goto("http://127.0.0.1:14462/revolution", { waitUntil: "domcontentloaded", timeout: 60000 });
await page.waitForTimeout(9000);

const doors = (tag) => page.evaluate((label) => {
  const out = [];
  for (const node of document.querySelectorAll("button, a, summary, [role='button'], input[type='submit']")) {
    const b = node.getBoundingClientRect();
    const text = (node.innerText || node.getAttribute("aria-label") || "").replace(/\s+/g, " ").trim().slice(0, 34);
    if (!text && !node.getAttribute("data-testid")) continue;
    out.push({ label, text, testid: node.getAttribute("data-testid"), tag: node.tagName,
      disabled: Boolean(node.disabled), visible: b.width > 0 && b.height > 0, top: Math.round(b.top),
      href: node.getAttribute("href") });
  }
  return out;
}, tag);

async function pressTestId(id, label) {
  const loc = page.locator(`[data-testid="${id}"]`);
  const n = await loc.count().catch(() => 0);
  note(`PRESS ${label} count=${n}`);
  if (!n) return false;
  await loc.first().scrollIntoViewIfNeeded().catch(() => {});
  await loc.first().click({ timeout: 8000 }).catch((e) => note(`CLICK_ERR ${String(e).slice(0, 80)}`));
  await page.waitForTimeout(4000);
  return true;
}

for (const id of ["rev-mobile-tab-trips", "rev-mobile-tab-me"]) {
  await pressTestId(id, id);
  const list = await doors(id);
  for (const d of list) {
    if (/journey|trip|claim|sign|login|auth|recover|restore|restore|token|traveler|demo|entry/i.test((d.testid || "") + (d.href || "")) || d.text) {
      note(`DOOR of=${id} tag=${d.tag} text=${JSON.stringify(d.text)} testid=${d.testid} disabled=${d.disabled} visible=${d.visible} top=${d.top} href=${d.href}`);
    }
  }
  note(`SCREEN_TEXT of=${id} ` + JSON.stringify((await page.evaluate(() => document.body.innerText || "")).replace(/\s+/g, " ").slice(0, 700)));
  await page.screenshot({ path: `${DIR}/430-au-${id}.png` }).catch(() => {});
}
await ctx.close();
