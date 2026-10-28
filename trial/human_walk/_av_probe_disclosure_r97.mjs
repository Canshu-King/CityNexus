import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";

// The last candidate door on a cold open is the disclosure whose own caption reads AI 已配置 · 未验证.
// Open it and print what is behind it, because "there is no way back into the trip" is a claim about
// every door on the screen and has to be measured door by door, not inferred from one screenshot.
const DIR = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261026_gozero";
const OUT = `${DIR}/av_disclosure_r97.txt`;
const NL = String.fromCharCode(10);
const lines = [];
const note = (v) => { lines.push(v); fs.writeFileSync(OUT, lines.join(NL) + NL, "utf8"); };

const ctx = await chromium.launchPersistentContext("D:/moodle/_cmdr_v3_live_1022/_chrome_gozero_aq92", {
  channel: "chrome", headless: false, viewport: { width: 430, height: 932 }, deviceScaleFactor: 1,
});
const page = ctx.pages()[0] ?? await ctx.newPage();
await page.goto("http://127.0.0.1:14462/revolution", { waitUntil: "domcontentloaded", timeout: 60000 });
await page.waitForTimeout(9000);

const census = () => page.evaluate(() => Array.from(document.querySelectorAll("button, a, input, summary, [role='dialog'] [data-testid]"))
  .map((n) => {
    const b = n.getBoundingClientRect();
    return { text: (n.innerText || n.getAttribute("aria-label") || n.value || "").replace(/\s+/g, " ").trim().slice(0, 40),
      testid: n.getAttribute("data-testid"), tag: n.tagName, disabled: Boolean(n.disabled), visible: b.width > 0 && b.height > 0 };
  }).filter((r) => r.text || r.testid));

note("BEFORE " + JSON.stringify(await census()));

const sum = page.locator("summary");
const n = await sum.count().catch(() => 0);
note("SUMMARY_COUNT " + n);
for (let k = 0; k < n; k += 1) {
  await sum.nth(k).click({ timeout: 6000 }).catch((e) => note("SUMMARY_CLICK_ERR " + String(e).slice(0, 70)));
  await page.waitForTimeout(2500);
  const open = await sum.nth(k).evaluate((el) => el.closest("details")?.open ?? null).catch(() => null);
  note(`AFTER_OPEN ${k} open=${open} ` + JSON.stringify((await page.evaluate(() => document.body.innerText || "")).replace(/\s+/g, " ").slice(0, 600)));
  await page.screenshot({ path: `${DIR}/430-av-disclosure-${k}.png` }).catch(() => {});
  const behind = await census();
  for (const d of behind) {
    if (/续期|重新|登录|身份|凭证|令牌|token|renew|signin|sign-in|claim|验证|配对|pair|设备/i.test(d.text + (d.testid || ""))) {
      note(`IDENTITY_DOOR text=${JSON.stringify(d.text)} testid=${d.testid} tag=${d.tag} disabled=${d.disabled} visible=${d.visible}`);
    }
  }
}
await ctx.close();
