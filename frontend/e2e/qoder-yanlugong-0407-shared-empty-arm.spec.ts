/* ORD-0555 family / 空态缺动作单 (lane 验路工, ORD-0407 direction).
 *
 * What this measures: the "read answered, the server named a plan, that plan has no stops"
 * arm of the share-receiving screen (`SharedJourneyPanel.tsx`, arm opened at line 278 on the
 * tip this lane cut its branch from). The order asks whether that arm is silent. It is not:
 * it carries two sentences, and the refresh action that this same file already offers on the
 * other arms is rendered inside the same success branch at line 327, below the notice.
 *
 * The empty state is manufactured at the transport layer, deliberately and in one place: the
 * door is answered with the shape the real door answers with (the key list this lane read off
 * `GET /api/v1/shared/journeys/{token}` on the same line) and only `active_plan.stops` is set
 * to the empty array. Everything else on the page comes from the real running product.
 */

import { expect, test } from "@playwright/test";

const TOKEN = "ord0407-yanlugong-fixture-token";
const DOOR = /\/api\/v1\/shared\/journeys\/ord0407-yanlugong-fixture-token/;

const EMPTY_STOPS_ANSWER = {
  id: "22222222-2222-4222-8222-222222222222",
  traveler_id: "11111111-1111-4111-8111-111111111111",
  title: "ORD-0407 empty-stop arm",
  city_code: "CNX-DEMO",
  status: "PLANNED",
  planning_mode: "balanced",
  start_at: "2026-10-10T00:00:00+08:00",
  end_at: "2026-10-12T00:00:00+08:00",
  timezone: "Asia/Shanghai",
  timezone_honoured: true,
  budget: null,
  live_view: null,
  current_activity_id: null,
  aborted_at: null,
  abort_reason: null,
  active_plan_version_id: "55555555-5555-4555-8555-555555555555",
  grant_scope: "JOURNEY",
  plan_state: "PLAN_PRESENT",
  active_plan: {
    id: "55555555-5555-4555-8555-555555555555",
    version_no: 1,
    source: "INITIAL",
    stops: [],
  },
};

test("the zero-stop arm speaks, and offers the action this file already owns", async ({ page }) => {
  let asks = 0;
  await page.route(DOOR, (route) => {
    asks += 1;
    void route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(EMPTY_STOPS_ANSWER) });
  });

  await page.goto(`/v8/shared/${TOKEN}`, { waitUntil: "load" });

  const notice = page.getByTestId("shared-plan-empty");
  await expect(notice).toBeVisible();
  await expect(page.getByTestId("shared-plan-line")).toBeVisible();

  const refresh = page.getByTestId("shared-refresh");
  await expect(refresh).toHaveCount(1);
  await expect(refresh).toBeVisible();
  await expect(refresh).toBeEnabled();

  const reads: Record<string, string> = {};
  const capture = async (label: string) => {
    reads[label] = [
      (await notice.locator("b").first().innerText()).trim(),
      (await notice.locator("p").first().innerText()).trim(),
      (await refresh.innerText()).trim(),
    ].join(" || ");
  };

  const firstLocale = await page.evaluate(() => localStorage.getItem("citynexus.locale") ?? "unset");
  await capture(firstLocale);
  await page.getByTestId("shared-language").click();
  await page.waitForTimeout(400);
  const secondLocale = await page.evaluate(() => localStorage.getItem("citynexus.locale") ?? "unset");
  await capture(secondLocale);

  const asksBeforeTap = asks;
  await refresh.click();
  await page.waitForTimeout(600);
  expect(asks, "the action must really re-read the door").toBeGreaterThan(asksBeforeTap);

  await page.screenshot({ path: "test-results/ord0407-shared-empty-arm.png", fullPage: true });
  // The two-language reading the order asks for, printed on the runner's stdout.
  console.log("ORD0407_EMPTY_ARM_READING", JSON.stringify({ locales: [firstLocale, secondLocale], reads }));
});
