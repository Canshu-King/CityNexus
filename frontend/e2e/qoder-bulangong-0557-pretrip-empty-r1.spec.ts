/**
 * ORD-0557 兜底行 (lane 补栏工) — the pre-trip checklist's empty-state sentence is read from the
 * dictionaries.
 *
 * The draft table's row for this file is `frontend/src/lib/pretripChecklist.ts:118`:
 * 「这一代都没有报出。」/ "Neither one is open on this generation.". Nothing held these words in the
 * dictionary, so one key is added with both arms (`detail.pretripNeitherOpen`), the Chinese side being
 * the words already on the glass. The domain follows the panel's own siblings — `detail.pretripAria`,
 * `detail.pretripKicker`, `detail.pretripHeading` — rather than the draft's three-segment suggestion,
 * because the standing rule for this order family is a lowercase two-segment key.
 *
 * Arms:
 *
 *   E1/E2  the sentence as the traveller reads it on the hub, zh then en, from `innerText` of the row
 *          inside the panel's own empty block — and the panel heading above it is read too, because
 *          the sentence's subject IS that heading (ORD-0401 ①), so an arm that found the words under a
 *          different heading would be measuring the wrong face;
 *   E3     the live action beside the sentence: the row is not a caption, it must still be pressable
 *          and must still name where it goes;
 *   E4     the dictionary's two arms are byte-for-byte the two literals the base generation's own blob
 *          carried (re-derived from that blob, not from memory);
 *   E5     the module no longer holds the literals and does name the key.
 */
import { expect, test, type Page } from "@playwright/test";
import { execSync } from "node:child_process";
import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import { evidencePath } from "./_qoderEvidence";

const FILE = "e2e/qoder-bulangong-0557-pretrip-empty-r1.spec.ts";
const node = (id: string, detail: string) => `${FILE} :: ${id} — ${detail}`;

const BASE_TIP = process.env.CITYNEXUS_ORD0557P_BASE_TIP ?? "";
const BASE_PREREQ = /^[0-9a-f]{40}$/.test(BASE_TIP)
  ? null
  : "missing environment variable: CITYNEXUS_ORD0557P_BASE_TIP must be the 40-hex generation this candidate was cut from";

const MODULE = fileURLToPath(new URL("../src/lib/pretripChecklist.ts", import.meta.url));
const DICTIONARY = fileURLToPath(new URL("../src/i18n/LocaleContext.tsx", import.meta.url));

const KEY = "detail.pretripNeitherOpen";
const ACTION_ROUTE = "studio";

