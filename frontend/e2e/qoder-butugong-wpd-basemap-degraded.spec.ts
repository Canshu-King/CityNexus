import { expect, test, type Page } from "@playwright/test";
import { writeFileSync } from "node:fs";
import { ensureDemoJourney } from "./_qoderShellSeed";
import { evidencePath } from "./_qoderEvidence";
import { scanContrast } from "./_qoderContrastScan";

/**
 * WP-D — the basemap degradation surface, measured both ways.
 *
 * Why this file exists at all: no gate in `frontend/e2e/` ever engineered a tile failure. The tile host
 * appears in three specs only as the string the ATTRIBUTION must carry
 * (`qoder-map-ord0412-label-scope.spec.ts:26`, `qoder-ord0415-label-string-origin.spec.ts:25`,
 * `qoder-map-ord0390-selection-both-ways.spec.ts:187`), and every `page.route` in the suite intercepts
 * `**\/api\/v1\/**`. So the plate could be written, deleted, or never rendered, and the suite would read
 * the same either way — it depends on which arm the ambient network happened to give that minute.
 *
 * Both arms are therefore pinned here, and neither arm is the ambient network:
 *   aborts   — `route.abort()` on the tile host, which is what the 2026-10-16 02:0x render pass hit
 *              (40–96 `net::ERR_ABORTED` per run). The plate must appear.
 *   answers  — `route.fulfill()` with a served 200 PNG. The plate must NOT appear. A surface that shows
 *              itself whether the tiles came or not is not a state, it is a decoration, and this arm is
 *              the only thing that tells the two apart.
 *              This is a TEST fixture for the success branch, not a product behaviour: nothing in
 *              `src/` ships a local tile, and requirement 1 of this order forbids one.
 *   ambient  — no interception at all, recorded rather than asserted, because on 2026-10-16 midday the
 *              host answers 200 through this machine's proxy and at 02:0x it did not. A reading that
 *              depends on the hour cannot be an assertion.
 *
 * The rest of the file measures the claims the plate makes: the stop count it quotes is the number of
 * pins actually painted, its rows say what the pin beside each number says, a finger on the glass still
 * moves the camera while it is up, the panel is not resized, the retry re-opens the same host rather
 * than pretending, and the new surface adds no contrast finding in either scheme.
 */

const FILE = "e2e/qoder-butugong-wpd-basemap-degraded.spec.ts";
const TILE_GLOB = "https://tile.openstreetmap.org/**";
const VIEWPORT = { width: 390, height: 844 };
const PNG_1PX = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFAAH/q842iWQAAAAASUVORK5CYII=",
  "base64",
);

test.use({ viewport: VIEWPORT, hasTouch: true });

const node = (id: string, detail: unknown) =>
  console.log(`${FILE} :: ${id} — ${JSON.stringify(detail)}`);

const rows: Record<string, unknown> = {};
const push = (id: string, detail: unknown) => {
  rows[id] = detail;
  node(id, detail);
};

type Arm = "aborted" | "answered" | "worstcase";

/* A 2x2 black/white checkerboard served as the tile: at 256 px per tile this puts a pure-white patch
   and a pure-black patch next to everything that floats on the glass. CMDR-DELIVER-0706 assigned
   `map-viewport-reset` and `v8-map-stop-label` to this branch with the reason that the gate's
   `backgroundUnder` walks DOM ancestors and therefore cannot see the picture behind them -- so the
   gate's green is not a visual conclusion, and A9 measures the picture instead. This is a measurement
   rig, not a product asset: nothing in `src/` ships it. */
const WORSTCASE_TILE_PNG = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAIAAAD91JpzAAAAE0lEQVR4nGNgYGD4//8/GDMwAAAp5AX71ZPZmwAAAABJRU5ErkJggg==",
  "base64",
);

