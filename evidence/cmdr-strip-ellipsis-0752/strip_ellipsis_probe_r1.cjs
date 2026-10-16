/* 首屏那条时间带（today-strip）的"省略号把诚实标签吃掉"这一手，前后各跑一次对拍。
 * 用法：node _cmdr_strip_ellipsis_probe_r1.cjs before|after
 * 读三样：
 *   甲 桌面 1280 档：两枚条目的盒高与行盒——正常换行后应当一字不变（不该动了宽屏的观感）
 *   乙 窄屏四档 × 两语臂：hidden_pct（被省略号吃掉的百分比），目标是全零
 *   丙 窄屏：文档横向溢出、条目底缘与固定底栏顶缘是否重叠
 */
const fs = require("fs");
const { chromium } = require("D:/moodle/CityNexus/frontend/node_modules/playwright/index.js");
const TAG = process.argv[2] || "now";

const READ = () => {
  const items = Array.from(document.querySelectorAll(".cn-strip-item"));
  const rows = items.map((el) => {
    const b = el.querySelector("b, strong");
    if (!b) return null;
    const rb = b.getBoundingClientRect();
    const rg = document.createRange();
    rg.selectNodeContents(b);
    const rects = Array.from(rg.getClientRects()).map(x => [Math.round(x.top), Math.round(x.width)]);
    return {
      full: (b.textContent || "").trim().slice(0, 46), shown: b.clientWidth, need: b.scrollWidth,
      hidden_pct: b.scrollWidth ? Math.round((1 - b.clientWidth / b.scrollWidth) * 100) : 0,
      h: Math.round(rb.height), lines: new Set(rects.map(x => x[0])).size, rects,
      bottom: Math.round(rb.bottom),
    };
  }).filter(Boolean);
  const bar = document.querySelector(".v8-mobile-nav, [data-testid='v8-mobile-nav']");
  const doc = document.documentElement;
  return {
    vw: window.innerWidth, doc_scroll: doc.scrollWidth, doc_client: doc.clientWidth,
    bar_top: bar && bar.checkVisibility({ checkVisibilityCSS: true }) ? Math.round(bar.getBoundingClientRect().top) : null,
    rows,
  };
};

(async () => {
  const b = await chromium.launch({ channel: "chrome", headless: true });
  const out = { tag: TAG, desktop: null, narrow: [] };
  for (const [w, loc] of [[1280, "zh-CN"], [320, "zh-CN"], [320, "en"], [360, "zh-CN"], [360, "en"], [390, "zh-CN"], [390, "en"], [430, "zh-CN"], [430, "en"]]) {
    const p = await b.newPage({ viewport: { width: w, height: 820 } });
    await p.addInitScript((l) => {
      localStorage.setItem("citynexus.v8.journey_id", "22222222-2222-4222-8222-222222222222");
      localStorage.setItem("citynexus.theme", "light");
      localStorage.setItem("citynexus.locale", l);
    }, loc);
    await p.goto("http://127.0.0.1:8121/", { waitUntil: "networkidle" });
    await p.waitForTimeout(2300);
    const r = await p.evaluate(READ);
    if (w === 1280) out.desktop = r; else out.narrow.push({ width: w, locale: loc, ...r });
    await p.close();
  }
  fs.writeFileSync("D:/moodle/_cmdr_fe_rev_1016/strip_ellipsis_" + TAG + ".json", JSON.stringify(out, null, 1), "utf-8");
  console.log(TAG, "| 桌面 1280 条目的盒：", JSON.stringify((out.desktop ? out.desktop.rows : []).map(x => x.full + " 高" + x.h + " 隐" + x.hidden_pct + "% 行" + x.lines)));
  for (const n of out.narrow) {
    const hid = n.rows.map(x => x.hidden_pct + "%/高" + x.h + "/行" + x.lines).join("  ");
    const over = n.rows.filter(x => n.bar_top !== null && x.bottom > n.bar_top).map(x => x.full.slice(0, 8));
    console.log("  ", n.width, n.locale, "| 隐藏", hid, "| 文档溢出", n.doc_scroll > n.doc_client, "| 压到底栏", over.length ? over.join(",") : "无");
  }
  await b.close();
})().catch(e => { console.log("FATAL " + e); process.exit(1); });
