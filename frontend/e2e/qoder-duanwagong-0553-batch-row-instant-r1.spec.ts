/* ORD-0553 · lane short-tiler (duanwagong) -- the batch-receipt row must render an instant,
 * not the server's ISO string with its offset sliced off.
 *
 * Before this order the row read `row.start_at.slice(0, 16).replace("T", " ")`, so whatever wall
 * clock the offset carried went straight to the traveller.  The row now goes through `formatWhen`.
 *
 * Two arms, one per locale, and both are read-only at the dictionary level: the only write is the
 * batch the traveller asked for, into this run's own throwaway database (authoritative mode refuses
 * to reopen a file that already exists, and the run id is in the file name).
 *
 * The expected string is computed in the page, from the server's raw `start_at` the second read
 * returns, using the browser's own Intl -- same ICU the product renders with, so this is not a
 * Node-vs-Chromium formatting difference.  What the arm actually claims is:
 *   T1/T2  the raw ISO shape is gone from the cell;
 *   T3     the cell equals the device-zone rendering of the instant the server holds for the same
 *          activity id (a client-side echo would pass T1/T2 and still fail here);
 *   T4     the row's two other children are untouched;
 *   T5     the cell follows the language the screen opened in.
 */
import { expect, test, type Page } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

const TICK = '[data-testid="v13-pick-candidate"]';
const CARDS = "article.v8-stay-card";
const FINISH = '[data-testid="v13-discovery-finish-batch"]';
const RECEIPT = '[data-testid="v13-discovery-batch-receipt"]';
const ROW = '[data-testid="v13-discovery-batch-row"]';
const PLAN_LINE = ".v8-batch-receipt-plan";
const FILE = "frontend/e2e/qoder-duanwagong-0553-batch-row-instant-r1.spec.ts";
const RUN = process.env.CITYNEXUS_E2E_RUN_ID ?? "dev";
const EVIDENCE_DIR = path.join(process.cwd(), "..", "review", "duanwagong", "readouts");

const LOCALES: Array<["zh-CN" | "en", string]> = [
  ["zh-CN", "zh"],
  ["en", "en"],
];

const readings: Record<string, Record<string, unknown>> = {};

test.afterEach(({}, info) => {
  const arm = /^T(\w+)/.exec(info.title)?.[0] ?? info.title.slice(0, 6);
  fs.mkdirSync(EVIDENCE_DIR, { recursive: true });
  const body = readings[arm] ?? {};
  fs.writeFileSync(
    path.join(EVIDENCE_DIR, `dwg0553__${arm}.json`),
    JSON.stringify({ run_id: RUN, spec: FILE, arm, ...body }, null, 1),
    "utf-8",
  );
});

const node = (arm: string, text: string) => `[dwg-0553 ${arm}] ${text}`;

async function openConsole(page: Page, locale: "zh-CN" | "en", arm: string) {
  let journeyId = "";
  const scene = await page.request.get("/api/v1/demo/scene");
  const sceneStatus = scene.status();
  if (sceneStatus === 200) {
    journeyId = String(((await scene.json()) as { journey_id?: string }).journey_id ?? "");
  }
  if (journeyId.length < 8) {
    const token = process.env.CITYNEXUS_DEMO_RESET_TOKEN;
    const seeded = await page.request.post("/api/v1/demo/reset", {
      headers: token ? { "X-Demo-Reset-Token": token } : {},
    });
    expect(
      seeded.status(),
      node(arm, `the stage held no journey (scene http ${sceneStatus}) and seeding answered ${seeded.status()}`),
    ).toBe(200);
    journeyId = String(((await seeded.json()) as { journey_id?: string }).journey_id ?? "");
  }
  expect(journeyId.length > 8, node(arm, "the stage named no journey, so there is no console to open")).toBe(true);

  await page.addInitScript((seed) => {
    localStorage.clear();
    localStorage.setItem("citynexus.locale", seed.locale);
    localStorage.setItem("citynexus.v8.journey_id", seed.journey);
  }, { locale, journey: journeyId });

  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/v8/hub", { waitUntil: "load" });
  await expect(page.getByTestId("today-hero"), node(arm, `Today never rendered in ${locale}`)).toBeVisible({
    timeout: 30_000,
  });
  await page.goto("/v8/discover", { waitUntil: "load" });
  await expect(page.getByTestId("v13-discovery-goal"), node(arm, "the discovery console never mounted")).toBeVisible({
    timeout: 30_000,
  });

  await page.locator('select[aria-label]').first().selectOption("replay");
  await page.getByTestId("v13-discover-submit").click();
  await expect(page.getByTestId("v13-discovery-result"), node(arm, "the console answered with no result block")).toBeVisible({
    timeout: 60_000,
  });
  await expect
    .poll(async () => await page.locator(CARDS).count(), {
      message: node(arm, "no result card rendered, so there is nothing to tick"),
      timeout: 30_000,
    })
    .toBeGreaterThan(0);

  return { journeyId, sceneStatus };
}

