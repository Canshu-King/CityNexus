/**
 * After the capped walk has frozen its plan: press 「根据路线重新安排」, read the diff it produces, apply it, and read
 * whether the new revision still honours the traveller's walking cap. Real clicks, rendered-text readings only.
 */
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";

const require = createRequire("D:/moodle/_cmdr_rescue_v3_1022/frontend/package.json");
const { chromium } = require("playwright");

const SHOTS = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261022_v3_human_chrome";
const STREAM = fs.openSync(path.join(SHOTS, "walk-116-log.txt"), "a");
const say = (t) => { fs.writeSync(STREAM, t + "\n"); };

const browser = await chromium.connectOverCDP("http://127.0.0.1:9335");
const context = browser.contexts()[0];
const candidates = context.pages().filter((p) => p.url().includes("14522"));

let page = null;
let best = -1;
for (const candidate of candidates) {
  const n = await candidate.evaluate(() => document.querySelectorAll("[data-testid='rev-amap-research-frozen']").length)
    .catch(() => 0);
  if (n > best) { best = n; page = candidate; }
}
if (!page || best === 0) { say(`REPLAN_SKIP no_frozen_rows best=${best}`); process.exit(0); }
page.setDefaultTimeout(20000);
say(`REPLAN_START ${new Date().toISOString()} frozen_rows=${best}`);

const snap = async (tag) => {
  const s = await page.evaluate(() => {
    const flatIn = (v) => String(v ?? "").replace(/\s+/g, " ").trim();
    const rows = [...document.querySelectorAll("[data-testid='rev-amap-research-frozen']")]
      .map((n) => flatIn(n.innerText).slice(0, 150));
    const bandEl = [...document.querySelectorAll("p,div")].find((n) => /转场已核实/.test(n.innerText || ""));
    return {
      frozen_rows: rows.length,
      rows_with_cap_sentence: rows.filter((r) => /超过你写的/.test(r)).length,
      sample_row: rows.find((r) => /超过你写的/.test(r)) || rows[0] || "(none)",
      band: bandEl ? flatIn(bandEl.innerText).slice(0, 240) : "(absent)",
      buttons: [...document.querySelectorAll("button")].map((b) => flatIn(b.innerText)).filter(Boolean).slice(0, 40),
    };
  });
  say(`${tag} ${JSON.stringify(s)}`);
  return s;
};

const before = await snap("R1_BEFORE");
const gate = await page.evaluate(() => {
  const b = [...document.querySelectorAll("button")].find((n) => /根据路线重新安排/.test(n.innerText || ""));
  if (!b) return { found: false };
  b.scrollIntoView({ block: "center" });
  const box = b.getBoundingClientRect();
  const hit = document.elementFromPoint(box.left + box.width / 2, box.top + box.height / 2);
  return { found: true, disabled: b.disabled, centre_hit_is_button: hit === b || b.contains(hit),
    topmost: hit ? hit.tagName + "." + String(hit.className).slice(0, 36) : "OUT" };
});
say(`R2_GATE ${JSON.stringify(gate)}`);
if (!gate.found) { process.exit(0); }
await page.getByRole("button", { name: /根据路线重新安排/ }).first().click();
say(`R3_PRESSED ${new Date().toISOString()}`);

await page.waitForTimeout(8000);
const diff = await page.evaluate(() => {
  const flatIn = (v) => String(v ?? "").replace(/\s+/g, " ").trim();
  const el = document.querySelector("[data-testid='rev-v3-replan-diff']");
  if (el) return { testid: true, text: flatIn(el.innerText).slice(0, 1000) };
  const cands = [...document.querySelectorAll("div,section")].filter((n) => /改动|差异|换成|不变|→/.test(n.innerText || ""));
  const bestOne = cands.sort((a, b) => (b.innerText || "").length - (a.innerText || "").length)[0];
  return { testid: false, text: bestOne ? flatIn(bestOne.innerText).slice(0, 1000) : "(no diff block)" };
});
say(`R4_DIFF ${JSON.stringify(diff)}`);
await page.waitForTimeout(2000);
const mid = await snap("R5_AFTER_DIFF_OPEN");

// apply whatever explicit apply control the diff block offers
const applyGate = await page.evaluate(() => {
  const flatIn = (v) => String(v ?? "").replace(/\s+/g, " ").trim();
  const scope = document.querySelector("[data-testid='rev-v3-replan-diff']") || document.body;
  const b = [...scope.querySelectorAll("button")].find((n) => !n.disabled && /应用|按这版|就按|确认|采纳/.test(n.innerText || ""));
  if (!b) return { found: false, labels: [...scope.querySelectorAll("button")].map((x) => flatIn(x.innerText)).slice(0, 20) };
  const label = flatIn(b.innerText);
  const box = b.getBoundingClientRect();
  const hit = document.elementFromPoint(box.left + box.width / 2, box.top + box.height / 2);
  b.click();
  return { found: true, label, centre_hit_is_button: hit === b || b.contains(hit) };
});
say(`R6_APPLY ${JSON.stringify(applyGate)}`);
await page.waitForTimeout(12000);
const after = await snap("R7_AFTER_APPLY");
say(`R8_CHECK cap_sentence_before=${before.rows_with_cap_sentence} cap_sentence_after=${after.rows_with_cap_sentence}`);

try {
  const cdp = await context.newCDPSession(page);
  const cap = await cdp.send("Page.captureScreenshot", { format: "png" });
  const name = "walk116-after-replan.png";
  fs.writeFileSync(path.join(SHOTS, name), Buffer.from(cap.data, "base64"));
  say(`SHOT ${name} bytes=${fs.statSync(path.join(SHOTS, name)).size}`);
} catch (error) { say("SHOT_ERR " + String(error.message).slice(0, 70)); }
say(`REPLAN_END ${new Date().toISOString()}`);
process.exit(0);
