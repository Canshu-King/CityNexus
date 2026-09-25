/**
 * ORD-0323 — two Q64 exposure cells, each judged from both directions.
 *
 * S1's full-tree scan (`evidence/cmdr-s1-verify-0306/verify_r1.json`) named exactly two places where a
 * screen still prints words it did not write:
 *   cell 1  `ProductErrorBoundary.tsx:104-105` -- the caught failure's own prose and React's component
 *           frames, both straight into a `<pre>`;
 *   cell 2  `JourneyInboxWorkbench.tsx:88` -- a rejected reply rebuilt as `new Error(<server sentence>)`,
 *           which this panel then renders at :687 / :691 / :731.
 *
 * Q64=① says a panel may show whitelisted fields it measured on its own, so every arm here carries two
 * observables that must not substitute for one another (the commander's own words: 两个观测量不许互替):
 *   NEGATIVE  the text this device is forbidden to repeat is not in the DOM at all -- not merely not
 *             visible, because a collapsed `<details>` is still on the screen for the next reader;
 *   POSITIVE  the allowed readings are still rendered, so a "clean" verdict cannot be bought by deleting
 *             the panel, the fold, or the measurement behind it.
 * Each direction has its own counter-example, run outside this file: `ord0323_run_arms.py` restores the
 * old sink (M_sink_back), strips the device fields while keeping the panel (M_fields_gone), puts the
 * server sentence back into the thrown error (M_throw_back), and strips status/content-type from the
 * device sentence while leaving the throw alone (M_device_text_blind).
 *
 * Cell 1's crash is driven for real: `GET .../inbox` answers with a draft row missing the field the queue
 * renders (`unresolved_fields`), so the render throws and the boundary is the component that has to speak.
 * Nothing here stubs the boundary itself.
 */
import { expect, test, type Page, type Route } from "@playwright/test";
import { writeFileSync } from "node:fs";
import { evidencePath } from "./_qoderEvidence";

const FILE = "e2e/qoder-ord0323-two-exposure-cells.spec.ts";
const node = (id: string, detail: string) => `${FILE} :: ${id} — ${detail}`;
const RUN = process.env.CITYNEXUS_E2E_RUN_ID ?? "local";

/* The three bodies the product must never repeat. Distinctive tokens, one per request leg, so a leak is
   attributable to the sink that carried it rather than to "something on the page". */
const UPSTREAM_MEMORY = "memory_forbidden_token_9f3c the traveller's own words were refused";
const UPSTREAM_INBOX = "inbox_forbidden_token_4b71 the review queue is not ready";
const UPSTREAM_CONFIRM = "confirm_forbidden_token_c258 the commitment was rejected";

/* What the pre-fix screen actually held, measured from the M_sink_back run's own evidence file rather than
   guessed at: the TypeError's prose, the property name inside it, and the component frame React printed. */
const CELL1_LEAKS = ["Cannot read", "unresolved_fields", "JourneyInboxWorkbench"];
const CELL2_LEAKS = [UPSTREAM_MEMORY, UPSTREAM_INBOX, UPSTREAM_CONFIRM];

const jsonBody = (o: unknown) => JSON.stringify(o);

type Readings = Record<string, unknown>;
const readings: Readings = {};

async function domReading(page: Page): Promise<{ root: string; body: string; overlay: string[] }> {
  return page.evaluate(() => {
    const root = document.getElementById("root");
    const body = document.body;
    return {
      root: root ? root.textContent ?? "" : "",
      body: body.textContent ?? "",
      // Anything bolted onto the page outside the product tree (a dev-only overlay would show here).
      overlay: Array.from(body.children).map((el) => {
        const tag = el.tagName.toLowerCase();
        const id = el.id ? `#${el.id}` : "";
        return `${tag}${id}${el.shadowRoot ? "[shadow]" : ""}`;
      }),
    };
  });
}