/** Put one arm of the tile network in place, then land on the map with a real journey behind it. */
async function openMapWithTiles(page: Page, arm: Arm) {
  const requests: { url: string; failed: boolean; status: number | null }[] = [];
  // A6 re-arms the same page eight times; without this the handler from the previous arm can still be
  // the one that answers, and an arm that silently runs the other arm's network is worse than no arm.
  await page.unroute(TILE_GLOB);
  await page.route(TILE_GLOB, async (route) => {
    const url = route.request().url();
    if (arm === "aborted") {
      requests.push({ url, failed: true, status: null });
      await route.abort();
    } else {
      requests.push({ url, failed: false, status: 200 });
      await route.fulfill({
        status: 200,
        contentType: "image/png",
        body: arm === "worstcase" ? WORSTCASE_TILE_PNG : PNG_1PX,
      });
    }
  });
  page.on("requestfailed", (req) => {
    if (!req.url().includes("tile.openstreetmap.org")) return;
    if (!requests.some((r) => r.url === req.url())) requests.push({ url: req.url(), failed: true, status: null });
  });
  await ensureDemoJourney(page);
  await page.goto("/v8/map", { waitUntil: "load" });
  await expect(page.getByTestId("v8-maplibre-panel").first()).toBeVisible({ timeout: 25_000 });
  // The plate is raised by maplibre's `error` event and cleared by its `idle` + a drawn-tile probe;
  // both land seconds after the panel is visible, so this wait is the claim being settled, not a sleep.
  await page.waitForTimeout(3_000);
  return requests;
}

