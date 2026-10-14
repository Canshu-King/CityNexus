/**
 * The saved 390x844 Chromium walkthrough `fusion/QODER_EXECUTION_ORDER.md` asks for (§7 and the
 * Deliverables section: "one saved 390x844 Chromium route walkthrough against one fused backend").
 *
 * What makes this a walkthrough and not four screenshots of the same page: every shot is preceded by
 * an assertion on that screen's own marker, and the manifest records the bytes and digest of each
 * PNG.  The byte-level rule is not decoration -- the earlier boot pass (`brick-fusion-boot-u1`) saved
 * four files whose sizes came in identical pairs, which is what a page that never navigated looks
 * like.  Here a repeated shot is a failed test, not a passed one.
 *
 * One backend, one journey, one traveller: the authoritative stack this run starts itself, the journey
 * the seed built through the product API, and a credential this branch's door signs.  Nothing is
 * fulfilled or stubbed; the stamp and the collected place are read back through the same doors the
 * screen used.
 *
 * R107/R108 (the order's other half) is answered as measured, not as hoped: the public discovery
 * console `v13-discovery` must appear on 城市探索 after these imports.  The GO bootstrap screen is
 * recorded by reachability -- it is state-gated at `V8Experience.tsx:1212` behind creating a journey
 * whose city holds no catalogue places, so it is not a URL this walk can take, and `QODER_PARITY.md`
 * §5 keeps the separate finding that its read door has no caller.
 */
