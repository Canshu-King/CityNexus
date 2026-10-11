/**
 * ORD-0557 兜底行 (lane 补栏工) — `lib/errorReceipt.ts` stops carrying a second copy of two words
 * the traveller dictionaries already hold.
 *
 * The draft table's two rows for this file are its `:71` 「服务器回执号」/ "server receipt" and its
 * `:72` 「服务器未给回执号」/ "no server receipt". They are NOT new keys: `detail.receiptLabel` and
 * `detail.receiptLabelAbsent` already carry both languages, and `components/CnxMeasuredFacts.tsx`
 * already reads them. Only the mount behind `components/RawFactsPanel.tsx` still took its words from
 * this helper, so the same fact could be named two ways depending on which component drew it.
 *
 * Arms, and what each can actually falsify:
 *
 *   R1/R3  the absent-receipt line on the glass (`innerText`), zh then en — the label AND the
 *          `NOT-EMITTED` token, with `data-cnx-receipt-present="false"` read beside it so a reading
 *          cannot be credited to the wrong branch;
 *   R2/R4  the same line when the refusal really did carry a shaped receipt, zh then en, with
 *          `data-cnx-receipt` naming the number the server sent;
 *   R5     the dictionary's two arms are byte-for-byte the four literals the base generation's own
 *          blob carried — re-derived from that blob, not from memory, so "nothing was reworded" is
 *          measured on both sides;
 *   R6     the module no longer holds the literals and does name the two keys.
 *
 * The surface is the wizard's create-failure fold, because that is the only mount that opts into
 * naming an absent receipt (`nameMissingReceipt` in `components/RawFactsPanel.tsx`); the shell's own
 * banner leaves that line off, which an earlier draft of this file mistook for a missing cell.
 *
 * The base generation is required, not defaulted. In a `git archive` export the object store cannot
 * be asked and R5 says so rather than passing on an empty parse.
 */
import { expect, test, type Page } from "@playwright/test";
import { execSync } from "node:child_process";
import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import { evidencePath } from "./_qoderEvidence";

const FILE = "e2e/qoder-bulangong-0557fb-receipt-label-r1.spec.ts";
const node = (id: string, detail: string) => `${FILE} :: ${id} — ${detail}`;

const BASE_TIP = process.env.CITYNEXUS_ORD0557FB_BASE_TIP ?? "";
const BASE_PREREQ = /^[0-9a-f]{40}$/.test(BASE_TIP)
  ? null
  : "missing environment variable: CITYNEXUS_ORD0557FB_BASE_TIP must be the 40-hex generation this candidate was cut from";

const MODULE = fileURLToPath(new URL("../src/lib/errorReceipt.ts", import.meta.url));
const DICTIONARY = fileURLToPath(new URL("../src/i18n/LocaleContext.tsx", import.meta.url));

const KEY_PRESENT = "detail.receiptLabel";
const KEY_ABSENT = "detail.receiptLabelAbsent";
/* CNX- plus eight Crockford-alphabet characters, the shape contracts/ERROR_RECEIPT_ID_V1.md fixes. */
const RECEIPT = "CNX-7K3M9QTB";
const MISSING_TOKEN = "NOT-EMITTED";
const CELL = "create-raw-facts-receipt";
const DRAFT_KEY = "citynexus.v8.trial_draft";
const DRAFT = {
  cityName: "天津",
  arrivalLocation: "天津站",
  departureLocation: "天津滨海国际机场",
  interests: [],
  specialRequirements: "",
};

/** What the glass said before this order, and what it must still say after it. */
const PAINTED: Record<"zh" | "en", { absent: string; present: string }> = {
  zh: { absent: `服务器未给回执号：${MISSING_TOKEN}`, present: `服务器回执号：${RECEIPT}` },
  en: { absent: `no server receipt：${MISSING_TOKEN}`, present: `server receipt：${RECEIPT}` },
};

const clean = (value: string | null | undefined) => String(value ?? "").replace(/\s+/g, " ").trim();

