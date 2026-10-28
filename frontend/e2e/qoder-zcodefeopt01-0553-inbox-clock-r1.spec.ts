/**
 * ORD-0553-r2 -- JourneyInboxWorkbench datetime-local pair (scheduled_departure_at /
 * scheduled_arrival_at).  The conversion policy under test (frontend/src/lib/inboxScheduleClock.ts):
 * the input speaks the traveller device's local wall clock, the stored schedule keeps the
 * offset the server stamped on it, and a save converts back through the instant.
 *
 * Two arms on the real stack, same stored instants, different devices:
 *  zh + Asia/Shanghai (the zone the stored values carry) -- the inputs must show the same
 *    digits the pre-fix editor showed, byte for byte;
 *  en + UTC (a foreign device) -- the same instant must read as the UTC wall clock, which the
 *    pre-fix code got wrong by relabelling the stored wall as local.
 *
 * Mount and intake follow e2e/qoder-inbox-review-queue.spec.ts: the workbench's draft panel
 * renders the draft the same mount created, so the reservation is imported through the
 * structured-JSON aside with destination omitted (the server calls it critical, so the draft
 * stays pending and its corrections form stays editable).
 */
import { expect, test, type Page } from "@playwright/test";
import { writeFileSync } from "node:fs";
import { evidencePath } from "./_qoderEvidence";

const FILE = "e2e/qoder-zcodefeopt01-0553-inbox-clock-r1.spec.ts";
const node = (id: string, detail: string) => `${FILE} :: ${id} — ${detail}`;

const VIEWPORT = { width: 390, height: 844 };
const STORED_DEPARTURE = "2026-10-09T18:00:00+08:00";
const STORED_ARRIVAL = "2026-10-10T09:30:00+08:00";

type Draft = { id: string; status: string; extracted?: Record<string, unknown> };

async function readScene(page: Page): Promise<Record<string, string | null>> {
  const response = await page.request.get("/api/v1/demo/scene");
  return (await response.json()) as Record<string, string | null>;
}

async function openBookings(page: Page, journeyId: string, locale: string): Promise<void> {
  await page.addInitScript(
    ([id, loc]) => {
      localStorage.clear();
      localStorage.setItem("citynexus.v8.journey_id", String(id));
      localStorage.setItem("citynexus.locale", String(loc));
    },
    [journeyId, locale],
  );
  await page.goto("/v8/bookings", { waitUntil: "load" });
  await expect(page.getByTestId("v13-2-memory")).toBeVisible({ timeout: 30_000 });
}

async function importPendingDraft(page: Page, reference: string): Promise<void> {
  await page.getByTestId("bookings-advanced").locator("summary").click();
  await page.getByTestId("bookings-json-input").fill(
    JSON.stringify({
      reservation_type: "RAIL",
      title: "天津西 → 北京南 高铁",
      confirmation_ref: reference,
      origin: "天津西",
      /* destination deliberately omitted -- the server calls it critical, so the draft lands
         pending and the corrections form below keeps its editable inputs. */
      scheduled_departure_at: STORED_DEPARTURE,
      scheduled_arrival_at: STORED_ARRIVAL,
      amount_minor: 55300,
      currency: "CNY",
      provider_key: "e2e-ord0553-r2",
    }),
  );
  await page.getByRole("button", { name: /审核并保护|Review and protect/ }).click();
}

async function findDraft(page: Page, journeyId: string, reference: string): Promise<Draft> {
  const deadline = Date.now() + 20_000;
  while (Date.now() < deadline) {
    const response = await page.request.get(`/api/v1/journeys/${journeyId}/inbox`);
    const body = (await response.json()) as { drafts?: Draft[] };
    const mine = (body.drafts ?? []).find(
      (item) => String(item.extracted?.confirmation_ref ?? "") === reference,
    );
    if (mine) return mine;
    await page.waitForTimeout(1000);
  }
  throw new Error(node("findDraft", `no draft with confirmation_ref ${reference} appeared in the inbox within 20s`));
}

for (const arm of [
  { id: "zh-shanghai", locale: "zh-CN", timezoneId: "Asia/Shanghai", departure: "2026-10-09T18:00", arrival: "2026-10-10T09:30" },
  { id: "en-utc", locale: "en-US", timezoneId: "UTC", departure: "2026-10-09T10:00", arrival: "2026-10-10T01:30" },
] as const) {
  test.describe(`ord0553-r2 inbox clock ${arm.id}`, () => {
    test.use({ viewport: VIEWPORT, hasTouch: true, timezoneId: arm.timezoneId });

    test(`the datetime-local pair reads the traveller's own wall clock (${arm.id})`, async ({ page }) => {
      test.setTimeout(300_000);
      const NODE = `inbox-clock-${arm.id}`;
      const seeded = await readScene(page);
      const journeyId = String(seeded.journey_id ?? "");
      const reference = `R0553ZC-${arm.id.toUpperCase()}-${Math.floor(Math.random() * 1e6).toString().padStart(6, "0")}`;

      await openBookings(page, journeyId, arm.locale);
      await importPendingDraft(page, reference);
      const mine = await findDraft(page, journeyId, reference);
      /* The corrections form renders only for the draft the reviewer opened from the queue
         (JourneyInboxWorkbench renders `v13-2-review` under the draft that `inbox-open-review`
         set), so the reading arm opens my own row rather than assuming the mount preselected it. */
      const row = page.locator('[data-testid="inbox-pending-row"]', { hasText: reference });
      await expect(row, node(NODE, "the queue did not show my draft's row after the import")).toHaveCount(1, { timeout: 20_000 });
      await row.getByTestId("inbox-open-review").click();
      const evidence: Record<string, unknown> = {
        node: NODE,
        stored: { departure: STORED_DEPARTURE, arrival: STORED_ARRIVAL },
        draft: { id: mine.id, status: mine.status },
        device: { locale: arm.locale, timezoneId: arm.timezoneId },
      };

      const inputs = page.locator('[data-testid="v13-2-review"] input[type="datetime-local"]');
      await expect(inputs, node(NODE, "the corrections form did not render its two datetime-local inputs after the import")).toHaveCount(2, { timeout: 20_000 });
      const gotDeparture = await inputs.nth(0).inputValue();
      const gotArrival = await inputs.nth(1).inputValue();
      evidence.read = { departure: gotDeparture, arrival: gotArrival };
      evidence.labels = {
        departure: (await inputs.nth(0).locator("xpath=ancestor::label").textContent()) ?? "",
        arrival: (await inputs.nth(1).locator("xpath=ancestor::label").textContent()) ?? "",
      };

      expect(gotDeparture, node(NODE, `departure input read ${gotDeparture}; the stored instant ${STORED_DEPARTURE} on a ${arm.timezoneId} device must show ${arm.departure}`)).toBe(arm.departure);
      expect(gotArrival, node(NODE, `arrival input read ${gotArrival}; the stored instant ${STORED_ARRIVAL} on a ${arm.timezoneId} device must show ${arm.arrival}`)).toBe(arm.arrival);

      writeFileSync(evidencePath("ord0553", `r0553_inbox_clock_${arm.id}.json`), JSON.stringify(evidence, null, 2));
    });
  });
}
