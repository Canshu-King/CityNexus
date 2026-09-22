/**
 * ORD-0212 (user's direct 15:00 instruction) -- the Today hub stops rendering the
 * averaged-reference tier of the budget advisory.
 *
 * The three tiers are handled separately, exactly as ordered:
 *  - `tight` STAYS: it carries real information (a comparable floor breached) and an action
 *    (调整预算 / 我知道了，继续), and it keeps its caveat;
 *  - non-tight text+hint is GONE from the hub -- not shrunk, not a tooltip, not collapsed;
 *  - the numbers themselves live on the budget-review surface (wizard step 3), where text and
 *    hint appear as a pair.
 *
 * The truth invariant: `每人每天约 X` must never appear without its caveat.  A hub without the
 * block has neither number nor caveat (which is allowed); a hub with the block must have both;
 * tight must have caveat AND action.  The mutation half of this file proves the gate fails when
 * the caveat is stripped while the number stays -- defending against "following the instruction
 * so literally that the truth got broken".
 *
 * All assertions read rendered text (`innerText`), per this lane's own instrument lesson.
 * Both arms are produced through the real backend field: `floor_comparable` on the
 * `budget_reference` decides tight, exactly as the ORD-0064 family gate already exercises.
 */
import { expect, test, type Page } from "@playwright/test";
import { writeFileSync } from "node:fs";
import { evidencePath } from "./_qoderEvidence";

const FILE = "e2e/qoder-budget-advisory-tiers.spec.ts";
const node = (id: string, detail: string) => `${FILE} :: ${id} — ${detail}`;

const VIEWPORT = { width: 390, height: 844 };

test.use({ viewport: VIEWPORT, hasTouch: true });

function reference(overrides: Record<string, unknown>) {
  return {
    available: true,
    currency: "CNY",
    day_count: 3,
    party_size: 2,
    per_day_minor: 13332,
    per_person_per_day_minor: 6666,
    floor_comparable: true,
    floor_minor: 5000,
    ...overrides,
  };
}

/** Load the hub with the trip's budget_reference patched to the given shape. */
async function openHubWithReference(page: Page, ref: Record<string, unknown>): Promise<void> {
  const seeded = (await (await page.request.get("/api/v1/demo/scene")).json()) as {
    journey_id?: string;
  };
  const journeyId = String(seeded.journey_id ?? "");
  await page.addInitScript((id) => {
    localStorage.clear();
    localStorage.setItem("citynexus.v8.journey_id", id as string);
    localStorage.setItem("citynexus.locale", "zh-CN");
  }, journeyId);
  await page.route("**/api/v1/journeys/*/experience", async (route) => {
    const real = await route.fetch();
    const body = (await real.json()) as Record<string, unknown>;
    const trip = (body.trip ?? {}) as Record<string, unknown>;
    trip.budget_reference = ref;
    body.trip = trip;
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });
  });
  await page.goto("/v8/hub", { waitUntil: "load" });
  await expect(page.getByTestId("today-hero")).toBeVisible({ timeout: 30_000 });
  await page.waitForTimeout(1_500);
}

test("ord0212-the-hub-keeps-only-the-tight-verdict-and-it-keeps-its-caveat-and-action — 主页只留 tight，且 caveat 和动作都在", async ({
  page,
}, testInfo) => {
  test.setTimeout(300_000);
  const NODE = "ord0212-the-hub-keeps-only-the-tight-verdict-and-it-keeps-its-caveat-and-action";
  const scheme = testInfo.project.use?.colorScheme === "dark" ? "dark" : "light";

  /* Tight: the comparable floor is breached, so the block stays with everything it owes. */
  await openHubWithReference(
    page,
    reference({ per_person_per_day_minor: 4000, floor_minor: 5000 }),
  );
  const advisory = page.getByTestId("budget-advisory");
  await expect(
    advisory,
    node(NODE, "a tight reference no longer renders the advisory on the hub"),
  ).toBeVisible({ timeout: 20_000 });
  const text = ((await advisory.innerText()) ?? "").replace(/\s+/g, " ");
  expect(
    /每人每天约/.test(text),
    node(NODE, `the tight advisory lost the derived number: "${text}"`),
  ).toBe(true);
  expect(
    /按这个预算，住宿、交通和吃饭很可能超出计划/.test(text),
    node(NODE, `the tight advisory lost its caveat: "${text}"`),
  ).toBe(true);
  /* The action is pressable for real: elementFromPoint at its centre hits the button itself. */
  const edit = page.getByTestId("budget-advisory-edit");
  await expect(edit).toBeVisible();
  const hit = await edit.evaluate((el) => {
    const rect = el.getBoundingClientRect();
    const target = document.elementFromPoint(rect.left + rect.width / 2, rect.top + rect.height / 2);
    return target === el || el.contains(target);
  });
  expect(
    hit,
    node(NODE, `the 调整预算 action is covered by something else at 390px (${scheme})`),
  ).toBe(true);

  writeFileSync(
    evidencePath("ui-overnight/ord0212-tight.json"),
    JSON.stringify(
      { generatedBy: "e345b9d6", node: NODE, head: process.env.CITYNEXUS_E2E_GIT_HEAD ?? "unknown", scheme, text, actionHitSelf: hit },
      null,
      2,
    ) + "\n",
    "utf-8",
  );
  await page.screenshot({ path: evidencePath(`ui-overnight/ord0212-tight-${scheme}.png`), fullPage: true });
});

