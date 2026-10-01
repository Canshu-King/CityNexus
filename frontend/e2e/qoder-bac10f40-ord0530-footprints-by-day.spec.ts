/**
 * ORD-0530 -- the footprint screen reads by day, and the day comes from the server.
 *
 * What the arms defend, in the order's own words:
 *   1. an answered-empty read says 还没有足迹 and paints no day line and no row -- the screen cannot
 *      invent a stamp the door did not hand back (this is the false-green defence);
 *   2. a read the server refused says so, and says it differently from a read that never arrived;
 *      the reason code (`CHECKIN_JOURNEY_IN_RECYCLE_BIN` on a trashed trip, reached through the
 *      product's own DELETE door) stays a value the component switches on and never reaches the DOM;
 *   3. the day a stamp belongs to is that instant read in the TRIP's timezone. The browser context is
 *      pinned to America/Los_Angeles while the denominator trip is Asia/Shanghai, so a grouping that
 *      fell back to the device's clock would land on a different date -- and the arm asserts the
 *      journey-zone date, computed here in the test from the same rows the screen reads;
 *   4. every row carries 时刻 + 地点/活动名 + 备注（没写时写"没写备注"）+ 来源, and the counts on the
 *      screen equal the rows the door returned;
 *   5. both shapes are read -- 390x844 and 1280x900 -- with `scrollIntoViewIfNeeded` before the
 *      centre `elementFromPoint`, so a below-the-fold null is never reported as a defect (the
 *      ORD-0390 lesson).
 *
 * Arm order is load-bearing: the refused arm puts a trip in the recycle bin through the product's own
 * DELETE door, and in authoritative mode the setup screen hands every test the same demo trip -- so
 * the destructive arm runs last, and the two arms that need a live trip run before it.
 *
 * Two denominators, one spec. In authoritative mode the trip is the one the setup screen creates and
 * the stops are stamped through the product's own 打卡 control, so there is one day. Against this
 * lane's private stack the trip is named by `CITYNEXUS_ORD0530_JOURNEY` and carries stamps on two
 * days, which is what makes the grouping counterexample bite. Nothing here rewrites a response body:
 * the only injection is making the door not answer (arm 3), which is a failure, not a fabrication.
 */
import { expect, test, type Page } from "@playwright/test";
import { writeFileSync } from "node:fs";
import { evidencePath } from "./_qoderEvidence";
import { ensureDemoJourney } from "./_qoderShellSeed";
import { footprintCopy } from "../src/features/checkin/footprintCopy";

const FILE = "e2e/qoder-bac10f40-ord0530-footprints-by-day.spec.ts";
const PHONE = { width: 390, height: 844 };
const DESKTOP = { width: 1280, height: 900 };
const SEEDED = process.env.CITYNEXUS_ORD0530_JOURNEY ?? "";
const ZONE = "Asia/Shanghai";
const DEVICE_ZONE = "America/Los_Angeles";

const COPY = {
  empty: "还没有足迹。打开行程，在一站上按「打卡」。",
  refused: "服务器答了，但这次没有把足迹交出来。",
  unreachable: "这一屏没问到服务器，所以这里既没说有事，也没说没事。",
  noteAbsent: "没写备注",
  sourceWeb: "网页端打的",
  zoneLead: "日期按这趟行程自己的时区",
};

const runId = process.env.CITYNEXUS_E2E_RUN_ID || "dev";
/* One artefact per arm, written at the moment that arm reads. A single aggregate file only ever
   holds whichever worker wrote last -- the lesson `e2e/qoder-map-ord0412-label-scope.spec.ts:59`
   records, and the reason this file has no "the arms write their readings" test at the end. */
const push = (arm: string, v: Record<string, unknown>) => {
  const payload = { file: FILE, arm, run_id: runId, denominator: SEEDED ? "copied private db" : "authoritative fresh db", ...v };
  writeFileSync(evidencePath("ord0530", `${arm}__${runId}.json`), JSON.stringify(payload, null, 1), "utf8");
  console.log(`${FILE} :: ${arm} — ${JSON.stringify(v)}`);
};

