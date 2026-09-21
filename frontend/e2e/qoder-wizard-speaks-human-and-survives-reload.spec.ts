/**
 * ORD-0135 (high) -- the create-a-trip wizard has to survive a refresh, speak the traveller's
 * language on the confirmation step, and turn "还需要填写" into a route rather than a diagnosis.
 *
 * Three nodes, all at 390x844 with touch on the production build, because that is the phone the
 * order was written from:
 *  N1 fill to step 3, refresh, and the traveller must still be on step 3 with her own values;
 *  N2 the confirmation step may print no internal key -- `relaxed`, `balanced`, `packed`,
 *     `food`, `culture` are this product's vocabulary, not hers (the leak measured at
 *     `JourneyTrialSetup.tsx:854`, which printed `draft.pace` straight out; the option table with
 *     轻松/适中/紧凑 already existed 600 lines above it).  Note the third key is `packed`, not the
 *     `strict` named in the order -- corrected against the file, not assumed;
 *  N3 with the step blocked, every named missing field has to be a control that moves focus to
 *     that field.  A sentence that says "抵达地点" is a diagnosis; the traveller still has to find
 *     the box on a 390px screen.
 */
import { expect, test, type Page } from "@playwright/test";
import { writeFileSync } from "node:fs";
import { evidencePath } from "./_qoderEvidence";

const FILE = "e2e/qoder-wizard-speaks-human-and-survives-reload.spec.ts";
const node = (id: string, detail: string) => `${FILE} :: ${id} — ${detail}`;

const VIEWPORT = { width: 390, height: 844 };

test.use({ viewport: VIEWPORT, hasTouch: true });

/** Internal tokens that must never reach the traveller's screen. */
const LEAKS = [
  "relaxed",
  "balanced",
  "packed",
  "strict",
  "food",
  "nature",
  "culture",
  "seaside",
  "shopping",
  "family",
];

async function openWizard(page: Page): Promise<void> {
  /* The seeded storageState carries `citynexus.v8.journey_id`, which would open Today instead of the
     wizard.  Replayed on every navigation on purpose: node 1 refreshes mid-form and must still be
     journey-less when it comes back, or it would be measured against a loaded trip. */
  await page.addInitScript(() => {
    localStorage.removeItem("citynexus.v8.journey_id");
    localStorage.setItem("citynexus.locale", "zh-CN");
  });
  await page.goto("/v8/hub", { waitUntil: "load" });
  await expect(page.getByTestId("trial-setup")).toBeVisible({ timeout: 30_000 });
}

async function fillStep1(page: Page): Promise<void> {
  await page.getByTestId("trial-city").fill("天津");
  await page.getByTestId("trial-arrival").fill("天津站");
  await page.getByTestId("trial-departure").fill("北京南站");
  await page.getByTestId("trial-next").click();
  await expect(page.getByTestId("trial-step2-body")).toBeVisible({ timeout: 20_000 });
}

async function fillStep2(page: Page): Promise<void> {
  await page.getByTestId("trial-party").fill("2");
  await page.getByTestId("trial-budget").fill("1200");
  const interest = page.getByTestId("trial-interest-food");
  if (await interest.count()) await interest.click();
  await page.getByTestId("trial-next").click();
  await expect(page.getByTestId("trial-step3-body")).toBeVisible({ timeout: 20_000 });
}

/** Which element actually holds the caret -- focus claimed is not focus delivered. */
async function focusedTestId(page: Page): Promise<string | null> {
  return page.evaluate(() => {
    const active = document.activeElement as HTMLElement | null;
    if (!active) return null;
    return active.dataset.testid ?? active.id ?? active.tagName.toLowerCase();
  });
}

test("ord0135-the-wizard-survives-a-refresh-on-the-step-you-were-on — 填到第 3 步刷新，还在第 3 步且字还在", async ({
  page,
}) => {
  test.setTimeout(300_000);
  const NODE = "ord0135-the-wizard-survives-a-refresh-on-the-step-you-were-on";
  await openWizard(page);
  await fillStep1(page);
  await fillStep2(page);
  const before = {
    city: await page.getByTestId("review-city").innerText(),
    pace: await page.getByTestId("review-pace").innerText(),
  };
  await page.reload({ waitUntil: "load" });
  await expect(
    page.getByTestId("trial-step3-body"),
    node(
      NODE,
      `after a refresh the wizard is not on step 3 (it had ${JSON.stringify(before)}) -- a phone reload in the middle of a form sends the traveller back to the beginning`,
    ),
  ).toBeVisible({ timeout: 20_000 });
  const after = {
    city: await page.getByTestId("review-city").innerText(),
    pace: await page.getByTestId("review-pace").innerText(),
  };
  expect(
    after,
    node(NODE, `the step came back but the answers did not: before ${JSON.stringify(before)}, after ${JSON.stringify(after)}`),
  ).toEqual(before);
  writeFileSync(
    evidencePath("ui-overnight/ord0135-draft-refresh.json"),
    JSON.stringify({ generatedBy: "e345b9d6", node: NODE, head: process.env.CITYNEXUS_E2E_GIT_HEAD ?? "unknown", before, after }, null, 2) + "\n",
    "utf-8",
  );
});