async function boot(page: Page, journeyId: string): Promise<void> {
  await page.addInitScript((id) => {
    localStorage.clear();
    localStorage.setItem("citynexus.v8.journey_id", id as string);
    localStorage.setItem("citynexus.locale", "zh-CN");
  }, journeyId);
  await page.setViewportSize({ width: 390, height: 844 });
}

async function journeyId(page: Page): Promise<string> {
  const scene = (await (await page.request.get("/api/v1/demo/scene")).json()) as { journey_id?: string };
  const id = String(scene.journey_id ?? "");
  expect(id.length > 0, node("boot", "the stage named no journey, so there is no inbox to open"));
  return id;
}

/* The arm key is the cell, not the test's prefix: eight legs share the `N4_` prefix and the two Q68 legs
 * share `N6_`, so keying on the first token would have collided two legs onto one evidence file. */
const armOf = (title: string): string =>
  /^N4_(T\d\d)_/.exec(title)?.[1] ?? /^N6_(Q68[ab])_/.exec(title)?.[1] ?? title.split("_")[0];

test.afterEach(({}, info) => {
  const arm = armOf(info.title);
  const body: Readings = { ...(readings[arm] ?? {}) };
  /* A red arm has to carry its own readings too, or the counter-example proves nothing about which
     direction flipped. */
  body.test_status = info.status;
  if (info.status !== "passed") {
    body.error_head = String(info.error?.message ?? "").replace(/\s+/g, " ").slice(0, 600);
  }
  writeFileSync(
    evidencePath(`ord0323/${RUN}__${arm}.json`),
    JSON.stringify({ run_id: RUN, arm, ...body }, null, 1),
    "utf-8",
  );
});

test("N1_boundary_panel_keeps_its_own_readings_and_drops_the_failure_prose — 边界自己量的字段还在，失败原文与组件帧不在屏上", async ({
  page,
}) => {
  test.setTimeout(300_000);
  const arm = "N1";
  const id = await journeyId(page);
  const consoleErrors: string[] = [];
  page.on("console", (m) => {
    if (m.type() === "error") consoleErrors.push(m.text());
  });
  /* A queue row without the field the row renders. The server contract says `unresolved_fields` is always
     present; this is the shape that makes the panel throw, which is the only way the boundary gets to
     speak -- so the arm drives the real component tree, not a stand-in. */
  await page.route("**/api/v1/journeys/*/inbox", async (r: Route) => {
    if (r.request().method() !== "GET") return r.fallback();
    await r.fulfill({
      status: 200,
      contentType: "application/json",
      body: jsonBody({
        drafts: [
          {
            id: "ORD0323-CRASH-1",
            artifact_type: "STRUCTURED_JSON",
            extracted: { title: "天津西 → 北京南 高铁" },
            status: "NEEDS_REVIEW",
            extraction_mode: "RULE",
          },
        ],
      }),
    });
  });
  await boot(page, id);
  await page.goto("/v8/bookings", { waitUntil: "load" });

  const panel = page.getByTestId("product-error-boundary");
  await expect(panel, node(arm, "the render never threw, so the boundary had nothing to say and every claim below would be vacuous")).toBeVisible({
    timeout: 30_000,
  });
  /* The fold is opened by structure, not by a testid of my own: the same arm has to be able to speak on
     the pre-fix file, and there it hung for the whole budget waiting for an element the old screen never
     had (measured in the first pass, shape `cell1_baseline_sink`). */
  await panel.locator("details").locator("summary").click();
  const detail = ((await page.getByTestId("error-detail").textContent()) ?? "").trim();
  const dom = await domReading(page);
  readings[arm] = {
    panel_copy: clean(((await panel.textContent()) ?? "")),
    error_detail_text: detail,
    console_error_count: consoleErrors.length,
    console_error_head: consoleErrors.slice(0, 2).map((s) => s.slice(0, 220)),
    root_text_length: dom.root.length,
    overlay_hosts: dom.overlay,
    leaked_needles_still_on_screen: CELL1_LEAKS.filter((n) => dom.root.includes(n) || dom.body.includes(n)),
  };

  /* POSITIVE -- readings this device took itself, each one only present if the measurement still runs. */
  expect(detail, node(arm, "技术详情 renders empty, which is how a fold passes a 'nothing leaked' check while telling the reader nothing")).not.toBe("");
  expect(
    /route=\/v8\/bookings/.test(detail),
    node(arm, `the fold no longer states which screen failed; it reads "${detail.slice(0, 200)}"`),
  ).toBe(true);
  expect(
    /caught_at=\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(detail),
    node(arm, `no device timestamp in the fold, so the reading is not the device's own; it reads "${detail.slice(0, 200)}"`),
  ).toBe(true);
  expect(
    /failures_caught_here=[1-9]\d{0,2}/.test(detail),
    node(arm, `the boundary does not count what it caught; it reads "${detail.slice(0, 200)}"`),
  ).toBe(true);
  expect(
    /online_at_this_device=(yes|no)/.test(detail),
    node(arm, `the fold dropped the device's own connectivity reading; it reads "${detail.slice(0, 200)}"`),
  ).toBe(true);
  expect(
    detail.includes("failure_text_rendered=no"),
    node(arm, `the fold no longer states its own boundary; it reads "${detail.slice(0, 200)}"`),
  ).toBe(true);

  /* NEGATIVE -- the failure prose and the component frames are not in the DOM. Asserted on textContent,
     not innerText: a collapsed fold is still a page a screenshot tool can expand. */
  expect(
    (readings[arm] as Readings).leaked_needles_still_on_screen,
    node(
      arm,
      `the boundary is printing what it was handed again (${JSON.stringify(
        (readings[arm] as Readings).leaked_needles_still_on_screen,
      )}); the screen reads "${clean(dom.root).slice(0, 240)}"`,
    ),
  ).toEqual([]);
});