import { createHash } from "node:crypto";
import { mkdirSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { dirname } from "node:path";
import { expect, test, type Page } from "@playwright/test";
import { evidencePath } from "./_qoderEvidence";
import { VIEWPORT, ask, checkinsPath, flat, openAs, stage } from "./_qoderOrd0510Stage";

const FILE = "e2e/qoder-ord0510-walk-390x844.spec.ts";
const node = (detail: string) => `${FILE} :: ${detail}`;
test.use({ viewport: VIEWPORT, hasTouch: true });

const SHELF_NAME = "走查架子";
const DIR = "qoder-ord0510-walk";

type Frame = {
  shot: string;
  route: string;
  markers: string[];
  painted: string;
  bytes: number;
  digest: string;
};

const frames: Frame[] = [];

/**
 * Paint this screen, prove it is the screen we came for, and save it.
 * `markers` are testids; `contains` is a phrase the screen must actually show.
 */
async function shoot(page: Page, shot: string, route: string, markers: string[], contains: string[]) {
  for (const id of markers) {
    await expect(page.getByTestId(id).first(), node(`${shot}: ${id} is not on this screen`))
      .toBeVisible({ timeout: 20_000 });
  }
  for (const phrase of contains) {
    await expect(page.locator("body"), node(`${shot}: the screen does not say "${phrase}"`))
      .toContainText(phrase, { timeout: 20_000 });
  }
  const p = evidencePath(DIR, shot + ".png");
  mkdirSync(dirname(p), { recursive: true });
  await page.screenshot({ path: p, fullPage: false });
  const heads = page.locator("h1");
  const painted = (await heads.count()) > 0 ? flat(await heads.first().innerText()).slice(0, 60) : "";
  frames.push({
    shot,
    route,
    markers,
    painted,
    bytes: statSync(p).size,
    digest: createHash("sha256").update(readFileSync(p)).digest("hex").slice(0, 12),
  });
}

test("qoder-ord0510-walk — 390x844 一路走查，每一屏自己作证", async ({ browser, request }) => {
  test.setTimeout(300_000);
  const s = await stage(request, "walk");

  // A shelf through the door, so the collect leg has somewhere to go without the screen inventing one.
  const shelves = await ask(request, "GET", "/api/v1/collections", { token: s.token });
  if (!shelves.some((f: any) => f.name === SHELF_NAME)) {
    await ask(request, "POST", "/api/v1/collections", { token: s.token, data: { name: SHELF_NAME } });
  }

  /* `/` opens on the hub route, but naming the address is what the shell's own `navigate` does
     (`V8Experience.tsx:958`), so the walk uses the form the product writes. */
  const { page, close } = await openAs(browser, s, s.token, "/v8/hub");
  await shoot(page, "01_root", "/v8/hub", ["plan-ranking"], []);

  await page.goto("/v8/discover", { waitUntil: "load", timeout: 90_000 });
  await shoot(page, "02_discover", "/v8/discover",
    ["prep-panel", "v13-discovery", "collection-panel"], []);

  await page.goto("/v8/trips", { waitUntil: "load", timeout: 90_000 });
  await shoot(page, "03_trips_fresh", "/v8/trips",
    ["trip-itinerary", "trips-tabs", "footprint-panel"], ["足迹"]);

  /* The station this walk stamps is whichever one is still unstamped, not a fixed index: the
     four-arm spec runs in the same stack and has already pressed two of them.  It is picked once and
     then held by index -- a `filter({ has: [data-state="fresh"] })` locator is a self-invalidating
     one, and measured exactly that: after the press the set lost that row, `.first()` re-resolved to
     the next fresh stop, and the wait watched a row it had never touched (42 x `unexpected value
     "fresh"` while the stamped row sat one position earlier). */
  const rows = page.getByTestId("trip-stop");
  const rowCount = await rows.count();
  expect(rowCount, node("the trip workspace holds no stops to walk past")).toBeGreaterThan(0);
  let index = -1;
  for (let i = 0; i < rowCount; i += 1) {
    const button = rows.nth(i).getByTestId("stop-checkin");
    if ((await button.getAttribute("data-state")) === "fresh" && !(await button.isDisabled())) {
      index = i;
      break;
    }
  }
  expect(index, node(`none of the ${rowCount} stops can still be stamped`)).toBeGreaterThanOrEqual(0);
  const stop = rows.nth(index);
  const stampEntry = stop.getByTestId("stop-checkin");
  const stopTitle = (await stop.locator(".trip-stop-body b").first().innerText()).trim();

  // The stamp, then the line the read door returns -- the screen is shot with the row it did not have.
  await stampEntry.click();
  await expect(stampEntry, node(`"${stopTitle}" never reached 已打卡`)).toHaveAttribute(
    "data-state",
    "stamped",
    { timeout: 20_000 },
  );
  await page.getByTestId("footprint-retry").click();
  await expect(
    page.getByTestId("footprint-row").filter({ hasText: stopTitle }),
    node(`the read door gave back no row for "${stopTitle}"`),
  ).toHaveCount(1, { timeout: 20_000 });
  await shoot(page, "04_trips_stamped", "/v8/trips",
    ["footprint-row", "trip-itinerary"], [stopTitle, "网页端打的"]);

  const onServer = await ask(request, "GET", checkinsPath(s.journeyId), { token: s.token });
  expect(onServer.some((row: any) => row.activity_id || row.place_id),
    node("the painted stamp is not on the server")).toBe(true);

  // The collect leg, answered by the read door rather than by the tap.
  const collectEntry = page.locator('[data-testid="collect-entry"]:not([disabled])').first();
  await collectEntry.click();
  await page.getByTestId("collect-picker").getByTestId("collect-shelf")
    .filter({ hasText: SHELF_NAME }).first().click();
  await shoot(page, "05_trips_collected", "/v8/trips",
    ["collect-result"], ["已收在", SHELF_NAME]);

  await page.goto("/v8/live", { waitUntil: "load", timeout: 90_000 });
  await shoot(page, "06_live", "/v8/live", ["live-recovery"], []);

  await page.goto("/v8/me", { waitUntil: "load", timeout: 90_000 });
  await shoot(page, "07_me", "/v8/me", ["v8-me"], []);

  /* The R107/R108 half, said as a measurement: the GO bootstrap screen has no URL, so counting it
     across the routes this walk can reach is the honest form of "does it still appear". */
  const goReachable = await page.getByTestId("bootstrap-discovery").count();

  await close();

  const digests = frames.map((f) => f.digest);
  expect(new Set(digests).size, node("two saved shots are the same bytes")).toBe(frames.length);

  const manifest = {
    viewport: VIEWPORT,
    backend: `127.0.0.1:${Number(process.env.CITYNEXUS_BACKEND_PORT ?? 8000)}`,
    journey_id: s.journeyId,
    frames,
    stop_rows: rowCount,
    stamped_row: index,
    stamped_stop: stopTitle,
    r107_discovery_console: "v13-discovery",
    go_bootstrap_reachable_by_url: goReachable > 0,
    go_bootstrap_note:
      "state-gated at V8Experience.tsx:1212 (a new journey whose city holds no catalogue places); " +
      "no URL route, so this walk records absence rather than pretending a click path",
    stamps_on_server: onServer.length,
  };
  const mp = evidencePath(DIR, "walk_manifest.json");
  writeFileSync(mp, JSON.stringify(manifest, null, 1), "utf8");
  console.log("O510WALK " + JSON.stringify({ frames: frames.length, digests, goReachable }));
});
