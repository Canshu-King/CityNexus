/**
 * ORD-0541 -- the share outlet is idempotent, judged on the requests it makes and the rows the server
 * keeps.
 *
 * The finding, in the words it reached the ledger in: pressing 分享这张图 again minted another grant.
 * Nothing on the traveller's screen said so, and both links worked, so the only evidence that the
 * trip had been shared twice was a roster that kept growing. The commander's ruling for what may be
 * reused is verbatim 「`visibility` 恰为 `LINK_READ` 才算可复用链接」, which is what A3 measures from
 * the other side: a standing row at another tier is not this outlet's link, even though it is a row
 * on the same journey.
 *
 *   A1  two presses, one write: the second press asks the create door for nothing, hands back the same
 *       address, and leaves the server's roster the size it was;
 *   A2  reuse is not "never write" -- withdraw what stands through the server's own revoke door and
 *       the next press mints exactly one grant again;
 *   A3  a standing row whose tier is not `LINK_READ` is not reused (PUBLIC / PRIVATE /
 *       INVITEES_ONLY), and neither is a `LINK_READ` row whose answer carries no token or already
 *       carries a revocation;
 *   A4  when the list door refuses, nothing is written at all -- the press that cannot ask is not a
 *       press that may mint;
 *   A5  the two confirmation sentences are different words, in both shipped languages and both shapes
 *       of screen, with no key name on either.
 *
 * One ruler, three bundles. Pointed at the base generation A1, A2 and A4 go red, because that line
 * writes before it asks; pointed at the bundle with the tier predicate dropped A3 goes red. An arm
 * that is green on all three is not measuring idempotency.
 */
import { mkdirSync, writeFileSync } from "node:fs";
import { expect, test, type Browser, type Page } from "@playwright/test";

const JOURNEY_ID = "22222222-2222-4222-8222-222222222222";
const FRONT = `http://127.0.0.1:${Number(process.env.CITYNEXUS_ORD0541_FRONT)}`;
const GEN = (process.env.CITYNEXUS_ORD0541_GEN ?? "").trim();
const EVIDENCE = (process.env.CITYNEXUS_ORD0541_EVIDENCE ?? "").trim();
for (const [name, value] of [
  ["CITYNEXUS_ORD0541_FRONT", process.env.CITYNEXUS_ORD0541_FRONT],
  ["CITYNEXUS_ORD0541_GEN", GEN],
  ["CITYNEXUS_ORD0541_EVIDENCE", EVIDENCE],
] as const) {
  if (!value) throw new Error(`[ord0541] ${name} must be named by the runner`);
}
mkdirSync(EVIDENCE, { recursive: true });

const DOOR = `/api/v1/journeys/${JOURNEY_ID}/share-grants`;
const GRANT_ID = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i;
/** The two confirmation sentences, taken from the dictionary lines this order ships: 新建 names the
 *  write it did, 复用 names the write it did not. The arms match on the words a traveller reads, not
 *  on a `data-*` attribute, because the claim under test is the one on the screen. */
const WROTE = /确实写入|wrote a new grant/;
const REUSED = /没有再写入|wrote nothing/;

function write(name: string, body: unknown) {
  writeFileSync(`${EVIDENCE}/${name}.json`, JSON.stringify(body, null, 1), "utf8");
  console.log(`O541 ${GEN} ${name} ${JSON.stringify(body).slice(0, 900)}`);
}

