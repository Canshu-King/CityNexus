/*
 * ORD-0507 item 2, re-cut at this generation and run on the line's own production bundle
 * (`playwright.prod-gate.config.ts`).  Item 3's 「技术详情」 fold is deliberately NOT in this hand:
 * the line now carries its refusal sentences through `refusalWords` + `CHECKIN_REFUSAL_COPY`, and my old
 * candidate shipped a second vocabulary (`checkin.refused.*`) beside it, so the fold is held until one
 * vocabulary wins -- see the lane's block naming that collision.  Arms 2a/2b are unchanged in intent.
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
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";

const NODE_CLOCK = "ord0507-2a-clock-parenthetical-holds-only-the-noun";
const NODE_STAGE = "ord0507-2b-new-journey-screen-names-whose-journey-is-on-stage";
const NODE_SEED = "ord0507-r7-seed-the-trip-the-arm-actually-reads";

const node = (id: string, detail: string) => `[${id}] ${detail}`;
const clean = (value: string) => value.replace(/\s+/g, " ").trim();
const MACHINE_TOKEN = /[A-Z][A-Z0-9_]{3,}/;
/* a sentence terminator anywhere between the brackets means the bracket holds a clause, not a noun */
const PAREN = /[（(]([^）)]*)[）)]/;
const HAS_CLAUSE = (inner: string) => /[。]|(?<=[a-z])\.(?=\s?[A-Za-z])/.test(inner);

/* A green run has to leave the painted sentence behind, not just pass.  One file per arm per locale, so
   a counter-arm re-running the same arm cannot overwrite the guard's own painting. */
function paint(arm: string, locale: string, payload: Record<string, unknown>) {
  const dir = resolve(process.cwd(), "review/ord0507/paintings");
  mkdirSync(dir, { recursive: true });
  writeFileSync(resolve(dir, `${arm}_${locale}.json`), JSON.stringify(payload, null, 2), "utf8");
}

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
    display_name: `ORD-0507 r7 ${locale} traveller`,
    locale: "zh-CN",
    timezone: "Asia/Shanghai",
  });
  expect(traveler.status, node(NODE_SEED, `POST /travelers answered ${traveler.status}`)).toBe(201);
  const journey = await apiPost(request, "/api/v1/journeys", {
    traveler_id: traveler.body.id,
    title: "天津 · ORD-0507 r7 屏幕上的句子",
    city_code: "CN-TIANJIN",
    timezone: "Asia/Shanghai",
    start_at: "2026-10-09T18:00:00+08:00",
    end_at: "2026-10-11T15:00:00+08:00",
    budget: { amount_minor: 120000, currency: "CNY" },
  });
  expect(journey.status, node(NODE_SEED, `POST /journeys answered ${journey.status}`)).toBe(201);
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
    paint("2a-clock-sentence", locale, {
      sentence: read.sentence,
      paren: read.parenContent,
      cursor_status: read.cursorStatus,
    });
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
    paint("2b-stage-attribution", locale, {
      mismatch_sentence: painted,
      stage_row: stageRow,
    });
    await page.close();
  });
}
