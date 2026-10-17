/* 键盘焦点 + 截断普查 第二版（现尖 17 屏 × 两档宽度）。
 * 第一版有两处要改：
 *   1) 截断判据把 span.v8-sr-only（屏幕阅读专用、本来就靠 clip 藏起来的字）当成"用户看不见的字"，
 *      八条读数全是它，属假阳性 —— 第二版加视觉隐藏排除项，并把排除掉的条数一起出声。
 *   2) "无焦点指示 0" 这个零没有负对照撑着＝哑尺。第二版带 --killfocus 档：
 *      签完名之后注入一条把 outline/box-shadow 抹平的 CSS，同一把尺必须立刻数出红来，
 *      否则这枚零不算证明。
 * 另外把每一屏的 h1..h6 全列出来：第一版有两只屏（trash、access）题头读成 "-"，要分清是"屏上真没标题"
 * 还是"我的尺只找 h1,h2"。
 * 用法：node _cmdr_focus_trunc_r2.cjs <宽度,逗号> <主题> <屏key,逗号或 ALL> [killfocus]
 */
const { chromium } = require("D:/moodle/CityNexus/frontend/node_modules/playwright/index.js");
const fs = require("fs");

const BASE = "http://127.0.0.1:8121";
const ALL_KEYS = ["hub", "live", "map", "studio", "stay", "discover", "import", "bookings",
  "footprints", "agent", "authoritative", "intelligence", "twin", "trash", "access", "trips", "me"];
const WIDTHS = (process.argv[2] ? process.argv[2].split(",") : ["1280", "390"]).map(Number);
const THEME = process.argv[3] || "light";
const KEYS = (!process.argv[4] || process.argv[4] === "ALL") ? ALL_KEYS : process.argv[4].split(",");
const KILL = process.argv.slice(5).includes("killfocus");
const MAX_TABS = 90;

const SIGN = `(() => {
  const sel = 'a,button,input,select,textarea,summary,[tabindex]:not([tabindex="-1"]),[role=button]';
  let n = 0;
  for (const el of Array.from(document.querySelectorAll(sel))) {
    if (!el.checkVisibility({ checkOpacity: true, checkVisibilityCSS: true })) continue;
    const cs = getComputedStyle(el);
    el.__sig0 = [cs.outlineStyle, cs.outlineWidth, cs.outlineColor, cs.boxShadow, cs.borderTopColor,
      cs.borderTopWidth, cs.backgroundColor].join("|");
    el.__tag = el.tagName.toLowerCase() + (typeof el.className === "string" && el.className ? "." + el.className.trim().split(/\\s+/).slice(0, 3).join(".") : "");
    el.__txt = ((el.textContent || el.getAttribute("aria-label") || el.getAttribute("placeholder") || "")
      .replace(/\\s+/g, " ").trim().slice(0, 26));
    el.__idx = n; n++;
  }
  return n;
})()`;

const NOW = `(() => {
  const el = document.activeElement;
  if (!el || el === document.body) return { none: true };
  const cs = getComputedStyle(el);
  const sig = [cs.outlineStyle, cs.outlineWidth, cs.outlineColor, cs.boxShadow, cs.borderTopColor,
    cs.borderTopWidth, cs.backgroundColor].join("|");
  const r = el.getBoundingClientRect();
  return {
    tag: el.__tag || el.tagName.toLowerCase(), txt: el.__txt || "", tid: el.getAttribute("data-testid") || "",
    idx: typeof el.__idx === "number" ? el.__idx : null,
    before: el.__sig0 || "", after: sig, changed: !!el.__sig0 && el.__sig0 !== sig,
    outline: cs.outlineStyle + " " + cs.outlineWidth + " " + cs.outlineColor,
    box: [Math.round(r.width), Math.round(r.height)],
  };
})()`;

/* 截断第二版：只看真能给眼睛看的字。排除项逐条记数，不静默吞。 */
const TRUNC = `(() => {
  const kept = [], excluded = { sr_only: 0, clipped_box: 0, ellipsis: 0 };
  for (const el of Array.from(document.querySelectorAll("body *"))) {
    const own = Array.from(el.childNodes).filter(n => n.nodeType === 3).map(n => n.textContent).join("").trim();
    if (!own) continue;
    if (!el.checkVisibility({ checkOpacity: true, checkVisibilityCSS: true })) continue;
    const cs = getComputedStyle(el);
    if (!/hidden|clip|ellipsis/.test(cs.overflowX)) continue;
    if (el.scrollWidth - el.clientWidth <= 2) continue;
    if (cs.textOverflow === "ellipsis") { excluded.ellipsis++; continue; }
    const cn = (typeof el.className === "string" ? el.className : "");
    if (/sr-only|visually-hidden|screen-reader/.test(cn) || cs.clipPath !== "none"
        || (cs.position === "absolute" && el.getBoundingClientRect().width <= 2)) { excluded.sr_only++; continue; }
    kept.push({ tag: el.tagName.toLowerCase() + (cn ? "." + cn.trim().split(/\\s+/).slice(0, 3).join(".") : ""),
      txt: own.slice(0, 24), tid: el.getAttribute("data-testid") || "", over: el.scrollWidth - el.clientWidth,
      w: Math.round(el.getBoundingClientRect().width), fs: cs.fontSize });
  }
  return { kept: kept, excluded: excluded };
})()`;