const readPlate = (page: Page) =>
  page.evaluate(() => {
    const plate = document.querySelector<HTMLElement>(".v8-map-degraded");
    const panel = document.querySelector<HTMLElement>(".v8-map-panel");
    const canvas = document.querySelector<HTMLElement>(".v8-maplibre-canvas");
    const control = document.querySelector<HTMLElement>("[data-testid='map-viewport-reset']");
    const notice = document.querySelector<HTMLElement>(".v8-map-tile-notice");
    const box = (el: HTMLElement | null) => {
      if (!el) return null;
      const r = el.getBoundingClientRect();
      return { x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height) };
    };
    const overlapArea = (a: HTMLElement | null, b: HTMLElement | null) => {
      if (!a || !b) return 0;
      const r = a.getBoundingClientRect();
      const o = b.getBoundingClientRect();
      const w = Math.min(r.right, o.right) - Math.max(r.left, o.left);
      const h = Math.min(r.bottom, o.bottom) - Math.max(r.top, o.top);
      return w > 0 && h > 0 ? Math.round(w * h) : 0;
    };
    /* Whose pixel is the canvas centre? A plate that took the drag is the failure this project has
       already been bitten by twice (ORD-0134 ②, and the pass-9 overlay blocker), so it is measured
       rather than assumed. `firstOwned` is the same question from the other side: how far down the
       plate has to be before the map is reachable again. */
    const frame = canvas?.getBoundingClientRect();
    const centreOwnedBy = frame
      ? (document.elementFromPoint(Math.round(frame.x + frame.width / 2), Math.round(frame.y + frame.height / 2))
          ?.className ?? "nothing")
      : "no canvas";
    return {
      plate: plate ? box(plate) : null,
      platePresent: !!plate,
      tier: plate?.getAttribute("data-cnx-basemap") ?? null,
      retries: plate?.getAttribute("data-cnx-basemap-retries") ?? null,
      stopsClaimed: plate?.getAttribute("data-cnx-basemap-stops") ?? null,
      texts: plate
        ? Array.from(plate.querySelectorAll<HTMLElement>("p,b")).map((el) => ({
            cls: el.className,
            text: (el.textContent ?? "").trim(),
          }))
        : [],
      buttons: plate
        ? Array.from(plate.querySelectorAll<HTMLButtonElement>("button")).map((el) => {
            const r = el.getBoundingClientRect();
            const cx = Math.round(r.x + r.width / 2);
            const cy = Math.round(r.y + r.height / 2);
            /* The paint is 32 px and the hit box is 44, extended outward by a pseudo-element so it costs
               no layout. Probing 21 px above and below the centre is what proves the extension exists
               rather than trusting the CSS that says it does. */
            const probe = (y: number) => {
              const e = document.elementFromPoint(cx, y);
              return e?.closest("button")?.getAttribute("data-testid") ?? (e ? String(e.className || e.tagName) : "nothing");
            };
            return {
              testId: el.getAttribute("data-testid"),
              label: (el.textContent ?? "").trim(),
              w: Math.round(r.width),
              h: Math.round(r.height),
              top: Math.round(r.top),
              bottom: Math.round(r.bottom),
              expanded: el.getAttribute("aria-expanded"),
              hitAbove: probe(cy - 21),
              hitBelow: probe(cy + 21),
            };
          })
        : [],
      pins: document.querySelectorAll(".v8-map-panel .v9-map-marker").length,
      /* What the plate costs. It is reserved ground for the placement pass, so every pixel it takes out
         of the glass comes off the number of stop names that fit — the accepted count at 390x844 on the
         untouched tip is five, and five is exactly the floor
         `qoder-0512-stop-names-on-the-glass.spec.ts` asks for. Reading both arms here is what keeps a
         contrast count that goes DOWN from being reported as a fix when it is really a mask. */
      namesShown: Array.from(
        document.querySelectorAll<HTMLElement>(".v8-map-panel [data-testid='v8-map-stop-label']"),
      ).filter((el) => el.getAttribute("data-placement") === "shown").map((el) => el.textContent?.trim() ?? ""),
      /* The direct question the reframe exists to answer: is any pin standing under the plate? */
      pinsUnderPlate: (() => {
        if (!plate) return null;
        const r = plate.getBoundingClientRect();
        return Array.from(document.querySelectorAll<HTMLElement>(".v8-map-panel .v9-map-marker")).filter((m) => {
          const b = m.getBoundingClientRect();
          const cx = b.x + b.width / 2;
          const cy = b.y + b.height / 2;
          return cx >= r.left && cx <= r.right && cy >= r.top && cy <= r.bottom;
        }).length;
      })(),
      hiddenReasons: Array.from(
        document.querySelectorAll<HTMLElement>(".v8-map-panel [data-testid='v8-map-stop-label']"),
      ).map((el) => `${el.getAttribute("data-placement")}/${el.getAttribute("data-blocked-by")}`),
      /* Where the journey actually sits on this camera, in panel-relative pixels. The plate has to go
         somewhere the pins are not, and that is a measurement, not an opinion. */
      pinSpread: (() => {
        const p = document.querySelector<HTMLElement>(".v8-map-panel");
        if (!p) return null;
        const top = p.getBoundingClientRect().top;
        const ys = Array.from(document.querySelectorAll<HTMLElement>(".v8-map-panel .v9-map-marker")).map(
          (m) => Math.round(m.getBoundingClientRect().top + m.getBoundingClientRect().height / 2 - top),
        );
        return ys.length ? { min: Math.min(...ys), max: Math.max(...ys), panelH: Math.round(p.getBoundingClientRect().height) } : null;
      })(),
      basemapHostAttr: plate?.getAttribute("data-cnx-basemap-host") ?? null,
      /* The licence line must survive its own surface: the plate is allowed to take ground, not the
         traveller's only route to the tile licence (ORD-A, and `qoder-0512` treats the attribution as
         reserved ground for exactly that reason). */
      plateCoversAttribution: (() => {
        const a = document.querySelector<HTMLElement>("[data-testid='v8-map-attribution']");
        if (!plate || !a) return null;
        const r = plate.getBoundingClientRect();
        const o = a.getBoundingClientRect();
        const w = Math.min(r.right, o.right) - Math.max(r.left, o.left);
        const h = Math.min(r.bottom, o.bottom) - Math.max(r.top, o.top);
        return w > 0 && h > 0 ? Math.round(w * h) : 0;
      })(),
      /* The paint is 32 px and the hit box is 44 (extended outward by a pseudo-element, so it costs no
         layout) — probed per button above. */
      /* The plate and the legacy notice are the same element family; both must survive, because
         `qoder-map-ord0403-*.spec.ts:213` measures `.v8-map-tile-notice` and MapPanel reserves it. */
      noticeKept: !!notice,
      panel: box(panel),
      canvas: box(canvas),
      control: box(control),
      overlapPlateControl: overlapArea(plate, control),
      overlapNoticeControl: overlapArea(notice, control),
      centreOwnedBy: String(centreOwnedBy),
      camera: (() => {
        const m = (document.querySelector(".v8-maplibre-canvas") as any)?.citynexusMap;
        if (!m) return null;
        const c = m.getCenter();
        return { zoom: Math.round(m.getZoom() * 1000) / 1000, lat: Math.round(c.lat * 1e5) / 1e5, lng: Math.round(c.lng * 1e5) / 1e5 };
      })(),
      canvasCentreY: frame ? Math.round(frame.y + frame.height / 2) : null,
      pointerEventsOnPlate: plate ? getComputedStyle(plate).pointerEvents : null,
      pointerEventsOnRetry: plate?.querySelector(".v8-map-degraded-btn")
        ? getComputedStyle(plate.querySelector(".v8-map-degraded-btn") as HTMLElement).pointerEvents
        : null,
    };
  });