const SEL = { COPY, ZONE };

/** Everything the screen says, read off `innerText`. No assertion in this file reads a data
 *  attribute: the words are the product's output (Q64=①/Q70/Q71). */
const witness = (sel: typeof SEL) => {
  const doc = document;
  const text = (el: Element | null) => (el instanceof HTMLElement ? el.innerText.replace(/\s+/g, " ").trim() : "");
  const panel = doc.querySelector<HTMLElement>("[data-testid='footprint-panel']");
  const days = Array.from(doc.querySelectorAll<HTMLElement>("[data-testid='footprint-day']"));
  const stamps = Array.from(doc.querySelectorAll<HTMLElement>("[data-testid='footprint-row']"));
  const probe = (el: HTMLElement) => {
    el.scrollIntoView({ block: "center" });
    const r = el.getBoundingClientRect();
    const cx = Math.round(r.x + r.width / 2);
    const cy = Math.round(r.y + r.height / 2);
    const at = doc.elementFromPoint(cx, cy);
    return {
      box: { x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height) },
      centre: { x: cx, y: cy },
      in_viewport: r.top >= 0 && r.bottom <= window.innerHeight,
      hit: at ? at.tagName.toLowerCase() + "." + String(at.className || "").slice(0, 24) : "none",
      hit_is_self: !!(at && (at === el || el.contains(at))),
    };
  };
  const painted = text(panel);
  return {
    panel_present: !!panel,
    tally: text(doc.querySelector("[data-testid='footprint-tally']")),
    state_line:
      text(doc.querySelector("[data-testid='footprint-empty']")) ||
      text(doc.querySelector("[data-testid='footprint-refused']")) ||
      text(doc.querySelector("[data-testid='footprint-unreachable']")) ||
      text(doc.querySelector("[data-testid='footprint-no-journey']")),
    zone_line: text(doc.querySelector("[data-testid='footprint-day-zone']")),
    day_rows: days.map((el) => ({ text: text(el), probe: probe(el) })),
    stamp_rows: stamps.map((el) => ({
      cells: Array.from(el.querySelectorAll("span")).map((cell) => text(cell)).filter(Boolean),
      text: text(el),
      probe: probe(el),
    })),
    /* Which day each row sits under, read from the DOM order rather than from a class convention. */
    under_day: stamps.map((el) => {
      let node: Element | null = el.closest("[data-testid='footprint-day-group']") ?? null;
      return text(node?.querySelector("[data-testid='footprint-day']") ?? null);
    }),
    screaming_snake: painted.match(/\b[A-Z][A-Z0-9]{4,}\b/g) ?? [],
    uuids: painted.match(/\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b/gi) ?? [],
  };
};

type Witness = ReturnType<typeof witness>;

/** The journey's own timezone, straight off the payload the shell reads. */
async function tripZone(page: Page, journeyId: string): Promise<string | null> {
  const answer = await page.request.get(`/api/v1/journeys/${journeyId}/experience`);
  expect(answer.status(), "the shell's own read answers").toBe(200);
  const body = await answer.json();
  return body?.journey?.timezone ?? null;
}

async function doorRows(page: Page, journeyId: string): Promise<{ stamped_at: string; target_key: string; note: string | null; source: string }[]> {
  const answer = await page.request.get(`/api/v1/journeys/${journeyId}/checkins`);
  expect(answer.status(), "the footprint read route answers").toBe(200);
  return await answer.json();
}

/**
 * The day a stamp falls on, computed here from the door's own rows -- a second computation of the
 * rule, not a copy of what the component printed. The shape is the one `Intl` produces for zh-CN with
 * these options (9月29日周二), which is also what the screen prints; what the arm is testing is which
 * DATE each stamp lands on, so the two sides have to agree on the calendar, not on my spelling.
 */
function dayInZone(iso: string, zone: string): string {
  return new Intl.DateTimeFormat("zh-CN", {
    timeZone: zone,
    month: "long",
    day: "numeric",
    weekday: "short",
  }).format(new Date(iso));
}

