/* 触摸目标普查：把出厂那把手机几何尺（frontend/e2e/_qoderMobileScan.ts）搬到"六屏 × 两档窄视口"上跑，
 * 判据一字不改（MIN_TOUCH_PX 44、控件清单 PRIMARY_CONTROL_SELECTOR、禁用态豁免都在尺里）。
 * 常驻门只在 1440 跑这一把，等于手机上没人量过拇指。
 *
 * 用法：node _cmdr_touch_census_r1.cjs <标签>
 */
const fs = require("fs");
const esbuild = require("D:/moodle/CityNexus/frontend/node_modules/esbuild");
const { chromium } = require("D:/moodle/CityNexus/frontend/node_modules/playwright/index.js");

const SRC = "D:/moodle/_cmdr_fe_rev_1016/tip/frontend/e2e/_qoderMobileScan.ts";
const SHIM = "D:/moodle/_cmdr_fe_rev_1016/_touch_shim_r1.cjs";
const LABEL = process.argv[2] || "run";
const BASE = "http://127.0.0.1:8121";

const js = esbuild.transformSync(fs.readFileSync(SRC, "utf8"), { loader: "ts", format: "cjs" }).code;
fs.writeFileSync(SHIM, js);
const mod = require(SHIM);
const SEL = mod.PRIMARY_CONTROL_SELECTOR;

const STEPS = [
  ["hub", null], ["live", '[data-testid="today-hero-cta"]'], ["copilot", '[data-testid="nav-agent"]'],
  ["trips", '[data-testid="nav-trips"]'], ["map", '[data-testid="nav-map"]'], ["me", '[data-testid="nav-me"]'],
];

(async () => {
  const b = await chromium.launch({ channel: "chrome", headless: true });
  const scenes = [];
  for (const W of [320, 390]) {
    for (const [screen, nav] of STEPS) {
      const p = await b.newPage({ viewport: { width: W, height: 780 }, hasTouch: true, isMobile: true });
      await p.addInitScript(() => {
        localStorage.setItem("citynexus.v8.journey_id", "22222222-2222-4222-8222-222222222222");
        localStorage.setItem("citynexus.theme", "light");
        localStorage.setItem("citynexus.locale", "zh-CN");
      });
      await p.goto(BASE + "/", { waitUntil: "networkidle" });
      await p.waitForTimeout(2200);
      if (nav) { await p.evaluate(s => { const e = document.querySelector(s); if (e) e.click(); }, nav); await p.waitForTimeout(1400); }
      const heading = await p.evaluate(() => ((document.querySelector(".v8-page h1, .v8-page-intro h1") || {}).innerText) || "");
      const g = await mod.probeMobileGeometry(p, { ctaCandidates: [".v8-primary", ".v8-primary-button", ".trial-sticky-cta button"], controlSelector: SEL, minTouchPx: 44 });
      const small = (g.smallTargets || []).map(t => ({ screen, w: W, selector: t.selector, testId: t.testId, text: t.text, h: t.height || (t.rect && t.rect.height), wd: t.width || (t.rect && t.rect.width) }));
      scenes.push({ screen, w: W, heading, small_count: small.length, rows: small, overflow: (g.overflow || g.overflowRows || []).length });
      console.log("w=" + W + " " + screen.padEnd(8) + " 标题=" + heading.slice(0, 18).padEnd(20)
        + " 小目标 " + small.length + " 枚｜溢出 " + scenes[scenes.length - 1].overflow + " 行");
      for (const s of small) console.log("     " + String(s.h).padStart(4) + "×" + String(s.wd).padEnd(4) + " " + (s.selector || "").slice(0, 42).padEnd(42) + " " + (s.text || "").slice(0, 18));
      await p.close();
    }
  }
  const all = [];
  for (const s of scenes) for (const r of s.rows) all.push(r);
  const byKey = {};
  for (const r of all) {
    const k = r.selector + "||" + r.testId + "||" + r.h + "x" + r.wd;
    byKey[k] = byKey[k] || { selector: r.selector, testId: r.testId, h: r.h, w: r.wd, text: r.text, where: [], n: 0 };
    byKey[k].n++; byKey[k].where.push(r.w + "/" + r.screen);
  }
  fs.writeFileSync("D:/moodle/_cmdr_fe_rev_1016/touch_census_" + LABEL + ".json",
    JSON.stringify({ label: LABEL, at: new Date().toISOString(), control_selector: SEL, min_touch_px: 44,
                     scenes: scenes.map(s => ({ screen: s.screen, w: s.w, heading: s.heading, small: s.small_count, overflow: s.overflow })),
                     readings: all.length, distinct: Object.values(byKey).length, kinds: Object.values(byKey) }, null, 1), "utf-8");
  console.log("累计小目标读数 " + all.length + " 条，去重 " + Object.values(byKey).length + " 种｜收据 touch_census_" + LABEL + ".json");
  await b.close();
})().catch(e => { console.log("FATAL " + e); process.exit(1); });