test("N2_rejected_readings_render_their_own_status_and_content_type_not_the_reply_s_sentence — 顶回来的两条读数各自还在，回复原话不在屏上", async ({
  page,
}) => {
  test.setTimeout(300_000);
  const arm = "N2";
  const id = await journeyId(page);
  await page.route("**/api/v1/journeys/*/memory", async (r: Route) => {
    await r.fulfill({
      status: 500,
      contentType: "application/json",
      body: jsonBody({ error: { message: UPSTREAM_MEMORY } }),
    });
  });
  await page.route("**/api/v1/journeys/*/inbox", async (r: Route) => {
    if (r.request().method() !== "GET") return r.fallback();
    await r.fulfill({
      status: 503,
      contentType: "application/json",
      body: jsonBody({ detail: UPSTREAM_INBOX }),
    });
  });
  await boot(page, id);
  await page.goto("/v8/bookings", { waitUntil: "load" });

  const message = page.locator(".v10-inbox-message").first();
  await expect(
    message,
    node(arm, "the refused memory read left no sentence at all, so there is nothing to judge -- an empty screen is not an honest screen"),
  ).toBeVisible({ timeout: 30_000 });
  const messageText = clean(await message.textContent());
  const pending = page.getByTestId("inbox-pending-error");
  await expect(
    pending,
    node(arm, "the refused queue read left no warning in the queue's own slot; an unreadable list and an empty list are showing alike"),
  ).toBeVisible({ timeout: 30_000 });
  const pendingText = clean(await pending.textContent());
  const dom = await domReading(page);
  readings[arm] = {
    message_text: messageText,
    pending_text: pendingText,
    leaked_needles_still_on_screen: CELL2_LEAKS.filter((n) => dom.root.includes(n) || dom.body.includes(n)),
  };

  /* POSITIVE -- each slot carries the reading of ITS OWN request, which is what makes these two
     observables independent rather than one claim written twice. */
  expect(
    messageText.includes("500"),
    node(arm, `the memory slot no longer states the status this device measured (${messageText})`),
  ).toBe(true);
  expect(
    /Cannot read|Unexpected token|JSON|is not valid JSON/.test(messageText),
    node(arm, `the status line is showing parser or engine prose instead of the channel's own sentence (${messageText})`),
  ).toBe(false);
  expect(
    pendingText.includes("503") && pendingText.includes("application/json"),
    node(arm, `the queue slot no longer states the status and content type this device got (${pendingText})`),
  ).toBe(true);
  expect(
    !messageText.includes("503") && !pendingText.includes("500"),
    node(arm, `the two slots swapped readings (memory: "${messageText}" / queue: "${pendingText}") -- one is showing the other's request`),
  ).toBe(true);

  /* NEGATIVE -- no reply sentence, from either leg, reaches the DOM. */
  expect(
    (readings[arm] as Readings).leaked_needles_still_on_screen,
    node(
      arm,
      `the panel is repeating the reply again (${JSON.stringify((readings[arm] as Readings).leaked_needles_still_on_screen)}); memory reads "${messageText}" and the queue reads "${pendingText}"`,
    ),
  ).toEqual([]);
});

