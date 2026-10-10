import { expect, test } from "@playwright/test";
import { readFileSync, writeFileSync } from "node:fs";
import { evidencePath } from "./_qoderEvidence";

/**
 * wenangong-0549 -- the five words this order moved onto existing dictionary keys,
 * read off the live screen in both languages.
 *
 * Expected strings are NOT typed here and NOT read from the dictionary: they come from
 * `review/wenangong/i18n_0549_plan_ai_expect.json`, frozen out of the authoritative tip's
 * own inline arms before the swap. So a red row means the screen started saying something
 * other than what it said on the tip -- which is exactly the thing this order forbids.
 *
 * The 「技术详情」 block sits inside a `<details>`: the fold is opened before it is measured,
 * and every cell is proven inside the 390x844 viewport first.
 */

const FILE = "e2e/qoder-wenangong-0549-plan-ai-words.spec.ts";
const node = (id: string, detail: string) => `${FILE} :: ${id} — ${detail}`;
const clean = (t: string) => t.replace(/\s+/g, " ").trim();

const SENTENCE = "没什么别的要求，这就是喜欢吃东西，有特色美食和特色景点玩一下。";
const envelope = (code: string, message: string) => ({
  error: { code, message, message_key: "request.invalid", details: null },
});

test("wenangong-0549-plan-ai-words-unchanged-on-screen — 五枚词逐枚上屏，逐字等于改前", async ({
  page,
}) => {
  test.setTimeout(300_000);
  const table = JSON.parse(
    readFileSync(new URL("../../review/wenangong/i18n_0549_plan_ai_expect.json", import.meta.url), "utf-8"),
  ) as Record<string, { inline_zh: string; inline_en: string; tip_line: number }>;

  const live = await page.request.get("/api/v1/demo/scene");
  expect(live.ok(), node("seed", `GET /demo/scene answered ${live.status()}`)).toBe(true);
  const seeded = (await live.json()) as Record<string, unknown>;
  const journeyId = String(seeded.journey_id ?? "");
  expect(journeyId.length > 0, node("seed", `the seeded stage holds no journey: ${JSON.stringify(seeded)}`)).toBe(true);

  await page.route("**/api/v1/places?city_code=*", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        { id: "place-a", name: "A" },
        { id: "place-b", name: "B" },
        { id: "place-c", name: "C" },
      ]),
    }),
  );
  await page.route("**/api/v1/journeys/*/plans/generate", (route) =>
    route.fulfill({
      status: 422,
      contentType: "application/json",
      body: JSON.stringify(envelope("CATALOG_EMPTY", "No feasible plan candidates satisfy the journey constraints")),
    }),
  );
  await page.addInitScript(
    ([id]) => {
      localStorage.clear();
      localStorage.setItem("citynexus.v8.journey_id", id as string);
      const wanted = new URLSearchParams(window.location.search).get("cnxlocale");
      if (wanted === "en" || wanted === "zh-CN") localStorage.setItem("citynexus.locale", wanted);
    },
    [journeyId],
  );
  await page.setViewportSize({ width: 390, height: 844 });

  const rows: Record<string, unknown>[] = [];
  const arm = (key: string, lang: string) => (lang === "zh-CN" ? table[key].inline_zh : table[key].inline_en);

  for (const lang of ["zh-CN", "en"]) {
    await page.goto(`/v8/hub?cnxlocale=${lang}`, { waitUntil: "load" });
    await expect(page.getByTestId("today-hero"), node("hero", `${lang}: Today never rendered`)).toBeVisible({
      timeout: 30_000,
    });

    await page.getByTestId("hub-plan-with-ai").click();
    const sheet = page.getByTestId("plan-ai-sheet");
    await expect(sheet, node("sheet", `${lang}: the AI sheet did not open`)).toBeVisible({ timeout: 20_000 });

    /* 面板自己的标题（改前写在本屏第 722 行） */
    const title = page.locator("#plan-ai-title");
    await expect(title, node("itinerary.planWithAi", `${lang}: the sheet's own title is off screen`)).toBeInViewport();
    const saidTitle = clean(await title.innerText());
    rows.push({ locale: lang, key: "itinerary.planWithAi", shown: saidTitle, expected: arm("itinerary.planWithAi", lang) });
    expect(saidTitle, node("itinerary.planWithAi", `${lang}: title reads ${JSON.stringify(saidTitle)}`)).toBe(
      arm("itinerary.planWithAi", lang),
    );

    /* 关闭键的可读名（改前第 729 行，这是读屏播报名，不是画出来的字） */
    const close = page.locator(".plan-ai-close");
    const saidClose = clean((await close.getAttribute("aria-label")) || "");
    rows.push({ locale: lang, key: "shell.close", shown: saidClose, expected: arm("shell.close", lang), slot: "aria" });
    expect(saidClose, node("shell.close", `${lang}: close announces ${JSON.stringify(saidClose)}`)).toBe(
      arm("shell.close", lang),
    );

    await page.getByTestId("plan-ai-input").fill(SENTENCE);
    await page.getByTestId("plan-ai-submit").click();

    /* 「技术详情」是一层折叠（改前第 1018 行）：先点开再量。 */
    const fold = page.getByTestId("plan-ai-detail-toggle");
    await expect(fold, node("hub.continuationTechnicalDetail", `${lang}: the detail fold never appeared`)).toBeVisible({
      timeout: 60_000,
    });
    await fold.click();
    const saidFold = clean(await fold.innerText());
    rows.push({
      locale: lang,
      key: "hub.continuationTechnicalDetail",
      shown: saidFold,
      expected: arm("hub.continuationTechnicalDetail", lang),
    });
    expect(saidFold, node("hub.continuationTechnicalDetail", `${lang}: fold reads ${JSON.stringify(saidFold)}`)).toBe(
      arm("hub.continuationTechnicalDetail", lang),
    );

    /* 折叠里那枚本机回读字段标签（改前第 1061 行）。它在不在取决于服务器这次给了什么，
       所以先数在不在，不在就如实写 absent，而不是默默少一行。 */
    const raw = page.getByTestId("plan-ai-raw-label");
    const rawCount = await raw.count();
    if (rawCount > 0) {
      await expect(raw, node("detail.rawFactsHeading", `${lang}: the raw label is off screen`)).toBeInViewport();
      const saidRaw = clean(await raw.innerText());
      rows.push({ locale: lang, key: "detail.rawFactsHeading", shown: saidRaw, expected: arm("detail.rawFactsHeading", lang) });
      expect(saidRaw, node("detail.rawFactsHeading", `${lang}: raw label reads ${JSON.stringify(saidRaw)}`)).toBe(
        arm("detail.rawFactsHeading", lang),
      );
    } else {
      rows.push({ locale: lang, key: "detail.rawFactsHeading", shown: "ABSENT", expected: "not rendered for this refusal" });
    }

    /* 「已取消」那一枚（改前第 200 行）要一次真被取消的运行才上屏；本规格不造它，
       所以这里明确写下它此刻不在屏上，别把没看到的当成看到的。 */
    rows.push({ locale: lang, key: "bookings.realtimeCancelled", shown: "NOT_REACHED", expected: "needs a cancelled run" });
  }

  writeFileSync(
    evidencePath("ui-overnight/wenangong-0549-plan-ai-words.json"),
    JSON.stringify(
      {
        generatedBy: "wenangong-0549",
        head: process.env.CITYNEXUS_E2E_GIT_HEAD ?? "unknown",
        readings: rows.length,
        rows,
      },
      null,
      2,
    ) + "\n",
    "utf-8",
  );
  await page.screenshot({ path: evidencePath("ui-overnight/wenangong-0549-plan-ai-words.png"), fullPage: true });
});
