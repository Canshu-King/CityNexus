/* 四枚死灰字面量的逐枚直读：两档宽度 × 两主题 × 六屏，报"这枚选择器在不在屏上、
 * 自己的字色、合成后的底、WCAG 比值"。改前改后各跑一遍，两臂同一把尺。
 * 用法：node _cmdr_muted_sites_read_r1.cjs <标签>
 */
const fs = require("fs");
const { chromium } = require("D:/moodle/CityNexus/frontend/node_modules/playwright/index.js");
const LABEL = process.argv[2] || "run";

const SELECTORS = [".v8-me-card p", ".v9-inbox small", ".v9-offline article span", ".v8-mode-chips button"];
const STEPS = [
  ["hub", null], ["live", '[data-testid="today-hero-cta"]'], ["copilot", '[data-testid="nav-agent"]'],
  ["trips", '[data-testid="nav-trips"]'], ["map", '[data-testid="nav-map"]'], ["me", '[data-testid="nav-me"]'],
];

function srgb(c) { c = c / 255.0; return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); }
function lumOf(t) { return 0.2126 * srgb(t[0]) + 0.7152 * srgb(t[1]) + 0.0722 * srgb(t[2]); }
function parse(rgb) {
  const m = /rgba?\(([^)]+)\)/.exec(rgb || "");
  if (!m) return null;
  const p = m[1].split(",").map(x => Number(x.trim()));
  return { t: [p[0], p[1], p[2]], a: p.length === 4 ? p[3] : 1 };
}
function composite(layers, base) {
  let cur = base.slice();
  for (let i = layers.length - 1; i >= 0; i--) {
    const l = layers[i];
    cur = [0, 1, 2].map(k => l.a * l.t[k] + (1 - l.a) * cur[k]);
  }
  return cur;
}
function ratio(fg, bg) {
  const a = lumOf(fg), b = lumOf(bg);
  return Math.round(((Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05)) * 100) / 100;
}

const READ = (sels) => {
  const stackOf = (el) => {
    const st = []; let anc = el, base = null, hops = 0;
    while (anc && hops < 12) {
      const m = /rgba?\(([^)]+)\)/.exec(getComputedStyle(anc).backgroundColor || "");
      if (m) {
        const p = m[1].split(",").map(x => Number(x.trim()));
        const a = p.length === 4 ? p[3] : 1;
        if (a > 0) { st.push({ t: [p[0], p[1], p[2]], a }); if (a >= 1) { base = [p[0], p[1], p[2]]; break; } }
      }
      anc = anc.parentElement; hops++;
    }
    return { st, base };
  };
  return sels.map(sel => {
    const els = Array.from(document.querySelectorAll(sel));
    const vis = els.filter(e => e.checkVisibility({ checkOpacity: true, checkVisibilityCSS: true })
      && e.getBoundingClientRect().width > 1 && e.getBoundingClientRect().height > 1);
    return {
      sel, in_dom: els.length, visible: vis.length,
      items: vis.slice(0, 4).map(e => {
        const s = stackOf(e);
        return { color: getComputedStyle(e).color, stack: s.st, base: s.base,
                 text: (e.textContent || "").replace(/\s+/g, " ").trim().slice(0, 26) };
      }),
    };
  });
};

(async () => {
  const b = await chromium.launch({ channel: "chrome", headless: true });
  const rec = { label: LABEL, at: new Date().toISOString(), rows: [] };
  for (const W of [390, 1280]) {
    for (const theme of ["light", "dark"]) {
      for (const [screen, nav] of STEPS) {
        const p = await b.newPage({ viewport: { width: W, height: 860 } });
        await p.addInitScript((t) => {
          localStorage.setItem("citynexus.v8.journey_id", "22222222-2222-4222-8222-222222222222");
          localStorage.setItem("citynexus.theme", t);
          localStorage.setItem("citynexus.locale", "zh-CN");
        }, theme);
        await p.goto("http://127.0.0.1:8121/", { waitUntil: "networkidle" });
        await p.waitForTimeout(2000);
        if (nav) { await p.evaluate((s) => { const e = document.querySelector(s); if (e) e.click(); }, nav); await p.waitForTimeout(1300); }
        const out = await p.evaluate(`(${READ.toString()})(${JSON.stringify(SELECTORS)})`);
        for (const one of out) {
          for (const it of one.items) {
            const fg = parse(it.color);
            const base = it.base || (theme === "dark" ? [0, 0, 0] : [255, 255, 255]);
            const eff = composite(it.stack, base);
            rec.rows.push({ w: W, theme, screen, sel: one.sel, in_dom: one.in_dom, visible: one.visible,
                            color: it.color, text: it.text,
                            eff_bg: "rgb(" + eff.map(x => Math.round(x)).join(", ") + ")",
                            ratio: fg ? ratio(fg.t, eff) : null });
          }
        }
        await p.close();
      }
    }
  }
  const bySel = {};
  for (const r of rec.rows) {
    const k = r.sel + "||" + r.color + "||" + r.eff_bg + "||" + r.ratio;
    bySel[k] = bySel[k] || { sel: r.sel, color: r.color, eff_bg: r.eff_bg, ratio: r.ratio, n: 0, where: {} };
    bySel[k].n++; bySel[k].where[r.w + "/" + r.theme + "/" + r.screen] = (bySel[k].where[r.w + "/" + r.theme + "/" + r.screen] || 0) + 1;
  }
  fs.writeFileSync("D:/moodle/_cmdr_fe_rev_1016/muted_sites_" + LABEL + ".json",
    JSON.stringify({ label: LABEL, readings: rec.rows.length, groups: Object.values(bySel), rows: rec.rows }, null, 1), "utf-8");
  console.log("标签=" + LABEL + " 直读命中 " + rec.rows.length + " 条，去重 " + Object.keys(bySel).length + " 组");
  for (const g of Object.values(bySel).sort((x, y) => x.ratio - y.ratio)) {
    console.log("  " + String(g.ratio).padEnd(6) + " | " + g.sel.padEnd(26) + " | 字 " + g.color.padEnd(20)
      + " | 底 " + g.eff_bg.padEnd(20) + " | " + g.n + " 条 | " + Object.keys(g.where).join(","));
  }
  const seen = new Set(rec.rows.map(r => r.sel));
  for (const s of SELECTORS) if (!seen.has(s)) console.log("  没在屏上读到（不渲染或选择器不命中）：" + s);
  await b.close();
})().catch(e => { console.log("FATAL " + e); process.exit(1); });