test("N3_confirm_fold_carries_the_attempt_reading_not_the_attempt_s_words — 确认那一折带着这台设备的读数，不带回复的原话", async ({
  page,
}) => {
  test.setTimeout(300_000);
  const arm = "N3";
  const id = await journeyId(page);
  const draft = {
    id: "ORD0323-D3",
    artifact_type: "STRUCTURED_JSON",
    extracted: { title: "天津西 → 北京南 高铁", reservation_type: "RAIL" },
    status: "NEEDS_REVIEW",
    unresolved_fields: [],
    extraction_mode: "RULE",
    interpretation: { anchor_role: "MID_TRIP", anchor_role_confidence: 0.8, payment_status: null, reasoning_summary: null, semantic_target: null },
    smart_intake: { decision: "REQUIRES_CONFIRMATION", reasons: [], conflicts: [], resolved_target: null, role_confidence: 0.5 },
  };
  await page.route("**/api/v1/journeys/*/inbox", async (r: Route) => {
    if (r.request().method() !== "GET") return r.fallback();
    await r.fulfill({ status: 200, contentType: "application/json", body: jsonBody({ drafts: [draft] }) });
  });
  await page.route("**/api/v1/journeys/*/inbox/*/confirm", async (r: Route) => {
    await r.fulfill({
      status: 500,
      contentType: "application/json",
      body: jsonBody({ error: { message: UPSTREAM_CONFIRM } }),
    });
  });
  await boot(page, id);
  await page.goto("/v8/bookings", { waitUntil: "load" });

  await expect(
    page.getByTestId("inbox-pending-row").first(),
    node(arm, "the queue never rendered the draft row, so there is no review to open and the fold below would prove nothing"),
  ).toBeVisible({ timeout: 30_000 });
  await page.getByTestId("inbox-open-review").first().click();
  await expect(
    page.getByTestId("v13-2-confirm"),
    node(arm, "the review panel never opened for a draft the server itself reports as reviewable"),
  ).toBeVisible({ timeout: 15_000 });
  await page.getByTestId("v13-2-confirm").click();

  const fold = page.getByTestId("inbox-confirm-detail");
  await expect(
    fold,
    node(arm, "a refused confirmation with no technical fold at all -- the pairing ORD-0302 X-5 settled: a promise needs its block"),
  ).toBeVisible({ timeout: 30_000 });
  const summaryText = clean(await fold.locator("summary").innerText());
  await fold.locator("summary").click();
  const detailText = clean(await fold.textContent());
  const codeText = clean(await fold.locator("code").innerText());
  const dom = await domReading(page);
  readings[arm] = {
    fold_summary: summaryText,
    fold_text: detailText,
    fold_code_visible: codeText,
    status_line: clean((await page.locator(".v10-inbox-message").first().textContent().catch(() => "")) ?? ""),
    leaked_needles_still_on_screen: CELL2_LEAKS.filter((n) => dom.root.includes(n) || dom.body.includes(n)),
  };

  expect(
    summaryText.includes("技术详情"),
    node(arm, `the fold promised something different from what it holds now (${summaryText})`),
  ).toBe(true);
  expect(
    detailText.includes("500") && detailText.includes("application/json"),
    node(arm, `the confirmation fold no longer states what this device measured about the attempt (${detailText})`),
  ).toBe(true);
  expect(
    codeText.includes("500"),
    node(arm, `the reading is in the fold but not on the screen once it is opened (${codeText})`),
  ).toBe(true);

  expect(
    (readings[arm] as Readings).leaked_needles_still_on_screen,
    node(
      arm,
      `the confirmation fold is repeating the reply again (${JSON.stringify((readings[arm] as Readings).leaked_needles_still_on_screen)}); it reads "${detailText}"`,
    ),
  ).toEqual([]);
});

