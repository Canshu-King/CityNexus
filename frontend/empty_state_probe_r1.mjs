/* ORD-0599 -- walk the two empty states as a traveller and press their buttons.

   Reads what is ON SCREEN (innerText of the rendered block) and where a press actually lands
   (URL after the click), so the receipt cannot be satisfied by the code merely existing.

   Run from `frontend/` with the two env vars the shell needs:
     JOURNEY_ID=<uuid> FRONTEND=http://127.0.0.1:<port> node empty_state_probe_r1.mjs

   Plain ESM on purpose: node runs this file directly, so the receipt's command is the one below
   and not a test-runner invocation with its own prerequisites. */
import { chromium } from "@playwright/test";

const FRONTEND = process.env.FRONTEND ?? "http://127.0.0.1:5199";
const JOURNEY = process.env.JOURNEY_ID ?? "";

/* The bottom nav overlays the last row of a short viewport (ORD-0338: laid out is not hittable),
   so the press is taken only after the control is scrolled to the middle, and the hit test is a
   real elementFromPoint probe rather than a check that the node exists. */
async function walk(page, screen, emptyId, actionId) {
  await page.goto(`${FRONTEND}/v8/hub`, { waitUntil: "load" });
  await page.goto(`${FRONTEND}/v8/${screen}`, { waitUntil: "load" });
  const btn = page.locator(`[data-testid="${actionId}"]`);
  await btn.waitFor({ state: "visible", timeout: 30_000 });
  await btn.scrollIntoViewIfNeeded();
  await page.waitForTimeout(250);

  const box = await btn.boundingBox();
  const hits = box
    ? await page.evaluate(
        ([sel, cx, cy]) => {
          const el = document.querySelector(sel);
          if (!el) return false;
          const at = document.elementFromPoint(cx, cy);
          return at === el || (!!at && el.contains(at));
        },
        [`[data-testid="${actionId}"]`, box.x + box.width / 2, box.y + box.height / 2],
      )
    : false;

  /* Read the label, tag and empty text BEFORE the press: after it the route has changed and the
     control is gone, which is how a first version of this probe timed out on its own read. */
  const label = (await btn.innerText()).trim();
  const tag = await btn.evaluate((e) => e.tagName);
  const emptyText = await page.locator(`[data-testid="${emptyId}"]`).first().innerText().catch(() => null);

  await btn.click();
  await page.waitForTimeout(600);
  const landed = new URL(page.url());
  const tripsMarkers = await page
    .locator('[data-testid="trips-tabs"], [data-testid="trip-itinerary"]')
    .count();

  return {
    screen,
    empty_text: emptyText,
    action_label: label,
    action_tag: tag,
    action_hits: hits,
    action_box_px: box ? `${Math.round(box.width)}x${Math.round(box.height)}` : null,
    landed_on: landed.pathname,
    trips_markers_on_landing: String(tripsMarkers),
  };
}

async function main() {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
  await page.goto(`${FRONTEND}/v8/hub`, { waitUntil: "load" });
  await page.evaluate((id) => window.localStorage.setItem("citynexus.v8.journey_id", id), JOURNEY);

  const results = [
    await walk(page, "footprints", "footprint-empty", "footprint-empty-action"),
    await walk(page, "trash", "trash-empty", "trash-empty-action"),
  ];

  for (const r of results) {
    console.log("=== screen: " + r.screen);
    console.log("  empty block text: " + JSON.stringify(r.empty_text));
    console.log("  action label: " + JSON.stringify(r.action_label) + " tag=" + r.action_tag);
    console.log("  action box px: " + r.action_box_px + " hit-test passes: " + r.action_hits);
    console.log("  landed on: " + r.landed_on + " trips markers there: " + r.trips_markers_on_landing);
  }
  await browser.close();

  /* The verdict is computed from the rows above, not written by hand: a screen passes only when its
     control is hittable AND the press actually moved the route. */
  const bad = results.filter((r) => !r.action_hits || !r.landed_on.includes("trips"));
  console.log("VERDICT: " + (bad.length === 0 ? "PASS" : "FAIL " + bad.map((b) => b.screen).join(",")));
  process.exit(bad.length === 0 ? 0 : 1);
}

void main();