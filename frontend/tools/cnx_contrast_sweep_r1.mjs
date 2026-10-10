#!/usr/bin/env node
/* cnx_contrast_sweep_r1 — 逐节点量「文字颜色 vs 它实际落在的不透明背景」，覆盖公共对比度尺走不到的屏。
 *
 * 为什么要有它：公共尺 qoder-contrast-audit 只显式审计两枚屏，其余导航屏从未被量过。
 * 本仪表自带一道自校闸门：先用文档记录的已知比值校准算法，对不上就 ABORT 不出数。
 *
 * 用法（需要一枚本车道自己的后端与 dev server）：
 *   node frontend/tools/cnx_contrast_sweep_r1.mjs \
 *     --base http://localhost:5233/ --api http://127.0.0.1:8125 \
 *     --routes v8/hub,v8/live,v8/stay --viewports desktop,mobile --out sweep.json
 */
import { chromium } from "playwright";
import { writeFileSync } from "node:fs";

const argv = process.argv.slice(2);
const opt = (name, dflt) => {
  const i = argv.indexOf("--" + name);
  return i >= 0 && argv[i + 1] !== undefined ? argv[i + 1] : dflt;
};

const BASE = opt("base", "http://localhost:5233/");
const API = opt("api", "http://127.0.0.1:8125");
const ROUTES = opt("routes", "v8/hub,v8/live,v8/stay,v8/studio,v8/map,v8/discover,v8/plan-ranking,v8/pending-set,v8/collections,v8/import,v8/footprints,v8/trips-workspace").split(",");
const VIEWPORTS = { desktop: { width: 1280, height: 900 }, mobile: { width: 390, height: 844 } };
const VIEWS = opt("viewports", "desktop,mobile").split(",");
const THEMES = opt("themes", "light,dark").split(",");
const OUT = opt("out", "contrast-sweep.json");

const srgb = (c) => { const v = c / 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
const lum = (r, g, b) => 0.2126 * srgb(r) + 0.7152 * srgb(g) + 0.0722 * srgb(b);
const hex = (s) => [parseInt(s.slice(1, 3), 16), parseInt(s.slice(3, 5), 16), parseInt(s.slice(5, 7), 16)];
const ratioOf = (a, b) => { const L1 = lum(...a), L2 = lum(...b); const hi = Math.max(L1, L2), lo = Math.min(L1, L2); return (hi + 0.05) / (lo + 0.05); };

// Self-calibration gate: design-tokens.css records #0a5cd6 on the #f5f5f7 canvas as 5.49:1.
const CAL = { fg: "#0a5cd6", bg: "#f5f5f7", expected: 5.49, tolerance: 0.02 };
const cal = ratioOf(hex(CAL.fg), hex(CAL.bg));
if (Math.abs(cal - CAL.expected) > CAL.tolerance) {
  console.error(`ABORT instrument out of calibration: ${CAL.fg} on ${CAL.bg} measured ${cal.toFixed(2)}, documented ${CAL.expected}. Refusing to emit numbers.`);
  process.exit(3);
}
console.log(`calibrated: ${CAL.fg} on ${CAL.bg} = ${cal.toFixed(2)} (documented ${CAL.expected})`);

const SWEEP = `((cal) => {
  const srgb = (c) => { const v = c / 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
  const lum = (r, g, b) => 0.2126 * srgb(r) + 0.7152 * srgb(g) + 0.0722 * srgb(b);
  const toRgb = (s) => { const m = /rgba?\\(([^)]+)\\)/.exec(s || ''); if (!m) return null; const p = m[1].split(',').map((x) => parseFloat(x)); return { r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1 }; };
  const bgOf = (el) => { let n = el; while (n && n !== document.documentElement) { const c = toRgb(getComputedStyle(n).backgroundColor); if (c && c.a > 0.85) return c; n = n.parentElement; } return { r: 255, g: 255, b: 255, a: 1 }; };
  const bad = [];
  let scanned = 0;
  for (const el of document.querySelectorAll('*')) {
    let hasText = false;
    for (const node of el.childNodes) { if (node.nodeType === 3 && node.textContent.trim()) { hasText = true; break; } }
    if (!hasText) continue;
    const box = el.getBoundingClientRect();
    if (box.width < 1 || box.height < 1) continue;
    const cs = getComputedStyle(el);
    const fg = toRgb(cs.color);
    if (!fg) continue;
    const bg = bgOf(el);
    const L1 = lum(fg.r, fg.g, fg.b), L2 = lum(bg.r, bg.g, bg.b);
    const hi = Math.max(L1, L2), lo = Math.min(L1, L2);
    const r = (hi + 0.05) / (lo + 0.05);
    if (!Number.isFinite(r)) continue;
    scanned++;
    const px = parseFloat(cs.fontSize);
    const bold = parseInt(cs.fontWeight, 10) >= 700;
    const need = (px >= 24 || (px >= 18.66 && bold)) ? 3 : 4.5;
    if (r >= need) continue;
    bad.push({ tag: el.tagName.toLowerCase(), cls: String(el.className || '').split(/\\s+/).filter(Boolean).slice(0, 2).join('.'), testid: el.getAttribute('data-testid') || '', text: el.textContent.trim().replace(/\\s+/g, ' ').slice(0, 24), color: cs.color, bg: 'rgb(' + Math.round(bg.r) + ',' + Math.round(bg.g) + ',' + Math.round(bg.b) + ')', size: px, weight: cs.fontWeight, ratio: Math.round(r * 100) / 100, need });
  }
  const seen = new Set();
  return { url: location.href, theme: document.documentElement.getAttribute('data-theme') || '(light-default)', scanned, bad: bad.filter((b) => { const k = b.tag + b.cls + b.color + b.bg + b.text; if (seen.has(k)) return false; seen.add(k); return true; }) };
})`;

const call = async (p, i) => { const r = await fetch(new URL(p, API), i); const t = await r.text(); if (!r.ok) throw new Error(p + " http_status=" + r.status); return t ? JSON.parse(t) : {}; };

const seedJourney = async () => {
  const t = await call("/api/v1/travelers", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ display_name: "Contrast sweep traveller", locale: "en-GB", timezone: "Asia/Shanghai" }) });
  const j = await call("/api/v1/journeys", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ traveler_id: t.id, title: "Contrast sweep trip", city_code: "CN-TIANJIN", timezone: "Asia/Shanghai", start_at: "2026-10-09T18:00:00+08:00", end_at: "2026-10-11T15:00:00+08:00", budget: { amount_minor: 120000, currency: "CNY" } }) });
  await call(`/api/v1/journeys/${j.id}/stay-options/generate`, { method: "POST" });
  return j.id;
};