function clean(value: string): string {
  return String(value ?? "").replace(/\s+/g, " ").trim();
}

/* ------------------------------------------------------------------ N4: the eight legs D numbered.
 * T05-T13 of `evidence/ord0320-triage-d/ord0320_triage_r2.json` are eight catch sites plus the technical
 * fold, and all nine carried the same reply's sentence to the screen through `error.message`. One test
 * walks the legs with a route plan that changes per leg: every leg asserts its own needle is nowhere in
 * the DOM, and its own measured status is in the slot that leg writes to -- which is what makes the
 * reading attributable to the leg instead of to the page.
 */
const NEEDLES: Record<string, string> = {
  T06: "import_forbidden_leg_t06",
  T07: "memory_forbidden_token_9f3c the traveller's own words were refused",
  T08: "inbox_forbidden_token_4b71 the review queue is not ready",
  T09: "text_extract_forbidden_leg_t09",
  T10: "vision_forbidden_leg_t10",
  T11: "smart_apply_forbidden_leg_t11",
  T12: "confirm_forbidden_token_c258 the commitment was rejected",
  T13: "patch_forbidden_leg_t13",
};

type Leg = {
  cell: string;
  match: string;
  method: string;
  status: number;
  slot: "message" | "queue" | "fold";
  trigger: "none" | "manual" | "paste" | "vision" | "review_smart" | "review_confirm" | "review_patch";
};

const LEGS: Leg[] = [
  {cell: "T06", match: "/inbox/import", method: "POST", status: 502, slot: "message", trigger: "manual"},
  {cell: "T07", match: "/memory", method: "GET", status: 500, slot: "message", trigger: "none"},
  {cell: "T08", match: "/inbox", method: "GET", status: 503, slot: "queue", trigger: "none"},
  {cell: "T09", match: "/inbox/text-extract", method: "POST", status: 504, slot: "message", trigger: "paste"},
  {cell: "T10", match: "/inbox/vision", method: "POST", status: 507, slot: "message", trigger: "vision"},
  {cell: "T11", match: "/smart-apply", method: "POST", status: 506, slot: "message", trigger: "review_smart"},
  {cell: "T12", match: "/confirm", method: "POST", status: 509, slot: "fold", trigger: "review_confirm"},
  {cell: "T13", match: "PATCH_INBOX", method: "PATCH", status: 511, slot: "message", trigger: "review_patch"},
];

const draftRow = {
  id: "ORD0323-D3",
  artifact_type: "STRUCTURED_JSON",
  extracted: {title: "天津西 → 北京南 高铁", reservation_type: "RAIL"},
  status: "NEEDS_REVIEW",
  unresolved_fields: [],
  extraction_mode: "RULE",
  interpretation: {anchor_role: "MID_TRIP", anchor_role_confidence: 0.8, payment_status: null, reasoning_summary: null, semantic_target: null},
  smart_intake: {decision: "AUTO_APPLY", reasons: [], conflicts: [], resolved_target: null, role_confidence: 0.5},
};

