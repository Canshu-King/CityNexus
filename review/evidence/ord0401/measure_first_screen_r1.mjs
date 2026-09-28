/**
 * ORD-0401 -- the real rectangle a first-screen control may occupy on Today.
 *
 * `innerHeight` is not the fold here: the bottom tab bar and two floating pills are `position:fixed`,
 * so a control can sit inside the viewport and still be un-clickable. This walks the blocks that are
 * above the fold, and hit-tests a grid, so "first screen" becomes a measured rectangle.
 */
import { chromium } from "playwright";
import { mkdirSync, writeFileSync } from "node:fs";

const BASE = process.env.ORD0401_BASE ?? "http://127.0.0.1:4781";
const OUT = process.env.ORD0401_OUT ?? "D:/moodle/_qoder_q_ord0401_evidence";
mkdirSync(OUT, { recursive: true });

const SCAN = () => {
  const vp = { w: window.innerWidth, h: window.innerHeight };
  const overlays = [...document.querySelectorAll("*")]
    .filter((el) => ["fixed", "sticky"].includes(getComputedStyle(el).position))
    .map((el) => {
      const r = el.getBoundingClientRect();
      return {
        testid: el.getAttribute("data-testid"),
        class: (typeof el.className === "string" ? el.className : "").slice(0, 50),
        position: getComputedStyle(el).position,
        x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height),
      };
    })
    .filter((o) => o.w > 0 && o.h > 0 && o.y < vp.h && o.y + o.h > 0);

  const blocks = [...document.querySelectorAll(".v8-page > *, .v8-hero-grid > *, .v8-hero > *, .cn-hero-strip > *")]
    .map((el) => {
      const r = el.getBoundingClientRect();
      return {
        tag: el.tagName.toLowerCase(),
        class: (typeof el.className === "string" ? el.className : "").slice(0, 46),
        testid: el.getAttribute("data-testid"),
        y: Math.round(r.y + window.scrollY),
        h: Math.round(r.height),
        text: (el.innerText || "").replace(/\s+/g, " ").trim().slice(0, 40),
      };
    })
    .filter((b) => b.h > 0 && b.y < 900);

  // Hit-test the button column (where a quiet row's action actually lands, x ~ 31..150) at each y.
  const probes = [];
  for (let y = 300; y <= 840; y += 20) {
    for (const x of [60, 200, 340]) {
      const el = document.elementFromPoint(x, y);
      const who = el
        ? `${el.tagName.toLowerCase()}:${(el.getAttribute("data-testid") || (typeof el.className === "string" ? el.className.split(" ")[0] : "")).slice(0, 26)}`
        : "null";
      probes.push({ x, y, who });
    }
  }
  const firstBlocked = (x) => {
    const row = probes.filter((p) => p.x === x);
    const hit = row.find((p) => /v8-mobile-nav|copilot-dock|sim-float/.test(p.who));
    return hit ? hit.y : null;
  };
  return {
    viewport: vp,
    overlays,
    blocks_above_fold: blocks,
    blocked_from: { x60: firstBlocked(60), x200: firstBlocked(200), x340: firstBlocked(340) },
    grid: probes,
  };
};

const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 390, height: 844 } });
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
await page.screenshot({ path: `${OUT}/hub-390-first-screen.png` });
writeFileSync(`${OUT}/first_screen_rect_r1.json`, JSON.stringify(s, null, 2));
console.log("overlays:");
for (const o of s.overlays) console.log(`  ${o.position.padEnd(7)} x=${o.x} y=${o.y} w=${o.w} h=${o.h} ${o.testid ?? o.class}`);
console.log("\nblocks:");
for (const b of s.blocks_above_fold) console.log(`  y=${String(b.y).padStart(4)} h=${String(b.h).padStart(4)} ${b.tag}.${b.class.slice(0, 34)} ${b.testid ?? ""} | ${b.text.slice(0, 26)}`);
console.log("\nblocked_from:", JSON.stringify(s.blocked_from));
console.log("grid y=640..800:", JSON.stringify(s.grid.filter((g) => g.y >= 640 && g.y <= 800 && g.x === 60)));
await browser.close();