const browser = await chromium.launch();
const journey = await seedJourney().catch((e) => { console.error("seed failed: " + e.message); return null; });
const report = { base: BASE, journey, calibrated: { ...CAL, measured: Number(cal.toFixed(2)) }, screens: {} };
const controls = new Map();

for (const view of VIEWS) {
  for (const theme of THEMES) {
    const ctx = await browser.newContext({ viewport: VIEWPORTS[view], colorScheme: theme });
    if (journey) await ctx.addInitScript((id) => { localStorage.setItem("citynexus.v8.journey_id", id); localStorage.setItem("citynexus.demo.journey_id", id); }, journey);
    const page = await ctx.newPage();
    for (const route of ROUTES) {
      await page.goto(BASE + route, { waitUntil: "networkidle", timeout: 45000 }).catch(() => {});
      await page.waitForTimeout(2000);
      await page.evaluate(() => { document.querySelectorAll("details:not([open])").forEach((d) => d.setAttribute("open", "")); });
      const r = await page.evaluate(`${SWEEP}(${JSON.stringify(CAL)})`);
      report.screens[`${view}|${theme}|${route}`] = r;
      for (const b of r.bad) {
        const k = `${b.tag}.${b.cls}|${b.color}|${b.bg}`;
        const cur = controls.get(k);
        if (!cur || b.ratio < cur.ratio) controls.set(k, { ...b, view, theme, route });
      }
    }
    await ctx.close();
  }
}
report.distinct = { screens_with_findings: Object.values(report.screens).filter((s) => s.bad.length).length, screens_scanned: Object.keys(report.screens).length, distinct_controls: controls.size, worst: Math.min(...[...controls.values()].map((c) => c.ratio)) };
writeFileSync(OUT, JSON.stringify(report, null, 1));
console.log(`screens_scanned=${report.distinct.screens_scanned} screens_with_findings=${report.distinct.screens_with_findings} distinct_controls=${report.distinct.distinct_controls} worst=${report.distinct.worst}`);
for (const c of [...controls.values()].sort((a, b) => a.ratio - b.ratio).slice(0, 14)) {
  console.log(`  ${String(c.ratio).padEnd(5)}/${c.need} ${c.view}/${c.theme} ${c.route}  ${c.tag}.${c.cls.slice(0, 24)} "${c.text.slice(0, 14)}" ${c.color} on ${c.bg} ${c.size}px/${c.weight}`);
}
await browser.close();
