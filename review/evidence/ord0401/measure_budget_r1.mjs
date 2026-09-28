/**
 * ORD-0401 -- what does the first screen actually leave available?
 *
 * A control is only "in the first screen" if its centre can be hit there: `elementFromPoint` must
 * return the control itself, not the fold, and not a fixed bar drawn over it. This reads every
 * fixed/sticky element that covers the viewport bottom at each width, plus the real panel's own
 * anchor geometry, so the budget is a measured rectangle rather than `innerHeight`.
 */
import { chromium } from "playwright";
import { mkdirSync, writeFileSync } from "node:fs";

const BASE = process.env.ORD0401_BASE ?? "http://127.0.0.1:4781";
const OUT = process.env.ORD0401_OUT ?? "D:/moodle/_qoder_q_ord0401_evidence";
mkdirSync(OUT, { recursive: true });
const WIDTHS = (process.env.ORD0401_WIDTHS ?? "320,360,390,414").split(",").map(Number);

const SCAN = () => {
  const vp = { w: window.innerWidth, h: window.innerHeight };
  const covering = [];
  for (const el of document.querySelectorAll("*")) {
    const cs = getComputedStyle(el);
    if (!["fixed", "sticky"].includes(cs.position)) continue;
    const r = el.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) continue;
    covering.push({
      tag: el.tagName.toLowerCase(),
      class: (typeof el.className === "string" ? el.className : "").slice(0, 60),
      testid: el.getAttribute("data-testid"),
      position: cs.position,
      y: Math.round(r.y),
      bottom: Math.round(r.bottom),
      h: Math.round(r.height),
      w: Math.round(r.width),
      touches_viewport_bottom: r.bottom >= vp.h - 1 && r.y < vp.h,
    });
  }
  const yOf = (sel) => {
    const el = document.querySelector(sel);
    return el ? Math.round(el.getBoundingClientRect().top + window.scrollY) : null;
  };
  const strip = document.querySelector('[data-testid="today-strip"]');
  const panel = document.querySelector('[data-testid="pretrip-checklist"]');
  /* Hit-test the fold's own last un-covered line: where may a control's centre actually land? */
  const barsAtBottom = covering
    .filter((c) => c.position === "fixed" && c.touches_viewport_bottom)
    .map((c) => c.y);
  const highestBottomBar = barsAtBottom.length ? Math.min(...barsAtBottom) : null;
  const probe = (y) => {
    const el = document.elementFromPoint(Math.round(vp.w / 2), y);
    return el ? `${el.tagName.toLowerCase()}.${(typeof el.className === "string" ? el.className : "").slice(0, 40)}` : "null";
  };
  return {
    viewport: vp,
    covering_fixed_or_sticky: covering,
    usable_first_screen_bottom: highestBottomBar === null ? vp.h : highestBottomBar,
    hit_at_840: probe(840),
    hit_at_820: probe(820),
    hit_at_780: probe(780),
    hit_at_700: probe(700),
    anchors: {
      today_strip_top: yOf('[data-testid="today-strip"]'),
      band_top: yOf('[data-testid="today-attention-band"]'),
      panel_top: yOf('[data-testid="pretrip-checklist"]'),
      panel_h: panel ? Math.round(panel.getBoundingClientRect().height) : null,
      doc_height: document.scrollingElement.scrollHeight,
    },
  };
};

const browser = await chromium.launch();
const report = { base: BASE, arms: [] };
for (const width of WIDTHS) {
  const ctx = await browser.newContext({ viewport: { width, height: 844 } });
  const page = await ctx.newPage();
  await page.addInitScript((v) => localStorage.setItem("citynexus.locale", v), "zh-CN");
  await page.route((url) => url.pathname.startsWith("/api/"), async (route) =>
    route.request().method() === "GET" ? route.continue() : route.fulfill({ status: 405, body: "{}" }),
  );
  await page.goto(`${BASE}/v8`, { waitUntil: "load" });
  await page.waitForTimeout(1200);
  const demo = page.getByTestId("trial-tianjin-demo");
  if (await demo.count()) {
    await demo.click();
    await page.waitForFunction(() => !!localStorage.getItem("citynexus.v8.journey_id"), null, { timeout: 30_000 }).catch(() => {});
  }
  await page.goto(`${BASE}/v8/hub`, { waitUntil: "load" });
  await page.waitForTimeout(2200);
  const s = await page.evaluate(SCAN);
  report.arms.push({ width, ...s });
  console.log(
    `\n=== ${width}x844 === usable_bottom=${s.usable_first_screen_bottom} anchors=${JSON.stringify(s.anchors)}`,
  );
  for (const c of s.covering_fixed_or_sticky) {
    console.log(`  ${c.position.padEnd(7)} y=${String(c.y).padStart(4)}..${String(c.bottom).padEnd(4)} h=${String(c.h).padStart(3)} ${c.testid ?? c.class.slice(0, 40)}`);
  }
  console.log(`  hit@700=${s.hit_at_700} hit@780=${s.hit_at_780} hit@820=${s.hit_at_820} hit@840=${s.hit_at_840}`);
  await ctx.close();
}
await browser.close();
writeFileSync(`${OUT}/first_screen_budget_r1.json`, JSON.stringify(report, null, 2));