const PAINTED: Record<"zh" | "en", string> = {
  zh: "这一代都没有报出。",
  en: "Neither one is open on this generation.",
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

/** The base module's own two words, read out of the base generation's bytes. */
function baseLiterals(): { zh: string; en: string } {
  let text: string;
  try {
    text = execSync(`git show ${BASE_TIP}:frontend/src/lib/pretripChecklist.ts`, { encoding: "utf8", maxBuffer: 8 * 1024 * 1024 });
  } catch (error) {
    throw new Error(node("base-literals", `the object store cannot answer for ${BASE_TIP} (${String(error).slice(0, 180)}); in a git-archive export there is no store to ask, and this arm refuses rather than passing on an empty parse`));
  }
  const match = text.match(/zh \? "([^"]+)" : "([^"]+)"/);
  if (!match) {
    throw new Error(node("base-literals", "the base module's empty-state ternary is not where it was, so the byte comparison would be meaningless"));
  }
  return { zh: match[1], en: match[2] };
}

/** Open the hub in the traveller's language, with the journey this run seeded. */
async function openHub(page: Page, locale: "zh" | "en"): Promise<void> {
  await page.addInitScript((value) => {
    localStorage.setItem("citynexus.locale", value);
  }, locale === "zh" ? "zh-CN" : "en");
  await page.goto("/v8/hub", { waitUntil: "load" });
  await expect(
    page.getByTestId("pretrip-checklist"),
    node("surface", "行前清单没上屏，这一臂没有可读的东西"),
  ).toBeVisible({ timeout: 30_000 });
  await expect(page.getByTestId("pretrip-empty")).toBeVisible({ timeout: 20_000 });
}

function writeJsonEvidence(name: string, payload: Record<string, unknown>): void {
  writeFileSync(
    evidencePath("ord0557p", `${name}.json`),
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
  const id = locale === "zh" ? "E1" : "E2";
  test(`${id} ${locale} 屏：空态那一句逐字没动，且仍挂在它自己的标题下`, async ({ page }) => {
    test.setTimeout(180_000);
    const arm = `empty-sentence-${locale}`;
    await openHub(page, locale);
    const panel = page.getByTestId("pretrip-checklist");
    const heading = clean(await panel.locator("h2").innerText());
    const sentence = clean(await page.getByTestId("pretrip-empty").locator("span").first().innerText());
    expect(sentence, node(arm, `空态念的是 "${sentence}"，改前那一代念的是 "${PAINTED[locale]}"`)).toBe(PAINTED[locale]);
    expect(heading.length > 0, node(arm, "标题是空的，说明这句挂在错的面上")).toBe(true);
    const box = await page.getByTestId("pretrip-empty").boundingBox();
    const head = await panel.locator("h2").boundingBox();
    expect(
      box !== null && head !== null && box.y > head.y,
      node(arm, `这一行不在标题之下（heading=${JSON.stringify(head)} row=${JSON.stringify(box)}）`),
    ).toBe(true);
    await page.getByTestId("pretrip-empty").screenshot({ path: evidencePath("ord0557p", `pretrip-empty-${locale}.png`) });
    writeJsonEvidence(`${id}-sentence-${locale}`, { heading, sentence, expected: PAINTED[locale] });
  });
}

test("E3 那一句旁边的动作还活着，并且说自己去哪里", async ({ page }) => {
  test.setTimeout(180_000);
  const arm = "empty-state-action";
  await openHub(page, "zh");
  const action = page.getByTestId("pretrip-empty-action");
  await expect(action).toBeVisible();
  const label = clean(await action.innerText());
  expect(label.length > 0, node(arm, "空态动作没有标签，等于没有出口")).toBe(true);
  await action.scrollIntoViewIfNeeded();
  await action.click();
  await expect(
    page.getByTestId("pretrip-checklist"),
    node(arm, `点了「${label}」之后这一屏整块消失，说明它没有把 traveller 送到它说的那一面`),
  ).toHaveCount(0);
  writeJsonEvidence("e3-action", { label, expected_route: ACTION_ROUTE });
});

test("E4 字典两侧的字节就是改前源码里那两句", async () => {
  const arm = "dictionary-matches-base-literals";
  if (BASE_PREREQ) throw new Error(node(arm, BASE_PREREQ));
  const blocks = dictionaryBlocks();
  const base = baseLiterals();
  const pairs = [
    { side: "en", key: KEY, dictionary: blocks.en[KEY], base: base.en },
    { side: "zh-CN", key: KEY, dictionary: blocks.zhCN[KEY], base: base.zh },
  ];
  for (const pair of pairs) {
    expect(
      pair.dictionary,
      node(arm, `${pair.key} 的 ${pair.side} 侧是 "${pair.dictionary}"，而改前那枚模块写的是 "${pair.base}" — 这一单搬字，不改字`),
    ).toBe(pair.base);
  }
  writeJsonEvidence("e4-base-literal-pairing", { pairs });
});

test("E5 写死的两句确实从模块里走了", async () => {
  const arm = "source-no-longer-invents-words";
  const text = readFileSync(MODULE, "utf8");
  for (const forbidden of ['"这一代都没有报出。"', '"Neither one is open on this generation."']) {
    expect(
      text.includes(forbidden),
      node(arm, `${forbidden} 还写死在这枚模块里 — 字典就成了第二份拷贝，不是来源`),
    ).toBe(false);
  }
  expect(
    new RegExp(`dictionaryText\\([\\s\\S]{0,80}?"${KEY}"`).test(text),
    node(arm, `${KEY} 没有被这枚模块读到`),
  ).toBe(true);
});
