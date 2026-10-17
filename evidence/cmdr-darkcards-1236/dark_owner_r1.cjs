/* 我自己复算子 Agent 的那批暗档读数，并把"谁是那块白底的持有者"打出来 ——
 * 因为要修就得改容器，不是改文字。沿祖先链合成（带 alpha 的层逐层压），
 * 记录第一层不透明底色属于哪个 tag.class。暗档 1280。只读。
 * 用法：node _cmdr_dark_owner_r1.cjs [key,逗号] [阈值]
 */
const { chromium } = require("D:/moodle/CityNexus/frontend/node_modules/playwright/index.js");
const fs = require("fs");

const BASE = "http://127.0.0.1:8121";
const KEYS = (process.argv[2] ? process.argv[2].split(",") : ["authoritative", "studio", "twin"]);
const THRESH = Number(process.argv[3] || 4.5);

const SNAP = `(() => {
  const srgb = (c) => { c = c / 255.0; return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); };
  const lum = (t) => 0.2126 * srgb(t[0]) + 0.7152 * srgb(t[1]) + 0.0722 * srgb(t[2]);
  const parse = (rgb) => { const m = /rgba?\\(([^)]+)\\)/.exec(rgb || ""); if (!m) return null;
    const p = m[1].split(",").map(x => Number(x.trim())); return { t: [p[0], p[1], p[2]], a: p.length === 4 ? p[3] : 1 }; };
  const name = (el) => el.tagName.toLowerCase() + (typeof el.className === "string" && el.className
    ? "." + el.className.trim().split(/\\s+/).slice(0, 3).join(".") : "");
  const ratio = (a, b) => { const x = lum(a), y = lum(b); return Math.round(((Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05)) * 100) / 100; };
  const out = [];
  for (const el of Array.from(document.querySelectorAll("body *"))) {
    if (!el.checkVisibility({ checkOpacity: true, checkVisibilityCSS: true })) continue;
    const own = Array.from(el.childNodes).filter(n => n.nodeType === 3).map(n => n.textContent).join("").trim();
    if (!own) continue;
    const r = el.getBoundingClientRect();
    if (r.width < 1 || r.height < 1) continue;
    const fg = parse(getComputedStyle(el).color); if (!fg || fg.a < 1) continue;
    let anc = el, hops = 0, owner = null; const layers = [];
    while (anc && hops < 14) {
      const m = parse(getComputedStyle(anc).backgroundColor);
      if (m && m.a > 0) {
        layers.push({ n: name(anc), t: m.t, a: m.a });
        if (m.a >= 1) { owner = { n: name(anc), tid: anc.getAttribute("data-testid") || "", t: m.t }; break; }
      }
      anc = anc.parentElement; hops++;
    }
    if (!owner) continue;
    let cur = owner.t.slice();
    for (let i = layers.length - 2; i >= 0; i--) { const l = layers[i]; cur = [0, 1, 2].map(k => l.a * l.t[k] + (1 - l.a) * cur[k]); }
    const rr = ratio(fg.t, cur);
    if (rr >= ${THRESH}) continue;
    out.push({ sel: name(el), tid: el.getAttribute("data-testid") || "", text: own.slice(0, 24),
      color: getComputedStyle(el).color, fs: getComputedStyle(el).fontSize, owner: owner.n, owner_rgb: owner.t.join(","),
      owner_tid: owner.tid, bg: cur.map(x => Math.round(x)).join(","), ratio: rr,
      chain: layers.map(l => l.n + "@" + l.a.toFixed(2)).join(" < "), hops });
  }
  return out;
})()`;

(async () => {
  const b = await chromium.launch({ channel: "chrome", headless: true });
  const all = [];
  for (const key of KEYS) {
    const p = await b.newPage({ viewport: { width: 1280, height: 900 } });
    await p.addInitScript(() => {
      localStorage.setItem("citynexus.v8.journey_id", "22222222-2222-4222-8222-222222222222");
      localStorage.setItem("citynexus.theme", "dark");
      localStorage.setItem("citynexus.locale", "zh-CN");
    });
    await p.goto(BASE + "/", { waitUntil: "networkidle" });
    await p.waitForTimeout(2100);
    await p.evaluate(() => { const e = document.querySelector('[data-testid="v8-mobile-menu"]'); if (e) e.click(); });
    await p.waitForTimeout(900);
    await p.evaluate((k) => { const e = document.querySelector('[data-testid="v8-drawer-entry-' + k + '"]'); if (e) e.click(); }, key);
    await p.waitForTimeout(1500);
    /* 滚到底，把折叠以下的也拉到视口里再量：第一版对拍尺的盲区就在这 */
    for (let i = 0; i < 6; i++) {
      await p.evaluate(() => window.scrollBy(0, 700));
      await p.waitForTimeout(220);
    }
    await p.evaluate(() => window.scrollTo(0, 0));
    await p.waitForTimeout(400);
    const rows = await p.evaluate(SNAP);
    const byOwner = {};
    for (const r of rows) byOwner[r.owner] = (byOwner[r.owner] || 0) + 1;
    console.log("=== " + key + " 暗档 1280｜低于 " + THRESH + " 的读数 " + rows.length + " 条");
    for (const [o, n] of Object.entries(byOwner).sort((a, b) => b[1] - a[1])) console.log("   持有白底的容器 " + o + " ：" + n + " 条");
    for (const r of rows.slice(0, 14)) {
      console.log("   " + String(r.ratio).padEnd(5) + r.sel.padEnd(34) + (r.text || "").slice(0, 14).padEnd(15) +
        " 底=" + r.bg + " 于 " + r.owner + " 链深 " + r.hops);
    }
    all.push({ key, rows });
    await p.close();
  }
  fs.writeFileSync("dark_owner_" + KEYS.join("_") + ".json", JSON.stringify(all, null, 2));
  await b.close();
})();
