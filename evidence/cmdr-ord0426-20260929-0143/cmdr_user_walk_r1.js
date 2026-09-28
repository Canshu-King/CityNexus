/* CMDR first-hand user walk r1 - act like a traveller on the phone shape and report which controls do
 * nothing.
 *
 * Why this exists: everything I have measured tonight was targeted (deep links, one button, one caption).
 * A green gate plus targeted probes still misses the thing a user feels fastest: you tap something and the
 * screen does not answer.  So this walks every route, taps every control that is NOT destructive, and asks
 * after each tap whether anything a traveller would notice actually changed.
 *
 * Deliberately conservative about writes:
 *   - runs against MY private stack (own port, own sqlite copy), never the shared preview DB;
 *   - skips any control whose own text matches a destructive list (丢弃/删除/清空/重置/退出/撤销/undelete/
 *     delete/reset/clear/withdraw/cancel) - a walk must not destroy the seeded journey it is reading;
 *   - skips the service worker / offline entry (that arm belongs to ORD-0274's own instrument).
 *
 * "Changed" is measured three ways and reported per click, because one alone lies:
 *   dom_chars   - rendered text length delta (a modal opening changes it; so does a spinner)
 *   url         - route moved
 *   testids     - which panel testids are present before/after (a screen swap is the real signal)
 * A control that produces none of the three, and logs no console error and no failing request, is INERT.
 *
 * Usage: node _cmdr_user_walk_r1.js <base> <out-dir> [routes-csv]
 */
const { chromium } = require("D:/moodle/CityNexus/frontend/node_modules/playwright");
const fs = require("fs");
const BASE = process.argv[2] || "http://127.0.0.1:4805";
const OUT = process.argv[3] || "D:/moodle/_qoder_cmdr_ref_20260921/live_checks/_user_walk_r1/";
const ROUTES = (process.argv[4] || "hub,live,map,studio,stay,discover,bookings,agent,authoritative,intelligence,twin,trips,me,trash").split(",");
fs.mkdirSync(OUT, { recursive: true });

const DESTRUCTIVE = /(丢弃|删除|清空|重置|退出|撤销|放弃|delete|remove|reset|clear|withdraw|cancel|discard|undelete|sign out|log out)/i;

const SNAP = () => {
  const vis = (e) => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
  const controls = Array.from(document.querySelectorAll("button,[role=button],a,[data-testid]"))
    .filter(vis)
    .map((e) => ({
      tag: e.tagName, text: (e.innerText || e.textContent || "").replace(/\s+/g, " ").trim().slice(0, 60),
      testid: e.getAttribute("data-testid"),
      box: (() => { const r = e.getBoundingClientRect(); return [Math.round(r.x), Math.round(r.y), Math.round(r.width), Math.round(r.height)]; })(),
      disabled: !!e.disabled || e.getAttribute("aria-disabled") === "true",
    }));
  const testids = Array.from(document.querySelectorAll("[data-testid]")).filter(vis).map((e) => e.getAttribute("data-testid"));
  return { url: location.pathname + location.search, controls, testids,
           dom_chars: (document.body.innerText || "").length };
};