/** The same instant read on this browser's clock -- the rule the order forbids, kept here so the
 *  reading can say whether the two zones actually disagree on this run. */
function dayInDeviceZone(iso: string): string {
  return new Intl.DateTimeFormat("zh-CN", {
    timeZone: DEVICE_ZONE,
    month: "long",
    day: "numeric",
    weekday: "short",
  }).format(new Date(iso));
}

async function openFootprints(page: Page, journeyId: string, size = PHONE): Promise<Witness> {
  await page.setViewportSize(size);
  await page.addInitScript((id) => {
    localStorage.setItem("citynexus.v8.journey_id", id);
    localStorage.setItem("citynexus.locale", "zh-CN");
  }, journeyId);
  await page.goto("/v8/footprints", { waitUntil: "load", timeout: 90000 });
  await page.waitForSelector("[data-testid='footprint-panel']", { timeout: 30000 });
  /* Wait for the read to settle: the state line or the first row has to exist, otherwise the arm
     would be reading the frame before the door answered. */
  await page.waitForFunction(
    () => {
      const s = document.querySelector("[data-testid='footprint-empty'],[data-testid='footprint-refused'],[data-testid='footprint-unreachable']");
      const r = document.querySelector("[data-testid='footprint-row']");
      return !!s || !!r;
    },
    null,
    { timeout: 30000 },
  );
  await page.waitForTimeout(700);
  return page.evaluate(witness, SEL);
}

async function freshTrip(page: Page): Promise<string> {
  await page.setViewportSize(PHONE);
  await ensureDemoJourney(page);
  return page.evaluate(() => localStorage.getItem("citynexus.v8.journey_id") ?? "");
}

test("ORD-0530 zh 390x844 arm=answered_empty invents no stamp and no day", async ({ page }) => {
  const journeyId = await freshTrip(page);
  expect(journeyId.length, "the setup screen hands over a trip").toBeGreaterThan(8);
  const served = await doorRows(page, journeyId);
  expect(served.length, "this trip has nothing stamped on it").toBe(0);
  const w = await openFootprints(page, journeyId);
  expect(w.panel_present, "the panel is the surface being read").toBe(true);
  expect(w.state_line, "the empty arm says 还没有足迹").toBe(COPY.empty);
  expect(w.day_rows.length, "no stamp, no day line").toBe(0);
  expect(w.stamp_rows.length, "no stamp, no row").toBe(0);
  expect(w.tally).toContain("共有 0 枚足迹");
  push("answered_empty", {
    journey_id: journeyId,
    door_rows: served.length,
    state_line: w.state_line,
    day_rows: w.day_rows.length,
    stamp_rows: w.stamp_rows.length,
    tally: w.tally,
    screaming_snake: w.screaming_snake,
    uuids: w.uuids,
  });
});

