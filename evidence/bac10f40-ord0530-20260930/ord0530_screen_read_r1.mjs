/**
 * ORD-0530 -- read the footprint screen the way a traveller sees it, and write down what is painted.
 *
 * This is the before/after instrument for the day-grouping change. It reads `innerText` of the rows
 * (never a `data-*` attribute), takes a centre hit with `document.elementFromPoint` only after
 * scrolling the row into the viewport, and runs at two shapes: the phone 390x844 and a desktop
 * 1280x900. The browser context is deliberately pinned to a timezone that is NOT the journey's
 * (America/Los_Angeles against a journey whose server timezone is Asia/Shanghai), because the whole
 * point of the order is that the day a stamp belongs to comes from the server's moment plus the
 * journey's own timezone -- and a grouping that quietly used the device's zone would only be visible
 * as a wrong date when the two disagree.
 *
 * Usage:  node ord0530_screen_read_r1.py --out <dir> --tag <label>
 *   (it is a .mjs driver kept beside the order's evidence; nothing here starts a server)
 */
import { chromium } from "playwright";
import { mkdirSync, writeFileSync } from "node:fs";

const BASE = "http://127.0.0.1:4795";
const JOURNEY = "22222222-2222-4222-8222-222222222222";
const args = process.argv.slice(2);
const outDir = args[args.indexOf("--out") + 1];
const tag = args[args.indexOf("--tag") + 1];
mkdirSync(outDir, { recursive: true });

const SHAPES = [
  { name: "phone_390x844", width: 390, height: 844 },
  { name: "desktop_1280x900", width: 1280, height: 900 },
];

const browser = await chromium.launch();
const report = { base: BASE, journey: JOURNEY, tag, browser_timezone: "America/Los_Angeles", shapes: [] };

for (const shape of SHAPES) {
  const context = await browser.newContext({
    viewport: { width: shape.width, height: shape.height },
    locale: "zh-CN",
    timezoneId: "America/Los_Angeles",
  });
  const page = await context.newPage();
  await page.addInitScript((journey) => {
    localStorage.setItem("citynexus.v8.journey_id", journey);
    localStorage.setItem("citynexus.locale", "zh-CN");
  }, JOURNEY);
  await page.goto(`${BASE}/v8/footprints`, { waitUntil: "load", timeout: 60000 });
  await page.waitForSelector("[data-testid='footprint-panel']", { timeout: 30000 });
  await page.waitForTimeout(2500);

  const read = await page.evaluate(() => {
    const panel = document.querySelector("[data-testid='footprint-panel']");
    const text = (el) => (el?.innerText ?? "").replace(/\s+/g, " ").trim();
    const rows = Array.from(document.querySelectorAll("[data-testid='footprint-row']"));
    const days = Array.from(document.querySelectorAll("[data-testid='footprint-day']"));
    const probe = (el) => {
      el.scrollIntoView({ block: "center" });
      const r = el.getBoundingClientRect();
      const cx = Math.round(r.x + r.width / 2);
      const cy = Math.round(r.y + r.height / 2);
      const at = document.elementFromPoint(cx, cy);
      return {
        box: { x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height) },
        centre: { x: cx, y: cy },
        in_viewport: r.top >= 0 && r.bottom <= window.innerHeight,
        hit: at ? at.tagName.toLowerCase() + "." + String(at.className || "").slice(0, 24) : "none",
        hit_is_self: !!(at && (at === el || el.contains(at))),
      };
    };
    const machine = text(panel).match(/\b[A-Z][A-Z0-9_]{4,}\b/g) ?? [];
    const uuids = text(panel).match(/\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b/g) ?? [];
    return {
      panel_text: text(panel),
      tally: text(document.querySelector("[data-testid='footprint-tally']")),
      state_line: text(document.querySelector("[data-testid='footprint-empty']")) ||
        text(document.querySelector("[data-testid='footprint-failed']")) ||
        text(document.querySelector("[data-testid='footprint-no-journey']")),
      day_rows: days.map((el) => ({ text: text(el), probe: probe(el) })),
      stamp_rows: rows.map((el) => ({
        cells: Array.from(el.querySelectorAll("span,b,i,em")).map((cell) => text(cell)).filter(Boolean),
        text: text(el),
        probe: probe(el),
      })),
      screaming_snake_count: machine.length,
      screaming_snake_tokens: machine.slice(0, 6),
      uuid_count: uuids.length,
      uuid_tokens: uuids.slice(0, 4),
    };
  });
  await page.screenshot({ path: `${outDir}/footprints_${tag}_${shape.name}.png`, fullPage: true });
  report.shapes.push({ shape, read });
  await context.close();
}
await browser.close();

writeFileSync(`${outDir}/footprints_${tag}.json`, JSON.stringify(report, null, 1), "utf8");
console.log("shapes", report.shapes.length, "out", `${outDir}/footprints_${tag}.json`);
for (const s of report.shapes) {
  console.log(
    " ",
    s.shape.name,
    "days",
    s.read.day_rows.length,
    "rows",
    s.read.stamp_rows.length,
    "snake",
    s.read.screaming_snake_count,
    "uuid",
    s.read.uuid_count,
  );
}
