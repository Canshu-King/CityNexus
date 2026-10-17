/* 票夹那三张卡的逐枚直读：两档宽度 × 两主题，每张卡报它自己的底、自己的字、边框、
 * 语义标签的颜色，以及"标签叠在合成底色上"的 WCAG 比值；另各截一张元素图，方便我用眼睛复核。
 * 用法：node _cmdr_tripstop_read_r1.cjs <标签>
 */
const fs = require("fs");
const { chromium } = require("D:/moodle/CityNexus/frontend/node_modules/playwright/index.js");
const LABEL = process.argv[2] || "run";

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
  return Math.round(((Math.max(a, b) + 0.05) / (min_(a, b) + 0.05)) * 100) / 100;
}
function min_(a, b) { return Math.min(a, b); }

const READ = `(() => {
  const cards = Array.from(document.querySelectorAll("article.trip-stop"));
  const stackOf = (el) => {
    const st = []; let anc = el, base = null, hops = 0;
    while (anc && hops < 12) {
      const c = getComputedStyle(anc).backgroundColor;
      const m = /rgba?\\(([^)]+)\\)/.exec(c || "");
      if (m) { const p = m[1].split(",").map(x => Number(x.trim())); const a = p.length === 4 ? p[3] : 1;
               if (a > 0) { st.push({t:[p[0],p[1],p[2]], a}); if (a >= 1) { base = [p[0],p[1],p[2]]; break; } } }
      anc = anc.parentElement; hops++;
    }
    return { stack: st, base };
  };
  return cards.map(el => {
    const cs = getComputedStyle(el);
    const lab = el.querySelector(".trip-stop-protected, .trip-stop-disrupted, .trip-stop-current");
    const time = el.querySelector(".trip-stop-time b, b");
    return {
      cls: el.className,
      own_bg: cs.backgroundColor, own_color: cs.color, border: cs.borderTopColor,
      label_sel: lab ? ("." + lab.className.trim().split(/\\s+/).join(".")) : "",
      label_color: lab ? getComputedStyle(lab).color : "", label_text: lab ? lab.textContent.trim().slice(0, 14) : "",
      label_stack: lab ? stackOf(lab) : null,
      time_color: time ? getComputedStyle(time).color : "", time_text: time ? time.textContent.trim().slice(0, 14) : "",
      time_stack: time ? stackOf(time) : null,
    };
  });
})()`;

(async () => {
  const b = await chromium.launch({ channel: "chrome", headless: true });
  const rec = { label: LABEL, at: new Date().toISOString(), rows: [] };
  for (const W of [390, 1280]) {
    for (const theme of ["light", "dark"]) {
      const p = await b.newPage({ viewport: { width: W, height: 860 } });
      await p.addInitScript((t) => {
        localStorage.setItem("citynexus.v8.journey_id", "22222222-2222-4222-8222-222222222222");
        localStorage.setItem("citynexus.theme", t);
        localStorage.setItem("citynexus.locale", "zh-CN");
      }, theme);
      await p.goto("http://127.0.0.1:8121/", { waitUntil: "networkidle" });
      await p.waitForTimeout(2000);
      await p.evaluate(() => { const e = document.querySelector('[data-testid="nav-trips"]'); if (e) e.click(); });
      await p.waitForTimeout(1400);
      const heading = await p.evaluate(() => ((document.querySelector(".v8-page h1") || {}).innerText) || "");
      const cards = await p.evaluate(READ);
      for (const c of cards) {
        const row = { w: W, theme, heading, cls: c.cls, own_bg: c.own_bg, own_color: c.own_color, border: c.border,
                      label_sel: c.label_sel, label_color: c.label_color, label_text: c.label_text,
                      time_color: c.time_color, time_text: c.time_text };
        for (const [key, node] of [["label", c.label_stack], ["time", c.time_stack]]) {
          if (!node || !node.stack.length) continue;
          const base = node.base || (theme === "dark" ? [0, 0, 0] : [255, 255, 255]);
          const eff = composite(node.stack, base);
          const fgKey = key === "label" ? c.label_color : c.time_color;
          const fg = parse(fgKey);
          row[key + "_eff_bg"] = "rgb(" + eff.map(x => Math.round(x)).join(", ") + ")";
          row[key + "_ratio"] = fg ? ratio(fg.t, eff) : null;
        }
        rec.rows.push(row);
        console.log("w=" + W + " " + theme + " | " + c.cls.slice(0, 34).padEnd(34) + " | 卡底 " + c.own_bg.padEnd(22)
          + " | 卡字 " + c.own_color.padEnd(20) + " | 标签 " + (c.label_sel || "-").slice(0, 26).padEnd(26)
          + " " + (c.label_color || "-").padEnd(20) + " 比值 " + (row.label_ratio === undefined ? "-" : row.label_ratio)
          + " | 时间字 " + (c.time_color || "-").padEnd(20) + " 比值 " + (row.time_ratio === undefined ? "-" : row.time_ratio));
      }
      if (theme === "dark" && W === 390) {
        for (const want of ["protected", "disrupted"]) {
          const loc = p.locator("article.trip-stop." + want).first();
          if (await loc.count() > 0) await loc.screenshot({ path: "D:/moodle/_cmdr_fe_rev_1016/shots/tripstop_" + want + "_dark.png" });
        }
      }
      await p.close();
    }
  }
  fs.writeFileSync("D:/moodle/_cmdr_fe_rev_1016/tripstop_read_" + LABEL + ".json", JSON.stringify(rec, null, 1), "utf-8");
  console.log("读数落 tripstop_read_" + LABEL + ".json，共 " + rec.rows.length + " 行");
  await b.close();
})().catch(e => { console.log("FATAL " + e); process.exit(1); });
