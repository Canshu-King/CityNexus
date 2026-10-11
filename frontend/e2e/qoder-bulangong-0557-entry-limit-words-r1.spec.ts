/**
 * ORD-0557 (lane 补栏工) — `lib/entryLimits.ts` reads the words it invents from the dictionaries.
 *
 * The commander's table gave three self-made strings in this one file:
 *   `:100` 「${field.min} ${field.unitZh}起」, `:121` 「必填」, `:121` 「选填」.
 * They now come from `trial.rangeFrom`, `trial.fieldRequired` and `trial.fieldOptional`. The English
 * arm of the range key replaces the `from …` twin of that same line (`:104`), because a key whose
 * other side nothing reads is a dead arm, and the order asks for both sides of every key.
 *
 * What has to hold — each of these is a different property:
 *
 *   S1/S2  the glass still says, in BOTH locales, exactly what it said before. This is a lift, not a
 *          rewrite, so one differing character is a defect; assertions read `innerText`, never a
 *          `data-*` mirror;
 *   S3     the dictionary's two arms are byte-for-byte the words the PRE-change source carried. That
 *          wording is re-derived from the base generation's own blob rather than from memory, so
 *          "nothing was reworded" is measured on both sides;
 *   S4     the module no longer holds the literals and does hold the key names;
 *   S5     nothing that was substituted leaks onto the glass — an unfilled `{min}` or a printed key
 *          name would read as a pass in the source and a defect on screen;
 *   S6     the form still works: the same bounds on the same controls (`entryFieldBounds` is the half
 *          of this file this order did not touch, and this arm checks rather than assumes it), and the
 *          step still turns.
 *
 * The base generation is required, not defaulted: evidence that cannot name the bytes it was cut
 * against is not evidence. In a `git archive` export the object store cannot be asked, and S3 says so
 * instead of passing on an empty parse.
 */
import { expect, test, type Page } from "@playwright/test";
import { execSync } from "node:child_process";
import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import { evidencePath } from "./_qoderEvidence";

const FILE = "e2e/qoder-bulangong-0557-entry-limit-words-r1.spec.ts";
const node = (id: string, detail: string) => `${FILE} :: ${id} — ${detail}`;

const BASE_TIP = process.env.CITYNEXUS_ORD0557_BASE_TIP ?? "";
const BASE_PREREQ = /^[0-9a-f]{40}$/.test(BASE_TIP)
  ? null
  : "missing environment variable: CITYNEXUS_ORD0557_BASE_TIP must be the 40-hex generation this candidate was cut from";

const MODULE = fileURLToPath(new URL("../src/lib/entryLimits.ts", import.meta.url));
const DICTIONARY = fileURLToPath(new URL("../src/i18n/LocaleContext.tsx", import.meta.url));

const KEY_REQUIRED = "trial.fieldRequired";
const KEY_OPTIONAL = "trial.fieldOptional";
const KEY_RANGE_FROM = "trial.rangeFrom";
const LABELS = ["trial-party-label", "trial-rooms-label", "trial-budget-label", "trial-stay-budget-label"];

/** The four labels of the entry step as the pre-change code composed them. Which fact each one names
 *  (required? which bound?) still comes from `ENTRY_FIELDS`; only the words moved. */
const PAINTED: Record<"zh" | "en", Record<string, string>> = {
  zh: {
    "trial-party-label": "旅行人数（必填 · 1-20 人）",
    "trial-rooms-label": "房间数（建议值，可调整）（选填 · 1-20 间）",
    "trial-budget-label": "总预算（必填 · 1 元起）",
    "trial-stay-budget-label": "住宿预算（选填 · 0 元起）",
  },
  en: {
    "trial-party-label": "Travellers（required · 1-20 people）",
    "trial-rooms-label": "Rooms (suggested)（optional · 1-20 rooms）",
    "trial-budget-label": "Total budget（required · from 1 CNY）",
    "trial-stay-budget-label": "Stay budget（optional · from 0 CNY）",
  },
};

