/* CMDR text-collision ruler r1 - find pairs of visible text whose boxes actually overlap.
 *
 * Why: I saw it in my own screenshot first. On /v8/map at 390x844 the basemap-failure banner ("Basemap did
 * not load - showing the route diagram only.") sits in the same band as the "Fit to my journey" control, and
 * a map label is drawn under one of them.  Everything I have measured so far about layout has been about
 * SIZE (overflow height, oversized svg, an icon with no dimension) - never about two pieces of copy
 * occupying the same pixels.  A size ruler cannot see a collision, and a collision is the layout defect a
 * user notices fastest: the sentence becomes unreadable.
 *
 * What counts as a collision, and what deliberately does not:
 *   - both elements must be LEAF text (no child elements) and actually painted (non-zero box, opacity 1);
 *   - their client rects must intersect by at least MIN_OVERLAP px on BOTH axes, so a 1 px anti-alias
 *     touching edge is not reported;
 *   - an ancestor/descendant pair is skipped (a wrapper's box always contains its child's);
 *   - a control painted ON TOP of the map canvas is legitimate - the canvas is not text, so it never enters
 *     the candidate set (we only take elements with a text leaf);
 *   - pairs inside the same button (icon + label) are skipped when one box is contained in the other AND
 *     they share a parent - that is normal inline layout, not a collision.
 *
 * Usage: node _text_collision_r1.js <base> <out-dir> [locale=zh] [routes-csv]
 */
const { chromium } = require("D:/moodle/CityNexus/frontend/node_modules/playwright");
const fs = require("fs");
const BASE = process.argv[2] || "http://127.0.0.1:4805";
const OUT = process.argv[3] || "D:/moodle/_qoder_cmdr_ref_20260921/live_checks/_text_collision_r1/";
const LOCALE = process.argv[4] || "zh";
const ROUTES = (process.argv[5] || "hub,live,map,studio,stay,discover,bookings,agent,authoritative,intelligence,twin,trips,me,trash").split(",");
fs.mkdirSync(OUT, { recursive: true });
const MIN_OVERLAP = 4;

(async () => {
  const br = await chromium.launch({ channel: "chrome", headless: true });
  const ctx = await br.newContext({ viewport: { width: 390, height: 844 } });
  const page = await ctx.newPage();
  await page.addInitScript((l) => { try { localStorage.setItem("citynexus.locale", l); } catch (e) {} }, LOCALE);
  const report = { base: BASE, locale: LOCALE, min_overlap_px: MIN_OVERLAP, routes: {} };

  for (const route of ROUTES) {
    await page.goto(BASE.replace(/\/$/, "") + "/v8/" + route, { waitUntil: "networkidle", timeout: 60000 });
    const seal = page.getByText("使用封存的演示行程", { exact: false }).first();
    if (await seal.count()) { await seal.click(); await page.waitForTimeout(4000); }
    await page.waitForTimeout(1000);
    const r = await page.evaluate((MIN) => {
      const leaves = [];
      document.querySelectorAll("body *").forEach((e) => {
        if (e.children.length) return;
        const t = (e.textContent || "").replace(/\s+/g, " ").trim();
        if (!t) return;
        const cs = getComputedStyle(e);
        if (cs.visibility === "hidden" || cs.display === "none" || Number(cs.opacity) < 0.9) return;
        const b = e.getBoundingClientRect();
        if (b.width < 2 || b.height < 2) return;
        leaves.push({ el: e, text: t.slice(0, 70), tag: e.tagName,
                      testid: e.getAttribute("data-testid"),
                      box: [Math.round(b.x), Math.round(b.y), Math.round(b.width), Math.round(b.height)] });
      });
      const pairs = [];
      const inter = (a, b) => {
        const ox = Math.min(a[0] + a[2], b[0] + b[2]) - Math.max(a[0], b[0]);
        const oy = Math.min(a[1] + a[3], b[1] + b[3]) - Math.max(a[1], b[1]);
        return [ox, oy];
      };
      for (let i = 0; i < leaves.length; i++) {
        for (let j = i + 1; j < leaves.length; j++) {
          const A = leaves[i], B = leaves[j];
          if (A.el.contains(B.el) || B.el.contains(A.el)) continue;
          const [ox, oy] = inter(A.box, B.box);
          if (ox < MIN || oy < MIN) continue;
          if (A.el.parentElement === B.el.parentElement) {
            const big = A.box[2] * A.box[3] >= B.box[2] * B.box[3] ? A : B;
            const small = big === A ? B : A;
            const inside = small.box[0] >= big.box[0] && small.box[1] >= big.box[1] &&
                           small.box[0] + small.box[2] <= big.box[0] + big.box[2] + 1 &&
                           small.box[1] + small.box[3] <= big.box[1] + big.box[3] + 1;
            if (inside) continue;
          }
          pairs.push({ a: { text: A.text, tag: A.tag, testid: A.testid, box: A.box },
                       b: { text: B.text, tag: B.tag, testid: B.testid, box: B.box },
                       overlap_px: [ox, oy] });
        }
      }
      return { leaves: leaves.length, pairs, path: location.pathname };
    }, MIN_OVERLAP);
    report.routes[route] = { leaves: r.leaves, collisions: r.pairs.length, pairs: r.pairs.slice(0, 20) };
    await page.screenshot({ path: OUT + "collide_" + route + "_" + LOCALE + ".png" });
    console.log(route.padEnd(15), "leaves", String(r.leaves).padStart(3), "COLLISIONS", String(r.pairs.length).padStart(2));
    r.pairs.slice(0, 4).forEach((p) => console.log("     ", JSON.stringify(p.a.text).slice(0, 46),
      "x", JSON.stringify(p.b.text).slice(0, 46), "overlap", p.overlap_px.join("x")));
  }
  const total = Object.values(report.routes).reduce((a, x) => a + x.collisions, 0);
  report.summary = { routes: ROUTES.length, total_collisions: total,
                     verdict: total > 0 ? "TEXT_OVERLAPS_TEXT" : "NO_TEXT_COLLISIONS" };
  fs.writeFileSync(OUT + "collisions_" + LOCALE + ".json", JSON.stringify(report, null, 1));
  console.log("TOTAL COLLISIONS", total, "| VERDICT", report.summary.verdict);
  await br.close();
})().catch((e) => { console.log("FATAL", String(e).slice(0, 240)); process.exit(9); });
