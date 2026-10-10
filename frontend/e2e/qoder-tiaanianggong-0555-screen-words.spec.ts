/**
 * ORD-0555 (提案工) -- screen proof for the three AI-sheet card titles this lane moved off inline
 * `zh ? "…" : "…"` ternaries and onto new `planning.*` dictionary keys.
 *
 * The order forbids a re-wording: the sentence painted on the screen has to be the one that was
 * painted before the move.  Those literals are therefore asserted by equality, in BOTH locales, on
 * the real panel driven to a real answer by the real product code path (the same forcing shapes
 * `qoder-ord0302-unreadable-server-body.spec.ts` uses: an aborted request, a 422 that carries the
 * server's own sentence, a non-JSON 5xx).
 */
import { expect, test, type Page, type Route } from "@playwright/test";
import { writeFileSync } from "node:fs";
import { evidencePath } from "./_qoderEvidence";

const FILE = "e2e/qoder-tiaanianggong-0555-screen-words.spec.ts";
const node = (id: string, detail: string) => `${FILE} :: ${id} — ${detail}`;
const clean = (value: string | null | undefined) =>
  String(value ?? "").replace(/\s+/g, " ").trim();

const USER_SENTENCE = "帮我排三天，喜欢美食和特色景点。";
const SERVER_SENTENCE = "该目的地的候选目录尚未就绪，请稍后重试。";

type Force = { status: number; contentType: string; body: string } | { abort: true };

/* title literals are the pre-move screen text, copied off the blob this lane replaced (7ce836f9a). */
const ARMS: { id: string; key: string; force: Force; zh: string; en: string }[] = [
  {
    id: "NETWORK",
    key: "planning.theServerCouldNotBeReached",
    force: { abort: true },
    zh: "连不上服务端",
    en: "The server could not be reached",
  },
  {
    id: "HTTP_422",
    key: "planning.theRequestWasRefused",
    force: {
      status: 422,
      contentType: "application/json",
      body: JSON.stringify({
        error: { code: "request.invalid", message: SERVER_SENTENCE, message_key: "request.invalid", details: null },
      }),
    },
    zh: "这个要求被明确拒绝",
    en: "The request was refused",
  },
  {
    id: "HTTP_500",
    key: "planning.theServerFailedToFinish",
    force: {
      status: 500,
      contentType: "text/html",
      body: "<html><body>502 Bad Gateway</body></html>",
    },
    zh: "服务端处理失败",
    en: "The server failed to finish",
  },
];
const LOCALES = ["zh-CN", "en"] as const;

async function bootAndAsk(page: Page, force: Force, locale: string): Promise<Record<string, unknown>> {
  const scene = (await (await page.request.get("/api/v1/demo/scene")).json()) as { journey_id?: string };
  const journeyId = String(scene.journey_id ?? "");
  expect(journeyId.length > 0, node(locale, "the stage named no journey")).toBe(true);
  await page.addInitScript(
    ([id, lang]) => {
      localStorage.clear();
      localStorage.setItem("citynexus.v8.journey_id", id as string);
      localStorage.setItem("citynexus.locale", lang as string);
    },
    [journeyId, locale],
  );
  await page.setViewportSize({ width: 390, height: 844 });

  await page.route("**/api/v1/journeys/*/plans", async (r: Route) => {
    if (r.request().method() !== "GET") return r.fallback();
    await r.fulfill({ status: 200, contentType: "application/json", body: "[]" });
  });
  await page.route("**/api/v1/journeys/*/agent/commands", async (r: Route) => {
    if (r.request().method() !== "POST") return r.fallback();
    if ("abort" in force) return r.abort();
    await r.fulfill({ status: force.status, contentType: force.contentType, body: force.body });
  });

  await page.goto("/v8/hub", { waitUntil: "load" });
  await expect(page.getByTestId("today-hero"), node(locale, "the hub never rendered")).toBeVisible({
    timeout: 30_000,
  });
  await page.getByTestId("hub-plan-with-ai").click();
  await page.getByTestId("plan-ai-input").fill(USER_SENTENCE);
  await page.getByTestId("plan-ai-submit").click();
  const result = page.getByTestId("plan-ai-result");
  await expect(result, node(locale, "the sheet never answered")).toBeVisible({ timeout: 120_000 });
  const title = clean(await result.locator("b").first().innerText());
  const status = (await result.getAttribute("data-result-status")) ?? "";
  return { locale, status, title, card_text: clean(await result.innerText()) };
}

const readings: Record<string, unknown> = {};

for (const arm of ARMS) {
  for (const locale of LOCALES) {
    const id = `${arm.id}-${locale}`;
    test(`ord0555-screen-${id} ${arm.key} paints the pre-move sentence on a real card`, async ({ page }) => {
      const read = await bootAndAsk(page, arm.force, locale);
      const want = locale === "zh-CN" ? arm.zh : arm.en;
      readings[id] = { key: arm.key, want, read };
      expect(read.title, node(id, `painted title is ${JSON.stringify(read.title)}, not ${JSON.stringify(want)}`)).toBe(want);
      /* the same card must not be a blank shell -- the sentence below the title has to be there too */
      expect(String(read.card_text).length, node(id, "the card rendered no body line")).toBeGreaterThan(
        want.length,
      );
    });
  }
}

test.afterAll(() => {
  writeFileSync(evidencePath("ord0555_screen_words_readings.json"), JSON.stringify(readings, null, 2));
});
