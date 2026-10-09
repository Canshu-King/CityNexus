/* Product-shell regression check for the tooltip order.  The preview proxy is pointed at a dead
   port on purpose: loading a CityNexus screen issues reads that write (`GET /experience`), and the
   backend on :8000 is shared with other lanes, so a shell-boot check must not put traffic on it.
   Run from `frontend/`:  node _scratch/drive_shell_r1.mjs */
import { chromium } from "playwright";
import { writeFileSync } from "node:fs";

const PAGE_URL = "http://127.0.0.1:6112/v8/hub";
const OUT = new URL("./_out/", import.meta.url).pathname.replace(/^\//, "");
const R = {};
const errs = [];

const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 1280, height: 860 }, locale: "zh-CN" });
const page = await ctx.newPage();
page.on("pageerror", (e) => errs.push("pageerror:" + String(e.message).slice(0, 240)));
page.on("console", (m) => {
  if (m.type() === "error") errs.push("console:" + String(m.text()).slice(0, 240));
});

await page.goto(PAGE_URL, { waitUntil: "domcontentloaded", timeout: 60000 });
await page.waitForTimeout(2500);

R.shell = await page.evaluate(() => {
  const root = document.getElementById("root");
  let tip_rule = false;
  for (const sheet of document.styleSheets) {
    let rules;
    try {
      rules = sheet.cssRules;
    } catch {
      continue;
    }
    for (const rule of rules || []) {
      if (rule.selectorText && rule.selectorText.includes(".cn-tip")) {
        tip_rule = true;
        break;
      }
    }
    if (tip_rule) break;
  }
  const probe = document.createElement("div");
  probe.className = "cn-tip";
  document.body.appendChild(probe);
  const pcs = getComputedStyle(probe);
  const probe_style = { position: pcs.position, z_index: pcs.zIndex, max_width: pcs.maxWidth };
  probe.remove();
  return {
    root_children: root ? root.children.length : -1,
    body_chars: document.body.innerText.trim().length,
    title: document.title,
    h1_or_headline: (document.querySelector("h1,h2,strong") || {}).innerText || null,
    cn_tip_rule_present: tip_rule,
    cn_tip_computed: probe_style,
    sw_controller: navigator.serviceWorker ? Boolean(navigator.serviceWorker.controller) : null,
  };
});

R.api_calls_made = await page.evaluate(() =>
  performance
    .getEntriesByType("resource")
    .filter((e) => e.name.includes("/api/"))
    .map((e) => e.name.replace(/^https?:\/\/[^/]+/, ""))
    .slice(0, 12),
);

await page.screenshot({ path: OUT + "tip1008_product_shell.png" });

R.errors = errs;
await ctx.close();
await browser.close();
writeFileSync(OUT + "shell_readings_r1.json", JSON.stringify({ R }, null, 1), "utf8");
console.log(JSON.stringify({ R }, null, 1));
