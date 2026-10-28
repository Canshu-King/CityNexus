import { chromium } from "file:///D:/moodle/_cmdr_rescue_v3_1022/frontend/node_modules/playwright/index.mjs";
import fs from "node:fs";

// The resume arm printed "我的旅程" in the body text and then found zero buttons with that name, so
// the first screen's trip entry is not a button.  Rather than guess a second role, read every real
// interactive element on that screen with its role, its accessible name and its testid.
const DIR = "D:/moodle/_cmdr_rescue_v3_1022/trial/results/20261026_gozero";
const OUT = `${DIR}/as-role-census-r94.txt`;
const NL = String.fromCharCode(10);
const lines = [];
const note = (v) => { lines.push(v); fs.writeFileSync(OUT, lines.join(NL) + NL, "utf8"); };

const ctx = await chromium.launchPersistentContext("D:/moodle/_cmdr_v3_live_1022/_chrome_gozero_aq92", {
  channel: "chrome", headless: false, viewport: { width: 430, height: 932 }, deviceScaleFactor: 1,
});
const page = ctx.pages()[0] ?? await ctx.newPage();
await page.goto("http://127.0.0.1:14462/revolution", { waitUntil: "domcontentloaded", timeout: 60000 });
await page.waitForTimeout(6000);

const census = await page.evaluate(() => {
  const sel = "button, a, [role], input, [data-testid], summary, [tabindex]";
  const seen = new Set();
  const rows = [];
  for (const node of document.querySelectorAll(sel)) {
    const label = (node.innerText || node.getAttribute("aria-label") || node.value || "").replace(/\s+/g, " ").trim().slice(0, 40);
    const box = node.getBoundingClientRect();
    const key = `${node.tagName}|${node.getAttribute("role")}|${node.getAttribute("data-testid")}|${label}`;
    if (seen.has(key)) continue;
    seen.add(key);
    if (!box.width && !box.height && !label) continue;
    rows.push({ tag: node.tagName, role: node.getAttribute("role"), testid: node.getAttribute("data-testid"),
      label, href: node.getAttribute("href"), visible: box.width > 0 && box.height > 0, top: Math.round(box.top) });
  }
  return rows;
});
note("CENSUS_TOTAL " + census.length);
for (const r of census) {
  if (/旅程|探索|行程|trip|journey/i.test(r.label + (r.testid || "") + (r.href || "")) || /nav|tab/i.test(r.testid || "")) {
    note(`CANDIDATE tag=${r.tag} role=${r.role} testid=${r.testid} visible=${r.visible} top=${r.top} href=${r.href} label=${JSON.stringify(r.label)}`);
  }
}
note("BODY_HEAD " + JSON.stringify((await page.evaluate(() => document.body.innerText || "")).replace(/\s+/g, " ").slice(0, 200)));
await page.screenshot({ path: `${DIR}/430-as-role-census.png` }).catch(() => {});
await ctx.close();