function dictionaryBlocks(): Record<"en" | "zhCN", Record<string, string>> {
  const src = readFileSync(DICTIONARY, "utf8");
  const blocks: Record<"en" | "zhCN", Record<string, string>> = { en: {}, zhCN: {} };
  for (const tag of ["en", "zhCN"] as const) {
    const at = src.indexOf(tag === "en" ? "const en: Dict = {" : "const zhCN: Dict = {");
    if (at < 0) {
      throw new Error(node("dictionary-parse", `the ${tag} table marker moved; this arm cannot tell an absent key from a moved file`));
    }
    const parsed: Record<string, string> = {};
    for (const match of src.slice(at, src.indexOf("\n};", at)).matchAll(/^\s*"([^"]+)":\s*"((?:[^"\\]|\\.)*)"/gm)) {
      parsed[match[1]] = JSON.parse(`"${match[2]}"`);
    }
    if (Object.keys(parsed).length < 100) {
      throw new Error(node("dictionary-parse", `only ${Object.keys(parsed).length} keys parsed from the ${tag} block — blinded`));
    }
    blocks[tag] = parsed;
  }
  return blocks;
}

/**
 * The four literals the base module painted, read out of the base generation's own bytes.
 *
 * Line-scoped on purpose: an earlier draft matched "the present word" against the absent line and
 * compared the wrong pair, which is how a byte-comparison arm goes green on a mistake. Each of the
 * two arms of the base ternary is now taken as one line carrying two quoted words, and a line that
 * is not where the base had it throws instead of yielding "".
 */
function baseLiterals(): Record<"presentZh" | "absentZh" | "presentEn" | "absentEn", string> {
  let text: string;
  try {
    text = execSync(`git show ${BASE_TIP}:frontend/src/lib/errorReceipt.ts`, { encoding: "utf8", maxBuffer: 8 * 1024 * 1024 });
  } catch (error) {
    throw new Error(node("base-literals", `the object store cannot answer for ${BASE_TIP} (${String(error).slice(0, 180)}); in a git-archive export there is no store to ask, and this arm refuses rather than reporting a vacuous pass`));
  }
  const arms = [...text.matchAll(/zh \? "([^"]+)" : "([^"]+)"/g)].map((match) => ({ zh: match[1], en: match[2] }));
  if (arms.length !== 2) {
    throw new Error(node("base-literals", `expected the base module to hold exactly two "zh ? … : …" arms inside receiptLabel and read ${arms.length}; the byte comparison would be meaningless`));
  }
  const [present, absent] = arms;
  return { presentZh: present.zh, presentEn: present.en, absentZh: absent.zh, absentEn: absent.en };
}

const refusalBody = (extra: Record<string, unknown> = {}) =>
  JSON.stringify({ detail: "SENT-9F2K-4227 upstream wording that must never reach the glass", ...extra });

/** Land on the wizard's review step with a filled draft, in the traveller's own language. */
async function openReviewStep(page: Page, locale: "zh" | "en"): Promise<void> {
  await page.addInitScript(
    ([key, seed, lang]) => {
      localStorage.clear();
      localStorage.setItem("citynexus.locale", lang);
      localStorage.removeItem("citynexus.v8.journey_id");
      localStorage.setItem(key, JSON.stringify({ step: 3, draft: seed }));
    },
    [DRAFT_KEY, DRAFT, locale === "zh" ? "zh-CN" : "en"] as const,
  );
  await page.goto("/v8/hub", { waitUntil: "load" });
  await expect(page.getByTestId("trial-step3-body")).toBeVisible({ timeout: 30_000 });
}

/** The travelers leg always succeeds here: the refusal under test is the journey create. */
async function refuseCreate(page: Page, body: string): Promise<void> {
  await page.route("**/api/v1/travelers", (route) =>
    route.request().method() !== "POST"
      ? route.fallback()
      : route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ id: "trv-ord0557fb" }) }),
  );
  await page.route("**/api/v1/journeys", (route) =>
    route.request().method() !== "POST"
      ? route.fallback()
      : route.fulfill({ status: 422, contentType: "application/json; charset=utf-8", body }),
  );
}

async function openReceiptCell(page: Page, arm: string): Promise<void> {
  const create = page.getByTestId("trial-create");
  await expect(create, node(arm, "确认页挡住了这一按，创建从未发出")).not.toHaveAttribute("aria-disabled", "true", { timeout: 5_000 });
  await create.click();
  await expect(
    page.getByTestId("trial-create-error"),
    node(arm, "创建被拒，但这屏没有出自己的失败面板"),
  ).toBeVisible({ timeout: 20_000 });
  await page.getByTestId("create-technical-toggle").click();
  await expect(
    page.getByTestId(CELL),
    node(arm, "折叠打开了却没有那一格；这一臂没有可读的东西"),
  ).toBeVisible({ timeout: 20_000 });
}

async function readCell(page: Page): Promise<{ text: string; present: string | null; receipt: string | null }> {
  const cell = page.getByTestId(CELL);
  await cell.scrollIntoViewIfNeeded();
  return {
    text: clean(await cell.innerText()),
    present: await cell.getAttribute("data-cnx-receipt-present"),
    receipt: await cell.getAttribute("data-cnx-receipt"),
  };
}

