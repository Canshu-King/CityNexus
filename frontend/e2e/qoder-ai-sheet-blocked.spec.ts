/**
 * ORD-0107 -- when the AI planner has nothing to build from, the screen has to say *which* nothing.
 *
 * The defect this closes is a chain of silences measured on the user's own phone:
 *   `PlanWithAiSheet.tsx:358` turned a failed catalogue read into `[]`;
 *   `:360` then took the first eight ids in whatever order the server happened to return them;
 *   `:362` skipped the request entirely when fewer than two survived, and the traveller was left with
 *   "没有生成可行方案 … 可以调整预算或换个说法再试" -- advice about their wording and budget for a
 *   problem that was our data.
 *
 * Four forced arms plus one unforced, because each silence needs its own witness:
 *   catalogue-empty / catalogue-short / catalogue-unreadable / compose-refused, and then the real
 *   server answering the user's own sentence.  Every arm also asserts the forbidden advice is gone.
 */
import { expect, test, type Page, type Request, type Route } from "@playwright/test";
import { writeFileSync } from "node:fs";
import { evidencePath } from "./_qoderEvidence";

const FILE = "e2e/qoder-ai-sheet-blocked.spec.ts";
const node = (id: string, detail: string) => `${FILE} :: ${id} — ${detail}`;
const clean = (value: string | null | undefined) =>
  String(value ?? "").replace(/\s+/g, " ").trim();

/** The user's own words, verbatim from the 14:31 phone screenshot quoted in the ledger.  Not a probe
 *  sentence chosen to make the test pass. */
const USER_SENTENCE =
  "没什么别的要求，这就是喜欢吃东西，有特色美食，然后特色景点玩一下。";

/** What the order forbids: advice about the traveller's wording or budget. */
const FORBIDDEN = ["调整预算", "换个说法", "改个说法", "adjust the budget", "rephrase"];

async function readScene(page: Page): Promise<Record<string, string | null>> {
  const response = await page.request.get("/api/v1/demo/scene");
  return (await response.json()) as Record<string, string | null>;
}

async function openHubWithJourney(
  page: Page,
  journeyId: string,
  locale: string,
) {
  await page.addInitScript(
    ([id, lang]) => {
      localStorage.clear();
      localStorage.setItem("citynexus.v8.journey_id", id as string);
      localStorage.setItem("citynexus.locale", lang as string);
    },
    [journeyId, locale],
  );
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/v8/hub", { waitUntil: "load" });
  await expect(page.getByTestId("today-hero")).toBeVisible({ timeout: 30_000 });
}

/** Drive the sheet to an answer and hand back what the screen actually said. */
async function askTheSheet(page: Page, NODE: string) {
  await page.getByTestId("hub-plan-with-ai").click();
  await expect(
    page.getByTestId("plan-ai-sheet"),
    node(NODE, "the AI planning sheet did not open from the hub"),
  ).toBeVisible({ timeout: 15_000 });
  const input = page.getByTestId("plan-ai-input");
  await input.fill(USER_SENTENCE);
  await page.getByTestId("plan-ai-submit").click();
  const result = page.getByTestId("plan-ai-result");
  await expect(
    result,
    node(NODE, "the sheet never answered the traveller at all"),
  ).toBeVisible({ timeout: 120_000 });
  const status = (await result.getAttribute("data-result-status")) ?? "";
  const text = clean(await result.innerText());
  const reasonLocator = page.getByTestId("plan-ai-reason");
  let reason = "";
  if ((await reasonLocator.count()) > 0) {
    await page.getByTestId("plan-ai-detail-toggle").click();
    reason = clean(await reasonLocator.innerText());
  }
  const nextStep = page.getByTestId("plan-ai-next-step");
  const steps = (await nextStep.count())
    ? [clean(await nextStep.innerText()), (await nextStep.getAttribute("data-next-step")) ?? ""]
    : [];
  return { status, text, reason, steps };
}

const envelope = (code: string, message: string) => ({
  error: { code, message, message_key: "request.invalid", details: null },
});

