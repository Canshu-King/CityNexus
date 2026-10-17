/* 小字灰的清点：把六屏上每一处"实际渲染出来的文字"按 (前景, 有效背景, 选择器) 去重，
 * 报出 WCAG 比值低于 4.5 的那些。出厂尺只在它自己的判据里报，这一把不问判据、只问算出来的比值，
 * 目的是给我自己定下一刀的顺序，不是替代那把尺。
 *
 * 用法：node _cmdr_muted_scan_r1.cjs <标签> [宽度,逗号分隔]
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
  if (p.length === 4 && p[3] === 0) return null;
  return [p[0], p[1], p[2]];
}
function ratio(fg, bg) {
  const a = lumOf(fg), b = lumOf(bg);
  return Math.round(((Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05)) * 100) / 100;
}

const SNAP = `(() => {
  const out = [];
  for (const el of Array.from(document.querySelectorAll("body *"))) {
    if (!el.checkVisibility({ checkOpacity: true, checkVisibilityCSS: true })) continue;
    const r = el.getBoundingClientRect();
    if (r.width < 1 || r.height < 1) continue;
    const cs = getComputedStyle(el);
    // 只算"这个元素自己直接带的文字"：把子元素的文本排除，避免同一个比值被祖先重复计一遍。
    const own = Array.from(el.childNodes).filter(n => n.nodeType === 3).map(n => n.textContent).join("").trim();
    if (!own) continue;
    let bgEl = el, bg = "rgba(0, 0, 0, 0)";
    while (bgEl) { const c = getComputedStyle(bgEl).backgroundColor; if (c && c !== "rgba(0, 0, 0, 0)") { bg = c; break; } bgEl = bgEl.parentElement; }
    out.push({
      tag: el.tagName.toLowerCase(),
      sel: el.tagName.toLowerCase() + (typeof el.className === "string" && el.className ? "." + el.className.trim().split(/\\s+/).slice(0, 2).join(".") : ""),
      tid: el.getAttribute("data-testid") || "",
      color: cs.color, bg, font_size: cs.fontSize, font_weight: cs.fontWeight,
      text: own.slice(0, 26),
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
        const heading = await p.evaluate(() => ((document.querySelector(".v8-page h1, .v8-page-intro h1") || {}).innerText) || "");
        for (const row of await p.evaluate(SNAP)) {
          const fg = parse(row.color), bgc = parse(row.bg);
          if (!fg || !bgc) continue;
          const rt = ratio(fg, bgc);
          all.push({ w: W, theme, screen, heading, sel: row.sel, tid: row.tid, color: row.color, bg: row.bg,
                    ratio: rt, font_size: row.font_size, font_weight: row.font_weight, text: row.text,
                    fails_aa: rt < 4.5 });
        }
        await p.close();
      }
    }
  }
  const fails = all.filter(x => x.fails_aa);
  const byKey = {};
  for (const f of fails) {
    const k = [f.sel, f.tid, f.color, f.bg, f.ratio].join("||");
    byKey[k] = byKey[k] || { sel: f.sel, tid: f.tid, color: f.color, bg: f.bg, ratio: f.ratio,
                              font_size: f.font_size, font_weight: f.font_weight, occurrences: 0,
                              screens: {}, samples: [] };
    byKey[k].occurrences += 1;
    byKey[k].screens[f.theme + "/" + f.screen] = (byKey[k].screens[f.theme + "/" + f.screen] || 0) + 1;
    if (byKey[k].samples.length < 3) byKey[k].samples.push(f.text);
  }
  const list = Object.values(byKey).sort((x, y) => x.ratio - y.ratio);
  fs.writeFileSync("D:/moodle/_cmdr_fe_rev_1016/muted_scan_" + LABEL + ".json",
    JSON.stringify({ scanned: all.length, distinct_failing_kinds: list.length, kinds: list }, null, 1), "utf-8");
  console.log("标签=" + LABEL + " 扫到直接带字的元素读数 " + all.length + " 条｜低于 4.5 的去重种数 " + list.length);
  for (const k of list.slice(0, 24)) {
    console.log("  ratio " + k.ratio + " | " + k.sel.slice(0, 40) + " | " + k.color + " on " + k.bg
      + " | " + k.font_size + "/" + k.font_weight + " | 出现 " + k.occurrences + " 次 | 屏 "
      + Object.keys(k.screens).join(",") + " | 例：" + k.samples.join(" / "));
  }
  await b.close();
})().catch(e => { console.log("FATAL " + e); process.exit(1); });
