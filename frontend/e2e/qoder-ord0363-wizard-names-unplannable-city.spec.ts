import { expect, test, type Page } from "@playwright/test";
import { openScreen } from "./_qoderShellSeed";
import { evidencePath } from "./_qoderEvidence";
import { writeFileSync } from "node:fs";

/**
 * ORD-0363 -- the wizard must not let a traveller select a city the server cannot answer and then
 * surface that as a "network unavailable"-shaped failure.
 *
 * The "See supported destinations" panel already groups by the server's answer (ORD-0346), but the
 * destination *field* still only consults the client-side spelling table, so 东京 / 福州 / 新加坡 --
 * names the table knows but `GET /destinations/capability` answers with `NO_CANONICAL_IDENTITY` --
 * looked plannable: a neutral "已自动设置", an advance, and an empty plan that read like an outage.
 *
 * The capability route is stubbed here rather than taken from a live seed, so the state under test
 * ("what the server said about THIS name") is deterministic and does not depend on which city the
 * shared demo DB happens to hold rows for right now. Two directions are asserted:
 *
 *   arm 1 -- an unanswerable, table-recognised name is NAMED with the server's frozen verdict and
 *            blocked at the Next button, and the words are NOT "network".
 *   arm 2 -- a read that never lands is NOT laundered into "this destination cannot be planned"
 *            (Q64/Q71); it must not claim NO_CANONICAL_IDENTITY or block as if the server answered.
 *
 * The banned token `NOT_ANSWERED` (struck by the arbiter on choose B -- see anywhere_capability.py)
 * must not appear on any surface; the arms assert its absence as well.
 */

const FILE = "e2e/qoder-ord0363-wizard-names-unplannable-city.spec.ts";
const node = (id: string, detail: string) => `${FILE} :: ${id} — ${detail}`;

function capabilityPayload(query: string) {
  if (query === "东京") {
    return {
      query,
      capability: "UNAVAILABLE",
      reason_code: "NO_CANONICAL_IDENTITY",
      recommended_action: "CHOOSE_ANOTHER_DESTINATION",
      destination_state: "UNAVAILABLE",
      destination_resolution: "NO_MATCH",
      retryable: false,
      canonical_destination_id: null,
      place_count: 0,
      missing_categories: [],
      candidates: [],
    };
  }
  // positive control: a name the server can plan with (identity + material).
  return {
    query,
    capability: "HYDRATABLE",
    reason_code: "COVERAGE_INCOMPLETE",
    recommended_action: "START_HYDRATION",
    destination_state: "HYDRATABLE",
    destination_resolution: "RESOLVED",
    retryable: false,
    canonical_destination_id: "CN-BEIJING",
    place_count: 14,
    missing_categories: ["mobility"],
    candidates: [],
  };
}

/** Route the capability endpoint so each offered name returns a controlled answer. */
async function stubCapability(page: Page, mode: "answers" | "abort") {
  await page.route("**/api/v1/destinations/capability*", (route) => {
    if (mode === "abort") return route.abort();
    const raw = new URL(route.request().url()).searchParams.get("query") ?? "";
    let name = raw;
    try {
      name = decodeURIComponent(raw);
    } catch {
      /* use raw */
    }
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(capabilityPayload(name)),
    });
  });
}

async function openWizardStep1(page: Page) {
  await page.emulateMedia({ colorScheme: "light", media: "screen" });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.addInitScript(() => {
    localStorage.clear();
    localStorage.setItem("citynexus.locale", "zh-CN");
  });
  await openScreen(page, "/v8", ["trial-setup"]);
}

test.describe("ORD-0363 the wizard names an unanswerable city instead of a fake outage", () => {
  test("arm1-unanswerable-named-and-blocked-not-network", async ({ page }) => {
    test.setTimeout(200_000);
    await stubCapability(page, "answers");
    await openWizardStep1(page);
    await page.getByTestId("trial-city").fill("东京");
    await expect(page.getByTestId("trial-next")).toBeVisible();

    const caution = page.getByTestId("trial-city-unservable");
    await expect(caution, node("arm1", "no named caution appeared for a server-unnamed city")).toBeVisible({
      timeout: 20_000,
    });
    const text = (await caution.innerText()).replace(/\s+/g, " ");
    // the server's own frozen fields are spoken, verbatim.
    expect(text, node("arm1", `caution text: ${JSON.stringify(text)}`)).toContain("NO_CANONICAL_IDENTITY");
    expect(text, node("arm1", `caution text: ${JSON.stringify(text)}`)).toContain("还没有身份");
    // the cover the traveller must never be handed, and the token that was struck, are absent.
    expect(text, node("arm1", "a can't-plan city was explained as a network outage")).not.toMatch(/网络|network|网络不可用|network unavailable/i);
    expect(text, node("arm1", "the struck invented token reappeared")).not.toContain("NOT_ANSWERED");

    // the Next button refuses to advance on this city -- present, not missing.
    await expect(page.getByTestId("trial-next"), node("arm1", "Next still enabled for an unanswerable city")).toHaveAttribute(
      "aria-disabled",
      "true",
    );

    // positive control: a plannable name is NOT blocked and NOT warned about.
    await page.getByTestId("trial-city").fill("北京");
    await expect(page.getByTestId("trial-city-unservable")).toHaveCount(0, { timeout: 20_000 });
    await expect(page.getByTestId("trial-next")).not.toHaveAttribute("aria-disabled", "true");

    writeFileSync(
      evidencePath("ord0363/arm1-unservable-named.json"),
      JSON.stringify({ generatedBy: "S3-stateboard", order: "ORD-0363", arm: "arm1", text }, null, 1) + "\n",
      "utf-8",
    );
  });

  test("arm2-failed-read-is-not-laundered-into-a-server-verdict", async ({ page }) => {
    test.setTimeout(200_000);
    await stubCapability(page, "abort"); // the device gets nothing
    await openWizardStep1(page);
    await page.getByTestId("trial-city").fill("东京");
    await expect(page.getByTestId("trial-next")).toBeVisible();
    await page.waitForTimeout(3_000);

    // A read that never landed must NOT be reported as "this destination cannot be planned".
    await expect(
      page.getByTestId("trial-city-unservable"),
      node("arm2", "a failed read was laundered into a server unanswerable verdict"),
    ).toHaveCount(0);
    // so the traveller is not blocked as if the server had spoken.
    await expect(
      page.getByTestId("trial-next"),
      node("arm2", "a failed read blocked advance like a server verdict"),
    ).not.toHaveAttribute("aria-disabled", "true");
    // and nothing on the step claims the frozen no-identity reason it never received.
    const body = (await page.getByTestId("trial-step1-body").innerText()).replace(/\s+/g, " ");
    expect(body, node("arm2", "a network-only failure was written up as NO_CANONICAL_IDENTITY")).not.toContain("NO_CANONICAL_IDENTITY");
    expect(body, node("arm2", "the struck token appeared on a failed read")).not.toContain("NOT_ANSWERED");

    writeFileSync(
      evidencePath("ord0363/arm2-failed-read.json"),
      JSON.stringify({ generatedBy: "S3-stateboard", order: "ORD-0363", arm: "arm2", body }, null, 1) + "\n",
      "utf-8",
    );
  });
});
