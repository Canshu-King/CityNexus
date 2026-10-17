/* 小字灰的清点 v2：六屏上每一处"自己直接带文字"的元素，算出它真正坐在哪层底色上。
 *
 * 为什么要有 v2：v1 把 rgba(255,159,10,0.12) 当成不透明的 rgb(255,159,10) 来比，
 * 于是报出一堆 1.89、1.2 的假红——半透明那层要先和它下面的层合成，才是眼睛看到的那一手。
 * 这一版沿祖先链取每一层 (色, alpha)，自下而上合成到不透明为止，再算比值；
 * 同时记下"这层底色是谁给的"（那一枚选择器就是我下一刀要改的规则）。
 *
 * 用法：node _cmdr_muted_scan_r2.cjs <标签> [宽度,逗号分隔]
 */
const fs = require("fs");
const { chromium } = require("D:/moodle/CityNexus/frontend/node_modules/playwright/index.js");
const LABEL = process.argv[2] || "run";
const WIDTHS = (process.argv[3] || "390,1280").split(",").map(Number);

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
  const a = p.length === 4 ? p[3] : 1;
  return { t: [p[0], p[1], p[2]], a };
}
function composite(layers, baseT) { // layers: 由近到远（元素自己最先），baseT 是不透明底层
  let cur = baseT.slice();
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

const SNAP = `(() => {
  const out = [];
  const selOf = (el) => el.tagName.toLowerCase() + (typeof el.className === "string" && el.className ? "." + el.className.trim().split(/\\s+/).slice(0, 2).join(".") : "");
  for (const el of Array.from(document.querySelectorAll("body *"))) {
    if (!el.checkVisibility({ checkOpacity: true, checkVisibilityCSS: true })) continue;
    const r = el.getBoundingClientRect();
    if (r.width < 1 || r.height < 1) continue;
    const own = Array.from(el.childNodes).filter(n => n.nodeType === 3).map(n => n.textContent).join("").trim();
    if (!own) continue;
    const cs = getComputedStyle(el);
    const stack = [];
    let anc = el, opaqueBase = null, baseOwner = "";
    let hops = 0;
    while (anc && hops < 12) {
      const c = getComputedStyle(anc).backgroundColor;
      const m = /rgba?\\(([^)]+)\\)/.exec(c || "");
      if (m) {
        const p = m[1].split(",").map(x => Number(x.trim()));
        const a = p.length === 4 ? p[3] : 1;
        if (a > 0) {
          stack.push({ t: [p[0], p[1], p[2]], a, sel: selOf(anc), tid: anc.getAttribute("data-testid") || "" });
          if (a >= 1) { opaqueBase = [p[0], p[1], p[2]]; baseOwner = selOf(anc); break; }
        }
      }
      anc = anc.parentElement; hops++;
    }
    out.push({
      sel: selOf(el), tid: el.getAttribute("data-testid") || "",
      color: cs.color, font_size: cs.fontSize, font_weight: cs.fontWeight,
      text: own.slice(0, 26),
      stack, opaque_base: opaqueBase, base_owner: baseOwner, base_hops: hops,
    });
  }
  return out;
})()`;

(async () => {
  const b = await chromium.launch({ channel: "chrome", headless: true });
  const all = [];
  for (const W of WIDTHS) {
    for (const theme of ["light", "dark"]) {
      for (const [screen, sel] of STEPS) {
        const p = await b.newPage({ viewport: { width: W, height: 860 } });
        await p.addInitScript((t) => {
          localStorage.setItem("citynexus.v8.journey_id", "22222222-2222-4222-8222-222222222222");
          localStorage.setItem("citynexus.theme", t);
          localStorage.setItem("citynexus.locale", "zh-CN");
        }, theme);
        await p.goto("http://127.0.0.1:8121/", { waitUntil: "networkidle" });
        await p.waitForTimeout(2000);
        if (sel) { await p.evaluate((s) => { const e = document.querySelector(s); if (e) e.click(); }, sel); await p.waitForTimeout(1300); }
        const rootBg = await p.evaluate(() => {
          const g = (e) => { const c = getComputedStyle(e).backgroundColor; const m = /rgba?\(([^)]+)\)/.exec(c); return m ? [Number(m[1].split(",")[0]), Number(m[1].split(",")[1]), Number(m[1].split(",")[2])] : null; };
          return { body: g(document.body), html: g(document.documentElement) };
        });
        for (const row of await p.evaluate(SNAP)) {
          const fg = parse(row.color);
          if (!fg) continue;
          const base = row.opaque_base || (theme === "dark" ? [0, 0, 0] : [255, 255, 255]);
          const eff = composite(row.stack, base);
          const rt = ratio(fg.t, eff);
          // 最近一层"不是完全透明"的底色是谁给的：那枚选择器就是可改的规则所有者
          const owner = row.stack.length ? row.stack[0] : null;
          all.push({ w: W, theme, screen, color: row.color, font_size: row.font_size, font_weight: row.font_weight,
                    text: row.text, sel: row.sel, tid: row.tid,
                    nearest_bg: owner ? ("rgba(" + owner.t.concat([owner.a]).join(", ") + ")") : "none",
                    nearest_bg_owner_sel: owner ? owner.sel : "(root)", nearest_bg_owner_hops: owner ? 0 : row.base_hops,
                    opaque_base: "rgb(" + base.join(", ") + ")", base_owner_sel: row.base_owner || "(root/html)",
                    effective_bg: "rgb(" + eff.map(x => Math.round(x)).join(", ") + ")",
                    ratio: rt, fails_aa: rt < 4.5, no_opaque_found: !row.opaque_base, root_bg: JSON.stringify(rootBg) });
        }
        await p.close();
      }
    }
  }
  const fails = all.filter(x => x.fails_aa);
  const byKey = {};
  for (const f of fails) {
    const k = [f.sel, f.tid, f.color, f.effective_bg, f.ratio].join("||");
    byKey[k] = byKey[k] || { sel: f.sel, tid: f.tid, color: f.color, effective_bg: f.effective_bg, ratio: f.ratio,
                             nearest_bg: f.nearest_bg, nearest_bg_owner_sel: f.nearest_bg_owner_sel,
                             base_owner_sel: f.base_owner_sel, font_size: f.font_size, font_weight: f.font_weight,
                             occurrences: 0, screens: {}, samples: [] };
    byKey[k].occurrences += 1;
    const skey = f.w + "/" + f.theme + "/" + f.screen;
    byKey[k].screens[skey] = (byKey[k].screens[skey] || 0) + 1;
    if (byKey[k].samples.length < 3) byKey[k].samples.push(f.text);
  }
  const list = Object.values(byKey).sort((x, y) => x.ratio - y.ratio);
  fs.writeFileSync("D:/moodle/_cmdr_fe_rev_1016/muted_scan_" + LABEL + ".json",
    JSON.stringify({ scanned: all.length, failing_readings: fails.length, distinct_kinds: list.length,
                     no_opaque_base_rows: all.filter(x => x.no_opaque_found).length, kinds: list }, null, 1), "utf-8");
  console.log("标签=" + LABEL + " 读数 " + all.length + " 条｜合成后仍低于 4.5 的：" + fails.length + " 条，去重 " + list.length + " 种｜没找到不透明底层的行数 " + all.filter(x => x.no_opaque_found).length);
  for (const k of list.slice(0, 26)) {
    console.log("  ratio " + k.ratio + " | " + k.sel.slice(0, 34) + " | 字 " + k.color + " | 有效底 " + k.effective_bg
      + " | 最近那层 " + k.nearest_bg + " 属于 " + k.nearest_bg_owner_sel.slice(0, 30)
      + " | " + k.font_size + "/" + k.font_weight + " | " + k.occurrences + " 次 | " + Object.keys(k.screens).join(",")
      + " | " + k.samples.join(" / "));
  }
  await b.close();
})().catch(e => { console.log("FATAL " + e); process.exit(1); });
