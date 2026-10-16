/* 全量找"中文在词内断行"的元素（把我那一手一刀的补丁变成一把能数分母的尺）。
 *
 * 判据：逐枚取叶子元素的逐字形行盒（Range 一次扩一个字符）；
 *   若相邻两枚字形的 top 不同（跨行了），且这两枚都是中日韩汉字（U+4E00-U+9FFF），
 *   就算一处"词内断行"候选——中文没有空格，断在任意两枚汉字之间都不是自然断点。
 * 只报数与出处，不改任何东西；每档宽度 × 两语臂 × 六屏各跑一遍。
 */
const fs = require("fs");
const { chromium } = require("D:/moodle/CityNexus/frontend/node_modules/playwright/index.js");

const STEPS = [
  ["hub", null], ["live", '[data-testid="today-hero-cta"]'], ["copilot", '[data-testid="nav-agent"]'],
  ["trips", '[data-testid="nav-trips"]'], ["map", '[data-testid="nav-map"]'], ["me", '[data-testid="nav-me"]'],
];
const CJK = "[\\u4E00-\\u9FFF]";

const SCAN = (cjk) => {
  const rx = new RegExp("^" + cjk + "$");
  const hits = [];
  for (const el of document.querySelectorAll("body *")) {
    if (el.childElementCount !== 0) continue;
    const node = el.firstChild;
    if (!node || node.nodeType !== 3) continue;
    const data = node.data || "";
    const t = data.trim();
    if (data.length < 2 || t.length < 2) continue;
    if (!el.checkVisibility({ checkOpacity: true, checkVisibilityCSS: true })) continue;
    const r = el.getBoundingClientRect();
    if (r.width < 2 || r.height < 2) continue;
    const tops = [];
    for (let i = 0; i < data.length; i++) {
      const rg = document.createRange();
      rg.setStart(node, i);
      rg.setEnd(node, Math.min(i + 1, node.length));
      const rr = rg.getBoundingClientRect();
      tops.push([Math.round(rr.top), Math.round(rr.width), i]);
    }
    for (let i = 0; i + 1 < tops.length; i++) {
      const a = tops[i][0], b = tops[i + 1][0];
      if (a === b || !Number.isFinite(a) || !Number.isFinite(b)) continue;
      const g1 = data[i], g2 = data[i + 1];
      if (rx.test(g1) && rx.test(g2)) {
        hits.push({
          text: t.slice(0, 30), cut: i, left: g1, right: g2,
          tag: el.tagName, cls: (el.getAttribute("class") || "").slice(0, 40),
          tid: el.getAttribute("data-testid") || "",
          widths: tops.map(x => x[1]).slice(0, 8), box: [Math.round(r.width), Math.round(r.height)],
        });
        break;
      }
    }
  }
  return hits;
};

(async () => {
  const b = await chromium.launch({ channel: "chrome", headless: true });
  const all = [];
  for (const w of [320, 360, 390, 430]) {
    for (const loc of ["zh-CN", "en"]) {
      for (const [screen, sel] of STEPS) {
        const p = await b.newPage({ viewport: { width: w, height: 820 } });
        await p.addInitScript((l) => {
          localStorage.setItem("citynexus.v8.journey_id", "22222222-2222-4222-8222-222222222222");
          localStorage.setItem("citynexus.theme", "light");
          localStorage.setItem("citynexus.locale", l);
        }, loc);
        await p.goto("http://127.0.0.1:8121/", { waitUntil: "networkidle" });
        await p.waitForTimeout(1900);
        if (sel) { await p.evaluate((s) => { const e = document.querySelector(s); if (e) e.click(); }, sel); await p.waitForTimeout(1100); }
        const hits = await p.evaluate(SCAN, CJK);
        for (const h of hits) all.push({ width: w, locale: loc, screen, ...h });
        await p.close();
      }
      process.stdout.write(w + loc + " ");
    }
  }
  console.log("");
  fs.writeFileSync("D:/moodle/_cmdr_fe_rev_1016/cjk_break_scan.json", JSON.stringify(all, null, 1), "utf-8");
  const by = {};
  for (const h of all) { const k = h.text + "||" + (h.cls || h.tid || h.tag); (by[k] = by[k] || { ...h, n: 0, widths: new Set() }).n += 1; by[k].widths.add(h.width); }
  const list = Object.values(by).sort((x, y) => y.n - x.n);
  console.log("候选断行处合计", all.length, "| 去重后元素种数", list.length);
  for (const h of list.slice(0, 22)) {
    console.log("  " + h.text.slice(0, 14).padEnd(14) + " 断在「" + h.left + "|" + h.right + "」处 | 命中 " + h.n +
      " 格 | 宽度档 " + Array.from(h.widths).join("/") + " | " + (h.cls ? "." + h.cls.split(" ")[0] : "") + (h.tid ? " [" + h.tid + "]" : ""));
  }
  await b.close();
})().catch(e => { console.log("FATAL " + e); process.exit(1); });
