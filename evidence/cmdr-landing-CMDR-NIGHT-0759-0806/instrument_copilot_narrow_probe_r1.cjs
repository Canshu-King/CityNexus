/* 窄屏下 Copilot 那屏的进度容器到底在不在：DOM 里有没有、可不可见、渲染盒多大。
 * 只为把账本里那句话写实，不改产品码。用法：node _cmdr_copilot_narrow_probe_r1.cjs
 */
const { chromium } = require("D:/moodle/CityNexus/frontend/node_modules/playwright/index.js");
const fs = require("fs");
const ARM = process.argv[2] || "arm";
const rec = { arm: ARM, at: new Date().toISOString(), widths: [] };

(async () => {
  const b = await chromium.launch({ channel: "chrome", headless: true });
  for (const w of [320, 390, 1280]) {
    const p = await b.newPage({ viewport: { width: w, height: 780 } });
    await p.addInitScript(() => {
      localStorage.setItem("citynexus.v8.journey_id", "22222222-2222-4222-8222-222222222222");
      localStorage.setItem("citynexus.theme", "dark");
      localStorage.setItem("citynexus.locale", "zh-CN");
    });
    await p.goto("http://127.0.0.1:8121/", { waitUntil: "networkidle" });
    await p.waitForTimeout(2000);
    const nav = await p.$('[data-testid="nav-agent"]');
    const navBox = nav ? await nav.boundingBox() : null;
    // 宽屏那档底栏没有盒（桌面布局另走一侧），handle.click 会超时；这里用 DOM 自己的 click()，
    // 与对拍尺同一形制，两臂都靠它把屏切到 Copilot。
    await p.evaluate(() => { const e = document.querySelector('[data-testid="nav-agent"]'); if (e) e.click(); });
    await p.waitForTimeout(1200);
    const info = await p.evaluate(() => {
      const els = Array.from(document.querySelectorAll(".v8-agent-progress"));
      const heading = (document.querySelector(".v8-page h1") || {}).innerText || "";
      return {
        count: els.length,
        visible: els.filter(e => e.checkVisibility({ checkOpacity: true, checkVisibilityCSS: true })).length,
        boxes: els.map(e => { const r = e.getBoundingClientRect(); return [Math.round(r.width), Math.round(r.height)]; }),
        bg: els.length ? getComputedStyle(els[0]).backgroundColor : null,
        color: els.length ? getComputedStyle(els[0]).color : null,
        heading,
        hamburger: !!document.querySelector('[data-testid="nav-open"], .v8-nav-toggle') && getComputedStyle(document.querySelector('[data-testid="nav-open"], .v8-nav-toggle') || document.body).display,
      };
    });
    const row = { viewport_w: w, nav_box: navBox, dom: info };
    rec.widths.push(row);
    console.log("w=" + w, "| navBox=" + JSON.stringify(navBox), "|", JSON.stringify(info));
    await p.close();
  }
  fs.writeFileSync("D:/moodle/_cmdr_fe_rev_1016/copilot_narrow_" + ARM + ".json", JSON.stringify(rec, null, 1), "utf-8");
  await b.close();
})().catch(e => { console.log("FATAL " + e); process.exit(1); });
