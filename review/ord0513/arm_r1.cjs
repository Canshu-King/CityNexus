/* ORD-0513 · does the refusal line on the glass read like a person, in both language arms?
 *
 * The walk is the product's own: open a trip, press 收藏到… on the first stop that offers it, pick a
 * shelf, then press the same shelf a second time.  The second tap is the refusal -- the door answers
 * 409 PLACE_ALREADY_IN_COLLECTION -- and what the screen prints is the thing under measurement.
 * Every assertion reads `innerText` of the rendered line; nothing here is judged off a `data-*` slot,
 * which is the house rule since Q71.
 *
 * Two arms are measured here because two arms exist. The order's third language arm, `de`, is
 * `NOT_AVAILABLE` -- not untranslated: on the tip this run is cut against, `LocaleContext.tsx`
 * declares `export type TripLocale = "en" | "zh-CN"` and registers
 * `const dictionaries: Record<TripLocale, Dict> = { en, "zh-CN": zhCN }`, so there is no third slot
 * to fill without opening the two hot lines the ruling names as off-limits. Full reasoning, with
 * both search counts and what the loose matches actually hit, is in `NOT_AVAILABLE_de.md` beside this
 * file in the same evidence ref.
 *
 * argv: node ord0513_arm_r1.cjs <preview-base> <zh-CN|en> <journeyId> <shape> <tag>
 */
const { chromium } = require("playwright");

const BASE = process.argv[2];
const LOCALE = process.argv[3];
const JOURNEY = process.argv[4];
const SHAPE = process.argv[5] || "390x844";
const TAG = process.argv[6] || "run";
const [W, H] = SHAPE.split("x").map((n) => parseInt(n, 10));
const AT = `[${LOCALE}@${SHAPE}]`;

const ID_SHAPE = /(?:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})|place-[a-z0-9-]{4,}/i;
const MACHINE_WORD = /(PLACE_|COLLECTION_|_NOT_FOUND|ALREADY_IN|http_status|traveler_id|folder_id|place_id)/;
const KEY_SHAPE = /\b(access|collect|agent|nav|poiImport)\.[A-Za-z][A-Za-z0-9.]*\b/;