/** Drag the canvas centre the way the traveller does, and ask whether the camera moved. */
async function dragCentre(page: Page) {
  const before = await page.evaluate(() => {
    const map = (document.querySelector(".v8-maplibre-canvas") as any)?.citynexusMap;
    const c = map?.getCenter();
    return c ? { lng: c.lng, lat: c.lat } : null;
  });
  const frame = await page.locator(".v8-maplibre-canvas").boundingBox();
  if (!frame || !before) return { before, after: null, moved: false };
  await page.mouse.move(frame.x + frame.width / 2, frame.y + frame.height / 2);
  await page.mouse.down();
  await page.mouse.move(frame.x + frame.width / 2 - 70, frame.y + frame.height / 2 - 40, { steps: 8 });
  await page.mouse.up();
  await page.waitForTimeout(700);
  const after = await page.evaluate(() => {
    const map = (document.querySelector(".v8-maplibre-canvas") as any)?.citynexusMap;
    const c = map?.getCenter();
    return c ? { lng: c.lng, lat: c.lat } : null;
  });
  return { before, after, moved: !!after && (after.lng !== before.lng || after.lat !== before.lat) };
}

test("A1-abort-raises-the-plate — tiles refused must produce the surface, and only then", async ({ page }) => {
  test.setTimeout(180_000);
  const requests = await openMapWithTiles(page, "aborted");
  const plate = await readPlate(page);
  await page.screenshot({ path: evidencePath("butugong-wpd", "A1_plate_aborted_390x844.png") });
  push("A1-abort-raises-the-plate", { requests: requests.length, aborted: requests.filter((r) => r.failed).length, ...plate });

  expect(plate.platePresent, "the degradation surface must appear when every tile request is aborted").toBe(true);
  expect(plate.tier, "the tier word rides in an attribute, the human words on the glass").toBe("NOT_AVAILABLE");
  expect(plate.noticeKept, "the ORD-0037 notice keeps its node, class and test identity inside the plate").toBe(true);
  expect(plate.texts.some((t) => t.cls.includes("degraded-headline") && /没接上|did not|No basemap/.test(t.text)),
    "the sentence must name the class of failure, not only the fact").toBeTruthy();
  expect(plate.texts.some((t) => t.cls === "v8-map-tile-notice" && t.text.length > 10),
    "the shipped ORD-0037 sentence stays in the document and keeps role=status, even unpainted").toBeTruthy();
  /* The two literals that name the basemap -- the URL the style asks for and the host the plate carries
     -- are tied by measurement rather than by a parse a reader has to trust: this compares the attribute
     against the host of the requests the arm actually made. */
  expect(Array.from(new Set(requests.map((r) => new URL(r.url).host))),
    "the plate's host must be the host that was called").toEqual([plate.basemapHostAttr]);
  expect(plate.plateCoversAttribution, "the plate may take ground, not the route to the tile licence").toBe(0);
  expect(plate.pointerEventsOnPlate, "the plate is paper: it may not win a drag").toBe("none");
  expect(plate.pointerEventsOnRetry, "the retry is a real control and takes the pointer back").toBe("auto");
  expect(plate.overlapPlateControl, "the plate must not stand on the named viewport control").toBe(0);
  expect(plate.overlapNoticeControl, "…nor may the notice line inside it").toBe(0);
  /* The plate and the journey in one number. The pins occupy relative 59..187 of this 392 px panel and
     the bottom 139 px is the caption band, so the plate only coexists with the map if the camera is told
     how much of its own glass was taken — the reading that caught the first build painting over every
     pin (a 180 px plate: 8 of 9 pins under it, and zero stop names left shown). */
  expect(plate.plate?.h, "a closed plate stays inside the height the panel's geometry leaves").toBeLessThanOrEqual(96);
  /* Recorded, not asserted to zero, and the reason is arithmetic rather than taste: this canvas is 392 px
     tall, the named control owns its top 61 px and the caption band its bottom 197 px of fit padding, so
     the camera has 153 px and the pins measured 43..187 of it. A plate with two real controls cannot fit
     in the ~30 px that is left without taking the journey out of the frame entirely. Where the framing
     can still be honoured the panel reframes around the plate (the `roomForPlate` guard in `MapPanel`);
     where it cannot, the pins sit under paper and A5 is the arm that proves the same nine stops are all
     still readable one tap away. Either way the count is on the record. */
  expect(plate.pins, "the plate's stop count and the painted pins are one number").toBe(Number(plate.stopsClaimed));
  expect(plate.buttons.length, "two exits: ask the host again, and read the stops without it").toBe(2);
  for (const b of plate.buttons) {
    expect(b.h, `「${b.label}」 paints at least a 32 px control`).toBeGreaterThanOrEqual(32);
    expect(b.hitAbove, `「${b.label}」 is reachable 21 px above its centre`).toBe(b.testId);
    expect(b.hitBelow, `「${b.label}」 is reachable 21 px below its centre`).toBe(b.testId);
  }
  /* The invariant this plate's whole layout is built on: every control it paints sits ABOVE the
     canvas's vertical centre, so a one-finger drag in the middle of the glass still lands on the map
     while the plate is up. A7 measures the drag; this measures why the drag is free. */
  if (plate.canvasCentreY != null) {
    for (const b of plate.buttons)
      expect(b.bottom, `「${b.label}」 must stay above the canvas centre at ${plate.canvasCentreY}`).toBeLessThan(plate.canvasCentreY);
  }
  /* The claim on the glass and the thing on the screen must be the same number, not two counts that
     happen to agree today. */
  expect(Number(plate.stopsClaimed), "the stop count the plate quotes is the number of pins painted").toBe(plate.pins);
});

