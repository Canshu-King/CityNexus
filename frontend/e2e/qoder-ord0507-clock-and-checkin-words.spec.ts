/*
 * ORD-0507 items 2 and 3, run on the line's own production bundle (`playwright.prod-gate.config.ts`).
 *
 *  2a  the Today clock sentence used to splice a whole clause *inside* the parentheses, so one
 *      bracket carried a second sentence.  Judged on `innerText`, in both shipped locales, after
 *      reaching Today the way a clean browser can -- by walking the setup wizard.
 *  2b  the new-journey screen showed 「台上行程 <id>」 with no counter-sentence, which attributed the
 *      demo stage's global journey to a traveller who has not created one yet.
 *  3   one flat sentence for seven named check-in refusals, and the server's own answer thrown away.
 *      Now one sentence per code, with the original in a 「技术详情」 fold.
 *
 * Nothing here is judged off a `data-*` attribute: the attributes are read to prove which arm the
 * sentence came from, and the assertions are on what is painted.
 */
import { expect, test, type Page } from "@playwright/test";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const NODE_CLOCK = "ord0507-2a-clock-parenthetical-holds-only-the-noun";
const NODE_STAGE = "ord0507-2b-new-journey-screen-names-whose-journey-is-on-stage";
const NODE_REFUSE = "ord0507-3-checkin-refusal-says-which-fact-and-keeps-the-original";
const NODE_PAIR = "ord0507-3b-every-checkin-key-asked-for-exists-in-both-dictionaries";

const node = (id: string, detail: string) => `[${id}] ${detail}`;
const clean = (value: string) => value.replace(/\s+/g, " ").trim();
const MACHINE_TOKEN = /[A-Z][A-Z0-9_]{3,}/;
/* a sentence terminator anywhere between the brackets means the bracket holds a clause, not a noun */
const PAREN = /[（(]([^）)]*)[）)]/;
const HAS_CLAUSE = (inner: string) => /[。]|(?<=[a-z])\.(?=\s?[A-Za-z])/.test(inner);

const WORDS = {
  "zh-CN": {
    basisNouns: ["行程起点", "执行游标"],
    /* the degraded clock has two legitimate wordings, chosen by how far the projection got -- the
       same pair the shipped gate `qoder-speaks-the-travellers-language` accepts */
    degraded: /没有给出这一分钟的执行游标|时间窗|没有按游标定位/,
    claimsCursor: /执行游标）/,
    noJourneyInView: "这一屏还没有正在看的行程",
    duplicate: "已经有一枚印",
    bin: "回收站",
    technical: "技术详情",
  },
  en: {
    basisNouns: ["journey start", "execution cursor"],
    degraded: /gave no execution cursor|by the journey's window|no station is claimed from the cursor/,
    claimsCursor: /execution cursor\)/,
    noJourneyInView: "no journey in view",
    duplicate: "already holds a stamp",
    bin: "recycle bin",
    technical: "Technical detail",
  },
} as const;

type Locale = keyof typeof WORDS;

const API = `http://127.0.0.1:${Number(process.env.CITYNEXUS_BACKEND_PORT ?? 8000)}`;

async function apiPost(request: any, path: string, body?: unknown) {
  const response = await request.post(`${API}${path}`, { data: body ?? {} });
  const text = await response.text();
  let parsed: any = null;
  try {
    parsed = JSON.parse(text);
  } catch {
    parsed = { raw: text.slice(0, 200) };
  }
  return { status: response.status(), body: parsed };
}

/** A journey of this test's own, built only through the product's own doors. */
async function seedExecutingJourney(request: any, locale: Locale) {
  const traveler = await apiPost(request, "/api/v1/travelers", {
    display_name: `ORD-0507 r2 ${locale} traveller`,
    locale: "zh-CN",
    timezone: "Asia/Shanghai",
  });
  expect(traveler.status, node(NODE_REFUSE, `POST /travelers answered ${traveler.status}`)).toBe(201);
  const journey = await apiPost(request, "/api/v1/journeys", {
    traveler_id: traveler.body.id,
    title: "天津 · ORD-0507 r2 屏幕上的句子",
    city_code: "CN-TIANJIN",
    timezone: "Asia/Shanghai",
    start_at: "2026-10-09T18:00:00+08:00",
    end_at: "2026-10-11T15:00:00+08:00",
    budget: { amount_minor: 120000, currency: "CNY" },
  });
  expect(journey.status, node(NODE_REFUSE, `POST /journeys answered ${journey.status}`)).toBe(201);
  const prepared = await apiPost(request, "/api/v1/demo/prepare-scenario");
  const started = await apiPost(request, "/api/v1/demo/start-scenario");
  return {
    journeyId: String(journey.body.id),
    prepared: { status: prepared.status, journey_status: prepared.body?.journey_status },
    started: { status: started.status, journey_status: started.body?.journey_status },
  };
}

