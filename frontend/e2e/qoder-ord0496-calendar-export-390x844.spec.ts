/**
 * ORD-0496 slice 3 on glass: the calendar export pressed once at 390x844, and the file it wrote
 * counted from its own bytes.
 *
 * Why a browser and not the pytest arms: the door arms prove RFC grammar and scope, but the order's
 * slice-3 acceptance is "界面守门在 390x844 真点一次导出并留字节数/事件数回执".  A download is only
 * proved by a file.  The bytes this test counts are what Chromium accepted from the blob the screen
 * created -- nothing here re-fetches the door and calls that the export.
 *
 * TWO LEGS, BOTH WITH THEIR OWN RECEIPT.
 *  - the traveller the seed built, holding a credential this branch's door signs: one tap must produce
 *    a download whose bytes hold VEVENTs, whose name carries the trip's real title, and whose on-screen
 *    sentence counts the same number the bytes count.
 *  - the same screen with no credential: the tap must produce a refusal sentence and NO download.  A
 *    door that answered 401 but whose screen then printed `calendar.refused.unknown` as a word would
 *    pass a "did it refuse?" grep, so this leg asserts the absence of a raw key as its own fact.
 *
 * The number of events is not predicted from the plan.  The exporter's own rule (an activity needs a
 * parseable clock with its own offset, else it is skipped and counted) is measured at the door in the
 * pytest arms; here the arithmetic is checked against the door's headers, and the file is checked
 * against itself.
 */
import { createHash } from "node:crypto";
import { readFileSync, writeFileSync } from "node:fs";
import { relative, resolve } from "node:path";
import { expect, test, type Page } from "@playwright/test";
import { evidencePath } from "./_qoderEvidence";
import { API, VIEWPORT, openAs, stage } from "./_qoderOrd0510Stage";

const FILE = "e2e/qoder-ord0496-calendar-export-390x844.spec.ts";
const node = (detail: string) => `${FILE} :: ${detail}`;
const DIR = "qoder-ord0496-calendar";
const CALENDAR = (journeyId: string) =>
  `/api/v1/journeys/${encodeURIComponent(journeyId)}/calendar.ics`;

const eventsIn = (text: string) => (text.match(/BEGIN:VEVENT/g) ?? []).length;

/**
 * RFC grammar read off the archived bytes, so a receipt line in the seam doc never has to be
 * re-typed from a console: `DTSTAMP` is the row's own `updated_at`, so the file is only stable while
 * the rows are -- a second run stages new activity ids and the sha moves with them.  Which lines can
 * move is therefore recorded next to the sha instead of being argued.
 */
function grammarCensus(bytes: Buffer) {
  const lines = bytes.toString("utf-8").split("\r\n");
  const count = (field: string) => lines.filter((l) => l.startsWith(`${field}:`)).length;
  return {
    crlf_pairs: (bytes.toString("latin1").match(/\r\n/g) ?? []).length,
    bare_line_feeds: bytes.filter((byte, index) => byte === 0x0a && bytes[index - 1] !== 0x0d).length,
    physical_lines_nonempty: lines.filter((l) => l.length > 0).length,
    lines_over_75_octets: lines.filter((l) => Buffer.byteLength(l, "utf-8") > 75).length,
    longest_line_octets: Math.max(...lines.map((l) => Buffer.byteLength(l, "utf-8"))),
    folded_continuation_lines: lines.filter((l) => l.startsWith(" ")).length,
    dtstart: count("DTSTART"),
    dtend: count("DTEND"),
    uid: count("UID"),
    dtstamp: count("DTSTAMP"),
    dtstamp_values: [...new Set(lines.filter((l) => l.startsWith("DTSTAMP:")))],
    run_dependent_fields: ["UID (the staged row's own id)", "DTSTAMP (the row's updated_at)"],
  };
}

/** The notice line, read off the screen, with the button pressed and the download awaited. */
async function pressExport(page: Page, context: { downloads: string[] }) {
  page.on("download", (download) => context.downloads.push(download.suggestedFilename()));
  await page.getByTestId("calendar-export").click();
  await expect(page.getByTestId("calendar-export-notice"), node("the screen said nothing back"))
    .toBeVisible({ timeout: 20_000 });
}

