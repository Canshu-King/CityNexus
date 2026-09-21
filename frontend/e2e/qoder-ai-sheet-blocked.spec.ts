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

/* ------------------------------------------- ORD-0104 ①: an example is about this trip or it is absent.
 *
 * The sheet used to show two hardcoded Xiamen itineraries on every city's screen -- placeholder and
 * chips -- which is the screen stating facts it never learned.  Two arms: the real fixture (a city this
 * server has no places for, so nothing may be suggested) and a stub that hands back two of the
 * journey's own city's place names (so the suggestion must be about those).
 */
const FOREIGN_FACTS = ["厦门", "鼓浪屿", "环岛路", "沙茶面", "Xiamen", "Gulangyu"];

test("ord0104-ai-sheet-examples-follow-the-destination — 例子要么跟这趟走，要么没有", async ({
  page,
}) => {
  test.setTimeout(300_000);
  const NODE = "ord0104-ai-sheet-examples-follow-the-destination";
  const seeded = await readScene(page);
  const journeyId = String(seeded.journey_id ?? "");
  const cityCode = String(
    ((await (await page.request.get(`/api/v1/journeys/${journeyId}`)).json()) as {
      city_code?: string;
    }).city_code ?? "",
  );

  const arms: Record<string, unknown> = {};
  for (const [key, names] of [
    ["real", null],
    ["two-places", ["海河游船码头", "天津之眼"]],
  ] as const) {
    await page.unroute("**/api/v1/places?city_code=*");
    let stubHits = 0;
    const seen: string[] = [];
    page.on("request", (request) => {
      if (request.url().includes("/api/v1/places")) seen.push(request.url());
    });
    if (names) {
      await page.route("**/api/v1/places?city_code=*", async (route) => {
        stubHits += 1;
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify(
            names.map((name, index) => ({ id: `place-${index}`, name })),
          ),
        });
      });
    }
    await openHubWithJourney(page, journeyId, "zh-CN");
    await page.getByTestId("hub-plan-with-ai").click();
    const sheet = page.getByTestId("plan-ai-sheet");
    await expect(
      sheet,
      node(NODE, `${key}: the AI sheet did not open`),
    ).toBeVisible({ timeout: 15_000 });
    const chips = page.locator('[data-testid="plan-ai-examples"] button');
    /* The suggestions come from an async read that starts when the sheet mounts.  Counting them at
     first paint is a race the isolated run wins and the full chain loses -- measured, when this arm
     read 0 chips in the chain and 2 on its own.  Wait for the count to settle instead. */
    /* Wait for the read to land before counting anything: `data-examples-state` says "reading" until
       the request answers, so an arm cannot pass by being measured too early. */
    await expect
      .poll(() => page.getByTestId("plan-ai-examples").getAttribute("data-examples-state"), {
        timeout: 15_000,
        intervals: [200],
        message: node(NODE, `${key}: the sheet never finished reading this city's places, so a count of ${names ? 2 : 0} would prove nothing`),
      })
      .not.toBe("reading");
    const count = await chips.count();
    const chipTexts: string[] = [];
    for (let index = 0; index < count; index += 1) {
      chipTexts.push(clean(await chips.nth(index).innerText()));
    }
    let placeholder = "";
    await expect
      .poll(
        async () => {
          placeholder =
            (await page.getByTestId("plan-ai-input").getAttribute("placeholder")) ?? "";
          return placeholder;
        },
        {
          timeout: 15_000,
          intervals: [250],
          message: node(NODE, `${key}: the input never got a placeholder to read`),
        },
      )
      .not.toBe("");
    const shown = `${chipTexts.join(" ")} ${placeholder}`;
    for (const foreign of FOREIGN_FACTS) {
      expect(
        shown.includes(foreign),
        node(NODE, `${key}: another city's concrete fact (${JSON.stringify(foreign)}) is on this screen for ${JSON.stringify(cityCode)}: ${JSON.stringify(shown)}`),
      ).toBe(false);
    }
    if (names) {
      expect(
        count,
        node(NODE, `${key}: the city has two catalogued places and the sheet offered ${count} suggestions (stub served ${stubHits} times; requests seen: ${JSON.stringify(seen)})`),
      ).toBe(2);
      for (const chip of chipTexts) {
        expect(
          names.some((name) => chip.includes(name)),
          node(NODE, `${key}: a suggestion names no place this city actually has: ${JSON.stringify(chip)}`),
        ).toBe(true);
      }
      expect(
        names.some((name) => placeholder.includes(name)),
        node(NODE, `${key}: the placeholder is not built from this city's places: ${JSON.stringify(placeholder)}`),
      ).toBe(true);
    } else {
      expect(
        count,
        node(NODE, `${key}: with ${JSON.stringify(cityCode)} answering no places the sheet still invented a suggestion: ${JSON.stringify(chipTexts)}`),
      ).toBe(0);
      expect(
        placeholder,
        node(NODE, `${key}: no places to name, so the placeholder must stay destination-neutral: ${JSON.stringify(placeholder)}`),
      ).toContain("用你自己的话说");
    }
    await sheet.screenshot({
      path: evidencePath(`ui-overnight/ai-sheet-examples-${key}.png`),
    });
    arms[key] = { cityCode, chipCount: count, chipTexts, placeholder };
    await page.getByTestId("plan-ai-dismiss").click();
    /* The next arm registers its own stub *before* the sheet mounts, so the sheet has to be gone
       first -- an arm that inherits the previous arm's open sheet silently reads the previous arm's
       data.  Measured: that is exactly how `two-places` came back with 0 suggestions. */
    await expect
      .poll(() => page.getByTestId("plan-ai-sheet").count(), {
        timeout: 10_000,
        intervals: [200],
        message: node(NODE, `${key}: the sheet stayed open, so the next arm would not be its own measurement`),
      })
      .toBe(0);
  }
  await page.unroute("**/api/v1/places?city_code=*");

  writeFileSync(
    evidencePath("ui-overnight/ord0104-ai-sheet-examples.json"),
    JSON.stringify(
      {
        generatedBy: "e345b9d6",
        order: "ORD-0104 residual 1",
        node: NODE,
        head: process.env.CITYNEXUS_E2E_GIT_HEAD ?? "unknown",
        forbiddenFacts: FOREIGN_FACTS,
        arms,
      },
      null,
      2,
    ) + "\n",
    "utf-8",
  );
});