const HEADINGS = `(() => {
  const hs = Array.from(document.querySelectorAll("h1,h2,h3,h4,h5,h6")).filter(h => h.checkVisibility());
  return hs.map(h => h.tagName + ":" + h.textContent.replace(/\\s+/g, " ").trim().slice(0, 40));
})()`;

(async () => {
  const b = await chromium.launch({ channel: "chrome", headless: true });
  const results = [];
  for (const W of WIDTHS) {
    for (const key of KEYS) {
      const p = await b.newPage({ viewport: { width: W, height: 900 } });
      await p.addInitScript((t) => {
        localStorage.setItem("citynexus.v8.journey_id", "22222222-2222-4222-8222-222222222222");
        localStorage.setItem("citynexus.theme", t);
        localStorage.setItem("citynexus.locale", "zh-CN");
      }, THEME);
      const errs = [];
      p.on("pageerror", e => errs.push(String(e.message).slice(0, 70)));
      await p.goto(BASE + "/", { waitUntil: "networkidle" });
      await p.waitForTimeout(2000);
      await p.evaluate(() => { const e = document.querySelector('[data-testid="v8-mobile-menu"]'); if (e) e.click(); });
      await p.waitForTimeout(900);
      await p.evaluate((k) => { const e = document.querySelector('[data-testid="v8-drawer-entry-' + k + '"]'); if (e) e.click(); }, key);
      await p.waitForTimeout(1500);
      const drawerOpen = await p.evaluate(() => !!document.querySelector('[id="v8-nav-drawer"]'));
      if (drawerOpen) {
        await p.evaluate(() => { const e = document.querySelector('[data-testid="v8-drawer-close"]'); if (e) e.click(); });
        await p.waitForTimeout(700);
      }
      const heads = await p.evaluate(HEADINGS);
      /* 负对照必须在"签名之前"注入：签名与聚焦后的读数要处在同一套 CSS 里，
       * 否则"注入本身改了基线"会被当成焦点指示 —— 第一版对照就错在这个顺序上。 */
      if (KILL) {
        await p.addStyleTag({ content: "*, *::before, *::after { outline: none !important; box-shadow: none !important; }" });
      }
      const nSign = await p.evaluate(SIGN);
      const seen = [];
      const visited = new Set();
      let prevId = "", stuck = 0, wrapped = 0;
      for (let i = 0; i < MAX_TABS; i++) {
        await p.keyboard.press("Tab");
        const s = await p.evaluate(NOW);
        if (s.none) { wrapped++; if (wrapped >= 2) break; continue; }
        const id = (s.idx === null ? "x" + s.tag + "|" + s.txt : "i" + s.idx);
        if (id === prevId) { stuck++; if (stuck >= 2) break; } else { stuck = 0; }
        if (visited.has(id) && seen.length >= 3) break;
        visited.add(id); prevId = id; seen.push(s);
      }
      const tr = await p.evaluate(TRUNC);
      results.push({ w: W, theme: THEME, mode: KILL ? "killfocus" : "normal", key, headings: heads,
        heading_n: heads.length, focusable_signed: nSign, tab_stops: seen.length,
        no_indicator: seen.filter(s => !s.changed).length, indeterminate: seen.filter(s => s.before === "").length,
        trunc_n: tr.kept.length, trunc_excluded: tr.excluded, errs: errs.slice(0, 2),
        no_ind_list: seen.filter(s => !s.changed).slice(0, 6).map(s => ({ tag: s.tag, txt: s.txt, tid: s.tid, outline: s.outline })),
        trunc_list: tr.kept.slice(0, 6) });
      const r = results[results.length - 1];
      console.log("w=" + W + " " + (KILL ? "[杀指示] " : "") + key.padEnd(14) +
        " 标题=" + r.heading_n + " 可聚焦=" + r.focusable_signed + " Tab站=" + r.tab_stops +
        " 无指示=" + r.no_indicator + " 截断=" + r.trunc_n + " (排除 sr-only " + r.trunc_excluded.sr_only +
        " / 省略号 " + r.trunc_excluded.ellipsis + ")");
      await p.close();
    }
  }
  const out = "focus_trunc_" + (KILL ? "kill_" : "") + THEME + "_" + WIDTHS.join("_") + ".json";
  fs.writeFileSync(out, JSON.stringify(results, null, 2));
  const tot = results.reduce((a, r) => a + r.tab_stops, 0);
  const bad = results.reduce((a, r) => a + r.no_indicator, 0);
  const noHead = results.filter(r => r.heading_n === 0).map(r => r.key + "@" + r.w);
  console.log("合计：面 " + results.length + "｜Tab 站 " + tot + "｜无焦点指示 " + bad +
    "｜截断 " + results.reduce((a, r) => a + r.trunc_n, 0) + "｜零标题的屏 " + (noHead.length ? noHead.join(",") : "无") + "｜落盘 " + out);
  await b.close();
})();
