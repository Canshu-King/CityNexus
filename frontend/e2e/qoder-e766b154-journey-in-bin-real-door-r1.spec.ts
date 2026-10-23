/**
 * lane e766b154 -- can the traveller actually be shown the 回收站 sentence? The real door, no instrument.
 *
 * The order I took from my own self-declaration (ledger CMDR 00:5x asked for the remaining sentences to
 * be read through the real door): `journeyInBin` is the one of the six still-instrumented rows whose
 * refusal the backend can genuinely produce -- a trip that is in the recycle bin. So this file does what
 * a traveller does to get there: it asks the product's own DELETE door to withdraw the demo trip from
 * THIS LANE's private store, opens the itinerary screen, taps 打卡, and reads what the door answers and
 * what the glass shows. Then it asks the product's own undelete door to put it back and proves the store
 * is as it was.
 *
 * Two outcomes are both readings, and neither is fudged:
 *   REACHED  -- the control mounted, the tap happened, the door answered 409 with the named code, and
 *               the sentence is on the glass;
 *   NOT_REACHABLE_BY_UI -- the shell cannot even load a withdrawn trip, so no control exists to tap. That
 *               is a fact about the entry path, and it explains why this row stayed instrument-only.
 *
 * Writes: exactly two doors on this lane's own sqlite file (DELETE then undelete). The commander's
 * :4783/:4787/:4789 and the shared :8000/:4781/:4782/:8693 are refused by name in the config.
 */
import { expect, test } from "@playwright/test";
import * as fs from "fs";
import * as path from "path";
import { scanScreenText } from "./_qoderTextScan";
import { CHECKIN_COPY } from "../src/features/checkin/checkinCopy";

const FILE = "e2e/qoder-e766b154-journey-in-bin-real-door-r1.spec.ts";
const node = (id: string, detail: string) => `${FILE} :: ${id} — ${detail}`;
const OUT = process.env.CITYNEXUS_E766_BIN_OUT || "";
const BASE = process.env.CITYNEXUS_E766_BIN_BASE || "";
const JOURNEY = process.env.CITYNEXUS_E766_BIN_JOURNEY || "";

const BUTTON = { "zh-CN": "打卡", en: "Check in" } as Record<string, string>;
const UUID = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i;

test.use({ viewport: { width: 390, height: 844 }, hasTouch: true });

function write(name: string, body: Record<string, unknown>) {
  if (!OUT) return;
  fs.mkdirSync(OUT, { recursive: true });
  fs.writeFileSync(path.join(OUT, `${name}.json`), JSON.stringify(body, null, 1), "utf8");
}

async function shot(page: import("@playwright/test").Page, name: string) {
  if (!OUT) return;
  fs.mkdirSync(OUT, { recursive: true });
  await page.screenshot({ path: path.join(OUT, `${name}.png`) });
}

async function doorState(page: import("@playwright/test").Page, journeyId: string) {
  const one = await page.request.get(`${BASE}/api/v1/journeys/${journeyId}`);
  const list = await page.request.get(`${BASE}/api/v1/recycle-bin/journeys`);
  const rows = (await list.json().catch(() => [])) as { id?: string }[];
  return {
    read_journey_status: one.status(),
    recycle_bin_status: list.status(),
    recycle_bin_rows: Array.isArray(rows) ? rows.length : -1,
    journey_in_bin: Array.isArray(rows) && rows.some((r) => r.id === journeyId),
  };
}