function writeJsonEvidence(name: string, payload: Record<string, unknown>): void {
  writeFileSync(
    evidencePath("ord0557fb", `${name}.json`),
    JSON.stringify(
      {
        run: process.env.CITYNEXUS_E2E_RUN_ID ?? "dev",
        git_head: process.env.CITYNEXUS_E2E_GIT_HEAD ?? "unknown",
        base_tip: BASE_TIP || "unset",
        ...payload,
      },
      null,
      2,
    ) + "\n",
    "utf8",
  );
}

for (const locale of ["zh", "en"] as const) {
  const absentId = locale === "zh" ? "R1" : "R3";
  const presentId = locale === "zh" ? "R2" : "R4";

  test(`${absentId} ${locale} 屏：服务器没给回执号那一格逐字没动`, async ({ page }) => {
    test.setTimeout(180_000);
    const arm = `absent-receipt-${locale}`;
    await refuseCreate(page, refusalBody());
    await openReviewStep(page, locale);
    await openReceiptCell(page, arm);
    const cell = await readCell(page);
    expect(cell.text, node(arm, `屏上念的是 "${cell.text}"，改前那一代念的是 "${PAINTED[locale].absent}"`)).toBe(PAINTED[locale].absent);
    expect(cell.present, node(arm, `这一臂没有被标成缺席，读数归给了错的分支：${JSON.stringify(cell)}`)).toBe("false");
    expect(cell.receipt, node(arm, `缺席那一格里印出了一枚号，说明它不是缺席：${JSON.stringify(cell)}`)).toBe(MISSING_TOKEN);
    await page.getByTestId(CELL).screenshot({ path: evidencePath("ord0557fb", `receipt-absent-${locale}.png`) });
    writeJsonEvidence(`${absentId}-absent-${locale}`, { cell, expected: PAINTED[locale].absent });
  });

  test(`${presentId} ${locale} 屏：真给了形状合规的回执号那一格逐字没动`, async ({ page }) => {
    test.setTimeout(180_000);
    const arm = `present-receipt-${locale}`;
    await refuseCreate(page, refusalBody({ error_receipt_id: RECEIPT }));
    await openReviewStep(page, locale);
    await openReceiptCell(page, arm);
    const cell = await readCell(page);
    expect(cell.text, node(arm, `屏上念的是 "${cell.text}"，改前那一代念的是 "${PAINTED[locale].present}"`)).toBe(PAINTED[locale].present);
    expect(cell.present, node(arm, `这一臂没有被标成在场：${JSON.stringify(cell)}`)).toBe("true");
    expect(cell.receipt, node(arm, `属性里没有服务器给的那枚号，屏上的数就没有归属：${JSON.stringify(cell)}`)).toBe(RECEIPT);
    await page.getByTestId(CELL).screenshot({ path: evidencePath("ord0557fb", `receipt-present-${locale}.png`) });
    writeJsonEvidence(`${presentId}-present-${locale}`, { cell, expected: PAINTED[locale].present });
  });
}

test("R5 字典两侧的字节就是改前源码里那几个字", async () => {
  const arm = "dictionary-matches-base-literals";
  if (BASE_PREREQ) throw new Error(node(arm, BASE_PREREQ));
  const blocks = dictionaryBlocks();
  const base = baseLiterals();
  const pairs = [
    { side: "en", key: KEY_PRESENT, dictionary: blocks.en[KEY_PRESENT], base: base.presentEn },
    { side: "zh-CN", key: KEY_PRESENT, dictionary: blocks.zhCN[KEY_PRESENT], base: base.presentZh },
    { side: "en", key: KEY_ABSENT, dictionary: blocks.en[KEY_ABSENT], base: base.absentEn },
    { side: "zh-CN", key: KEY_ABSENT, dictionary: blocks.zhCN[KEY_ABSENT], base: base.absentZh },
  ];
  for (const pair of pairs) {
    expect(
      pair.dictionary,
      node(arm, `${pair.key} 的 ${pair.side} 侧是 "${pair.dictionary}"，而改前那枚模块写的是 "${pair.base}" — 这一单搬字，不改字`),
    ).toBe(pair.base);
  }
  writeJsonEvidence("r5-base-literal-pairing", { pairs });
});

test("R6 写死的串确实从模块里走了", async () => {
  const arm = "source-no-longer-invents-words";
  const text = readFileSync(MODULE, "utf8");
  for (const forbidden of ['"服务器回执号"', '"服务器未给回执号"', '"server receipt"', '"no server receipt"']) {
    expect(
      text.includes(forbidden),
      node(arm, `${forbidden} 还写死在这枚模块里 — 那字典就成了第二份拷贝，不是来源`),
    ).toBe(false);
  }
  for (const key of [KEY_PRESENT, KEY_ABSENT]) {
    expect(
      new RegExp(`dictionaryText\\([\\s\\S]{0,140}?"${key}"`).test(text),
      node(arm, `${key} 没有被这枚模块读到`),
    ).toBe(true);
  }
});