test("ord0107-ai-sheet-names-why-it-could-not-plan — 排不出来必须说得出是哪一类", async ({
  page,
}) => {
  test.setTimeout(420_000);
  const NODE = "ord0107-ai-sheet-names-why-it-could-not-plan";
  const seeded = await readScene(page);
  const journeyId = String(seeded.journey_id ?? "");
  expect(
    journeyId.length > 0,
    node(NODE, "no journey on the stage to ask the planner about"),
  ).toBe(true);

  const arms: Record<string, unknown> = {};
  const clearRoutes = async () => {
    await page.unroute("**/api/v1/journeys/*/agent/commands");
    await page.unroute("**/api/v1/places?city_code=*");
    await page.unroute("**/api/v1/journeys/*/plans/generate");
  };
  /* The mission is answered here so the four forced arms reach the fallback without waiting on a
     model this deployment does not have.  It is a completed mission that produced no plans -- the
     exact condition the fallback exists for. */
  const stubMission = async () => {
    await page.route("**/api/v1/journeys/*/agent/commands", async (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          mission: {
            status: "COMPLETED",
            failure_reason: null,
            reasoning_summary: null,
          },
        }),
      }),
    );
  };

  type Arm = {
    key: string;
    places: (route: Route) => Promise<void>;
    generate?: (route: Route) => Promise<void>;
    expectStatus: string;
    expectWords: string;
    expectStep: string;
    /** Does pressing the offered next step actually take the traveller somewhere? */
    proveStep?: boolean;
    /** This arm reaches the compose request, so its body is inspectable. */
    expectBodyWithoutPlaceIds?: boolean;
  };
  const cases: Arm[] = [
    {
      key: "catalogue-empty",
      places: async (route: Route) =>
        route.fulfill({ status: 200, contentType: "application/json", body: "[]" }),
      expectStatus: "BLOCKED:CATALOG_EMPTY",
      expectWords: "这座城我们还没有任何地点数据",
      expectStep: "another-city",
      proveStep: true,
    },
    {
      key: "catalogue-short",
      places: async (route: Route) =>
        route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify([{ id: "place-only-one", name: "Only one" }]),
        }),
      expectStatus: "BLOCKED:CATALOG_INSUFFICIENT",
      expectWords: "这座城我们手上的地点太少",
      expectStep: "another-city",
    },
    {
      key: "catalogue-unreadable",
      places: async (route: Route) =>
        route.fulfill({
          status: 503,
          contentType: "application/json",
          body: JSON.stringify(
            envelope("CATALOG_PROVIDER_UNAVAILABLE", "the catalogue service is down"),
          ),
        }),
      expectStatus: "BLOCKED:CATALOG_PROVIDER_UNAVAILABLE",
      expectWords: "CATALOG_PROVIDER_UNAVAILABLE",
      expectStep: "",
    },
    {
      key: "compose-refused",
      places: async (route: Route) =>
        route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify([
            { id: "place-a", name: "A" },
            { id: "place-b", name: "B" },
            { id: "place-c", name: "C" },
          ]),
        }),
      generate: async (route: Route) =>
        route.fulfill({
          status: 422,
          contentType: "application/json",
          body: JSON.stringify(
            envelope("CATALOG_EMPTY", "No feasible plan candidates satisfy the journey constraints"),
          ),
        }),
      expectStatus: "BLOCKED:CATALOG_EMPTY",
      expectWords: "这座城我们还没有任何地点数据",
      expectStep: "another-city",
      expectBodyWithoutPlaceIds: true,
    },
  ];

  for (const item of cases) {
    await clearRoutes();
    await stubMission();
    await page.route("**/api/v1/places?city_code=*", (route) => item.places(route));
    if (item.generate) {
      const refuse = item.generate;
      await page.route("**/api/v1/journeys/*/plans/generate", (route) => refuse(route));
    }
    /* Did the sheet ask the server to compose at all?  The silent skip this order closes was exactly
       "fewer than two places, so send nothing and say nothing". */
    const generated: string[] = [];
    const bodies: string[] = [];
    const onRequest = (request: Request) => {
      if (request.method() === "POST" && request.url().includes("/plans/generate")) {
        generated.push(request.url());
        bodies.push(request.postData() ?? "");
      }
    };
    page.on("request", onRequest);
    await openHubWithJourney(page, journeyId, "zh-CN");
    const answer = await askTheSheet(page, NODE);
    page.off("request", onRequest);

    expect(
      answer.status,
      node(NODE, `${item.key}: the screen said ${JSON.stringify(answer.status)}, not the named block ${JSON.stringify(item.expectStatus)} -- full text ${JSON.stringify(answer.text)}`),
    ).toBe(item.expectStatus);
    expect(
      answer.text,
      node(NODE, `${item.key}: the block is named but the reason is not in the words the traveller reads: ${JSON.stringify(answer.text)}`),
    ).toContain(item.expectWords);
    for (const phrase of FORBIDDEN) {
      expect(
        answer.text.includes(phrase),
        node(NODE, `${item.key}: the screen still blames the traveller (${JSON.stringify(phrase)}) in ${JSON.stringify(answer.text)}`),
      ).toBe(false);
    }
    /* Filed before anything is pressed: the next step closes this sheet by design, and a picture of
       the answer has to be a picture of the answer. */
    await page.getByTestId("plan-ai-sheet").screenshot({
      path: evidencePath(`ui-overnight/ai-sheet-${item.key}.png`),
    });
    if (item.expectStep) {
      expect(
        answer.steps[1],
        node(NODE, `${item.key}: no actionable next step on this refusal: ${JSON.stringify(answer)}`),
      ).toBe(item.expectStep);
      if (item.proveStep) {
        /* "一个能点的下一步" is only true if pressing it goes somewhere. */
        await page.getByTestId("plan-ai-next-step").click();
        await expect(
          page.getByTestId("trial-setup"),
          node(NODE, `${item.key}: the offered next step closed the sheet but opened nothing the traveller can act on`),
        ).toBeVisible({ timeout: 15_000 });
        await expect(
          page.getByTestId("plan-ai-sheet"),
          node(NODE, `${item.key}: the sheet stayed open behind the next step`),
        ).toHaveCount(0);
      }
    }
    if (item.key === "catalogue-unreadable") {
      /* ②: a failed read must be visible as itself, with the server's sentence kept. */
      expect(
        answer.reason,
        node(NODE, `${item.key}: the technical detail lost the server's own sentence: ${JSON.stringify(answer)}`),
      ).toContain("the catalogue service is down");
    }
    if (item.expectBodyWithoutPlaceIds) {
      /* ORD-0107 ①: the shortlist this screen used to build out of the read order is gone, so the
         request must carry no ids at all -- the server's catalogue path chooses. */
      expect(
        bodies.length,
        node(NODE, `${item.key}: the compose request never went out, so its body could not be read: ${JSON.stringify(generated)}`),
      ).toBeGreaterThan(0);
      expect(
        bodies[0].includes("place_ids"),
        node(NODE, `${item.key}: the sheet is still picking places by position -- the request carries place_ids: ${JSON.stringify(bodies[0])}`),
      ).toBe(false);
    }
    if (item.key === "catalogue-empty" || item.key === "catalogue-short") {
      expect(
        generated.length,
        node(NODE, `${item.key}: with fewer than two catalogued places the sheet still sent a compose request to the server: ${JSON.stringify(generated)}`),
      ).toBe(0);
    }
    arms[item.key] = answer;
    await clearRoutes();
  }

  /* The unforced arm: the real server, the user's own sentence.  Whatever it decides, two things must
     hold -- no blame-the-traveller advice, and a named code whenever the answer is a refusal. */
  await clearRoutes();
  await openHubWithJourney(page, journeyId, "zh-CN");
  const real = await askTheSheet(page, NODE);
  for (const phrase of FORBIDDEN) {
    expect(
      real.text.includes(phrase),
      node(NODE, `the real run answers ${JSON.stringify(real.status)} with advice about the traveller's wording (${JSON.stringify(phrase)}): ${JSON.stringify(real.text)}`),
    ).toBe(false);
  }
  if (real.status.startsWith("BLOCKED:")) {
    expect(
      real.status.slice("BLOCKED:".length).length,
      node(NODE, `a BLOCKED answer carries no code: ${JSON.stringify(real)}`),
    ).toBeGreaterThan(0);
    expect(
      real.steps.length,
      node(NODE, `a BLOCKED answer offers no next step: ${JSON.stringify(real)}`),
    ).toBeGreaterThan(0);
  }
  arms.real = { ...real, aiState: await page.getByTestId("plan-ai-preflight").getAttribute("data-ai-state").catch(() => null) };
  await page.getByTestId("plan-ai-sheet").screenshot({
    path: evidencePath("ui-overnight/ai-sheet-real-answer.png"),
  });

  writeFileSync(
    evidencePath("ui-overnight/ord0107-ai-sheet-arms.json"),
    JSON.stringify(
      {
        generatedBy: "e345b9d6",
        order: "ORD-0107",
        node: NODE,
        head: process.env.CITYNEXUS_E2E_GIT_HEAD ?? "unknown",
        journeyId,
        userSentence: USER_SENTENCE,
        forbiddenAdvicePhrases: FORBIDDEN,
        arms,
      },
      null,
      2,
    ) + "\n",
    "utf-8",
  );
});