for (const shape of [PHONE, DESKTOP]) {
  const label = `${shape.width}x${shape.height}`;
  test(`ORD-0530 zh ${label} arm=grouped_by_the_trips_own_day`, async ({ page, context }) => {
    await context.addCookies([]);
    let journeyId = SEEDED;
    if (!journeyId) {
      /* Authoritative mode has no seeded history, so the stops are stamped through the traveller's own
         door: 打卡 on the first two stops of the itinerary. */
      journeyId = await freshTrip(page);
      await page.goto("/v8/trips", { waitUntil: "load" });
      await page.waitForSelector("[data-testid='trip-itinerary']", { timeout: 30000 });
      for (const control of await page.locator("[data-testid='stop-checkin']").all()) {
        await control.scrollIntoViewIfNeeded();
        await control.click();
        await page.waitForTimeout(600);
        if ((await doorRows(page, journeyId)).length >= 2) break;
      }
    } else {
      await page.setViewportSize(shape);
      await page.addInitScript((id) => localStorage.setItem("citynexus.locale", "zh-CN"), journeyId);
    }
    expect(journeyId.length, "a trip to read").toBeGreaterThan(8);

    const zone = await tripZone(page, journeyId);
    expect(zone, "the trip carries its own timezone").toBe(ZONE);
    const served = await doorRows(page, journeyId);
    expect(served.length, "the denominator has stamps to group").toBeGreaterThan(0);

    const w = await openFootprints(page, journeyId, shape);
    const expectedDays = Array.from(new Set(served.map((row) => dayInZone(row.stamped_at, ZONE))));
    expect(w.day_rows.map((d) => d.text), "one visible line per day the trip was on").toEqual(expectedDays);
    expect(w.stamp_rows.length, "one row per stamp the door returned").toBe(served.length);
    expect(w.tally, "and the count says so").toContain(`共有 ${served.length} 枚足迹`);
    expect(w.tally, "the tally names how many days").toContain(`分成 ${expectedDays.length} 天`);
    expect(w.zone_line.startsWith(COPY.zoneLead), `the screen names which clock split the days, got "${w.zone_line}"`).toBe(true);
    expect(w.zone_line).toContain(ZONE);
    for (const row of w.stamp_rows) {
      expect(row.cells.length, `a row carries time, name, note and source: ${row.text}`).toBeGreaterThanOrEqual(4);
      expect(/^\d{1,2}:\d{2}$/.test(row.cells[0]), `the first cell is a clock, got "${row.cells[0]}"`).toBe(true);
      expect(row.cells[2], `the note cell is never empty: ${row.text}`).not.toBe("");
      expect([COPY.noteAbsent, COPY.sourceWeb].includes(row.cells[3]) || row.cells[3].length > 0, "source cell carries words").toBe(true);
      expect(row.cells.some((cell) => cell === COPY.sourceWeb) || row.cells.some((cell) => cell === COPY.noteAbsent), `row names its source or its absent note: ${row.text}`).toBe(true);
    }
    /* The device's clock is 15 hours away from the trip's, so at least one stamp lands on a different
       date in each -- that is what makes this arm able to tell the two rules apart at all. */
    const deviceDays = Array.from(new Set(served.map((row) => dayInDeviceZone(row.stamped_at))));
    const disagree = expectedDays.some((day) => !deviceDays.includes(day));
    for (const day of w.day_rows) {
      expect(day.probe.in_viewport, "the day line was on screen when it was hit-tested").toBe(true);
      expect(day.probe.hit_is_self, "the day line takes its own centre hit").toBe(true);
    }
    expect(w.stamp_rows[0].probe.hit_is_self, "a stamp row takes its own centre hit").toBe(true);
    expect(w.screaming_snake.length, `no machine word on the screen: ${JSON.stringify(w.screaming_snake)}`).toBe(0);
    expect(w.uuids.length, `no bare uuid on the screen: ${JSON.stringify(w.uuids)}`).toBe(0);
    await page.screenshot({ path: evidencePath("ord0530", `footprints_${label}_${process.env.CITYNEXUS_E2E_RUN_ID || "dev"}.png`) });
    push(`grouped_by_the_trips_own_day_${label}`, {
      journey_id: journeyId,
      shape,
      trip_zone: zone,
      device_zone: DEVICE_ZONE,
      device_zone_would_give: deviceDays,
      trip_zone_gives: expectedDays,
      zones_disagree: disagree,
      door_rows: served.map((row) => ({ stamped_at: row.stamped_at, target_key: row.target_key, note: row.note, source: row.source })),
      day_rows: w.day_rows.map((d) => ({ text: d.text, box: d.probe.box, centre: d.probe.centre, hit: d.probe.hit, in_viewport: d.probe.in_viewport })),
      stamp_rows: w.stamp_rows.map((r) => ({ text: r.text, cells: r.cells, under_day: r.probe.box.y, hit: r.probe.hit, in_viewport: r.probe.in_viewport })),
      under_day: w.under_day,
      tally: w.tally,
      zone_line: w.zone_line,
      screaming_snake: w.screaming_snake,
      uuids: w.uuids,
    });
  });
}