/** Open the traveller's poster sheet and count every call to the grant door this page makes. */
async function openSheet(browser: Browser, locale = "zh-CN", viewport = { width: 390, height: 844 }) {
  const context = await browser.newContext({ viewport, hasTouch: viewport.width < 500, locale });
  await context.addInitScript(
    ([language, journey]) => {
      localStorage.setItem("citynexus.locale", language);
      localStorage.setItem("citynexus.v8.journey_id", journey);
    },
    [locale, JOURNEY_ID] as const,
  );
  const page = await context.newPage();
  const calls: string[] = [];
  page.on("request", (request) => {
    if (request.url().includes(DOOR)) calls.push(`${request.method()} ${request.url().replace(FRONT, "")}`);
  });
  await page.goto(`${FRONT}/v8/trips`, { waitUntil: "load", timeout: 90_000 });
  await expect(page.getByTestId("trip-poster-bar").first()).toBeVisible({ timeout: 30_000 });
  await page.waitForTimeout(700);
  await page.getByTestId("poster-open").click();
  await expect(page.getByTestId("trip-poster")).toBeVisible({ timeout: 20_000 });
  return { context, page, calls, posts: () => calls.filter((call) => call.startsWith("POST")).length };
}

/**
 * Press 分享这张图 and read back what the sheet ended up claiming.
 *
 * `previous` is the sentence the sheet was showing before this press. The panel clears its own
 * sentence while it asks, so an empty read means "not answered yet" and a read equal to `previous`
 * means the repaint has not landed -- both keep polling. Reading the line without that guard would
 * let a second press be judged on the first press's sentence.
 */
async function press(page: Page, previous: string | null = null) {
  const result = page.getByTestId("poster-share-result");
  await page.getByTestId("poster-share").click();
  if (previous === null) {
    await expect(result).toBeVisible({ timeout: 30_000 });
  } else {
    await expect
      .poll(
        async () => {
          const text = (await result.innerText().catch(() => "")).trim();
          return text !== "" && text !== previous;
        },
        { timeout: 30_000 },
      )
      .toBe(true);
  }
  const sentence = (await result.innerText()).trim();
  const link = (
    await page.getByTestId("poster-share-link").inputValue({ timeout: 3_000 }).catch(() => "")
  ).trim();
  return {
    state: await result.getAttribute("data-share-state"),
    sentence,
    grant_id: GRANT_ID.exec(sentence)?.[0] ?? null,
    link,
    link_present: await page.getByTestId("poster-share-link").count(),
    key_echo: /\bposter\.[A-Za-z0-9_.]+/.test(sentence),
  };
}

/** The roster, read by this instrument rather than through the sheet's own sentence. `page.request`
 *  is an API context: it is not touched by `page.route`, so a stubbed press cannot fake this read. */
async function roster(page: Page): Promise<any[]> {
  const answer = await page.request.get(`${FRONT}${DOOR}`);
  const body = await answer.json();
  return Array.isArray(body) ? body : [];
}

const tokenOf = (link: string) => /\/v8\/shared\/([^/]+)\/([^/]+)$/.exec(link.trim())?.[1] ?? null;

/** Fake only the press's own asking: the read-back after a real write reaches the real door, so what
 *  an arm confirms is always a row the server actually made. */
async function fakeFirstAsks(page: Page, rows: unknown[], asks = 1) {
  let fakes_left = asks;
  await page.route(`**${DOOR}`, (route) => {
    if (route.request().method() === "GET" && fakes_left > 0) {
      fakes_left -= 1;
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(rows),
      });
    }
    return route.continue();
  });
}