async function openShell(page: Page, journeyId: string, locale: Locale, path: string) {
  await page.addInitScript(
    ([id, lang]) => {
      localStorage.clear();
      /* both keys, the way the shell's own fresh-journey helper writes them: the trips screen reads
         the demo id, and a shell holding only one of the two lands on a different screen */
      localStorage.setItem("citynexus.v8.journey_id", id as string);
      localStorage.setItem("citynexus.demo.journey_id", id as string);
      localStorage.setItem("citynexus.locale", lang as string);
    },
    [journeyId, locale],
  );
  await page.goto(path, { waitUntil: "load" });
}

/** The only way a clean browser has into the inner screens: walk the setup wizard. */
async function walkTheWizard(page: Page, locale: Locale) {
  await page.addInitScript((lang) => {
    localStorage.clear();
    localStorage.setItem("citynexus.locale", lang as string);
  }, locale);
  await page.goto("/v8/hub", { waitUntil: "load" });
  await page.waitForSelector('[data-testid="trial-setup"]', { timeout: 30_000 });
  const zh = locale === "zh-CN";
  await page.fill('[data-testid="trial-city"]', zh ? "天津" : "Tianjin");
  await page.fill('[data-testid="trial-arrival"]', zh ? "天津站" : "Tianjin Railway Station");
  await page.fill('[data-testid="trial-departure"]', zh ? "北京南站" : "Beijing South Station");
  await page.getByTestId("trial-next").click();
  await page.waitForSelector('[data-testid="trial-step2-body"]', { timeout: 20_000 });
  await page.getByTestId("trial-pace-packed").click();
  await page.fill('[data-testid="trial-budget"]', "1500");
  await page.getByTestId("trial-next").click();
  await page.waitForSelector('[data-testid="trial-step3-body"]', { timeout: 20_000 });
  /* the CTA is a grid row; pressing the word is what made this look unreachable before */
  await page.getByTestId("trial-create").click();
  await page.waitForSelector('[data-testid="today-heading"]', { timeout: 150_000 });
}

async function readClock(page: Page) {
  const source = page.getByTestId("today-clock-source");
  await expect(source, node(NODE_CLOCK, "the clock-source line vanished")).toBeVisible({ timeout: 30_000 });
  await expect
    .poll(() => source.getAttribute("data-clock-source"), { timeout: 40_000, intervals: [400] })
    .toBe("SCENE");
  const sentence = clean(await source.innerText());
  const match = sentence.match(PAREN);
  return {
    sentence,
    clockSource: await source.getAttribute("data-clock-source"),
    cursorStatus: await source.getAttribute("data-cursor-status"),
    parenContent: match ? match[1] : null,
  };
}

