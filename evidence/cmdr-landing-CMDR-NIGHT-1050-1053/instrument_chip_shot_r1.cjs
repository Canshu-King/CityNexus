/* Copilot 那排建议 chip 在 390 宽的两张图：改前（临时退回尖上那一版 css 由外部控制）与改后。
 * 只截图 + 打印每枚 chip 的盒高，判据不在这把尺里。
 * 用法：node _cmdr_chip_shot_r1.cjs <标签>
 */
const fs = require("fs");
const { chromium } = require("D:/moodle/CityNexus/frontend/node_modules/playwright/index.js");
const LABEL = process.argv[2] || "run";

(async () => {
  const b = await chromium.launch({ channel: "chrome", headless: true });
  const p = await b.newPage({ viewport: { width: 390, height: 780 }, hasTouch: true, isMobile: true });
  await p.addInitScript(() => {
    localStorage.setItem("citynexus.v8.journey_id", "22222222-2222-4222-8222-222222222222");
    localStorage.setItem("citynexus.theme", "light");
    localStorage.setItem("citynexus.locale", "zh-CN");
  });
  await p.goto("http://127.0.0.1:8121/", { waitUntil: "networkidle" });
  await p.waitForTimeout(2200);
  await p.evaluate(() => { const e = document.querySelector('[data-testid="nav-agent"]'); if (e) e.click(); });
  await p.waitForTimeout(1500);
  const rows = await p.evaluate(() => Array.from(document.querySelectorAll(".v15-copilot-suggestions button")).map(el => {
    const r = el.getBoundingClientRect();
    return { text: (el.textContent || "").trim().slice(0, 20), h: Math.round(r.height), w: Math.round(r.width) };
  }));
  const box = await p.evaluate(() => {
    const el = document.querySelector(".v15-copilot-suggestions");
    if (!el) return null;
    el.scrollIntoView({ block: "center" });
    const r = el.getBoundingClientRect();
    return { x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height) };
  });
  await p.waitForTimeout(400);
  if (box) await p.screenshot({ path: "D:/moodle/_cmdr_fe_rev_1016/shots/chips_390_" + LABEL + ".png", clip: { x: Math.max(0, box.x), y: Math.max(0, box.y - 6), width: Math.min(390, box.w), height: box.h + 12 } });
  fs.writeFileSync("D:/moodle/_cmdr_fe_rev_1016/chips_390_" + LABEL + ".json", JSON.stringify({ label: LABEL, chips: rows, container: box }, null, 1), "utf-8");
  console.log("chip 数 " + rows.length + "｜" + rows.map(r => r.text + " " + r.h + "×" + r.w).join(" / "));
  await b.close();
})().catch(e => { console.log("FATAL " + e); process.exit(1); });