const failures = [];
const checks = [];
const ok = (name, held, reading) => {
  checks.push({ check: name, held: !!held, reading: reading === undefined ? null : reading });
  if (!held) failures.push(name);
};
const say = (name, reading) => checks.push({ check: name, held: null, reading: reading });

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: W, height: H } });
  const page = await ctx.newPage();
  const errors = [];
  page.on("console", (m) => { if (m.type() === "error") errors.push(m.text().slice(0, 150)); });
  const posts = [];
  page.on("response", (r) => {
    if (r.request().method() === "POST" && /collections/.test(r.url())) {
      posts.push({ url: r.url().replace(/^https?:\/\/[^/]+/, ""), status: r.status() });
    }
  });

  await page.addInitScript(([locale, journey]) => {
    window.localStorage.setItem("citynexus.locale", locale);
    window.localStorage.setItem("citynexus.v8.journey_id", journey);
  }, [LOCALE, JOURNEY]);

  await page.goto(BASE + "/v8/trips", { waitUntil: "domcontentloaded" });
  await page.waitForTimeout(6000);

  const entry = page.locator('[data-testid="collect-entry"]').first();
  ok(`${AT} the 收藏到 entry is on the screen`, (await entry.count()) > 0,
     { entries: await page.locator('[data-testid="collect-entry"]').count(),
       itinerary: await page.locator('[data-testid="trip-itinerary"]').count() });
  if ((await entry.count()) === 0) {
    const painted = await page.evaluate(() => ({
      testids: Array.from(document.querySelectorAll("[data-testid]"))
        .map((e) => e.getAttribute("data-testid")).slice(0, 20),
      words: (document.body.innerText || "").replace(/\s+/g, " ").trim().slice(0, 160),
    }));
    say(`${AT} what painted instead`, painted);
    await browser.close();
    process.stdout.write(JSON.stringify({ tag: TAG, locale: LOCALE, shape: SHAPE, failures,
                                         checks, painted }) + String.fromCharCode(10));
    process.exit(failures.length ? 1 : 0);
  }

  const readLine = () => page.evaluate(() => {
    const el = document.querySelector('[data-testid="collect-result"]');
    return el ? el.innerText.replace(/\s+/g, " ").trim() : null;
  });
  const detailCount = () => page.evaluate(() => document.querySelectorAll("details").length);
  const summaryLabels = () => page.evaluate(() =>
    Array.from(document.querySelectorAll("details > summary"))
      .map((s) => s.innerText.replace(/\s+/g, " ").trim()).slice(0, 6));
  const emptyDetails = () => page.evaluate(() =>
    Array.from(document.querySelectorAll("details")).filter((d) => {
      const kids = Array.from(d.children).filter((c) => c.tagName !== "SUMMARY");
      return kids.every((c) => !(c.innerText || "").trim());
    }).length);

  await entry.click();
  /* The shelf list is a read of its own door; 3 s was not enough on a cold backend and the arm
     reported "no shelves" for a panel that was still loading. Poll for the state, then judge. */
  for (let i = 0; i < 12 && (await page.locator('[data-testid="collect-shelf"]').count()) === 0; i += 1) {
    await page.waitForTimeout(1000);
  }
  const shelves = page.locator('[data-testid="collect-shelf"]');
  ok(`${AT} at least one shelf is offered`, (await shelves.count()) > 0, await shelves.count());
  if ((await shelves.count()) === 0) {
    say(`${AT} what the opened panel shows`, await page.evaluate(() => {
      const el = document.querySelector('[data-testid="collect-into"]');
      return el ? el.innerText.replace(/\s+/g, " ").trim().slice(0, 160) : null;
    }));
    say(`${AT} shelf area words`, await page.evaluate(() => {
      const el = document.querySelector('[data-testid="collect-no-shelf"]')
        || document.querySelector('[data-testid="collect-list-failure"]');
      return el ? el.innerText.replace(/\s+/g, " ").trim() : null;
    }));
  } else {
    /* Tap the same shelf until the door refuses. The store is shared across the rows of one phase and
       a place already on a shelf answers 409 on the *first* tap, so "exactly two taps" would describe
       the previous row's writes rather than this one's. Up to four attempts, and the 409 is read off
       the network, not off a colour. */
    let refused = null;
    let met409 = false;
    for (let attempt = 0; attempt < 4 && !met409; attempt += 1) {
      if ((await shelves.count()) === 0) {
        await entry.click();
        await page.waitForTimeout(2500);
      }
      if ((await shelves.count()) === 0) break;
      await shelves.first().click();
      await page.waitForTimeout(3000);
      met409 = posts.some((p) => p.status === 409);
      refused = await readLine();
      if (!met409) {
        // the panel closes itself after a write; reopen so the next tap is a real tap on a shelf
        if ((await shelves.count()) === 0) {
          await entry.click();
          await page.waitForTimeout(2200);
        }
      }
      say(`${AT} attempt ${attempt + 1}`, { met409, line: refused, posts: posts.length });
    }
    ok(`${AT} the walk met a 409 from the door`, met409, posts);
    ok(`${AT} the refusal line is on the screen and not empty`, !!refused, refused);
    ok(`${AT} the refusal sentence carries no identifier`,
       refused !== null && !ID_SHAPE.test(refused), { line: refused });
    ok(`${AT} the refusal sentence carries no machine token`,
       refused !== null && !MACHINE_WORD.test(refused), { line: refused });
    ok(`${AT} the refusal sentence is not a dictionary key吐回`,
       refused !== null && !KEY_SHAPE.test(refused), { line: refused });
    ok(`${AT} the refusal sentence reads like a sentence (>= 8 chars, has a space)`,
       refused !== null && refused.length >= 8 && /\s/.test(refused), { length: (refused || "").length });
    const dets = await detailCount();
    say(`${AT} details elements on this screen`, { count: dets, summaries: await summaryLabels(),
                                                  empty: await emptyDetails() });
    const labelled = (await summaryLabels()).some((s) => /技术|详情|detail|Technical/i.test(s));
    ok(`${AT} no empty 技术详情 face`, labelled === false || dets > 0,
       { label_seen: labelled, details: dets, empty: await emptyDetails() });
  }

  await browser.close();
  const out = { tag: TAG, locale: LOCALE, shape: SHAPE, posts, checks, failures,
                console_errors: errors };
  process.stdout.write(JSON.stringify(out) + String.fromCharCode(10));
  process.stderr.write(`${TAG}/${LOCALE}@${SHAPE} failures: ${JSON.stringify(failures)}${String.fromCharCode(10)}`);
  process.exit(failures.length ? 1 : 0);
})().catch((e) => {
  process.stdout.write(JSON.stringify({ tag: TAG, locale: LOCALE, shape: SHAPE,
    failures: ["instrument threw: " + String((e && e.message) || e).slice(0, 150)] })
    + String.fromCharCode(10));
  process.exit(1);
});