test("ORD-0530 zh 390x844 arm=retry_button_keeps_its_line one line, own width, own centre", async ({ page }) => {
  /* The screen's own control, read the way a thumb meets it. At 390 the head is a flex row and the
     button shrank to 48 px, so 重读一次 stacked one character per line (box 48x105, four painted line
     rects). A bounding box cannot prove wrapping -- it grows with the wrap -- so this counts the text
     range's client rects, and compares the button's rendered width against the same button at desktop
     width, where it never wrapped. The centre hit is taken without scrolling, because that is the
     state the traveller arrives in. */
  const journeyId = SEEDED || (await freshTrip(page));
  const measure = async (size: { width: number; height: number }, centre = false) => {
    await openFootprints(page, journeyId, size);
    return page.evaluate((wantCentre) => {
      const el = document.querySelector("[data-testid='footprint-retry']") as HTMLElement;
      if (wantCentre) el.scrollIntoView({ block: "center" });
      const r = el.getBoundingClientRect();
      const rects: { y: number; h: number }[] = [];
      const walk = (node: Node) => {
        if (node.nodeType === 3 && (node as Text).textContent && (node as Text).textContent!.trim()) {
          const rg = document.createRange();
          rg.selectNodeContents(node);
          Array.from(rg.getClientRects()).forEach((x) => {
            if (x.width > 0 && x.height > 0) rects.push({ y: Math.round(x.y), h: Math.round(x.height) });
          });
        }
        node.childNodes.forEach(walk);
      };
      walk(el);
      const c = { x: Math.round(r.x + r.width / 2), y: Math.round(r.y + r.height / 2) };
      const hit = document.elementFromPoint(c.x, c.y) as Element | null;
      const nav = document.querySelector(".v8-mobile-nav");
      return { text: el.innerText.replace(/\s+/g, " ").trim(),
               box: { x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height) },
               painted_lines: new Set(rects.map((x) => x.y)).size,
               centre: c,
               hit: hit ? hit.tagName.toLowerCase() + "." + String(hit.className) : "none",
               hit_is_self: !!hit && (hit === el || el.contains(hit)),
               hit_is_nav: !!hit && !!nav && (hit === nav || nav.contains(hit)),
               nav_top: nav ? Math.round(nav.getBoundingClientRect().top) : null,
               inner_height: window.innerHeight,
               scroll_y: Math.round(window.scrollY || document.scrollingElement?.scrollTop || 0),
               scroller_top: (() => { const s = el.closest("[class*='scroll']") as HTMLElement | null;
                 return s ? { tag: s.tagName.toLowerCase() + '.' + String(s.className),
                              top: Math.round(s.getBoundingClientRect().top),
                              bottom: Math.round(s.getBoundingClientRect().bottom),
                              scroll_top: Math.round(s.scrollTop) } : null; })(),
               in_viewport: r.top >= 0 && r.bottom <= window.innerHeight };
    }, centre);
  };
  const phone = await measure(PHONE);
  const desk = await measure(DESKTOP);
  const centred = await measure(PHONE, true);
  expect(phone.text, "the button says the word the product's own copy table gives it")
    .toBe(footprintCopy("zh-CN", "retry"));
  expect(phone.painted_lines, "one line at 390, measured on the painted text rects").toBe(1);
  expect(phone.box.w, "and it keeps the width the same button has where nothing squeezes it")
    .toBe(desk.box.w);
  /* The shell restores its own scroll position on arrival, which can put the header half out of
     the viewport (read below as shell_restored_scroll_y). That is not this control's defect, and
     ORD-0537 already set the shape: reachability means some scroll position puts the centre on
     the control itself, with the fixed bar not in the way. */
  expect(centred.in_viewport, "a scroll position puts the whole button inside the viewport").toBe(true);
  expect(centred.hit_is_self, "and its centre hit lands on the button itself").toBe(true);
  expect(centred.hit_is_nav, "while the fixed bottom bar does not take that hit").toBe(false);
  push("retry_button_keeps_its_line", {
    journey_id: journeyId,
    phone: phone, centred: centred, desktop_width: desk.box.w,
    desktop_painted_lines: desk.painted_lines,
    shell_restored_scroll_y: phone.scroll_y,
    nav_top_read_on_screen: phone.nav_top,
    how_wrapping_is_measured: "Range.getClientRects() over the text node, not getBoundingClientRect()",
  });

});

