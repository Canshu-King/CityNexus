/* 合成尺第二版：把 background-image 里那层渐变也算进底色。
 * 为什么必须出这一版：手机上「权威行程执行」那屏下半部整张卡是浅的，而两臂十七屏普查里
 * 它一条都没报——因为 `section.v12-authoritative-panel` 的 background-color 是透明的，
 * 浅色来自 `background-image: linear-gradient(...)`，第一版尺只沿 backgroundColor 爬祖先链，
 * 于是把黑底当成了它的底，替那张卡判了"绿"。这是尺的盲区，不是产品没错。
 * 做法：同一根祖先链上，先把每层的 background-color 压进来，再把该层 background-image 里
 * 出现的每个 rgba/rgb 色标各压一次，得到一组候选底色；比值取最差的那一枚。
 * 正控两枚沿用：侧栏 `em`「•••」1280 亮档 2.18、Copilot 紫药丸 3.97。
 * 用法：node _cmdr_grad_scan_r1.cjs <key,逗号或 ALL> <宽度,逗号> <主题,逗号>
 */
const fs = require("fs");
const { chromium } = require("D:/moodle/CityNexus/frontend/node_modules/playwright/index.js");
const BASE = "http://127.0.0.1:8121";
const ALL_KEYS = ["hub", "live", "map", "studio", "stay", "discover", "import", "bookings",
  "footprints", "agent", "authoritative", "intelligence", "twin", "trash", "access", "trips", "me"];
const KEYS = (!process.argv[2] || process.argv[2] === "ALL") ? ALL_KEYS : process.argv[2].split(",");
const WIDTHS = (process.argv[3] || "1280,390").split(",").map(Number);
const THEMES = (process.argv[4] || "light,dark").split(",");

const SNAP = `(() => {
  const srgb = (c) => { c = c / 255.0; return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); };
  const lum = (t) => 0.2126 * srgb(t[0]) + 0.7152 * srgb(t[1]) + 0.0722 * srgb(t[2]);
  const parse = (rgb) => { const m = /rgba?\\(([^)]+)\\)/.exec(rgb || ""); if (!m) return null;
    const p = m[1].split(",").map(x => Number(x.trim())); return { t: [p[0], p[1], p[2]], a: p.length === 4 ? p[3] : 1 }; };
  const allColors = (s) => { const out = []; const re = /rgba?\\([^)]*\\)/g; let m;
    while ((m = re.exec(s || ""))) { const p = m[0].replace(/rgba?\\(|\\)/g, "").split(",").map(x => Number(x.trim()));
      if (p.length >= 3 && p.slice(0, 3).every(Number.isFinite)) out.push({ t: [p[0], p[1], p[2]], a: p.length === 4 ? p[3] : 1 }); }
    return out; };
  const over = (base, l) => [0, 1, 2].map(k => l.a * l.t[k] + (1 - l.a) * base[k]);
  const name = (el) => el.tagName.toLowerCase() + (typeof el.className === "string" && el.className
    ? "." + el.className.trim().split(/\\s+/).slice(0, 3).join(".") : "");
  const ratio = (a, b) => { const x = lum(a), y = lum(b); return Math.round(((Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05)) * 100) / 100; };
  const out = [];
  for (const el of Array.from(document.querySelectorAll("body *"))) {
    if (!el.checkVisibility({ checkOpacity: true, checkVisibilityCSS: true })) continue;
    const r = el.getBoundingClientRect();
    if (r.width < 1 || r.height < 1) continue;
    const own = Array.from(el.childNodes).filter(n => n.nodeType === 3).map(n => n.textContent).join("").trim();
    if (!own) continue;
    const fg = parse(getComputedStyle(el).color); if (!fg || fg.a < 1) continue;
    let anc = el, hops = 0, opaqueHit = null; const stack = []; const grads = [];
    while (anc && hops < 14) {
      const cs = getComputedStyle(anc);
      const m = parse(cs.backgroundColor);
      if (m && m.a > 0) { stack.push(m); if (m.a >= 1 && !grads.some(g => g.layer === stack.length - 1)) { opaqueHit = stack.length - 1; } }
      const gi = (cs.backgroundImage || "");
      if (gi && gi !== "none" && /gradient\\(/.test(gi)) {
        const stops = allColors(gi);
        if (stops.length) grads.push({ at: stack.length, stops: stops, img: gi.slice(0, 58), n: name(anc) });
      }
      if (opaqueHit !== null) break;
      anc = anc.parentElement; hops++;
    }
    if (opaqueHit === null) continue;
    const bases = [];
    const build = (upto) => { let cur = [255, 255, 255]; for (let i = upto; i >= 0; i--) cur = over(cur, stack[i]); return cur; };
    bases.push({ bg: build(opaqueHit), via: "color" });
    for (const g of grads) {
      for (const s of g.stops) {
        let cur = build(g.at - 1);
        cur = over(cur, s);
        bases.push({ bg: cur, via: "grad:" + g.n + ":" + s.t.join(",") + "@" + s.a.toFixed(2) });
      }
    }
    let worst = null;
    for (const cand of bases) { const rr = ratio(fg.t, cand.bg); if (worst === null || rr < worst.ratio) worst = { ratio: rr, via: cand.via, bg: cand.bg.map(x => Math.round(x)).join(",") }; }
    out.push({ sel: name(el), tid: el.getAttribute("data-testid") || "", text: own.slice(0, 26),
      color: getComputedStyle(el).color, font: getComputedStyle(el).fontSize,
      bg_color_only: bases[0].bg.map(x => Math.round(x)).join(","), ratio_color_only: ratio(fg.t, bases[0].bg),
      worst_bg: worst.bg, worst_ratio: worst.ratio, worst_via: worst.via, grad_layers: grads.length });
  }
  return out;
})()`;