test("A2-answered-hides-the-plate — the reverse arm, or the surface is a decoration", async ({ page }) => {
  test.setTimeout(180_000);
  const requests = await openMapWithTiles(page, "answered");
  const plate = await readPlate(page);
  await page.screenshot({ path: evidencePath("butugong-wpd", "A2_no_plate_when_tiles_answer_390x844.png") });
  push("A2-answered-hides-the-plate", { requests: requests.length, served200: requests.filter((r) => !r.failed).length, ...plate });

  expect(requests.length, "the arm must actually have been exercised — 0 requests proves nothing").toBeGreaterThan(0);
  expect(plate.platePresent, "with tiles served 200 the surface must not be painted").toBe(false);
  expect(plate.noticeKept, "…and neither may the legacy notice line").toBe(false);
});

test("A3-ambient-network — recorded, never asserted: what the real host did on this run", async ({ page }) => {
  test.setTimeout(180_000);
  const seen: { url: string; status: number | null; failed: boolean }[] = [];
  page.on("response", (res) => {
    if (res.url().includes("tile.openstreetmap.org")) seen.push({ url: res.url(), status: res.status(), failed: false });
  });
  page.on("requestfailed", (req) => {
    if (req.url().includes("tile.openstreetmap.org")) seen.push({ url: req.url(), status: null, failed: true });
  });
  await ensureDemoJourney(page);
  await page.goto("/v8/map", { waitUntil: "load" });
  await expect(page.getByTestId("v8-maplibre-panel").first()).toBeVisible({ timeout: 25_000 });
  await page.waitForTimeout(4_000);
  const plate = await readPlate(page);
  const summary = {
    tileResponses: seen.length,
    http200: seen.filter((s) => s.status === 200).length,
    failed: seen.filter((s) => s.failed).length,
    platePresent: plate.platePresent,
  };
  rows["A3-ambient-network"] = summary;
  node("A3-ambient-network", summary);
  /* Deliberately no assertion on the outcome: the 02:0x pass and this one disagree because of the
     network, and a gate that follows the hour teaches nobody anything. What IS asserted is that the
     plate agrees with the tiles — a blank basemap with no plate, or a plate over a drawn map, is the
     defect class, whichever arm the machine happens to be in. */
  const tilesAnswered = summary.http200 > 0;
  expect(plate.platePresent, "the plate must track what the tile host actually did, both arms").toBe(!tilesAnswered);
});

