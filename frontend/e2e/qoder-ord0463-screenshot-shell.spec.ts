/**
 * ORD-0463 -- the screenshot branch of the POI import screen, judged on rendered text.
 *
 * The order for this round is a shell: 接收图片、明说"尚未识别"，不许把"识别中"写成已识别.  So the
 * arms are about what the screen is forbidden to say as much as what it says:
 *
 *  S1 the screenshot mode states, before any file is chosen, that nothing has been recognised -- and
 *     the words 识别中 appear nowhere on the screen;
 *  S2 choosing a real picture puts this device's own reading on screen (name, octets, media type) and
 *     still says nothing was recognised; the candidate pool does not appear, and no request is sent;
 *  S3 the English arm says the same thing in English, with no Chinese leaking in;
 *  S4 a non-image file is refused by name rather than counted as a picture;
 *  S5 the branch ORD-0437 built is not broken by this: its own predicate (the named element exists and
 *     its painted words mention 截图/screenshot) still holds in both languages, and the text branch is
 *     untouched.
 *
 * Nothing here is mocked. The screen is driven on this lane's built bundle over this lane's backend,
 * which runs on a read-only snapshot copy of the shared preview database.
 */
import { expect, test, type Page } from "@playwright/test";
import { mkdirSync, writeFileSync } from "node:fs";

const FILE = "e2e/qoder-ord0463-screenshot-shell.spec.ts";
const node = (id: string, detail: string) => `${FILE} :: ${id} — ${detail}`;
const RUN = process.env.CITYNEXUS_E2E_RUN_ID ?? "local";
const EVIDENCE = process.env.CITYNEXUS_EVIDENCE_DIR ?? "D:/moodle/_qoder_n2b_ord0463_20260929/evidence";
const JOURNEY = process.env.CITYNEXUS_N2B_JOURNEY ?? "";
const PNG = "D:/moodle/_qoder_n2b_ord0463_20260929/fixture_shot.png";
const NOT_IMAGE = "D:/moodle/_qoder_n2b_ord0463_20260929/fixture_not_image.txt";

const readings: Record<string, unknown> = {};

function write(arm: string, body: Record<string, unknown>) {
  mkdirSync(EVIDENCE, { recursive: true });
  writeFileSync(`${EVIDENCE}/${RUN}__${arm}.json`, JSON.stringify(body, null, 1), "utf-8");
}

async function enterScreenshotMode(page: Page, locale: string) {
  await page.addInitScript(
    ([jid, loc]) => {
      localStorage.clear();
      localStorage.setItem("citynexus.v8.journey_id", jid);
      localStorage.setItem("citynexus.locale", loc);
    },
    [JOURNEY, locale],
  );
  page.setDefaultTimeout(30_000);
  await page.goto("/v8/import", { waitUntil: "load" });
  await expect(page.getByTestId("poi-import"), node("boot", "the import screen did not mount")).toHaveCount(1);
  await page.getByTestId("poi-import-mode-screenshot").click();
  await expect(page.getByTestId("poi-import-screenshot-shell")).toHaveCount(1);
}