async function drive(page: Page, trigger: Leg["trigger"]): Promise<void> {
  if (trigger === "manual") {
    await page.getByTestId("inbox-tab-manual").click();
    await page.getByTestId("manual-title").fill("天津西 → 北京南 高铁");
    await page.getByTestId("manual-from").fill("天津");
    await page.getByTestId("manual-to").fill("北京");
    await page.getByTestId("manual-submit").click();
    return;
  }
  if (trigger === "vision") {
    await page.getByTestId("inbox-tab-paste").click();
    await page.locator("input[type=file]").first().setInputFiles({
      name: "ticket.png",
      mimeType: "image/png",
      buffer: Buffer.from(
        "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000a49444154789c636000000200" +
        "0100ffff03000006000557bfabd40000000049454e44ae426082", "hex"),
    });
    /* A file <input> is itself exposed with role=button and carries the whole label in its accessible
       name, so the substring match resolved to two controls. */
    await page.getByRole("button", {name: "提取图片草稿", exact: true}).click();
    return;
  }
  await page.getByTestId("inbox-open-review").first().click();
  if (trigger === "review_smart") await page.getByTestId("v13-2-smart-apply").click();
  if (trigger === "review_confirm") await page.getByTestId("v13-2-confirm").click();
  if (trigger === "review_patch") await page.getByTestId("v13-2-save-corrections").click();
}

/* ------------------------------------------------------------------ Q68: the 「原因编号」 slot holds a code or nothing.
 * CMDR 04:45 ruled the slot's format is a promise: `serverReasonCode` used to fall back on
 * `detail.slice(0, 60).toUpperCase()`, which put the reply's sentence into a place the card labels a
 * machine code. Two legs, because both halves of that ruling are observable: a real code must still be
 * shown (the fix may not be "show nothing"), and prose must be shown only where Q67=① put it -- the
 * 技术详情 fold, under the attribution label.
 */
const Q68_CODE = "ZZ_Q68_SERVER_CODE";
const Q68_PROSE = "q68_forbidden_prose_行程过长无法在三日预算内排布";

async function askTheSheet(page: Page, generateBody: string): Promise<void> {
  const scene = (await (await page.request.get("/api/v1/demo/scene")).json()) as { journey_id?: string };
  const id = String(scene.journey_id ?? "");
  expect(id.length > 0, node("Q68", "the stage named no journey"));
  await page.addInitScript((jid) => {
    localStorage.clear();
    localStorage.setItem("citynexus.v8.journey_id", jid as string);
    localStorage.setItem("citynexus.locale", "zh-CN");
  }, id);
  await page.setViewportSize({width: 390, height: 844});
  const mission = {mission: {id: "ord0323-q68-mission", status: "FAILED_UPSTREAM", failure_reason: null,
                             reasoning_summary: null}};
  await page.route("**/api/v1/journeys/*/agent/commands", async (r: Route) => {
    if (r.request().method() !== "POST") return r.fallback();
    await r.fulfill({status: 200, contentType: "application/json", body: jsonBody(mission)});
  });
  await page.route("**/api/v1/journeys/*/plans/generate", async (r: Route) => {
    if (r.request().method() !== "POST") return r.fallback();
    await r.fulfill({status: 503, contentType: "application/json", body: generateBody});
  });
  await page.route("**/api/v1/journeys/*/plans", async (r: Route) => {
    if (r.request().method() !== "GET") return r.fallback();
    await r.fulfill({status: 200, contentType: "application/json", body: "[]"});
  });
  await page.route("**/api/v1/places**", async (r: Route) => {
    await r.fulfill({status: 200, contentType: "application/json",
                     body: jsonBody([{id: "p1", name: "天津西站"}, {id: "p2", name: "北京南站"}])});
  });
  await page.goto("/v8/hub", {waitUntil: "load"});
  await expect(page.getByTestId("today-hero")).toBeVisible({timeout: 30_000});
  await page.getByTestId("hub-plan-with-ai").click();
  await page.getByTestId("plan-ai-input").fill("帮我排三天，喜欢美食和特色景点。");
  await page.getByTestId("plan-ai-submit").click();
  await expect(page.getByTestId("plan-ai-result")).toBeVisible({timeout: 60_000});
}