(async () => {
  const br = await chromium.launch({ channel: "chrome", headless: true });
  const ctx = await br.newContext({ viewport: { width: 390, height: 844 } });
  const page = await ctx.newPage();
  const report = { base: BASE, at: new Date().toISOString(), viewport: "390x844", routes: {} };
  const errors = [];
  const failedReq = [];
  page.on("pageerror", (e) => errors.push(String(e).slice(0, 200)));
  page.on("console", (m) => { if (m.type() === "error") errors.push("console:" + m.text().slice(0, 160)); });
  page.on("requestfailed", (r) => failedReq.push(r.url().slice(0, 120) + " " + (r.failure() || {}).errorText));
  page.on("response", (r) => { if (r.status() >= 500) failedReq.push("HTTP" + r.status() + " " + r.url().slice(0, 120)); });

  for (const route of ROUTES) {
    await page.goto(BASE.replace(/\/$/, "") + "/v8/" + route, { waitUntil: "networkidle", timeout: 60000 });
    const seal = page.getByText("使用封存的演示行程", { exact: false }).first();
    if (await seal.count()) { await seal.click(); await page.waitForTimeout(4000); }
    await page.waitForTimeout(1000);
    const before = await page.evaluate(SNAP);
    const seen = new Set();
    const taps = [];
    // click at most 12 controls per route, in DOM order, skipping duplicates by (text|testid)
    for (const c of before.controls) {
      if (taps.length >= 12) break;
      if (c.disabled) continue;
      if (!c.text && !c.testid) continue;
      const key = (c.text || "") + "|" + (c.testid || "");
      if (seen.has(key)) continue;
      seen.add(key);
      if (DESTRUCTIVE.test(c.text)) { taps.push({ control: c, clicked: false, reason: "skipped_destructive" }); continue; }
      const [x, y, w, h] = c.box;
      const cx = Math.round(x + w / 2), cy = Math.round(y + h / 2);
      if (cx < 0 || cy < 0 || cx > 390 || cy > 844) { taps.push({ control: c, clicked: false, reason: "centre_offscreen" }); continue; }
      const hit = await page.evaluate(([px, py]) => {
        const e = document.elementFromPoint(px, py);
        return e ? (e.tagName + "|" + (e.getAttribute("data-testid") || "")) : "none";
      }, [cx, cy]);
      if (!/(BUTTON|A|v8-|cn-)/.test(hit) && hit === "none") { taps.push({ control: c, clicked: false, reason: "hit_test_missed" }); continue; }
      const e0 = errors.length;
      await page.mouse.click(cx, cy);
      await page.waitForTimeout(1400);
      const after = await page.evaluate(SNAP);
      const newTestids = after.testids.filter((t) => !before.testids.includes(t));
      const goneTestids = before.testids.filter((t) => !after.testids.includes(t));
      const delta = { chars: after.dom_chars - before.dom_chars, url_changed: after.url !== before.url,
                      new_testids: newTestids.slice(0, 6), gone_testids: goneTestids.slice(0, 6),
                      new_errors: errors.length - e0 };
      const answered = delta.url_changed || delta.chars !== 0 || newTestids.length > 0 || goneTestids.length > 0
        || delta.new_errors > 0;
      taps.push({ control: c, clicked: true, hit_test: hit, delta, verdict: answered ? "ANSWERED" : "INERT" });
      // go back to this route's own screen before the next tap, so one modal doesn't shade the rest
      await page.goto(BASE.replace(/\/$/, "") + "/v8/" + route, { waitUntil: "networkidle", timeout: 60000 });
      await page.waitForTimeout(900);
    }
    const inert = taps.filter((t) => t.verdict === "INERT" || (t.clicked && !t.verdict));
    report.routes[route] = { controls_visible: before.controls.length, attempted: taps.length,
                             inert: taps.filter((t) => t.verdict === "INERT").length,
                             skipped: taps.filter((t) => !t.clicked).map((t) => ({ text: t.control.text, reason: t.reason })),
                             taps };
    fs.writeFileSync(OUT + "after_" + route + ".png", await page.screenshot({ type: "png" }));
    console.log(route.padEnd(15), "controls", String(before.controls.length).padStart(3),
                "tapped", String(taps.filter((t) => t.clicked).length).padStart(2),
                "INERT", String(taps.filter((t) => t.verdict === "INERT").length).padStart(2),
                "skipped", String(taps.filter((t) => !t.clicked).length).padStart(2));
  }
  report.errors = errors.slice(0, 40);
  report.error_count = errors.length;
  report.failed_requests = failedReq.slice(0, 30);
  report.failed_request_count = failedReq.length;
  const totalInert = Object.values(report.routes).reduce((a, r) => a + r.inert, 0);
  report.summary = { routes: ROUTES.length, total_inert_controls: totalInert,
                     verdict: totalInert > 0 ? "SOME_CONTROLS_DO_NOTHING" : "NO_INERT_CONTROLS_FOUND" };
  fs.writeFileSync(OUT + "user_walk_r1.json", JSON.stringify(report, null, 1));
  console.log("TOTAL INERT", totalInert, "| pageerrors+console errors", errors.length, "| failed reqs", failedReq.length);
  console.log("VERDICT", report.summary.verdict);
  await br.close();
})().catch((e) => { console.log("FATAL", String(e).slice(0, 240)); process.exit(9); });