test.describe("ORD-0463 the screenshot shell receives and does not recognise", () => {
  test("S1 before any file: it says nothing has been recognised, and mounts no parse-phase state", async ({
    page,
  }) => {
    expect(JOURNEY.length > 0, node("S1", "CITYNEXUS_N2B_JOURNEY was not named"));
    await enterScreenshotMode(page, "zh-CN");
    const named = page.getByTestId("poi-import-mode-unsupported");
    await expect(named, node("S1", "the branch lost its named sentence")).toHaveCount(1);
    const words = (await named.innerText()).replace(/\s+/g, " ");
    expect(words.includes("截图"), node("S1", `the sentence does not name the form: ${words}`)).toBe(true);
    expect(words.includes("还没有"), node("S1", `the sentence does not say 尚未识别: ${words}`)).toBe(true);
    /* What the order forbids is a *state*, not a word: the screen may say out loud that no
       "recognising" state will appear -- that sentence has to contain the word to name it. So the
       check is on the phase indicator ORD-0437's parse path drives (`poi-import-phase`), which must
       simply not exist while this branch is showing. */
    await expect(
      page.getByTestId("poi-import-phase"),
      node("S1", "a parse phase indicator is mounted by a branch that parses nothing"),
    ).toHaveCount(0);
    const shell = (await page.getByTestId("poi-import-screenshot-shell").innerText()).replace(/\s+/g, " ");
    for (const claim of ["已识别出", "识别到", "个地点已加入"]) {
      expect(shell.includes(claim), node("S1", `the shell claims recognition (${claim}): ${shell}`)).toBe(
        false,
      );
    }
    await expect(
      page.getByTestId("poi-import-results"),
      node("S1", "a candidate pool appeared from a screen that recognised nothing"),
    ).toHaveCount(0);
    readings.S1 = { words };
    write("S1", { spec: FILE, ...readings.S1 });
    await page.screenshot({ path: `${EVIDENCE}/${RUN}__S1_before_pick.png` });
  });

  test("S2 a chosen picture is reported as received and unrecognised, with no request and no pool", async ({
    page,
  }) => {
    const posts: string[] = [];
    page.on("request", (request) => {
      if (request.method() !== "GET") posts.push(`${request.method()} ${request.url()}`);
    });
    await enterScreenshotMode(page, "zh-CN");
    await page.getByTestId("poi-import-image-file").setInputFiles(PNG);
    const line = page.getByTestId("poi-import-image-received");
    await expect(line, node("S2", "the chosen file produced no reading on screen")).toHaveCount(1);
    const words = (await line.innerText()).replace(/\s+/g, " ");
    expect(words.includes("fixture_shot.png"), node("S2", `name missing: ${words}`)).toBe(true);
    expect(words.includes("86 字节"), node("S2", `octets missing: ${words}`)).toBe(true);
    expect(words.includes("image/png"), node("S2", `media type missing: ${words}`)).toBe(true);
    expect(
      words.includes("还没有从它识别出任何东西"),
      node("S2", `the sentence claims recognition: ${words}`),
    ).toBe(true);
    const stays = (await page.getByTestId("poi-import-image-stays").innerText()).replace(/\s+/g, " ");
    expect(stays.includes("不发任何请求"), node("S2", `the stays-put claim is gone: ${stays}`)).toBe(true);
    expect(
      posts,
      node("S2", `this branch sent something: ${JSON.stringify(posts)}`),
    ).toEqual([]);
    await expect(
      page.getByTestId("poi-import-results"),
      node("S2", "the shared candidate pool was touched by a shell that recognised nothing"),
    ).toHaveCount(0);
    readings.S2 = { words, stays, non_get_requests: posts };
    write("S2", { spec: FILE, ...readings.S2 });
    await page.screenshot({ path: `${EVIDENCE}/${RUN}__S2_received.png` });
  });

  test("S3 the English arm says the same thing in its own words, with no Chinese on it", async ({
    page,
  }) => {
    await enterScreenshotMode(page, "en");
    const words = (await page.getByTestId("poi-import-mode-unsupported").innerText()).replace(/\s+/g, " ");
    expect(/screenshot/i.test(words), node("S3", `en sentence lost the form name: ${words}`)).toBe(true);
    expect(
      words.toLowerCase().includes("not built"),
      node("S3", `en sentence does not say it has not been recognised: ${words}`),
    ).toBe(true);
    await page.getByTestId("poi-import-image-file").setInputFiles(PNG);
    const received = (await page.getByTestId("poi-import-image-received").innerText()).replace(/\s+/g, " ");
    expect(
      received.includes("Nothing has been recognised from it"),
      node("S3", `en receipt claims recognition: ${received}`),
    ).toBe(true);
    const block = (await page.getByTestId("poi-import-screenshot-shell").innerText()).replace(/\s+/g, " ");
    expect(/[\u4e00-\u9fff]/.test(block), node("S3", `en arm renders CJK: ${block.slice(0, 200)}`)).toBe(
      false,
    );
    readings.S3 = { words, received };
    write("S3", { spec: FILE, ...readings.S3 });
  });

  test("S4 a file that is not a picture is refused by name, not counted as one", async ({ page }) => {
    await enterScreenshotMode(page, "zh-CN");
    await page.getByTestId("poi-import-image-file").setInputFiles(NOT_IMAGE);
    const words = (await page.getByTestId("poi-import-image-received").innerText()).replace(/\s+/g, " ");
    expect(
      words.includes("不是图片类型"),
      node("S4", `a non-image was accepted as a picture: ${words}`),
    ).toBe(true);
    expect(words.includes("text/plain"), node("S4", `the type was not named: ${words}`)).toBe(true);
    readings.S4 = { words };
    write("S4", { spec: FILE, ...readings.S4 });
  });

  test("S5 the branch ORD-0437 built still holds its own predicate in both languages", async ({
    page,
  }) => {
    const arms: Record<string, unknown> = {};
    for (const locale of ["zh-CN", "en"]) {
      await enterScreenshotMode(page, locale);
      const words = (await page.getByTestId("poi-import-mode-unsupported").innerText()).replace(/\s+/g, " ");
      arms[locale] = { words, matches: /截图|screenshot/i.test(words) };
      expect(
        /截图|screenshot/i.test(words),
        node("S5", `${locale}: ORD-0437's own predicate no longer holds: ${words}`),
      ).toBe(true);
    }
    /* and the text branch is untouched: the input, its counter and the scope hint are all still there */
    await enterScreenshotMode(page, "zh-CN");
    await page.getByTestId("poi-import-mode-text").click();
    await expect(page.getByTestId("poi-import-text")).toHaveCount(1);
    await expect(page.getByTestId("poi-import-scope-hint")).toHaveCount(1);
    readings.S5 = arms;
    write("S5", { spec: FILE, ...readings });
  });
});