test("ORD-0541 A1 the second press asks the create door for nothing", async ({ browser }) => {
  const { context, page, calls, posts } = await openSheet(browser);
  const rows_before = await roster(page);

  const first = await press(page);
  const posts_after_first = posts();
  const rows_after_first = await roster(page);

  const second = await press(page, first.sentence);
  const posts_after_second = posts();
  const rows_after_second = await roster(page);

  const reading = {
    rows_before: rows_before.length,
    rows_after_first: rows_after_first.length,
    rows_after_second: rows_after_second.length,
    door_calls: calls,
    posts_after_first,
    /** The number this order is about: a second press that writes leaves another grant behind. */
    posts_on_second_press: posts_after_second - posts_after_first,
    first,
    second,
    same_grant_id: first.grant_id !== null && first.grant_id === second.grant_id,
    same_link: first.link !== "" && first.link === second.link,
    same_token: tokenOf(first.link) !== null && tokenOf(first.link) === tokenOf(second.link),
    /** The row the screen handed over, as the server itself describes it. */
    row_the_screen_named: rows_after_second.find((row) => row.id === second.grant_id) ?? null,
  };
  write("A1_two_presses", reading);

  expect(first.state, "the first press confirms").toBe("CONFIRMED");
  expect(second.state, "and so does the second").toBe("CONFIRMED");
  expect(reading.posts_on_second_press, "the second press made no write call at all").toBe(0);
  expect(reading.rows_after_second, "the roster is the size the first press left it").toBe(
    reading.rows_after_first,
  );
  expect(reading.same_link, "the address handed over is the same address").toBe(true);
  expect(reading.same_grant_id, "named by the same row of the server's own list").toBe(true);
  expect(REUSED.test(second.sentence), "and the sheet says in words that it wrote nothing").toBe(true);
  expect(first.key_echo || second.key_echo, "neither sentence is a key name").toBe(false);
  expect(second.link_present, "a reused link is still a link: the field that carries it is present")
    .toBe(1);
  expect(reading.row_the_screen_named?.revoked_at, "and the row it names is standing").toBeNull();
  await context.close();
});

test("ORD-0541 A2 withdrawing what stands makes the next press write again", async ({ browser }) => {
  const { context, page, calls, posts } = await openSheet(browser);
  const first = await press(page);
  const posts_before = posts();

  /* Withdraw every standing link this outlet could reuse, through the server's own revoke door -- the
     product's, not an instrument reaching into the store -- and read the answers back rather than
     assuming the rows went away. All of them, not just the one on screen: the outlet is allowed to
     hand over any standing row, so "nothing reusable is left" is what makes the next press's write
     the honest reading instead of an accident of which row it happened to pick. */
  const standing = (await roster(page)).filter(
    (row) => row.revoked_at === null && row.visibility === "LINK_READ",
  );
  const revoke_statuses: Record<string, number> = {};
  for (const row of standing) {
    revoke_statuses[row.id] = (await page.request.post(`${FRONT}${DOOR}/${row.id}/revoke`)).status();
  }
  const rows_after_revoke = await roster(page);
  const still_standing = rows_after_revoke.filter(
    (row) => row.revoked_at === null && row.visibility === "LINK_READ",
  );
  const row_now = rows_after_revoke.find((row) => row.id === first.grant_id) ?? null;

  const second = await press(page, first.sentence);
  const posts_after = posts();

  const reading = {
    first,
    door_calls: calls,
    rows_revoked_by_this_arm: Object.keys(revoke_statuses).length,
    revoke_http_statuses: revoke_statuses,
    row_named_by_screen_after_revoke: row_now,
    standing_link_read_rows_after_revoke: still_standing.length,
    second,
    posts_on_press_after_revoke: posts_after - posts_before,
    rows_after_revoke: rows_after_revoke.length,
    link_changed: first.link !== second.link,
  };
  write("A2_revoke_then_press", reading);

  /* A precondition, not a product claim: this arm needs something standing to withdraw, and A1 leaves
     exactly that behind. Without it the arm would be "pressed and wrote", which is A3's shape. */
  expect(Object.values(revoke_statuses), "the arm had a standing link to withdraw").not.toHaveLength(0);
  for (const [id, status] of Object.entries(revoke_statuses)) {
    expect(status, `the revoke door answered for ${id}`).toBe(200);
  }
  expect(row_now?.revoked_at, "and the roster says the screen's own row is withdrawn").not.toBeNull();
  expect(reading.standing_link_read_rows_after_revoke, "with nothing link-readable left standing").toBe(0);
  expect(reading.posts_on_press_after_revoke, "the next press writes exactly one grant").toBe(1);
  expect(second.state, "and confirms it the same way as any other write").toBe("CONFIRMED");
  expect(WROTE.test(second.sentence), "with the words that say a write happened").toBe(true);
  expect(reading.link_changed, "and the address is a new one, not a withdrawn link").toBe(true);
  await context.close();
});