test("A4-retry-asks-again — the button must reopen the same host, not repaint the page", async ({ page }) => {
  test.setTimeout(180_000);
  const requests = await openMapWithTiles(page, "aborted");
  const panelBoxBefore = await readPlate(page);
  const before = requests.length;
  await page.getByTestId("v8-map-degraded-retry").click();
  await page.waitForTimeout(3_000);
  const after = requests.length;
  const plate = await readPlate(page);
  const camera = await page.evaluate(() => {
    const map = (document.querySelector(".v8-maplibre-canvas") as any)?.citynexusMap;
    const z = map?.getZoom();
    return z == null ? null : Math.round(z * 1000) / 1000;
  });
  push("A4-retry-asks-again", {
    requestsBefore: before,
    requestsAfter: after,
    retriesAttribute: plate.retries,
    zoom: camera,
    stillPresent: plate.platePresent,
    retriedLine: plate.texts.find((t) => t.cls.includes("degraded-retried"))?.text ?? null,
  });

  expect(after, "pressing retry must put new requests to the tile host on the wire").toBeGreaterThan(before);
  expect(plate.retries, "…and the plate's own retry count must move with it").toBe("1");
  expect(plate.texts.find((t) => t.cls.includes("degraded-retried"))?.text,
    "a second failed attempt has to be readable on the glass").toContain("1");
  expect(plate.platePresent, "a retry that does not come back keeps saying so — it may not fake success").toBe(true);
  expect(camera, "a retry about the basemap must not move the camera the traveller set").not.toBeNull();
  expect(plate.panel, "…nor resize the panel").toEqual(panelBoxBefore.panel);
});

test("A5-list-is-the-pins — the tile-independent view says what each pin says", async ({ page }) => {
  test.setTimeout(180_000);
  await openMapWithTiles(page, "aborted");
  await page.getByTestId("v8-map-degraded-stops-toggle").click();
  await page.waitForTimeout(600);
  const read = await page.evaluate(() => {
    const pins = Array.from(document.querySelectorAll<HTMLElement>(".v8-map-panel .v9-map-marker"));
    const rowsEl = Array.from(document.querySelectorAll<HTMLElement>(".v8-map-panel .v8-map-degraded-stop"));
    return {
      pins: pins.length,
      rows: rowsEl.length,
      /* Pair each row with the pin of the same ordinal. The rule lives in one function
         (`stopGlassWord`), so a disagreement is a real defect and not a second opinion. */
      pairs: rowsEl.map((row, i) => ({
        ordinal: row.querySelector(".v8-map-degraded-ordinal")?.textContent?.trim() ?? "",
        word: row.querySelector(".v8-map-degraded-stop-word")?.textContent?.trim() ?? "",
        pinNumber: pins[i]?.textContent?.trim() ?? "",
        pinAria: pins[i]?.getAttribute("aria-label") ?? "",
      })),
      expands: document.querySelector("[data-testid='v8-map-degraded-stops-toggle']")?.getAttribute("aria-expanded"),
    };
  });
  await page.screenshot({ path: evidencePath("butugong-wpd", "A5_stop_list_open_390x844.png") });
  push("A5-list-is-the-pins", read);

  expect(read.rows, "every plotted stop must be readable without a basemap").toBeGreaterThan(0);
  expect(read.rows, "…and the list is exactly the set of pins, no more").toBe(read.pins);
  for (const p of read.pairs) {
    expect(p.ordinal, "a row carries the number its pin shows").toBe(p.pinNumber);
    expect(p.word, "a row says the word its pin says").toBe(p.pinAria);
  }
  expect(read.expands, "the disclosure reports its own state").toBe("true");
});

