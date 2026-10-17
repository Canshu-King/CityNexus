/* 子 Agent 那把尺报过"横向溢出一百零六条，hub 在 320 占二十六条"。
 * 我自己另取一次：412 与 320 两档走 hub，数 documentElement.scrollWidth 与窗口宽的差，
 * 再数"自身右边超出视口右界"的可见元素有几枚。只读。 */
const { chromium } = require("D:/moodle/CityNexus/frontend/node_modules/playwright/index.js");
(async () => {
  const b = await chromium.launch({ channel: "chrome", headless: true });
  for (const W of [412, 320]) {
    const p = await b.newPage({ viewport: { width: W, height: 860 } });
    await p.addInitScript(() => {
      localStorage.setItem("citynexus.v8.journey_id", "22222222-2222-4222-8222-222222222222");
      localStorage.setItem("citynexus.theme", "dark");
      localStorage.setItem("citynexus.locale", "zh-CN");
    });
    await p.goto("http://127.0.0.1:8121/", { waitUntil: "networkidle" });
    await p.waitForTimeout(2200);
    const got = await p.evaluate(() => {
      const de = document.documentElement;
      const over = [];
      for (const el of Array.from(document.querySelectorAll("body *"))) {
        if (!el.checkVisibility({ checkOpacity: true, checkVisibilityCSS: true })) continue;
        const r = el.getBoundingClientRect();
        if (r.width < 1 || r.height < 1) continue;
        if (r.right > window.innerWidth + 1 || r.left < -1) {
          const own = Array.from(el.childNodes).filter(n => n.nodeType === 3).map(n => n.textContent).join("").trim();
          over.push({ sel: el.tagName.toLowerCase() + (typeof el.className === "string" && el.className ? "." + el.className.trim().split(/\s+/)[0] : ""),
            text: own.slice(0, 18), right: Math.round(r.right), left: Math.round(r.left), w: Math.round(r.width) });
        }
      }
      return { doc_w: de.scrollWidth, win_w: window.innerWidth, body_w: document.body.scrollWidth, n: over.length, over: over.slice(0, 6) };
    });
    console.log("w=" + W + "｜documentElement.scrollWidth=" + got.doc_w + " body=" + got.body_w + " 窗口=" + got.win_w +
      " → 整页横向" + (got.doc_w > got.win_w + 1 ? "溢出 " + (got.doc_w - got.win_w) + "px" : "无") + "｜出界元素 " + got.n + " 枚");
    for (const o of got.over) console.log("     " + o.sel.padEnd(26) + (o.text || "").slice(0, 14).padEnd(15) + "left=" + o.left + " right=" + o.right + " w=" + o.w);
    await p.close();
  }
  await b.close();
})();