test("N6_Q68a_a_server_code_still_reaches_the_code_slot — 编号那格：服务器真给了编号时，编号还在屏上", async ({page}) => {
  test.setTimeout(300_000);
  const arm = "Q68a";
  await askTheSheet(page, jsonBody({error: {reason_code: Q68_CODE}, detail: Q68_PROSE}));
  const card = clean(await page.getByTestId("plan-ai-result").textContent());
  const dom = await domReading(page);
  readings[arm] = {card_text: card, code_in_card: card.includes(Q68_CODE),
                   prose_outside_the_fold: clean(card.replace(clean(await page.getByTestId("plan-ai-reason").textContent().catch(() => "")), "")),
                   needle_in_dom: dom.body.includes(Q68_PROSE)};
  expect(card.includes(Q68_CODE),
    node(arm, `the code slot lost a code the server really gave (${card.slice(0, 200)}) -- "do not show prose" is not "show nothing"`)).toBe(true);
  expect(card.includes("BLOCKED") || card.includes("服务器回的原因编号"),
    node(arm, `the card no longer names this as a server-coded block (${card.slice(0, 200)})`)).toBe(true);
});

test("N6_Q68b_a_sentence_only_refusal_is_not_presentation_as_a_code — 编号那格：只有句子时，编号位上不许出现句子，句子归技术详情", async ({
  page,
}) => {
  test.setTimeout(300_000);
  const arm = "Q68b";
  await askTheSheet(page, jsonBody({detail: Q68_PROSE}));
  const reasonEl = page.getByTestId("plan-ai-reason");
  const reasonText = clean(await reasonEl.textContent().catch(() => ""));
  const cardAll = clean(await page.getByTestId("plan-ai-result").textContent());
  const cardWithoutReason = cardAll.replace(reasonText, "");
  const dom = await domReading(page);
  readings[arm] = {
    card_text: cardAll,
    reason_fold_text: reasonText,
    uppercased_prose_in_code_slot: cardWithoutReason.toUpperCase().includes(Q68_PROSE.toUpperCase().slice(0, 18)),
    attributed_sentence_in_fold: reasonText.includes(Q68_PROSE),
    server_label_present: /服务器给出的原因|Reason the server gave/.test(cardAll),
    needle_in_dom: dom.body.includes(Q68_PROSE),
  };
  /* the code slot's own text may not hold the sentence, in any case or truncation */
  expect(
    cardWithoutReason.toUpperCase().includes(Q68_PROSE.toUpperCase().slice(0, 18)),
    node(arm, `the 原因编号 slot is showing the reply's sentence again (${cardWithoutReason.slice(0, 220)})`),
  ).toBe(false);
  /* and Q67=①'s home for it is still there: the attributed sentence inside 技术详情 */
  expect(reasonText.includes(Q68_PROSE),
    node(arm, `the sentence vanished from 技术详情 too (${reasonText.slice(0, 160)}) -- Q68 says the code slot is not its place, not that it may be deleted`)).toBe(true);
  expect(/服务器给出的原因|Reason the server gave/.test(cardAll),
    node(arm, `the attribution label is gone, so whatever sentence shows is unattributed (${cardAll.slice(0, 220)})`)).toBe(true);
});

/* One test per leg: a shared test spends one timeout across eight chances and hides which leg stuck
 * (measured -- the loop version died at `running_leg = T09` with three legs done). Each leg gets its own
 * route plan, its own 120 s budget, and its own evidence file named by D's cell id. */