test("ORD-0541 A3 a standing row at another tier is not this outlet's link", async ({ browser }) => {
  /* Every shape is the same sentence: "the list door offers a row that stands, has a token, and is
     not `LINK_READ`". The ruling names one tier this outlet may hand over, so any other tier has to
     reach the create door -- and the row it writes has to be the tier asked for, not the one it
     found. The last two shapes are the other half of the predicate: a `LINK_READ` row whose answer
     carries no token, or already carries a revocation. */
  const shapes = [
    { name: "PUBLIC", rows: [{ id: "grant-public-standing", visibility: "PUBLIC", revoked_at: null, expires_at: null, token: "p".repeat(32) }] },
    { name: "PRIVATE", rows: [{ id: "grant-private-standing", visibility: "PRIVATE", revoked_at: null, expires_at: null, token: "r".repeat(32) }] },
    { name: "INVITEES_ONLY", rows: [{ id: "grant-invitees-standing", visibility: "INVITEES_ONLY", revoked_at: null, expires_at: null, token: "i".repeat(32) }] },
    { name: "LINK_READ_without_token", rows: [{ id: "grant-no-token", visibility: "LINK_READ", revoked_at: null, expires_at: null }] },
    { name: "LINK_READ_revoked", rows: [{ id: "grant-revoked", visibility: "LINK_READ", revoked_at: "2026-10-01T00:00:00+00:00", expires_at: null, token: "v".repeat(32) }] },
  ];
  const readings: any[] = [];
  for (const shape of shapes) {
    const { context, page, calls, posts } = await openSheet(browser);
    await fakeFirstAsks(page, shape.rows);
    const first = await press(page);
    const rows = await roster(page);
    readings.push({
      shape: shape.name,
      door_calls: calls,
      /** The arm's whole question: did this press write, or did it hand over somebody else's row? */
      posts: posts(),
      state: first.state,
      sentence: first.sentence,
      reused_wording: REUSED.test(first.sentence),
      grant_id: first.grant_id,
      row_written: rows.find((row) => row.id === first.grant_id) ?? null,
      invented_row_handed_over: first.grant_id === shape.rows[0].id,
      token_the_link_carries: tokenOf(first.link),
      invented_token_handed_over: tokenOf(first.link) === (shape.rows[0] as any).token,
    });
    await context.close();
  }
  write("A3_tier_predicate", { readings });

  for (const reading of readings) {
    expect(reading.state, `${reading.shape}: the write still confirms through the read-back`)
      .toBe("CONFIRMED");
    expect(reading.posts, `${reading.shape}: a row of that shape is not reusable, so this press wrote`)
      .toBe(1);
    expect(reading.reused_wording, `${reading.shape}: the sheet cannot claim it wrote nothing`).toBe(false);
    expect(reading.invented_row_handed_over, `${reading.shape}: the id on screen is not the invented row`)
      .toBe(false);
    expect(
      reading.invented_token_handed_over,
      `${reading.shape}: and neither is the token inside the link`,
    ).toBe(false);
    expect(
      reading.row_written?.visibility,
      `${reading.shape}: the row the server made is the tier this outlet asks for`,
    ).toBe("LINK_READ");
  }
});

