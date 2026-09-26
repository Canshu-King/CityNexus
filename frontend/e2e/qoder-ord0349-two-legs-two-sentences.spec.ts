/**
 * ORD-0349 — two legs, two sentences, two pictures.
 *
 * HJ-P3 measured that a leg which never connected and a leg which answered with something unusable
 * produced pixel-identical screenshots while the screen said "the server answered just now" over both.
 * This spec keeps the two apart where it can be measured: the dictionary strings, the leg kinds the
 * shipped classifier gives them, and the rendered pixels of each sentence -- with a same-sentence
 * control so the pixel comparison is shown to be capable of equality before it is trusted for
 * difference.
 *
 * It does not need a backend: the two sentences are read from the product's own dictionary through
 * `useT`, and the alert is the real `JourneyTrialSetup` mounted with them.
 */
import { expect, test } from "@playwright/test";
import { createHash } from "node:crypto";
import { writeFileSync } from "node:fs";
import { classifyReadFailure, OriginResponseUnusableError } from "../src/lib/failureAttribution";
import { ReadDeadlineMissed } from "../src/lib/readDeadline";
import { evidencePath } from "./_qoderEvidence";

const FILE = "e2e/qoder-ord0349-two-legs-two-sentences.spec.ts";
const node = (id: string, detail: string) => `${FILE} :: ${id} — ${detail}`;

/** Verbatim from the shipped gate this order must not redden:
 *  `e2e/qoder-sealed-failure-speaks-and-offers-retry.spec.ts:27`. */
const GATE_ANSWERED_SENTENCE =
  "没读到封存演示的信息：服务器刚才答了，但答的内容我们用不了。这不是你填错了什么。";

/** What each leg may and may not say.  "刚才答了" is an assertion that an answer arrived; "没有拿到
 *  服务器的回答" is the opposite assertion.  Neither may appear in the other's sentence. */
const CLAIMS_ANSWERED = ["刚才答了", "the server answered"];
const CLAIMS_NO_ANSWER = ["没有拿到服务器的回答", "got no answer from the server"];
const CLAIMS_ANSWERED_EN = ["the server answered", "answered just now"];
/** Verbatim from the same gate's English arm (`:29-30`). */
const GATE_ANSWERED_SENTENCE_EN =
  "Couldn't read the sealed demo: the server answered just now, but what it answered isn't something we can use. Nothing you filled in caused this.";

/** Only the alert box, not the whole wizard: the surrounding form pre-fills dates from "now", and two
 *  mounts a few milliseconds apart would then differ for a reason that has nothing to do with the
 *  sentence under test -- which is exactly the false difference a control arm exists to catch. */
async function sha256OfAlert(page: import("@playwright/test").Page, caseName: string): Promise<string> {
  /* Freeze sticky/absolute overlays so a fixed band cannot fall inside one shot and not another;
     applied to every load, so it cannot flatter the comparison. */
  await page.addStyleTag({ content: "*, *::before, *::after { position: static !important; }" });
  const buf = await page
    .locator('[data-testid="trial-sealed-unavailable"]')
    .screenshot({ animations: "disabled", caret: "hide", scale: "css" });
  return createHash("sha256").update(buf).digest("hex");
}

async function mount(page: import("@playwright/test").Page, locale: "zh-CN" | "en", caseName = "answered") {
  await page.addInitScript((loc) => {
    localStorage.setItem("citynexus.locale", loc);
    localStorage.setItem("citynexus.storage-seeded", "1");
  }, locale);
  await page.goto(`/?case=${caseName}`, { waitUntil: "load" });
  await page.addScriptTag({ type: "module", url: "/e2e/fixtures/ord0349-sealed-alert-harness.tsx" });
  await page.waitForSelector('[data-testid="ord0349-case"]');
  /* A pending webfont would move glyph pixels between the two control shots, which is the difference
     I am trying to detect, not noise to eliminate: settle first, then shoot. */
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(400);
}