test("qoder-ord0496-calendar — 390x844 点一次导出，字节与事件数自己作证", async ({
  browser,
  request,
}) => {
  test.setTimeout(180_000);
  const s = await stage(request, "calendar");

  const logged = await openAs(browser, s, s.token, "/v8/trips");
  const anon = await openAs(browser, s, null, "/v8/trips");
  try {
    // The button is part of the itinerary header; prove the screen is the itinerary before pressing.
    await expect(logged.page.getByTestId("trip-itinerary").first(), node("not on the itinerary"))
      .toBeVisible({ timeout: 20_000 });
    const button = logged.page.getByTestId("calendar-export");
    const label = await button.innerText();
    expect(label.trim().length, node("the export button carries no words")).toBeGreaterThan(0);

    const downloads: string[] = [];
    const [download] = await Promise.all([
      logged.page.waitForEvent("download", { timeout: 20_000 }),
      pressExport(logged.page, { downloads }),
    ]);

    const written = await download.path();
    expect(written, node("Chromium accepted no file for the download it announced")).not.toBeNull();
    const bytes = readFileSync(written as string);
    const text = bytes.toString("utf-8");
    const census = grammarCensus(bytes);
    const events = eventsIn(text);
    expect(events, node("the downloaded file holds no VEVENT")).toBeGreaterThan(0);
    expect(text.startsWith("BEGIN:VCALENDAR"), node("the file is not a calendar object")).toBe(true);
    expect(census.bare_line_feeds, node("the file carries a bare line feed, so it is no iCalendar"))
      .toBe(0);
    expect(census.lines_over_75_octets, node("a contentline is longer than RFC 5545 allows"))
      .toBe(0);
    expect(download.suggestedFilename(), node("the file name lost the trip's own title"))
      .toContain(`--${s.journeyId}.ics`);

    const notice = (await logged.page.getByTestId("calendar-export-notice").innerText()).trim();
    expect(notice, node("the screen's sentence does not count the events the file holds"))
      .toContain(String(events));
    expect(notice.includes("calendar."), node(`the screen printed a dictionary key: ${notice}`))
      .toBe(false);

    // The door's own arithmetic, for the same journey and the same credential.
    const raw = await request.get(`${API}${CALENDAR(s.journeyId)}`, {
      headers: { Authorization: `Bearer ${s.token}` },
    });
    expect(raw.status(), node("the door did not answer 200 for the traveller the screen used"))
      .toBe(200);
    const headers = raw.headers();
    const counted = Number(headers["x-citynexus-ics-events"]);
    const activities = Number(headers["x-citynexus-ics-activities"]);
    const noClock = Number(headers["x-citynexus-ics-skipped-no-clock"]);
    const noStamp = Number(headers["x-citynexus-ics-skipped-no-stamps"]);
    expect(activities, node(`activities ${activities} != events ${counted} + no-clock ${noClock} + no-stamp ${noStamp}`))
      .toBe(counted + noClock + noStamp);
    expect(counted, node("the file the traveller got and the door's count disagree")).toBe(events);

    // `evidencePath` makes its own parent directory, so the save needs no mkdir of its own.
    const saved = evidencePath(DIR, "exported.ics");
    writeFileSync(saved, bytes);
    await logged.page.screenshot({ path: evidencePath(DIR, "01_exported.png") });

    // The anonymous leg: same screen, no credential, so a refusal and no file.
    const anonDownloads: string[] = [];
    await pressExport(anon.page, { downloads: anonDownloads });
    const anonNotice = (await anon.page.getByTestId("calendar-export-notice").innerText()).trim();
    expect(anonNotice.includes("calendar."), node(`the refusal is a raw key: ${anonNotice}`)).toBe(false);
    expect(anonDownloads, node(`an unauthenticated tap wrote files: ${anonDownloads.join(",")}`))
      .toEqual([]);
    const door = await anon.page.evaluate(
      (path) => fetch(path).then((r) => ({ status: r.status, type: r.headers.get("content-type") })),
      CALENDAR(s.journeyId),
    );
    expect(door.status, node("the door answered an anonymous request with something other than a refusal"))
      .toBe(401);
    expect(String(door.type ?? "").includes("text/calendar"), node("a refusal arrived as a calendar"))
      .toBe(false);
    await anon.page.screenshot({ path: evidencePath(DIR, "02_refused.png") });

    const manifest = {
      order: "ORD-0496 slice 3 (.ics export)",
      spec: FILE,
      viewport: VIEWPORT,
      route: "/v8/trips",
      run: {
        id: process.env.CITYNEXUS_E2E_RUN_ID ?? "(unset)",
        authoritative: process.env.CITYNEXUS_E2E_AUTHORITATIVE === "1",
        backend_db: process.env.CITYNEXUS_DATABASE_URL ?? "(inherited)",
      },
      journeyId: s.journeyId,
      button_label: label.trim(),
      exported: {
        suggested_filename: download.suggestedFilename(),
        bytes: bytes.byteLength,
        sha256: createHash("sha256").update(bytes).digest("hex").slice(0, 16),
        vevents_counted_from_bytes: events,
        door_header_events: counted,
        door_header_activities: activities,
        door_header_skipped_no_clock: noClock,
        door_header_skipped_no_stamps: noStamp,
        notice: notice,
        file: relative(resolve(process.cwd(), ".."), saved).replace(/\\/g, "/"),
      },
      grammar: census,
      anonymous: {
        notice: anonNotice,
        downloads_written: anonDownloads.length,
        door_status: door.status,
      },
      shots: ["01_exported.png", "02_refused.png"],
      recordedAt: new Date().toISOString(),
    };
    writeFileSync(
      evidencePath(DIR, "manifest.json"),
      JSON.stringify(manifest, null, 2).replace(/\r\n/g, "\n"),
    );
    console.log(
      `[ord0496][glass] events=${events} bytes=${bytes.byteLength} door_events=${counted} ` +
        `activities=${activities} no_clock=${noClock} no_stamp=${noStamp} anon_downloads=${anonDownloads.length} ` +
        `crlf=${census.crlf_pairs} bare_lf=${census.bare_line_feeds} over75=${census.lines_over_75_octets} ` +
        `sha=${manifest.exported.sha256} run=${manifest.run.id}`,
    );
  } finally {
    await logged.close();
    await anon.close();
  }
});