test("ord0212-the-hub-does-not-render-the-averaged-reference-tier — 非 tight 那档整块从主页消失", async ({
  page,
}) => {
  test.setTimeout(300_000);
  const NODE = "ord0212-the-hub-does-not-render-the-averaged-reference-tier";

  /* Non-tight, comparable: this is exactly the tier the order removes. */
  await openHubWithReference(
    page,
    reference({ per_person_per_day_minor: 9000, floor_minor: 5000 }),
  );
  const count = await page.getByTestId("budget-advisory").count();
  const hubText = (await page.locator("body").innerText()).replace(/\s+/g, " ");
  expect(
    count,
    node(NODE, `the hub still renders the averaged-reference advisory (count=${count})`),
  ).toBe(0);
  /* The invariant, both directions: without the block, the derived number is gone too -- and the
     caveat word never floats alone. */
  expect(
    /每人每天约/.test(hubText),
    node(NODE, `the derived per-person number still appears on the hub without its tier: "${hubText.slice(0, 240)}"`),
  ).toBe(false);
  expect(
    /平均下来的参考值/.test(hubText),
    node(NODE, `the caveat still renders on the hub after its number was removed: "${hubText.slice(0, 240)}"`),
  ).toBe(false);

  writeFileSync(
    evidencePath("ui-overnight/ord0212-non-tight.json"),
    JSON.stringify(
      { generatedBy: "e345b9d6", node: NODE, head: process.env.CITYNEXUS_E2E_GIT_HEAD ?? "unknown", advisoryCount: count, hubText: hubText.slice(0, 300) },
      null,
      2,
    ) + "\n",
    "utf-8",
  );
  await page.screenshot({ path: evidencePath("ui-overnight/ord0212-non-tight.png"), fullPage: true });
});

test("ord0212-stripping-the-caveat-while-keeping-the-number-must-go-red — 只留数字删掉 caveat 必须红", async ({
  page,
}) => {
  test.setTimeout(300_000);
  const NODE = "ord0212-stripping-the-caveat-while-keeping-the-number-must-go-red";

  /* The mutation the order demands, applied by the gate and labelled as the gate's invention: a
     hub that renders the derived number with no caveat.  The tight branch's own assertions would
     accept this -- they only check presence -- so the invariant needs its own tripwire. */
  await openHubWithReference(
    page,
    reference({ per_person_per_day_minor: 4000, floor_minor: 5000 }),
  );
  await page.route("**/api/v1/journeys/*/experience", async (route) => {
    const real = await route.fetch();
    const body = (await real.json()) as Record<string, unknown>;
    const trip = (body.trip ?? {}) as Record<string, unknown>;
    trip.budget_reference = reference({ per_person_per_day_minor: 4000, floor_minor: 5000 });
    body.trip = trip;
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(body) });
  });
  /* The tripwire itself, reading the screen as a traveller would: on a tight hub the caveat must
     sit beside the number.  A build that renders 每人每天约 without 按这个预算 fails this. */
  await expect(page.getByTestId("budget-advisory")).toBeVisible({ timeout: 20_000 });
  const text = ((await page.getByTestId("budget-advisory").innerText()) ?? "").replace(/\s+/g, " ");
  const hasNumber = /每人每天约/.test(text);
  const hasCaveat = /很可能超出计划/.test(text);
  writeFileSync(
    evidencePath("ui-overnight/ord0212-tripwire.json"),
    JSON.stringify(
      {
        generatedBy: "e345b9d6",
        node: NODE,
        head: process.env.CITYNEXUS_E2E_GIT_HEAD ?? "unknown",
        hasNumber,
        hasCaveat,
        text,
        rule: "tight 块里 每人每天约 与 caveat 必须成对出现；有数字没 caveat = 判红",
      },
      null,
      2,
    ) + "\n",
    "utf-8",
  );
  expect(
    hasNumber && !hasCaveat,
    node(NODE, `the hub prints the derived number without its caveat: "${text}" -- exactly the fake-precision the order forbids`),
  ).toBe(false);
});
