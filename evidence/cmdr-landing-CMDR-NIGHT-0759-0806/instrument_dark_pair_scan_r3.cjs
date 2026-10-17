/* 暗档"两张白"现场清点：同一枚元素在两主题下各读一次 computed 背景与前景，只比"实际生效的那一手"。
 *
 * 为什么不用静态推：06:1x 我那把"从 CSS 文本里推断有没有暗档配对"的镜头试过两次都不可信
 * （把 .v8-runtime-card 与 .v8-runtime-card small 当成同一种元素；又在压缩行里取错选择器，
 *  把作用于一切的规则从两行膨胀到 82 行，见账本 CMDR-NIGHT-0730）。
 * 这一版不问 CSS 写了什么，只问浏览器最后算什么：两主题各扫一遍，按 (选择器, testid, 文本) 对齐，
 * 报"暗档下仍然是浅底（相对亮度 > 0.72）"的元素——那才是用户真看到的白卡片。
 */
const fs = require("fs");
const { chromium } = require("D:/moodle/CityNexus/frontend/node_modules/playwright/index.js");

const STEPS = [
  ["hub", null], ["live", '[data-testid="today-hero-cta"]'], ["copilot", '[data-testid="nav-agent"]'],
  ["trips", '[data-testid="nav-trips"]'], ["map", '[data-testid="nav-map"]'], ["me", '[data-testid="nav-me"]'],
];
const W = Number(process.argv[2] || 1280);
const TAG = process.argv[3] ? "_" + process.argv[3] : "";

function srgb(c) { c = c / 255.0; return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); }
function lumOf(t) { return 0.2126 * srgb(t[0]) + 0.7152 * srgb(t[1]) + 0.0722 * srgb(t[2]); }
function parse(rgb) {
  const m = /rgba?\(([^)]+)\)/.exec(rgb || "");
  if (!m) return null;
  const n = m[1].split(",").map(x => parseFloat(x.trim()));
  if (n.length >= 4 && n[3] === 0) return null;
  return [n[0], n[1], n[2]];
}

const SNAP = () => {
  const out = [];
  for (const el of document.querySelectorAll("body *")) {
    if (!el.checkVisibility({ checkOpacity: true, checkVisibilityCSS: true })) continue;
    const r = el.getBoundingClientRect();
    if (r.width < 24 || r.height < 12) continue;
    if (r.top > window.innerHeight || r.bottom < 0) continue;
    const cs = getComputedStyle(el);
    out.push({
      sel: el.tagName.toLowerCase() + (typeof el.className === "string" && el.className ? "." + el.className.trim().split(/\s+/).slice(0, 2).join(".") : ""),
      tid: el.getAttribute("data-testid") || "",
      text: (el.innerText || "").replace(/\s+/g, " ").trim().slice(0, 18),
      own_bg: cs.backgroundColor, color: cs.color, radius: cs.borderRadius,
      area: Math.round(r.width * r.height),
    });
  }
  return out;
};

(async () => {
  const b = await chromium.launch({ channel: "chrome", headless: true });
  const by = {};
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
      if (sel) { await p.evaluate((s) => { const e = document.querySelector(s); if (e) e.click(); }, sel); await p.waitForTimeout(1200); }
      for (const row of await p.evaluate(SNAP)) {
        const k = screen + "||" + row.sel + "||" + row.tid + "||" + row.text;
        by[k] = by[k] || { screen, sel: row.sel, tid: row.tid, text: row.text, area: row.area };
        by[k][theme] = row;
      }
      await p.close();
    }
  }
  const rows = Object.values(by).filter(x => x.light && x.dark);
  const unpaired = [];
  for (const x of rows) {
    const lb = parse(x.dark.own_bg);
    if (!lb) continue;
    const L = lumOf(lb);
    if (L > 0.72) {
      const sameAsLight = x.light.own_bg === x.dark.own_bg;
      const dc = parse(x.dark.color);
      unpaired.push({ screen: x.screen, sel: x.sel, tid: x.tid, text: x.text, dark_bg: x.dark.own_bg, bg_lum: round(L),
                      dark_color: x.dark.color, color_lum: dc ? round(lumOf(dc)) : null,
                      与亮档同一手: sameAsLight, contrast: dc ? round((Math.max(L, lumOf(dc)) + .05) / (Math.min(L, lumOf(dc)) + .05)) : null });
    }
  }
  function round(n) { return Math.round(n * 100) / 100; }
  fs.writeFileSync("D:/moodle/_cmdr_fe_rev_1016/dark_pair_scan_" + W + TAG + ".json", JSON.stringify({ rows_scanned: rows.length, unpaired }, null, 1), "utf-8");
  console.log("宽度", W, TAG, "| 两主题都对上的元素", rows.length, "| 暗档仍浅底", unpaired.length);
  const seen = new Set();
  for (const u of unpaired.sort((x, y) => y.area - x.area)) {
    const k = u.screen + u.sel + u.tid;
    if (seen.has(k)) continue;
    seen.add(k);
    console.log("   " + u.screen.padEnd(8) + " | " + u.sel.slice(0, 34).padEnd(34) + " | " + (u.tid || "-").slice(0, 24).padEnd(24)
      + " | bg " + u.dark_bg + " (lum " + u.bg_lum + ") | ink " + u.dark_color + " | contrast " + u.contrast
      + " | " + (u.与亮档同一手 ? "与亮档同一手（没暗档这一手）" : "暗档另有值但仍浅"));
  }
  await b.close();
})().catch(e => { console.log("FATAL " + e); process.exit(1); });
