/* 窄屏"文字被切掉"的普查：自身溢出（scrollWidth>clientWidth）或右缘越过视口的可见元素。
 * 关键是把"故意省略号截断"与"真被切"分开：逐枚带出 text-overflow、overflow、white-space，
 * 以及父层是否有 overflow:hidden 在裁它。只读数，不改。
 */
const fs = require("fs");
const { chromium } = require("D:/moodle/CityNexus/frontend/node_modules/playwright/index.js");

const STEPS = [
  ["hub", null], ["live", '[data-testid="today-hero-cta"]'], ["copilot", '[data-testid="nav-agent"]'],
  ["trips", '[data-testid="nav-trips"]'], ["map", '[data-testid="nav-map"]'], ["me", '[data-testid="nav-me"]'],
];

const SCAN = () => {
  const hits = [];
  for (const el of document.querySelectorAll("body *")) {
    if (el.childElementCount > 1) continue;
    const t = (el.textContent || "").trim();
    if (t.length < 2) continue;
    if (!el.checkVisibility({ checkOpacity: true, checkVisibilityCSS: true })) continue;
    const r = el.getBoundingClientRect();
    if (r.width < 2 || r.height < 2) continue;
    const cs = getComputedStyle(el);
    const selfOverflow = el.scrollWidth > el.clientWidth + 1;
    const pastViewport = Math.round(r.right) > window.innerWidth + 1;
    const pastDoc = document.documentElement.scrollWidth > window.innerWidth + 1;
    if (!selfOverflow && !pastViewport) continue;
    let clippedBy = null, n = el.parentElement;
    while (n && n !== document.body) {
      const ncs = getComputedStyle(n);
      if (ncs.overflow !== "visible" || ncs.overflowX !== "visible") { clippedBy = (n.className || n.tagName).toString().split(" ")[0]; break; }
      n = n.parentElement;
    }
    hits.push({
      text: t.slice(0, 30), tag: el.tagName, cls: (el.getAttribute("class") || "").slice(0, 34),
      tid: el.getAttribute("data-testid") || "", self_overflow: selfOverflow,
      scroll_w: el.scrollWidth, client_w: el.clientWidth, past_viewport: pastViewport, right: Math.round(r.right),
      text_overflow: cs.textOverflow, white_space: cs.whiteSpace, overflow_x: cs.overflowX, clipped_by: clippedBy,
      doc_overflow: pastDoc,
    });
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
        await p.waitForTimeout(1800);
        if (sel) { await p.evaluate((s) => { const e = document.querySelector(s); if (e) e.click(); }, sel); await p.waitForTimeout(1000); }
        for (const h of await p.evaluate(SCAN)) all.push({ width: w, locale: loc, screen, ...h });
        await p.close();
      }
      process.stdout.write(w + loc + " ");
    }
  }
  console.log("");
  fs.writeFileSync("D:/moodle/_cmdr_fe_rev_1016/overflow_scan.json", JSON.stringify(all, null, 1), "utf-8");
  const by = {};
  for (const h of all) {
    const k = (h.cls || h.tid || h.tag) + "||" + h.text.slice(0, 12);
    (by[k] = by[k] || { ...h, n: 0, where: new Set() }).n += 1;
    by[k].where.add(h.width + h.locale.slice(0, 2) + "/" + h.screen);
  }
  const list = Object.values(by).sort((x, y) => y.n - x.n);
  console.log("溢出元素处数", all.length, "| 去重种数", list.length);
  for (const h of list.slice(0, 26)) {
    console.log("  " + h.text.slice(0, 12).padEnd(13) + " | " + (h.cls || h.tid || h.tag).slice(0, 26).padEnd(27) +
      " 自身溢出" + (h.self_overflow ? "是" : "否") + " 越视口" + (h.past_viewport ? "是" : "否") +
      " 省略号:" + h.text_overflow + " 空白:" + h.white_space.slice(0, 9) + " 裁于:" + (h.clipped_by || "-") + " ×" + h.n + " " + Array.from(h.where).slice(0, 4).join(","));
  }
  await b.close();
})().catch(e => { console.log("FATAL " + e); process.exit(1); });