type PaintedLocale = keyof typeof PAINTED;

const clean = (value: string | null | undefined) => String(value ?? "");

/** A dictionary is two blocks; a line number for their boundary rots the moment anyone adds a word.
 *  Markers come from the source, and a parse that reads too few keys says so instead of passing. */
function dictionaryBlocks(): Record<"en" | "zhCN", Record<string, string>> {
  const src = readFileSync(DICTIONARY, "utf8");
  const blocks: Record<"en" | "zhCN", Record<string, string>> = { en: {}, zhCN: {} };
  for (const tag of ["en", "zhCN"] as const) {
    const at = src.indexOf(tag === "en" ? "const en: Dict = {" : "const zhCN: Dict = {");
    if (at < 0) {
      throw new Error(node("dictionary-parse", `the ${tag} table marker moved; this arm cannot tell an absent key from a moved file`));
    }
    const end = src.indexOf("\n};", at);
    const parsed: Record<string, string> = {};
    for (const match of src.slice(at, end).matchAll(/^\s*"([^"]+)":\s*"((?:[^"\\]|\\.)*)"/gm)) {
      parsed[match[1]] = JSON.parse(`"${match[2]}"`);
    }
    if (Object.keys(parsed).length < 100) {
      throw new Error(node("dictionary-parse", `only ${Object.keys(parsed).length} keys parsed from the ${tag} block — blinded`));
    }
    blocks[tag] = parsed;
  }
  return blocks;
}

/** The base generation's own bytes, asked of the object store. */
function baseModuleText(): string {
  try {
    return execSync(`git show ${BASE_TIP}:frontend/src/lib/entryLimits.ts`, {
      encoding: "utf8",
      maxBuffer: 8 * 1024 * 1024,
    });
  } catch (error) {
    throw new Error(
      node("base-words-parse", `the object store cannot answer for ${BASE_TIP} (${String(error).slice(0, 180)}); in a git-archive export there is no store to ask, and this arm refuses rather than reporting a vacuous pass`),
    );
  }
}

type BaseWords = Record<"rangeZh" | "rangeEn" | "requiredZh" | "optionalZh" | "requiredEn" | "optionalEn", string>;

/**
 * The words the base module painted, re-derived from the base source.
 *
 * A pattern that matches nothing must not yield "": each field is asserted present, so a base line
 * that moved reddens this arm instead of quietly comparing against an empty string.
 */
function basePaintedWords(): BaseWords {
  const text = baseModuleText();
  const grab = (pattern: RegExp, label: string): string => {
    const match = text.match(pattern);
    if (!match) {
      throw new Error(node("base-words-parse", `${label} is not where the base generation had it, so the byte comparison would be meaningless`));
    }
    return match[1];
  };
  /* The holes the base filled from ENTRY_FIELDS become the placeholders the dictionary carries. */
  const toPlaceholders = (template: string) =>
    template
      .replace(/\$\{field\.min\}/g, "{min}")
      .replace(/\$\{field\.max\}/g, "{max}")
      .replace(/\$\{field\.unitZh\}/g, "{unit}")
      .replace(/\$\{field\.unitEn\}/g, "{unit}");

  return {
    rangeZh: toPlaceholders(grab(/\? `([^`]*\$\{field\.unitZh\}起)`/, "the zh open-ended range template")),
    rangeEn: toPlaceholders(grab(/\? `(from [^`]*\$\{field\.unitEn\})`/, "the en open-ended range template")),
    requiredZh: grab(/field\.required \? "([^"]+)" :/, "the zh required word"),
    optionalZh: grab(/field\.required \? "[^"]+" : "([^"]+)"/, "the zh optional word"),
    requiredEn: grab(/: field\.required \? "([^"]+)" :/, "the en required word"),
    optionalEn: grab(/: field\.required \? "[^"]+" : "([^"]+)"/, "the en optional word"),
  };
}

/** Step 2 of the entry wizard, reached through the front door in the traveller's own language. */
async function openEntryStep(page: Page, locale: PaintedLocale): Promise<void> {
  await page.addInitScript((value) => {
    localStorage.removeItem("citynexus.v8.journey_id");
    localStorage.removeItem("citynexus.v8.trial_draft");
    localStorage.setItem("citynexus.locale", value);
  }, locale === "zh" ? "zh-CN" : "en");
  await page.goto("/v8/hub", { waitUntil: "load" });
  await expect(page.getByTestId("trial-setup")).toBeVisible({ timeout: 30_000 });
  /* Step 1 blocks on exactly these three fields (`missingStep1`), and on nothing else. */
  await page.getByTestId("trial-city").fill(locale === "zh" ? "天津" : "Tianjin");
  await page.getByTestId("trial-arrival").fill(locale === "zh" ? "天津站" : "Tianjin West Station");
  await page.getByTestId("trial-departure").fill(locale === "zh" ? "北京南站" : "Beijing South Station");
  await page.getByTestId("trial-next").click();
  await expect(page.getByTestId("trial-step2-body")).toBeVisible({ timeout: 20_000 });
}

function writeJsonEvidence(name: string, payload: Record<string, unknown>): void {
  writeFileSync(
    evidencePath("ord0557", `${name}.json`),
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

test("S1 中文那屏逐字没动", async ({ page }) => {
  test.setTimeout(180_000);
  const arm = "zh-glass-unchanged";
  await openEntryStep(page, "zh");
  const readings: Record<string, string> = {};
  for (const testId of LABELS) {
    const label = page.getByTestId(testId);
    await label.scrollIntoViewIfNeeded();
    readings[testId] = clean(await label.innerText());
    expect(
      readings[testId],
      node(arm, `${testId} paints "${readings[testId]}" while the pre-change composition was "${PAINTED.zh[testId]}"`),
    ).toBe(PAINTED.zh[testId]);
  }
  await page.getByTestId("trial-step2-body").screenshot({ path: evidencePath("ord0557", "entry-step2-zh.png") });
  writeJsonEvidence("s1-painted-zh", { painted: readings });
});

test("S2 英文那屏逐字没动", async ({ page }) => {
  test.setTimeout(180_000);
  const arm = "en-glass-unchanged";
  await openEntryStep(page, "en");
  const readings: Record<string, string> = {};
  for (const testId of LABELS) {
    const label = page.getByTestId(testId);
    await label.scrollIntoViewIfNeeded();
    readings[testId] = clean(await label.innerText());
    expect(
      readings[testId],
      node(arm, `${testId} paints "${readings[testId]}" while the pre-change composition was "${PAINTED.en[testId]}"`),
    ).toBe(PAINTED.en[testId]);
  }
  await page.getByTestId("trial-step2-body").screenshot({ path: evidencePath("ord0557", "entry-step2-en.png") });
  writeJsonEvidence("s2-painted-en", { painted: readings });
});

test("S5 屏上没有残余的占位符，也没有键名漏出来", async ({ page }) => {
  test.setTimeout(180_000);
  const arm = "no-substitution-residue";
  for (const locale of ["zh", "en"] as const) {
    await openEntryStep(page, locale);
    const body = clean(await page.getByTestId("trial-step2-body").innerText());
    for (const forbidden of ["{min}", "{unit}", "{max}", KEY_RANGE_FROM, KEY_REQUIRED, KEY_OPTIONAL]) {
      expect(
        body.includes(forbidden),
        node(arm, `the ${locale} glass still carries "${forbidden}" — a half-installed key reads green in the source and broken on screen`),
      ).toBe(false);
    }
  }
});

test("S6 控件的边界没动，步骤还走得下去", async ({ page }) => {
  test.setTimeout(180_000);
  const arm = "controls-still-bound";
  await openEntryStep(page, "zh");
  const bounds: Record<string, { min: string | null; max: string | null; value: string }> = {};
  for (const testId of ["trial-party", "trial-rooms", "trial-budget", "trial-stay-budget"]) {
    const input = page.getByTestId(testId);
    bounds[testId] = {
      min: await input.getAttribute("min"),
      max: await input.getAttribute("max"),
      value: await input.inputValue(),
    };
  }
  /* `entryFieldBounds` is the half of the file this order left alone; these pairs are what the same
     entries declared before it, restated here so a silent move cannot pass. */
  expect(bounds["trial-party"].min, node(arm, "party min moved")).toBe("1");
  expect(bounds["trial-party"].max, node(arm, "party max moved")).toBe("20");
  expect(bounds["trial-rooms"].min, node(arm, "rooms min moved")).toBe("1");
  expect(bounds["trial-rooms"].max, node(arm, "rooms max moved")).toBe("20");
  expect(bounds["trial-budget"].min, node(arm, "budget min moved")).toBe("1");
  expect(bounds["trial-budget"].max, node(arm, "budget grew a max it never had")).toBe(null);
  expect(bounds["trial-stay-budget"].min, node(arm, "stayBudget min moved")).toBe("0");
  expect(bounds["trial-stay-budget"].max, node(arm, "stayBudget grew a max it never had")).toBe(null);

  await page.getByTestId("trial-next").click();
  await expect(page.getByTestId("trial-step3-body")).toBeVisible({ timeout: 20_000 });
});

test("S3 字典两侧的字节就是改前源码里那几个字", async () => {
  const arm = "dictionary-matches-base-literals";
  if (BASE_PREREQ) throw new Error(node(arm, BASE_PREREQ));
  const blocks = dictionaryBlocks();
  const base = basePaintedWords();
  const pairs: Array<{ side: string; key: string; dictionary: string; base: string }> = [
    { side: "en", key: KEY_REQUIRED, dictionary: blocks.en[KEY_REQUIRED], base: base.requiredEn },
    { side: "zh-CN", key: KEY_REQUIRED, dictionary: blocks.zhCN[KEY_REQUIRED], base: base.requiredZh },
    { side: "en", key: KEY_OPTIONAL, dictionary: blocks.en[KEY_OPTIONAL], base: base.optionalEn },
    { side: "zh-CN", key: KEY_OPTIONAL, dictionary: blocks.zhCN[KEY_OPTIONAL], base: base.optionalZh },
    { side: "en", key: KEY_RANGE_FROM, dictionary: blocks.en[KEY_RANGE_FROM], base: base.rangeEn },
    { side: "zh-CN", key: KEY_RANGE_FROM, dictionary: blocks.zhCN[KEY_RANGE_FROM], base: base.rangeZh },
  ];
  for (const pair of pairs) {
    expect(
      pair.dictionary,
      node(arm, `${pair.key} on the ${pair.side} side holds "${pair.dictionary}" while the base generation painted "${pair.base}" — this order lifts words, it does not rewrite them`),
    ).toBe(pair.base);
  }
  writeJsonEvidence("s3-base-literal-pairing", { pairs });
});

test("S4 写死的串确实从模块里走了", async () => {
  const arm = "source-no-longer-invents-words";
  const text = readFileSync(MODULE, "utf8");
  for (const forbidden of ["}起", '"必填"', '"选填"', "`from ${"]) {
    expect(
      text.includes(forbidden),
      node(arm, `"${forbidden}" is still composed in this module — the dictionary would then be a rival copy, not the source`),
    ).toBe(false);
  }
  for (const key of [KEY_REQUIRED, KEY_OPTIONAL, KEY_RANGE_FROM]) {
    expect(
      new RegExp(`dictionaryText\\([\\s\\S]{0,120}?"${key}"`).test(text),
      node(arm, `${key} is not read by this module at all`),
    ).toBe(true);
  }
});