for (const leg of LEGS) {
  test(`N4_${leg.cell}_a_refused_${leg.method}_leaves_no_reply_words_and_keeps_its_own_reading — ${leg.cell}：自己那句原话不在屏上，自己那次读数还在屏上`, async ({
    page,
  }) => {
    test.setTimeout(120_000);
    const arm = leg.cell;
    const id = await journeyId(page);
    await page.route("**/api/v1/journeys/**", async (r: Route) => {
      const path = new URL(r.request().url()).pathname;
      const method = r.request().method();
      const mine =
        leg.match === "PATCH_INBOX"
          ? method === "PATCH" && /\/inbox\/[A-Za-z0-9-]+$/.test(path)
          : method === leg.method && path.endsWith(leg.match);
      if (mine) {
        await r.fulfill({
          status: leg.status,
          contentType: "application/json",
          body: jsonBody({error: {message: NEEDLES[leg.cell]}, detail: NEEDLES[leg.cell]}),
        });
        return;
      }
      if (path.endsWith("/inbox") && method === "GET") {
        await r.fulfill({status: 200, contentType: "application/json", body: jsonBody({drafts: [draftRow]})});
        return;
      }
      return r.fallback();
    });
    await boot(page, id);
    await page.goto("/v8/bookings", {waitUntil: "load"});
    await expect(
      page.getByTestId("v13-2-memory"),
      node(arm, `${leg.cell}: the wallet panel never rendered, so this leg has no surface to be judged on`),
    ).toBeVisible({timeout: 30_000});
    if (leg.trigger === "paste") {
      await page.getByTestId("inbox-tab-paste").click();
      /* This page holds a second textarea inside the closed structured-JSON aside; only the visible one is
         the paste box. */
      await page.locator("textarea").filter({visible: true}).first().fill("9月26日 天津西→北京南 G8901 二等座 07:30");
      await page.getByRole("button", {name: "提取文本草稿", exact: true}).click();
    } else if (leg.trigger !== "none") {
      await drive(page, leg.trigger);
    }
    const slot =
      leg.slot === "message"
        ? page.locator(".v10-inbox-message").first()
        : leg.slot === "queue"
          ? page.getByTestId("inbox-pending-error")
          : page.getByTestId("inbox-confirm-detail");
    await expect(
      slot,
      node(arm, `${leg.cell}: the leg was refused but its own slot shows nothing -- an empty screen is not an honest screen`),
    ).toBeVisible({timeout: 30_000});
    if (leg.slot === "fold") await slot.locator("summary").click();
    const text = clean(await slot.textContent());
    const dom = await domReading(page);
    const found = Object.entries(NEEDLES)
      .filter(([, n]) => dom.root.includes(n) || dom.body.includes(n))
      .map(([c]) => c);
    const foreign = LEGS.filter((o) => o.cell !== leg.cell).map((o) => String(o.status)).filter((x) => text.includes(x));
    readings[arm] = {
      cell: leg.cell,
      route: leg.match,
      method: leg.method,
      status_asked: leg.status,
      slot_text: text,
      status_in_slot: text.includes(String(leg.status)),
      needles_found: found,
      foreign_status_found: foreign,
      internal_token_on_screen: /inbox request rejected/i.test(text),
    };
    expect(found, node(arm, `${leg.cell}: a reply's own words are on the screen (${JSON.stringify(found)}); the slot reads "${text}"`)).toEqual([]);
    expect(text.includes(String(leg.status)),
      node(arm, `${leg.cell}: the slot no longer states the status this device measured for THIS request (${text})`)).toBe(true);
    expect(foreign,
      node(arm, `${leg.cell}: the slot shows another leg's status ${JSON.stringify(foreign)} instead of its own (${text})`)).toEqual([]);
    if (leg.slot !== "message") {
      expect(text.includes("application/json"),
        node(arm, `${leg.cell}: the machine slot lost the content type this device measured (${text})`)).toBe(true);
    }
    expect(/inbox request rejected/i.test(text),
      node(arm, `${leg.cell}: the carrier's internal token reached the traveller (${text})`)).toBe(false);
  });
}
