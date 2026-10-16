/* 「路线证据」这一枚：上一版没找到它，因为抽屉的 details 没点开。这一版先点开再量。
 * 同一页里 control 与 keep-all 前后对拍，四档宽度。 */
const fs = require("fs");
const { chromium } = require("D:/moodle/CityNexus/frontend/node_modules/playwright/index.js");

const FIND = () => {
  const scopes = ["details.v9-evidence-drawer", ".v9-evidence-drawer"];
  for (const s of scopes) {
    for (const root of document.querySelectorAll(s)) {
      for (const el of root.querySelectorAll("*")) {
        if (el.childElementCount !== 0) continue;
        const t = (el.textContent || "").trim();
        if (!t.includes("路线证据")) continue;
        const r = el.getBoundingClientRect();
        if (r.width < 2 || r.height < 2) continue;
        el.setAttribute("data-cnx-probe", "B");
        return { found: true, tag: el.tagName, cls: (el.getAttribute("class") || "").slice(0, 40), text: t.slice(0, 24), drawer_open: root.hasAttribute("open") };
      }
    }
  }
  return { found: false, why: "点开抽屉后仍找不到含「路线证据」的叶子节点" };
};

const LINES = () => {
  const el = document.querySelector('[data-cnx-probe="B"]');
  if (!el) return null;
  const r = new Range();
  r.selectNodeContents(el);
  const rects = Array.from(r.getClientRects()).map(x => ({ w: Math.round(x.width), t: Math.round(x.top) }));
  return { widths: rects.map(x => x.w), lines: new Set(rects.map(x => x.t)).size, box: Math.round(el.getBoundingClientRect().width),
           now: [getComputedStyle(el).wordBreak, getComputedStyle(el).overflowWrap] };
};

(async () => {
  const b = await chromium.launch({ channel: "chrome", headless: true });
  const out = [];
  for (const w of [320, 360, 390, 430]) {
    const p = await b.newPage({ viewport: { width: w, height: 800 } });
    await p.addInitScript(() => {
      localStorage.setItem("citynexus.v8.journey_id", "22222222-2222-4222-8222-222222222222");
      localStorage.setItem("citynexus.theme", "light");
      localStorage.setItem("citynexus.locale", "zh-CN");
    });
    await p.goto("http://127.0.0.1:8121/", { waitUntil: "networkidle" });
    await p.waitForTimeout(2200);
    await p.evaluate(() => { const e = document.querySelector('[data-testid="today-hero-cta"]'); if (e) e.click(); });
    await p.waitForTimeout(1200);
    await p.evaluate(() => { const s = document.querySelector("summary.v9-evidence-summary"); if (s) s.click(); });
    await p.waitForTimeout(900);
    const f = await p.evaluate(FIND);
    const ctrl = f.found ? await p.evaluate(LINES) : null;
    await p.evaluate(() => { const el = document.querySelector('[data-cnx-probe="B"]'); if (el) { el.style.wordBreak = "keep-all"; el.style.overflowWrap = "normal"; } });
    const fixed = f.found ? await p.evaluate(LINES) : null;
    out.push({ width: w, meta: f, control: ctrl, keep_all: fixed });
    await p.close();
  }
  fs.writeFileSync("D:/moodle/_cmdr_fe_rev_1016/wrapfix_B.json", JSON.stringify(out, null, 1), "utf-8");
  for (const r of out) {
    console.log("宽度", r.width, "| 找到", r.meta.found, (r.meta.text || "") + " " + (r.meta.why || ""),
      "| control 行盒", r.control && r.control.widths, "行数", r.control && r.control.lines, "现状", r.control && r.control.now,
      "| keep-all 行盒", r.keep_all && r.keep_all.widths, "行数", r.keep_all && r.keep_all.lines);
  }
  await b.close();
})().catch(e => { console.log("FATAL " + e); process.exit(1); });
