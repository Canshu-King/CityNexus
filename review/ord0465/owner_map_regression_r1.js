/*
 * ORD-0465 regression - the owner's own map, on the same built bundle.
 *
 * This order widened `MapPanel`'s data prop from `V8Data` to the six fields the component reads and
 * turned three of those reads optional-chained. That is a change to a component four other surfaces
 * mount, so the claim "nothing else moved" needs its own reading rather than a typecheck pass.
 *
 * Driven against the lane's own backend (:8731) and front (:4931) with the seeded trip selected as
 * this device's journey, which is the path the shell's boot read takes. The map is judged by what it
 * puts on screen: the panel mounts, the marker count equals the number of located stops the server
 * sent for that plan, and the "no coordinates" face is NOT the one showing.
 */
const fs = require("fs");
const path = require("path");
const LANE = "D:/moodle/_qoder_r_ord0465_20260929";
const REPO = LANE + "/wt";
const { chromium } = require(path.join(LANE, "wt/frontend/node_modules/playwright"));

const FRONT = "http://127.0.0.1:4931";
const BACKEND = "http://127.0.0.1:8731/api/v1";
const seed = JSON.parse(fs.readFileSync(path.join(LANE, "run/seed_report.json"), "utf-8"));
const journeyId = seed.journeys.with_plan;

(async () => {
  const serverExperience = await fetch(`${BACKEND}/journeys/${journeyId}/experience`).then((r) => r.json());
  const locatedFromServer = (serverExperience.active_plan?.activities ?? []).filter(
    (item) => item.location && item.location.latitude != null && item.location.longitude != null,
  ).length;

  const browser = await chromium.launch({ channel: "chrome", headless: true });
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 }, locale: "zh-CN" });
  const page = await context.newPage();
  await page.addInitScript(([id]) => {
    window.localStorage.setItem("citynexus.v8.journey_id", id);
  }, [journeyId]);
  await page.goto(FRONT + "/v8/map", { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(6000);

  const panel = await page.$('[data-testid="v8-maplibre-panel"]');
  const empty = await page.$('[data-testid="v8-map-empty"]');
  const markers = await page.$$eval(".maplibregl-marker", (els) => els.length).catch(() => 0);
  const shellText = await page.innerText("body").catch(() => "");
  const mounted = shellText.length > 200;

  const outcome = {
    journey_id: journeyId,
    located_stops_from_the_server: locatedFromServer,
    owner_map_panel_mounted: Boolean(panel),
    owner_map_shows_the_no_coordinate_face: Boolean(empty),
    owner_map_marker_count: markers,
    shell_rendered: mounted,
    shell_text_chars: shellText.length,
  };
  outcome.pass =
    mounted && Boolean(panel) && !empty && markers === locatedFromServer && locatedFromServer > 0;

  await page.screenshot({ path: path.join(REPO, "review/ord0465/regression_owner_map.png") });
  fs.writeFileSync(path.join(REPO, "review/ord0465/regression_owner_map_r1.json"),
    JSON.stringify(outcome, null, 2), { encoding: "utf-8" });
  console.log(JSON.stringify(outcome, null, 2));
  await browser.close();
  process.exit(outcome.pass ? 0 : 1);
})().catch((error) => {
  console.error("REGRESSION_DRIVER_ERROR", String(error && error.message));
  process.exit(2);
});
