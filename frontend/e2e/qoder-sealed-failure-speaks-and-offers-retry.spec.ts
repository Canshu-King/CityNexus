/**
 * ORD-0273 — the sealed-demo failure speaks from an i18n key and offers a working next step.
 *
 * TEXT: the user sentence must equal the registered `trial.sealedUnreadable` dictionary value;
 * the raw error facts (message, error name, MIME shapes) live only in data-* on the alert element
 * and must never leak into the main copy.  The leak shapes are named precisely -- no wide regex.
 *
 * ACTION: the failure screen carries an executable next step -- 「重试」 bound to the same read.
 * The read is deadline-bounded by ORD-0263's READ_DEADLINE_MS, so a retry cannot open a second
 * unbounded wait (0273 cell 1's single-clock principle).
 */
import { expect, test, type Page } from "@playwright/test";
import { writeFileSync } from "node:fs";
import { evidencePath } from "./_qoderEvidence";

const FILE = "e2e/qoder-sealed-failure-speaks-and-offers-retry.spec.ts";
const node = (id: string, detail: string) => `${FILE} :: ${id} — ${detail}`;
const VIEWPORT = { width: 390, height: 844 };
test.use({ viewport: VIEWPORT, hasTouch: true });

/** The registered i18n value, held by this gate and never imported from the product file. */
const FROZEN_SENTENCE = "没读到封存演示的信息：服务器刚才答了，但答的内容我们用不了。这不是你填错了什么。";
/** The named leak shapes (commander's list): none of these may appear in the main copy. */
const LEAK_SHAPES = ["origin answered", "unusable body", "text/html", "text/plain", "Error", "TypeError"];

async function openWizardWithBrokenScene(page: Page) {
  const seeded = (await (await page.request.get("/api/v1/demo/scene")).json()) as {
    journey_id?: string;
  };
  const journeyId = String(seeded.journey_id ?? "");
  expect(journeyId.length, node("seed", "/api/v1/demo/scene returned no journey_id")).toBeGreaterThan(8);
  await page.addInitScript((id) => {
    if (localStorage.getItem("citynexus.storage-seeded") !== "1") {
      localStorage.clear();
      localStorage.setItem("citynexus.storage-seeded", "1");
    }
    localStorage.setItem("citynexus.locale", "zh-CN");
    localStorage.removeItem("citynexus.v8.journey_id");
  }, journeyId);
  /* The commander's 08:40 shape: the sealed-demo read answers 200 with an HTML body. */
  await page.route("**/api/v1/demo/scene*", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "text/html; charset=utf-8",
      body: "<!doctype html><html><body>spa fallback</body></html>",
    });
  });
  await page.goto("/v8", { waitUntil: "load" });
  await page.waitForTimeout(1_000);
  return journeyId;
}

test("ord0273-text-the-sentence-is-the-key-and-no-shape-leaks — 主文案是键值，不漏技术形状", async ({
  page,
}) => {
  test.setTimeout(180_000);
  await openWizardWithBrokenScene(page);
  await page.getByTestId("trial-tianjin-demo").click();

  const alert = page.getByTestId("trial-sealed-unavailable");
  await expect(alert, node("ord0273-text", "the failure alert never rendered")).toBeVisible({
    timeout: 15_000,
  });
  const sentence = (await alert.locator("p").innerText()).replace(/\s+/g, " ").trim();
  expect(
    sentence,
    node("ord0273-text", `the user sentence reads "${sentence}" -- it must equal the i18n value exactly`),
  ).toBe(FROZEN_SENTENCE);
  for (const shape of LEAK_SHAPES) {
    expect(
      sentence.toLowerCase().includes(shape.toLowerCase()),
      node("ord0273-text", `the leak shape "${shape}" reached the main copy`),
    ).toBe(false);
  }
  /* The technical facts stay diagnosable but out of the sentence: data-* on the same element. */
  const detail = await alert.evaluate((el) => ({
    errorName: el.getAttribute("data-error-name") ?? "",
    errorMessage: el.getAttribute("data-error-message") ?? "",
  }));
  expect(
    detail.errorMessage.length > 0,
    node("ord0273-text", "the technical detail vanished entirely -- telemetry lost its facts"),
  ).toBe(true);

  writeFileSync(
    evidencePath("ord0273-text-reading.json"),
    JSON.stringify({ generatedBy: "e345b9d6", node: "ord0273-text", sentence, detail, leakShapesChecked: LEAK_SHAPES }, null, 1),
  );
  await page.screenshot({
    path: evidencePath(`ui-overnight/ord0273-sealed-failure-${process.env.CITYNEXUS_E2E_RUN_ID ?? "dev"}.png`),
  });
});

test("ord0273-action-retry-is-a-real-executable-step — 失败屏带着能走的那一步", async ({ page }) => {
  test.setTimeout(180_000);
  await openWizardWithBrokenScene(page);
  await page.getByTestId("trial-tianjin-demo").click();
  const alert = page.getByTestId("trial-sealed-unavailable");
  await expect(alert).toBeVisible({ timeout: 15_000 });

  /* The retry CTA exists, is enabled, and re-runs the SAME read (which still answers the same broken
     body here) -- so the second attempt must land in the same named state, not a second unbounded
     wait: the single-clock principle holds on the retry path too. */
  const retry = page.getByTestId("trial-sealed-retry");
  await expect(retry, node("ord0273-action", "the retry CTA is missing")).toBeVisible({ timeout: 10_000 });
  await expect(retry).toBeEnabled();
  const secondAttempt = page.waitForTimeout(14_000).then(() => "settled");
  await retry.click();
  await expect(alert).toBeVisible({ timeout: 16_000 });
  const still = (await alert.locator("p").innerText()).replace(/\s+/g, " ").trim();
  expect(
    still,
    node("ord0273-action", `after the retry the screen reads "${still}" -- the named state must return, not hang`),
  ).toBe(FROZEN_SENTENCE);
  await secondAttempt;

  writeFileSync(
    evidencePath("ord0273-action-reading.json"),
    JSON.stringify(
      {
        generatedBy: "e345b9d6",
        node: "ord0273-action",
        retryLabel: (await retry.innerText()).trim(),
        afterRetrySentence: still,
        note: "retry re-enters the same deadline-bounded read; the named failure state returns, no second clock",
      },
      null,
      1,
    ),
  );
});
