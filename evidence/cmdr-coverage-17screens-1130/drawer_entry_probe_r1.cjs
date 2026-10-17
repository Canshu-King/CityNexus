/* 抽屉里那些屏的入口清单：点开抽屉，把每一枚 `v8-drawer-entry-*` 的 testid、文字、盒尺寸读出来。
 * 目的：把"六屏"之外的屏也纳入普查分母。只读不改。
 * 用法：node _cmdr_drawer_entries_r1.cjs
 */
const { chromium } = require("D:/moodle/CityNexus/frontend/node_modules/playwright/index.js");

(async () => {
  const b = await chromium.launch({ channel: "chrome", headless: true });
  for (const W of [1280, 390]) {
    const p = await b.newPage({ viewport: { width: W, height: 900 } });
    await p.addInitScript(() => {
      localStorage.setItem("citynexus.v8.journey_id", "22222222-2222-4222-8222-222222222222");
      localStorage.setItem("citynexus.theme", "light");
      localStorage.setItem("citynexus.locale", "zh-CN");
    });
    await p.goto("http://127.0.0.1:8121/", { waitUntil: "networkidle" });
    await p.waitForTimeout(2200);
    await p.evaluate(() => { const e = document.querySelector('[data-testid="v8-mobile-menu"]'); if (e) e.click(); });
    await p.waitForTimeout(1200);
    const got = await p.evaluate(() => {
      const els = Array.from(document.querySelectorAll('[data-testid^="v8-drawer-entry"]'));
      return {
        n_entries: els.length,
        entries: els.map(e => ({ tid: e.getAttribute("data-testid"), text: (e.textContent || "").replace(/\s+/g, " ").trim().slice(0, 22), vis: e.checkVisibility() })),
        other_testids: Array.from(document.querySelectorAll('[data-testid]')).map(e => e.getAttribute("data-testid")).filter(t => /drawer|menu|panel/.test(t)).slice(0, 30),
      };
    });
    console.log("w=" + W + " 抽屉入口 " + got.n_entries + " 枚");
    for (const e of got.entries) console.log("   " + (e.tid || "-").padEnd(42) + " " + e.text + (e.vis ? "" : " (不可见)"));
    console.log("   含 drawer/menu/panel 的 testid：" + got.other_testids.join(", "));
    await p.close();
  }
  await b.close();
})().catch(e => { console.log("FATAL " + e); process.exit(1); });
