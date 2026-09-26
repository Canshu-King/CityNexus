import { expect, test, type Page, type Route } from "@playwright/test";

/**
 * ORD-0363-r1 -- the headline 「（服务器给的原因编号：X）」 must wear the "服务器给的" attribution
 * ONLY when X actually arrived in the server's refusal envelope.  When this screen synthesises the
 * code itself (it counted `GET /places`, got too few, and wrote `BLOCKED:CATALOG_EMPTY`), the same
 * code is a THIS-DEVICE reading and must not be labelled a server verdict.  The judgement now shares
 * one predicate with the Q70 `data-cnx-field` anchor (PlanWithAiSheet `statusCopy(..., serverBacked)`
 * and `reasonAnchor`), so the sentence and its anchor can never disagree.
 *
 * Two directions, each an arm; the two mutates named in the order are the negative controls:
 *   mutate A "drop the server code, always let the client claim 服务器给的"  -> arm_device reddens.
 *   mutate B "hang data-cnx-field on a code the server never sent"           -> arm_device reddens.
 *
 * The sheet is driven exactly the way ORD-0280 drives it (hub -> plan-with-ai -> ask), with the
 * `/places` and `/plans/generate` legs stubbed so "what the server said" is deterministic and never
 * depends on the shared demo DB's current rows. No write endpoint is added; nothing is mocked into
 * existence -- the server codes used here (CATALOG_INSUFFICIENT) are the ones `services.py` already
 * returns on a real refusal.
 */

const NODE = "e2e/qoder-ord0363r1-headline-attribution-is-servers.spec.ts";
const USER_SENTENCE = "帮我排一天";

const json = (status: number, body: unknown) => ({
  status,
  contentType: "application/json",
  body: JSON.stringify(body),
});

async function bootAndAsk(
  page: Page,
  arms: { places: unknown[]; generateRefusal?: { status: number; body: unknown } },
) {
  const sceneRes = await page.request.get("/api/v1/demo/scene");
  const scene = (await sceneRes.json()) as { journey_id?: string };
  const journeyId = String(scene.journey_id ?? "");
  expect(journeyId.length > 0, `${NODE}: stage named no journey`).toBe(true);
  await page.addInitScript((id) => {
    localStorage.clear();
    localStorage.setItem("citynexus.v8.journey_id", id as string);
    localStorage.setItem("citynexus.locale", "zh-CN");
  }, journeyId);
  await page.setViewportSize({ width: 390, height: 844 });

  await page.route("**/api/v1/journeys/*/plans", async (r: Route) => {
    if (r.request().method() !== "GET") return r.fallback();
    await r.fulfill(json(200, [])); // KNOWN-and-empty baseline, else the fallback branch never runs
  });
  await page.route("**/api/v1/places**", async (r: Route) => {
    if (r.request().method() !== "GET") return r.fallback();
    await r.fulfill(json(200, arms.places));
  });
  await page.route("**/api/v1/journeys/*/plans/generate", async (r: Route) => {
    if (r.request().method() !== "POST") return r.fallback();
    if (arms.generateRefusal) {
      await r.fulfill(json(arms.generateRefusal.status, arms.generateRefusal.body));
    } else {
      await r.fulfill(json(200, []));
    }
  });

  await page.goto("/v8/hub", { waitUntil: "load" });
  await expect(page.getByTestId("today-hero"), `${NODE}: hub never rendered`).toBeVisible({
    timeout: 30_000,
  });
  await page.getByTestId("hub-plan-with-ai").click();
  await expect(page.getByTestId("plan-ai-sheet"), `${NODE}: sheet never opened`).toBeVisible({
    timeout: 15_000,
  });
  await page.getByTestId("plan-ai-input").fill(USER_SENTENCE);
  await page.getByTestId("plan-ai-submit").click();
  const result = page.getByTestId("plan-ai-result");
  await expect(result, `${NODE}: the sheet never answered`).toBeVisible({ timeout: 120_000 });

  const headline = page.getByTestId("plan-ai-headline");
  await expect(headline, `${NODE}: no headline line`).toBeVisible();
  return {
    status: (await result.getAttribute("data-result-status")) ?? "",
    text: (await headline.innerText()).replace(/\s+/g, " "),
    cnxField: (await headline.getAttribute("data-cnx-field")) ?? null,
    cnxValue: (await headline.getAttribute("data-cnx-value")) ?? null,
  };
}

test.describe("ORD-0363-r1 headline attribution follows the server envelope, not the client's count", () => {
  test("arm_server: a code the server really sent may say 服务器给的 and carries the anchor", async ({ page }) => {
    test.setTimeout(240_000);
    // >=2 places clears the client's pre-count, so the only way to BLOCK is the server's refusal.
    const out = await bootAndAsk(page, {
      places: [{ id: "p1" }, { id: "p2" }],
      generateRefusal: {
        status: 422,
        body: { reason_code: "CATALOG_INSUFFICIENT", message: "too few places for a day" },
      },
    });
    expect(out.status, JSON.stringify(out)).toBe("BLOCKED:CATALOG_INSUFFICIENT");
    expect(out.text, JSON.stringify(out)).toContain("服务器给的原因编号");
    expect(out.text, JSON.stringify(out)).toContain("CATALOG_INSUFFICIENT");
    // the Q70 anchor names the real envelope field, matching the sentence.
    expect(out.cnxField, JSON.stringify(out)).toBe("reason_code");
    expect(out.cnxValue, JSON.stringify(out)).toBe("CATALOG_INSUFFICIENT");
  });

  test("arm_device: a code this screen counted itself must NOT claim 服务器给的 and gets no anchor", async ({ page }) => {
    test.setTimeout(240_000);
    // GET /places -> 0 rows: the client synthesises BLOCKED:CATALOG_EMPTY (a device reading).
    const out = await bootAndAsk(page, { places: [] });
    expect(out.status, JSON.stringify(out)).toBe("BLOCKED:CATALOG_EMPTY");
    expect(out.text, JSON.stringify(out)).not.toContain("服务器给的原因编号");
    expect(out.text, JSON.stringify(out)).not.toContain("server reason code");
    expect(out.text, JSON.stringify(out)).toContain("这台设备");
    // no server field backs it, so no data-cnx-field anchor (mutate B would wrongly add one).
    expect(out.cnxField, JSON.stringify(out)).toBeNull();
    expect(out.cnxValue, JSON.stringify(out)).toBeNull();
  });
});
