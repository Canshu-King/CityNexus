/* ORD-0562, third generation, third pass: read the line three times around the one screenshot.
 *
 * Why this exists: the pass before this one wrote rendered_text = "... 2 days", then took the picture, and
 * the picture showed "3 days" for the same journey in the same browser context one second later. So either
 * the hub line is not stable between reads, or the instrument's own before/after calls straddle a state
 * change. This version reads the text before the shot, reads it again after the shot, and reads the server
 * payload the line is built from, all in the same breath, so a disagreement names which of the three moved.
 */
const fs = require("fs");
const FRONT = process.env.BASE;
const { chromium } = require(process.env.PW_CLI);

async function probe(page) {
  return page.evaluate(() => {
    const line = document.querySelector('[data-testid="today-when"]');
    if (!line) return { present: false };
    const r = line.getBoundingClientRect();
    const top = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
    return {
      present: true,
      text: (line.innerText || "").replace(/\s+/g, " ").trim(),
      box: { x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height) },
      in_viewport: r.top >= 0 && r.bottom <= innerHeight,
      centre_element: top ? (top.tagName + "." + (top.className || "")).slice(0, 90) : null,
      line_is_own_top: !!top && (top === line || line.contains(top)),
      wizard_on_screen: !!document.querySelector('[data-testid="trial-city"]'),
      stored_journey: localStorage.getItem("citynexus.v8.journey_id"),
    };
  });
}

async function serverShape(page, id) {
  return page.evaluate(async (journey) => {
    const r = await fetch(`/api/v1/journeys/${journey}/experience`, { headers: { "Content-Type": "application/json" } });
    const b = await r.json().catch(() => null);
    return {
      http_status: r.status,
      journey_start: b && b.journey ? b.journey.start_at : null,
      journey_end: b && b.journey ? b.journey.end_at : null,
      temporal_shape: b && b.journey ? b.journey.temporal_shape ?? null : null,
      trip_day_count_source: b && b.trip ? { arrival: b.trip.arrival_anchor, departure: b.trip.departure_anchor } : null,
      plan_count: b && b.plans ? b.plans.length : (b && b.active_plan ? 1 : 0),
    };
  }, id);
}

(async () => {
  const want = process.env.JOURNEY;
  const out = { pageerrors: [], journey_id: want };
  const browser = await chromium.launch({ timeout: 120000 });
  const ctx = await browser.newContext({
    viewport: { width: 390, height: 844 }, locale: "en-US", hasTouch: true,
    serviceWorkers: "block",
    storageState: { cookies: [], origins: [{ origin: FRONT, localStorage: [
      { name: "citynexus.v8.journey_id", value: want },
      { name: "citynexus.locale", value: "en" },
    ] }] },
  });
  const page = await ctx.newPage();
  page.on("pageerror", (e) => out.pageerrors.push(String(e).slice(0, 160)));

  await page.goto(FRONT + "/v8/hub", { waitUntil: "load" });
  await page.getByTestId("today-heading").waitFor({ timeout: 60000 });

  for (let attempt = 0; attempt < 8; attempt += 1) {
    const state = await probe(page);
    if (state.line_is_own_top && !state.wizard_on_screen) break;
    await page.keyboard.press("Escape").catch(() => {});
    const closer = page.locator('[data-testid*="close"], [aria-label*="lose"], [aria-label*="Dismiss"]');
    if (await closer.count()) await closer.first().click({ timeout: 2000 }).catch(() => {});
    await page.waitForTimeout(1000);
  }

  out.read_before_shot = await probe(page);
  await page.screenshot({ path: process.env.SHOT, fullPage: false });
  out.read_after_shot = await probe(page);
  out.server_shape = await serverShape(page, want);
  out.location = page.url();

  await ctx.close(); await browser.close();

  const b = out.read_before_shot, a = out.read_after_shot;
  fs.writeFileSync(process.env.OUT, JSON.stringify(out, null, 1), "utf8");
  const agreed = b.present && a.present && b.text === a.text && b.line_is_own_top && a.line_is_own_top
    && !a.wizard_on_screen && a.stored_journey === want;
  console.log((agreed ? "AGREED " : "DISAGREED ") + JSON.stringify({
    before: b.text, after: a.text, stored: a.stored_journey, want: want,
    day_count: a.day_count, server_shape: out.server_shape.temporal_shape,
  }));
  process.exit(agreed ? 0 : 1);
})().catch((e) => { console.error("FAIL " + String(e).slice(0, 300)); process.exit(1); });