test("A6-both-themes — the new surface adds no contrast finding, light or dark", async ({ page }) => {
  test.setTimeout(240_000);
  const out: Record<string, unknown> = {};
  for (const arm of ["aborted", "answered"] as Arm[]) {
    for (const scheme of ["light", "dark"] as const) {
      for (const vp of [{ width: 390, height: 844, name: "mobile" }, { width: 1280, height: 900, name: "desktop" }]) {
        await page.setViewportSize(vp);
        await page.emulateMedia({ colorScheme: scheme, media: "screen" });
        await openMapWithTiles(page, arm);
        const scan = await scanContrast(page, { scheme });
        const mine = scan.rows.filter(
          (r) => r.selector.includes("v8-map-degraded") || (r.testId ?? "").includes("v8-map-degraded"),
        );
        const key = `${arm}-${scheme}-${vp.name}`;
        out[key] = {
          scanned: scan.count,
          pageRows: scan.rows.length,
          /* The whole page-wide list, not just its length: a count that falls between the two arms has
             to be attributable, or "fewer findings" is reported as "fixed" when the plate merely made
             those elements not measurable (`_qoderContrastScan.ts` skips what is not visible). */
          pageRowKeys: scan.rows.map((r) => `${r.kind} ${r.selector}`),
          plateRows: mine,
          warnings: scan.warnings,
        };
        if (arm === "aborted") {
          await page.screenshot({ path: evidencePath("butugong-wpd", `A6_plate_${scheme}_${vp.name}.png`) });
        }
        /* The plate only exists on the aborted arm, so the rows attributed to it can only be opened by
           it. The page-wide count is recorded for both arms and read by the two-arm table, because this
           screen carries legacy literals this lane is not allowed to touch (`styles.css:176` paints the
           panel with #dfeae8). */
        expect(mine, `no contrast finding may come from the new surface (${key})`).toEqual([]);
      }
    }
  }
  rows["A6-both-themes"] = out;
  node("A6-both-themes", Object.fromEntries(Object.entries(out).map(([k, v]) => [k, (v as any).pageRows])));
});

test("A7-glass-still-owned — a drag on the map while the plate is up moves the map", async ({ page }) => {
  test.setTimeout(180_000);
  await openMapWithTiles(page, "aborted");
  const plate = await readPlate(page);
  const drag = await dragCentre(page);
  push("A7-glass-still-owned", { ...drag, centreOwnedBy: plate.centreOwnedBy, plate: plate.plate });

  expect(plate.centreOwnedBy, "the canvas centre must still be the map's own canvas under the plate").toContain("maplibregl");
  expect(drag.moved, `a one-finger drag at the centre must move the camera: ${JSON.stringify(drag)}`).toBe(true);
});

test("A8-wrapped-rows — at 320 the two exits must not share a hit box", async ({ page }) => {
  test.setTimeout(180_000);
  await page.setViewportSize({ width: 320, height: 653 });
  await openMapWithTiles(page, "aborted");
  const read = await page.evaluate(() => {
    const row = document.querySelector<HTMLElement>(".v8-map-panel .v8-map-degraded-actions");
    const b = Array.from(document.querySelectorAll<HTMLElement>(".v8-map-panel .v8-map-degraded-btn")).map((el) => {
      const r = el.getBoundingClientRect();
      return { testId: el.getAttribute("data-testid"), top: Math.round(r.top), bottom: Math.round(r.bottom), left: Math.round(r.left), right: Math.round(r.right) };
    });
    if (b.length < 2) return { b, wrapped: false, hitOverlapPx2: null, rowGap: null, each: [] };
    /* The hit box is the paint box grown to 44 px tall about its centre (that is what the ::before
       does); horizontally it does not grow. Two buttons collide only if those boxes intersect, which is
       the question -- not whether this particular width happens to wrap. */
    const hit = (x: (typeof b)[number]) => {
      const paintH = x.bottom - x.top;
      const grow = Math.max(0, (44 - paintH) / 2);
      return { x0: x.left, x1: x.right, y0: x.top - grow, y1: x.bottom + grow };
    };
    const [p, q] = [hit(b[0]), hit(b[1])];
    const w = Math.min(p.x1, q.x1) - Math.max(p.x0, q.x0);
    const h = Math.min(p.y1, q.y1) - Math.max(p.y0, q.y0);
    const wrapped = b[1].top >= b[0].bottom;
    const cx = Math.max(b[0].left, b[1].left) + 10;
    const cy = Math.round((b[0].bottom + b[1].top) / 2);
    const betweenEl = wrapped ? document.elementFromPoint(cx, cy) : null;
    return {
      b,
      wrapped,
      hitOverlapPx2: w > 0 && h > 0 ? Math.round(w * h) : 0,
      rowGap: row ? getComputedStyle(row).rowGap : null,
      columnGap: row ? getComputedStyle(row).columnGap : null,
      between: wrapped ? (betweenEl?.closest("button")?.getAttribute("data-testid") ?? "not-a-button") : "single row",
      each: b.map((x) => {
        const probe = (dy: number) => {
          const e = document.elementFromPoint(Math.round((x.left + x.right) / 2), x.top + Math.round((x.bottom - x.top) / 2) + dy);
          return e?.closest("button")?.getAttribute("data-testid") ?? (e ? "not-a-button" : "nothing");
        };
        return { testId: x.testId, minus21: probe(-21), plus21: probe(21) };
      }),
    };
  });
  await page.screenshot({ path: evidencePath("butugong-wpd", "A8_hit_boxes_320x653.png") });
  push("A8-wrapped-rows", read);

  /* The spacing rule the interface guide states is 8 px between touchables; with a 44 px hit box around
     a 32 px paint, a wrapped row would put 6 px of each button's reach into that gap and the two would
     overlap by 4 px. The row-gap is 16 px for exactly that reason, and this is the arm that says so --
     measured as an intersection of the hit boxes rather than as a claim about the CSS. */
  expect(read.hitOverlapPx2, "the two exits' hit boxes may not intersect").toBe(0);
  expect(read.rowGap, "the wrapped-row gap has to clear both 6 px reaches").toBe("16px");
  for (const e of read.each) {
    expect(e.minus21, `${e.testId} reachable 21 px above its centre`).toBe(e.testId);
    expect(e.plus21, `${e.testId} reachable 21 px below its centre`).toBe(e.testId);
  }
});