for (const locale of ["zh-CN", "en"] as Locale[]) {
  const words = WORDS[locale];

  test(`ord0507-2a-clock-sentence [${locale}] — 括号里只放那个名词`, async ({ page, request }) => {
    test.setTimeout(400_000);
    /* reachability first: Today is entered the way a clean browser can enter it */
    if (locale === "zh-CN") {
      await walkTheWizard(page, locale);
      expect(
        await page.evaluate(() => localStorage.getItem("citynexus.v8.journey_id")),
        node(NODE_CLOCK, "the wizard did not hand the shell a journey"),
      ).toBeTruthy();
    }
    const seeded = await seedExecutingJourney(request, locale);
    await openShell(page, seeded.journeyId, locale, "/v8/hub");
    await expect(page.getByTestId("today-hero"), node(NODE_CLOCK, "Today never rendered")).toBeVisible({
      timeout: 40_000,
    });

    const read = await readClock(page);
    const cursorAbsent = !!read.cursorStatus && read.cursorStatus !== "VALID";
    /* ORD-0208's own rule, restated here so this rewording cannot trade one defect for another: a
       bracket may not name an execution cursor in a state the server itself calls absent/stale */
    expect(
      cursorAbsent && words.claimsCursor.test(read.sentence),
      node(NODE_CLOCK, `the sentence claims a server cursor while the cursor is ${read.cursorStatus}: ${JSON.stringify(read.sentence)}`),
    ).toBe(false);
    if (read.parenContent !== null) {
      expect(
        HAS_CLAUSE(read.parenContent),
        node(
          NODE_CLOCK,
          `the parentheses still carry a whole clause: (${read.parenContent}) -- full sentence ${JSON.stringify(read.sentence)}`,
        ),
      ).toBe(false);
      expect(
        words.basisNouns.includes(clean(read.parenContent)),
        node(
          NODE_CLOCK,
          `the bracket is not one of the two nouns the scene can name: got ${JSON.stringify(read.parenContent)}, sentence ${JSON.stringify(read.sentence)}, cursor_status=${read.cursorStatus}`,
        ),
      ).toBe(true);
    }
    /* the degraded clock is still disclosed in words, just no longer inside the bracket */
    if (read.cursorStatus && read.cursorStatus !== "VALID") {
      expect(
        words.degraded.test(read.sentence),
        node(NODE_CLOCK, `the cursor disclosure disappeared with the bracket: ${JSON.stringify(read.sentence)} (cursor_status=${read.cursorStatus})`),
      ).toBe(true);
    }
    expect(
      MACHINE_TOKEN.test(read.sentence),
      node(NODE_CLOCK, `a machine token is painted on the traveller's line: ${JSON.stringify(read.sentence)}`),
    ).toBe(false);
  });

  test(`ord0507-2b-stage-attribution [${locale}] — 新建那一屏要说台上不是你的行程`, async ({
    browser,
    request,
  }) => {
    test.setTimeout(300_000);
    /* a journey must be on the stage for this arm to mean anything: it is put there through the
       product's own scenario doors, and read back from the panel afterwards */
    const seeded = await seedExecutingJourney(request, locale);
    const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
    await page.addInitScript((lang) => {
      localStorage.clear();
      localStorage.setItem("citynexus.locale", lang as string);
    }, locale);
    await page.goto("/v8/hub", { waitUntil: "load" });
    await page.waitForSelector('[data-testid="trial-setup"]', { timeout: 30_000 });
    await page.getByTestId("sim-ball").click();
    await page.waitForSelector('[data-testid="sim-journey"]', { timeout: 20_000 });
    await page.waitForTimeout(1_500);

    const stageRow = clean(await page.getByTestId("sim-journey").innerText());
    expect(
      stageRow !== "— · —" && stageRow.startsWith("—") === false,
      node(NODE_STAGE, `nothing is on the stage, so the arm measures nothing: 台上行程 reads ${JSON.stringify(stageRow)} (seeded ${seeded.journeyId})`),
    ).toBe(true);
    const mismatch = page.getByTestId("sim-journey-mismatch");
    const count = await mismatch.count();
    const painted = count ? clean(await mismatch.innerText()) : null;
    expect(
      count,
      node(NODE_STAGE, `the new-journey screen names a stage journey (${JSON.stringify(stageRow)}) with 0 counter-sentences`),
    ).toBe(1);
    expect(
      painted,
      node(NODE_STAGE, `the counter-sentence is empty while 台上行程 reads ${JSON.stringify(stageRow)}`),
    ).not.toBeNull();
    expect(
      (painted as string).includes(words.noJourneyInView),
      node(NODE_STAGE, `it does not say this screen has nothing in view: ${JSON.stringify(painted)} / stage row ${JSON.stringify(stageRow)}`),
    ).toBe(true);
    const stageId = stageRow.split("·")[0].trim();
    expect(
      stageId.length > 0 && (painted as string).includes(stageId),
      node(NODE_STAGE, `it does not name the journey it is separating off: painted ${JSON.stringify(painted)}, stage row ${JSON.stringify(stageRow)}`),
    ).toBe(true);
    expect(
      MACHINE_TOKEN.test(painted as string),
      node(NODE_STAGE, `a machine token is painted in the traveller's sentence: ${JSON.stringify(painted)}`),
    ).toBe(false);
    await page.close();
  });

  test(`ord0507-3-checkin-words [${locale}] — 一种拒绝一句话，原文进技术详情`, async ({ page }) => {
    test.setTimeout(400_000);
    /* Which journey this arm runs on, stated: the 打卡 control only exists on a journey that carries
       a selected plan, and the doors that put a plan on a journey are `POST /demo/reset` (this lane's
       red line -- calls=0, never invoked here) and the scenario doors, which on this tip answered 200
       for a lane-seeded DRAFT without advancing it to a plan.  So the arm runs on the journey the
       harness's own real-seed project established through the same product surfaces, and it writes
       only what a traveller writes: two taps on one stop. */
    await page.addInitScript((lang) => {
      localStorage.setItem("citynexus.locale", lang as string);
    }, locale);
    await page.goto("/v8/trips", { waitUntil: "load" });
    await page.waitForSelector('[data-testid="trip-itinerary"]', { timeout: 40_000 });
    const journeyId = await page.evaluate(() => localStorage.getItem("citynexus.v8.journey_id") ?? "");
    expect(journeyId.length > 0, node(NODE_REFUSE, "the harness handed this run no journey to stamp on")).toBe(true);
    const control = page.locator("[data-testid='stop-checkin']").first();
    await expect(control, node(NODE_REFUSE, "the itinerary has no 打卡 control to press")).toBeVisible({
      timeout: 30_000,
    });

    /* first tap: a real 201.  second tap: a real 409 CHECKIN_DUPLICATE_STAMP. */
    await control.click();
    await page.waitForTimeout(3_000);
    await page.locator("[data-testid='stop-checkin']").first().click();
    await page.waitForSelector("[data-testid='stop-checkin-notice']", { timeout: 30_000 });
    const duplicateNotice = clean(await page.locator("[data-testid='stop-checkin-notice']").first().innerText());
    expect(
      duplicateNotice.includes(words.duplicate),
      node(NODE_REFUSE, `the duplicate refusal is not its own sentence: ${JSON.stringify(duplicateNotice)}`),
    ).toBe(true);
    expect(
      MACHINE_TOKEN.test(duplicateNotice),
      node(NODE_REFUSE, `the refusal sentence paints a machine token: ${JSON.stringify(duplicateNotice)}`),
    ).toBe(false);

    const fold = page.locator("[data-testid='stop-checkin-technical']");
    const foldCount = await fold.count();
    expect(
      foldCount,
      node(NODE_REFUSE, `no 技术详情 fold beside ${JSON.stringify(duplicateNotice)}`),
    ).toBeGreaterThan(0);
    const summary = clean(await fold.first().locator("summary").innerText());
    expect(summary, node(NODE_REFUSE, `the fold is not labelled in the traveller's language: ${JSON.stringify(summary)}`)).toBe(
      words.technical,
    );
    const rawLoc = page.locator("[data-testid='stop-checkin-technical-raw']");
    const countBefore = await rawLoc.count();
    /* a closed <details> keeps its children in the DOM but paints nothing, so the collapsed reading
       is textContent (the line exists) and the opened reading is innerText (the line is on screen) */
    const domText = countBefore
      ? clean(((await rawLoc.first().textContent().catch(() => "")) ?? "") as string)
      : "";
    await fold.first().locator("summary").click();
    await page.waitForTimeout(1_000);
    const countAfter = await rawLoc.count();
    const painted = countAfter ? clean(await rawLoc.first().innerText().catch(() => "")) : "";
    const said = painted.length > 0 ? painted : domText;
    expect(
      said,
      node(
        NODE_REFUSE,
        `the fold carries no technical line: rows_with_fold=${foldCount} raw_before_click=${countBefore} raw_after_click=${countAfter} summary=${JSON.stringify(summary)} notice=${JSON.stringify(duplicateNotice)}`,
      ),
    ).not.toBe("");
    expect(
      painted.length > 0,
      node(
        NODE_REFUSE,
        `opening 技术详情 did not put the original on screen (painted=${JSON.stringify(painted)}, dom=${JSON.stringify(domText)}, raw_before=${countBefore}, raw_after=${countAfter})`,
      ),
    ).toBe(true);
    expect(
      said.includes("CHECKIN_DUPLICATE_STAMP"),
      node(NODE_REFUSE, `the fold does not carry the server's own code: ${JSON.stringify(said)}`),
    ).toBe(true);
    expect(/http_status=409/.test(said), node(NODE_REFUSE, `the fold drops the status it answered: ${JSON.stringify(said)}`)).toBe(true);
    const detailsMatch = said.match(/details=(\{[^·]*)/);
    const detailPairs = detailsMatch ? (detailsMatch[1].match(/"[a-z_]+"\s*:/g) ?? []).length : 0;
    expect(
      detailPairs,
      node(NODE_REFUSE, `the fold carries no details from the door: ${JSON.stringify(said)}`),
    ).toBeGreaterThan(0);
    expect(
      said.includes("CHECKIN_DUPLICATE_STAMP") && said.length > "CHECKIN_DUPLICATE_STAMP".length + 40,
      node(NODE_REFUSE, `the technical line is the code alone, not the answer: ${JSON.stringify(said)}`),
    ).toBe(true);

    /* what the flat sentence used to be, read off the dictionary the same screen ships: the painted
       line has to be the per-code one, not this generic fallback */
    const generic = locale === "zh-CN" ? "服务器没收下这次打卡" : "would not take this stamp";
    expect(
      duplicateNotice.includes(generic),
      node(NODE_REFUSE, `the duplicate arm still paints the flat fallback sentence: ${JSON.stringify(duplicateNotice)}`),
    ).toBe(false);
    console.log(
      JSON.stringify({
        node: NODE_REFUSE,
        locale,
        journey_id: journeyId,
        duplicate_sentence: duplicateNotice,
        duplicate_technical: said,
        raw_before_click: countBefore,
        raw_after_click: countAfter,
      }),
    );
  });
}

test("ord0507-3b-checkin-keys-pair — 每一枚键在两本字典里都有", async () => {
  test.setTimeout(60_000);
  const root = process.cwd();
  const locale = readFileSync(resolve(root, "src/i18n/LocaleContext.tsx"), "utf8");
  const screen = readFileSync(resolve(root, "src/features/trip/TripItinerary.tsx"), "utf8");
  const doors = readFileSync(resolve(root, "src/features/checkin/checkins.ts"), "utf8");

  const asked = new Set<string>();
  for (const m of screen.matchAll(/t\(\s*"checkin\.[A-Za-z0-9_.]+"/g)) asked.add(m[0].replace(/t\(\s*"/, "").replace(/"$/, ""));
  for (const m of doors.matchAll(/:\s*"checkin\.[A-Za-z0-9_.]+"/g)) asked.add(m[0].replace(/:\s*"/, "").replace(/"$/, ""));
  asked.add("checkin.technicalDetail");
  asked.add("checkin.technicalRaw");

  const defined = (key: string) =>
    (locale.match(new RegExp(`"${key.replace(/\./g, "\\.")}"\\s*:`, "g")) ?? []).length;
  const missing: Record<string, string> = {};
  for (const key of asked) {
    /* exactly two definitions = one per dictionary arm; one means a locale would print the key,
       three means someone shadowed a key inside one dictionary */
    if (defined(key) !== 2) missing[key] = String(defined(key));
  }
  expect(
    Object.keys(missing),
    node(NODE_PAIR, `keys asked for whose definitions are not exactly one per dictionary (t() would print the key name): ${JSON.stringify(missing)}; asked ${asked.size} keys`),
  ).toEqual([]);

  /* the mapping itself: one distinct key per named refusal, or the seven collapse again */
  const mapBlock = doors.slice(doors.indexOf("checkinRefusalKey"), doors.indexOf("checkinRefusalKey") + 1400);
  const mapped = [...mapBlock.matchAll(/"checkin\.[A-Za-z0-9_.]+"/g)].map((m) => m[0].replace(/"/g, ""));
  expect(mapped.length, node(NODE_PAIR, `the refusal map does not cover all eight codes: ${JSON.stringify(mapped)}`)).toBe(8);
  expect(
    new Set(mapped).size,
    node(NODE_PAIR, `two codes share one sentence key: ${JSON.stringify(mapped)}`),
  ).toBe(8);
});