for (const locale of ["zh-CN", "en"]) {
  test(`b-${locale} — 真门把行程收进回收站后，这一屏还按得到打卡吗`, async ({ page }) => {
    test.setTimeout(180_000);
    const before = await doorState(page, JOURNEY);

    const withdrawn = await page.request.delete(`${BASE}/api/v1/journeys/${JOURNEY}`);
    const afterDelete = await doorState(page, JOURNEY);

    await page.addInitScript((arg) => {
      window.localStorage.clear();
      window.localStorage.setItem("citynexus.v8.journey_id", arg.id);
      window.localStorage.setItem("citynexus.locale", arg.locale);
    }, { id: JOURNEY, locale });
    await page.goto(`${BASE}/v8/trips`, { waitUntil: "load" });
    await page.waitForTimeout(4_000);

    const screen = await page.evaluate(() => {
      const strip = (x: string | null | undefined) => String(x || "").replace(/\s+/g, " ").trim();
      const rows = Array.from(document.querySelectorAll("[data-testid='trip-stop']")).map((row) => ({
        stop: strip(row.querySelector(".trip-stop-body b")?.textContent),
        control: strip(row.querySelector("[data-testid='stop-checkin']")?.textContent),
      }));
      return {
        href: location.href,
        stops: rows.length,
        controls: rows.filter((r) => r.control).length,
        body_head: strip(document.body.innerText).slice(0, 160),
      };
    });
    const scan = await scanScreenText(page);

    let tapped: { stop: string; control: string } | null = null;
    let painted: string | null = null;
    let notices = 0;
    let door: { status: number; reason_code: string | null; message: string | null } | null = null;
    if (screen.controls > 0) {
      const fresh = await page.evaluate((word) => {
        const strip = (x: string | null | undefined) => String(x || "").replace(/\s+/g, " ").trim();
        return Array.from(document.querySelectorAll("[data-testid='trip-stop']"))
          .map((row) => ({
            stop: strip(row.querySelector(".trip-stop-body b")?.textContent),
            control: strip(row.querySelector("[data-testid='stop-checkin']")?.textContent),
          }))
          .filter((r) => r.control === word);
      }, BUTTON[locale]);
      if (fresh && fresh.length) {
        tapped = fresh[0];
        page.once("response", () => undefined);
        const control = page.locator("[data-testid='trip-stop']").filter({ hasText: tapped.stop })
          .locator("[data-testid='stop-checkin']");
        const answered = page.waitForResponse(
          (r) => r.url().includes("/checkins") && r.request().method() === "POST", { timeout: 20_000 });
        await control.scrollIntoViewIfNeeded();
        await control.click();
        const response = await answered;
        let parsed: { error?: { reason_code?: string; message?: string } } = {};
        try { parsed = await response.json(); } catch { parsed = {}; }
        door = { status: response.status(), reason_code: parsed.error?.reason_code ?? null,
          message: parsed.error?.message ?? null };
        await page.waitForTimeout(3_000);
        const rows = await page.evaluate(() => {
          const strip = (x: string | null | undefined) => String(x || "").replace(/\s+/g, " ").trim();
          return Array.from(document.querySelectorAll("[data-testid='trip-stop']")).map((row) => ({
            stop: strip(row.querySelector(".trip-stop-body b")?.textContent),
            notice: strip(row.querySelector("[data-testid='stop-checkin-notice']")?.textContent) || null,
          }));
        });
        const withNotice = rows.filter((r) => r.notice);
        notices = withNotice.length;
        painted = withNotice.length === 1 ? String(withNotice[0].notice) : null;
      }
    }

    /* Put it back through the product's own door, then prove the store is as it was. */
    const restored = await page.request.post(`${BASE}/api/v1/journeys/${JOURNEY}/undelete`);
    const afterRestore = await doorState(page, JOURNEY);

    const expected = locale === "zh-CN" ? CHECKIN_COPY.journeyInBin.zh : CHECKIN_COPY.journeyInBin.en;
    const reached = painted !== null;
    const reading = {
      file: FILE, locale, base: BASE, viewport: "390x844", journey_id: JOURNEY,
      door_before_delete: before, delete_door_status: withdrawn.status(), door_after_delete: afterDelete,
      screen: { ...screen, painted_leaves: scan.visualLeaves },
      tapped_stop: tapped ? tapped.stop : null,
      post_answer: door, notices_count: notices, painted_notice: painted,
      expected_from_table: expected,
      verdict: reached ? "REACHED" : (screen.controls === 0 ? "NOT_REACHABLE_BY_UI" : "REACHED_BUT_NO_NOTICE"),
      undelete_door_status: restored.status(), door_after_restore: afterRestore,
      checks: {
        withdraw_accepted_by_product_door: withdrawn.status() === 204,
        trip_is_in_the_bin_after_withdrawal: afterDelete.journey_in_bin === true,
        read_door_refuses_the_withdrawn_trip: afterDelete.read_journey_status !== 200,
        sentence_painted_equals_the_tables_own_row: painted === expected,
        exactly_one_notice_on_the_whole_screen: notices === 1,
        no_uuid_reached_the_travellers_sentence: painted !== null && !UUID.test(painted),
        restored_by_product_door: restored.status() === 200,
        bin_is_empty_again_after_restore: afterRestore.journey_in_bin === false
          && afterRestore.read_journey_status === 200,
      },
      taken_at: new Date().toISOString(),
    };
    write(`b-${locale}`, reading);
    await shot(page, `b-${locale}`);

    expect(reading.checks.withdraw_accepted_by_product_door,
      node(`b-${locale}`, "the product's own DELETE door did not withdraw the trip")).toBe(true);
    expect(reading.checks.trip_is_in_the_bin_after_withdrawal,
      node(`b-${locale}`, "the recycle-bin door does not list the withdrawn trip")).toBe(true);
    expect(reading.checks.restored_by_product_door,
      node(`b-${locale}`, "the product's own undelete door refused")).toBe(true);
    expect(reading.checks.bin_is_empty_again_after_restore,
      node(`b-${locale}`, "the trip was NOT put back -- this lane leaves no side effects")).toBe(true);
    if (reached) {
      expect(reading.checks.sentence_painted_equals_the_tables_own_row,
        node(`b-${locale}`, `painted=${String(painted)}`)).toBe(true);
      expect(reading.checks.no_uuid_reached_the_travellers_sentence,
        node(`b-${locale}`, "an identifier reached the sentence")).toBe(true);
    } else {
      expect(screen.controls, node(`b-${locale}`,
        `the screen mounted ${screen.controls} controls but no refusal was painted; body head: `
        + `${screen.body_head}`)).toBe(0);
    }
  });
}