test("ORD-0541 A4 a list door that refuses costs the press no write", async ({ browser }) => {
  const { context, page, calls, posts } = await openSheet(browser);
  await page.route(`**${DOOR}`, (route) =>
    route.fulfill({
      status: 500,
      contentType: "application/json",
      body: JSON.stringify({ error: { reason_code: "INTERNAL" } }),
    }),
  );
  const press1 = await press(page);
  const reading = {
    door_calls: calls,
    posts: posts(),
    state: press1.state,
    sentence: press1.sentence,
    status_named: /状态码 (\d{3})|status (\d{3})/.exec(press1.sentence)?.[1] ?? null,
    link_present: press1.link_present,
  };
  write("A4_read_refused", reading);

  /* ORD-0528 already required this sentence; ORD-0541 adds the half that costs a write. A press that
     cannot ask what stands must not mint a grant on the strength of not having asked -- that is the
     same accumulation A1 measures, arriving through a failing door instead of a working one. */
  expect(reading.state, "a refusing list door is a non-confirmation").toBe("NOT_CONFIRMED");
  expect(reading.posts, "and it is a press that wrote nothing").toBe(0);
  expect(reading.status_named, "the screen quotes the number the door answered with").toBe("500");
  expect(reading.link_present, "with no link handed over").toBe(0);
  await context.close();
});

test("ORD-0541 A5 the two confirmations are two sentences, in both languages and both shapes", async ({
  browser,
}) => {
  const readings: any[] = [];
  for (const locale of ["zh-CN", "en"] as const) {
    for (const viewport of [
      { name: "phone", width: 390, height: 844 },
      { name: "desktop", width: 1280, height: 900 },
    ] as const) {
      const { context, page, posts } = await openSheet(browser, locale, {
        width: viewport.width,
        height: viewport.height,
      });
      /* Ask the sheet as if nothing stood (the first GET is faked empty), then ask again for real, so
         this arm always reads both sentences rather than whichever the run order leaves behind. */
      await fakeFirstAsks(page, []);
      const wrote = await press(page);
      const posts_after_wrote = posts();
      const reused = await press(page, wrote.sentence);
      const sheet = (await page.getByTestId("trip-poster").innerText()).trim();
      const box = await page.getByTestId("poster-share-result").boundingBox();

      readings.push({
        locale,
        viewport: `${viewport.width}x${viewport.height}`,
        wrote_sentence: wrote.sentence,
        reused_sentence: reused.sentence,
        sheet_inner_text_chars: sheet.length,
        result_box: box ? { width: Math.round(box.width), height: Math.round(box.height) } : null,
        posts_on_second_press: posts() - posts_after_wrote,
        /* Recorded, not asserted: this arm forces the first press to write by faking its asking, so the
           second press may legitimately hand over an older standing link than the one just made. Which
           row a press reuses is A1's question; A5 is only about the words on the screen. */
        same_link: wrote.link === reused.link,
        sentences_are_different_words: wrote.sentence !== reused.sentence,
        wrote_words: WROTE.test(wrote.sentence),
        reused_words: REUSED.test(reused.sentence),
        key_echo_hits: (sheet.match(/\b(poster|sharedPoster|shared)\.[A-Za-z0-9_.]+/g) ?? []).length,
      });
      await context.close();
    }
  }
  write("A5_screen_reads", { readings });
  for (const reading of readings) {
    expect(reading.key_echo_hits, `${reading.locale} at ${reading.viewport} leaks no key name`).toBe(0);
    expect(reading.sheet_inner_text_chars).toBeGreaterThan(60);
    expect(reading.wrote_words, `${reading.locale} at ${reading.viewport}: the write says it wrote`)
      .toBe(true);
    expect(reading.reused_words, `${reading.locale} at ${reading.viewport}: the reuse says it did not`)
      .toBe(true);
    expect(
      reading.sentences_are_different_words,
      `${reading.locale} at ${reading.viewport}: 新建 and 复用 are not the same sentence`,
    ).toBe(true);
    expect(reading.posts_on_second_press, `${reading.locale} at ${reading.viewport}: the second press writes nothing`)
      .toBe(0);
    expect(
      reading.result_box?.height,
      `${reading.locale} at ${reading.viewport}: the line is laid out, not absent`,
    ).toBeGreaterThan(0);
  }
});
