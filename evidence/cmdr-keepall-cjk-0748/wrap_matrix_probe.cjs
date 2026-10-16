/* 折行修复选型 v2：只量"那一枚词自己的元素"，control 与改法在同一页里前后对拍。
 *
 * 为什么有这一版：v1 那把尺里 B 与 C 两枚选择器抓错了元素（B 抓到一枚空文本的图标 span，
 * C 抓到装三枚徽章的容器），于是它们的"零劈开"是空的，不能当证据。这一版按文字找叶子节点
 * （childElementCount === 0 且自身文本含目标词），并且在同一页里先量 control、
 * 再给这一枚加 inline 的候选改法、再量一次——同一元素、同一宽度、同一时刻，只有改法不同。
 */
const fs = require("fs");
const { chromium } = require("D:/moodle/CityNexus/frontend/node_modules/playwright/index.js");

const WIDTHS = [320, 360, 390, 430];
const TARGETS = [
  { key: "A", word: "证据", scope: "summary.v9-evidence-summary", screen: "live" },
  { key: "B", word: "路线证据", scope: ".v9-evidence-drawer", screen: "live" },
  { key: "C", word: "模拟承诺", scope: ".v8-booking-card", screen: "bookings" },
  { key: "E", word: "生效中", scope: ".v8-booking-card", screen: "bookings" },
  { key: "D", word: "中途", scope: ".v13-2-memory-panel, section", screen: "bookings" },
];
const CANDIDATES = [
  ["keep-all", "keep-all", "normal"],
  ["keep-all only", "keep-all", null],
];

const FIND = (spec) => {
  const roots = document.querySelectorAll(spec.scope.split(",").map(s => s.trim()).join(","));
  for (const root of roots) {
    const els = root.querySelectorAll("*");
    for (const el of els) {
      if (el.childElementCount !== 0) continue;
      const t = (el.textContent || "").trim();
      if (t.includes(spec.word)) {
        const r = el.getBoundingClientRect();
        if (r.width > 1 && r.height > 1 && el.checkVisibility({ checkOpacity: true, checkVisibilityCSS: true })) {
          el.setAttribute("data-cnx-probe", spec.key);
          return { found: true, tag: el.tagName, cls: (el.getAttribute("class") || "").slice(0, 40), text: t.slice(0, 26) };
        }
      }
    }
  }
  return { found: false, why: "该屏上找不到含这枚词的叶子节点（可能这一代没渲染这个状态）" };
};

const LINES = (key) => {
  const el = document.querySelector('[data-cnx-probe="' + key + '"]');
  if (!el) return null;
  const r = new Range();
  r.selectNodeContents(el);
  const rects = Array.from(r.getClientRects()).map(x => ({ w: Math.round(x.width), t: Math.round(x.top) }));
  const tops = new Set(rects.map(x => x.t));
  return { n_rects: rects.length, n_lines: tops.size, widths: rects.map(x => x.w), text: (el.textContent || "").trim().slice(0, 22),
           style_now: [getComputedStyle(el).wordBreak, getComputedStyle(el).overflowWrap] };
};

(async () => {
  const b = await chromium.launch({ channel: "chrome", headless: true });
  const out = [];
  for (const w of WIDTHS) {
    const p = await b.newPage({ viewport: { width: w, height: 800 } });
    await p.addInitScript(() => {
      localStorage.setItem("citynexus.v8.journey_id", "22222222-2222-4222-8222-222222222222");
      localStorage.setItem("citynexus.theme", "light");
      localStorage.setItem("citynexus.locale", "zh-CN");
    });
    await p.goto("http://127.0.0.1:8121/", { waitUntil: "networkidle" });
    await p.waitForTimeout(2300);
    await p.evaluate(() => { const e = document.querySelector('[data-testid="today-hero-cta"]'); if (e) e.click(); });
    await p.waitForTimeout(1200);
    for (const t of TARGETS.filter(x => x.screen === "live")) {
      const f = await p.evaluate(FIND, t);
      const ctrl = f.found ? await p.evaluate(LINES, t.key) : null;
      const tries = [];
      for (const [name, wb, ow] of CANDIDATES) {
        await p.evaluate(({ key, wb, ow }) => {
          const el = document.querySelector('[data-cnx-probe="' + key + '"]');
          if (el) { el.style.wordBreak = wb; if (ow) el.style.overflowWrap = ow; }
        }, { key: t.key, wb, ow });
        const m = f.found ? await p.evaluate(LINES, t.key) : null;
        tries.push({ name, m });
        await p.evaluate((key) => { const el = document.querySelector('[data-cnx-probe="' + key + '"]'); if (el) { el.style.wordBreak = ""; el.style.overflowWrap = ""; } }, t.key);
      }
      out.push({ width: w, target: t.key, word: t.word, found: f.found, meta: f, control: ctrl, tries });
    }
    await p.evaluate(() => { const e = document.querySelector('[data-testid="nav-trips"]'); if (e) e.click(); });
    await p.waitForTimeout(900);
    await p.evaluate(() => { const e = document.querySelector('[data-testid="trips-tab-bookings"]'); if (e) e.click(); });
    await p.waitForTimeout(1200);
    for (const t of TARGETS.filter(x => x.screen === "bookings")) {
      const f = await p.evaluate(FIND, t);
      const ctrl = f.found ? await p.evaluate(LINES, t.key) : null;
      const tries = [];
      for (const [name, wb, ow] of CANDIDATES) {
        await p.evaluate(({ key, wb, ow }) => {
          const el = document.querySelector('[data-cnx-probe="' + key + '"]');
          if (el) { el.style.wordBreak = wb; if (ow) el.style.overflowWrap = ow; }
        }, { key: t.key, wb, ow });
        const m = f.found ? await p.evaluate(LINES, t.key) : null;
        tries.push({ name, m });
        await p.evaluate((key) => { const el = document.querySelector('[data-cnx-probe="' + key + '"]'); if (el) { el.style.wordBreak = ""; el.style.overflowWrap = ""; el.removeAttribute("data-cnx-probe"); } }, t.key);
        continue;
      }
      out.push({ width: w, target: t.key, word: t.word, found: f.found, meta: f, control: ctrl, tries });
    }
    await p.close();
    process.stdout.write(w + " ");
  }
  console.log("");
  fs.writeFileSync("D:/moodle/_cmdr_fe_rev_1016/wrapfix_matrix_r2.json", JSON.stringify(out, null, 1), "utf-8");
  for (const r of out) {
    if (!r.found) { console.log("宽度 %d %s「%s」→ 没找到这枚词：%s" % (r.width, r.target, r.word, (r.meta.why || "").slice(0, 40))); continue; }
    const c = r.control;
    const line = ["宽度 %d %s「%s」文本=%r control 行数=%d 行盒=%s 现状=%s" % (r.width, r.target, r.word, c.text, c.n_lines, c.widths.join("/"), c.style_now.join("+"))];
    for (const t of r.tries) line.push(" | %s -> 行数 %d 盒 %s" % (t.name, t.m ? t.m.n_lines : -1, t.m ? t.m.widths.join("/") : "-"));
    console.log(line.join(""));
  }
  await b.close();
})().catch(e => { console.log("FATAL " + e); process.exit(1); });
