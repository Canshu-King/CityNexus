/**
 * ORD-0530 reach -- can a traveller on a narrow screen actually hit the footprint screen's own controls?
 *
 * The delivered readings for this screen prove what it SAYS (rows, days, tally, source word) and that
 * a row's centre hit lands on the row itself once scrolled.  What was never measured is the two things
 * a thumb has to reach: the `重读一次` / `Read again` button, and the LAST stamp row, which sits lowest
 * on the glass.  On a phone the shell paints a fixed bottom bar, and `ORD-0537` measured that the map
 * screen's switch is outside the viewport until you scroll -- so the same question is open here.
 *
 * Two states are measured per target, because the order's own judge is about a state, not a pixel:
 *   parked   -- whatever the shell's scroll position is when the screen loads, hit-tested as-is
 *   lifted   -- the target scrolled to the middle of the viewport, then hit-tested
 * A target is reachable if some scroll position puts its centre on itself, and is not eaten by the bar.
 * Touch-target size is read as rendered height, not from CSS.
 */
import { chromium } from "playwright";
import { mkdirSync, writeFileSync } from "node:fs";

const BASE = process.env.ORD0530_BASE;
if (!BASE) throw new Error("ORD0530_BASE is required");
const JOURNEY = process.env.ORD0530_JOURNEY || "22222222-2222-4222-8222-222222222222";
const args = process.argv.slice(2);
const outDir = args[args.indexOf("--out") + 1];
const tag = args[args.indexOf("--tag") + 1];
mkdirSync(outDir, { recursive: true });

const SHAPES = [
  { name: "phone_390x844", width: 390, height: 844, note: "the narrow档 the order asks about" },
  { name: "desktop_1280x900", width: 1280, height: 900, note: "control: no mobile bottom bar here" },
];
const browser = await chromium.launch();
const report = { base: BASE, journey: JOURNEY, tag, browser_locale: "zh-CN",
                 timezone: "America/Los_Angeles", shapes: [] };

for (const shape of SHAPES) {
  const context = await browser.newContext({ viewport: { width: shape.width, height: shape.height },
                                            locale: "zh-CN", timezoneId: "America/Los_Angeles" });
  const page = await context.newPage();
  await page.addInitScript((o) => {
    localStorage.setItem("citynexus.v8.journey_id", o.journey);
    localStorage.setItem("citynexus.locale", "zh-CN");
  }, { journey: JOURNEY });
  await page.goto(`${BASE}/v8/footprints`, { waitUntil: "load", timeout: 60000 });
  await page.waitForSelector("[data-testid='footprint-panel']", { timeout: 30000 });
  await page.waitForTimeout(2500);

  const measure = async (doScroll) => page.evaluate((wantScroll) => {
    const box = (el) => {
      const r = el.getBoundingClientRect();
      return { x: Math.round(r.x), y: Math.round(r.y), top: Math.round(r.top),
               right: Math.round(r.right), bottom: Math.round(r.bottom),
               w: Math.round(r.width), h: Math.round(r.height) };
    };
    const centre = (b) => ({ x: Math.round(b.x + b.w / 2), y: Math.round(b.y + b.h / 2) });
    const probe = (el, label) => {
      if (wantScroll) el.scrollIntoView({ block: "center" });
      const b = box(el);
      const c = centre(b);
      const hit = document.elementFromPoint(c.x, c.y);
      const nav = document.querySelector(".v8-mobile-nav");
      const nb = nav ? box(nav) : null;
      return { label, box: b, centre: c,
               in_viewport: b.top >= 0 && b.bottom <= window.innerHeight,
               hit_tag: hit ? (hit.tagName.toLowerCase() + "." + String(hit.className)) : "none",
               hit_is_self: !!hit && (hit === el || el.contains(hit) || (hit.parentElement === el)),
               hit_is_nav: !!hit && !!nb && (hit === nav || nav.contains(hit)),
               centre_below_nav_floor: nb ? c.y >= nb.top : null };
    };
    const panel = document.querySelector("[data-testid='footprint-panel']");
    const retry = document.querySelector("[data-testid='footprint-retry']");
    const rows = Array.from(document.querySelectorAll("[data-testid='footprint-row']"));
    const nav = document.querySelector(".v8-mobile-nav");
    const out = { scroll_y: Math.round(window.scrollY ?? document.scrollingElement?.scrollTop ?? 0),
                  inner_height: window.innerHeight,
                  nav_present: !!nav,
                  nav_box: nav ? box(nav) : null,
                  panel_box: box(panel) };
    out.targets = [];
    if (retry) out.targets.push(probe(retry, "retry_button"));
    if (rows.length) out.targets.push(probe(rows[rows.length - 1], "last_stamp_row"));
    out.retry_min_height = retry ? Math.round(parseFloat(getComputedStyle(retry).minHeight || "0")) : null;
    out.retry_word = retry ? retry.innerText.replace(/\s+/g, " ").trim() : null;
    return out;
  }, doScroll);

  const parked = await measure(false);
  await page.screenshot({ path: `${outDir}/footprints_${tag}_parked_${shape.name}.png` });
  const lifted = await measure(true);
  await page.screenshot({ path: `${outDir}/footprints_${tag}_lifted_${shape.name}.png` });

  const verdict = {};
  for (let i = 0; i < lifted.targets.length; i += 1) {
    const p = parked.targets[i], l = lifted.targets[i];
    verdict[p.label] = {
      parked_in_viewport: p.in_viewport, parked_hit: p.hit_tag, parked_hit_is_self: p.hit_is_self,
      parked_hit_is_nav: p.hit_is_nav, parked_centre: p.centre,
      lifted_in_viewport: l.in_viewport, lifted_hit: l.hit_tag, lifted_hit_is_self: l.hit_is_self,
      lifted_hit_is_nav: l.hit_is_nav, lifted_centre: l.centre,
      reachable_by_some_scroll: l.in_viewport && l.hit_is_self && !l.hit_is_nav,
    };
  }
  report.shapes.push({ shape, parked, lifted, verdict,
                       target_count: lifted.targets.length,
                       retry_word: lifted.retry_word, retry_min_height: lifted.retry_min_height });
  await context.close();
}
await browser.close();

report.all_reachable = report.shapes.every((s) => s.shape.name === "desktop_1280x900"
  || Object.values(s.verdict).every((v) => v.reachable_by_some_scroll));
writeFileSync(`${outDir}/footprints_${tag}.json`, JSON.stringify(report, null, 1), "utf8");
console.log("shapes", report.shapes.length, "all_reachable(phone)", report.all_reachable);
for (const s of report.shapes) {
  console.log(" ", s.shape.name, "nav", s.parked.nav_present, "targets", s.target_count,
              "retry_word", JSON.stringify(s.retry_word), "retry_min_height", s.retry_min_height);
  for (const [k, v] of Object.entries(s.verdict)) {
    console.log(`    ${k}: parked_in_viewport=${v.parked_in_viewport} parked_hit_is_self=${v.parked_hit_is_self} parked_hit_is_nav=${v.parked_hit_is_nav} lifted_hit_is_self=${v.lifted_hit_is_self} reachable=${v.reachable_by_some_scroll}`);
  }
}
console.log("out", `${outDir}/footprints_${tag}.json`);