test("A9-on-the-imagery — what the DOM ruler cannot see, the pixels can", async ({ page }) => {
  test.setTimeout(240_000);
  const out: Record<string, unknown> = {};
  for (const scheme of ["light", "dark"] as const) {
    await page.setViewportSize(VIEWPORT);
    await page.emulateMedia({ colorScheme: scheme, media: "screen" });
    await openMapWithTiles(page, "worstcase");
    const boxes = await page.evaluate(() => {
      const panel = document.querySelector<HTMLElement>(".v8-map-panel");
      if (!panel) return null;
      const pr = panel.getBoundingClientRect();
      /* Clip-relative coordinates: the sampler opens the PNG of this clip, so image px == page px minus
         the clip origin. `deviceScaleFactor` is 1 here (the default), which is what makes that true. */
      const rel = (el: HTMLElement) => {
        const r = el.getBoundingClientRect();
        const cs = getComputedStyle(el);
        return {
          tag: el.tagName,
          role: el.getAttribute("role"),
          contrastRole: el.getAttribute("data-contrast-role"),
          x: Math.round(r.left - pr.left),
          y: Math.round(r.top - pr.top),
          w: Math.round(r.width),
          h: Math.round(r.height),
          background: cs.backgroundColor,
          borderTop: cs.borderTopWidth + " " + cs.borderTopStyle + " " + cs.borderTopColor,
          color: cs.color,
        };
      };
      const control = document.querySelector<HTMLElement>("[data-testid='map-viewport-reset']");
      const chips = Array.from(
        document.querySelectorAll<HTMLElement>(".v8-map-panel [data-testid='v8-map-stop-label']"),
      ).filter((el) => el.getAttribute("data-placement") === "shown");
      return {
        panel: { x: Math.round(pr.left), y: Math.round(pr.top), w: Math.round(pr.width), h: Math.round(pr.height) },
        control: control ? rel(control) : null,
        chips: chips.map(rel),
        themeAttr: document.documentElement.getAttribute("data-theme"),
      };
    });
    expect(boxes, `${scheme}: the panel and the floating control must exist to be sampled`).not.toBeNull();
    const shot = `A9_worstcase_${scheme}.png`;
    await page.screenshot({ path: evidencePath("butugong-wpd", shot), clip: { x: boxes!.panel.x, y: boxes!.panel.y, width: boxes!.panel.w, height: boxes!.panel.h } });
    out[scheme] = { shot, ...boxes };
    /* No assertion on the ratios here: the sampler reads the PNG and the numbers go into the receipt as
       measurements. Asserting a threshold before measuring would be writing the conclusion first. */
  }
  rows["A9-on-the-imagery"] = out;
  node("A9-on-the-imagery", {
    light_control: out.light && (out.light as any).control,
    dark_control: out.dark && (out.dark as any).control,
    chips_light: ((out.light as any)?.chips ?? []).length,
    chips_dark: ((out.dark as any)?.chips ?? []).length,
  });
  writeFileSync(evidencePath("butugong-wpd", "A9_boxes.json"), JSON.stringify(out, null, 1), "utf8");
});

test.afterAll(() => {
  writeFileSync(evidencePath("butugong-wpd", "readings.json"), JSON.stringify({ file: FILE, rows }, null, 1), "utf8");
});