(async () => {
  const b = await chromium.launch({ channel: "chrome", headless: true });
  const rows = [];
  for (const W of WIDTHS) {
    for (const theme of THEMES) {
      for (const key of KEYS) {
        const p = await b.newPage({ viewport: { width: W, height: 900 } });
        await p.addInitScript((t) => {
          localStorage.setItem("citynexus.v8.journey_id", "22222222-2222-4222-8222-222222222222");
          localStorage.setItem("citynexus.theme", t);
          localStorage.setItem("citynexus.locale", "zh-CN");
        }, theme);
        await p.goto(BASE + "/", { waitUntil: "networkidle" });
        await p.waitForTimeout(2000);
        await p.evaluate(() => { const e = document.querySelector('[data-testid="v8-mobile-menu"]'); if (e) e.click(); });
        await p.waitForTimeout(900);
        await p.evaluate((k) => { const e = document.querySelector('[data-testid="v8-drawer-entry-' + k + '"]'); if (e) e.click(); }, key);
        await p.waitForTimeout(1500);
        const got = await p.evaluate(SNAP);
        for (const r of got) rows.push(Object.assign({ w: W, theme, screen: key }, r));
        const low = got.filter(r => r.worst_ratio < 4.5);
        const lowByColor = got.filter(r => r.ratio_color_only < 4.5);
        const blind = low.filter(r => r.ratio_color_only >= 4.5);
        console.log("w=" + W + " " + theme.padEnd(5) + " " + key.padEnd(14) + " 读数 " + String(got.length).padStart(4) +
          "｜只看底色低值 " + lowByColor.length + "｜算上渐变低值 " + low.length + "｜渐变才暴露的 " + blind.length);
        for (const r of blind.slice(0, 5)) {
          console.log("      " + String(r.worst_ratio).padEnd(5) + r.sel.slice(0, 30).padEnd(31) + (r.text || "").slice(0, 14).padEnd(15) +
            "底色只算=" + r.bg_color_only + " (" + r.ratio_color_only + ") → 渐变后=" + r.worst_bg + " 经 " + r.worst_via.slice(0, 56));
        }
        await p.close();
      }
    }
  }
  const low = rows.filter(r => r.worst_ratio < 4.5);
  const lowC = rows.filter(r => r.ratio_color_only < 4.5);
  const hub = rows.find(r => r.screen === "hub" && r.sel === "em" && (r.text || "").indexOf("•") === 0 && r.w === 1280 && r.theme === "light");
  const pill = rows.find(r => r.sel.indexOf("v8-status-pill.violet") >= 0 && r.theme === "light");
  const out = "grad_scan_" + KEYS.length + "keys_" + WIDTHS.join("_") + ".json";
  fs.writeFileSync(out, JSON.stringify({ at: new Date().toISOString(), widths: WIDTHS, themes: THEMES, keys: KEYS,
    loads: WIDTHS.length * THEMES.length * KEYS.length, readings: rows.length,
    low_color_only: lowC.length, low_with_gradient: low.length, blind_spots_exposed: low.filter(r => r.ratio_color_only >= 4.5).length,
    positive_control_em: hub ? { color_only: hub.ratio_color_only, with_grad: hub.worst_ratio } : null,
    positive_control_pill: pill ? { color_only: pill.ratio_color_only, with_grad: pill.worst_ratio, text: pill.text } : null,
    rows: rows }, null, 1));
  console.log("合计：读数 " + rows.length + "｜只看底色低值 " + lowC.length + "｜算渐变低值 " + low.length +
    "｜渐变新暴露 " + low.filter(r => r.ratio_color_only >= 4.5).length + "｜正控 em " + JSON.stringify(hub ? hub.worst_ratio : null) +
    " 药丸 " + JSON.stringify(pill ? pill.worst_ratio : null) + "｜落盘 " + out);
  await b.close();
})();