test("ORD-0530 zh 390x844 arm=retry_after_the_door_stops keeps nothing it did not re-read", async ({ page }) => {
  /* The shape a "no stamps invented" claim really has to survive: the screen HAS rows, then the door
     stops answering and the traveller presses 重读一次. If a failed re-read left the old rows on the
     glass, the screen would be asserting footprints the server did not just give it. */
  const journeyId = SEEDED || (await freshTrip(page));
  const first = await openFootprints(page, journeyId);
  const served = await doorRows(page, journeyId);
  expect(first.stamp_rows.length, "the denominator paints one row per stamp").toBe(served.length);
  expect(first.stamp_rows.length, "and this arm needs something on the screen to lose").toBeGreaterThan(0);
  await page.route("**/api/v1/journeys/*/checkins*", (route) => route.abort());
  const retry = page.locator("[data-testid='footprint-retry']");
  await retry.scrollIntoViewIfNeeded();
  await retry.click();
  await page.waitForFunction(
    () => !!document.querySelector("[data-testid='footprint-unreachable']"),
    null,
    { timeout: 30000 },
  );
  await page.waitForTimeout(700);
  const after = await page.evaluate(witness, SEL);
  expect(after.state_line, "the screen says it never reached the server").toBe(COPY.unreachable);
  expect(after.stamp_rows.length, "and the stamps it can no longer read are gone from the glass").toBe(0);
  expect(after.day_rows.length, "and so are the days under them").toBe(0);
  expect(after.tally, "the count follows the read, not the memory").toContain("共有 0 枚足迹");
  push("retry_after_the_door_stops", {
    journey_id: journeyId,
    rows_before: first.stamp_rows.length,
    door_rows: served.length,
    state_after: after.state_line,
    rows_after: after.stamp_rows.length,
    days_after: after.day_rows.length,
    tally_after: after.tally,
    injected: "route.abort on the checkins read, then the screen's own 重读一次",
  });
});

test("ORD-0530 zh 390x844 arm=refused_and_unreachable say which step did not answer", async ({ page }) => {
  /* A refusal reached through the product: the trip is put in the recycle bin through its own DELETE
     door, and the footprint read then answers 409 with reason_code
     CHECKIN_JOURNEY_IN_RECYCLE_BIN. Nothing about that answer is invented here. */
  const journeyId = await freshTrip(page);
  const gone = await page.request.delete(`/api/v1/journeys/${journeyId}`);
  expect(gone.status(), "the trash door takes it").toBe(204);
  const refused = await openFootprints(page, journeyId);
  expect(refused.state_line, "the refused arm names the server's no").toBe(COPY.refused);
  expect(refused.stamp_rows.length, "a refusal paints no row").toBe(0);
  expect(refused.day_rows.length, "and no day").toBe(0);
  expect(refused.screaming_snake.length, "the reason code stays off the screen").toBe(0);

  /* The other failure: the door never answers at all. */
  const live = SEEDED || journeyId;
  await page.route("**/api/v1/journeys/*/checkins*", (route) => route.abort());
  const w = await openFootprints(page, live);
  expect(w.state_line, "an unanswered read says it never reached the server").toBe(COPY.unreachable);
  expect(w.stamp_rows.length, "and does not fall back to painting stamps").toBe(0);
  expect(w.day_rows.length, "or days").toBe(0);
  push("refused_and_unreachable", {
    refused_journey_id: journeyId,
    refused_line: refused.state_line,
    refused_rows: refused.stamp_rows.length,
    refused_days: refused.day_rows.length,
    unreachable_journey_id: live,
    unreachable_line: w.state_line,
    unreachable_rows: w.stamp_rows.length,
    unreachable_days: w.day_rows.length,
    injected: "route.abort on the checkins read (a failure, not a doctored answer)",
  });
});

