const { chromium } = require("D:/moodle/CityNexus/frontend/node_modules/playwright/index.js");
(async () => {
  const b = await chromium.launch({ channel: "chrome", headless: true });
  for (const w of [320, 360, 390]) {
    const p = await b.newPage({ viewport: { width: w, height: 820 } });
    await p.addInitScript(() => {
      localStorage.setItem("citynexus.v8.journey_id", "22222222-2222-4222-8222-222222222222");
      localStorage.setItem("citynexus.theme", "light");
      localStorage.setItem("citynexus.locale", "zh-CN");
    });
    await p.goto("http://127.0.0.1:8121/", { waitUntil: "networkidle" });
    await p.waitForTimeout(2000);
    await p.evaluate(() => { const e = document.querySelector('[data-testid="nav-map"]'); if (e) e.click(); });
    await p.waitForTimeout(1300);
    const r = await p.evaluate(() => Array.from(document.querySelectorAll(".v8-lede")).map(el => {
      const cs = getComputedStyle(el);
      const rg = document.createRange(); rg.selectNodeContents(el);
      const rects = Array.from(rg.getClientRects()).map(x => Math.round(x.width));
      let inside = false, n = el.parentElement;
      while (n) { if ((n.className || "").toString().includes("v8-page")) { inside = true; break; } n = n.parentElement; }
      return { text: (el.textContent || "").trim().slice(0, 16), wb: cs.wordBreak, in_v8_page: inside,
               ancestors: (() => { const a = []; let q = el.parentElement; for (let i = 0; i < 3 && q; i++) { a.push((q.className || q.tagName).toString().split(" ")[0]); q = q.parentElement; } return a.join("<"); })(),
               rects };
    }));
    console.log("地图屏 宽度", w, JSON.stringify(r));
    await p.close();
  }
  await b.close();
})().catch(e => { console.log("FATAL " + e); process.exit(1); });