test("ord0135-the-confirmation-step-prints-no-internal-key — 确认页不许把 relaxed 这类内部枚举给用户看", async ({
  page,
}) => {
  test.setTimeout(300_000);
  const NODE = "ord0135-the-confirmation-step-prints-no-internal-key";
  await openWizard(page);
  await fillStep1(page);
  await fillStep2(page);
  const pace = ((await page.getByTestId("review-pace").innerText()) ?? "").trim();
  const interests = ((await page.getByTestId("review-interests").innerText()) ?? "").trim();
  const body = (await page.locator("body").innerText()).replace(/\s+/g, " ");
  expect(
    ["轻松", "适中", "紧凑"].includes(pace),
    node(NODE, `the confirmation step prints 节奏 as "${pace}" -- an internal enum shown to the traveller instead of 轻松/适中/紧凑`),
  ).toBe(true);
  const leaked = LEAKS.filter((token) => new RegExp(`(^|[^a-z])${token}([^a-z]|$)`, "i").test(body));
  expect(
    leaked,
    node(NODE, `the wizard's own vocabulary reaches the screen: ${JSON.stringify(leaked)} (pace "${pace}", interests "${interests}")`),
  ).toEqual([]);
  writeFileSync(
    evidencePath("ui-overnight/ord0135-review-words.json"),
    JSON.stringify(
      { generatedBy: "e345b9d6", node: NODE, head: process.env.CITYNEXUS_E2E_GIT_HEAD ?? "unknown", pace, interests, leaked, body: body.slice(0, 400) },
      null,
      2,
    ) + "\n",
    "utf-8",
  );
  await page.screenshot({ path: evidencePath("ui-overnight/ord0135-review-words.png"), fullPage: true });
});

test("ord0135-a-missing-field-is-a-route-not-only-a-diagnosis — 「还需要填写」要点得过去", async ({
  page,
}) => {
  test.setTimeout(300_000);
  const NODE = "ord0135-a-missing-field-is-a-route-not-only-a-diagnosis";
  await openWizard(page);
  /* Do not `click()` this control: Playwright refuses to click an `aria-disabled` element, and the
     wizard uses `aria-disabled` deliberately (ORD-0066 甲 measured that a hard `disabled` dropped
     the button out of the tab sequence, so the reason parked beside it was never reached).  The
     order asks for the disabled state to be expressed accessibly and for the block to still be
     walkable -- so both halves are asserted here instead of being clicked past. */
  const next = page.getByTestId("trial-next");
  await expect(next).toHaveAttribute("aria-disabled", "true", { timeout: 10_000 });
  const nextHandle = await next.elementHandle();
  await nextHandle?.focus();
  expect(
    await focusedTestId(page),
    node(NODE, "the blocked 下一步 is not focusable, so a keyboard traveller never hears its reason"),
  ).toBe("trial-next");
  const hint = page.getByTestId("trial-required-hint");
  await expect(
    hint,
    node(NODE, "the step is blocked but no visible reason is offered"),
  ).toBeVisible({ timeout: 10_000 });
  const line = ((await hint.innerText()) ?? "").replace(/\s+/g, " ");
  expect(
    /还需要填写/.test(line),
    node(NODE, `the blocked hint reads "${line}" instead of naming the missing fields`),
  ).toBe(true);
  const jumps = page.getByTestId("trial-missing-jump");
  const count = await jumps.count();
  expect(
    count,
    node(NODE, `the hint lists missing fields but offers no way to reach them (${count} jump controls)`),
  ).toBeGreaterThan(0);
  const landed: Record<string, string | null> = {};
  for (let index = 0; index < count; index += 1) {
    const jump = jumps.nth(index);
    const target = (await jump.getAttribute("data-target")) ?? "";
    await jump.click();
    landed[target] = await focusedTestId(page);
    expect(
      landed[target],
      node(NODE, `the jump for "${(await jump.innerText()).trim()}" did not move the caret to ${target} (focus landed on ${landed[target]})`),
    ).toBe(target);
  }
  writeFileSync(
    evidencePath("ui-overnight/ord0135-missing-jumps.json"),
    JSON.stringify({ generatedBy: "e345b9d6", node: NODE, head: process.env.CITYNEXUS_E2E_GIT_HEAD ?? "unknown", hintLine: line, focusAfterEachJump: landed }, null, 2) + "\n",
    "utf-8",
  );
  await page.screenshot({ path: evidencePath("ui-overnight/ord0135-missing-jumps.png"), fullPage: true });
});