test("the dictionary separates the legs, and neither sentence asserts the other", async ({ page }) => {
  await mount(page, "zh-CN");
  const answered = (await page.getByTestId("ord0349-dict-answered").innerText()).trim();
  const noAnswer = (await page.getByTestId("ord0349-dict-no-answer").innerText()).trim();
  writeFileSync(
    evidencePath("ord0349-sentences.json"),
    JSON.stringify({ answered, noAnswer, gateAnswered: GATE_ANSWERED_SENTENCE }, null, 1),
  );

  expect(answered.length, node("sentences", "the answered sentence is empty")).toBeGreaterThan(8);
  expect(noAnswer.length, node("sentences", "the no-answer sentence is empty")).toBeGreaterThan(8);
  expect(answered === noAnswer, node("sentences", "both legs still share one sentence")).toBe(false);

  for (const shape of [...CLAIMS_ANSWERED, ...CLAIMS_ANSWERED_EN]) {
    expect(noAnswer.includes(shape), node("sentences", `the no-answer sentence claims "${shape}"`)).toBe(false);
  }
  for (const shape of CLAIMS_NO_ANSWER) {
    expect(answered.includes(shape), node("sentences", `the answered sentence claims "${shape}"`)).toBe(false);
  }
  /* The leg this order must leave alone: the shipped gate's own fate (a 200 that answers HTML) reads
     the answered sentence, so its assertion still matches the product word for word. */
  expect(answered, node("sentences", "the answered sentence no longer matches the shipped gate")).toBe(
    GATE_ANSWERED_SENTENCE,
  );
});

test("the shipped classifier tells the legs apart the way the sentence choice now assumes", async () => {
  const legs = {
    refused: new TypeError("Failed to fetch"),
    deadline: new ReadDeadlineMissed(12_000),
    answeredHtml200: new OriginResponseUnusableError(200, "text/html; charset=utf-8", "html"),
    answeredEmpty500: Object.assign(new Error("CityNexus API 500"), { status: 500 }) as Error,
  };
  const kinds: Record<string, string> = {};
  for (const [name, error] of Object.entries(legs)) {
    kinds[name] = classifyReadFailure(error as unknown).evidence_kind;
  }
  writeFileSync(evidencePath("ord0349-leg-kinds.json"), JSON.stringify(kinds, null, 1));

  expect(kinds.refused, node("legs", "a refused connection is not a transport fact")).toBe("TRANSPORT");
  expect(kinds.deadline, node("legs", "a deadline that elapsed is reported as an answer")).toBe("TRANSPORT");
  expect(kinds.answeredHtml200, node("legs", "a 200 that answered HTML is not transport")).toBe("HTTP_RESPONSE");
  expect(kinds.answeredEmpty500, node("legs", "a 500 answer is not transport")).toBe("HTTP_RESPONSE");
});

test("the two legs render as two pictures, and the same sentence renders as one", async ({ page }) => {
  await mount(page, "zh-CN", "answered");
  const answered = await sha256OfAlert(page, "answered");
  await mount(page, "zh-CN", "no-answer");
  const noAnswer = await sha256OfAlert(page, "no-answer");
  /* The control: the same load again.  If this hashes differently, pixel comparison is noise here and
     the arm below has no business claiming a difference. */
  const page2 = await page.context().newPage();
  await mount(page2, "zh-CN", "no-answer");
  const again = await sha256OfAlert(page2, "no-answer");
  await page2.close();
  writeFileSync(
    evidencePath("ord0349-pixels.json"),
    JSON.stringify({ answered, noAnswer, noAnswerAgain: again, control_stable: noAnswer === again, separated: answered !== noAnswer }, null, 1),
  );

  /* The control first: if identical content did not hash identically, a difference would be noise. */
  expect(noAnswer === again, node("pixels", "the same sentence did not screenshot identically -- the instrument is unstable")).toBe(true);
  expect(answered !== noAnswer, node("pixels", "the two legs still produce the same pixels")).toBe(true);
});

test("the English arm matches the shipped gate's English sentence too", async ({ page }) => {
  await mount(page, "en");
  const answered = (await page.getByTestId("ord0349-dict-answered").innerText()).trim();
  const noAnswer = (await page.getByTestId("ord0349-dict-no-answer").innerText()).trim();
  writeFileSync(evidencePath("ord0349-sentences-en.json"), JSON.stringify({ answered, noAnswer }, null, 1));
  expect(answered, node("sentences-en", "the English answered sentence drifted from the gate")).toBe(GATE_ANSWERED_SENTENCE_EN);
  for (const shape of CLAIMS_NO_ANSWER) {
    expect(answered.includes(shape), node("sentences-en", `English answered sentence claims "${shape}"`)).toBe(false);
  }
  for (const shape of CLAIMS_ANSWERED_EN) {
    expect(noAnswer.includes(shape), node("sentences-en", `English no-answer sentence claims "${shape}"`)).toBe(false);
  }
});

test("ORD-0339's rule still holds on these mounts: no exception words in the DOM", async ({ page }) => {
  await mount(page, "zh-CN");
  const html = await page.evaluate(() => document.body.innerHTML);
  expect(html.includes("data-error-"), node("q71", "a data-error-* attribute came back")).toBe(false);
});