for (const [locale, tag] of LOCALES) {
  const arm = `T${tag}`;
  test(`T${tag} - the batch row renders the instant in ${locale}`, async ({ page, request }) => {
    test.setTimeout(360_000);
    const boot = await openConsole(page, locale, arm);

    await page.locator(TICK).first().click();
    await page.waitForTimeout(200);
    await page.locator(FINISH).click();
    await expect(page.locator(RECEIPT), node(arm, "the batch produced no read-back block")).toBeVisible({
      timeout: 60_000,
    });
    await page.waitForTimeout(800);

    const cell = page.locator(`${ROW} span`).first();
    const shown = (await cell.innerText()).replace(/\s+/g, " ").trim();
    const rowText = (await page.locator(ROW).first().innerText()).replace(/\s+/g, " ");
    const activityId = /([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/.exec(rowText)?.[1] ?? null;
    const planLine = (await page.locator(`${RECEIPT} ${PLAN_LINE}`).first().innerText()).replace(/\s+/g, " ");
    const planId = /([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/.exec(planLine)?.[1] ?? null;

    /* The second read: what the store really holds for that activity, not the browser's memory. */
    const again = planId ? await request.get(`/api/v1/plans/${planId}`) : null;
    const payload = again
      ? ((await again.json()) as { activities?: Array<{ id: string; start_at: string }> })
      : null;
    const serverStartAt =
      (payload?.activities ?? []).find((a) => a.id === activityId)?.start_at ?? null;

    /* Recompute the traveller's reading from the server's raw instant, in the page, with the
       browser's own Intl and the browser's own device zone. */
    const expected =
      serverStartAt === null
        ? null
        : await page.evaluate((raw) =>
            new Intl.DateTimeFormat(
              localStorage.getItem("citynexus.locale") === "zh-CN" ? "zh-CN" : "en-GB",
              { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" },
            ).format(new Date(raw)),
          serverStartAt);
    const deviceZone = await page.evaluate(() => Intl.DateTimeFormat().resolvedOptions().timeZone);

    fs.mkdirSync(EVIDENCE_DIR, { recursive: true });
    await page.screenshot({
      path: path.join(EVIDENCE_DIR, `dwg0553_${arm}_${RUN}.png`),
      fullPage: true,
    });

    readings[arm] = {
      spec: FILE,
      run_id: RUN,
      locale,
      journey_id: boot.journeyId,
      scene_status: boot.sceneStatus,
      plan_id: planId,
      activity_id: activityId,
      server_start_at: serverStartAt,
      cell_on_screen: shown,
      expected_from_server_instant: expected,
      device_zone: deviceZone,
      row_text: rowText,
    };

    expect(activityId, node(arm, `the row carries no activity id (row read "${rowText}")`)).not.toBeNull();
    expect(planId, node(arm, `the read-back block named no plan (line read "${planLine}")`)).not.toBeNull();
    expect(again?.status(), node(arm, `second read of plan ${planId} answered ${again?.status()}`)).toBe(200);
    expect(serverStartAt, node(arm, `activity ${activityId} is not in the plan the server returned`)).not.toBeNull();

    /* T1 / T2 -- the ISO shape the order was written about is off the screen. */
    expect(/\d{4}-\d{2}-\d{2}/.test(shown), node(arm, `the cell still prints an ISO date: "${shown}"`)).toBe(false);
    expect(/\d{2}:\d{2}:\d{2}/.test(shown), node(arm, `the cell still prints seconds from the raw instant: "${shown}"`)).toBe(false);

    /* T3 -- and it prints the instant the store holds, in the device zone. */
    expect(shown, node(arm, `cell "${shown}" is not the device-zone reading "${expected}" of ${serverStartAt}`)).toBe(expected ?? "");

    /* T4 -- the row's other two children survived the move. */
    expect(rowText, node(arm, `the row lost its activity id (row read "${rowText}")`)).toContain(String(activityId));
    expect(rowText.length, node(arm, "the row renders no title beside the time")).toBeGreaterThan(String(activityId).length + 4);

    /* T5 -- the cell follows the language the screen opened in. */
    if (locale === "zh-CN") {
      expect(shown, node(arm, `zh screen printed a non-Chinese date: "${shown}"`)).toContain("月");
    } else {
      expect(/^[A-Z][a-z]{2} \d/.test(shown), node(arm, `en screen printed a non-English date: "${shown}"`)).toBe(true);
    }
  });
}
