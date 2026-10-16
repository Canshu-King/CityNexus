const { chromium } = require("D:/moodle/CityNexus/frontend/node_modules/playwright/index.js");
(async () => {
  const b = await chromium.launch({ channel: "chrome", headless: true });
  const p = await b.newPage({ viewport: { width: 320, height: 820 } });
  await p.addInitScript(() => {
    localStorage.setItem("citynexus.v8.journey_id", "22222222-2222-4222-8222-222222222222");
    localStorage.setItem("citynexus.theme", "light");
    localStorage.setItem("citynexus.locale", "zh-CN");
  });
  await p.goto("http://127.0.0.1:8121/", { waitUntil: "networkidle" });
  await p.waitForTimeout(2100);
  await p.evaluate(() => { const e = document.querySelector('[data-testid="nav-map"]'); if (e) e.click(); });
  await p.waitForTimeout(1300);
  const r = await p.evaluate(() => {
    const el = Array.from(document.querySelectorAll(".v8-lede")).find(x => (x.textContent || "").includes("采集的路线几何"));
    if (!el) return { found: false };
    const node = el.firstChild;
    const data = node && node.nodeType === 3 ? node.data : null;
    const rows = [];
    if (data) for (let i = 0; i < data.length; i++) {
      const rg = document.createRange(); rg.setStart(node, i); rg.setEnd(node, i + 1);
      const rr = rg.getBoundingClientRect(); rows.push([data[i], Math.round(rr.top), Math.round(rr.width)]);
    }
    const breaks = [];
    for (let i = 0; i + 1 < rows.length; i++) if (rows[i][1] !== rows[i + 1][1]) breaks.push(rows[i][0] + "｜" + rows[i + 1][0] + " (top " + rows[i][1] + "→" + rows[i + 1][1] + ")");
    return { found: true, full: (el.textContent || "").trim(), node_len: data ? data.length : -1, other_children: el.children.length, wb: getComputedStyle(el).wordBreak, breaks };
  });
  console.log(JSON.stringify(r, null, 1));
  await b.close();
})().catch(e => { console.log("FATAL " + e); process.exit(1); });
